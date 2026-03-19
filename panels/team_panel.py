# -*- coding: utf-8 -*-
"""
Agent 团队协作面板 - OpenClaw 生态专属管家
"""

import os
import json
import time
import subprocess
import threading
from datetime import datetime
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, asdict, field

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.dialogs import Messagebox
    TTKBOOTSTRAP_AVAILABLE = True
except ImportError:
    import tkinter as tk
    from tkinter import ttk as ttk_module, messagebox
    ttk = ttk_module
    ttk.Canvas = tk.Canvas
    ttk.Toplevel = tk.Toplevel
    ttk.StringVar = tk.StringVar

    class Messagebox:
        @staticmethod
        def show_info(message, title="提示"):
            messagebox.showinfo(title, message)
        @staticmethod
        def askyesno(title, message):
            return messagebox.askyesno(title, message)
        @staticmethod
        def showerror(title, message):
            messagebox.showerror(title, message)

    TTKBOOTSTRAP_AVAILABLE = False

from tkinter.constants import X, Y, BOTH, LEFT, RIGHT, VERTICAL, CENTER, NW, W


@dataclass
class AgentInfo:
    """Agent 信息"""
    id: str
    name: str
    identity_name: str = ""
    identity_emoji: str = "🤖"
    workspace: str = ""
    agent_dir: str = ""
    model: str = ""
    bindings: int = 0
    is_default: bool = False
    routes: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    description: str = ""
    status: str = "unknown"
    owner_id: str = ""
    
    @property
    def display_name(self) -> str:
        return self.identity_name or self.name or self.id
    
    @property
    def display_emoji(self) -> str:
        return self.identity_emoji or "🤖"


@dataclass
class TeamMember:
    """团队成员"""
    id: str
    name: str
    email: str
    role: str = "OPERATOR"


class AgentCard(ttk.Frame):
    """Agent 卡片组件"""
    
    STATUS_COLORS = {
        'online': '#10B981', 'offline': '#9CA3AF',
        'busy': '#F59E0B', 'error': '#EF4444', 'unknown': '#6B7280'
    }
    
    def __init__(self, parent, agent: AgentInfo, is_owner: bool = False,
                 on_action: Callable = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.agent = agent
        self.is_owner = is_owner
        self.on_action = on_action
        self._build_ui()
    
    def _build_ui(self):
        container = ttk.Frame(self, padding=15)
        container.pack(fill=X, expand=True)
        
        # 头部
        header = ttk.Frame(container)
        header.pack(fill=X)
        
        ttk.Label(header, text=self.agent.display_emoji, font=("Microsoft YaHei", 24)).pack(side=LEFT)
        
        name_frame = ttk.Frame(header)
        name_frame.pack(side=LEFT, padx=(10, 0), fill=Y)
        
        name_text = self.agent.display_name
        if self.agent.is_default:
            name_text += " (默认)"
        
        ttk.Label(name_frame, text=name_text, font=("Microsoft YaHei", 12, "bold")).pack(anchor=W)
        ttk.Label(name_frame, text=f"📦 {self.agent.model or '未配置模型'}",
                 foreground="#666", font=("Microsoft YaHei", 9)).pack(anchor=W)
        
        status_color = self.STATUS_COLORS.get(self.agent.status, '#6B7280')
        status_text = {'online': '● 运行中', 'offline': '● 已停止'}.get(self.agent.status, '● 未知')
        ttk.Label(header, text=status_text, foreground=status_color,
                 font=("Microsoft YaHei", 9, "bold")).pack(side=RIGHT)
        
        # 描述
        if self.agent.description:
            ttk.Label(container, text=self.agent.description,
                     foreground="#666", wraplength=400).pack(anchor=W, pady=(10, 0))
        
        # 操作按钮
        actions = ttk.Frame(container)
        actions.pack(fill=X, pady=(15, 0))
        
        if self.agent.status == 'online':
            ttk.Button(actions, text="⏹ 停止", command=lambda: self._on_action('stop'),
                      width=8).pack(side=LEFT, padx=(0, 5))
        else:
            ttk.Button(actions, text="▶ 启动", command=lambda: self._on_action('start'),
                      width=8).pack(side=LEFT, padx=(0, 5))
        
        ttk.Button(actions, text="⚙️ 配置", command=lambda: self._on_action('config'),
                  width=8).pack(side=LEFT, padx=(0, 5))
        ttk.Button(actions, text="📊 日志", command=lambda: self._on_action('logs'),
                  width=8).pack(side=LEFT, padx=(0, 5))
        
        if self.is_owner:
            ttk.Button(actions, text="🗑️ 删除", command=lambda: self._on_action('delete'),
                      width=8).pack(side=RIGHT)
    
    def _on_action(self, action: str):
        if self.on_action:
            self.on_action(action, self.agent)


class TeamPanel(ttk.Frame):
    """Agent 团队协作面板"""
    
    TABS = [
        ("agents", "🤖 我的 Agents"),
        ("market", "🏪 Agent 市场"),
        ("routes", "🔀 路由编排"),
        ("team", "👥 团队协作"),
        ("costs", "💰 成本分析"),
    ]
    
    def __init__(self, parent, app=None, theme_manager=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.theme_manager = theme_manager
        self.agents: List[AgentInfo] = []
        self.team_members: List[TeamMember] = []
        self.current_user_id = "user_001"
        self._load_data()
        self._build_ui()
        self.refreshing = True
        self.refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self.refresh_thread.start()
    
    def _build_ui(self):
        # 标题栏
        header = ttk.Frame(self)
        header.pack(fill=X, pady=(0, 10))
        
        ttk.Label(header, text="🦞 Agent 团队协作",
                 font=("Microsoft YaHei", 16, "bold")).pack(side=LEFT)
        
        btn_frame = ttk.Frame(header)
        btn_frame.pack(side=RIGHT)
        
        ttk.Button(btn_frame, text="➕ 新建 Agent",
                  command=self._show_create_agent_dialog).pack(side=RIGHT, padx=(5, 0))
        ttk.Button(btn_frame, text="🔄 刷新",
                  command=self._refresh_agents).pack(side=RIGHT)
        
        # 标签页
        self.tab_var = ttk.StringVar(value="agents")
        tab_frame = ttk.Frame(self)
        tab_frame.pack(fill=X, pady=10)
        
        for key, label in self.TABS:
            btn = ttk.Radiobutton(tab_frame, text=label, variable=self.tab_var,
                                 value=key, command=self._on_tab_change)
            btn.pack(side=LEFT, padx=(0, 5))
        
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill=BOTH, expand=True)
        
        self._show_agents_tab()
    
    def _on_tab_change(self):
        tab = self.tab_var.get()
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        if tab == "agents":
            self._show_agents_tab()
        elif tab == "market":
            self._show_market_tab()
        elif tab == "routes":
            self._show_routes_tab()
        elif tab == "team":
            self._show_team_tab()
        elif tab == "costs":
            self._show_costs_tab()
    
    def _show_agents_tab(self):
        stats_frame = ttk.Frame(self.content_frame)
        stats_frame.pack(fill=X, pady=(0, 10))
        
        total = len(self.agents)
        online = sum(1 for a in self.agents if a.status == 'online')
        
        ttk.Label(stats_frame, text=f"共 {total} 个 Agent",
                 font=("Microsoft YaHei", 11, "bold")).pack(side=LEFT)
        ttk.Label(stats_frame, text=f"运行中: {online} 个", foreground="#10B981").pack(side=LEFT, padx=(20, 0))
        
        # Agent 列表
        canvas = ttk.Canvas(self.content_frame)
        scrollbar = ttk.Scrollbar(self.content_frame, orient=VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=RIGHT, fill=Y)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        
        self.agents_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=self.agents_frame, anchor=NW, width=600)
        self.agents_frame.bind("<Configure>",
                              lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        self._render_agent_cards()
    
    def _render_agent_cards(self):
        for widget in self.agents_frame.winfo_children():
            widget.destroy()
        
        if not self.agents:
            ttk.Label(self.agents_frame, text="暂无 Agent\n点击右上角「新建 Agent」创建",
                     foreground="#999", justify=CENTER).pack(pady=50)
            return
        
        for agent in self.agents:
            is_owner = agent.owner_id == self.current_user_id or not agent.owner_id
            card = AgentCard(self.agents_frame, agent, is_owner=is_owner,
                           on_action=self._on_agent_action, relief="solid", borderwidth=1)
            card.pack(fill=X, pady=5, padx=5)
    
    def _on_agent_action(self, action: str, agent: AgentInfo):
        if action == 'start':
            agent.status = 'online'
            self._on_tab_change()
        elif action == 'stop':
            agent.status = 'offline'
            self._on_tab_change()
        elif action == 'config':
            self._show_agent_config(agent)
        elif action == 'logs':
            Messagebox.show_info(f"查看 {agent.display_name} 的日志", "日志")
        elif action == 'delete':
            self._delete_agent(agent)
    
    def _show_agent_config(self, agent: AgentInfo):
        dialog = ttk.Toplevel(self)
        dialog.title(f"配置 Agent: {agent.display_name}")
        dialog.geometry("500x400")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        basic_frame = ttk.LabelFrame(dialog, text="基本信息", padding=10)
        basic_frame.pack(fill=X, padx=10, pady=10)
        
        ttk.Label(basic_frame, text="显示名称:").pack(anchor=W)
        name_var = ttk.StringVar(value=agent.identity_name or agent.name)
        ttk.Entry(basic_frame, textvariable=name_var).pack(fill=X, pady=5)
        
        ttk.Label(basic_frame, text="图标 (emoji):").pack(anchor=W)
        emoji_var = ttk.StringVar(value=agent.identity_emoji or "🤖")
        ttk.Entry(basic_frame, textvariable=emoji_var).pack(fill=X, pady=5)
        
        def do_save():
            agent.identity_name = name_var.get()
            agent.identity_emoji = emoji_var.get()
            try:
                subprocess.run([
                    "openclaw", "agents", "set-identity", agent.id,
                    "--name", name_var.get(), "--emoji", emoji_var.get()
                ], capture_output=True, timeout=10)
            except Exception as e:
                print(f"更新失败: {e}")
            self._save_data()
            self._on_tab_change()
            dialog.destroy()
            Messagebox.show_info("配置已保存", "成功")
        
        ttk.Button(dialog, text="保存", command=do_save).pack(pady=20)
    
    def _delete_agent(self, agent: AgentInfo):
        if Messagebox.askyesno("确认删除", f"确定要删除 Agent \"{agent.display_name}\" 吗？"):
            try:
                result = subprocess.run(
                    ["openclaw", "agents", "delete", agent.id, "--yes"],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    self.agents = [a for a in self.agents if a.id != agent.id]
                    self._save_data()
                    self._on_tab_change()
                    Messagebox.show_info(f"Agent {agent.display_name} 已删除", "成功")
                else:
                    Messagebox.showerror("删除失败", result.stderr or "未知错误")
            except Exception as e:
                Messagebox.showerror("删除失败", str(e))
    
    def _show_create_agent_dialog(self):
        dialog = ttk.Toplevel(self)
        dialog.title("新建 Agent")
        dialog.geometry("400x350")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        ttk.Label(dialog, text="Agent ID:").pack(anchor=W, padx=20, pady=(20, 5))
        id_var = ttk.StringVar()
        ttk.Entry(dialog, textvariable=id_var, width=40).pack(padx=20)
        
        ttk.Label(dialog, text="显示名称:").pack(anchor=W, padx=20, pady=(15, 5))
        name_var = ttk.StringVar()
        ttk.Entry(dialog, textvariable=name_var, width=40).pack(padx=20)
        
        ttk.Label(dialog, text="图标 (emoji):").pack(anchor=W, padx=20, pady=(15, 5))
        emoji_var = ttk.StringVar(value="🤖")
        ttk.Entry(dialog, textvariable=emoji_var, width=40).pack(padx=20)
        
        def do_create():
            agent_id = id_var.get().strip()
            if not agent_id:
                Messagebox.showwarning("警告", "请输入 Agent ID")
                return
            try:
                result = subprocess.run(
                    ["openclaw", "agents", "add", agent_id],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    if name_var.get() or emoji_var.get():
                        subprocess.run([
                            "openclaw", "agents", "set-identity", agent_id,
                            "--name", name_var.get() or agent_id,
                            "--emoji", emoji_var.get() or "🤖"
                        ], capture_output=True, timeout=10)
                    self._refresh_agents()
                    dialog.destroy()
                    Messagebox.show_info(f"Agent {agent_id} 创建成功", "成功")
                else:
                    Messagebox.showerror("创建失败", result.stderr or "未知错误")
            except Exception as e:
                Messagebox.showerror("创建失败", str(e))
        
        ttk.Button(dialog, text="创建", command=do_create).pack(pady=20)
    
    def _show_market_tab(self):
        ttk.Label(self.content_frame, text="🏪 Agent 市场",
                 font=("Microsoft YaHei", 12, "bold")).pack(anchor=W, pady=(0, 10))
        
        market_agents = [
            ("代码审查助手", "🔍", "自动审查代码，发现潜在问题", "开发", "1.2k"),
            ("文档生成器", "📝", "根据代码自动生成文档", "开发", "856"),
            ("需求分析师", "📊", "分析需求文档，提取关键信息", "产品", "643"),
        ]
        
        for name, emoji, desc, category, downloads in market_agents:
            card = ttk.Frame(self.content_frame, relief="solid", borderwidth=1, padding=10)
            card.pack(fill=X, pady=5)
            
            header = ttk.Frame(card)
            header.pack(fill=X)
            
            ttk.Label(header, text=f"{emoji} {name}",
                     font=("Microsoft YaHei", 11, "bold")).pack(side=LEFT)
            ttk.Label(header, text=f"⬇ {downloads}", foreground="#666").pack(side=RIGHT)
            
            ttk.Label(card, text=desc, foreground="#666").pack(anchor=W, pady=5)
            
            footer = ttk.Frame(card)
            footer.pack(fill=X)
            
            ttk.Label(footer, text=f"#{category}", foreground="#3B82F6").pack(side=LEFT)
            ttk.Button(footer, text="安装",
                      command=lambda n=name: Messagebox.show_info(f"安装 {n}", "安装")).pack(side=RIGHT)
    
    def _show_routes_tab(self):
        ttk.Label(self.content_frame, text="🔀 路由编排",
                 font=("Microsoft YaHei", 12, "bold")).pack(anchor=W, pady=(0, 10))
        ttk.Label(self.content_frame,
                 text="配置消息如何路由到不同 Agent",
                 foreground="#666").pack(anchor=W, pady=(0, 10))
    
    def _show_team_tab(self):
        ttk.Label(self.content_frame, text="👥 团队协作",
                 font=("Microsoft YaHei", 12, "bold")).pack(anchor=W, pady=(0, 10))
        
        for member in self.team_members:
            row = ttk.Frame(self.content_frame)
            row.pack(fill=X, pady=5)
            ttk.Label(row, text=f"{member.name} ({member.email})").pack(side=LEFT)
            ttk.Label(row, text=member.role, foreground="#3B82F6").pack(side=LEFT, padx=(10, 0))
    
    def _show_costs_tab(self):
        ttk.Label(self.content_frame, text="💰 成本分析",
                 font=("Microsoft YaHei", 12, "bold")).pack(anchor=W, pady=(0, 10))
        ttk.Label(self.content_frame,
                 text="按 Agent 统计成本使用情况",
                 foreground="#666").pack(anchor=W, pady=(0, 10))
    
    def _refresh_agents(self):
        try:
            # Windows 下需 shell=True 才能从 PATH 解析 openclaw
            cmd = "openclaw agents list --json"
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode == 0 and (result.stdout or "").strip():
                data = json.loads(result.stdout)
                self.agents = []
                items = data if isinstance(data, list) else data.get("agents", data.get("items", []))
                for item in items:
                    agent = AgentInfo(
                        id=item.get("id", ""),
                        name=item.get("name", ""),
                        identity_name=item.get("identityName", ""),
                        identity_emoji=item.get("identityEmoji", "🤖"),
                        workspace=item.get("workspace", ""),
                        agent_dir=item.get("agentDir", ""),
                        model=item.get("model", ""),
                        bindings=item.get("bindings", 0),
                        is_default=item.get("isDefault", False),
                        routes=item.get("routes", []),
                        status="online" if item.get("isDefault") else "offline"
                    )
                    self.agents.append(agent)
                self._save_data()
                # 初始化阶段 _build_ui 可能尚未执行，此时还没有 tab_var
                if hasattr(self, "tab_var"):
                    self._on_tab_change()
        except FileNotFoundError:
            # openclaw 未安装或不在 PATH，保留已加载的缓存数据
            pass
        except json.JSONDecodeError as e:
            print(f"刷新 Agents 解析结果失败: {e}")
        except subprocess.TimeoutExpired:
            print("刷新 Agents 超时")
        except Exception as e:
            print(f"刷新 Agents 失败: {e}")
    
    def _refresh_loop(self):
        while self.refreshing:
            time.sleep(30)
    
    def _load_data(self):
        config_path = os.path.expanduser("~/.openclaw/team_data.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for m in data.get('members', []):
                        self.team_members.append(TeamMember(**m))
                    # 从缓存恢复 Agent 列表（与 _save_data 的 asdict 格式一致）
                    for item in data.get('agents', []):
                        try:
                            self.agents.append(AgentInfo(**item))
                        except (TypeError, KeyError):
                            pass
        except Exception as e:
            print(f"加载团队数据失败: {e}")
        
        if not self.team_members:
            self.team_members = [
                TeamMember("user_001", "张三", "zhangsan@example.com", "OWNER"),
                TeamMember("user_002", "李四", "lisi@example.com", "ADMIN"),
            ]
        
        self._refresh_agents()
    
    def _save_data(self):
        config_path = os.path.expanduser("~/.openclaw/team_data.json")
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            data = {
                'members': [asdict(m) for m in self.team_members],
                'agents': [asdict(a) for a in self.agents]
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存团队数据失败: {e}")
    
    def destroy(self):
        self.refreshing = False
        self._save_data()
        super().destroy()
