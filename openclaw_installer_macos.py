#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw macOS 自动安装程序
功能与 Windows v2 一致，适配 macOS：
1. 检查/安装 Node.js（官方 .pkg 或 Homebrew）
2. 安装 OpenClaw (npm install -g)
3. 图形化配置模型与 API Key
4. 配置文件写入 ~/.openclaw/openclaw.json
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

# 仅允许在 macOS 上运行
if sys.platform != 'darwin':
    print("此程序仅支持 macOS。Windows 请使用 openclaw_installer_v2.py")
    sys.exit(1)

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext, filedialog
except ImportError:
    print("错误：需要 tkinter。macOS 自带 Python 可能未包含，请用 Homebrew: brew install python-tk")
    sys.exit(1)

# 配置
NODEJS_VERSION = "20.11.0"
MAX_RETRIES = 3
# Node 官方 macOS 通用 pkg（Intel + Apple Silicon）
NODE_PKG_URL = f"https://nodejs.org/dist/v{NODEJS_VERSION}/node-v{NODEJS_VERSION}.pkg"

# 模型与 API 提示（与 Windows 版一致）
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


def _ensure_path():
    """确保 PATH 包含 macOS 常见 Node 安装路径"""
    paths = ["/usr/local/bin", "/opt/homebrew/bin"]
    current = os.environ.get("PATH", "")
    for p in paths:
        if p not in current:
            current = p + ":" + current
    os.environ["PATH"] = current


def _font(name_fallback="Helvetica", size=11):
    """macOS 友好字体：PingFang SC 或 Helvetica"""
    return (name_fallback, size)


class Logger:
    """日志记录器（子线程通过 root.after 安全写 GUI）"""
    def __init__(self, text_widget=None, log_file=None, root=None):
        self.text_widget = text_widget
        self.log_file = log_file
        self.root = root

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
                with open(self.log_file, "a", encoding="utf-8") as f:
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
        _ensure_path()
        self.root = root
        self.config_only = config_only
        self.dialog_parent = dialog_parent
        self.root.title("OpenClaw 自动安装程序 (macOS)")
        self.root.geometry("750x650")
        self.root.resizable(True, True)
        self.center_window()

        self.install_dir = os.path.expanduser("~/.openclaw")
        self.node_installed = False
        self.openclaw_installed = False
        self.installer_path = None

        log_dir = os.path.expanduser("~/.openclaw/logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"install_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

        self.setup_ui()
        self.logger = Logger(self.log_text, log_file, self.root)
        self.logger.info(f"日志文件: {log_file}")
        if config_only:
            self.root.withdraw()
            self.root.after(200, self.show_config_dialog)

    def center_window(self):
        self.root.update_idletasks()
        w, h = 750, 650
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def setup_ui(self):
        font_title = _font("Helvetica", 18)
        font_normal = _font("Helvetica", 10)
        font_small = _font("Helvetica", 9)

        title = tk.Label(self.root, text="OpenClaw 自动安装程序 (macOS)", font=(font_title[0], font_title[1], "bold"))
        title.pack(pady=15)
        subtitle = tk.Label(self.root, text="检查 Node.js → 安装 OpenClaw → 配置模型与 API Key", font=font_small, fg="gray")
        subtitle.pack()

        self.steps_frame = tk.LabelFrame(self.root, text="安装进度", font=font_normal)
        self.steps_frame.pack(fill=tk.X, padx=30, pady=10)

        self.step1_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self.steps_frame, text="步骤 1: 检查/安装 Node.js", variable=self.step1_var, state=tk.DISABLED, font=font_normal).pack(anchor=tk.W, padx=10, pady=3)
        self.step2_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self.steps_frame, text="步骤 2: 安装 OpenClaw", variable=self.step2_var, state=tk.DISABLED, font=font_normal).pack(anchor=tk.W, padx=10, pady=3)
        self.step3_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self.steps_frame, text="步骤 3: 配置模型和 API Key", variable=self.step3_var, state=tk.DISABLED, font=font_normal).pack(anchor=tk.W, padx=10, pady=3)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress_var, maximum=100, length=400)
        self.progress_bar.pack(fill=tk.X, padx=30, pady=5)
        self.progress_label = tk.Label(self.root, text="准备就绪", font=font_small)
        self.progress_label.pack()

        log_frame = tk.LabelFrame(self.root, text="安装日志", font=font_normal)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, width=80, font=("Menlo", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=30, pady=15)
        self.start_btn = tk.Button(btn_frame, text="开始安装", command=self.start_install, font=font_normal, bg="#4CAF50", fg="white", width=15, height=2)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        self.config_btn = tk.Button(btn_frame, text="仅配置模型", command=self.show_config_dialog, font=font_normal, bg="#2196F3", fg="white", width=15, height=2)
        self.config_btn.pack(side=tk.LEFT, padx=5)
        self.save_log_btn = tk.Button(btn_frame, text="保存日志", command=self.save_log, font=font_normal, width=12, height=2)
        self.save_log_btn.pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="退出", command=self.root.quit, font=font_normal, width=10, height=2).pack(side=tk.RIGHT, padx=5)

    def update_progress(self, value, message=""):
        def _update():
            self.progress_var.set(value)
            if message:
                self.progress_label.config(text=message)
        self.root.after(0, _update)

    def save_log(self):
        content = self.log_text.get("1.0", tk.END)
        if not content.strip():
            messagebox.showwarning("警告", "日志为空")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("日志文件", "*.log"), ("文本文件", "*.txt")],
            initialfile=f"openclaw_install_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                messagebox.showinfo("保存成功", f"日志已保存到:\n{path}")
            except Exception as e:
                messagebox.showerror("保存失败", str(e))

    def download_with_retry(self, url, path, max_retries=3):
        for attempt in range(max_retries):
            try:
                self.logger.log(f"下载尝试 {attempt + 1}/{max_retries}...")
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})
                with urllib.request.urlopen(req, timeout=120) as resp:
                    with open(path, "wb") as f:
                        shutil.copyfileobj(resp, f)
                self.logger.success(f"下载成功: {path}")
                return True
            except Exception as e:
                self.logger.error(f"下载失败 (尝试 {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    self.logger.log(f"等待 {wait} 秒后重试...")
                    time.sleep(wait)
                else:
                    raise Exception(f"下载失败，已重试 {max_retries} 次: {e}")

    def check_nodejs(self):
        self.logger.info("=== 检查 Node.js ===")
        self.update_progress(5, "检查 Node.js...")
        # 按 PATH 查找 + 常见路径
        node_candidates = [
            "node",
            "/usr/local/bin/node",
            "/opt/homebrew/bin/node",
        ]
        for node_cmd in node_candidates:
            try:
                cmd = [node_cmd, "--version"] if os.path.isabs(node_cmd) or "/" in node_cmd else f"{node_cmd} --version"
                if isinstance(cmd, str):
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=10, env=os.environ)
                else:
                    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=10, env=os.environ)
                if result.returncode == 0:
                    version = (result.stdout or "").strip()
                    self.logger.success(f"Node.js 已安装: {version}")
                    self.node_installed = True
                    self.update_progress(15, "Node.js 已安装")
                    return True
            except Exception:
                continue
        self.logger.info("Node.js 未安装，需要安装")
        return False

    def install_nodejs(self):
        self.logger.info("=== 安装 Node.js ===")
        self.update_progress(20, "正在下载 Node.js...")
        self.installer_path = os.path.join(tempfile.gettempdir(), f"node-v{NODEJS_VERSION}.pkg")
        try:
            self.download_with_retry(NODE_PKG_URL, self.installer_path, MAX_RETRIES)
        except Exception as e:
            self.logger.error(f"下载失败: {e}")
            msg = f"无法下载 Node.js。\n请手动安装:\n1. 打开 https://nodejs.org\n2. 下载 macOS 安装包并安装\n\n错误: {e}"
            self.root.after(0, lambda: messagebox.showerror("下载失败", msg))
            return False
        self.update_progress(35, "正在打开 Node 安装程序...")
        try:
            # 用 open 打开 .pkg，由用户完成安装（需输入密码）
            subprocess.run(["open", self.installer_path], check=True, timeout=10)
            self.logger.success("已打开 Node 安装程序，请在弹出的窗口中完成安装。")
            self.update_progress(45, "请完成 Node 安装后重新点击「开始安装」")
            msg = "Node.js 安装程序已打开。\n请完成安装后关闭本窗口，重新运行本程序并再次点击「开始安装」。"
            self.root.after(0, lambda: messagebox.showinfo("请完成安装", msg))
        except Exception as e:
            self.logger.error(f"打开安装程序失败: {e}")
            self.root.after(0, lambda: messagebox.showerror("错误", f"无法打开安装包:\n{e}"))
            return False
        return False  # 本次未完成安装，需用户重试

    def cleanup_temp_files(self):
        if self.installer_path and os.path.exists(self.installer_path):
            try:
                os.remove(self.installer_path)
                self.logger.info(f"已清理临时文件: {self.installer_path}")
            except Exception as e:
                self.logger.error(f"清理临时文件失败: {e}")

    def _get_openclaw_candidates_macos(self):
        """macOS 下可能存在的 openclaw 路径（不依赖当前 PATH）"""
        home = os.path.expanduser("~")
        candidates = [
            "/usr/local/bin/openclaw",
            "/opt/homebrew/bin/openclaw",
            os.path.join(home, ".npm-global", "bin", "openclaw"),
            os.path.join(home, ".local", "bin", "openclaw"),
        ]
        # nvm 等安装的 node 的全局 bin
        nvm_glob = os.path.join(home, ".nvm", "versions", "node", "*", "bin", "openclaw")
        try:
            import glob
            candidates.extend(glob.glob(nvm_glob))
        except Exception:
            pass
        return [p for p in candidates if p and os.path.isfile(p)]

    def check_openclaw(self):
        """检查 OpenClaw 是否已安装（先 PATH，再常见路径，最后 npm list -g）"""
        self.logger.info("=== 检查 OpenClaw ===")
        self.update_progress(55, "检查 OpenClaw...")
        _ensure_path()

        def try_run(cmd, use_shell=True, env=None):
            try:
                r = subprocess.run(
                    cmd, shell=use_shell, capture_output=True, text=True,
                    encoding="utf-8", errors="ignore", timeout=10, env=env or os.environ
                )
                if r.returncode == 0 and (r.stdout or "").strip():
                    return (r.stdout or "").strip()
            except Exception:
                pass
            return None

        # 1) 当前 PATH
        version = try_run("openclaw --version")
        if version:
            self.logger.success(f"OpenClaw 已安装: {version}，跳过安装")
            self.openclaw_installed = True
            self.update_progress(95, "OpenClaw 已存在，跳过安装")
            return True

        # 2) 显式路径（解决从启动器/双击启动时 PATH 不完整）
        for path in self._get_openclaw_candidates_macos():
            self.logger.info(f"尝试路径: {path}")
            version = try_run([path, "--version"], use_shell=False)
            if version:
                self.logger.success(f"OpenClaw 已安装: {version}，跳过安装")
                self.openclaw_installed = True
                self.update_progress(95, "OpenClaw 已存在，跳过安装")
                return True

        # 3) npm list -g
        try:
            r = subprocess.run(
                "npm list -g openclaw --depth=0",
                shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=15, env=os.environ
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
        try:
            r = subprocess.run("openclaw --version", shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=10, env=os.environ)
            if r.returncode == 0 and (r.stdout or "").strip():
                return (r.stdout or "").strip()
        except Exception:
            pass
        for path in self._get_openclaw_candidates_macos():
            try:
                r = subprocess.run([path, "--version"], capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=10, env=os.environ)
                if r.returncode == 0 and (r.stdout or "").strip():
                    return (r.stdout or "").strip()
            except Exception:
                pass
        return None

    def _get_latest_openclaw_version(self):
        try:
            r = subprocess.run("npm view openclaw version", shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=15, env=os.environ)
            if r.returncode == 0 and (r.stdout or "").strip():
                return (r.stdout or "").strip()
        except Exception:
            pass
        return None

    def update_openclaw_if_needed(self):
        self.logger.info("=== 检查 OpenClaw 版本 ===")
        current = self._get_current_openclaw_version()
        latest = self._get_latest_openclaw_version()
        if not current:
            return True
        if not latest:
            self.logger.info("无法获取最新版本，跳过更新检查")
            return True
        if self._parse_version(current) >= self._parse_version(latest):
            self.logger.success(f"OpenClaw 已是最新: {current}")
            return True
        self.logger.info(f"当前 {current}，最新 {latest}，正在更新...")
        self.update_progress(70, "正在更新 OpenClaw...")
        try:
            r = subprocess.run("npm install -g openclaw@latest", shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=300, env=os.environ)
            if r.returncode != 0:
                self.logger.error("更新失败")
                return False
            self.logger.success("OpenClaw 已更新到最新")
            return True
        except Exception as e:
            self.logger.error(f"更新异常: {e}")
            return False

    def is_model_configured(self):
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
        _ensure_path()
        try:
            result = subprocess.run(
                "npm install -g openclaw@latest",
                shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=300, env=os.environ
            )
            if result.returncode != 0:
                raise Exception(result.stderr or result.stdout or "npm 安装失败")
            self.logger.success("OpenClaw 安装成功")
            self.update_progress(85, "OpenClaw 安装成功")
            result = subprocess.run(
                "openclaw --version",
                shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=10, env=os.environ
            )
            if result.returncode == 0:
                version = (result.stdout or "").strip()
                self.logger.success(f"OpenClaw 版本: {version}")
                self.openclaw_installed = True
                self.update_progress(95, "OpenClaw 安装完成")
                return True
            raise Exception("验证 openclaw 命令失败")
        except subprocess.TimeoutExpired:
            self.logger.error("安装超时")
            self.root.after(0, lambda: messagebox.showerror("安装超时", "OpenClaw 安装超时，请检查网络"))
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

    def start_install(self):
        self.start_btn.config(state=tk.DISABLED)
        self.config_btn.config(state=tk.DISABLED)
        self.save_log_btn.config(state=tk.DISABLED)
        thread = threading.Thread(target=self.install_process, daemon=True)
        thread.start()

    def _show_error(self, title, msg):
        messagebox.showerror(title, msg)

    def install_process(self):
        try:
            self.root.after(0, lambda: self.step1_var.set(False))
            if not self.check_nodejs():
                if not self.install_nodejs():
                    self.root.after(0, lambda: self._show_error("安装失败", "Node.js 未安装成功，请按提示完成安装后重试"))
                    self.root.after(0, self._reenable_buttons)
                    return
            self.root.after(0, lambda: self.step1_var.set(True))

            self.root.after(0, lambda: self.step2_var.set(False))
            openclaw_already_installed = self.check_openclaw()
            if not openclaw_already_installed:
                if not self.install_openclaw():
                    self.root.after(0, lambda: self._show_error("安装失败", "OpenClaw 安装失败"))
                    self.root.after(0, self._reenable_buttons)
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
            self.root.after(0, lambda: self._show_error("安装错误", str(e)))
        finally:
            self.root.after(0, self._reenable_buttons)

    def _reenable_buttons(self):
        self.start_btn.config(state=tk.NORMAL)
        self.config_btn.config(state=tk.NORMAL)
        self.save_log_btn.config(state=tk.NORMAL)


class ConfigDialog:
    """配置对话框（与 Windows 版逻辑一致）"""
    def __init__(self, parent, installer):
        self.installer = installer
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("配置 OpenClaw")
        self.dialog.geometry("700x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self._center()
        self._setup_ui()

    def _center(self):
        self.dialog.update_idletasks()
        w, h = 700, 600
        x = (self.dialog.winfo_screenwidth() // 2) - (w // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (h // 2)
        self.dialog.geometry(f"{w}x{h}+{x}+{y}")

    def _setup_ui(self):
        font_title = _font("Helvetica", 16)
        font_n = _font("Helvetica", 11)
        font_s = _font("Helvetica", 9)
        tk.Label(self.dialog, text="配置 OpenClaw", font=(font_title[0], font_title[1], "bold")).pack(pady=15)
        security = tk.Frame(self.dialog, bg="#FFF3CD", padx=10, pady=10)
        security.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(security, text="⚠️ 安全提示: API Key 将保存在本地配置文件中，请妥善保管！", font=font_s, bg="#FFF3CD", fg="#856404", wraplength=650).pack()

        model_frame = tk.LabelFrame(self.dialog, text="选择模型", font=font_n)
        model_frame.pack(fill=tk.X, padx=20, pady=10)
        self.category_var = tk.StringVar(value="国产模型")
        cf = tk.Frame(model_frame)
        cf.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(cf, text="模型类别:", font=font_n).pack(side=tk.LEFT)
        category_combo = ttk.Combobox(cf, textvariable=self.category_var, values=list(MODELS.keys()), state="readonly", width=15)
        category_combo.pack(side=tk.LEFT, padx=5)
        category_combo.bind("<<ComboboxSelected>>", self.on_category_change)
        msf = tk.Frame(model_frame)
        msf.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(msf, text="模型:", font=font_n).pack(side=tk.LEFT)
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(msf, textvariable=self.model_var, values=list(MODELS["国产模型"].keys()), state="readonly", width=40)
        self.model_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.model_combo.bind("<<ComboboxSelected>>", self.on_model_change)
        self.model_desc = tk.Label(model_frame, text="", font=font_s, fg="gray", wraplength=630)
        self.model_desc.pack(padx=10, pady=5)

        api_frame = tk.LabelFrame(self.dialog, text="API Key 配置", font=font_n)
        api_frame.pack(fill=tk.X, padx=20, pady=10)
        self.api_hint = tk.Label(api_frame, text="", font=font_s, fg="blue", wraplength=630)
        self.api_hint.pack(padx=10, pady=5)
        api_in = tk.Frame(api_frame)
        api_in.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(api_in, text="API Key:", font=font_n).pack(side=tk.LEFT)
        self.api_key_var = tk.StringVar()
        self.api_key_entry = tk.Entry(api_in, textvariable=self.api_key_var, font=("Menlo", 10), width=50, show="*")
        self.api_key_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.show_key_btn = tk.Button(api_in, text="显示", command=self.toggle_key_visibility, font=font_s)
        self.show_key_btn.pack(side=tk.LEFT)
        self.api_format_hint = tk.Label(api_frame, text="", font=("Helvetica", 8), fg="gray")
        self.api_format_hint.pack(padx=10, pady=2)

        adv = tk.LabelFrame(self.dialog, text="高级选项", font=font_n)
        adv.pack(fill=tk.X, padx=20, pady=10)
        self.thinking_var = tk.BooleanVar(value=False)
        tk.Checkbutton(adv, text="启用 Thinking 模式", variable=self.thinking_var, font=font_n).pack(anchor=tk.W, padx=10, pady=5)
        self.webchat_var = tk.BooleanVar(value=True)
        tk.Checkbutton(adv, text="启用 WebChat 界面", variable=self.webchat_var, font=font_n).pack(anchor=tk.W, padx=10, pady=5)

        preview_frame = tk.LabelFrame(self.dialog, text="配置预览", font=font_n)
        preview_frame.pack(fill=tk.X, padx=20, pady=10)
        self.preview_text = scrolledtext.ScrolledText(preview_frame, height=5, width=70, font=("Menlo", 9))
        self.preview_text.pack(fill=tk.X, padx=5, pady=5)
        self.preview_text.config(state=tk.DISABLED)
        tk.Button(preview_frame, text="更新预览", command=self.update_preview, font=font_s).pack(anchor=tk.E, padx=5, pady=2)

        next_hint = tk.Label(self.dialog, text="请填写 API Key 后点击「保存配置」完成设置", font=font_s, fg="#333")
        next_hint.pack(pady=(15, 5))
        btn_frame = tk.Frame(self.dialog)
        btn_frame.pack(fill=tk.X, padx=20, pady=(5, 20))
        tk.Button(btn_frame, text="保存配置", command=self.save_config, font=font_n, bg="#4CAF50", fg="white", width=15, height=2).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="测试连接", command=self.test_connection, font=font_n, bg="#2196F3", fg="white", width=15, height=2).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="取消", command=self.dialog.destroy, font=font_n, width=10, height=2).pack(side=tk.RIGHT, padx=5)

        self.on_category_change()
        self.update_preview()

    def on_category_change(self, event=None):
        cat = self.category_var.get()
        models = list(MODELS[cat].keys())
        self.model_combo["values"] = models
        if models:
            self.model_combo.set(models[0])
            self.on_model_change()

    def on_model_change(self, event=None):
        cat = self.category_var.get()
        model = self.model_var.get()
        if model in MODELS[cat]:
            self.model_desc.config(text=MODELS[cat][model])
            provider = model.split("/")[0]
            self.api_hint.config(text=f"提示: {API_KEY_HINTS[provider]}" if provider in API_KEY_HINTS else "")
            hints = {"moonshot": "格式: sk-xxx", "deepseek": "格式: sk-xxx", "alibaba": "格式: sk-xxx", "openai": "格式: sk-xxx", "anthropic": "格式: sk-ant-xxx", "google": "格式: xxx"}
            self.api_format_hint.config(text=hints.get(provider, ""))
        self.update_preview()

    def toggle_key_visibility(self):
        if self.api_key_entry["show"] == "*":
            self.api_key_entry.config(show="")
            self.show_key_btn.config(text="隐藏")
        else:
            self.api_key_entry.config(show="*")
            self.show_key_btn.config(text="显示")

    def update_preview(self):
        cfg = self.get_config(for_preview=True)
        if cfg:
            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete("1.0", tk.END)
            self.preview_text.insert(tk.END, json.dumps(cfg, indent=2, ensure_ascii=False))
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
        provider = model.split("/")[0]
        config = {
            "model": model,
            "thinking": self.thinking_var.get(),
            "channels": {"webchat": {"enabled": self.webchat_var.get()}},
            "apiKeys": {}
        }
        if api_key:
            config["apiKeys"][provider] = api_key
        return config

    def save_config(self):
        """只修改 openclaw.json 的 models 相关字段（如 apiKey）。"""
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
            if os.path.isfile(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            else:
                existing = {}
            if "models" not in existing:
                existing["models"] = {}
            if "providers" not in existing["models"]:
                existing["models"]["providers"] = {}
            if provider not in existing["models"]["providers"]:
                existing["models"]["providers"][provider] = {}
            existing["models"]["providers"][provider]["apiKey"] = api_key
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("保存成功", f"已仅更新 models 中的 {provider} apiKey：\n{config_path}")
            self.installer.step3_var.set(True)
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("保存失败", f"无法保存配置:\n{e}")

    def test_connection(self):
        config = self.get_config()
        if not config:
            return
        model = config["model"]
        provider = model.split("/")[0]
        api_key = config["apiKeys"].get(provider, "")
        masked = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else "*" * len(api_key)
        messagebox.showinfo("连接测试", f"配置信息:\n\n模型: {model}\n提供商: {provider}\nAPI Key: {masked}")


def main():
    root = tk.Tk()
    OpenClawInstaller(root)
    root.mainloop()


if __name__ == "__main__":
    main()
