# -*- coding: utf-8 -*-
"""
团队协作界面 - 成员管理、共享配置、权限设置

功能:
- 成员管理（邀请/权限/角色）
- 共享配置同步
- 操作日志审计
- 团队资源配额
"""

import os
import json
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    from ttkbootstrap.dialogs import Messagebox
    TTKBOOTSTRAP_AVAILABLE = True
except ImportError:
    import tkinter as tk
    from tkinter import ttk as ttk_module, messagebox
    ttk = ttk_module
    ttk.Canvas = tk.Canvas
    ttk.Toplevel = tk.Toplevel
    ttk.StringVar = tk.StringVar
    ttk.BooleanVar = tk.BooleanVar
    ttk.DoubleVar = tk.DoubleVar

    class Messagebox:
        @staticmethod
        def show_info(message, title="提示"):
            messagebox.showinfo(title, message)

        @staticmethod
        def showwarning(title, message):
            messagebox.showwarning(title, message)

        @staticmethod
        def askyesno(title, message):
            return messagebox.askyesno(title, message)

        @staticmethod
        def showerror(title, message):
            messagebox.showerror(title, message)

    TTKBOOTSTRAP_AVAILABLE = False

from tkinter import simpledialog
from tkinter.constants import (
    X, Y, BOTH, LEFT, RIGHT, TOP, BOTTOM,
    W, E, N, S, NW, NE, SW, SE, CENTER,
    VERTICAL, HORIZONTAL
)


class Role(Enum):
    """团队角色"""
    OWNER = ("所有者", "拥有所有权限，可管理团队成员")
    ADMIN = ("管理员", "可管理技能和配置，不能删除团队")
    DEVELOPER = ("开发者", "可使用技能，管理自己的配置")
    VIEWER = ("观察者", "只读访问，不能修改配置")
    
    def __init__(self, label: str, description: str):
        self.label = label
        self.description = description


@dataclass
class TeamMember:
    """团队成员"""
    id: str
    name: str
    email: str
    role: str
    avatar: str = ""
    joined_at: str = ""
    last_active: str = ""
    is_online: bool = False


@dataclass
class AuditLog:
    """审计日志"""
    id: str
    timestamp: str
    user_id: str
    user_name: str
    action: str
    target_type: str
    target_id: str
    target_name: str
    details: str = ""
    ip_address: str = ""


@dataclass
class SharedConfig:
    """共享配置"""
    id: str
    name: str
    type: str  # 'api_keys', 'skills', 'scripts', 'rules'
    content: Dict
    shared_by: str
    shared_at: str
    updated_at: str
    sync_enabled: bool = True
    auto_sync: bool = False


class MemberCard(ttk.Frame):
    """成员卡片组件"""
    
    ROLE_COLORS = {
        'OWNER': '#EF4444',
        'ADMIN': '#F59E0B',
        'DEVELOPER': '#3B82F6',
        'VIEWER': '#10B981'
    }
    
    def __init__(self, parent, member: TeamMember, is_me: bool = False,
                 on_action: Callable = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.member = member
        self.is_me = is_me
        self.on_action = on_action
        
        self._build_ui()
    
    def _build_ui(self):
        container = ttk.Frame(self, padding=10)
        container.pack(fill=X, expand=True)
        
        # 头像和名称
        header = ttk.Frame(container)
        header.pack(fill=X)
        
        avatar_text = self.member.name[0].upper() if self.member.name else "?"
        avatar = ttk.Label(header, text=avatar_text,
                          font=("Microsoft YaHei", 16, "bold"),
                          background="#3B82F6", foreground="white",
                          width=2, anchor=CENTER)
        avatar.pack(side=LEFT)
        
        name_frame = ttk.Frame(header)
        name_frame.pack(side=LEFT, padx=(10, 0))
        
        name_text = self.member.name
        if self.is_me:
            name_text += " (我)"
        
        ttk.Label(name_frame, text=name_text,
                 font=("Microsoft YaHei", 11, "bold")).pack(anchor=W)
        
        ttk.Label(name_frame, text=self.member.email,
                 foreground="#666", font=("Microsoft YaHei", 9)).pack(anchor=W)
        
        # 在线状态
        if self.member.is_online:
            ttk.Label(header, text="● 在线",
                     foreground="#10B981", font=("Microsoft YaHei", 9)).pack(side=RIGHT)
        else:
            last_active = self._format_last_active(self.member.last_active)
            ttk.Label(header, text=f"离线 {last_active}",
                     foreground="#999", font=("Microsoft YaHei", 9)).pack(side=RIGHT)
        
        # 角色标签
        role_color = self.ROLE_COLORS.get(self.member.role, '#666')
        role_label = Role[self.member.role].label if self.member.role in Role.__members__ else self.member.role
        
        role_tag = ttk.Label(container, text=role_label,
                            foreground=role_color,
                            font=("Microsoft YaHei", 9, "bold"))
        role_tag.pack(anchor=W, pady=(5, 0))
        
        # 操作按钮
        if not self.is_me and self.on_action:
            actions = ttk.Frame(container)
            actions.pack(fill=X, pady=(10, 0))
            
            ttk.Button(actions, text="更改角色",
                      command=lambda: self.on_action('change_role', self.member),
                      bootstyle="info-outline" if TTKBOOTSTRAP_AVAILABLE else None,
                      width=10).pack(side=LEFT, padx=(0, 5))
            
            ttk.Button(actions, text="移除",
                      command=lambda: self.on_action('remove', self.member),
                      bootstyle="danger-outline" if TTKBOOTSTRAP_AVAILABLE else None,
                      width=8).pack(side=LEFT)
    
    def _format_last_active(self, last_active: str) -> str:
        """格式化最后活跃时间"""
        if not last_active:
            return "很久"
        
        try:
            last = datetime.fromisoformat(last_active)
            now = datetime.now()
            delta = now - last
            
            if delta.days > 0:
                return f"{delta.days}天前"
            elif delta.seconds > 3600:
                return f"{delta.seconds // 3600}小时前"
            elif delta.seconds > 60:
                return f"{delta.seconds // 60}分钟前"
            else:
                return "刚刚"
        except:
            return "很久"


class TeamPanel(ttk.Frame):
    """团队协作面板"""
    
    TABS = [
        ("members", "👥 成员管理"),
        ("shared", "📤 共享配置"),
        ("logs", "📋 操作日志"),
        ("permissions", "🔐 权限设置"),
    ]
    
    def __init__(self, parent, app=None, theme_manager=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.theme_manager = theme_manager
        
        # 数据
        self.members: List[TeamMember] = []
        self.logs: List[AuditLog] = []
        self.shared_configs: List[SharedConfig] = []
        self.current_user_id = "user_001"  # 模拟当前用户
        
        # 加载数据
        self._load_data()
        
        self._build_ui()
    
    def _build_ui(self):
        """构建界面"""
        # 标题栏
        header = ttk.Frame(self)
        header.pack(fill=X, pady=(0, 10))
        
        ttk.Label(header, text="👥 团队协作",
                 font=("Microsoft YaHei", 16, "bold")).pack(side=LEFT)
        
        ttk.Button(header, text="➕ 邀请成员",
                  command=self._show_invite_dialog,
                  bootstyle="primary" if TTKBOOTSTRAP_AVAILABLE else None).pack(side=RIGHT)
        
        # 标签页
        self.tab_var = ttk.StringVar(value="members")
        tab_frame = ttk.Frame(self)
        tab_frame.pack(fill=X, pady=10)
        
        for key, label in self.TABS:
            btn = ttk.Radiobutton(tab_frame, text=label, variable=self.tab_var,
                                 value=key, command=self._on_tab_change,
                                 bootstyle="toolbutton" if TTKBOOTSTRAP_AVAILABLE else None)
            btn.pack(side=LEFT, padx=(0, 5))
        
        # 内容区域
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill=BOTH, expand=True)
        
        # 初始化显示成员管理
        self._show_members_tab()
    
    def _on_tab_change(self):
        """标签页切换"""
        tab = self.tab_var.get()
        
        # 清除当前内容
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        if tab == "members":
            self._show_members_tab()
        elif tab == "shared":
            self._show_shared_tab()
        elif tab == "logs":
            self._show_logs_tab()
        elif tab == "permissions":
            self._show_permissions_tab()
    
    def _show_members_tab(self):
        """显示成员管理标签页"""
        # 成员列表
        list_frame = ttk.Frame(self.content_frame)
        list_frame.pack(fill=BOTH, expand=True)
        
        # 统计信息
        stats_frame = ttk.Frame(list_frame)
        stats_frame.pack(fill=X, pady=(0, 10))
        
        total = len(self.members)
        online = sum(1 for m in self.members if m.is_online)
        
        ttk.Label(stats_frame, text=f"团队成员 ({total}人)",
                 font=("Microsoft YaHei", 11, "bold")).pack(side=LEFT)
        
        ttk.Label(stats_frame, text=f"在线: {online}人",
                 foreground="#10B981").pack(side=LEFT, padx=(20, 0))
        
        # 成员卡片列表
        canvas = ttk.Canvas(list_frame)
        scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=RIGHT, fill=Y)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        
        members_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=members_frame, anchor=NW, width=500)
        
        members_frame.bind("<Configure>",
                          lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        for member in self.members:
            card = MemberCard(
                members_frame,
                member,
                is_me=(member.id == self.current_user_id),
                on_action=self._on_member_action,
                relief="solid",
                borderwidth=1
            )
            card.pack(fill=X, pady=5, padx=5)
    
    def _show_shared_tab(self):
        """显示共享配置标签页"""
        # 共享配置列表
        for config in self.shared_configs:
            frame = ttk.LabelFrame(self.content_frame, text=config.name, padding=10)
            frame.pack(fill=X, pady=5)
            
            # 类型图标和名称
            type_icons = {
                'api_keys': '🔑',
                'skills': '🛠️',
                'scripts': '📜',
                'rules': '📋'
            }
            icon = type_icons.get(config.type, '📦')
            
            header = ttk.Frame(frame)
            header.pack(fill=X)
            
            ttk.Label(header, text=f"{icon} {config.name}",
                     font=("Microsoft YaHei", 11, "bold")).pack(side=LEFT)
            
            # 同步状态
            if config.sync_enabled:
                status_text = "✓ 同步开启"
                status_color = "#10B981"
            else:
                status_text = "✕ 同步关闭"
                status_color = "#999"
            
            ttk.Label(header, text=status_text,
                     foreground=status_color).pack(side=RIGHT)
            
            # 详情
            ttk.Label(frame, text=f"共享者: {config.shared_by}",
                     foreground="#666").pack(anchor=W)
            
            ttk.Label(frame, text=f"更新时间: {config.updated_at[:10]}",
                     foreground="#666").pack(anchor=W)
            
            # 内容摘要
            if config.type == 'api_keys':
                models = config.content.get('models', [])
                ttk.Label(frame, text=f"包含模型: {', '.join(models)}",
                         foreground="#666").pack(anchor=W, pady=(5, 0))
            
            # 操作按钮
            actions = ttk.Frame(frame)
            actions.pack(fill=X, pady=(10, 0))
            
            sync_var = ttk.BooleanVar(value=config.sync_enabled)
            ttk.Checkbutton(actions, text="启用同步",
                           variable=sync_var,
                           command=lambda c=config, v=sync_var: self._toggle_sync(c, v)).pack(side=LEFT)
            
            ttk.Button(actions, text="立即同步",
                      command=lambda c=config: self._sync_config(c),
                      bootstyle="primary-outline" if TTKBOOTSTRAP_AVAILABLE else None).pack(side=RIGHT)
        
        # 添加共享配置按钮
        ttk.Button(self.content_frame, text="➕ 添加共享配置",
                  command=self._show_add_shared_dialog,
                  bootstyle="primary" if TTKBOOTSTRAP_AVAILABLE else None).pack(pady=10)
    
    def _show_logs_tab(self):
        """显示操作日志标签页"""
        # 筛选栏
        filter_frame = ttk.Frame(self.content_frame)
        filter_frame.pack(fill=X, pady=(0, 10))
        
        ttk.Label(filter_frame, text="筛选:").pack(side=LEFT)
        
        self.log_filter_var = ttk.StringVar(value="all")
        ttk.Combobox(filter_frame, textvariable=self.log_filter_var,
                    values=["全部", "安装", "卸载", "配置更改", "成员操作"],
                    state="readonly", width=12).pack(side=LEFT, padx=5)
        
        ttk.Button(filter_frame, text="刷新",
                  command=self._refresh_logs).pack(side=LEFT, padx=5)
        
        # 日志表格
        headers = ["时间", "用户", "操作", "对象"]
        header_frame = ttk.Frame(self.content_frame)
        header_frame.pack(fill=X)
        
        for i, header_text in enumerate(headers):
            width = 15 if i == 0 else 12 if i == 1 else 15
            ttk.Label(header_frame, text=header_text,
                     font=("Microsoft YaHei", 9, "bold"),
                     width=width).pack(side=LEFT, padx=5)
        
        # 日志列表
        canvas = ttk.Canvas(self.content_frame)
        scrollbar = ttk.Scrollbar(self.content_frame, orient=VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=RIGHT, fill=Y)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        
        logs_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=logs_frame, anchor=NW, width=600)
        
        logs_frame.bind("<Configure>",
                       lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        for log in self.logs[:50]:  # 只显示最近50条
            row = ttk.Frame(logs_frame)
            row.pack(fill=X, pady=2)
            
            ttk.Label(row, text=log.timestamp[11:16], width=15).pack(side=LEFT, padx=5)
            ttk.Label(row, text=log.user_name, width=12).pack(side=LEFT, padx=5)
            ttk.Label(row, text=log.action, width=15).pack(side=LEFT, padx=5)
            ttk.Label(row, text=log.target_name, width=20).pack(side=LEFT, padx=5)
    
    def _show_permissions_tab(self):
        """显示权限设置标签页"""
        # 权限说明
        ttk.Label(self.content_frame, text="角色权限说明",
                 font=("Microsoft YaHei", 12, "bold")).pack(anchor=W, pady=(0, 10))
        
        for role in Role:
            frame = ttk.LabelFrame(self.content_frame, text=role.label, padding=10)
            frame.pack(fill=X, pady=5)
            
            ttk.Label(frame, text=role.description,
                     foreground="#666").pack(anchor=W)
            
            # 权限列表
            permissions = self._get_role_permissions(role)
            perms_text = " • ".join(permissions)
            ttk.Label(frame, text=f"权限: {perms_text}",
                     foreground="#333", wraplength=500).pack(anchor=W, pady=(5, 0))
        
        # 团队设置
        ttk.Separator(self.content_frame).pack(fill=X, pady=20)
        
        ttk.Label(self.content_frame, text="团队设置",
                 font=("Microsoft YaHei", 12, "bold")).pack(anchor=W, pady=(0, 10))
        
        settings_frame = ttk.Frame(self.content_frame)
        settings_frame.pack(fill=X)
        
        # 邀请链接
        ttk.Label(settings_frame, text="邀请链接:").pack(anchor=W)
        
        invite_frame = ttk.Frame(settings_frame)
        invite_frame.pack(fill=X, pady=5)
        
        self.invite_link_var = ttk.StringVar(value="https://butlerclaw.io/invite/abc123")
        ttk.Entry(invite_frame, textvariable=self.invite_link_var,
                 state="readonly").pack(side=LEFT, fill=X, expand=True)
        
        ttk.Button(invite_frame, text="复制",
                  command=self._copy_invite_link,
                  bootstyle="secondary" if TTKBOOTSTRAP_AVAILABLE else None).pack(side=LEFT, padx=(5, 0))
        
        ttk.Button(invite_frame, text="重新生成",
                  command=self._regenerate_invite_link,
                  bootstyle="warning" if TTKBOOTSTRAP_AVAILABLE else None).pack(side=LEFT, padx=(5, 0))
    
    def _get_role_permissions(self, role: Role) -> List[str]:
        """获取角色权限列表"""
        permissions = {
            Role.OWNER: ["管理团队成员", "管理团队设置", "管理所有配置", "查看所有日志", "删除团队"],
            Role.ADMIN: ["邀请成员", "管理技能", "管理共享配置", "查看日志"],
            Role.DEVELOPER: ["使用技能", "管理个人配置", "查看共享配置"],
            Role.VIEWER: ["查看配置", "查看日志"]
        }
        return permissions.get(role, [])
    
    def _on_member_action(self, action: str, member: TeamMember):
        """处理成员操作"""
        if action == 'change_role':
            self._show_change_role_dialog(member)
        elif action == 'remove':
            self._remove_member(member)
    
    def _show_change_role_dialog(self, member: TeamMember):
        """显示更改角色对话框"""
        dialog = ttk.Toplevel(self)
        dialog.title(f"更改 {member.name} 的角色")
        dialog.geometry("300x200")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        ttk.Label(dialog, text="选择新角色:").pack(pady=10)
        
        role_var = ttk.StringVar(value=member.role)
        for role in Role:
            ttk.Radiobutton(dialog, text=f"{role.label} - {role.description}",
                           variable=role_var, value=role.name).pack(anchor=W, padx=20)
        
        def do_change():
            member.role = role_var.get()
            manager = getattr(self.app, "team_manager", None) if self.app else None
            core_update_ok = True
            if manager:
                try:
                    # UI 角色映射到 core 角色
                    role_name = role_var.get()
                    core_role_name = "MEMBER"
                    if role_name == "ADMIN":
                        core_role_name = "ADMIN"
                    elif role_name == "VIEWER":
                        core_role_name = "GUEST"

                    from core.team_collab import UserRole as CoreUserRole, AuditAction as CoreAuditAction
                    ok = manager.update_team_member_role(
                        member.id,
                        getattr(CoreUserRole, core_role_name),
                    )
                    if ok:
                        manager.log_action(
                            action=CoreAuditAction.TEAM_MEMBER_UPDATE,
                            target_type="member",
                            target_id=member.id,
                            details={"new_role": core_role_name},
                        )
                    else:
                        core_update_ok = False
                except Exception as e:
                    core_update_ok = False
                    print(f"写入核心角色更新失败，已仅保存本地角色: {e}")

            if manager and not core_update_ok:
                # 明确提示失败原因；保留 UI 本地角色回退，避免用户误以为已经生效
                Messagebox.showwarning(
                    "角色更新未同步",
                    f"无法将 {member.name} 的角色同步到核心团队管理。\n"
                    "可能原因：当前账号权限不足，或该成员不存在于核心团队。\n"
                    "本次仅更新了当前界面/本地数据。"
                )
            self._save_data()
            self._add_log(f"更改 {member.name} 的角色为 {Role[member.role].label}")
            self._on_tab_change()
            dialog.destroy()
        
        ttk.Button(dialog, text="确认", command=do_change,
                  bootstyle="primary" if TTKBOOTSTRAP_AVAILABLE else None).pack(pady=20)
    
    def _remove_member(self, member: TeamMember):
        """移除成员"""
        if Messagebox.askyesno("确认", f"确定要移除 {member.name} 吗?"):
            manager = getattr(self.app, "team_manager", None) if self.app else None
            if manager:
                try:
                    manager.remove_team_member(member.id)
                except Exception:
                    pass
            self.members = [m for m in self.members if m.id != member.id]
            self._save_data()
            self._add_log(f"移除成员 {member.name}")
            self._on_tab_change()
    
    def _show_invite_dialog(self):
        """显示邀请成员对话框"""
        dialog = ttk.Toplevel(self)
        dialog.title("邀请成员")
        dialog.geometry("400x300")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        ttk.Label(dialog, text="邮箱地址:").pack(anchor=W, padx=20, pady=(20, 5))
        email_var = ttk.StringVar()
        ttk.Entry(dialog, textvariable=email_var, width=40).pack(padx=20)
        
        ttk.Label(dialog, text="角色:").pack(anchor=W, padx=20, pady=(15, 5))
        
        role_var = ttk.StringVar(value="DEVELOPER")
        for role in [Role.ADMIN, Role.DEVELOPER, Role.VIEWER]:
            ttk.Radiobutton(dialog, text=f"{role.label} - {role.description}",
                           variable=role_var, value=role.name).pack(anchor=W, padx=20)
        
        def do_invite():
            email = email_var.get().strip()
            if not email:
                Messagebox.showwarning("警告", "请输入邮箱地址")
                return
            
            # 创建新成员
            new_member = TeamMember(
                id=f"user_{int(time.time())}",
                name=email.split('@')[0],
                email=email,
                role=role_var.get(),
                joined_at=datetime.now().isoformat()
            )

            manager = getattr(self.app, "team_manager", None) if self.app else None
            if manager:
                try:
                    # 角色映射到 core 角色（admin/member/guest）
                    role_name = role_var.get()
                    core_role_name = "MEMBER"
                    if role_name == "ADMIN":
                        core_role_name = "ADMIN"
                    elif role_name == "VIEWER":
                        core_role_name = "GUEST"

                    from core.team_collab import TeamMember as CoreTeamMember, UserRole as CoreUserRole
                    core_member = CoreTeamMember(
                        id=new_member.id,
                        username=new_member.name,
                        email=new_member.email,
                        role=getattr(CoreUserRole, core_role_name),
                    )
                    manager.add_team_member(core_member)
                except Exception as e:
                    print(f"写入核心团队管理失败，已仅保存本地成员: {e}")

            self.members.append(new_member)
            self._save_data()
            self._add_log(f"邀请成员 {email} 加入团队")
            
            Messagebox.show_info("邀请已发送", f"已向 {email} 发送邀请邮件")
            self._on_tab_change()
            dialog.destroy()
        
        ttk.Button(dialog, text="发送邀请", command=do_invite,
                  bootstyle="primary" if TTKBOOTSTRAP_AVAILABLE else None).pack(pady=20)
    
    def _toggle_sync(self, config: SharedConfig, var):
        """切换同步状态"""
        config.sync_enabled = var.get()
        self._save_data()
    
    def _sync_config(self, config: SharedConfig):
        """同步配置"""
        config.updated_at = datetime.now().isoformat()
        self._save_data()
        Messagebox.show_info("同步完成", f"{config.name} 已同步")
    
    def _show_add_shared_dialog(self):
        """显示添加共享配置对话框"""
        dialog = ttk.Toplevel(self)
        dialog.title("添加共享配置")
        dialog.geometry("400x300")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        ttk.Label(dialog, text="配置名称:").pack(anchor=W, padx=20, pady=(20, 5))
        name_var = ttk.StringVar()
        ttk.Entry(dialog, textvariable=name_var, width=40).pack(padx=20)
        
        ttk.Label(dialog, text="配置类型:").pack(anchor=W, padx=20, pady=(15, 5))
        type_var = ttk.StringVar(value="api_keys")
        ttk.Combobox(dialog, textvariable=type_var,
                    values=[("api_keys", "API Keys"), ("skills", "技能"), ("scripts", "脚本"), ("rules", "规则")],
                    state="readonly", width=37).pack(padx=20)
        
        def do_add():
            name = name_var.get().strip()
            if not name:
                Messagebox.showwarning("警告", "请输入配置名称")
                return
            
            new_config = SharedConfig(
                id=f"config_{int(time.time())}",
                name=name,
                type=type_var.get(),
                content={},
                shared_by="我",
                shared_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            
            self.shared_configs.append(new_config)
            self._save_data()
            self._add_log(f"添加共享配置 {name}")
            self._on_tab_change()
            dialog.destroy()
        
        ttk.Button(dialog, text="添加", command=do_add,
                  bootstyle="primary" if TTKBOOTSTRAP_AVAILABLE else None).pack(pady=20)
    
    def _refresh_logs(self):
        """刷新日志"""
        self._on_tab_change()
    
    def _copy_invite_link(self):
        """复制邀请链接"""
        try:
            import pyperclip
            pyperclip.copy(self.invite_link_var.get())
            Messagebox.show_info("已复制", "邀请链接已复制到剪贴板")
        except Exception:
            # 回退到 Tk 剪贴板，避免因缺少 pyperclip 导致功能不可用
            self.clipboard_clear()
            self.clipboard_append(self.invite_link_var.get())
            self.update_idletasks()
            Messagebox.show_info("已复制", "邀请链接已复制到剪贴板")
    
    def _regenerate_invite_link(self):
        """重新生成邀请链接"""
        import random, string
        new_code = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        self.invite_link_var.set(f"https://butlerclaw.io/invite/{new_code}")
        Messagebox.show_info("已生成", "新的邀请链接已生成")
    
    def _add_log(self, action: str, target: str = ""):
        """添加日志"""
        log = AuditLog(
            id=f"log_{int(time.time())}",
            timestamp=datetime.now().isoformat(),
            user_id=self.current_user_id,
            user_name="我",
            action=action,
            target_type="",
            target_id="",
            target_name=target
        )
        self.logs.insert(0, log)
        self._save_data()
    
    def _load_data(self):
        """加载数据"""
        # 优先使用 core.team_manager 真实数据
        manager = getattr(self.app, "team_manager", None) if self.app else None
        if manager:
            try:
                role_map = {
                    "admin": "ADMIN",
                    "member": "DEVELOPER",
                    "guest": "VIEWER",
                }

                current = manager.get_current_user()
                if current:
                    self.current_user_id = current.id

                self.members = []
                for m in manager.get_team_members():
                    role_value = getattr(getattr(m, "role", None), "value", "member")
                    self.members.append(
                        TeamMember(
                            id=m.id,
                            name=getattr(m, "username", m.id),
                            email=getattr(m, "email", ""),
                            role=role_map.get(role_value, "DEVELOPER"),
                            joined_at=(
                                getattr(m, "created_at", datetime.now()).isoformat()
                                if getattr(m, "created_at", None) else datetime.now().isoformat()
                            ),
                            last_active=(
                                getattr(m, "last_active", datetime.now()).isoformat()
                                if getattr(m, "last_active", None) else ""
                            ),
                            is_online=bool(getattr(m, "last_active", None)),
                        )
                    )

                self.logs = []
                for lg in manager.get_audit_logs(limit=100):
                    ts = getattr(lg, "timestamp", datetime.now())
                    action = getattr(getattr(lg, "action", None), "value", "action")
                    self.logs.append(
                        AuditLog(
                            id=getattr(lg, "id", f"log_{int(time.time())}"),
                            timestamp=ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                            user_id=getattr(lg, "user_id", ""),
                            user_name=getattr(lg, "username", ""),
                            action=action,
                            target_type=getattr(lg, "target_type", ""),
                            target_id=getattr(lg, "target_id", ""),
                            target_name=getattr(lg, "target_id", ""),
                            details=str(getattr(lg, "details", "")),
                        )
                    )

                # 共享配置当前在 core 中不完整，暂时保留本地或示例
                if not self.shared_configs:
                    self.shared_configs = []
                return
            except Exception as e:
                print(f"从核心模块加载团队数据失败，回退本地数据: {e}")

        config_path = os.path.expanduser("~/.openclaw/team_data.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    for m in data.get('members', []):
                        self.members.append(TeamMember(**m))
                    
                    for l in data.get('logs', []):
                        self.logs.append(AuditLog(**l))
                    
                    for c in data.get('shared_configs', []):
                        self.shared_configs.append(SharedConfig(**c))
        except Exception as e:
            print(f"加载团队数据失败: {e}")
        
        # 如果没有数据，生成示例数据
        if not self.members:
            self._generate_sample_data()
    
    def _generate_sample_data(self):
        """生成示例数据"""
        self.members = [
            TeamMember("user_001", "张三", "zhangsan@example.com", "OWNER", is_online=True,
                      joined_at="2024-01-01T00:00:00", last_active=datetime.now().isoformat()),
            TeamMember("user_002", "李四", "lisi@example.com", "ADMIN", is_online=True,
                      joined_at="2024-01-15T00:00:00", last_active=datetime.now().isoformat()),
            TeamMember("user_003", "王五", "wangwu@example.com", "DEVELOPER", is_online=False,
                      joined_at="2024-02-01T00:00:00", last_active=(datetime.now() - timedelta(hours=2)).isoformat()),
            TeamMember("user_004", "赵六", "zhaoliu@example.com", "VIEWER", is_online=False,
                      joined_at="2024-03-01T00:00:00", last_active=(datetime.now() - timedelta(days=1)).isoformat()),
        ]
        
        self.shared_configs = [
            SharedConfig("config_001", "团队API Key池", "api_keys",
                        {"models": ["GPT-4o", "Claude 3.5", "DeepSeek"]},
                        "张三", "2024-01-01T00:00:00", "2024-03-15T10:30:00",
                        sync_enabled=True, auto_sync=True),
            SharedConfig("config_002", "常用技能包", "skills",
                        {"skills": ["weather", "github", "discord"]},
                        "李四", "2024-02-01T00:00:00", "2024-03-14T15:20:00",
                        sync_enabled=True, auto_sync=False),
        ]
        
        self.logs = [
            AuditLog("log_001", datetime.now().isoformat(), "user_002", "李四", "安装技能", "skill", "weather", "天气技能"),
            AuditLog("log_002", (datetime.now() - timedelta(hours=1)).isoformat(), "user_003", "王五", "更新配置", "config", "models", "模型配置"),
            AuditLog("log_003", (datetime.now() - timedelta(days=1)).isoformat(), "user_001", "张三", "邀请成员", "user", "user_004", "赵六"),
        ]
    
    def _save_data(self):
        """保存数据"""
        config_path = os.path.expanduser("~/.openclaw/team_data.json")
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            data = {
                'members': [asdict(m) for m in self.members],
                'logs': [asdict(l) for l in self.logs[:100]],  # 只保留最近100条
                'shared_configs': [asdict(c) for c in self.shared_configs]
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存团队数据失败: {e}")
    
    def on_show(self):
        """面板显示时调用"""
        pass
    
    def destroy(self):
        """销毁面板"""
        self._save_data()
        super().destroy()
