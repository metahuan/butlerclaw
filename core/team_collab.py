#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core.team_collab

团队协作模块：
- 配置同步机制
- 权限模型（管理员/成员/访客）
- 共享技能仓库
- 操作审计日志
"""

from __future__ import annotations

import os
import json
import hashlib
import threading
import subprocess
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Set
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict


class UserRole(Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"


class AuditAction(Enum):
    """审计操作类型"""
    LOGIN = "login"
    LOGOUT = "logout"
    CONFIG_VIEW = "config_view"
    CONFIG_UPDATE = "config_update"
    SKILL_INSTALL = "skill_install"
    SKILL_UNINSTALL = "skill_uninstall"
    SKILL_UPDATE = "skill_update"
    INSTANCE_CONNECT = "instance_connect"
    INSTANCE_DISCONNECT = "instance_disconnect"
    INSTANCE_COMMAND = "instance_command"
    TEAM_MEMBER_ADD = "team_member_add"
    TEAM_MEMBER_REMOVE = "team_member_remove"
    TEAM_MEMBER_UPDATE = "team_member_update"
    SYNC_PUSH = "sync_push"
    SYNC_PULL = "sync_pull"


class SyncStatus(Enum):
    """同步状态枚举"""
    PENDING = "pending"
    SYNCING = "syncing"
    SYNCED = "synced"
    CONFLICT = "conflict"
    ERROR = "error"


@dataclass
class TeamMember:
    """团队成员"""
    id: str
    username: str
    email: str
    role: UserRole
    avatar: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    last_active: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def has_permission(self, action: str) -> bool:
        """检查是否有权限执行操作"""
        permissions = {
            UserRole.ADMIN: [
                "config_view", "config_update", "skill_install", "skill_uninstall",
                "skill_update", "instance_connect", "instance_disconnect", "instance_command",
                "team_member_add", "team_member_remove", "team_member_update",
                "sync_push", "sync_pull"
            ],
            UserRole.MEMBER: [
                "config_view", "skill_install", "skill_update",
                "instance_connect", "instance_disconnect", "instance_command",
                "sync_pull"
            ],
            UserRole.GUEST: [
                "config_view", "sync_pull"
            ],
        }
        return action in permissions.get(self.role, [])


@dataclass
class AuditLogEntry:
    """审计日志条目"""
    id: str
    timestamp: datetime
    user_id: str
    username: str
    action: AuditAction
    target_type: str
    target_id: str
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: str = ""
    user_agent: str = ""
    success: bool = True
    error_message: str = ""


@dataclass
class SharedSkill:
    """共享技能"""
    id: str
    name: str
    description: str
    version: str
    author_id: str
    author_name: str
    source_url: str
    install_command: str
    category: str = ""
    tags: List[str] = field(default_factory=list)
    rating: float = 0.0
    install_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_official: bool = False
    is_approved: bool = False


@dataclass
class ConfigSyncItem:
    """配置同步项"""
    id: str
    file_path: str
    file_hash: str
    content: str
    modified_by: str
    modified_at: datetime
    sync_status: SyncStatus
    version: int = 1
    
    @staticmethod
    def calculate_hash(content: str) -> str:
        """计算内容哈希"""
        return hashlib.md5(content.encode("utf-8")).hexdigest()


class TeamCollaborationManager:
    """
    团队协作管理器 - OpenClaw 生态专属管家
    
    核心功能：
    - 团队成员管理 (SQLite 持久化)
    - Agent 模板管理 (团队共享的角色定义)
    - 细粒度权限控制 (谁可以用哪个 Agent)
    - 多实例 Agent 分发 (部署到成员的 OpenClaw 实例)
    - 操作审计日志 (持久化存储)
    """
    
    def __init__(self, team_id: str = "default", config_dir: Optional[str] = None):
        self.team_id = team_id
        self.config_dir = config_dir or os.path.expanduser("~/.butlerclaw")
        self.db_path = os.path.join(self.config_dir, f"team_{team_id}.db")
        
        # 内存缓存
        self._current_user: Optional[TeamMember] = None
        self._members: Dict[str, TeamMember] = {}
        self._audit_logs: List[AuditLogEntry] = []
        self._shared_skills: Dict[str, SharedSkill] = {}
        self._sync_items: Dict[str, ConfigSyncItem] = {}
        
        # Agent 管理相关
        self._agents: Dict[str, AgentInfo] = {}
        self._agent_policies: Dict[str, AgentUsagePolicy] = {}
        self._agent_templates: Dict[str, AgentTemplate] = {}  # 团队 Agent 模板
        self._member_agent_access: Dict[str, MemberAgentAccess] = {}  # key: "user_id:agent_id"
        
        self._lock = threading.Lock()
        
        # 初始化数据库
        self._init_database()
        self._load_from_database()
    
    def login(self, member: TeamMember) -> bool:
        """用户登录"""
        self._current_user = member
        member.last_active = datetime.now()
        return True
    
    def logout(self):
        """用户登出"""
        self._current_user = None
    
    def get_current_user(self) -> Optional[TeamMember]:
        """获取当前用户"""
        return self._current_user
    
    def check_permission(self, action: str) -> bool:
        """检查当前用户权限"""
        if not self._current_user:
            return False
        return self._current_user.has_permission(action)
    
    def add_team_member(self, member: TeamMember) -> bool:
        """添加团队成员（需要管理员权限）"""
        if not self.check_permission("team_member_add"):
            return False
        
        with self._lock:
            if member.id in self._members:
                return False
            self._members[member.id] = member
            return True
    
    def remove_team_member(self, member_id: str) -> bool:
        """移除团队成员（需要管理员权限）"""
        if not self.check_permission("team_member_remove"):
            return False
        
        with self._lock:
            if member_id in self._members:
                del self._members[member_id]
                return True
            return False

    def update_team_member_role(self, member_id: str, role: UserRole) -> bool:
        """更新团队成员角色（需要管理员权限）"""
        if not self.check_permission("team_member_update"):
            return False

        with self._lock:
            member = self._members.get(member_id)
            if not member:
                return False
            member.role = role
            member.last_active = datetime.now()
            return True
    
    def get_team_members(self) -> List[TeamMember]:
        """获取所有团队成员"""
        with self._lock:
            return list(self._members.values())
    
    def log_action(
        self,
        action: AuditAction,
        target_type: str = "",
        target_id: str = "",
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: str = "",
    ) -> Optional[AuditLogEntry]:
        """记录操作审计日志"""
        if not self._current_user:
            return None
        
        import uuid
        entry = AuditLogEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            user_id=self._current_user.id,
            username=self._current_user.username,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details or {},
            success=success,
            error_message=error_message,
        )
        
        with self._lock:
            self._audit_logs.append(entry)
        
        return entry
    
    def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        limit: int = 100,
    ) -> List[AuditLogEntry]:
        """获取审计日志"""
        with self._lock:
            logs = self._audit_logs
            
            if user_id:
                logs = [log for log in logs if log.user_id == user_id]
            
            if action:
                logs = [log for log in logs if log.action == action]
            
            # 按时间倒序
            logs = sorted(logs, key=lambda x: x.timestamp, reverse=True)
            
            return logs[:limit]
    
    def add_shared_skill(self, skill: SharedSkill) -> bool:
        """添加共享技能"""
        if not self.check_permission("skill_install"):
            return False
        
        # 设置作者信息
        if self._current_user:
            skill.author_id = self._current_user.id
            skill.author_name = self._current_user.username
        
        with self._lock:
            self._shared_skills[skill.id] = skill
        
        return True
    
    def get_shared_skills(self, approved_only: bool = True) -> List[SharedSkill]:
        """获取共享技能列表"""
        with self._lock:
            skills = list(self._shared_skills.values())
            
            if approved_only:
                skills = [s for s in skills if s.is_approved]
            
            # 按评分排序
            skills.sort(key=lambda s: s.rating, reverse=True)
            
            return skills
    
    def search_shared_skills(self, query: str) -> List[SharedSkill]:
        """搜索共享技能"""
        query = query.lower()
        
        with self._lock:
            return [
                skill for skill in self._shared_skills.values()
                if skill.is_approved and (
                    query in skill.name.lower()
                    or query in skill.description.lower()
                )
            ]
    
    def register_sync_file(self, file_path: str) -> Optional[ConfigSyncItem]:
        """注册文件进行同步"""
        if not self.check_permission("sync_push"):
            return None
        
        if not self._current_user:
            return None
        
        import uuid
        
        # 读取文件内容
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = ""
        
        item = ConfigSyncItem(
            id=str(uuid.uuid4()),
            file_path=file_path,
            file_hash=ConfigSyncItem.calculate_hash(content),
            content=content,
            modified_by=self._current_user.id,
            modified_at=datetime.now(),
            sync_status=SyncStatus.PENDING,
        )
        
        with self._lock:
            self._sync_items[file_path] = item
        
        return item
    
    def get_sync_items(self) -> List[ConfigSyncItem]:
        """获取所有同步项"""
        with self._lock:
            return list(self._sync_items.values())

    # ========== 新增：数据库初始化与持久化 ==========

    def _init_database(self):
        """初始化 SQLite 数据库"""
        import sqlite3
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 团队成员表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_members (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                email TEXT,
                role TEXT NOT NULL,
                avatar TEXT,
                created_at TEXT,
                last_active TEXT,
                metadata TEXT
            )
        """)
        
        # 审计日志表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                user_id TEXT,
                username TEXT,
                action TEXT,
                target_type TEXT,
                target_id TEXT,
                details TEXT,
                ip_address TEXT,
                success INTEGER,
                error_message TEXT
            )
        """)
        
        # Agent 模板表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                emoji TEXT,
                description TEXT,
                role_type TEXT,
                identity_prompt TEXT,
                tools_prompt TEXT,
                default_model TEXT,
                skills TEXT,
                env_vars TEXT,
                created_by TEXT,
                team_id TEXT,
                is_official INTEGER,
                is_shared INTEGER,
                version TEXT,
                changelog TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # 成员权限表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS member_agent_access (
                user_id TEXT,
                agent_template_id TEXT,
                can_use INTEGER,
                can_configure INTEGER,
                can_share INTEGER,
                daily_calls_limit INTEGER,
                monthly_budget_limit REAL,
                custom_model TEXT,
                custom_env_vars TEXT,
                assigned_at TEXT,
                assigned_by TEXT,
                PRIMARY KEY (user_id, agent_template_id)
            )
        """)
        
        # Agent 部署表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_deployments (
                id TEXT PRIMARY KEY,
                template_id TEXT,
                instance_id TEXT,
                deployed_by TEXT,
                status TEXT,
                agent_dir TEXT,
                agent_name TEXT,
                error_message TEXT,
                last_sync_at TEXT,
                last_used_at TEXT,
                total_calls INTEGER,
                deployed_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()

    def _load_from_database(self):
        """从数据库加载数据到内存"""
        import sqlite3
        
        if not os.path.exists(self.db_path):
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 加载团队成员
        cursor.execute("SELECT * FROM team_members")
        for row in cursor.fetchall():
            member = TeamMember(
                id=row[0],
                username=row[1],
                email=row[2] or "",
                role=UserRole(row[3]),
                avatar=row[4] or "",
                created_at=datetime.fromisoformat(row[5]) if row[5] else datetime.now(),
                last_active=datetime.fromisoformat(row[6]) if row[6] else None,
                metadata=json.loads(row[7]) if row[7] else {}
            )
            self._members[member.id] = member
        
        # 加载 Agent 模板
        cursor.execute("SELECT * FROM agent_templates")
        for row in cursor.fetchall():
            template = AgentTemplate(
                id=row[0],
                name=row[1],
                emoji=row[2] or "🤖",
                description=row[3] or "",
                role_type=AgentRoleType(row[4]) if row[4] else AgentRoleType.CUSTOM,
                identity_prompt=row[5] or "",
                tools_prompt=row[6] or "",
                default_model=row[7] or "moonshot/kimi-k2.5",
                skills=json.loads(row[8]) if row[8] else [],
                env_vars=json.loads(row[9]) if row[9] else {},
                created_by=row[10] or "",
                team_id=row[11] or "",
                is_official=bool(row[12]),
                is_shared=bool(row[13]),
                version=row[14] or "1.0.0",
                changelog=json.loads(row[15]) if row[15] else [],
                created_at=datetime.fromisoformat(row[16]) if row[16] else datetime.now(),
                updated_at=datetime.fromisoformat(row[17]) if row[17] else datetime.now()
            )
            self._agent_templates[template.id] = template
        
        # 加载成员权限
        cursor.execute("SELECT * FROM member_agent_access")
        for row in cursor.fetchall():
            access = MemberAgentAccess(
                user_id=row[0],
                agent_template_id=row[1],
                can_use=bool(row[2]),
                can_configure=bool(row[3]),
                can_share=bool(row[4]),
                daily_calls_limit=row[5] or 0,
                monthly_budget_limit=row[6] or 0.0,
                custom_model=row[7],
                custom_env_vars=json.loads(row[8]) if row[8] else {},
                assigned_at=datetime.fromisoformat(row[9]) if row[9] else datetime.now(),
                assigned_by=row[10] or ""
            )
            key = f"{access.user_id}:{access.agent_template_id}"
            self._member_agent_access[key] = access
        
        conn.close()

    def _save_member(self, member: TeamMember):
        """保存成员到数据库"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO team_members 
            (id, username, email, role, avatar, created_at, last_active, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            member.id, member.username, member.email, member.role.value,
            member.avatar, member.created_at.isoformat(),
            member.last_active.isoformat() if member.last_active else None,
            json.dumps(member.metadata)
        ))
        conn.commit()
        conn.close()

    def _save_audit_log(self, entry: AuditLogEntry):
        """保存审计日志到数据库"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs 
            (id, timestamp, user_id, username, action, target_type, target_id, 
             details, ip_address, success, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.id, entry.timestamp.isoformat(), entry.user_id, entry.username,
            entry.action.value, entry.target_type, entry.target_id,
            json.dumps(entry.details), entry.ip_address,
            1 if entry.success else 0, entry.error_message
        ))
        conn.commit()
        conn.close()

    def _save_agent_template(self, template: AgentTemplate):
        """保存 Agent 模板到数据库"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO agent_templates 
            (id, name, emoji, description, role_type, identity_prompt, tools_prompt,
             default_model, skills, env_vars, created_by, team_id, is_official,
             is_shared, version, changelog, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            template.id, template.name, template.emoji, template.description,
            template.role_type.value, template.identity_prompt, template.tools_prompt,
            template.default_model, json.dumps(template.skills),
            json.dumps(template.env_vars), template.created_by, template.team_id,
            1 if template.is_official else 0, 1 if template.is_shared else 0,
            template.version, json.dumps(template.changelog),
            template.created_at.isoformat(), template.updated_at.isoformat()
        ))
        conn.commit()
        conn.close()

    def _save_member_access(self, access: MemberAgentAccess):
        """保存成员权限到数据库"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO member_agent_access 
            (user_id, agent_template_id, can_use, can_configure, can_share,
             daily_calls_limit, monthly_budget_limit, custom_model, custom_env_vars,
             assigned_at, assigned_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            access.user_id, access.agent_template_id,
            1 if access.can_use else 0, 1 if access.can_configure else 0,
            1 if access.can_share else 0, access.daily_calls_limit,
            access.monthly_budget_limit, access.custom_model,
            json.dumps(access.custom_env_vars),
            access.assigned_at.isoformat(), access.assigned_by
        ))
        conn.commit()
        conn.close()

    # ========== 新增：Agent 模板管理接口 ==========

    def create_agent_template(
        self,
        name: str,
        role_type: AgentRoleType,
        identity_prompt: str,
        created_by: str,
        **kwargs
    ) -> Optional[AgentTemplate]:
        """
        创建团队 Agent 模板
        
        需要管理员权限
        """
        if not self.check_permission("team_member_update"):
            return None
        
        import uuid
        template_id = f"{self.team_id}-{self._slugify(name)}-{uuid.uuid4().hex[:8]}"
        
        template = AgentTemplate(
            id=template_id,
            name=name,
            role_type=role_type,
            identity_prompt=identity_prompt,
            created_by=created_by,
            team_id=self.team_id,
            **kwargs
        )
        
        with self._lock:
            self._agent_templates[template_id] = template
        
        self._save_agent_template(template)
        
        # 记录审计日志
        self.log_action(
            AuditAction.CONFIG_UPDATE,
            target_type="agent_template",
            target_id=template_id,
            details={"action": "create", "name": name}
        )
        
        return template

    def get_agent_templates(
        self,
        role_type: Optional[AgentRoleType] = None,
        user_id: Optional[str] = None
    ) -> List[AgentTemplate]:
        """
        获取 Agent 模板列表
        
        如果指定 user_id，则只返回该用户有权限访问的模板
        """
        with self._lock:
            templates = list(self._agent_templates.values())
        
        if role_type:
            templates = [t for t in templates if t.role_type == role_type]
        
        if user_id:
            # 过滤出用户有权限访问的模板
            accessible = []
            for template in templates:
                if self._check_agent_access(user_id, template.id, "use"):
                    accessible.append(template)
            templates = accessible
        
        return sorted(templates, key=lambda x: x.updated_at, reverse=True)

    def get_agent_template(self, template_id: str) -> Optional[AgentTemplate]:
        """获取单个 Agent 模板"""
        with self._lock:
            return self._agent_templates.get(template_id)

    def update_agent_template(self, template_id: str, **updates) -> Optional[AgentTemplate]:
        """更新 Agent 模板"""
        if not self.check_permission("config_update"):
            return None
        
        with self._lock:
            template = self._agent_templates.get(template_id)
            if not template:
                return None
            
            # 版本号递增
            if "identity_prompt" in updates or "skills" in updates:
                major, minor, patch = template.version.split(".")
                template.version = f"{major}.{minor}.{int(patch)+1}"
                template.changelog.append(
                    f"[{datetime.now().isoformat()}] Updated"
                )
            
            for key, value in updates.items():
                if hasattr(template, key):
                    setattr(template, key, value)
            
            template.updated_at = datetime.now()
        
        self._save_agent_template(template)
        
        self.log_action(
            AuditAction.CONFIG_UPDATE,
            target_type="agent_template",
            target_id=template_id,
            details={"action": "update", "fields": list(updates.keys())}
        )
        
        return template

    def delete_agent_template(self, template_id: str) -> bool:
        """删除 Agent 模板"""
        if not self.check_permission("config_update"):
            return False
        
        with self._lock:
            if template_id not in self._agent_templates:
                return False
            del self._agent_templates[template_id]
        
        # 从数据库删除
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM agent_templates WHERE id = ?", (template_id,))
        conn.commit()
        conn.close()
        
        self.log_action(
            AuditAction.CONFIG_UPDATE,
            target_type="agent_template",
            target_id=template_id,
            details={"action": "delete"}
        )
        
        return True

    # ========== 新增：成员权限管理接口 ==========

    def grant_agent_access(
        self,
        template_id: str,
        user_id: str,
        granted_by: str,
        can_use: bool = True,
        can_configure: bool = False,
        can_share: bool = False,
        daily_calls_limit: int = 0,
        monthly_budget_limit: float = 0.0
    ) -> bool:
        """授予成员对 Agent 的访问权限"""
        if not self.check_permission("team_member_update"):
            return False
        
        access = MemberAgentAccess(
            agent_template_id=template_id,
            user_id=user_id,
            can_use=can_use,
            can_configure=can_configure,
            can_share=can_share,
            daily_calls_limit=daily_calls_limit,
            monthly_budget_limit=monthly_budget_limit,
            assigned_by=granted_by
        )
        
        key = f"{user_id}:{template_id}"
        with self._lock:
            self._member_agent_access[key] = access
        
        self._save_member_access(access)
        
        self.log_action(
            AuditAction.TEAM_MEMBER_UPDATE,
            target_type="agent_access",
            target_id=f"{user_id}:{template_id}",
            details={"action": "grant", "template_id": template_id, "user_id": user_id}
        )
        
        return True

    def revoke_agent_access(self, template_id: str, user_id: str) -> bool:
        """撤销成员对 Agent 的访问权限"""
        if not self.check_permission("team_member_update"):
            return False
        
        key = f"{user_id}:{template_id}"
        with self._lock:
            if key not in self._member_agent_access:
                return False
            del self._member_agent_access[key]
        
        # 从数据库删除
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM member_agent_access WHERE user_id = ? AND agent_template_id = ?",
            (user_id, template_id)
        )
        conn.commit()
        conn.close()
        
        self.log_action(
            AuditAction.TEAM_MEMBER_UPDATE,
            target_type="agent_access",
            target_id=f"{user_id}:{template_id}",
            details={"action": "revoke"}
        )
        
        return True

    def _check_agent_access(self, user_id: str, template_id: str, permission: str) -> bool:
        """检查用户对 Agent 的权限"""
        # 检查是否是管理员
        member = self._members.get(user_id)
        if member and member.role == UserRole.ADMIN:
            return True
        
        key = f"{user_id}:{template_id}"
        access = self._member_agent_access.get(key)
        
        if not access:
            return False
        
        if permission == "use":
            return access.can_use
        elif permission == "configure":
            return access.can_configure
        elif permission == "share":
            return access.can_share
        
        return False

    def get_user_accessible_agents(self, user_id: str) -> List[AgentTemplate]:
        """获取用户有权限访问的所有 Agent 模板"""
        return self.get_agent_templates(user_id=user_id)

    # ========== 新增：Agent 部署到实例 ==========

    def deploy_agent_to_instance(
        self,
        template_id: str,
        instance_id: str,
        deployed_by: str,
        custom_name: Optional[str] = None
    ) -> Optional[AgentDeployment]:
        """
        将 Agent 模板部署到目标 OpenClaw 实例
        
        这会：
        1. 在目标实例创建 Agent 目录
        2. 写入 SOUL.md (identity_prompt)
        3. 写入 TOOLS.md (tools_prompt)
        4. 安装绑定的技能
        5. 注册到 OpenClaw
        """
        # 检查权限
        if not self._check_agent_access(deployed_by, template_id, "use"):
            return None
        
        template = self._agent_templates.get(template_id)
        if not template:
            return None
        
        import uuid
        deployment_id = f"{template_id}-{instance_id}-{uuid.uuid4().hex[:8]}"
        
        deployment = AgentDeployment(
            id=deployment_id,
            template_id=template_id,
            instance_id=instance_id,
            deployed_by=deployed_by,
            agent_name=custom_name or template.name,
            status="pending"
        )
        
        # 保存到数据库
        self._save_deployment(deployment)
        
        # 异步执行部署
        threading.Thread(
            target=self._do_deploy_agent,
            args=(deployment, template),
            daemon=True
        ).start()
        
        self.log_action(
            AuditAction.INSTANCE_COMMAND,
            target_type="agent_deployment",
            target_id=deployment_id,
            details={"template_id": template_id, "instance_id": instance_id}
        )
        
        return deployment

    def _do_deploy_agent(self, deployment: AgentDeployment, template: AgentTemplate):
        """实际执行 Agent 部署"""
        try:
            deployment.status = "deploying"
            self._update_deployment_status(deployment)
            
            # 获取实例管理器
            from .instance_manager import get_instance_manager
            instance_mgr = get_instance_manager()
            target = instance_mgr.get_instance(deployment.instance_id)
            
            if not target:
                raise ValueError(f"Instance {deployment.instance_id} not found")
            
            # 构建 Agent 目录路径
            agent_dir = f"~/.openclaw/agents/{self._slugify(deployment.agent_name)}"
            
            # 创建目录
            self._exec_on_instance(target, f"mkdir -p {agent_dir}")
            
            # 写入 SOUL.md
            soul_content = self._generate_soul_md(template, deployment.agent_name)
            self._write_file_on_instance(target, f"{agent_dir}/SOUL.md", soul_content)
            
            # 写入 TOOLS.md
            if template.tools_prompt:
                self._write_file_on_instance(
                    target, f"{agent_dir}/TOOLS.md", template.tools_prompt
                )
            
            # 写入配置
            config = {
                "model": template.default_model,
                "skills": template.skills,
                "env": template.env_vars,
                "version": template.version
            }
            self._write_file_on_instance(
                target,
                f"{agent_dir}/.agent_config.json",
                json.dumps(config, indent=2, ensure_ascii=False)
            )
            
            # 安装技能
            for skill_id in template.skills:
                self._exec_on_instance(target, f"openclaw skills install {skill_id}")
            
            # 注册到 OpenClaw
            self._exec_on_instance(
                target,
                f"openclaw agents add {self._slugify(deployment.agent_name)} --path {agent_dir}"
            )
            
            deployment.status = "running"
            deployment.agent_dir = agent_dir
            deployment.last_sync_at = datetime.now()
            
        except Exception as e:
            deployment.status = "error"
            deployment.error_message = str(e)
        
        self._update_deployment_status(deployment)

    def _save_deployment(self, deployment: AgentDeployment):
        """保存部署记录到数据库"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO agent_deployments 
            (id, template_id, instance_id, deployed_by, status, agent_dir, agent_name,
             error_message, last_sync_at, last_used_at, total_calls, deployed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            deployment.id, deployment.template_id, deployment.instance_id,
            deployment.deployed_by, deployment.status, deployment.agent_dir,
            deployment.agent_name, deployment.error_message,
            deployment.last_sync_at.isoformat() if deployment.last_sync_at else None,
            deployment.last_used_at.isoformat() if deployment.last_used_at else None,
            deployment.total_calls, deployment.deployed_at.isoformat()
        ))
        conn.commit()
        conn.close()

    def _update_deployment_status(self, deployment: AgentDeployment):
        """更新部署状态"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE agent_deployments 
            SET status = ?, agent_dir = ?, error_message = ?, last_sync_at = ?
            WHERE id = ?
        """, (
            deployment.status, deployment.agent_dir, deployment.error_message,
            deployment.last_sync_at.isoformat() if deployment.last_sync_at else None,
            deployment.id
        ))
        conn.commit()
        conn.close()

    def get_deployments(
        self,
        template_id: Optional[str] = None,
        instance_id: Optional[str] = None
    ) -> List[AgentDeployment]:
        """获取 Agent 部署列表"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM agent_deployments WHERE 1=1"
        params = []
        
        if template_id:
            query += " AND template_id = ?"
            params.append(template_id)
        
        if instance_id:
            query += " AND instance_id = ?"
            params.append(instance_id)
        
        cursor.execute(query, params)
        
        deployments = []
        for row in cursor.fetchall():
            deployment = AgentDeployment(
                id=row[0],
                template_id=row[1],
                instance_id=row[2],
                deployed_by=row[3],
                status=row[4],
                agent_dir=row[5] or "",
                agent_name=row[6] or "",
                error_message=row[7] or "",
                last_sync_at=datetime.fromisoformat(row[8]) if row[8] else None,
                last_used_at=datetime.fromisoformat(row[9]) if row[9] else None,
                total_calls=row[10] or 0,
                deployed_at=datetime.fromisoformat(row[11]) if row[11] else datetime.now()
            )
            deployments.append(deployment)
        
        conn.close()
        return deployments

    # ========== 辅助方法 ==========

    def _slugify(self, text: str) -> str:
        """将文本转换为安全的文件名"""
        import re
        return re.sub(r'[^\w\-]', '-', text.lower())

    def _generate_soul_md(self, template: AgentTemplate, agent_name: str) -> str:
        """生成 SOUL.md 内容"""
        return f"""# {agent_name} - {template.emoji}

{template.identity_prompt}

---

## 团队信息

- 团队: {self.team_id}
- 模板: {template.name} (v{template.version})
- 模型: {template.default_model}
- 技能: {', '.join(template.skills) if template.skills else '无'}
"""

    def _exec_on_instance(self, instance, command: str) -> str:
        """在实例上执行命令"""
        from .instance_manager import get_instance_manager
        result = get_instance_manager().execute_command(instance.id, command)
        if not result.success:
            raise RuntimeError(f"Command failed: {result.stderr}")
        return result.stdout

    def _write_file_on_instance(self, instance, path: str, content: str):
        """在实例上写入文件"""
        import base64
        encoded = base64.b64encode(content.encode('utf-8')).decode()
        # 使用 PowerShell 兼容的方式
        self._exec_on_instance(
            instance,
            f"echo {encoded} | base64 -d > {path} 2>nul || powershell -Command \"[IO.File]::WriteAllText('{path}', [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded}')))\""
        )

    # ========== OpenClaw 工作区辅助 ==========

    def get_default_workspace_path(self) -> str:
        """
        根据 ~/.openclaw/openclaw.json 猜测一个默认工作区路径。

        优先级示例（视实际 openclaw.json 结构而定）：
        - data.workspace / workspace
        - data.projects[0].path
        - 否则回退到当前工作目录
        """
        try:
            config_path = os.path.join(self.config_dir, "openclaw.json")
            if os.path.isfile(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    ws = (
                        data.get("workspace")
                        or (data.get("data") or {}).get("workspace")
                        or (data.get("data") or {}).get("projects_path")
                    )
                    if isinstance(ws, str) and ws.strip():
                        return os.path.expanduser(ws.strip())
                    # 如果有 projects 列表，取第一个
                    projects = (data.get("projects") or []) or (data.get("data") or {}).get("projects") or []
                    if isinstance(projects, list) and projects:
                        first = projects[0]
                        if isinstance(first, dict):
                            p = first.get("path") or first.get("workspace_path")
                            if isinstance(p, str) and p.strip():
                                return os.path.expanduser(p.strip())
        except Exception:
            pass
        # 回退：当前工作目录
        return os.getcwd()

    # ========== Agent 管理接口 ==========

    def register_agent(self, agent: AgentInfo) -> bool:
        """
        注册/更新一个 Agent。

        调用场景：
        - Butlerclaw 扫描某个 OpenClaw 工作空间时，发现可用的 Agent/Workflow
        - 外部工具显式把某个 Agent 注册进来，让协作面板可以管理它
        """
        with self._lock:
            self._agents[agent.id] = agent
        return True

    def get_agents(self) -> List[AgentInfo]:
        """获取当前已注册的所有 Agents"""
        with self._lock:
            return list(self._agents.values())

    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """根据 ID 获取 Agent 详情"""
        with self._lock:
            return self._agents.get(agent_id)

    def remove_agent(self, agent_id: str) -> bool:
        """从管理列表中移除一个 Agent（不负责删除实际代码/配置）"""
        with self._lock:
            existed = agent_id in self._agents
            if existed:
                del self._agents[agent_id]
                self._agent_policies.pop(agent_id, None)
            return existed

    def set_agent_policy(self, policy: AgentUsagePolicy) -> bool:
        """为 Agent 设置/更新使用策略（配额/预算/允许角色）"""
        with self._lock:
            if policy.agent_id not in self._agents:
                return False
            self._agent_policies[policy.agent_id] = policy
            return True

    def get_agent_policy(self, agent_id: str) -> Optional[AgentUsagePolicy]:
        """获取某个 Agent 的使用策略"""
        with self._lock:
            return self._agent_policies.get(agent_id)

    def is_agent_allowed_for_role(self, agent_id: str, role: UserRole) -> bool:
        """
        判断某个角色是否允许使用/管理该 Agent。

        目前是纯静态判断（不统计实时调用次数/预算），
        与成本控制模块联动可以在上层做进一步限制。
        """
        policy = self.get_agent_policy(agent_id)
        if not policy:
            # 没有策略时，默认管理员和成员允许，访客只读/不允许写操作
            return role in (UserRole.ADMIN, UserRole.MEMBER)
        return role in policy.allowed_roles

    def discover_agents(self, workspace_path: Optional[str] = None) -> List[AgentInfo]:
        """
        通过 OpenClaw CLI 自动发现 Agents。

        优先尝试：
            openclaw agents list --format json
        如不支持 --format，则尝试解析普通文本输出（尽量容错，解析失败则返回空列表）。
        """
        workspace_path = workspace_path or self.get_default_workspace_path()
        try:
            # 优先尝试 JSON 格式输出
            try:
                result = subprocess.run(
                    ["openclaw", "agents", "list", "--format", "json"],
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    encoding="utf-8",
                    errors="ignore",
                )
            except Exception:
                # 回退到不带 --format 的调用
                result = subprocess.run(
                    ["openclaw", "agents", "list"],
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    encoding="utf-8",
                    errors="ignore",
                )

            if result.returncode != 0:
                # CLI 调用失败时不抛异常，只返回空列表，避免影响 UI
                return []

            stdout = result.stdout.strip()
            agents: List[AgentInfo] = []

            # 优先按 JSON 解析
            try:
                if stdout.startswith("[") or stdout.startswith("{"):
                    data = json.loads(stdout)
                    items = data if isinstance(data, list) else data.get("agents", [])
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        agent_id = str(item.get("id") or item.get("name") or "")
                        if not agent_id:
                            continue
                        name = str(item.get("name") or agent_id)
                        desc = str(item.get("description") or item.get("desc") or "")
                        tags = item.get("tags") or []
                        if not isinstance(tags, list):
                            tags = []
                        agent = AgentInfo(
                            id=agent_id,
                            name=name,
                            description=desc,
                            workspace_path=workspace_path,
                            config_path=item.get("config_path", ""),
                            tags=[str(t) for t in tags],
                            enabled=bool(item.get("enabled", True)),
                            metadata=item,
                        )
                        self.register_agent(agent)
                        agents.append(agent)
                    return agents
            except Exception:
                # JSON 解析失败则退回到文本解析
                pass

            # 简单解析文本输出（例如表格形式），只做最小支持：
            # 取非空行，跳过第一行表头，按空白分割前两列为 id / name。
            lines = [line.strip() for line in stdout.splitlines() if line.strip()]
            if len(lines) <= 1:
                return []

            body = lines[1:]
            agents = []
            for line in body:
                parts = line.split()
                if not parts:
                    continue
                agent_id = parts[0]
                name = parts[1] if len(parts) > 1 else agent_id
                agent = AgentInfo(
                    id=agent_id,
                    name=name,
                    workspace_path=workspace_path,
                )
                self.register_agent(agent)
                agents.append(agent)

            return agents
        except Exception:
            # 为了稳健性，这里不向外抛异常，只在需要时再增加日志
            return []


@dataclass
class AgentInfo:
    """
    OpenClaw Agent 信息（面向 Butlerclaw 的统一视图）

    这里的 Agent 可以是：
    - OpenClaw 配置中的一个 agent/skill
    - 某个工作流入口（如一个特定的 command / route）
    """
    id: str
    name: str
    description: str = ""
    workspace_path: str = ""
    config_path: str = ""
    owner_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentUsagePolicy:
    """Agent 使用策略 / 配额（与成本控制模块协同）"""
    agent_id: str
    daily_calls_limit: int = 0
    monthly_calls_limit: int = 0
    daily_budget_usd: float = 0.0
    monthly_budget_usd: float = 0.0
    allowed_roles: List[UserRole] = field(default_factory=lambda: [UserRole.ADMIN, UserRole.MEMBER])
    last_reset: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ========== 新增：Agent 模板与权限系统 ==========

class AgentRoleType(Enum):
    """Agent 在团队中的角色类型"""
    DEVELOPER = "developer"           # 开发类 Agent
    PRODUCT = "product"               # 产品类 Agent  
    DESIGN = "design"                 # 设计类 Agent
    DATA = "data"                     # 数据类 Agent
    OPERATIONS = "operations"         # 运维类 Agent
    CUSTOM = "custom"                 # 自定义


@dataclass
class AgentTemplate:
    """
    团队 Agent 模板
    
    这是团队共享的 Agent 定义，包含：
    - 角色身份 (SOUL.md 内容)
    - 系统提示词
    - 绑定的技能
    - 模型配置
    """
    id: str                           # 唯一标识，如 "dev-assistant-v2"
    name: str                         # 显示名称
    emoji: str = "🤖"
    description: str = ""
    
    # 角色定义
    role_type: AgentRoleType = AgentRoleType.CUSTOM
    identity_prompt: str = ""         # 系统提示词/SOUL.md 内容
    tools_prompt: str = ""            # TOOLS.md 内容
    
    # 配置
    default_model: str = "moonshot/kimi-k2.5"
    skills: List[str] = field(default_factory=list)  # 绑定的技能ID列表
    env_vars: Dict[str, str] = field(default_factory=dict)
    
    # 团队设置
    created_by: str = ""              # 创建者用户ID
    team_id: str = ""                 # 所属团队
    is_official: bool = False         # 是否官方模板
    is_shared: bool = True            # 是否团队共享
    
    # 版本控制
    version: str = "1.0.0"
    changelog: List[str] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class MemberAgentAccess:
    """
    成员对 Agent 的访问权限配置
    """
    agent_template_id: str
    user_id: str
    
    # 权限
    can_use: bool = True
    can_configure: bool = False
    can_share: bool = False
    
    # 使用配额（与成本控制联动）
    daily_calls_limit: int = 0        # 0 = 无限制
    monthly_budget_limit: float = 0.0  # 0 = 无限制
    
    # 个性化覆盖
    custom_model: Optional[str] = None
    custom_env_vars: Dict[str, str] = field(default_factory=dict)
    
    assigned_at: datetime = field(default_factory=datetime.now)
    assigned_by: str = ""             # 谁分配的权限


@dataclass
class AgentDeployment:
    """
    Agent 模板在某个 OpenClaw 实例上的部署
    """
    id: str                           # 部署ID
    template_id: str                  # 基于哪个模板
    instance_id: str                  # 部署在哪个实例
    deployed_by: str                  # 谁部署的
    
    # 部署状态
    status: str = "pending"           # pending/deploying/running/error
    agent_dir: str = ""               # 实际路径
    agent_name: str = ""              # 部署后的 Agent 名称
    error_message: str = ""
    
    # 运行时信息
    last_sync_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    total_calls: int = 0
    
    deployed_at: datetime = field(default_factory=datetime.now)


# 便捷函数
def get_team_collaboration_manager(team_id: str = "default") -> TeamCollaborationManager:
    """获取全局团队协作管理器"""
    return TeamCollaborationManager(team_id=team_id)