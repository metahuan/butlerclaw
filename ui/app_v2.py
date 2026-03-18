# -*- coding: utf-8 -*-
"""
Butlerclaw v2.0 - 主应用入口 (ttkbootstrap 现代化版本)

采用混合架构:
- 框架: ttkbootstrap (现代化 tkinter)
- 复杂组件: WebView2 嵌入
"""

import os
import sys
import json
import threading
import webbrowser
from datetime import datetime
from typing import Optional, Dict, Any, Callable

# ttkbootstrap - tkinter 现代化封装
try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    from ttkbootstrap.style import Style
    TTKBOOTSTRAP_AVAILABLE = True
except ImportError:
    import tkinter as ttk
    from tkinter import ttk as ttk_module
    TTKBOOTSTRAP_AVAILABLE = False

# WebView 支持
try:
    import webview
    WEBVIEW_AVAILABLE = True
except ImportError:
    WEBVIEW_AVAILABLE = False

# 导入面板
from panels.install_panel import InstallPanel
from panels.skills_panel import SkillsPanel
from panels.version_panel import VersionPanel
from panels.diagnose_panel import DiagnosePanel
from panels.settings_panel import SettingsPanel
from panels.instances_panel import InstancesPanel  # 新增
from panels.cost_panel import CostPanel            # 新增
from panels.team_panel import TeamPanel            # 新增

# 配置路径
CONFIG_DIR = os.path.expanduser("~/.openclaw")
CONFIG_PATH = os.path.join(CONFIG_DIR, "openclaw.json")


class ThemeManager:
    """主题管理器 - 支持亮/暗/自动模式"""
    
    THEMES = {
        "light": {
            "name": "亮色",
            "ttk_theme": "litera" if TTKBOOTSTRAP_AVAILABLE else "clam",
            "primary": "#3B82F6",
            "success": "#10B981",
            "warning": "#F59E0B",
            "error": "#EF4444",
            "bg": "#FFFFFF",
            "surface": "#F9FAFB",
            "border": "#E5E7EB",
            "text": "#111827",
            "text_secondary": "#6B7280",
        },
        "dark": {
            "name": "暗色",
            "ttk_theme": "darkly" if TTKBOOTSTRAP_AVAILABLE else "clam",
            "primary": "#60A5FA",
            "success": "#34D399",
            "warning": "#FBBF24",
            "error": "#F87171",
            "bg": "#111827",
            "surface": "#1F2937",
            "border": "#374151",
            "text": "#F9FAFB",
            "text_secondary": "#9CA3AF",
        }
    }
    
    def __init__(self):
        self.current_theme = self._load_theme_preference()
    
    def _load_theme_preference(self) -> str:
        """加载用户主题偏好"""
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    theme = config.get('ui', {}).get('theme', 'auto')
                    if theme in ['light', 'dark']:
                        return theme
                    # auto: 检测系统主题
                    return self._detect_system_theme()
        except Exception:
            pass
        return 'light'
    
    def _detect_system_theme(self) -> str:
        """检测系统主题 (Windows/macOS/Linux)"""
        import platform
        
        system = platform.system()
        try:
            if system == 'Windows':
                # Windows: 检查注册表
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
                    value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                    return 'light' if value == 1 else 'dark'
            elif system == 'Darwin':
                # macOS: defaults read
                import subprocess
                result = subprocess.run(
                    ['defaults', 'read', '-g', 'AppleInterfaceStyle'],
                    capture_output=True, text=True
                )
                return 'dark' if 'Dark' in result.stdout else 'light'
            else:
                # Linux: 尝试检测 GTK 主题
                import subprocess
                result = subprocess.run(
                    ['gsettings', 'get', 'org.gnome.desktop.interface', 'gtk-theme'],
                    capture_output=True, text=True
                )
                return 'dark' if 'dark' in result.stdout.lower() else 'light'
        except Exception:
            return 'light'
    
    def get_theme(self) -> Dict[str, Any]:
        """获取当前主题配置"""
        return self.THEMES.get(self.current_theme, self.THEMES['light'])
    
    def apply_theme(self, window):
        """应用主题到窗口"""
        theme = self.get_theme()
        
        if TTKBOOTSTRAP_AVAILABLE:
            style = Style(theme=theme['ttk_theme'])
        else:
            style = ttk.Style()
        
        # 配置全局样式
        window.configure(bg=theme['bg'])
        
        return style
    
    def toggle_theme(self):
        """切换主题"""
        self.current_theme = 'dark' if self.current_theme == 'light' else 'light'
        self._save_theme_preference()
        return self.current_theme
    
    def _save_theme_preference(self):
        """保存主题偏好"""
        try:
            config = {}
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            if 'ui' not in config:
                config['ui'] = {}
            config['ui']['theme'] = self.current_theme
            
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存主题偏好失败: {e}")


class Sidebar(ttk.Frame):
    """现代化侧边栏组件"""
    
    NAV_ITEMS = [
        ("install", "📦", "安装管理"),
        ("skills", "🛠️", "技能商城"),
        ("version", "🔄", "版本管理"),
        ("diagnose", "🏥", "健康诊断"),
        ("instances", "🖥️", "实例管理"),  # 新增
        ("cost", "💰", "成本控制"),       # 新增
        ("team", "👥", "团队协作"),       # 新增
        ("settings", "⚙️", "设置"),
    ]
    
    def __init__(self, parent, on_select: Callable, theme_manager: ThemeManager, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_select = on_select
        self.theme_manager = theme_manager
        self.current_key = "install"
        self.buttons = {}
        
        self._build_ui()
    
    def _build_ui(self):
        theme = self.theme_manager.get_theme()
        
        # Logo 区域
        logo_frame = ttk.Frame(self, padding=15)
        logo_frame.pack(fill=X)
        
        ttk.Label(
            logo_frame, 
            text="🦞 Butlerclaw",
            font=("Microsoft YaHei", 14, "bold")
        ).pack()
        
        ttk.Separator(self).pack(fill=X, padx=10, pady=5)
        
        # 导航按钮
        nav_frame = ttk.Frame(self)
        nav_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        for key, icon, label in self.NAV_ITEMS:
            btn = ttk.Button(
                nav_frame,
                text=f"{icon}  {label}",
                command=lambda k=key: self._on_select(k),
                bootstyle="primary-outline" if TTKBOOTSTRAP_AVAILABLE else None,
                width=20
            )
            btn.pack(fill=X, pady=2)
            self.buttons[key] = btn
        
        # 更新选中状态
        self._update_active_button()
        
        # 底部主题切换
        ttk.Separator(self).pack(fill=X, padx=10, pady=5)
        
        bottom_frame = ttk.Frame(self, padding=10)
        bottom_frame.pack(fill=X)
        
        self.theme_btn = ttk.Button(
            bottom_frame,
            text="🌙 暗色" if self.theme_manager.current_theme == 'light' else "☀️ 亮色",
            command=self._toggle_theme,
            bootstyle="secondary" if TTKBOOTSTRAP_AVAILABLE else None
        )
        self.theme_btn.pack(fill=X)
    
    def _on_select(self, key: str):
        self.current_key = key
        self._update_active_button()
        self.on_select(key)
    
    def _update_active_button(self):
        """更新按钮选中状态"""
        for key, btn in self.buttons.items():
            if key == self.current_key:
                if TTKBOOTSTRAP_AVAILABLE:
                    btn.configure(bootstyle="primary")
                else:
                    btn.configure(style="Active.TButton")
            else:
                if TTKBOOTSTRAP_AVAILABLE:
                    btn.configure(bootstyle="primary-outline")
                else:
                    btn.configure(style="TButton")
    
    def _toggle_theme(self):
        new_theme = self.theme_manager.toggle_theme()
        self.theme_btn.configure(
            text="🌙 暗色" if new_theme == 'light' else "☀️ 亮色"
        )
        # 通知主窗口刷新主题
        self.event_generate("<<ThemeChanged>>")


class ButlerclawApp:
    """Butlerclaw 主应用"""
    
    PANEL_CLASSES = {
        "install": InstallPanel,
        "skills": SkillsPanel,
        "version": VersionPanel,
        "diagnose": DiagnosePanel,
        "instances": InstancesPanel,
        "cost": CostPanel,
        "team": TeamPanel,
        "settings": SettingsPanel,
    }
    
    def __init__(self):
        # 初始化主题管理器
        self.theme_manager = ThemeManager()
        
        # 创建主窗口
        if TTKBOOTSTRAP_AVAILABLE:
            self.root = ttk.Window(
                title="Butlerclaw v2.0 - 龙虾管家",
                themename=self.theme_manager.get_theme()['ttk_theme'],
                size=(1200, 800),
                minsize=(900, 600)
            )
        else:
            self.root = ttk.Tk()
            self.root.title("Butlerclaw v2.0 - 龙虾管家")
            self.root.geometry("1200x800")
            self.root.minsize(900, 600)
        
        # 应用主题
        self.theme_manager.apply_theme(self.root)
        
        # 绑定主题切换事件
        self.root.bind("<<ThemeChanged>>", self._on_theme_changed)
        
        # 当前面板
        self.current_panel = None
        self.current_panel_key = None
        
        # 构建 UI
        self._build_ui()
        
        # 默认显示安装面板
        self._show_panel("install")
    
    def _build_ui(self):
        """构建主界面"""
        # 主容器
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=BOTH, expand=True)
        
        # 侧边栏
        self.sidebar = Sidebar(
            self.main_frame,
            on_select=self._show_panel,
            theme_manager=self.theme_manager,
            width=200
        )
        self.sidebar.pack(side=LEFT, fill=Y)
        
        # 分隔线
        ttk.Separator(self.main_frame, orient=VERTICAL).pack(side=LEFT, fill=Y)
        
        # 内容区域
        self.content_frame = ttk.Frame(self.main_frame, padding=15)
        self.content_frame.pack(side=LEFT, fill=BOTH, expand=True)
        
        # 状态栏
        self.status_bar = ttk.Frame(self.root, relief=SUNKEN, padding=5)
        self.status_bar.pack(side=BOTTOM, fill=X)
        
        self.status_label = ttk.Label(self.status_bar, text="就绪")
        self.status_label.pack(side=LEFT)
        
        self.version_label = ttk.Label(self.status_bar, text="")
        self.version_label.pack(side=RIGHT)
        
        # 加载版本信息
        self._load_version()
    
    def _show_panel(self, key: str):
        """显示指定面板"""
        if self.current_panel_key == key:
            return
        
        # 清除当前面板
        if self.current_panel:
            self.current_panel.destroy()
        
        # 创建新面板
        panel_class = self.PANEL_CLASSES.get(key)
        if panel_class:
            self.current_panel = panel_class(
                self.content_frame,
                app=self,
                theme_manager=self.theme_manager
            )
            self.current_panel.pack(fill=BOTH, expand=True)
            self.current_panel_key = key
            
            # 触发面板显示事件
            if hasattr(self.current_panel, 'on_show'):
                self.current_panel.on_show()
    
    def _on_theme_changed(self, event=None):
        """主题切换回调"""
        # 重新应用主题
        self.theme_manager.apply_theme(self.root)
        
        # 刷新当前面板
        if self.current_panel:
            self._show_panel(self.current_panel_key)
    
    def _load_version(self):
        """加载 OpenClaw 版本信息"""
        def worker():
            try:
                import subprocess
                result = subprocess.run(
                    "openclaw --version",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=5,
                    encoding="utf-8",
                    errors="ignore"
                )
                if result.returncode == 0:
                    version = result.stdout.strip()
                    self.root.after(0, lambda: self.version_label.config(text=f"OpenClaw {version}"))
                else:
                    self.root.after(0, lambda: self.version_label.config(text="OpenClaw 未安装"))
            except Exception:
                self.root.after(0, lambda: self.version_label.config(text="OpenClaw 未安装"))
        
        threading.Thread(target=worker, daemon=True).start()
    
    def set_status(self, message: str):
        """设置状态栏消息"""
        self.status_label.config(text=message)
    
    def run(self):
        """运行应用"""
        self.root.mainloop()


def main():
    """入口函数"""
    app = ButlerclawApp()
    app.run()


if __name__ == "__main__":
    main()
