#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw Windows 自动安装程序 v2.0
修复版本 - 解决测试报告中的问题

修复内容：
1. 添加网络下载重试机制
2. 修复 Node.js 环境变量问题
3. 添加临时文件清理
4. 添加安装进度条
5. 添加日志保存功能
6. API Key 安全提示
"""

import os
import sys
import json
import subprocess
import threading
import urllib.request
import tempfile
import shutil
import time
from datetime import datetime

# 检查是否有 tkinter
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext, filedialog
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
    print("错误：需要安装 tkinter。请运行: pip install tk")
    sys.exit(1)

# 配置
NODEJS_VERSION = "20.11.0"
MAX_RETRIES = 3

# API Key 环境变量前缀
API_KEY_ENV_PREFIX = "OPENCLAW_API_KEY"

def get_api_key_env_var_name(provider: str) -> str:
    """获取 provider 对应的环境变量名称"""
    return f"{API_KEY_ENV_PREFIX}_{provider.upper().replace('-', '_')}"

def get_api_key_from_env(provider: str) -> str:
    """从环境变量获取 API Key"""
    env_var = get_api_key_env_var_name(provider)
    return os.getenv(env_var, "")

def set_api_key_to_env(provider: str, api_key: str, permanent: bool = False):
    """
    设置 API Key 到环境变量
    permanent: 是否永久设置（Windows 下会设置用户环境变量）
    """
    env_var = get_api_key_env_var_name(provider)
    os.environ[env_var] = api_key
    
    if permanent and sys.platform == "win32":
        try:
            subprocess.run(
                f'[Environment]::SetEnvironmentVariable("{env_var}", "{api_key}", "User")',
                shell=True, capture_output=True, timeout=10
            )
        except Exception:
            pass  # 静默失败，不影响当前进程

def get_api_key_secure(provider: str, config: dict = None) -> str:
    """
    安全获取 API Key，优先级：
    1. 环境变量
    2. 配置文件（向后兼容）
    """
    # 1. 优先从环境变量读取
    env_key = get_api_key_from_env(provider)
    if env_key:
        return env_key
    
    # 2. 从配置文件读取（向后兼容）
    if config:
        providers = (config.get("models") or {}).get("providers") or {}
        provider_config = providers.get(provider, {})
        return provider_config.get("apiKey", "")
    
    return ""

# 模型选项
MODELS = {
    "国产模型": {
        "moonshot/kimi-k2.5": "Kimi K2.5 (Moonshot) - 长上下文，中文优秀",
        "deepseek/deepseek-chat": "DeepSeek V3 - 推理能力强，性价比高",
        "deepseek/deepseek-reasoner": "DeepSeek R1 - 推理模型，适合复杂任务",
        "alibaba/qwen-2.5-72b": "Qwen 2.5 (阿里) - 多语言能力强"
    },
    "国际模型": {
        "openai/gpt-4o": "GPT-4o (OpenAI) - 综合能力最强",
        "anthropic/claude-3.5-sonnet": "Claude 3.5 Sonnet - 代码能力强",
        "google/gemini-2.0-flash": "Gemini 2.0 Flash (Google) - 多模态能力强"
    }
}

API_KEY_HINTS = {
    "moonshot": "https://platform.moonshot.cn 获取 API Key",
    "deepseek": "https://platform.deepseek.com 获取 API Key",
    "alibaba": "https://dashscope.aliyun.com 获取 API Key",
    "openai": "https://platform.openai.com 获取 API Key",
    "anthropic": "https://console.anthropic.com 获取 API Key",
    "google": "https://aistudio.google.com 获取 API Key"
}

# 国内 IM 平台配置模板
CHANNELS_CONFIG = {
    "qqbot": {
        "name": "QQ 频道机器人",
        "icon": "💬",
        "fields": [
            {"key": "app_id", "label": "AppID", "type": "text", "required": True, "hint": "在 QQ 频道开放平台获取"},
            {"key": "app_secret", "label": "AppSecret", "type": "password", "required": True, "hint": ""},
            {"key": "bot_token", "label": "Bot Token", "type": "text", "required": True, "hint": "机器人令牌"},
            {"key": "webhook_path", "label": "Webhook 路径", "type": "text", "required": False, "default": "/qqbot/webhook", "hint": ""}
        ],
        "docs_url": "https://bot.q.qq.com/"
    },
    "wecom": {
        "name": "企业微信",
        "icon": "🏢",
        "fields": [
            {"key": "corp_id", "label": "CorpID", "type": "text", "required": True, "hint": "在企业微信管理后台获取"},
            {"key": "agent_id", "label": "AgentID", "type": "text", "required": True, "hint": "应用的 AgentID"},
            {"key": "secret", "label": "Secret", "type": "password", "required": True, "hint": "应用的 Secret"},
            {"key": "token", "label": "Token", "type": "text", "required": True, "hint": "回调配置中的 Token"},
            {"key": "encoding_aes_key", "label": "EncodingAESKey", "type": "text", "required": False, "hint": "消息加解密密钥（可选）"},
            {"key": "webhook_path", "label": "Webhook 路径", "type": "text", "required": False, "default": "/wecom/webhook", "hint": ""}
        ],
        "docs_url": "https://developer.work.weixin.qq.com/"
    },
    "dingtalk": {
        "name": "钉钉",
        "icon": "📱",
        "fields": [
            {"key": "app_key", "label": "AppKey", "type": "text", "required": True, "hint": "在钉钉开放平台获取"},
            {"key": "app_secret", "label": "AppSecret", "type": "password", "required": True, "hint": ""},
            {"key": "robot_code", "label": "RobotCode", "type": "text", "required": False, "hint": "机器人编码（可选）"},
            {"key": "webhook_path", "label": "Webhook 路径", "type": "text", "required": False, "default": "/dingtalk/webhook", "hint": ""}
        ],
        "docs_url": "https://open.dingtalk.com/"
    },
    "feishu": {
        "name": "飞书",
        "icon": "🚀",
        "fields": [
            {"key": "app_id", "label": "AppID", "type": "text", "required": True, "hint": "在飞书开放平台获取"},
            {"key": "app_secret", "label": "AppSecret", "type": "password", "required": True, "hint": ""},
            {"key": "encrypt_key", "label": "Encrypt Key", "type": "text", "required": False, "hint": "事件订阅加密密钥（可选）"},
            {"key": "verification_token", "label": "Verification Token", "type": "text", "required": False, "hint": "验证令牌（可选）"},
            {"key": "webhook_path", "label": "Webhook 路径", "type": "text", "required": False, "default": "/feishu/webhook", "hint": ""}
        ],
        "docs_url": "https://open.feishu.cn/"
    }
}


class Logger:
    """日志记录器（支持从子线程安全写入 GUI）"""
    def __init__(self, text_widget=None, log_file=None, root=None):
        self.text_widget = text_widget
        self.log_file = log_file
        self.root = root  # 用于 root.after 在主线程更新 GUI

    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}"

        if self.text_widget and self.root:
            def _update():
                self.text_widget.insert(tk.END, f"{message}\n")
                self.text_widget.see(tk.END)
            self.root.after(0, _update)
        elif self.text_widget:
            self.text_widget.insert(tk.END, f"{message}\n")
            self.text_widget.see(tk.END)

        if self.log_file:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(log_line + "\n")
            except OSError:
                pass
                
    def error(self, message):
        self.log(f"[ERROR] {message}")
        
    def info(self, message):
        self.log(f"[INFO] {message}")
        
    def success(self, message):
        self.log(f"[OK] {message}")


class OpenClawInstaller:
    def __init__(self, root, config_only=False, dialog_parent=None):
        self.root = root
        self.config_only = config_only
        self.dialog_parent = dialog_parent  # 仅配置模型时，配置对话框挂在此父窗口下，避免关闭时卡死
        self.root.title("OpenClaw 自动安装程序 v2.0")
        self.root.geometry("750x650")
        self.root.resizable(True, True)
        
        self.center_window()
        
        self.install_dir = os.path.expanduser("~/.openclaw")
        self.node_installed = False
        self.openclaw_installed = False
        self.installer_path = None
        
        # 初始化日志
        log_dir = os.path.expanduser("~/.openclaw/logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"install_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        self.setup_ui()
        self.logger = Logger(self.log_text, log_file, self.root)
        self.logger.info(f"日志文件: {log_file}")
        if config_only:
            self.root.withdraw()  # 仅配置模型时不显示安装器主窗口，只显示配置对话框
            self.root.after(200, self.show_config_dialog)
        
    def center_window(self):
        self.root.update_idletasks()
        width = 750
        height = 650
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
    def setup_ui(self):
        # 标题
        title = tk.Label(self.root, text="OpenClaw 自动安装程序 v2.0", 
                        font=("Microsoft YaHei", 18, "bold"))
        title.pack(pady=15)
        
        subtitle = tk.Label(self.root, text="修复版 - 更稳定、更安全", 
                           font=("Microsoft YaHei", 10), fg="gray")
        subtitle.pack()
        
        # 步骤框架
        self.steps_frame = tk.LabelFrame(self.root, text="安装进度", 
                                        font=("Microsoft YaHei", 11))
        self.steps_frame.pack(fill=tk.X, padx=30, pady=10)
        
        self.step1_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self.steps_frame, text="步骤 1: 检查/安装 Node.js", 
                      variable=self.step1_var, state=tk.DISABLED,
                      font=("Microsoft YaHei", 10)).pack(anchor=tk.W, padx=10, pady=3)
        
        self.step2_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self.steps_frame, text="步骤 2: 安装 OpenClaw", 
                      variable=self.step2_var, state=tk.DISABLED,
                      font=("Microsoft YaHei", 10)).pack(anchor=tk.W, padx=10, pady=3)
        
        self.step3_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self.steps_frame, text="步骤 3: 配置模型和 API Key", 
                      variable=self.step3_var, state=tk.DISABLED,
                      font=("Microsoft YaHei", 10)).pack(anchor=tk.W, padx=10, pady=3)
        
        # 进度条
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress_var, 
                                           maximum=100, length=400)
        self.progress_bar.pack(fill=tk.X, padx=30, pady=5)
        
        self.progress_label = tk.Label(self.root, text="准备就绪", font=("Microsoft YaHei", 9))
        self.progress_label.pack()
        
        # 日志区域
        log_frame = tk.LabelFrame(self.root, text="安装日志", font=("Microsoft YaHei", 10))
        log_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, width=80,
                                                  font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 按钮区域
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=30, pady=15)
        
        self.start_btn = tk.Button(btn_frame, text="开始安装", 
                                   command=self.start_install,
                                   font=("Microsoft YaHei", 11),
                                   bg="#4CAF50", fg="white",
                                   width=15, height=2)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.config_btn = tk.Button(btn_frame, text="仅配置模型", 
                                    command=self.show_config_dialog,
                                    font=("Microsoft YaHei", 11),
                                    bg="#2196F3", fg="white",
                                    width=15, height=2)
        self.config_btn.pack(side=tk.LEFT, padx=5)
        
        self.channels_btn = tk.Button(btn_frame, text="通道 (Channels)配置", 
                                      command=self.show_channels_dialog,
                                      font=("Microsoft YaHei", 11),
                                      bg="#9C27B0", fg="white",
                                      width=18, height=2)
        self.channels_btn.pack(side=tk.LEFT, padx=5)
        
        self.save_log_btn = tk.Button(btn_frame, text="保存日志", 
                                      command=self.save_log,
                                      font=("Microsoft YaHei", 11),
                                      width=12, height=2)
        self.save_log_btn.pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="退出", command=self.root.quit,
                 font=("Microsoft YaHei", 11), width=10, height=2).pack(side=tk.RIGHT, padx=5)
        
    def update_progress(self, value, message=""):
        """可在子线程中调用，通过 after 在主线程更新 GUI"""
        def _update():
            self.progress_var.set(value)
            if message:
                self.progress_label.config(text=message)
        self.root.after(0, _update)
        
    def log(self, message):
        if hasattr(self, 'logger'):
            self.logger.log(message)
        else:
            self.log_text.insert(tk.END, f"{message}\n")
            self.log_text.see(tk.END)
            self.log_text.update()
        
    def save_log(self):
        log_content = self.log_text.get("1.0", tk.END)
        if not log_content.strip():
            messagebox.showwarning("警告", "日志为空")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("日志文件", "*.log"), ("文本文件", "*.txt")],
            initialfile=f"openclaw_install_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                messagebox.showinfo("保存成功", f"日志已保存到:\n{file_path}")
            except Exception as e:
                messagebox.showerror("保存失败", str(e))
                
    def download_with_retry(self, url, path, max_retries=3):
        for attempt in range(max_retries):
            try:
                self.log(f"下载尝试 {attempt + 1}/{max_retries}...")
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
                })
                with urllib.request.urlopen(req, timeout=60) as response:
                    with open(path, 'wb') as f:
                        shutil.copyfileobj(response, f)
                self.logger.success(f"下载成功: {path}")
                return True
            except Exception as e:
                self.logger.error(f"下载失败 (尝试 {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    self.log(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"下载失败，已重试 {max_retries} 次: {e}")
                    
    def check_nodejs(self):
        self.logger.info("=== 检查 Node.js ===")
        self.update_progress(5, "检查 Node.js...")
        
        node_paths = [
            "node",
            r"C:\Program Files\nodejs\node.exe",
            r"C:\Program Files (x86)\nodejs\node.exe",
        ]
        
        for node_cmd in node_paths:
            try:
                cmd = f'"{node_cmd}" --version' if ' ' in node_cmd else f"{node_cmd} --version"
                result = subprocess.run(cmd, shell=True, capture_output=True,
                                        text=True, encoding='utf-8', errors='ignore', timeout=10)
                if result.returncode == 0:
                    version = result.stdout.strip()
                    self.logger.success(f"Node.js 已安装: {version}")
                    self.node_installed = True
                    self.update_progress(15, "Node.js 已安装")
                    return True
            except:
                continue
                
        self.logger.info("Node.js 未安装，需要安装")
        return False
        
    def install_nodejs(self):
        self.logger.info("=== 安装 Node.js ===")
        self.update_progress(20, "正在下载 Node.js...")
        
        node_url = f"https://nodejs.org/dist/v{NODEJS_VERSION}/node-v{NODEJS_VERSION}-x64.msi"
        self.installer_path = os.path.join(tempfile.gettempdir(), f"nodejs_installer_{int(time.time())}.msi")
        
        try:
            self.download_with_retry(node_url, self.installer_path, MAX_RETRIES)
            self.update_progress(35, "下载完成，正在安装...")
        except Exception as e:
            self.logger.error(f"下载失败: {e}")
            msg = f"无法下载 Node.js，请手动安装:\nhttps://nodejs.org\n\n错误: {e}"
            self.root.after(0, lambda: messagebox.showerror("下载失败", msg))
            return False
            
        try:
            result = subprocess.run(
                f'msiexec /i "{self.installer_path}" /passive /norestart',
                shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300
            )
            
            if result.returncode not in [0, 3010]:
                raise Exception(f"安装程序返回错误码: {result.returncode}")
                
            self.logger.success("Node.js 安装完成")
            self.update_progress(45, "Node.js 安装完成")
            
            # 更新环境变量（当前进程立即生效；setx 对新终端生效，注意 Windows setx 有约 1024 字符限制）
            self.logger.info("更新环境变量...")
            node_path = r"C:\Program Files\nodejs"
            current_path = os.environ.get('PATH', '')
            if node_path not in current_path:
                os.environ['PATH'] = node_path + ';' + current_path
            subprocess.run(f'setx PATH "{node_path};%PATH%"', shell=True, check=False)
            
            time.sleep(2)
            
            # 验证安装
            self.logger.info("验证 Node.js 安装...")
            result = subprocess.run(f'"{node_path}\\node.exe" --version',
                                   shell=True, capture_output=True,
                                   text=True, encoding='utf-8', errors='ignore', timeout=10)
            if result.returncode == 0:
                version = result.stdout.strip()
                self.logger.success(f"Node.js 安装成功: {version}")
                self.node_installed = True
                self.update_progress(50, "Node.js 安装成功")
                return True
            else:
                raise Exception("验证失败")
                
        except Exception as e:
            self.logger.error(f"安装失败: {e}")
            msg = (f"Node.js 安装失败。\n\n建议:\n1. 以管理员身份运行此程序\n"
                   f"2. 或手动安装: https://nodejs.org\n\n错误: {e}")
            self.root.after(0, lambda: messagebox.showerror("安装失败", msg))
            return False
        finally:
            self.cleanup_temp_files()
            
    def cleanup_temp_files(self):
        if self.installer_path and os.path.exists(self.installer_path):
            try:
                os.remove(self.installer_path)
                self.logger.info(f"清理临时文件: {self.installer_path}")
            except Exception as e:
                self.logger.error(f"清理临时文件失败: {e}")

    def _get_openclaw_candidates_win(self):
        """Windows 下可能存在的 openclaw 可执行路径（不依赖 PATH）"""
        candidates = []
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            candidates.append(os.path.join(appdata, "npm", "openclaw.cmd"))
            candidates.append(os.path.join(appdata, "npm", "openclaw"))
        for pf in (os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", "")):
            if pf:
                candidates.append(os.path.join(pf, "nodejs", "openclaw.cmd"))
                candidates.append(os.path.join(pf, "nodejs", "openclaw"))
        return [p for p in candidates if p]

    def check_openclaw(self):
        """检查 OpenClaw 是否已安装（先查 PATH，再查 Windows 常见安装路径）"""
        self.logger.info("=== 检查 OpenClaw ===")
        self.update_progress(55, "检查 OpenClaw...")

        def try_run(cmd, **kwargs):
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=10, **kwargs)
                if r.returncode == 0 and (r.stdout or "").strip():
                    return (r.stdout or "").strip()
            except Exception:
                pass
            return None

        # 1) 先按当前 PATH 尝试（用户已配置好 PATH 时有效）
        version = try_run("openclaw --version", shell=True)
        if version:
            self.logger.success(f"OpenClaw 已安装: {version}，跳过安装")
            self.openclaw_installed = True
            self.update_progress(95, "OpenClaw 已存在，跳过安装")
            return True

        # 2) Windows：在常见路径下显式查找（解决双击 .bat 时 PATH 里没有 npm 目录的问题）
        for path in self._get_openclaw_candidates_win():
            if not os.path.isfile(path):
                continue
            self.logger.info(f"尝试路径: {path}")
            # .cmd 必须用 shell=True 执行；其它用列表或带引号的命令
            version = try_run(f'"{path}" --version', shell=True)
            if version:
                self.logger.success(f"OpenClaw 已安装: {version}，跳过安装")
                self.openclaw_installed = True
                self.update_progress(95, "OpenClaw 已存在，跳过安装")
                return True

        # 3) 用 npm list -g 判断是否已安装（不依赖 openclaw 是否在 PATH）
        try:
            r = subprocess.run(
                "npm list -g openclaw --depth=0",
                shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=15
            )
            if r.returncode == 0 and "openclaw" in (r.stdout or ""):
                self.logger.success("OpenClaw 已通过 npm 全局安装，跳过安装")
                self.openclaw_installed = True
                self.update_progress(95, "OpenClaw 已存在，跳过安装")
                return True
        except Exception:
            pass

        self.logger.info("OpenClaw 未安装，需要安装")
        return False

    def _parse_version(self, s):
        """将版本字符串转为可比较的元组，如 '2026.3.2' -> (2026, 3, 2)。"""
        if not s:
            return (0, 0, 0)
        s = str(s).strip().lstrip("v")
        parts = []
        for x in s.replace("-", ".").split("."):
            try:
                parts.append(int(x))
            except ValueError:
                parts.append(0)
        return tuple(parts) if parts else (0, 0, 0)

    def _get_current_openclaw_version(self):
        """获取当前已安装的 openclaw 版本号字符串，未安装或失败返回 None。"""
        try:
            r = subprocess.run(
                "openclaw --version",
                shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=10
            )
            if r.returncode == 0 and (r.stdout or "").strip():
                return (r.stdout or "").strip()
        except Exception:
            pass
        for path in self._get_openclaw_candidates_win():
            if not os.path.isfile(path):
                continue
            try:
                r = subprocess.run(f'"{path}" --version', shell=True, capture_output=True,
                                   text=True, encoding="utf-8", errors="ignore", timeout=10)
                if r.returncode == 0 and (r.stdout or "").strip():
                    return (r.stdout or "").strip()
            except Exception:
                pass
        return None

    def _get_latest_openclaw_version(self):
        """从 npm 获取最新版本号字符串，失败返回 None。"""
        try:
            r = subprocess.run(
                "npm view openclaw version",
                shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=15
            )
            if r.returncode == 0 and (r.stdout or "").strip():
                return (r.stdout or "").strip()
        except Exception:
            pass
        return None

    def update_openclaw_if_needed(self):
        """若已安装但版本落后，则更新到最新。返回 True 表示无需更新或更新成功。"""
        self.logger.info("=== 检查 OpenClaw 版本 ===")
        current = self._get_current_openclaw_version()
        latest = self._get_latest_openclaw_version()
        if not current:
            return True
        if not latest:
            self.logger.info("无法获取最新版本，跳过更新检查")
            return True
        cur_t = self._parse_version(current)
        lat_t = self._parse_version(latest)
        if cur_t >= lat_t:
            self.logger.success(f"OpenClaw 已是最新: {current}")
            return True
        self.logger.info(f"当前 {current}，最新 {latest}，正在更新...")
        self.update_progress(70, "正在更新 OpenClaw...")
        try:
            r = subprocess.run(
                "npm install -g openclaw@latest",
                shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=300
            )
            if r.returncode != 0:
                self.logger.error(f"更新失败: {r.stderr}")
                return False
            self.logger.success("OpenClaw 已更新到最新")
            return True
        except Exception as e:
            self.logger.error(f"更新异常: {e}")
            return False

    def is_model_configured(self):
        """检测 openclaw.json 中是否已配置模型（models.providers 下至少有一个 apiKey）。"""
        config_path = os.path.join(os.path.expanduser("~/.openclaw"), "openclaw.json")
        if not os.path.isfile(config_path):
            return False
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            providers = (data.get("models") or {}).get("providers") or {}
            for prov, cfg in providers.items():
                if isinstance(cfg, dict) and (cfg.get("apiKey") or "").strip():
                    return True
            return False
        except Exception:
            return False

    def install_openclaw(self):
        self.logger.info("=== 安装 OpenClaw ===")
        self.update_progress(60, "正在安装 OpenClaw...")
        
        try:
            result = subprocess.run("npm install -g openclaw@latest",
                                   shell=True, capture_output=True,
                                   text=True, encoding='utf-8', errors='ignore', timeout=300)
            
            if result.returncode != 0:
                raise Exception(result.stderr)
                
            self.logger.success("OpenClaw 安装成功")
            self.update_progress(85, "OpenClaw 安装成功")
            
            # 验证安装
            result = subprocess.run("openclaw --version", shell=True, capture_output=True,
                                    text=True, encoding='utf-8', errors='ignore', timeout=10)
            if result.returncode == 0:
                version = result.stdout.strip()
                self.logger.success(f"OpenClaw 版本: {version}")
                self.openclaw_installed = True
                self.update_progress(95, "OpenClaw 安装完成")
                return True
            else:
                raise Exception("验证失败")
                
        except subprocess.TimeoutExpired:
            self.logger.error("安装超时")
            self.root.after(0, lambda: messagebox.showerror("安装超时", "OpenClaw 安装超时，请检查网络连接"))
            return False
        except Exception as e:
            self.logger.error(f"安装错误: {e}")
            err = str(e)
            self.root.after(0, lambda: messagebox.showerror("安装失败", f"OpenClaw 安装失败:\n{err}"))
            return False
            
    def show_config_dialog(self):
        parent = self.root
        if getattr(self, "config_only", False) and getattr(self, "dialog_parent", None):
            parent = self.dialog_parent
        d = ConfigDialog(parent, self)
        if getattr(self, "config_only", False):
            def on_dialog_closed(event):
                if event.widget == d.dialog:
                    try:
                        self.root.after(0, self.root.destroy)
                    except Exception:
                        pass
            d.dialog.bind("<Destroy>", on_dialog_closed)
    
    def show_channels_dialog(self):
        """显示通道配置对话框"""
        ChannelsConfigDialog(self.root, self)
        
    def start_install(self):
        self.start_btn.config(state=tk.DISABLED)
        self.config_btn.config(state=tk.DISABLED)
        self.channels_btn.config(state=tk.DISABLED)
        self.save_log_btn.config(state=tk.DISABLED)
        
        thread = threading.Thread(target=self.install_process)
        thread.daemon = True
        thread.start()
        
    def _show_error(self, title, msg):
        messagebox.showerror(title, msg)

    def install_process(self):
        try:
            self.root.after(0, lambda: self.step1_var.set(False))
            if not self.check_nodejs():
                if not self.install_nodejs():
                    self.root.after(0, lambda: self._show_error("安装失败", "Node.js 安装失败"))
                    return
            self.root.after(0, lambda: self.step1_var.set(True))
            
            self.root.after(0, lambda: self.step2_var.set(False))
            openclaw_already_installed = self.check_openclaw()
            if not openclaw_already_installed:
                if not self.install_openclaw():
                    self.root.after(0, lambda: self._show_error("安装失败", "OpenClaw 安装失败"))
                    return
            else:
                if not self.update_openclaw_if_needed():
                    self.logger.error("OpenClaw 更新失败，继续使用当前版本")
            self.root.after(0, lambda: self.step2_var.set(True))

            self.root.after(0, lambda: self.step3_var.set(False))
            self.update_progress(100, "安装完成")
            if openclaw_already_installed and self.is_model_configured():
                self.logger.success("=== 安装流程完成：OpenClaw 已是最新且模型已配置 ===")
                self.root.after(0, lambda: messagebox.showinfo("安装完成", "OpenClaw 已是最新版本，且模型已配置，无需再设置。"))
            else:
                self.root.after(0, self.show_config_dialog)
                self.logger.success("=== 安装流程完成，请保存模型配置 ===")
            
        except Exception as e:
            self.logger.error(f"安装出错: {e}")
            err_msg = str(e)
            self.root.after(0, lambda: self._show_error("安装错误", err_msg))
        finally:
            def _reenable():
                self.start_btn.config(state=tk.NORMAL)
                self.config_btn.config(state=tk.NORMAL)
                self.channels_btn.config(state=tk.NORMAL)
                self.save_log_btn.config(state=tk.NORMAL)
            self.root.after(0, _reenable)


class ConfigDialog:
    def __init__(self, parent, installer):
        self.installer = installer
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("配置 OpenClaw")
        self.dialog.geometry("700x680")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.center_window()
        self.setup_ui()
        self.load_existing_config()
        
    def center_window(self):
        self.dialog.update_idletasks()
        width = 700
        height = 680
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')
        
    def setup_ui(self):
        # 底部栏先 pack，保证始终贴在窗口底部可见
        bottom_bar = tk.Frame(self.dialog)
        bottom_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=(10, 15))
        
        next_hint = tk.Label(bottom_bar, text="请填写 API Key 后点击「保存配置」完成设置",
                             font=("Microsoft YaHei", 10), fg="#333")
        next_hint.pack(pady=(0, 8))
        
        btn_frame = tk.Frame(bottom_bar)
        btn_frame.pack(fill=tk.X)
        
        tk.Button(btn_frame, text="保存配置", command=self.save_config,
                 font=("Microsoft YaHei", 12), bg="#4CAF50", fg="white",
                 width=15, height=2).pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="测试连接", command=self.test_connection,
                 font=("Microsoft YaHei", 12), bg="#2196F3", fg="white",
                 width=15, height=2).pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="取消", command=self.dialog.destroy,
                 font=("Microsoft YaHei", 12), width=10, height=2).pack(side=tk.RIGHT, padx=5)
        
        # 上方可滚动内容放在一个 frame 里
        content = tk.Frame(self.dialog)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=(15, 5))
        
        tk.Label(content, text="配置 OpenClaw", 
                font=("Microsoft YaHei", 16, "bold")).pack(pady=(0, 10))
        
        security_frame = tk.Frame(content, bg="#FFF3CD", padx=10, pady=10)
        security_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(security_frame, 
                text="⚠️ 安全提示: API Key 建议保存到环境变量，更加安全！",
                font=("Microsoft YaHei", 9), bg="#FFF3CD", fg="#856404",
                wraplength=650).pack()
        
        # 保存方式选择
        save_method_frame = tk.LabelFrame(content, text="API Key 保存方式", font=("Microsoft YaHei", 11))
        save_method_frame.pack(fill=tk.X, pady=8)
        
        self.save_method_var = tk.StringVar(value="env")
        tk.Radiobutton(save_method_frame, 
                      text="环境变量 (推荐) - 更安全，不会写入配置文件",
                      variable=self.save_method_var, 
                      value="env",
                      font=("Microsoft YaHei", 10),
                      command=self.on_save_method_change).pack(anchor=tk.W, padx=10, pady=3)
        tk.Radiobutton(save_method_frame, 
                      text="配置文件 - 明文存储，方便迁移",
                      variable=self.save_method_var, 
                      value="file",
                      font=("Microsoft YaHei", 10),
                      command=self.on_save_method_change).pack(anchor=tk.W, padx=10, pady=3)
        
        self.env_var_label = tk.Label(save_method_frame, 
                                     text="", 
                                     font=("Microsoft YaHei", 9), 
                                     fg="blue")
        self.env_var_label.pack(anchor=tk.W, padx=10, pady=5)
        
        model_frame = tk.LabelFrame(content, text="选择模型", font=("Microsoft YaHei", 11))
        model_frame.pack(fill=tk.X, pady=8)
        
        self.category_var = tk.StringVar(value="国产模型")
        category_frame = tk.Frame(model_frame)
        category_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(category_frame, text="模型类别:", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
        
        category_combo = ttk.Combobox(category_frame, textvariable=self.category_var,
                                      values=list(MODELS.keys()), state="readonly", width=15)
        category_combo.pack(side=tk.LEFT, padx=5)
        category_combo.bind("<<ComboboxSelected>>", self.on_category_change)
        
        model_select_frame = tk.Frame(model_frame)
        model_select_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(model_select_frame, text="模型:", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
        
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(model_select_frame, textvariable=self.model_var,
                                        values=list(MODELS["国产模型"].keys()),
                                        state="readonly", width=40)
        self.model_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.model_combo.bind("<<ComboboxSelected>>", self.on_model_change)
        
        self.model_desc = tk.Label(model_frame, text="", font=("Microsoft YaHei", 9), 
                                  fg="gray", wraplength=630)
        self.model_desc.pack(padx=10, pady=5)
        
        api_frame = tk.LabelFrame(content, text="API Key 配置", font=("Microsoft YaHei", 11))
        api_frame.pack(fill=tk.X, pady=8)
        
        self.api_hint = tk.Label(api_frame, text="", font=("Microsoft YaHei", 9), 
                                fg="blue", wraplength=630)
        self.api_hint.pack(padx=10, pady=5)
        
        api_input_frame = tk.Frame(api_frame)
        api_input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(api_input_frame, text="API Key:", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
        
        self.api_key_var = tk.StringVar()
        self.api_key_entry = tk.Entry(api_input_frame, textvariable=self.api_key_var,
                                      font=("Consolas", 10), width=50, show="*")
        self.api_key_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.show_key_btn = tk.Button(api_input_frame, text="显示", 
                                      command=self.toggle_key_visibility,
                                      font=("Microsoft YaHei", 9))
        self.show_key_btn.pack(side=tk.LEFT)
        
        self.api_format_hint = tk.Label(api_frame, text="", font=("Microsoft YaHei", 8), fg="gray")
        self.api_format_hint.pack(padx=10, pady=2)
        
        advanced_frame = tk.LabelFrame(content, text="高级选项", font=("Microsoft YaHei", 11))
        advanced_frame.pack(fill=tk.X, pady=8)
        
        self.thinking_var = tk.BooleanVar(value=False)
        tk.Checkbutton(advanced_frame, text="启用 Thinking 模式",
                      variable=self.thinking_var,
                      font=("Microsoft YaHei", 10)).pack(anchor=tk.W, padx=10, pady=5)
        
        self.webchat_var = tk.BooleanVar(value=True)
        tk.Checkbutton(advanced_frame, text="启用 WebChat 界面",
                      variable=self.webchat_var,
                      font=("Microsoft YaHei", 10)).pack(anchor=tk.W, padx=10, pady=5)
        
        preview_frame = tk.LabelFrame(content, text="配置预览", font=("Microsoft YaHei", 11))
        preview_frame.pack(fill=tk.X, pady=8)
        
        self.preview_text = scrolledtext.ScrolledText(preview_frame, height=4, width=70,
                                                      font=("Consolas", 9))
        self.preview_text.pack(fill=tk.X, padx=5, pady=5)
        self.preview_text.config(state=tk.DISABLED)
        
        tk.Button(preview_frame, text="更新预览", command=self.update_preview,
                 font=("Microsoft YaHei", 9)).pack(anchor=tk.E, padx=5, pady=2)
        
        self.on_category_change()
        self.update_preview()
        
    def load_existing_config(self):
        """加载已有的模型配置（优先从环境变量读取 API Key）"""
        config_path = os.path.join(os.path.expanduser("~/.openclaw"), "openclaw.json")
        config = {}
        
        # 读取配置文件（如果存在）
        if os.path.isfile(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception as e:
                print(f"读取配置文件失败: {e}")
        
        try:
            models_config = config.get("models", {})
            
            # 加载默认模型
            default_model = models_config.get("default", "")
            if default_model:
                # 设置模型类别和模型
                for category, models in MODELS.items():
                    if default_model in models:
                        self.category_var.set(category)
                        self.on_category_change()
                        self.model_var.set(default_model)
                        self.on_model_change()
                        break
            
            # 加载 thinking 设置
            thinking = models_config.get("thinking", False)
            self.thinking_var.set(thinking)
            
            # 加载 webchat 设置
            webchat_config = config.get("channels", {}).get("webchat", {})
            webchat_enabled = webchat_config.get("enabled", True)
            self.webchat_var.set(webchat_enabled)
            
            # 加载 API Key（优先从环境变量读取）
            if default_model:
                provider = default_model.split('/')[0]
                
                # 1. 优先从环境变量读取
                env_api_key = get_api_key_from_env(provider)
                if env_api_key:
                    self.api_key_var.set(env_api_key)
                    self.use_env_var = True  # 标记使用了环境变量
                else:
                    # 2. 从配置文件读取（向后兼容）
                    providers = models_config.get("providers", {})
                    provider_config = providers.get(provider, {})
                    api_key = provider_config.get("apiKey", "")
                    if api_key:
                        self.api_key_var.set(api_key)
                        self.use_env_var = False
            
            # 更新预览
            self.update_preview()
            
        except Exception as e:
            print(f"加载已有模型配置失败: {e}")
    
    def on_category_change(self, event=None):
        category = self.category_var.get()
        models = list(MODELS[category].keys())
        self.model_combo['values'] = models
        if models:
            self.model_combo.set(models[0])
            self.on_model_change()
            
    def on_model_change(self, event=None):
        category = self.category_var.get()
        model = self.model_var.get()
        
        if model in MODELS[category]:
            self.model_desc.config(text=MODELS[category][model])
            
            provider = model.split('/')[0]
            if provider in API_KEY_HINTS:
                self.api_hint.config(text=f"提示: {API_KEY_HINTS[provider]}")
            else:
                self.api_hint.config(text="")
                
            format_hints = {
                "moonshot": "格式: sk-xxxxxxxxxxxxxxxx",
                "deepseek": "格式: sk-xxxxxxxxxxxxxxxx",
                "alibaba": "格式: sk-xxxxxxxxxxxxxxxx",
                "openai": "格式: sk-xxxxxxxxxxxxxxxx",
                "anthropic": "格式: sk-ant-xxxxxxxx",
                "google": "格式: xxxxxxxxxxxxxxxx"
            }
            self.api_format_hint.config(text=format_hints.get(provider, ""))
            
        self.update_preview()
        self.on_save_method_change()  # 更新环境变量提示
                
    def on_save_method_change(self):
        """当保存方式改变时更新提示"""
        model = self.model_var.get()
        if not model:
            return
        provider = model.split('/')[0]
        env_var_name = get_api_key_env_var_name(provider)
        
        if self.save_method_var.get() == "env":
            self.env_var_label.config(
                text=f"💡 将设置环境变量: {env_var_name}",
                fg="blue"
            )
        else:
            self.env_var_label.config(
                text=f"⚠️ API Key 将明文保存在配置文件中",
                fg="orange"
            )
                
    def toggle_key_visibility(self):
        if self.api_key_entry['show'] == '*':
            self.api_key_entry.config(show='')
            self.show_key_btn.config(text='隐藏')
        else:
            self.api_key_entry.config(show='*')
            self.show_key_btn.config(text='显示')
            
    def update_preview(self):
        config = self.get_config(for_preview=True)
        if config:
            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete("1.0", tk.END)
            self.preview_text.insert(tk.END, json.dumps(config, indent=2, ensure_ascii=False))
            self.preview_text.config(state=tk.DISABLED)
            
    def get_config(self, for_preview=False):
        model = self.model_var.get()
        api_key = self.api_key_var.get().strip()
        
        if not model:
            if not for_preview:
                messagebox.showerror("错误", "请选择模型")
            return None
            
        if not api_key and not for_preview:
            messagebox.showerror("错误", "请输入 API Key")
            return None
            
        provider = model.split('/')[0]
        
        config = {
            "model": model,
            "thinking": self.thinking_var.get(),
            "channels": {
                "webchat": {
                    "enabled": self.webchat_var.get()
                }
            },
            "apiKeys": {}
        }
        
        if api_key:
            config["apiKeys"][provider] = api_key
            
        return config
        
    def save_config(self):
        """保存模型配置，支持保存到环境变量或配置文件"""
        config = self.get_config()
        if not config:
            return
        
        provider = config["model"].split("/")[0]
        api_key = (config.get("apiKeys") or {}).get(provider, "").strip()
        if not api_key:
            messagebox.showerror("错误", "请输入 API Key")
            return

        config_dir = os.path.expanduser("~/.openclaw")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "openclaw.json")

        try:
            # 读取现有配置
            if os.path.isfile(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            else:
                existing = {}

            # 确保 models 结构存在
            if "models" not in existing:
                existing["models"] = {}
            if "providers" not in existing["models"]:
                existing["models"]["providers"] = {}
            
            # 根据保存方式处理 API Key
            save_method = getattr(self, 'save_method_var', None)
            use_env = save_method and save_method.get() == "env"
            
            if use_env:
                # 保存到环境变量
                set_api_key_to_env(provider, api_key, permanent=True)
                # 从配置文件移除 apiKey（如果存在）
                if provider in existing["models"]["providers"]:
                    existing["models"]["providers"][provider].pop("apiKey", None)
                    # 如果 provider 配置为空，删除整个 provider
                    if not existing["models"]["providers"][provider]:
                        del existing["models"]["providers"][provider]
                save_location = f"环境变量 ({get_api_key_env_var_name(provider)})"
            else:
                # 保存到配置文件
                if provider not in existing["models"]["providers"]:
                    existing["models"]["providers"][provider] = {}
                existing["models"]["providers"][provider]["apiKey"] = api_key
                save_location = f"配置文件 ({config_path})"
            
            # 保存默认模型
            existing["models"]["default"] = config["model"]
            
            # 保存 thinking 设置
            existing["models"]["thinking"] = config["thinking"]
            
            # 保存 channels.webchat 设置
            if "channels" not in existing:
                existing["channels"] = {}
            existing["channels"]["webchat"] = config["channels"]["webchat"]

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)

            messagebox.showinfo("保存成功", 
                f"模型配置已保存\n\n"
                f"API Key 保存位置: {save_location}\n"
                f"默认模型: {config['model']}\n"
                f"Thinking: {'开启' if config['thinking'] else '关闭'}\n"
                f"WebChat: {'开启' if config['channels']['webchat']['enabled'] else '关闭'}")
            self.installer.step3_var.set(True)
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("保存失败", f"无法保存配置:\n{e}")
            
    def test_connection(self):
        config = self.get_config()
        if not config:
            return
            
        model = config['model']
        provider = model.split('/')[0]
        api_key = config['apiKeys'].get(provider, '')
        
        # 检测 API Key 来源
        env_var_name = get_api_key_env_var_name(provider)
        env_api_key = get_api_key_from_env(provider)
        
        if env_api_key:
            key_source = f"环境变量 ({env_var_name})"
        elif api_key:
            key_source = "配置文件"
        else:
            key_source = "未设置"
        
        masked_key = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else '*' * len(api_key)
        test_msg = f"模型: {model}\n提供商: {provider}\nAPI Key 来源: {key_source}\nAPI Key: {masked_key}"
        messagebox.showinfo("连接测试", f"配置信息:\n\n{test_msg}")


class ChannelsConfigDialog:
    """国内 IM 平台通道配置对话框"""
    
    def __init__(self, parent, installer):
        self.installer = installer
        self.channel_vars = {}  # 存储各平台的启用状态
        self.field_entries = {}  # 存储各平台的输入字段
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("通道 (Channels) 配置 - 国内 IM 平台")
        self.dialog.geometry("800x700")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.center_window()
        self.setup_ui()
        self.load_existing_config()
        
    def center_window(self):
        self.dialog.update_idletasks()
        width = 800
        height = 700
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')
        
    def setup_ui(self):
        # 标题
        title_frame = tk.Frame(self.dialog)
        title_frame.pack(fill=tk.X, padx=20, pady=(15, 5))
        
        tk.Label(title_frame, text="📡 通道 (Channels) 配置", 
                font=("Microsoft YaHei", 16, "bold")).pack(anchor=tk.W)
        
        tk.Label(title_frame, 
                text="配置 OpenClaw 对接国内 IM 平台（QQ 频道、企业微信、钉钉、飞书）",
                font=("Microsoft YaHei", 10), fg="gray").pack(anchor=tk.W, pady=(5, 0))
        
        # 说明区域
        info_frame = tk.Frame(self.dialog, bg="#E3F2FD", padx=10, pady=10)
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        
        info_text = """💡 使用说明：
1. 选择要启用的平台，填写对应配置信息
2. 每个平台需要在各自的开放平台创建应用并获取凭证
3. 配置完成后，OpenClaw 将能够接收和发送消息到这些平台
4. 需要公网可访问的 Webhook 地址才能接收平台推送的消息"""
        
        tk.Label(info_frame, text=info_text, font=("Microsoft YaHei", 9), 
                bg="#E3F2FD", justify=tk.LEFT).pack(anchor=tk.W)
        
        # 底部栏（先 pack 到底部，保证按钮始终在视区内；尽量压低高度以留出配置区域）
        bottom_frame = tk.Frame(self.dialog)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=(0, 10))
        
        # 配置预览（缩小行数）
        preview_frame = tk.LabelFrame(bottom_frame, text="配置预览", font=("Microsoft YaHei", 9))
        preview_frame.pack(fill=tk.X, pady=(0, 4))
        
        self.preview_text = scrolledtext.ScrolledText(preview_frame, height=3, width=80,
                                                      font=("Consolas", 9))
        self.preview_text.pack(fill=tk.X, padx=4, pady=2)
        self.preview_text.config(state=tk.DISABLED)
        
        # 底部按钮行（单行紧凑）
        btn_frame = tk.Frame(bottom_frame)
        btn_frame.pack(fill=tk.X)
        
        tk.Button(btn_frame, text="保存", command=self.save_channels_config,
                 font=("Microsoft YaHei", 10), bg="#4CAF50", fg="white",
                 width=8).pack(side=tk.LEFT, padx=3)
        
        tk.Button(btn_frame, text="更新预览", command=self.update_preview,
                 font=("Microsoft YaHei", 10), bg="#2196F3", fg="white",
                 width=8).pack(side=tk.LEFT, padx=3)
        
        tk.Button(btn_frame, text="打开配置目录", command=self.open_config_dir,
                 font=("Microsoft YaHei", 10), width=10).pack(side=tk.LEFT, padx=3)
        
        tk.Button(btn_frame, text="关闭", command=self.dialog.destroy,
                 font=("Microsoft YaHei", 10), width=6).pack(side=tk.RIGHT, padx=3)
        
        # 创建 Notebook（标签页），填充中间区域
        self.notebook = ttk.Notebook(self.dialog)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # 为每个平台创建标签页
        for channel_key, channel_info in CHANNELS_CONFIG.items():
            self.create_channel_tab(channel_key, channel_info)
        
        # 初始更新预览
        self.update_preview()
    
    def create_channel_tab(self, channel_key, channel_info):
        """为单个平台创建配置标签页"""
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text=f"{channel_info['icon']} {channel_info['name']}")
        
        # 启用开关
        enable_frame = tk.Frame(tab)
        enable_frame.pack(fill=tk.X, padx=15, pady=10)
        
        var = tk.BooleanVar(value=False)
        self.channel_vars[channel_key] = var
        
        tk.Checkbutton(enable_frame, text=f"启用 {channel_info['name']}",
                      variable=var, font=("Microsoft YaHei", 11, "bold"),
                      command=self.update_preview).pack(anchor=tk.W)
        
        # 文档链接
        tk.Button(enable_frame, text="📖 查看开放平台文档",
                 command=lambda url=channel_info['docs_url']: self.open_url(url),
                 font=("Microsoft YaHei", 9), fg="blue").pack(anchor=tk.W, pady=(5, 0))
        
        # 配置字段
        fields_frame = tk.LabelFrame(tab, text="配置信息", font=("Microsoft YaHei", 10))
        fields_frame.pack(fill=tk.X, padx=15, pady=5)
        
        self.field_entries[channel_key] = {}
        
        for field in channel_info['fields']:
            field_frame = tk.Frame(fields_frame)
            field_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # 标签
            label_text = field['label'] + (" *" if field.get('required') else "")
            tk.Label(field_frame, text=label_text, 
                    font=("Microsoft YaHei", 10), width=18, anchor=tk.W).pack(side=tk.LEFT)
            
            # 根据字段类型创建不同的输入控件
            if field['type'] == 'checkbox':
                # 复选框类型
                entry_var = tk.BooleanVar(value=field.get('default', False))
                cb = tk.Checkbutton(field_frame, variable=entry_var,
                                   font=("Microsoft YaHei", 10))
                cb.pack(side=tk.LEFT, padx=5)
            else:
                # 文本/密码输入框
                entry_var = tk.StringVar()
                if field.get('default'):
                    entry_var.set(str(field['default']))
                    
                show_char = '*' if field['type'] == 'password' else None
                entry = tk.Entry(field_frame, textvariable=entry_var,
                               font=("Consolas", 10), width=45, show=show_char)
                entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
                
                # 显示/隐藏密码按钮
                if field['type'] == 'password':
                    def make_toggle(ent, btn):
                        def toggle():
                            if ent['show'] == '*':
                                ent.config(show='')
                                btn.config(text='隐藏')
                            else:
                                ent.config(show='*')
                                btn.config(text='显示')
                        return toggle
                    
                    toggle_btn = tk.Button(field_frame, text="显示", font=("Microsoft YaHei", 8))
                    toggle_btn.config(command=make_toggle(entry, toggle_btn))
                    toggle_btn.pack(side=tk.LEFT)
            
            # 提示文字
            if field.get('hint'):
                tk.Label(field_frame, text=field['hint'], 
                        font=("Microsoft YaHei", 8), fg="gray").pack(side=tk.LEFT, padx=5)
            
            self.field_entries[channel_key][field['key']] = entry_var
        
        # Webhook 地址提示
        webhook_frame = tk.Frame(tab, bg="#FFF8E1", padx=10, pady=10)
        webhook_frame.pack(fill=tk.X, padx=15, pady=10)
        
        webhook_path = ""
        for f in channel_info['fields']:
            if f['key'] == 'webhook_path':
                webhook_path = f.get('default', f'/webhook')
                break
        
        webhook_text = f"""📌 Webhook 配置提示：
在 {channel_info['name']} 开放平台中，将服务器 URL 设置为：
https://your-domain.com{webhook_path}
（请将 your-domain.com 替换为您的实际域名或公网 IP）"""
        
        tk.Label(webhook_frame, text=webhook_text, font=("Microsoft YaHei", 9),
                bg="#FFF8E1", justify=tk.LEFT).pack(anchor=tk.W)
    
    def open_url(self, url):
        """在浏览器中打开 URL"""
        import webbrowser
        webbrowser.open(url)
    
    def open_config_dir(self):
        """打开配置目录"""
        config_dir = os.path.expanduser("~/.openclaw")
        os.makedirs(config_dir, exist_ok=True)
        
        if sys.platform == 'win32':
            os.startfile(config_dir)
        elif sys.platform == 'darwin':
            subprocess.run(['open', config_dir])
        else:
            subprocess.run(['xdg-open', config_dir])
    
    def load_existing_config(self):
        """加载已有的通道配置"""
        config_path = os.path.join(os.path.expanduser("~/.openclaw"), "openclaw.json")
        if not os.path.isfile(config_path):
            return
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            channels_config = config.get("channels", {})
            
            for channel_key in CHANNELS_CONFIG.keys():
                channel_data = channels_config.get(channel_key, {})
                
                # 设置启用状态
                if channel_data.get("enabled"):
                    self.channel_vars[channel_key].set(True)
                
                # 填充字段值
                for field_key, entry_var in self.field_entries.get(channel_key, {}).items():
                    value = channel_data.get(field_key, "")
                    if value != "" and value is not None:
                        # 处理 Boolean 类型
                        if isinstance(entry_var, tk.BooleanVar):
                            entry_var.set(bool(value))
                        else:
                            entry_var.set(str(value))
                        
        except Exception as e:
            print(f"加载已有配置失败: {e}")
    
    def get_channels_config(self):
        """获取当前配置的通道信息"""
        config = {"channels": {}}
        
        for channel_key, channel_info in CHANNELS_CONFIG.items():
            if not self.channel_vars[channel_key].get():
                continue
            
            channel_config = {"enabled": True}
            
            for field in channel_info['fields']:
                field_key = field['key']
                entry_var = self.field_entries[channel_key].get(field_key)
                if entry_var:
                    if field['type'] == 'checkbox':
                        # Boolean 类型直接取值
                        channel_config[field_key] = entry_var.get()
                    else:
                        # 字符串类型需要 strip
                        value = entry_var.get().strip()
                        if value:
                            channel_config[field_key] = value
            
            config["channels"][channel_key] = channel_config
        
        return config
    
    def update_preview(self):
        """更新配置预览"""
        config = self.get_channels_config()
        
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete("1.0", tk.END)
        
        if config["channels"]:
            self.preview_text.insert(tk.END, json.dumps(config, indent=2, ensure_ascii=False))
        else:
            self.preview_text.insert(tk.END, "// 尚未配置任何通道\n// 请在上方标签页中启用并配置至少一个平台")
        
        self.preview_text.config(state=tk.DISABLED)
    
    def validate_config(self):
        """验证配置是否有效"""
        errors = []
        
        for channel_key, channel_info in CHANNELS_CONFIG.items():
            if not self.channel_vars[channel_key].get():
                continue
            
            for field in channel_info['fields']:
                if not field.get('required'):
                    continue
                
                entry_var = self.field_entries[channel_key].get(field['key'])
                if not entry_var:
                    errors.append(f"{channel_info['name']} - {field['label']} 为必填项")
                    continue
                
                # 根据字段类型验证
                if field['type'] == 'checkbox':
                    # Boolean 类型不需要验证（有默认值）
                    continue
                else:
                    # 字符串类型需要检查是否为空
                    if not entry_var.get().strip():
                        errors.append(f"{channel_info['name']} - {field['label']} 为必填项")
        
        return errors
    
    def save_channels_config(self):
        """保存通道配置到 openclaw.json"""
        # 验证
        errors = self.validate_config()
        if errors:
            messagebox.showerror("配置错误", "请完善以下必填项:\n\n" + "\n".join(errors))
            return
        
        config_dir = os.path.expanduser("~/.openclaw")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "openclaw.json")
        
        try:
            # 读取现有配置
            if os.path.isfile(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            else:
                existing = {}
            
            # 确保 channels 存在
            if "channels" not in existing:
                existing["channels"] = {}
            
            # 处理所有平台（包括启用和禁用的）
            for channel_key, channel_info in CHANNELS_CONFIG.items():
                is_enabled = self.channel_vars[channel_key].get()
                
                if is_enabled:
                    # 启用的平台：保存完整配置
                    channel_config = {"enabled": True}
                    for field in channel_info['fields']:
                        field_key = field['key']
                        entry_var = self.field_entries[channel_key].get(field_key)
                        if entry_var:
                            if field['type'] == 'checkbox':
                                channel_config[field_key] = entry_var.get()
                            else:
                                value = entry_var.get().strip()
                                if value:
                                    channel_config[field_key] = value
                    existing["channels"][channel_key] = channel_config
                else:
                    # 禁用的平台：如果已有配置，只修改 enabled 为 false
                    if channel_key in existing["channels"]:
                        existing["channels"][channel_key]["enabled"] = False
                    # 如果没有配置，可以选择不创建或创建一个空的禁用配置
            
            # 保存
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
            
            # 统计启用的平台
            enabled_count = sum(1 for v in self.channel_vars.values() if v.get())
            
            messagebox.showinfo("保存成功", 
                f"通道配置已保存到:\n{config_path}\n\n已启用 {enabled_count} 个平台")
            
        except Exception as e:
            messagebox.showerror("保存失败", f"无法保存配置:\n{e}")


def main():
    root = tk.Tk()
    app = OpenClawInstaller(root)
    root.mainloop()


if __name__ == "__main__":
    main()
