#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ButlerClaw 管家 - 主程序

一站式管理 OpenClaw：
- 安装管理：复用现有安装向导（Windows/macOS/Linux）
- 技能管理：查看已安装技能，调用 CLI 安装/卸载
- 版本管理：检查当前/最新版本，一键更新
- 诊断工具：基础环境与配置诊断，导出报告
"""

import os
import sys
import json
import threading
import subprocess
import shutil
import re
import webbrowser
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from skills_manager import SkillManager


# 根据平台选择安装器模块
if sys.platform == "win32":
    try:
        from openclaw_installer_v2 import OpenClawInstaller
    except ImportError:
        OpenClawInstaller = None
elif sys.platform == "darwin":
    try:
        from openclaw_installer_macos import OpenClawInstaller
    except ImportError:
        OpenClawInstaller = None
else:
    try:
        from openclaw_installer_linux import OpenClawInstaller
    except ImportError:
        OpenClawInstaller = None


CONFIG_DIR = os.path.expanduser("~/.openclaw")
CONFIG_PATH = os.path.join(CONFIG_DIR, "openclaw.json")
# 程序自身可清理的缓存：日志目录、助手缓存目录
LOGS_DIR = os.path.join(CONFIG_DIR, "logs")
ASSISTANT_CACHE_DIR = os.path.join(CONFIG_DIR, "assistant-cache")

# 技能分类（用于技能管理筛选）
SKILL_CATEGORIES = {
    "all": "全部",
    "tool": "工具",
    "dev": "开发",
    "productivity": "效率",
    "media": "媒体",
    "other": "其他",
}

# 导入新的技能管理模块
try:
    from skills_panel_new import SkillsPanelNew
except ImportError:
    SkillsPanelNew = None
try:
    from panels.instances_panel import InstancesPanel
except ImportError:
    InstancesPanel = None
try:
    from panels.cost_panel import CostPanel
except ImportError:
    CostPanel = None
try:
    from panels.team_panel import TeamPanel
except ImportError:
    TeamPanel = None
try:
    import hub_auth
except ImportError:
    hub_auth = None

# 导入核心功能模块
try:
    from core.instance_manager import InstanceManager, InstanceInfo, InstanceStatus, InstanceType
    # v2 core.cost_tracker 仅暴露 CostTracker/CostBudget/CostAlertLevel/ModelPricing。
    # 这里保持最小依赖，避免因历史命名变更导致主程序整体降级。
    from core.cost_tracker import CostTracker
    from core.team_collab import TeamCollaborationManager, UserRole, TeamMember, AuditAction
    CORE_MODULES_AVAILABLE = True
except ImportError as e:
    CORE_MODULES_AVAILABLE = False
    InstanceManager = None
    CostTracker = None
    TeamCollaborationManager = None
    print(f"[警告] 核心模块导入失败: {e}")


class BasePanel(ttk.Frame):
    """各功能模块面板基类"""

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app

    def on_show(self):
        """面板被选中时调用，子类可重写"""
        pass


class InstallPanel(BasePanel):
    """安装管理：运行安装向导、仅配置模型（检测已配置则提供更新/更换）"""

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, app, **kwargs)
        ttk.Label(self, text="安装管理", font=("", 16, "bold")).pack(pady=(20, 10))
        ttk.Label(
            self,
            text="检测并安装 Node.js、OpenClaw CLI，完成初始模型与 API Key 配置。",
            wraplength=520,
        ).pack(pady=5)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=15)
        self.btn = ttk.Button(btn_frame, text="运行安装向导", command=self._run_wizard)
        self.btn.pack(side=tk.LEFT, padx=(0, 10))
        self.config_btn = ttk.Button(btn_frame, text="仅配置模型", command=self._run_config_only)
        self.config_btn.pack(side=tk.LEFT)
        self.channels_btn = ttk.Button(
            btn_frame,
            text="通道 (Channels) 配置",
            command=self._run_channels_config,
        )
        self.channels_btn.pack(side=tk.LEFT, padx=(10, 0))
        if not OpenClawInstaller:
            self.btn.config(state="disabled")
            self.config_btn.config(state="disabled")
            self.channels_btn.config(state="disabled")
            ttk.Label(
                self,
                text="未找到对应平台的安装器模块",
                foreground="gray",
            ).pack(pady=5)

        ttk.Label(
            self,
            text="提示：若已安装 OpenClaw，向导会自动检测并仅在需要时更新或配置。「仅配置模型」会检测当前是否已配置：已配置可更新/更换 API Key，未配置则进行配置。",
            wraplength=520,
            foreground="gray",
        ).pack(pady=8)

    def _is_model_configured(self):
        """检测是否已配置模型（支持环境变量和配置文件）"""
        # 1. 检查环境变量
        env_prefix = "OPENCLAW_API_KEY"
        for key in os.environ:
            if key.startswith(env_prefix):
                if os.environ[key].strip():
                    return True
        
        # 2. 检查配置文件
        if not os.path.isfile(CONFIG_PATH):
            return False
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            providers = (data.get("models") or {}).get("providers") or {}
            for prov, cfg in providers.items():
                if isinstance(cfg, dict) and (cfg.get("apiKey") or "").strip():
                    return True
            return False
        except Exception:
            return False

    def _run_config_only(self):
        """仅配置模型：检测当前是否已配置，已配置则提示可更新/更换，未配置则直接打开配置；然后打开配置窗口。"""
        if not OpenClawInstaller:
            messagebox.showerror("错误", "当前平台暂无安装向导")
            return
        configured = self._is_model_configured()
        if configured:
            messagebox.showinfo(
                "仅配置模型",
                "当前已配置模型。将打开配置窗口，您可更新或更换 API Key、切换模型。",
            )
        else:
            messagebox.showinfo(
                "仅配置模型",
                "尚未配置模型。将打开配置窗口，请选择模型并填写 API Key。",
            )
        win = tk.Toplevel(self.winfo_toplevel())
        win.title("OpenClaw 安装向导 - 配置模型")
        # 传入助手主窗口作为配置对话框的父窗口，避免关闭时 destroy 导致主界面卡死
        OpenClawInstaller(win, config_only=True, dialog_parent=self.winfo_toplevel())
        self.app._install_window = win

    def _run_channels_config(self):
        """
        通道 (Channels) 配置：
        复用 OpenClawInstaller 中的 Channels 配置对话框，
        打开一个独立窗口，直接进入通道配置界面。
        """
        if not OpenClawInstaller:
            messagebox.showerror("错误", "当前平台暂无安装向导，无法配置通道。")
            return

        # 直接基于当前主窗口弹出 Channels 配置对话框，避免再次创建完整安装向导 UI
        try:
            from openclaw_installer_v2 import ChannelsConfigDialog  # type: ignore
        except Exception as e:
            messagebox.showerror("错误", f"无法导入通道配置对话框：\n{e}")
            return

        parent = self.winfo_toplevel()

        class _DummyInstaller:
            """为 ChannelsConfigDialog 提供最小 installer 接口的占位对象。"""

            def __init__(self):
                # 目前 ChannelsConfigDialog 只用到 installer 来兼容接口，这里预留扩展点
                self.root = parent

        try:
            ChannelsConfigDialog(parent, _DummyInstaller())
        except Exception as e:
            messagebox.showerror("错误", f"无法打开通道配置对话框：\n{e}")

    def _run_wizard(self):
        if not OpenClawInstaller:
            messagebox.showerror("错误", "当前平台暂无安装向导")
            return
        win = tk.Toplevel(self.winfo_toplevel())
        win.title("OpenClaw 安装向导")
        OpenClawInstaller(win)
        self.app._install_window = win


class SkillCard(ttk.Frame):
    """技能卡片：用于列表显示，支持点击选中"""

    def __init__(self, parent, skill_info, on_select=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.skill = skill_info
        self.on_select = on_select
        self.configure(relief="solid", borderwidth=1, padding=6)
        icon = skill_info.get("icon", "📦")
        ttk.Label(self, text=icon, font=("", 18)).pack(side=tk.LEFT, padx=(0, 8))
        info_frame = ttk.Frame(self)
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        name = skill_info.get("name", skill_info.get("id", "未知"))
        ttk.Label(info_frame, text=name, font=("", 11, "bold")).pack(side=tk.LEFT)
        version = skill_info.get("version", "?")
        ttk.Label(info_frame, text=f" v{version}", foreground="gray").pack(side=tk.LEFT, padx=(4, 0))
        if skill_info.get("has_update"):
            ttk.Label(info_frame, text=" ↻有更新", foreground="orange").pack(side=tk.LEFT, padx=(4, 0))
        if skill_info.get("installed"):
            ttk.Label(info_frame, text=" ✓已安装", foreground="green").pack(side=tk.RIGHT)
        desc = (skill_info.get("summary") or skill_info.get("description") or "")[:60]
        if len((skill_info.get("summary") or skill_info.get("description") or "")) > 60:
            desc += "..."
        ttk.Label(info_frame, text=desc or "暂无简介", foreground="gray", wraplength=320).pack(anchor=tk.W)
        self.bind("<Button-1>", self._on_click)
        for c in self.winfo_children():
            c.bind("<Button-1>", self._on_click)
            if hasattr(c, "winfo_children"):
                for cc in c.winfo_children():
                    cc.bind("<Button-1>", self._on_click)

    def _on_click(self, event):
        if self.on_select:
            self.on_select(self.skill)


class SkillDetailPanel(ttk.Frame):
    """技能详情面板：右侧显示选中技能的详细信息与操作按钮"""

    def __init__(self, parent, on_install=None, on_uninstall=None, on_update=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.skill = None
        self.on_install = on_install
        self.on_uninstall = on_uninstall
        self.on_update = on_update
        self.empty_label = ttk.Label(self, text="选择一个技能查看详情", foreground="gray")
        self.empty_label.pack(expand=True)
        self.content_frame = ttk.Frame(self)
        header = ttk.Frame(self.content_frame)
        header.pack(fill=tk.X, pady=(0, 10))
        self.icon_label = ttk.Label(header, text="📦", font=("", 28))
        self.icon_label.pack(side=tk.LEFT, padx=(0, 12))
        name_frame = ttk.Frame(header)
        name_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.name_label = ttk.Label(name_frame, text="", font=("", 14, "bold"))
        self.name_label.pack(anchor=tk.W)
        self.id_label = ttk.Label(name_frame, text="", foreground="gray")
        self.id_label.pack(anchor=tk.W)
        version_frame = ttk.Frame(self.content_frame)
        version_frame.pack(fill=tk.X, pady=4)
        ttk.Label(version_frame, text="版本：").pack(side=tk.LEFT)
        self.version_label = ttk.Label(version_frame, text="")
        self.version_label.pack(side=tk.LEFT)
        desc_header = ttk.Frame(self.content_frame)
        desc_header.pack(fill=tk.X, pady=(10, 4))
        ttk.Label(desc_header, text="功能简介", font=("", 10, "bold")).pack(side=tk.LEFT)
        ttk.Button(desc_header, text="中文", width=5, command=self._translate_to_zh).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        self.desc_text = scrolledtext.ScrolledText(
            self.content_frame, height=5, wrap=tk.WORD, font=("", 9)
        )
        self.desc_text.pack(fill=tk.X, pady=(0, 8))
        self.desc_text.config(state=tk.DISABLED)
        meta_frame = ttk.LabelFrame(self.content_frame, text="信息", padding=6)
        meta_frame.pack(fill=tk.X, pady=8)
        self.meta_grid = ttk.Frame(meta_frame)
        self.meta_grid.pack(fill=tk.X)
        ttk.Label(self.meta_grid, text="分类：").grid(row=0, column=0, sticky=tk.W)
        self.category_label = ttk.Label(self.meta_grid, text="")
        self.category_label.grid(row=0, column=1, sticky=tk.W, padx=(5, 15))
        ttk.Label(self.meta_grid, text="作者：").grid(row=0, column=2, sticky=tk.W)
        self.author_label = ttk.Label(self.meta_grid, text="")
        self.author_label.grid(row=0, column=3, sticky=tk.W, padx=(5, 0))
        self.action_frame = ttk.Frame(self.content_frame)
        self.action_frame.pack(fill=tk.X, pady=12)
        self.install_btn = ttk.Button(self.action_frame, text="安装", command=self._on_install)
        self.update_btn = ttk.Button(self.action_frame, text="更新", command=self._on_update)
        self.uninstall_btn = ttk.Button(self.action_frame, text="卸载", command=self._on_uninstall)

    def show_skill(self, skill_info):
        self.skill = skill_info
        self.empty_label.pack_forget()
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.icon_label.config(text=skill_info.get("icon", "📦"))
        self.name_label.config(text=skill_info.get("name", skill_info.get("id", "未知")))
        self.id_label.config(text=skill_info.get("id", ""))
        version = skill_info.get("version", "?")
        if skill_info.get("has_update"):
            current = skill_info.get("current_version", "?")
            self.version_label.config(text=f"{current} → {version}", foreground="orange")
        else:
            self.version_label.config(text=version, foreground="")
        self.desc_text.config(state=tk.NORMAL)
        self.desc_text.delete("1.0", tk.END)
        self.desc_text.insert("1.0", skill_info.get("description", skill_info.get("summary", "暂无描述")))
        self.desc_text.config(state=tk.DISABLED)
        self.category_label.config(text=SKILL_CATEGORIES.get(skill_info.get("category", "other"), "其他"))
        self.author_label.config(text=skill_info.get("author", "未知"))
        self._update_buttons()

    def _update_buttons(self):
        if not self.skill:
            return
        installed = self.skill.get("installed", False)
        has_update = self.skill.get("has_update", False)
        for w in (self.install_btn, self.update_btn, self.uninstall_btn):
            w.pack_forget()
        if installed:
            self.uninstall_btn.pack(side=tk.LEFT, padx=(0, 5))
            if has_update:
                self.update_btn.pack(side=tk.LEFT, padx=(0, 5))
        else:
            self.install_btn.pack(side=tk.LEFT, padx=(0, 5))

    def _on_install(self):
        if self.skill and self.on_install:
            self.on_install(self.skill)

    def _on_uninstall(self):
        if self.skill and self.on_uninstall:
            self.on_uninstall(self.skill)

    def _on_update(self):
        if self.skill and self.on_update:
            self.on_update(self.skill)

    def _translate_to_zh(self):
        """将当前功能简介翻译为中文（在线翻译，失败时提示错误）。"""
        text = self.desc_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showerror("错误", "没有可翻译的内容。")
            return

        # 后台线程执行网络请求，避免卡 UI
        def worker():
            try:
                import urllib.parse
                import urllib.request
                import json as _json

                params = {
                    "client": "gtx",
                    "sl": "auto",
                    "tl": "zh-CN",
                    "dt": "t",
                    "q": text,
                }
                url = "https://translate.googleapis.com/translate_a/single?" + urllib.parse.urlencode(
                    params
                )
                req = urllib.request.Request(
                    url, headers={"User-Agent": "OpenClaw-Assistant/1.0"}
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = resp.read().decode("utf-8")
                arr = _json.loads(data)
                zh = "".join(seg[0] for seg in arr[0] if seg[0])

                def update():
                    try:
                        if not self.desc_text.winfo_exists():
                            return
                        self.desc_text.config(state=tk.NORMAL)
                        self.desc_text.delete("1.0", tk.END)
                        self.desc_text.insert("1.0", zh)
                        self.desc_text.config(state=tk.DISABLED)
                    except Exception:
                        pass

                self.after(0, update)
            except Exception as e:
                def show_err():
                    messagebox.showerror("翻译失败", f"无法翻译为中文：\n{e}")
                try:
                    self.after(0, show_err)
                except Exception:
                    pass

        threading.Thread(target=worker, daemon=True).start()


class SkillsPanel(BasePanel):
    """
    技能管理（新设计）：
    - 左右分栏：技能列表（已安装 / 发现更多）+ 技能详情
    - 搜索与分类筛选
    - 卡片展示，详情面板操作（安装/卸载/更新）
    - 集成安装队列管理器、依赖检查、错误处理
    """

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, app, **kwargs)
        self.all_skills = []
        self.filtered_skills = []
        self.selected_skill = None
        self.manager = SkillManager()  # 使用统一的技能管理器提供数据
        
        # 导入并初始化技能安装优化模块
        try:
            from skills.install_queue import InstallQueueManager
            from skills.dependency_checker import DependencyChecker
            from skills.error_handler import InstallErrorHandler, OfflineInstaller
            
            self._queue_manager = InstallQueueManager(max_concurrent=1)
            self._dependency_checker = DependencyChecker()
            self._error_handler = InstallErrorHandler()
            self._offline_installer = OfflineInstaller()
            self._install_optimization_enabled = True
            
            # 设置队列回调
            self._queue_manager.on_task_complete = self._on_install_complete
            self._queue_manager.on_task_failed = self._on_install_failed
            self._queue_manager.on_queue_update = self._on_queue_update
            self._queue_manager.start()
        except ImportError as e:
            print(f"技能安装优化模块导入失败: {e}")
            self._install_optimization_enabled = False

        header = ttk.Frame(self)
        header.pack(fill=tk.X, pady=(12, 6))
        ttk.Label(header, text="技能管理", font=("", 16, "bold")).pack(side=tk.LEFT)

        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, pady=4)

        left_frame = ttk.Frame(main_frame, width=420)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_frame.pack_propagate(False)

        filter_frame = ttk.Frame(left_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 8))
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *a: self._filter_skills())
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=28)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(filter_frame, text="刷新", command=self._refresh, width=8).pack(side=tk.LEFT)

        category_frame = ttk.Frame(left_frame)
        category_frame.pack(fill=tk.X, pady=(0, 8))
        self.category_var = tk.StringVar(value="all")
        for key, label in SKILL_CATEGORIES.items():
            ttk.Radiobutton(
                category_frame, text=label, variable=self.category_var,
                value=key, command=self._filter_skills
            ).pack(side=tk.LEFT, padx=(0, 8))

        list_container = ttk.Frame(left_frame)
        list_container.pack(fill=tk.BOTH, expand=True)

        self.installed_frame = ttk.LabelFrame(list_container, text="已安装技能 (0)", padding=6)
        self.installed_frame.pack(fill=tk.X, pady=(0, 8))
        # 为已安装技能列表增加垂直滚动条，方便浏览更多技能
        self.installed_canvas = tk.Canvas(self.installed_frame, height=120)
        installed_scrollbar = ttk.Scrollbar(
            self.installed_frame, orient=tk.VERTICAL, command=self.installed_canvas.yview
        )
        self.installed_canvas.configure(yscrollcommand=installed_scrollbar.set)
        self.installed_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        installed_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.installed_inner = ttk.Frame(self.installed_canvas)
        self.installed_canvas.create_window((0, 0), window=self.installed_inner, anchor=tk.NW, width=400)
        self.installed_inner.bind(
            "<Configure>",
            lambda e: self.installed_canvas.configure(scrollregion=self.installed_canvas.bbox("all")),
        )

        self.available_frame = ttk.LabelFrame(list_container, text="发现更多技能 (0)", padding=6)
        self.available_frame.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(self.available_frame)
        scrollbar = ttk.Scrollbar(self.available_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.skills_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.skills_frame, anchor=tk.NW, width=400)
        self.skills_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        right_frame = ttk.LabelFrame(main_frame, text="技能详情", width=320)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        right_frame.pack_propagate(False)
        self.detail_panel = SkillDetailPanel(
            right_frame,
            on_install=self._install_skill,
            on_uninstall=self._uninstall_skill,
            on_update=self._update_skill,
        )
        self.detail_panel.pack(fill=tk.BOTH, expand=True)

        log_frame = ttk.LabelFrame(self, text="技能操作日志", padding=4)
        log_frame.pack(fill=tk.X, pady=(6, 4))
        self._log = scrolledtext.ScrolledText(log_frame, height=5, width=70, font=("Consolas", 9))
        self._log.pack(fill=tk.X)
        
        # 安装队列显示区域（新增）
        if self._install_optimization_enabled:
            self._build_install_queue_section()

        self._refresh()
    
    def _build_install_queue_section(self):
        """构建安装队列显示区域"""
        queue_frame = ttk.LabelFrame(self, text="安装队列", padding=6)
        queue_frame.pack(fill=tk.X, pady=(6, 4))
        
        # 队列头部
        header_frame = ttk.Frame(queue_frame)
        header_frame.pack(fill=tk.X, pady=(0, 4))
        
        self._queue_title_label = ttk.Label(
            header_frame, text="安装队列 (0个任务)", font=("Microsoft YaHei", 10, "bold")
        )
        self._queue_title_label.pack(side=tk.LEFT)
        
        self._queue_progress_label = ttk.Label(header_frame, text="0%")
        self._queue_progress_label.pack(side=tk.RIGHT)
        
        self._queue_progress = ttk.Progressbar(header_frame, length=150, mode="determinate")
        self._queue_progress.pack(side=tk.RIGHT, padx=10)
        
        # 任务列表容器
        self._queue_container = ttk.Frame(queue_frame)
        self._queue_container.pack(fill=tk.X)
        
        # 空状态提示
        self._queue_empty_label = ttk.Label(
            self._queue_container, text="暂无安装任务", foreground="gray"
        )
        self._queue_empty_label.pack(pady=10)
        
        # 任务控件字典
        self._queue_task_widgets = {}

    def _log_msg(self, msg: str):
        """
        写入技能操作日志：通过 after 在主线程安全更新。
        """

        def _do():
            try:
                if not self._log.winfo_exists():
                    return
                self._log.insert(tk.END, msg.rstrip() + "\n")
                self._log.see(tk.END)
            except Exception:
                pass

        try:
            self.after(0, _do)
        except Exception:
            pass

    def _read_config_plugins(self):
        if not os.path.isfile(CONFIG_PATH):
            return {}
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ((data.get("plugins") or {}).get("installs") or {})
        except Exception as e:
            self._log_msg(f"[错误] 读取配置失败: {e}")
            return {}

    def _refresh(self):
        """
        刷新技能列表：通过 SkillManager 获取统一的数据源（本地安装 + 内置技能），避免直接解析 CLI 输出。
        """

        self._log_msg("[信息] 正在刷新技能列表...")

        def worker():
            try:
                skills = self.manager.get_skills(force_refresh=True)
            except Exception as e:
                self._log_msg(f"[错误] 刷新技能列表失败: {e}")
                skills = []

            def done():
                self.all_skills = skills
                self._log_msg(f"[信息] 刷新完成，共 {len(self.all_skills)} 个技能。")
                self._filter_skills()

            try:
                self.after(0, done)
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _filter_skills(self):
        search_term = self.search_var.get().strip().lower()
        category = self.category_var.get()
        self.filtered_skills = [
            s for s in self.all_skills
            if (category == "all" or s.get("category") == category)
            and (not search_term or search_term in (s.get("name") or "").lower() or search_term in (s.get("id") or "").lower() or search_term in (s.get("description") or "").lower())
        ]
        self._update_skill_list()

    def _update_skill_list(self):
        """
        根据当前过滤结果刷新技能列表 UI。

        注意：该方法可能在面板/子控件销毁后依然被调用（例如后台刷新回调），
        因此需要在访问 Tk 控件前检查 winfo_exists 以避免 TclError。
        """
        try:
            if (
                not self.winfo_exists()
                or not self.installed_inner.winfo_exists()
                or not self.skills_frame.winfo_exists()
            ):
                return
        except Exception:
            return

        for w in list(self.installed_inner.winfo_children()):
            try:
                w.destroy()
            except Exception:
                pass
        for w in list(self.skills_frame.winfo_children()):
            try:
                w.destroy()
            except Exception:
                pass

        installed = [s for s in self.filtered_skills if s.get("installed")]
        available = [s for s in self.filtered_skills if not s.get("installed")]

        if installed:
            for skill in installed:
                card = SkillCard(self.installed_inner, skill, on_select=self._on_skill_select)
                card.pack(fill=tk.X, pady=2)
        else:
            ttk.Label(self.installed_inner, text="暂无已安装技能", foreground="gray").pack(pady=12)

        if available:
            for skill in available:
                card = SkillCard(self.skills_frame, skill, on_select=self._on_skill_select)
                card.pack(fill=tk.X, pady=2)
        else:
            ttk.Label(self.skills_frame, text="暂无更多技能", foreground="gray").pack(pady=12)

        try:
            self.installed_frame.config(text=f"已安装技能 ({len(installed)})")
            self.available_frame.config(text=f"发现更多技能 ({len(available)})")
        except Exception:
            pass

    def _on_skill_select(self, skill):
        self.selected_skill = skill
        self.detail_panel.show_skill(skill)

    def _install_skill(self, skill):
        """安装技能（集成依赖检查和安装队列）"""
        skill_id = skill.get("id")
        skill_name = skill.get("name", skill_id)
        
        # 使用新的安装优化流程
        if self._install_optimization_enabled:
            self._install_skill_optimized(skill_id, skill_name)
        else:
            # 回退到旧版安装方式
            self._install_skill_legacy(skill_id)
    
    def _install_skill_optimized(self, skill_id: str, skill_name: str):
        """优化的技能安装流程"""
        self._log_msg(f"[信息] 开始安装技能: {skill_name} ({skill_id})")
        
        # 1. 依赖检查
        self._log_msg(f"[信息] 检查依赖...")
        report = self._dependency_checker.check_before_install(skill_id)
        
        if not report.can_install:
            # 依赖检查失败，显示详细信息
            missing = [c.name for c in report.manual_required]
            messagebox.showerror(
                "依赖检查失败",
                f"无法安装 {skill_name}:\n\n"
                f"缺失依赖: {', '.join(missing)}\n\n"
                f"请手动安装缺失的依赖后重试。"
            )
            return
        
        # 2. 自动修复依赖
        if report.auto_fixable:
            self._log_msg(f"[信息] 自动修复依赖...")
            success, errors = self._dependency_checker.auto_fix_dependencies(report)
            if not success:
                self._log_msg(f"[警告] 部分依赖修复失败: {errors}")
                if not messagebox.askyesno(
                    "依赖修复",
                    f"部分依赖自动修复失败:\n{errors}\n\n是否继续安装？"
                ):
                    return
            else:
                self._log_msg(f"[信息] 依赖修复完成")
        
        # 3. 添加到安装队列
        task = self._queue_manager.add_task(
            skill_id=skill_id,
            skill_name=skill_name,
            priority=5
        )
        
        # 4. 更新UI
        self._add_task_to_queue_ui(task)
        self._log_msg(f"[信息] 技能 {skill_name} 已添加到安装队列")
    
    def _install_skill_legacy(self, skill_id: str):
        """旧版技能安装方式（回退）"""
        self._log_msg(f"> openclaw skill install {skill_id}")
        def worker():
            try:
                proc = subprocess.run(
                    f"openclaw skill install {skill_id}",
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                )
                if proc.stdout:
                    self._log_msg(proc.stdout)
                if proc.stderr:
                    self._log_msg(proc.stderr)
                if proc.returncode == 0:
                    self._log_msg(f"[信息] 技能 {skill_id} 安装成功")
                    self.after(0, self._refresh)
                else:
                    self._log_msg(f"[错误] 安装失败，返回码 {proc.returncode}")
            except Exception as e:
                self._log_msg(f"[异常] {e}")
                self.after(0, self._refresh)
        threading.Thread(target=worker, daemon=True).start()
    
    def _add_task_to_queue_ui(self, task):
        """添加任务到队列UI"""
        # 隐藏空状态
        self._queue_empty_label.pack_forget()
        
        # 创建任务行
        task_frame = ttk.Frame(self._queue_container)
        task_frame.pack(fill=tk.X, pady=2)
        
        # 状态图标
        status_label = ttk.Label(task_frame, text="⏳", font=("", 12))
        status_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # 技能名称
        name_label = ttk.Label(
            task_frame, text=task.skill_name, font=("Microsoft YaHei", 10),
            width=20
        )
        name_label.pack(side=tk.LEFT)
        
        # 状态文本
        state_label = ttk.Label(task_frame, text="等待中", width=12)
        state_label.pack(side=tk.LEFT, padx=10)
        
        # 进度条
        progress = ttk.Progressbar(task_frame, length=150, mode="determinate")
        progress.pack(side=tk.LEFT, padx=10)
        
        # 取消按钮
        cancel_btn = ttk.Button(
            task_frame, text="取消", width=6,
            command=lambda: self._cancel_install_task(task.id)
        )
        cancel_btn.pack(side=tk.LEFT)
        
        # 保存引用
        self._queue_task_widgets[task.id] = {
            "frame": task_frame,
            "status_label": status_label,
            "state_label": state_label,
            "progress": progress,
            "cancel_btn": cancel_btn
        }
        
        self._update_queue_title()
    
    def _update_queue_title(self):
        """更新队列标题"""
        stats = self._queue_manager.get_stats()
        self._queue_title_label.config(text=f"安装队列 ({stats.total}个任务)")
    
    def _cancel_install_task(self, task_id: str):
        """取消安装任务"""
        if self._queue_manager.cancel_task(task_id):
            self._log_msg(f"[信息] 任务已取消")
            # 更新UI
            if task_id in self._queue_task_widgets:
                widgets = self._queue_task_widgets[task_id]
                widgets["state_label"].config(text="已取消")
                widgets["cancel_btn"].config(state=tk.DISABLED)
    
    def _on_install_complete(self, task):
        """安装完成回调"""
        self._log_msg(f"[信息] 技能 {task.skill_name} 安装完成")
        
        # 更新UI
        if task.id in self._queue_task_widgets:
            widgets = self._queue_task_widgets[task.id]
            widgets["status_label"].config(text="✅")
            widgets["state_label"].config(text="已完成")
            widgets["progress"]["value"] = 100
            widgets["cancel_btn"].config(state=tk.DISABLED)
        
        # 刷新技能列表
        self.after(0, self._refresh)
        self._update_queue_title()
    
    def _on_install_failed(self, task, error_msg):
        """安装失败回调"""
        # 分析错误
        analysis = self._error_handler.analyze_error(error_msg, task.skill_id)
        
        self._log_msg(f"[错误] 技能 {task.skill_name} 安装失败: {analysis.message}")
        
        # 更新UI
        if task.id in self._queue_task_widgets:
            widgets = self._queue_task_widgets[task.id]
            widgets["status_label"].config(text="❌")
            widgets["state_label"].config(text="失败")
            widgets["cancel_btn"].config(state=tk.DISABLED)
        
        # 显示错误信息和解决方案
        solutions = "\n".join(f"• {s}" for s in analysis.solutions[:3])
        messagebox.showerror(
            "安装失败",
            f"技能 {task.skill_name} 安装失败\n\n"
            f"错误: {analysis.message}\n\n"
            f"建议解决方案:\n{solutions}"
        )
        
        self._update_queue_title()
    
    def _on_queue_update(self, stats):
        """队列更新回调"""
        percentage = int(stats.overall_progress * 100)
        self._queue_progress["value"] = percentage
        self._queue_progress_label.config(text=f"{percentage}%")
        
        # 更新进行中的任务
        for task in self._queue_manager.get_all_tasks():
            if task.id in self._queue_task_widgets:
                widgets = self._queue_task_widgets[task.id]
                
                # 更新状态文本
                status_texts = {
                    "pending": "等待中",
                    "downloading": "下载中",
                    "installing": "安装中",
                    "completed": "已完成",
                    "failed": "失败",
                    "cancelled": "已取消"
                }
                widgets["state_label"].config(
                    text=status_texts.get(task.status.value, task.status.value)
                )
                
                # 更新进度
                widgets["progress"]["value"] = task.progress
                
                # 更新状态图标
                status_icons = {
                    "pending": "⏳",
                    "downloading": "📥",
                    "installing": "⚙️",
                    "completed": "✅",
                    "failed": "❌",
                    "cancelled": "🚫"
                }
                widgets["status_label"].config(
                    text=status_icons.get(task.status.value, "•")
                )
        
        self._update_queue_title()

    def _uninstall_skill(self, skill):
        skill_id = skill.get("id")
        if not messagebox.askyesno("确认卸载", f"确定要卸载技能 {skill_id} 吗？"):
            return
        self._log_msg(f"> openclaw skill uninstall {skill_id}")
        def worker():
            try:
                proc = subprocess.run(
                    f"openclaw skill uninstall {skill_id}",
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                )
                if proc.stdout:
                    self._log_msg(proc.stdout)
                if proc.stderr:
                    self._log_msg(proc.stderr)
                if proc.returncode == 0:
                    self._log_msg(f"[信息] 技能 {skill_id} 卸载成功")
                    self.after(0, self._refresh)
                else:
                    self._log_msg(f"[错误] 卸载失败，返回码 {proc.returncode}")
            except Exception as e:
                self._log_msg(f"[异常] {e}")
                self.after(0, self._refresh)
        threading.Thread(target=worker, daemon=True).start()

    def _update_skill(self, skill):
        skill_id = skill.get("id")
        self._log_msg(f"> openclaw skill update {skill_id}")
        def worker():
            try:
                proc = subprocess.run(
                    f"openclaw skill update {skill_id}",
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                )
                if proc.returncode != 0:
                    proc = subprocess.run(
                        f"openclaw skill install {skill_id}",
                        shell=True,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="ignore",
                    )
                if proc.stdout:
                    self._log_msg(proc.stdout)
                if proc.stderr:
                    self._log_msg(proc.stderr)
                if proc.returncode == 0:
                    self._log_msg(f"[信息] 技能 {skill_id} 更新成功")
                    self.after(0, self._refresh)
                else:
                    self._log_msg(f"[错误] 更新失败，返回码 {proc.returncode}")
            except Exception as e:
                self._log_msg(f"[异常] {e}")
                self.after(0, self._refresh)
        threading.Thread(target=worker, daemon=True).start()


class VersionPanel(BasePanel):
    """版本管理：检查当前/最新版本，一键更新"""

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, app, **kwargs)

        header = ttk.Frame(self)
        header.pack(fill=tk.X, pady=(15, 8))
        ttk.Label(header, text="版本管理", font=("", 16, "bold")).pack(side=tk.LEFT)

        ttk.Label(
            self,
            text="通过 OpenClaw CLI 与 npm 检查当前版本与最新版本，并支持一键更新。",
            wraplength=520,
        ).pack(pady=(0, 10))

        info = ttk.Frame(self)
        info.pack(fill=tk.X, pady=4)
        ttk.Label(info, text="当前版本：").grid(row=0, column=0, sticky="w")
        self._cur_var = tk.StringVar(value="未知")
        ttk.Label(info, textvariable=self._cur_var).grid(row=0, column=1, sticky="w")

        ttk.Label(info, text="最新版本：").grid(row=1, column=0, sticky="w", pady=(2, 0))
        self._latest_var = tk.StringVar(value="未知")
        ttk.Label(info, textvariable=self._latest_var).grid(row=1, column=1, sticky="w", pady=(2, 0))

        btns = ttk.Frame(self)
        btns.pack(fill=tk.X, pady=(8, 4))
        ttk.Button(btns, text="检查更新", command=self._check).pack(side=tk.LEFT, padx=(0, 6))
        self._update_btn = ttk.Button(btns, text="更新到最新版", command=self._update)
        self._update_btn.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btns, text="查看更新说明", command=self._show_release_notes).pack(side=tk.LEFT)

        log_frame = ttk.LabelFrame(self, text="版本操作日志")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 8))
        self._log = scrolledtext.ScrolledText(
            log_frame, height=8, width=70, font=("Consolas", 9)
        )
        self._log.pack(fill=tk.BOTH, expand=True)

        self._check()

    def _log_msg(self, msg: str):
        """
        日志输出：确保在主线程写入，并在控件已销毁时安全忽略。
        """

        def _do_log():
            try:
                # 控件或窗口可能已经销毁，此处加保护
                if not self._log.winfo_exists():
                    return
                self._log.insert(tk.END, msg.rstrip() + "\n")
                self._log.see(tk.END)
            except Exception:
                # 不再向外抛异常，避免线程报 _tkinter.TclError
                pass

        try:
            # 使用 after 保证在 Tk 主线程中执行
            self.after(0, _do_log)
        except Exception:
            # 若面板自身已销毁，直接忽略
            pass

    def _parse_version(self, s):
        if not s:
            return (0, 0, 0)
        s = str(s).strip()
        # 提取类似 2026.3.8 或 v2026.3.8 这样的版本号
        m = re.search(r"\d+(?:\.\d+)+", s)
        if m:
            s = m.group(0)
        else:
            s = s.lstrip("v")
        parts = []
        for x in s.replace("-", ".").split("."):
            try:
                parts.append(int(x))
            except ValueError:
                parts.append(0)
        return tuple(parts) if parts else (0, 0, 0)

    def _run_cmd(self, cmd):
        try:
            r = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
            )
            return r
        except Exception as e:
            self._log_msg(f"[异常] {e}")
            return None

    def _check(self):
        def worker():
            self._log_msg("> openclaw --version")
            r1 = self._run_cmd("openclaw --version")
            cur = "未安装或未知"
            if r1 and r1.returncode == 0 and (r1.stdout or "").strip():
                cur = (r1.stdout or "").strip()
            if r1 and r1.stdout:
                self._log_msg(r1.stdout)
            if r1 and r1.stderr:
                self._log_msg(r1.stderr)

            self._log_msg("> npm view openclaw version")
            r2 = self._run_cmd("npm view openclaw version")
            latest = "未知"
            if r2 and r2.returncode == 0 and (r2.stdout or "").strip():
                latest = (r2.stdout or "").strip()
                self._log_msg(f"[信息] 最新版本: {latest}")
            else:
                if r2 and r2.stderr:
                    self._log_msg(r2.stderr)

            def update_ui():
                # 在主线程更新 Tk 变量
                self._cur_var.set(cur)
                self._latest_var.set(latest)
                cur_v = self._parse_version(cur)
                lat_v = self._parse_version(latest)
                if lat_v > cur_v and cur_v != (0, 0, 0):
                    self._log_msg("[提示] 有可用更新，可以点击“更新到最新版”。")
                elif cur_v >= lat_v and cur_v != (0, 0, 0):
                    self._log_msg("[信息] OpenClaw 已是最新版本。")

            try:
                self.after(0, update_ui)
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _update(self):
        def worker():
            # 禁用更新按钮，避免重复点击
            try:
                self.after(0, lambda: self._update_btn.config(state=tk.DISABLED))
            except Exception:
                pass

            self._log_msg("> npm install -g openclaw@latest")
            r = self._run_cmd("npm install -g openclaw@latest")
            if r and r.stdout:
                self._log_msg(r.stdout)
            if r and r.stderr:
                self._log_msg(r.stderr)
            if r and r.returncode == 0:
                self._log_msg("[信息] 更新成功，正在重新检查版本...")
                self._check()
            elif r:
                self._log_msg(f"[错误] 更新失败，返回码 {r.returncode}")
                err = (r.stderr or r.stdout or "").lower()
                if any(k in err for k in ["eacces", "permission", "权限", "sudo"]):
                    self._log_msg(
                        "[提示] 可能是权限不足：请在有管理员/sudo 权限的终端中运行本助手，"
                        "或手动在该终端执行上述 npm 命令。"
                    )

            # 无论成功失败，最后重新启用按钮
            try:
                self.after(0, lambda: self._update_btn.config(state=tk.NORMAL))
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _show_release_notes(self):
        """
        在默认浏览器中打开 OpenClaw 的版本/更新说明页面。
        这里使用 npm 包页面，用户可从中跳转到项目主页或 release notes。
        """
        url = "https://www.npmjs.com/package/openclaw"
        self._log_msg(f"[信息] 正在打开更新说明页面: {url}")
        try:
            webbrowser.open(url)
        except Exception as e:
            self._log_msg(f"[错误] 无法打开浏览器: {e}")


class DiagnosePanel(BasePanel):
    """诊断工具：环境与配置检查，导出报告（集成健康度评分系统）"""

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, app, **kwargs)

        # 延迟导入诊断引擎与检查项，避免在未使用诊断面板时增加启动开销
        from diagnose.engine import DiagnosticEngine
        from diagnose.checks import (
            NodeVersionCheck,
            NpmCheck,
            PathCheck,
            OpenClawCliCheck,
            ConfigFileExistCheck,
            ConfigJsonStructureCheck,
            ConfigApiKeyCheck,
            ConfigMigrationCheck,
            NpmRegistryConnectivityCheck,
            DiskSpaceCheck,
            SecurityPermissionCheck,
            SkillsHealthCheck,
            OpenClawBugHintsCheck,
        )
        from diagnose.models import DiagnosticGroup
        from diagnose.reporting import render_text_report
        
        # 导入健康度评分系统
        try:
            from diagnose.health_score import HealthScoreCalculator, HealthScoreHistory
            from diagnose.smart_fix import SmartFixAssistant
            self._health_calculator = HealthScoreCalculator()
            self._health_history = HealthScoreHistory()
            self._smart_fix = SmartFixAssistant()
            self._health_score_enabled = True
        except ImportError:
            self._health_score_enabled = False

        self._engine_cls = DiagnosticEngine
        self._checks_classes = [
            NodeVersionCheck,
            NpmCheck,
            PathCheck,
            OpenClawCliCheck,
            ConfigFileExistCheck,
            ConfigJsonStructureCheck,
            ConfigApiKeyCheck,
            ConfigMigrationCheck,
            NpmRegistryConnectivityCheck,
            DiskSpaceCheck,
            SecurityPermissionCheck,
            SkillsHealthCheck,
            OpenClawBugHintsCheck,
        ]
        self._render_text_report = render_text_report
        self._active_group = None

        header = ttk.Frame(self)
        header.pack(fill=tk.X, pady=(15, 4))
        ttk.Label(header, text="龙虾健康中心", font=("", 16, "bold")).pack(side=tk.LEFT)

        ttk.Label(
            self,
            text="检查 OpenClaw 环境、配置、安全与技能健康，为你提供一站式龙虾管家诊断。",
            wraplength=520,
        ).pack(pady=(0, 6))

        # 健康度评分显示区域（新增）
        if self._health_score_enabled:
            self._build_health_score_section()

        btns = ttk.Frame(self)
        btns.pack(fill=tk.X, pady=4)
        ttk.Button(btns, text="开始诊断", command=self._run_diagnose).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(
            btns,
            text="环境自检（OpenClaw）",
            command=self._env_self_check,
        ).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btns, text="导出诊断报告", command=self._export_report).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(btns, text="一键修复", command=self._auto_fix).pack(side=tk.LEFT, padx=(0, 6))

        # 安全四件套快捷入口（独立运行对应安全模块）
        security_btns = ttk.Frame(self)
        security_btns.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(
            security_btns,
            text="安全四件套：",
            foreground="gray",
        ).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(
            security_btns,
            text="权限体检",
            command=self._run_permission_scan,
        ).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(
            security_btns,
            text="技能查毒",
            command=self._run_skill_security_scan,
        ).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(
            security_btns,
            text="安全加固",
            command=self._run_security_hardening,
        ).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(
            security_btns,
            text="漏洞修复",
            command=self._run_vulnerability_scan,
        ).pack(side=tk.LEFT, padx=(0, 4))

        # 诊断项总览表格区域（类似“项目 / 状态 / 建议 / 操作”）
        overview_frame = ttk.LabelFrame(self, text="诊断项目总览", padding=4)
        overview_frame.pack(fill=tk.BOTH, expand=False, pady=(6, 4))

        header_row = ttk.Frame(overview_frame)
        header_row.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(header_row, text="诊断项", width=24).pack(side=tk.LEFT, padx=(2, 2))
        ttk.Label(header_row, text="状态", width=10).pack(side=tk.LEFT, padx=(2, 2))
        ttk.Label(header_row, text="建议", width=26).pack(side=tk.LEFT, padx=(2, 2))
        ttk.Label(header_row, text="操作", width=12).pack(side=tk.LEFT, padx=(2, 2))

        list_container = ttk.Frame(overview_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        # 调低高度，让下方区域（包含“分析错误”按钮）更容易出现在视野中
        self._items_canvas = tk.Canvas(list_container, height=140)
        items_scrollbar = ttk.Scrollbar(
            list_container, orient=tk.VERTICAL, command=self._items_canvas.yview
        )
        self._items_canvas.configure(yscrollcommand=items_scrollbar.set)
        self._items_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        items_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._items_inner = ttk.Frame(self._items_canvas)
        self._items_canvas.create_window((0, 0), window=self._items_inner, anchor=tk.NW, width=680)

        def _on_items_configure(event):
            self._items_canvas.configure(scrollregion=self._items_canvas.bbox("all"))

        self._items_inner.bind("<Configure>", _on_items_configure)

        # 详细结果 / 日志区域
        detail_frame = ttk.LabelFrame(self, text="诊断详情", padding=4)
        # 减少垂直占用空间，为错误分析区域腾出位置
        detail_frame.pack(fill=tk.BOTH, expand=False, pady=(4, 4))
        self._result_box = scrolledtext.ScrolledText(
            detail_frame, height=5, width=80, font=("Consolas", 9)
        )
        self._result_box.pack(fill=tk.BOTH, expand=True)

        # 错误信息快速分析（阶段 1：规则识别 + 指南）
        # 注意：放在 detail_frame 内部，确保小窗口下也能看到按钮，而不需要额外滚动
        error_frame = ttk.LabelFrame(
            detail_frame,
            text="错误信息快速分析（粘贴 OpenClaw 或 Agent 报错）",
            padding=4,
        )
        error_frame.pack(fill=tk.BOTH, expand=False, pady=(6, 0))

        hint = ttk.Label(
            error_frame,
            text="将终端或日志中的错误文本粘贴到下面，点击“分析错误”获取解释与排查建议。\n"
                 "例如：HTTP 400: Invalid request: tool call id write:44 is duplicated",
            foreground="#666",
            wraplength=660,
            justify=tk.LEFT,
        )
        hint.pack(anchor=tk.W, pady=(0, 4))

        self._error_input = scrolledtext.ScrolledText(
            error_frame, height=4, width=80, font=("Consolas", 9)
        )
        self._error_input.pack(fill=tk.BOTH, expand=True)

        btn_row = ttk.Frame(error_frame)
        btn_row.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(
            btn_row,
            text="分析错误",
            command=self._analyze_error_text,
        ).pack(side=tk.LEFT)
        ttk.Button(
            btn_row,
            text="清空",
            command=lambda: self._error_input.delete("1.0", tk.END),
        ).pack(side=tk.LEFT, padx=(6, 0))

        self._last_report = ""
        self._last_results = []
        self._health_score_result = None

    def _analyze_error_text(self):
        """根据常见模式分析错误信息，给出人话解释与排查建议。"""
        text = self._error_input.get("1.0", tk.END).strip()
        if not text:
            return

        lines = []
        lower = text.lower()

        # 规则 1：tool call id duplicated
        if "tool call id" in lower and "duplicated" in lower:
            lines.append("【问题类型】Tool 调用 ID 重复（tool call id duplicated）")
            lines.append(
                "【现象说明】请求被模型/网关拒绝，原因是同一个 tool 调用 ID 被重复使用，"
                "例如多轮对话里都在使用 write:44 作为调用 ID。"
            )
            lines.append(
                "【排查方向】在对应 Agent/Skill 的代码中，检查是否手动设置了 tool 调用 ID："
                "\n  - 搜索关键词：tool_call_id、tool_calls、\"write:44\"、\"tool call id\"；"
                "\n  - 看是否在构造请求时，把上一次响应中的 tool_calls 原样拷贝进新的请求；"
                "\n  - 或者直接把固定的字符串当作 id 使用。"
            )
            lines.append(
                "【修复建议】不要硬编码 tool 调用 ID，交给 SDK/模型自动生成；"
                "如果必须自定义 ID，应当在每次调用时生成全新的随机 ID（例如 UUID）。"
            )

        # 规则 2：context length / token 限制
        if "context_length_exceeded" in lower or "maximum context length" in lower:
            lines.append("【问题类型】上下文过长 / 超出 tokens 限制")
            lines.append(
                "【现象说明】单次对话携带的历史消息或系统提示过长，超过了当前模型允许的最大上下文窗口。"
            )
            lines.append(
                "【排查方向】检查该 Agent 的系统提示、对话历史保留条数、大块文档注入等，是否一次性塞入过多内容。"
            )
            lines.append(
                "【修复建议】缩短系统提示、裁剪历史消息数量、对长文档先做摘要后再塞入对话。"
            )

        # 可以在这里持续扩展更多规则（rate limit、auth、网络等）

        if not lines:
            lines.append("暂未匹配到内置的常见错误模式。")
            lines.append("建议：")
            lines.append("1）确认错误是否来自 OpenClaw CLI / Gateway 或某个 Agent 的响应；")
            lines.append("2）在反馈/提问时附上完整错误文本与相关 Agent 名称，便于进一步分析。")

        text_out = "\n".join(lines)
        try:
            if self._result_box.winfo_exists():
                self._result_box.insert(tk.END, "\n=== 错误分析 ===\n")
                self._result_box.insert(tk.END, text_out + "\n")
                self._result_box.see(tk.END)
        except Exception:
            pass

    def _run_security_suite_action(self, title: str, worker_func):
        """
        运行单个安全模块动作：
        - 清空当前结果
        - 在后台线程中执行 worker_func
        - 由 worker_func 负责调用 _render_overview / 更新详情
        """
        self._result_box.delete("1.0", tk.END)
        self._last_report = ""

        def worker():
            try:
                worker_func()
            except Exception as e:
                self._append(f"[{title}] 运行时出现异常: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def _run_permission_scan(self):
        """运行权限体检（PermissionScanner），并覆盖当前诊断总览。"""

        def do_scan():
            try:
                from security.permission_scanner import PermissionScanner
                from security.models import RiskLevel
            except ImportError:
                self._append("[权限体检] 未找到 security.permission_scanner 模块，请确认已安装安全中心组件。")
                return

            scanner = PermissionScanner()
            report = scanner.scan()
            checks = report.get("checks", [])

            # 适配到诊断总览所需的简化结果结构
            from diagnose.models import DiagnosticStatus as DS  # type: ignore

            class _SimpleResult:
                def __init__(self, name, status, message, details=""):
                    self.name = name
                    self.status = status
                    self.message = message
                    self.details = details

            def to_status(level):
                if level == RiskLevel.CRITICAL or level == RiskLevel.HIGH:
                    return DS.FAIL
                if level == RiskLevel.MEDIUM:
                    return DS.WARN
                return DS.PASS

            results = []
            for c in checks:
                status = to_status(getattr(c, "level", None))
                msg = getattr(c, "message", "")
                details = getattr(c, "details", "") or getattr(c, "fix_suggestion", "")
                results.append(
                    _SimpleResult(
                        name=getattr(c, "name", "未知检查项"),
                        status=status,
                        message=msg,
                        details=details,
                    )
                )

            # 更新总览和详情（覆盖原有内容）
            self._render_overview(results)

            lines = ["=== 权限体检报告 ===", f"综合评分: {report.get('score', '--')}"]
            for c in checks:
                lines.append(f"\n[{getattr(c, 'name', '未知')}]")
                lines.append(f"等级: {getattr(c, 'level', '')}")
                lines.append(f"说明: {getattr(c, 'message', '')}")
                if getattr(c, "fix_suggestion", ""):
                    lines.append(f"建议: {getattr(c, 'fix_suggestion', '')}")

            text = "\n".join(lines)
            try:
                if self._result_box.winfo_exists():
                    self._result_box.delete("1.0", tk.END)
                    self._result_box.insert(tk.END, text)
                    self._result_box.see(tk.END)
            except Exception:
                pass

        self._run_security_suite_action("权限体检", do_scan)

    def _run_skill_security_scan(self):
        """运行技能查毒（SkillSecurityScanner），并覆盖当前诊断总览。"""

        def do_scan():
            try:
                from security.skill_scanner import SkillSecurityScanner
            except ImportError:
                self._append("[技能查毒] 未找到 security.skill_scanner 模块，请确认已安装安全中心组件。")
                return

            scanner = SkillSecurityScanner()
            reports = scanner.scan_all()

            from diagnose.models import DiagnosticStatus as DS  # type: ignore

            class _SimpleResult:
                def __init__(self, name, status, message, details=""):
                    self.name = name
                    self.status = status
                    self.message = message
                    self.details = details

            # 按风险聚合
            suspicious = [r for r in reports if getattr(r, "is_suspicious", False)]
            unknown = [r for r in reports if getattr(r, "trust_level", "") in ("unknown", "community")]

            results = []
            if suspicious:
                names = ", ".join(getattr(r, "id", getattr(r, "name", "未知")) for r in suspicious[:5])
                results.append(
                    _SimpleResult(
                        name="高危/可疑技能",
                        status=DS.FAIL,
                        message=f"{len(suspicious)} 个技能被标记为可疑",
                        details=f"示例: {names}",
                    )
                )
            if unknown:
                names = ", ".join(getattr(r, "id", getattr(r, "name", "未知")) for r in unknown[:5])
                results.append(
                    _SimpleResult(
                        name="未知来源技能",
                        status=DS.WARN,
                        message=f"{len(unknown)} 个技能来源未知或社区贡献",
                        details=f"示例: {names}",
                    )
                )
            if not results:
                results.append(
                    _SimpleResult(
                        name="技能安全状态",
                        status=DS.PASS,
                        message="未发现明显可疑技能",
                        details="所有已安装技能来源与权限均在安全范围内。",
                    )
                )

            self._render_overview(results)

            # 详情文本
            lines = ["=== 技能安全扫描报告 ===", f"总计技能数: {len(reports)}"]
            for r in reports:
                lines.append(f"\n[{getattr(r, 'id', getattr(r, 'name', '未知'))}]")
                lines.append(f"来源可信度: {getattr(r, 'trust_level', 'unknown')}")
                if getattr(r, "permissions", None):
                    lines.append(f"权限: {getattr(r, 'permissions', '')}")
                if getattr(r, "network_calls", None):
                    lines.append(f"网络访问: {getattr(r, 'network_calls', '')}")
                if getattr(r, "file_operations", None):
                    lines.append(f"文件操作: {getattr(r, 'file_operations', '')}")

            text = "\n".join(lines)
            try:
                if self._result_box.winfo_exists():
                    self._result_box.delete("1.0", tk.END)
                    self._result_box.insert(tk.END, text)
                    self._result_box.see(tk.END)
            except Exception:
                pass

        self._run_security_suite_action("技能查毒", do_scan)

    def _run_security_hardening(self):
        """运行安全加固计划生成（不直接修改配置），并覆盖当前诊断总览。"""

        def do_scan():
            try:
                from security.hardening_engine import SecurityHardeningEngine
            except ImportError:
                self._append("[安全加固] 未找到 security.hardening_engine 模块，请确认已安装安全中心组件。")
                return

            engine = SecurityHardeningEngine()
            plan = engine.plan()
            actions = plan.get("actions", [])

            from diagnose.models import DiagnosticStatus as DS  # type: ignore

            class _SimpleResult:
                def __init__(self, name, status, message, details=""):
                    self.name = name
                    self.status = status
                    self.message = message
                    self.details = details

            results = []
            for a in actions:
                results.append(
                    _SimpleResult(
                        name=a.get("name", "加固项"),
                        status=DS.WARN,
                        message=a.get("summary", ""),
                        details=a.get("details", ""),
                    )
                )
            if not results:
                results.append(
                    _SimpleResult(
                        name="安全加固建议",
                        status=DS.PASS,
                        message="当前未发现可自动加固的高危项",
                        details="",
                    )
                )

            self._render_overview(results)

            # 详情文本
            lines = ["=== 安全加固计划 ==="]
            if not actions:
                lines.append("当前配置无需额外加固。")
            else:
                for a in actions:
                    lines.append(f"\n[{a.get('name', '加固项')}]")
                    if a.get("summary"):
                        lines.append(f"说明: {a['summary']}")
                    if a.get("details"):
                        lines.append(f"细节: {a['details']}")
                    if a.get("risk_level"):
                        lines.append(f"风险等级: {a['risk_level']}")

                lines.append(
                    "\n提示：本版本仅生成加固建议，不会直接修改配置文件或权限，请根据建议手动处理。"
                )

            text = "\n".join(lines)
            try:
                if self._result_box.winfo_exists():
                    self._result_box.delete("1.0", tk.END)
                    self._result_box.insert(tk.END, text)
                    self._result_box.see(tk.END)
            except Exception:
                pass

        self._run_security_suite_action("安全加固", do_scan)

    def _run_vulnerability_scan(self):
        """运行漏洞扫描（VulnerabilityPatcher.scan），并覆盖当前诊断总览。"""

        def do_scan():
            try:
                from security.vuln_patcher import VulnerabilityPatcher
            except ImportError:
                self._append("[漏洞修复] 未找到 security.vuln_patcher 模块，请确认已安装安全中心组件。")
                return

            patcher = VulnerabilityPatcher()
            hits = patcher.scan()

            from diagnose.models import DiagnosticStatus as DS  # type: ignore

            class _SimpleResult:
                def __init__(self, name, status, message, details=""):
                    self.name = name
                    self.status = status
                    self.message = message
                    self.details = details

            results = []
            for h in hits:
                severity = getattr(h, "severity", "MEDIUM")
                status = DS.FAIL if severity.upper() == "CRITICAL" else DS.WARN
                msg = getattr(h, "name", "已知漏洞")
                details = getattr(h, "description", "")
                results.append(
                    _SimpleResult(
                        name=getattr(h, "id", "漏洞"),
                        status=status,
                        message=msg,
                        details=details,
                    )
                )

            if not results:
                results.append(
                    _SimpleResult(
                        name="漏洞扫描结果",
                        status=DS.PASS,
                        message="未命中已知高危漏洞库中的条目",
                        details="",
                    )
                )

            self._render_overview(results)

            # 详情文本
            lines = ["=== 漏洞扫描报告 ==="]
            if not hits:
                lines.append("当前环境未命中本地漏洞数据库中的高危/中危漏洞。")
            else:
                for h in hits:
                    lines.append(f"\n[{getattr(h, 'id', '漏洞')}] {getattr(h, 'name', '')}")
                    lines.append(f"等级: {getattr(h, 'severity', '')}")
                    if getattr(h, "description", ""):
                        lines.append(f"说明: {getattr(h, 'description', '')}")
                    if getattr(h, "fix_action", ""):
                        lines.append(f"推荐修复: {getattr(h, 'fix_action', '')}")
                    if getattr(h, "miit_notice", ""):
                        lines.append(f"相关通报: {getattr(h, 'miit_notice', '')}")
                lines.append(
                    "\n提示：本版本仅提供漏洞识别与修复建议，具体修复请根据建议手动执行。"
                )

            text = "\n".join(lines)
            try:
                if self._result_box.winfo_exists():
                    self._result_box.delete("1.0", tk.END)
                    self._result_box.insert(tk.END, text)
                    self._result_box.see(tk.END)
            except Exception:
                pass

        self._run_security_suite_action("漏洞修复", do_scan)

    def _build_health_score_section(self):
        """构建健康度评分显示区域"""
        # 健康度评分框架（压缩高度，为下方区域腾出空间）
        self._health_frame = ttk.LabelFrame(
            self, text="健康度评分", padding=6
        )
        # 不再使用 expand，让整体区域更紧凑
        self._health_frame.pack(fill=tk.X, pady=(0, 4))
        
        # 左侧：评分显示
        left_frame = ttk.Frame(self._health_frame)
        left_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        # 大分数显示
        self._health_score_label = ttk.Label(
            left_frame, text="--", font=("Microsoft YaHei", 24, "bold"),
            foreground="#999"
        )
        self._health_score_label.pack()
        
        # 等级标签
        self._health_grade_label = ttk.Label(
            left_frame, text="等待诊断", font=("Microsoft YaHei", 10),
            foreground="#666"
        )
        self._health_grade_label.pack()
        
        # 中间：分类得分
        center_frame = ttk.Frame(self._health_frame)
        center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        title_label = ttk.Label(
            center_frame, text="分类得分", font=("Microsoft YaHei", 10, "bold")
        )
        title_label.pack(anchor=tk.W, pady=(0, 5))

        # 分类得分网格（使用单独的 Frame 避免与 pack 混用）
        grid_frame = ttk.Frame(center_frame)
        grid_frame.pack(fill=tk.X)

        self._category_labels = {}
        categories = [
            ("environment", "环境检查"),
            ("configuration", "配置检查"),
            ("tools", "工具检查"),
            ("security", "安全检查"),
            ("performance", "性能检查")
        ]

        for i, (cat_id, cat_name) in enumerate(categories):
            row = i // 3
            col = i % 3

            cat_frame = ttk.Frame(grid_frame)
            cat_frame.grid(row=row, column=col, padx=10, pady=3, sticky=tk.W)
            
            ttk.Label(
                cat_frame, text=f"{cat_name}:", font=("Microsoft YaHei", 9),
                foreground="#666"
            ).pack(side=tk.LEFT)
            
            score_label = ttk.Label(
                cat_frame, text="--", font=("Microsoft YaHei", 9, "bold"),
                foreground="#999", width=4
            )
            score_label.pack(side=tk.LEFT)
            
            self._category_labels[cat_id] = score_label
        
        # 右侧：操作按钮
        right_frame = ttk.Frame(self._health_frame)
        right_frame.pack(side=tk.RIGHT, padx=(20, 0))
        
        self._health_history_btn = ttk.Button(
            right_frame, text="查看历史", command=self._show_health_history
        )
        self._health_history_btn.pack(pady=2)
        
        self._health_trend_btn = ttk.Button(
            right_frame, text="趋势图", command=self._show_health_trend
        )
        self._health_trend_btn.pack(pady=2)

    def _update_health_score_display(self, score_result):
        """更新健康度评分显示"""
        if not self._health_score_enabled:
            return
        
        # 更新总分
        score = score_result.total_score
        grade = score_result.grade
        
        self._health_score_label.config(
            text=str(score),
            foreground=grade.color
        )
        
        self._health_grade_label.config(
            text=f"{grade.grade}级 - {grade.label}",
            foreground=grade.color
        )
        
        # 更新分类得分
        for cat in score_result.categories:
            cat_id = cat.name.lower().replace("检查", "").replace(" ", "_")
            if cat_id in self._category_labels:
                label = self._category_labels[cat_id]
                label.config(text=f"{cat.score}分")
                
                # 根据分数设置颜色
                if cat.score >= 80:
                    label.config(foreground="#4CAF50")
                elif cat.score >= 60:
                    label.config(foreground="#FFC107")
                else:
                    label.config(foreground="#F44336")

    def _show_health_history(self):
        """显示健康度历史"""
        if not self._health_score_enabled:
            return
        
        history = self._health_history.get_history(limit=10)
        
        if not history:
            messagebox.showinfo("历史记录", "暂无历史记录")
            return
        
        # 构建历史记录文本
        lines = ["健康度历史记录（最近10次）", "=" * 40]
        for record in reversed(history):
            lines.append(f"\n时间: {record['timestamp'][:19]}")
            lines.append(f"评分: {record['total_score']}分 ({record['grade']}级)")
            lines.append(f"状态: {record['grade_label']}")
        
        # 显示在历史对话框中
        self._show_text_dialog("健康度历史", "\n".join(lines))

    def _show_health_trend(self):
        """显示健康度趋势"""
        if not self._health_score_enabled:
            return
        
        trend = self._health_history.get_trend(days=30)
        
        if len(trend) < 2:
            messagebox.showinfo("趋势图", "数据点不足，无法生成趋势图\n请至少进行2次诊断")
            return
        
        # 构建趋势文本
        lines = ["健康度趋势（最近30天）", "=" * 40]
        for point in trend:
            lines.append(f"{point['date']}: {point['score']}分 ({point['grade']}级)")
        
        self._show_text_dialog("健康度趋势", "\n".join(lines))

    def _show_text_dialog(self, title: str, content: str):
        """显示文本对话框"""
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.geometry("500x400")
        dialog.transient(self)
        dialog.grab_set()
        
        text = scrolledtext.ScrolledText(
            dialog, wrap=tk.WORD, font=("Microsoft YaHei", 10)
        )
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert("1.0", content)
        text.config(state=tk.DISABLED)
        
        ttk.Button(dialog, text="关闭", command=dialog.destroy).pack(pady=10)

    def _append(self, line: str):
        """主线程安全写入诊断结果（子线程中调用时通过 after 投递到主线程）"""
        self._last_report += line.rstrip() + "\n"

        def _do():
            try:
                if self._result_box.winfo_exists():
                    self._result_box.insert(tk.END, line.rstrip() + "\n")
                    self._result_box.see(tk.END)
            except Exception:
                pass

        try:
            self.after(0, _do)
        except Exception:
            pass

    def _render_overview(self, results):
        """
        渲染“诊断项目总览”表格：
        诊断项 | 状态 | 建议 | 操作（查看 / 修复）
        """
        # 若面板已销毁则直接返回
        try:
            if not self.winfo_exists() or not self._items_inner.winfo_exists():
                return
        except Exception:
            return

        for w in list(self._items_inner.winfo_children()):
            try:
                w.destroy()
            except Exception:
                pass

        def short_hint(msg: str, limit: int = 30) -> str:
            m = (msg or "").strip().splitlines()[0] if msg else ""
            return (m[: limit - 1] + "…") if len(m) > limit else m

        def status_text(status):
            from diagnose.models import DiagnosticStatus as DS

            if status == DS.PASS:
                return "正常"
            if status == DS.WARN:
                return "警告"
            if status == DS.FAIL:
                return "错误"
            return str(status)

        def status_icon(status):
            from diagnose.models import DiagnosticStatus as DS

            if status == DS.PASS:
                return "✅"
            if status == DS.WARN:
                return "⚠️"
            if status == DS.FAIL:
                return "❌"
            return "•"

        for idx, res in enumerate(results):
            row = ttk.Frame(self._items_inner)
            row.pack(fill=tk.X, pady=1)

            ttk.Label(row, text=res.name, width=24, anchor=tk.W).pack(
                side=tk.LEFT, padx=(2, 2)
            )

            # 状态列：带图标与彩色文字
            fg_color = ""
            try:
                from diagnose.models import DiagnosticStatus as DS  # type: ignore

                if res.status == DS.PASS:
                    fg_color = "green"
                elif res.status == DS.WARN:
                    fg_color = "orange"
                elif res.status == DS.FAIL:
                    fg_color = "red"
            except Exception:
                fg_color = ""

            ttk.Label(
                row,
                text=f"{status_icon(res.status)} {status_text(res.status)}",
                width=10,
                anchor=tk.W,
                foreground=fg_color or None,
            ).pack(side=tk.LEFT, padx=(2, 2))

            ttk.Label(
                row,
                text=short_hint(res.message),
                width=26,
                anchor=tk.W,
            ).pack(side=tk.LEFT, padx=(2, 2))

            btn_area = ttk.Frame(row, width=12)
            btn_area.pack(side=tk.LEFT, padx=(2, 2))

            def make_view_handler(r=res):
                def _view():
                    try:
                        if self._result_box.winfo_exists():
                            self._result_box.delete("1.0", tk.END)
                            self._result_box.insert(
                                tk.END,
                                f"{r.name}\n状态: {status_text(r.status)}\n\n"
                                f"{r.message}\n\n{r.details or ''}",
                            )
                            self._result_box.see(tk.END)
                    except Exception:
                        pass

                return _view

            ttk.Button(btn_area, text="查看", width=5, command=make_view_handler()).pack(
                side=tk.LEFT, padx=(0, 2)
            )

            # 修复按钮：对警告 / 错误项高亮可用（当前版本为付费功能提示）
            from diagnose.models import DiagnosticStatus as DS  # type: ignore

            has_fix = res.status in (DS.WARN, DS.FAIL)

            def make_fix_handler(r=res):
                def _fix():
                    # 目前策略：诊断免费，自动修复为付费能力，先提示用户
                    if not getattr(r, "fix_action", None):
                        messagebox.showinfo(
                            "修复（专业版）",
                            "当前版本提供免费的诊断结果展示。\n\n"
                            "自动修复功能计划作为龙虾管家的专业版能力开放，"
                            "目前请根据“建议”内容手动处理相关问题。",
                        )
                        return
                    # 若未来为该检查配置了 fix_action，可在此处真正执行自动修复。
                    messagebox.showinfo(
                        "修复（专业版）",
                        "检测到该诊断项支持自动修复。\n\n"
                        "自动修复功能属于收费能力，后续版本开放后可在此一键修复。",
                    )

                return _fix

            fix_btn = ttk.Button(
                btn_area,
                text="修复",
                width=5,
                command=make_fix_handler(),
            )
            fix_btn.pack(side=tk.LEFT)
            if not has_fix:
                fix_btn.state(["disabled"])

    def _run_diagnose(self):
        self._result_box.delete("1.0", tk.END)
        self._last_report = ""
        self._last_results = []

        def worker():
            try:
                engine = self._engine_cls()
                # 注册所有检查项
                for cls in self._checks_classes:
                    try:
                        engine.register_check(cls())
                    except Exception as e:
                        self._append(f"[诊断引擎] 注册检查 {cls} 失败: {e}")
                results = engine.run_all()
                report = self._render_text_report(results)

                def update_ui():
                    # 更新总览表格
                    self._render_overview(results)
                    # 更新详情文本
                    try:
                        if self._result_box.winfo_exists():
                            self._result_box.delete("1.0", tk.END)
                            self._result_box.insert(tk.END, report)
                            self._result_box.see(tk.END)
                    except Exception:
                        pass
                    self._last_report = report
                    self._last_results = results

                    # 计算并显示健康度评分（新增）
                    if self._health_score_enabled:
                        try:
                            # 转换诊断结果为健康度评分格式
                            health_results = self._convert_to_health_results(results)
                            score_result = self._health_calculator.calculate(health_results)
                            self._update_health_score_display(score_result)
                            self._health_history.save(score_result)
                            self._health_score_result = score_result
                        except Exception as e:
                            print(f"健康度评分计算失败: {e}")

                try:
                    self.after(0, update_ui)
                except Exception:
                    pass
            except Exception as e:
                self._append(f"[诊断引擎] 运行诊断时出现异常: {e}")

        # 在后台线程中运行诊断，避免阻塞 UI
        threading.Thread(target=worker, daemon=True).start()

    def _convert_to_health_results(self, diagnose_results):
        """将诊断结果转换为健康度评分格式"""
        health_results = []
        
        from diagnose.models import DiagnosticStatus as DS
        
        category_map = {
            "ENV": "environment",
            "CONFIG": "configuration",
            "TOOLS": "tools",
            "SECURITY": "security",
            "PERFORMANCE": "performance",
            "GATEWAY": "environment",
            "CHANNELS": "configuration",
            "STATE": "configuration",
            "AUTOMATION": "tools",
            "MODELS": "configuration"
        }
        
        for res in diagnose_results:
            # 映射状态
            if res.status == DS.PASS:
                status = "pass"
            elif res.status == DS.WARN:
                status = "warn"
            elif res.status == DS.FAIL:
                status = "fail"
            else:
                status = "unknown"
            
            # 映射分类
            category = category_map.get(str(res.group), "other")
            
            health_results.append({
                "name": res.name,
                "status": status,
                "category": category,
                "message": res.message,
                "weight": 10
            })
        
        return health_results

    def _export_report(self):
        if not self._last_report.strip():
            messagebox.showerror("错误", "尚未生成诊断结果，请先点击“开始诊断”。")
            return
        path = filedialog.asksaveasfilename(
            title="保存诊断报告",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialfile="openclaw_diagnose_report.txt",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._last_report)
            messagebox.showinfo("保存成功", f"诊断报告已保存到:\n{path}")
        except Exception as e:
            messagebox.showerror("保存失败", f"无法保存报告:\n{e}")

    def _auto_fix(self):
        """
        一键修复：优先尝试修复环境与 CLI 基础问题，然后修复配置文件：
        - 环境：检查 Node.js 是否存在及主版本，给出升级/安装建议
        - CLI：若缺少 openclaw 命令，尝试执行 npm 安装；若权限不足，给出明确提示
        - 配置：针对配置文件缺失 / 损坏 / 结构异常的情况，尝试生成或修复 openclaw.json 的 models 部分
        """

        def worker():
            self._append("\n=== 一键修复（环境 & 配置） ===")
            
            # 使用智能修复助手（新增）
            if self._health_score_enabled and self._last_results:
                self._append("\n[智能修复] 分析诊断结果...")
                fix_count = 0
                manual_fixes = []
                
                for res in self._last_results:
                    from diagnose.models import DiagnosticStatus as DS
                    if res.status in (DS.WARN, DS.FAIL):
                        issue = {
                            "name": res.name,
                            "status": "fail" if res.status == DS.FAIL else "warn",
                            "message": res.message,
                            "category": str(res.group).lower()
                        }
                        
                        fix_result = self._smart_fix.analyze_and_fix(issue)
                        
                        if fix_result.level.value == "auto" and fix_result.success:
                            self._append(f"  ✅ 自动修复: {fix_result.message}")
                            fix_count += 1
                        elif fix_result.level.value == "manual":
                            manual_fixes.append({
                                "name": res.name,
                                "message": fix_result.message,
                                "details": fix_result.details
                            })
                
                if fix_count > 0:
                    self._append(f"\n[智能修复] 成功自动修复 {fix_count} 个问题")
                
                if manual_fixes:
                    self._append(f"\n[智能修复] 以下问题需要手动处理:")
                    for fix in manual_fixes:
                        self._append(f"  • {fix['name']}: {fix['message']}")

            # 1. Node.js 环境检查与修复建议
            self._append("\n[1] 环境修复 - Node.js")
            try:
                r_node = subprocess.run(
                    "node --version",
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                    timeout=10,
                )
                if r_node.returncode == 0 and (r_node.stdout or "").strip():
                    ver = (r_node.stdout or "").strip()
                    self._append(f"  ✅ 检测到 Node.js: {ver}")
                    # 简单版本建议
                    try:
                        clean = ver.strip().lstrip("v")
                        major = int(clean.split(".")[0])
                        if major < 18:
                            self._append(
                                f"  ⚠️ 当前 Node 主版本为 {major}，建议升级到 Node 18+ 以获得更佳兼容性。"
                            )
                    except Exception:
                        pass
                else:
                    self._append("  ❌ 未检测到 node 命令，无法自动安装 Node.js。")
                    if sys.platform == "win32":
                        self._append(
                            "  ▶ 请从 https://nodejs.org 下载并安装 LTS 版本 Node.js，"
                            "安装完成后重新运行诊断。"
                        )
                    elif sys.platform == "darwin":
                        self._append(
                            "  ▶ macOS 建议使用 Homebrew 安装：brew install node，"
                            "或从 https://nodejs.org 下载官方安装包。"
                        )
                    else:
                        self._append(
                            "  ▶ Linux 建议使用发行版包管理器安装（如 apt/dnf/pacman），"
                            "或参考 https://nodejs.org 的安装说明。"
                        )
            except Exception as e:
                self._append(f"  ⚠️ 检测/建议 Node.js 时出现异常: {e}")

            # 2. 尝试修复 OpenClaw CLI
            self._append("\n[2] 环境修复 - OpenClaw CLI")
            try:
                r_cli = subprocess.run(
                    "openclaw --version",
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                    timeout=10,
                )
                if r_cli.returncode == 0 and (r_cli.stdout or "").strip():
                    self._append(f"  ✅ 已检测到 OpenClaw CLI: {(r_cli.stdout or '').strip()}")
                else:
                    self._append("  ⚠️ 未检测到 openclaw 命令，尝试通过 npm 安装/修复...")
                    r_fix = subprocess.run(
                        "npm install -g openclaw@latest",
                        shell=True,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="ignore",
                        timeout=300,
                    )
                    if r_fix.stdout:
                        self._append(r_fix.stdout)
                    if r_fix.stderr:
                        self._append(r_fix.stderr)
                    if r_fix.returncode == 0:
                        self._append("  ✅ 已尝试安装/更新 OpenClaw CLI，建议重新运行诊断确认。")
                    else:
                        self._append(f"  ❌ npm 安装 openclaw 失败，返回码 {r_fix.returncode}。")
                        err = (r_fix.stderr or r_fix.stdout or "").lower()
                        if any(k in err for k in ["eacces", "permission", "权限", "sudo"]):
                            self._append(
                                "  ⚠️ 可能是权限不足，请在管理员/有 sudo 权限的终端中手动执行：\n"
                                "      npm install -g openclaw@latest"
                            )
            except Exception as e:
                self._append(f"  ⚠️ 尝试修复 OpenClaw CLI 时出现异常: {e}")

            # 3. 修复配置文件
            self._append("\n[3] 配置修复 - openclaw.json")
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            summary = []

            def backup_existing():
                try:
                    if os.path.isfile(CONFIG_PATH):
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        backup_path = CONFIG_PATH + f".bak.{ts}"
                        shutil.copy2(CONFIG_PATH, backup_path)
                        self._append(f"  ℹ️ 已备份原配置到: {backup_path}")
                        return True
                except Exception as e:
                    self._append(f"  ⚠️ 备份原配置失败: {e}")
                return False

            # 情况 1：文件不存在
            if not os.path.isfile(CONFIG_PATH):
                try:
                    minimal = {"models": {"providers": {}}}
                    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                        json.dump(minimal, f, ensure_ascii=False, indent=2)
                    self._append(f"  ✅ 未找到配置文件，已生成最小配置: {CONFIG_PATH}")
                    summary.append("生成最小配置")
                except Exception as e:
                    self._append(f"  ❌ 生成配置失败: {e}")
                    summary.append("生成失败")
            else:
                # 文件存在，尝试读取并修复
                try:
                    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except json.JSONDecodeError as e:
                    self._append(f"  ❌ JSON 解析失败: {e}")
                    if backup_existing():
                        try:
                            minimal = {"models": {"providers": {}}}
                            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                                json.dump(minimal, f, ensure_ascii=False, indent=2)
                            self._append("  ✅ 已用最小配置替换损坏的配置文件。")
                            summary.append("重写为最小配置")
                        except Exception as e2:
                            self._append(f"  ❌ 写入最小配置失败: {e2}")
                            summary.append("写入失败")
                    else:
                        summary.append("无法备份/重写")
                except Exception as e:
                    self._append(f"  ❌ 读取配置异常: {e}")
                    summary.append("读取异常")
                else:
                    if not isinstance(data, dict):
                        self._append("  ❌ 配置根节点不是对象，将用最小配置替换。")
                        if backup_existing():
                            try:
                                minimal = {"models": {"providers": {}}}
                                with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                                    json.dump(minimal, f, ensure_ascii=False, indent=2)
                                self._append("  ✅ 已用最小配置替换异常配置。")
                                summary.append("重写为最小配置")
                            except Exception as e2:
                                self._append(f"  ❌ 写入最小配置失败: {e2}")
                                summary.append("写入失败")
                    else:
                        changed = False
                        if "models" not in data or not isinstance(data.get("models"), dict):
                            data["models"] = {"providers": {}}
                            self._append("  ⚠️ 修复: 重建 models 结构。")
                            changed = True
                        providers = data["models"].get("providers")
                        if not isinstance(providers, dict):
                            data["models"]["providers"] = {}
                            self._append("  ⚠️ 修复: 重建 models.providers 结构。")
                            changed = True
                        if changed:
                            if backup_existing():
                                try:
                                    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                                        json.dump(data, f, ensure_ascii=False, indent=2)
                                    self._append("  ✅ 已修复配置文件的 models 相关结构。")
                                    summary.append("修复 models 结构")
                                except Exception as e2:
                                    self._append(f"  ❌ 写回配置失败: {e2}")
                                    summary.append("写回失败")
                            else:
                                summary.append("无法备份/写回")
                        else:
                            self._append("  ✅ 配置文件结构已正常，无需修复。")
                            summary.append("无需修复")

            self._append("=== 一键修复结束 ===")

        threading.Thread(target=worker, daemon=True).start()

    def _env_self_check(self):
        """
        环境自检（聚焦 OpenClaw CLI 与全局配置）：
        - 运行 openclaw --version，捕获类似“Invalid config ... Unrecognized keys”错误
        - 检查 ~/.openclaw/openclaw.json 中 models 节点的结构与可疑键名
        - 用中文给出直接可操作的指导
        """

        self._result_box.delete("1.0", tk.END)
        self._last_report = ""

        def worker():
            self._append("=== 环境自检（OpenClaw CLI & 配置） ===")

            # 1. 运行 openclaw --version，捕获典型错误
            self._append("\n[1] 检查 openclaw 命令可用性")
            try:
                r = subprocess.run(
                    "openclaw --version",
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                    timeout=15,
                )
            except Exception as e:
                self._append(f"  ❌ 无法运行 openclaw --version：{e}")
            else:
                out = (r.stdout or "").strip()
                err = (r.stderr or "").strip()
                if r.returncode == 0 and out:
                    self._append(f"  ✅ openclaw --version 输出：{out}")
                elif r.returncode != 0:
                    self._append(
                        f"  ❌ openclaw --version 返回码 {r.returncode}，原始输出如下："
                    )
                    if out:
                        self._append("  [stdout]\n" + out)
                    if err:
                        self._append("  [stderr]\n" + err)

                    # 针对 Invalid config / Unrecognized keys 做专项提示
                    m = re.search(
                        r"Invalid config at ([^\n]+openclaw\.json):\\n- models: Unrecognized keys: ([^\n]+)",
                        err or out,
                    )
                    if m:
                        cfg_path = m.group(1).strip()
                        bad_keys = m.group(2).strip()
                        self._append(
                            "\n  ⚠️ 侦测到 OpenClaw CLI 配置格式错误：\n"
                            f"     配置文件：{cfg_path}\n"
                            f"     未识别的键：{bad_keys}\n"
                            "  这通常是旧版本配置残留或手动编辑导致的。\n"
                            "  建议操作：\n"
                            "  1）打开上述文件，找到 models 下的这些键（例如 default / thinking），先暂时注释/删除；\n"
                            "  2）或在“诊断工具”中点击「一键修复」，让管家尝试重建 models 结构；\n"
                            "  3）修改后重新运行 openclaw --version 验证是否恢复正常。"
                        )

            # 2. 直接检查配置文件结构，识别可疑键名
            self._append("\n[2] 检查全局配置文件结构 (~/.openclaw/openclaw.json)")
            if not os.path.isfile(CONFIG_PATH):
                self._append(
                    f"  ⚠️ 未找到配置文件：{CONFIG_PATH}\n"
                    "  若你刚安装完 CLI，这属于正常情况；可以通过 OpenClaw 安装向导或 CLI 初始化生成。"
                )
            else:
                try:
                    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except json.JSONDecodeError as e:
                    self._append(f"  ❌ 配置 JSON 解析失败：{e}")
                    self._append(
                        "  建议：先备份该文件，然后在“诊断工具”点击「一键修复」，或手动修复 JSON 语法。"
                    )
                except Exception as e:
                    self._append(f"  ❌ 读取配置失败：{e}")
                else:
                    if not isinstance(data, dict):
                        self._append("  ❌ 配置根节点不是对象，这会导致 CLI 无法解析。")
                    models = data.get("models")
                    if models is None:
                        self._append("  ⚠️ 未找到 models 节点，某些功能可能受限。")
                    elif not isinstance(models, dict):
                        self._append("  ❌ models 节点不是对象，这会导致 CLI 报错。")
                    else:
                        expected_keys = {"providers"}
                        extra_keys = [k for k in models.keys() if k not in expected_keys]
                        if extra_keys:
                            self._append(
                                "  ⚠️ 在 models 下发现一些非标准键名："
                                + ", ".join(str(k) for k in extra_keys)
                            )
                            self._append(
                                "  这可能与 CLI 报“Unrecognized keys”有关。\n"
                                "  若你当前遇到相关错误，建议：\n"
                                "  - 先备份 openclaw.json；\n"
                                "  - 将这些键（例如 default / thinking）暂时移除或迁移到新格式；\n"
                                "  - 或在本界面使用「一键修复」让管家尝试重建 models.providers 结构。"
                            )
                        else:
                            self._append("  ✅ models 节点未发现明显的非标准键名。")

            self._append("\n=== 环境自检完成 ===")

        threading.Thread(target=worker, daemon=True).start()

class SettingsPanel(BasePanel):
    """设置：清除缓存、后续可扩展更新通道/备份/恢复等"""

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, app, **kwargs)
        ttk.Label(self, text="设置", font=("", 16, "bold")).pack(pady=(20, 10))
        ttk.Label(
            self,
            text="程序缓存、更新通道与配置备份等。",
            wraplength=520,
        ).pack(pady=5)

        # 清除缓存
        cache_frame = ttk.LabelFrame(self, text="程序缓存")
        cache_frame.pack(fill=tk.X, pady=(15, 10), padx=4)
        ttk.Label(
            cache_frame,
            text="清除本程序产生的日志与缓存（如 ~/.openclaw/logs、assistant-cache），不会删除 openclaw.json 或已安装技能。",
            wraplength=520,
        ).pack(anchor="w", padx=8, pady=(8, 4))
        ttk.Button(cache_frame, text="清除缓存", command=self._clear_cache).pack(
            anchor="w", padx=8, pady=(4, 8)
        )

        # 配置备份与恢复
        backup_frame = ttk.LabelFrame(self, text="配置备份与恢复")
        backup_frame.pack(fill=tk.X, pady=(5, 10), padx=4)
        ttk.Label(
            backup_frame,
            text="对 ~/.openclaw/openclaw.json 进行备份与恢复，便于在多环境/多次试验间切换。",
            wraplength=520,
        ).pack(anchor="w", padx=8, pady=(8, 4))
        btn_row = ttk.Frame(backup_frame)
        btn_row.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Button(btn_row, text="备份当前配置", command=self._backup_config).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(btn_row, text="从备份恢复", command=self._restore_config).pack(
            side=tk.LEFT
        )

        ttk.Label(
            self,
            text="其他设置（更新通道、更多备份策略等）后续开放。",
            foreground="gray",
        ).pack(pady=20)

    def _clear_cache(self):
        if not messagebox.askyesno("确认", "确定要清除程序缓存吗？将删除日志与助手缓存目录中的文件。"):
            return

        def worker():
            deleted = []
            errors = []
            for label, dir_path in [
                ("日志目录", LOGS_DIR),
                ("助手缓存", ASSISTANT_CACHE_DIR),
            ]:
                if not os.path.isdir(dir_path):
                    continue
                try:
                    for name in os.listdir(dir_path):
                        p = os.path.join(dir_path, name)
                        try:
                            if os.path.isfile(p):
                                os.remove(p)
                                deleted.append(f"{label}: {name}")
                            elif os.path.isdir(p):
                                shutil.rmtree(p, ignore_errors=True)
                                deleted.append(f"{label}: {name}/")
                        except OSError as e:
                            errors.append(f"{label} {name}: {e}")
                except OSError as e:
                    errors.append(f"{label}: {e}")

            def done():
                if errors:
                    messagebox.showwarning(
                        "清除缓存",
                        "部分清理完成。\n已删除: " + (", ".join(deleted) if deleted else "无") + "\n错误: " + "; ".join(errors),
                    )
                else:
                    msg = "已清除缓存。" if deleted else "未发现可清除的缓存文件。"
                    if deleted:
                        msg += "\n已删除: " + ", ".join(deleted[:10])
                        if len(deleted) > 10:
                            msg += f" 等共 {len(deleted)} 项"
                    messagebox.showinfo("清除缓存", msg)

            try:
                self.after(0, done)
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _backup_config(self):
        """备份 ~/.openclaw/openclaw.json 为用户选择路径的文件。"""
        if not os.path.isfile(CONFIG_PATH):
            messagebox.showerror("错误", f"未找到配置文件：\n{CONFIG_PATH}")
            return
        default_name = f"openclaw_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path = filedialog.asksaveasfilename(
            title="选择备份保存位置",
            defaultextension=".json",
            initialfile=default_name,
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
        )
        if not path:
            return
        try:
            shutil.copy2(CONFIG_PATH, path)
            messagebox.showinfo("备份成功", f"已备份配置到：\n{path}")
        except Exception as e:
            messagebox.showerror("备份失败", f"无法备份配置：\n{e}")

    def _restore_config(self):
        """从备份文件恢复 ~/.openclaw/openclaw.json（会先备份当前配置）。"""
        backup_path = filedialog.askopenfilename(
            title="选择要恢复的备份文件",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
        )
        if not backup_path:
            return
        if not messagebox.askyesno(
            "确认恢复",
            f"将使用以下文件覆盖当前配置：\n{backup_path}\n\n"
            f"当前配置（若存在）会自动备份为 .bak 文件，确认继续？",
        ):
            return

        try:
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            # 先备份当前配置
            if os.path.isfile(CONFIG_PATH):
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                bak = CONFIG_PATH + f".restore.bak.{ts}"
                shutil.copy2(CONFIG_PATH, bak)
            shutil.copy2(backup_path, CONFIG_PATH)
            messagebox.showinfo("恢复成功", f"已从备份恢复配置：\n{backup_path}")
        except Exception as e:
            messagebox.showerror("恢复失败", f"无法恢复配置：\n{e}")


class OpenClawAssistant:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("OpenClaw 龙虾管家")
        self.root.minsize(800, 550)
        self.root.geometry("900x600")
        self._install_window = None
        self._panels = {}
        self._current_panel = None
        
        # 初始化核心模块
        self._init_core_modules()
        
        self._build_ui()
    
    def _init_core_modules(self):
        """初始化核心功能模块"""
        self.instance_manager = None
        self.cost_tracker = None
        self.team_manager = None
        
        if CORE_MODULES_AVAILABLE:
            try:
                self.instance_manager = InstanceManager()
                # 先加载历史实例，再基于 openclaw.json / workspace 自动发现
                self.instance_manager.load_instances()
                try:
                    discovered = self.instance_manager.discover_instances()
                    print(f"[核心模块] 实例管理器已初始化，发现 {len(discovered)} 个实例")
                except Exception as e:
                    print(f"[核心模块] 实例自动发现失败（已忽略）：{e}")
            except Exception as e:
                print(f"[核心模块] 实例管理器初始化失败: {e}")
            
            try:
                self.cost_tracker = CostTracker()
                print("[核心模块] 成本追踪器已初始化")
            except Exception as e:
                print(f"[核心模块] 成本追踪器初始化失败: {e}")
            
            try:
                self.team_manager = TeamCollaborationManager()
                print("[核心模块] 团队协作管理器已初始化")
            except Exception as e:
                print(f"[核心模块] 团队协作管理器初始化失败: {e}")

    def _build_ui(self):
        # 顶部标题
        header = ttk.Frame(self.root)
        header.pack(fill=tk.X, padx=10, pady=8)
        ttk.Label(header, text="ButlerClaw 龙虾管家", font=("", 18, "bold")).pack(
            side=tk.LEFT
        )
        # 账号区：登录 / 已登录为 xxx · 免费版|专业版 + 退出
        self._account_frame = ttk.Frame(header)
        self._account_frame.pack(side=tk.RIGHT, padx=(0, 8))
        ttk.Button(header, text="帮助", width=6, command=self._on_help).pack(
            side=tk.RIGHT, padx=4
        )
        self._update_account_ui()

        # 主体：侧边栏 + 内容区
        main = ttk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 侧边栏
        sidebar = ttk.Frame(main, width=140)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        sidebar.pack_propagate(False)

        # 若存在新的技能面板实现（skills_panel_new.SkillsPanelNew），优先使用新面板；
        # 否则回退到内置的 SkillsPanel。
        skills_panel_cls = SkillsPanelNew or SkillsPanel
        skills_label = "技能商城" if SkillsPanelNew else "技能管理"

        nav_items = [
            ("安装", InstallPanel, "安装管理"),
            ("技能", skills_panel_cls, skills_label),
            ("版本", VersionPanel, "版本管理"),
            ("诊断", DiagnosePanel, "诊断工具"),
        ]
        # v2 核心功能面板（若可用则接入侧边栏）
        if InstancesPanel:
            nav_items.append(("实例", InstancesPanel, "实例管理"))
        if CostPanel:
            nav_items.append(("成本", CostPanel, "成本控制"))
        if TeamPanel:
            nav_items.append(("协作", TeamPanel, "团队协作"))
        # 设置固定放在末尾
        nav_items.append(("设置", SettingsPanel, "设置"))
        self._content = ttk.Frame(main)
        self._content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for key, panel_cls, label in nav_items:
            btn = ttk.Button(
                sidebar, text=label, width=14, command=lambda k=key: self._show_panel(k)
            )
            btn.pack(fill=tk.X, pady=4)
            self._panels[key] = (panel_cls, label)

        # 默认显示安装
        self._show_panel("安装")

        # 状态栏
        status = ttk.Frame(self.root)
        status.pack(fill=tk.X, padx=10, pady=6)
        self._status_var = tk.StringVar(value="就绪")
        ttk.Label(status, textvariable=self._status_var).pack(side=tk.LEFT)
        self._update_status()

    def _show_panel(self, key):
        for child in self._content.winfo_children():
            child.destroy()
        panel_cls, _ = self._panels[key]
        panel = panel_cls(self._content, self)
        panel.pack(fill=tk.BOTH, expand=True)
        self._current_panel = panel
        if hasattr(panel, "on_show"):
            panel.on_show()

    def _update_status(self):
        try:
            r = subprocess.run(
                "openclaw --version",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5,
                encoding="utf-8",
                errors="ignore",
            )
            if r.returncode == 0 and (r.stdout or "").strip():
                self._status_var.set(f"OpenClaw {(r.stdout or '').strip()}")
            else:
                self._status_var.set("OpenClaw 未安装")
        except Exception:
            self._status_var.set("OpenClaw 未安装")

    def set_status(self, text: str):
        """供子面板更新状态栏文本。"""
        if hasattr(self, "_status_var") and self._status_var is not None:
            self._status_var.set(text)

    def _on_help(self):
        messagebox.showinfo("帮助", "使用说明请参阅 README.md、开发方案_PRD.md 与 实施路线图.md")

    def _update_account_ui(self):
        """更新顶部账号区：未登录显示「登录」；已登录显示「已登录为 xxx · 免费版/专业版」+「退出」"""
        for w in self._account_frame.winfo_children():
            w.destroy()
        if not hub_auth:
            return
        if hub_auth.is_logged_in():
            user = hub_auth.get_cached_user() or {}
            level = (user.get("membershipLevel") or "free").strip()
            label = "专业版" if level == "pro" else "免费版"
            name = (user.get("username") or "用户").strip() or "用户"
            ttk.Label(self._account_frame, text=f"已登录为 {name} · {label}").pack(side=tk.LEFT, padx=(0, 8))
            ttk.Button(self._account_frame, text="退出", width=6, command=self._on_logout).pack(side=tk.LEFT)
        else:
            ttk.Button(self._account_frame, text="登录 ButlerClaw", width=14, command=self._on_login).pack(side=tk.LEFT)

    def _on_login(self):
        """打开登录对话框，成功则刷新账号区并可选刷新当前面板"""
        if not hub_auth or not hub_auth.is_hub_configured():
            messagebox.showwarning("登录", "未配置 Hub 地址，无法登录。请在 openclaw.json 中设置 hubBaseUrl 或设置环境变量 BUTLERCLAW_HUB_URL。")
            return
        self._show_login_dialog()

    def _show_login_dialog(self):
        """弹出登录窗口：邮箱、密码，调用 hub_auth.login，成功则关闭并刷新 UI"""
        dlg = tk.Toplevel(self.root)
        dlg.title("登录 ButlerClaw 账号")
        dlg.transient(self.root)
        dlg.resizable(False, False)
        frame = ttk.Frame(dlg, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="邮箱").grid(row=0, column=0, sticky=tk.W, pady=(0, 4))
        email_var = tk.StringVar()
        email_entry = ttk.Entry(frame, textvariable=email_var, width=28)
        email_entry.grid(row=1, column=0, sticky=tk.EW, pady=(0, 12))
        ttk.Label(frame, text="密码").grid(row=2, column=0, sticky=tk.W, pady=(0, 4))
        pwd_var = tk.StringVar()
        pwd_entry = ttk.Entry(frame, textvariable=pwd_var, show="*", width=28)
        pwd_entry.grid(row=3, column=0, sticky=tk.EW, pady=(0, 16))
        frame.columnconfigure(0, weight=1)
        msg_var = tk.StringVar()

        def do_login():
            email = email_var.get().strip()
            pwd = pwd_var.get()
            if not email:
                messagebox.showwarning("登录", "请输入邮箱", parent=dlg)
                return
            if not pwd:
                messagebox.showwarning("登录", "请输入密码", parent=dlg)
                return
            msg_var.set("登录中…")
            dlg.update_idletasks()
            ok, err = hub_auth.login(email, pwd)
            if ok:
                dlg.destroy()
                self._update_account_ui()
                if self._current_panel and hasattr(self._current_panel, "_refresh"):
                    self._current_panel._refresh()
                messagebox.showinfo("登录", "登录成功")
            else:
                msg_var.set("")
                messagebox.showerror("登录失败", err or "请检查邮箱和密码", parent=dlg)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, sticky=tk.EW, pady=(0, 0))
        ttk.Button(btn_frame, text="登录", width=10, command=do_login).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="取消", width=10, command=dlg.destroy).pack(side=tk.LEFT)
        dlg.geometry("320x220")
        dlg.grab_set()
        email_entry.focus_set()

    def _on_logout(self):
        """退出登录，清除本地登录态并刷新账号区"""
        if hub_auth:
            hub_auth.logout()
        self._update_account_ui()
        if self._current_panel and hasattr(self._current_panel, "_refresh"):
            self._current_panel._refresh()

    def run(self):
        self.root.mainloop()


def main():
    app = OpenClawAssistant()
    app.run()


if __name__ == "__main__":
    main()
