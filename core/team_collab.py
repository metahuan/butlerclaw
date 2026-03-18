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
    团队协作管理器
    
    管理团队协作功能，提供：
    - 成员权限管理
    - 操作审计日志
    - 共享技能仓库
    - 配置同步
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = config_dir or os.path.expanduser("~/.openclaw")
        self._current_user: Optional[TeamMember] = None
        self._members: Dict[str, TeamMember] = {}
        self._audit_logs: List[AuditLogEntry] = []
        self._shared_skills: Dict[str, SharedSkill] = {}
        self._sync_items: Dict[str, ConfigSyncItem] = {}
        self._lock = threading.Lock()
    
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


# 便捷函数
def get_team_collaboration_manager() -> TeamCollaborationManager:
    """获取全局团队协作管理器"""
    return TeamCollaborationManager()