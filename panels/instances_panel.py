# -*- coding: utf-8 -*-
"""
多实例管理面板 - 支持本地和远程 OpenClaw 实例管理

功能:
- 实例列表展示（本地 + 远程）
- 实时状态监控（CPU/内存/网络）
- 远程连接管理（SSH/Tailscale）
- 实例操作（启动/停止/重启/删除）
"""

import os
import json
import time
import threading
import subprocess
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, asdict

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    TTKBOOTSTRAP_AVAILABLE = True
except ImportError:
    import tkinter as tk
    from tkinter import ttk as ttk_module
    ttk = ttk_module
    # 兼容回退：ttk 中没有这些对象，补到命名空间以保持后续代码不改动
    ttk.Canvas = tk.Canvas
    ttk.Toplevel = tk.Toplevel
    ttk.StringVar = tk.StringVar
    ttk.BooleanVar = tk.BooleanVar
    ttk.DoubleVar = tk.DoubleVar
    TTKBOOTSTRAP_AVAILABLE = False

from tkinter import messagebox, simpledialog
from tkinter.constants import (
    X, Y, BOTH, LEFT, RIGHT, TOP, BOTTOM,
    W, E, N, S, NW, NE, SW, SE, CENTER,
    VERTICAL, HORIZONTAL
)


@dataclass
class InstanceInfo:
    """实例信息数据类"""
    id: str
    name: str
    host: str
    type: str  # 'local', 'ssh', 'tailscale'
    status: str  # 'running', 'stopped', 'offline', 'error'
    version: str = ""
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_total_mb: float = 0.0
    network_latency_ms: float = 0.0
    uptime_seconds: int = 0
    skill_count: int = 0
    task_count: int = 0
    last_seen: Optional[datetime] = None
    error_message: str = ""
    
    # 连接配置
    ssh_user: str = ""
    ssh_port: int = 22
    tailscale_ip: str = ""
    api_key: str = ""


class InstanceCard(ttk.Frame):
    """实例卡片组件"""
    
    STATUS_COLORS = {
        'running': '#10B981',
        'stopped': '#6B7280',
        'offline': '#EF4444',
        'error': '#F59E0B'
    }
    
    STATUS_ICONS = {
        'running': '●',
        'stopped': '○',
        'offline': '✕',
        'error': '⚠'
    }
    
    TYPE_ICONS = {
        'local': '🖥️',
        'ssh': '🌐',
        'tailscale': '🔗'
    }
    
    def __init__(self, parent, instance: InstanceInfo, on_action: Callable, **kwargs):
        super().__init__(parent, **kwargs)
        self.instance = instance
        self.on_action = on_action
        
        self._build_ui()
    
    def _build_ui(self):
        # 主容器
        container = ttk.Frame(self, padding=10)
        container.pack(fill=X, expand=True)
        
        # 顶部：图标 + 名称 + 状态
        header = ttk.Frame(container)
        header.pack(fill=X)
        
        icon = self.TYPE_ICONS.get(self.instance.type, '🖥️')
        ttk.Label(header, text=f"{icon} {self.instance.name}", 
                 font=("Microsoft YaHei", 12, "bold")).pack(side=LEFT)
        
        status_color = self.STATUS_COLORS.get(self.instance.status, '#6B7280')
        status_icon = self.STATUS_ICONS.get(self.instance.status, '?')
        status_label = ttk.Label(
            header, 
            text=f"{status_icon} {self._get_status_text()}",
            foreground=status_color,
            font=("Microsoft YaHei", 10)
        )
        status_label.pack(side=RIGHT)
        
        # 主机信息
        ttk.Label(container, text=f"主机: {self.instance.host}", 
                 foreground="#666").pack(anchor=W, pady=(5, 0))
        
        # 指标行
        metrics = ttk.Frame(container)
        metrics.pack(fill=X, pady=10)
        
        if self.instance.status == 'running':
            # CPU
            cpu_color = self._get_metric_color(self.instance.cpu_percent, 70, 90)
            ttk.Label(metrics, text=f"CPU: {self.instance.cpu_percent:.1f}%",
                     foreground=cpu_color).pack(side=LEFT, padx=(0, 15))
            
            # 内存
            mem_percent = (self.instance.memory_mb / self.instance.memory_total_mb * 100) if self.instance.memory_total_mb > 0 else 0
            mem_color = self._get_metric_color(mem_percent, 80, 95)
            mem_text = f"内存: {self.instance.memory_mb:.0f}/{self.instance.memory_total_mb:.0f}MB"
            ttk.Label(metrics, text=mem_text, foreground=mem_color).pack(side=LEFT, padx=(0, 15))
            
            # 延迟
            if self.instance.type != 'local':
                latency_color = self._get_metric_color(self.instance.network_latency_ms, 100, 500)
                ttk.Label(metrics, text=f"延迟: {self.instance.network_latency_ms:.0f}ms",
                         foreground=latency_color).pack(side=LEFT, padx=(0, 15))
            
            # 运行时间
            uptime = self._format_uptime(self.instance.uptime_seconds)
            ttk.Label(metrics, text=f"运行: {uptime}").pack(side=LEFT)
            
            # 技能/任务数
            ttk.Label(metrics, text=f"技能: {self.instance.skill_count}  任务: {self.instance.task_count}",
                     foreground="#666").pack(side=RIGHT)
        elif self.instance.status == 'offline':
            last_seen = self.instance.last_seen
            if last_seen:
                ago = datetime.now() - last_seen
                ttk.Label(metrics, text=f"最后在线: {self._format_ago(ago)}",
                         foreground="#999").pack(side=LEFT)
        elif self.instance.error_message:
            ttk.Label(metrics, text=f"错误: {self.instance.error_message}",
                     foreground="#EF4444", wraplength=400).pack(side=LEFT)
        
        # 操作按钮
        actions = ttk.Frame(container)
        actions.pack(fill=X, pady=(5, 0))
        
        if self.instance.status == 'running':
            if self.instance.type != 'local':
                ttk.Button(actions, text="连接", 
                          command=lambda: self.on_action('connect', self.instance),
                          bootstyle="primary-outline" if TTKBOOTSTRAP_AVAILABLE else None,
                          width=8).pack(side=LEFT, padx=(0, 5))
            ttk.Button(actions, text="停止",
                      command=lambda: self.on_action('stop', self.instance),
                      bootstyle="warning-outline" if TTKBOOTSTRAP_AVAILABLE else None,
                      width=8).pack(side=LEFT, padx=(0, 5))
            ttk.Button(actions, text="重启",
                      command=lambda: self.on_action('restart', self.instance),
                      bootstyle="info-outline" if TTKBOOTSTRAP_AVAILABLE else None,
                      width=8).pack(side=LEFT)
        elif self.instance.status == 'stopped':
            ttk.Button(actions, text="启动",
                      command=lambda: self.on_action('start', self.instance),
                      bootstyle="success-outline" if TTKBOOTSTRAP_AVAILABLE else None,
                      width=8).pack(side=LEFT, padx=(0, 5))
            ttk.Button(actions, text="删除",
                      command=lambda: self.on_action('delete', self.instance),
                      bootstyle="danger-outline" if TTKBOOTSTRAP_AVAILABLE else None,
                      width=8).pack(side=LEFT)
        elif self.instance.status == 'offline':
            ttk.Button(actions, text="重连",
                      command=lambda: self.on_action('reconnect', self.instance),
                      bootstyle="primary-outline" if TTKBOOTSTRAP_AVAILABLE else None,
                      width=8).pack(side=LEFT, padx=(0, 5))
            ttk.Button(actions, text="删除",
                      command=lambda: self.on_action('delete', self.instance),
                      bootstyle="danger-outline" if TTKBOOTSTRAP_AVAILABLE else None,
                      width=8).pack(side=LEFT)
    
    def _get_status_text(self) -> str:
        status_map = {
            'running': '运行中',
            'stopped': '已停止',
            'offline': '离线',
            'error': '错误'
        }
        return status_map.get(self.instance.status, self.instance.status)
    
    def _get_metric_color(self, value: float, warning: float, danger: float) -> str:
        if value >= danger:
            return '#EF4444'
        elif value >= warning:
            return '#F59E0B'
        return '#10B981'
    
    def _format_uptime(self, seconds: int) -> str:
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            return f"{seconds // 60}分钟"
        elif seconds < 86400:
            return f"{seconds // 3600}小时"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days}天{hours}小时"
    
    def _format_ago(self, delta: timedelta) -> str:
        if delta.days > 0:
            return f"{delta.days}天前"
        hours = delta.seconds // 3600
        if hours > 0:
            return f"{hours}小时前"
        minutes = delta.seconds // 60
        return f"{minutes}分钟前"


class InstancesPanel(ttk.Frame):
    """多实例管理面板"""
    
    def __init__(self, parent, app=None, theme_manager=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.theme_manager = theme_manager
        
        # 实例数据
        self.instances: List[InstanceInfo] = []
        self.selected_instance: Optional[InstanceInfo] = None
        self.monitoring = False
        
        # 加载保存的实例
        self._load_instances()
        
        self._build_ui()
        
        # 启动监控线程
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def _build_ui(self):
        """构建界面"""
        # 标题栏
        header = ttk.Frame(self)
        header.pack(fill=X, pady=(0, 10))
        
        ttk.Label(header, text="多实例管理", 
                 font=("Microsoft YaHei", 16, "bold")).pack(side=LEFT)
        
        ttk.Button(header, text="➕ 添加实例",
                  command=self._show_add_dialog,
                  bootstyle="primary" if TTKBOOTSTRAP_AVAILABLE else None).pack(side=RIGHT)
        
        # 筛选栏
        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill=X, pady=(0, 10))
        
        self.filter_var = ttk.StringVar(value="all")
        ttk.Combobox(filter_frame, textvariable=self.filter_var,
                    values=["全部", "运行中", "已停止", "离线"],
                    state="readonly", width=12).pack(side=LEFT, padx=(0, 10))
        
        self.search_var = ttk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.search_var,
                 width=30).pack(side=LEFT, padx=(0, 10))
        
        ttk.Button(filter_frame, text="🔍 搜索",
                  command=self._refresh_list).pack(side=LEFT, padx=(0, 10))
        
        ttk.Button(filter_frame, text="🔄 刷新",
                  command=self._refresh_all).pack(side=LEFT)
        
        # 主内容区：左右分栏
        content = ttk.Frame(self)
        content.pack(fill=BOTH, expand=True)
        
        # 左侧：实例列表
        left_frame = ttk.Frame(content)
        left_frame.pack(side=LEFT, fill=BOTH, expand=True)
        
        # 实例列表容器（带滚动条）
        list_container = ttk.Frame(left_frame)
        list_container.pack(fill=BOTH, expand=True)
        
        self.canvas = ttk.Canvas(list_container)
        scrollbar = ttk.Scrollbar(list_container, orient=VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=RIGHT, fill=Y)
        self.canvas.pack(side=LEFT, fill=BOTH, expand=True)
        
        self.instances_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.instances_frame, anchor=NW, width=500)
        
        self.instances_frame.bind("<Configure>", 
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        # 右侧：详情面板
        right_frame = ttk.LabelFrame(content, text="实例详情", padding=10, width=350)
        right_frame.pack(side=RIGHT, fill=BOTH, padx=(10, 0))
        right_frame.pack_propagate(False)
        
        self.detail_frame = ttk.Frame(right_frame)
        self.detail_frame.pack(fill=BOTH, expand=True)
        
        ttk.Label(self.detail_frame, text="选择一个实例查看详情",
                 foreground="#999").pack(expand=True)
        
        # 初始刷新
        self._refresh_list()
    
    def _load_instances(self):
        """从配置文件加载实例"""
        # 优先使用 core.instance_manager 的真实实例数据
        manager = getattr(self.app, "instance_manager", None) if self.app else None
        if manager:
            try:
                core_instances = manager.get_all_instances()
                status_map = {
                    "online": "running",
                    "offline": "offline",
                    "error": "error",
                    "connecting": "offline",
                    "unknown": "stopped",
                }
                type_map = {
                    "local": "local",
                    "remote_ssh": "ssh",
                    "remote_websocket": "tailscale",
                }

                self.instances = []
                for ci in core_instances:
                    c_status = getattr(getattr(ci, "status", None), "value", "unknown")
                    c_type = getattr(getattr(ci, "type", None), "value", "local")
                    self.instances.append(
                        InstanceInfo(
                            id=ci.id,
                            name=ci.name,
                            host=ci.host,
                            type=type_map.get(c_type, "local"),
                            status=status_map.get(c_status, "stopped"),
                            version=getattr(ci, "version", "") or "",
                        )
                    )

                # 若 core 中没有实例，补一个本地默认实例
                if not self.instances:
                    self.instances.append(
                        InstanceInfo(
                            id="local",
                            name="本地实例",
                            host="localhost",
                            type="local",
                            status="running",
                        )
                    )
                return
            except Exception as e:
                print(f"从核心模块加载实例失败，回退本地配置: {e}")

        config_path = os.path.expanduser("~/.openclaw/instances.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data.get('instances', []):
                        instance = InstanceInfo(**item)
                        self.instances.append(instance)
        except Exception as e:
            print(f"加载实例配置失败: {e}")
        
        # 如果没有实例，添加本地实例
        if not self.instances:
            self.instances.append(InstanceInfo(
                id="local",
                name="本地实例",
                host="localhost",
                type="local",
                status="running"
            ))
    
    def _save_instances(self):
        """保存实例配置"""
        config_path = os.path.expanduser("~/.openclaw/instances.json")
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            data = {
                'instances': [asdict(inst) for inst in self.instances]
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存实例配置失败: {e}")
    
    def _refresh_list(self):
        """刷新实例列表"""
        # 清空现有列表
        for widget in self.instances_frame.winfo_children():
            widget.destroy()
        
        # 筛选
        filter_type = self.filter_var.get()
        search_term = self.search_var.get().lower()
        
        filtered = self.instances
        if filter_type == "运行中":
            filtered = [i for i in filtered if i.status == 'running']
        elif filter_type == "已停止":
            filtered = [i for i in filtered if i.status == 'stopped']
        elif filter_type == "离线":
            filtered = [i for i in filtered if i.status == 'offline']
        
        if search_term:
            filtered = [i for i in filtered if 
                       search_term in i.name.lower() or 
                       search_term in i.host.lower()]
        
        # 显示实例卡片
        if not filtered:
            ttk.Label(self.instances_frame, text="暂无实例",
                     foreground="#999").pack(pady=20)
        else:
            for instance in filtered:
                card = InstanceCard(
                    self.instances_frame,
                    instance,
                    on_action=self._on_instance_action,
                    relief="solid",
                    borderwidth=1
                )
                card.pack(fill=X, pady=5, padx=5)
    
    def _refresh_all(self):
        """刷新所有实例状态"""
        # 优先通过 core manager 拉取最新状态
        manager = getattr(self.app, "instance_manager", None) if self.app else None
        if manager:
            try:
                self._load_instances()
                self._refresh_list()
                return
            except Exception as e:
                print(f"核心实例刷新失败，回退本地刷新: {e}")

        def worker():
            for instance in self.instances:
                self._check_instance_status(instance)
            self.after(0, self._refresh_list)
        
        threading.Thread(target=worker, daemon=True).start()
    
    def _check_instance_status(self, instance: InstanceInfo):
        """检查实例状态"""
        try:
            if instance.type == 'local':
                # 检查本地 OpenClaw
                result = subprocess.run(
                    "openclaw --version",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    instance.status = 'running'
                    instance.version = result.stdout.strip()
                    # 获取系统指标
                    self._get_local_metrics(instance)
                else:
                    instance.status = 'stopped'
            else:
                # 远程实例：通过 API 检查
                # TODO: 实现远程 API 调用
                pass
        except Exception as e:
            instance.status = 'error'
            instance.error_message = str(e)
    
    def _get_local_metrics(self, instance: InstanceInfo):
        """获取本地系统指标"""
        try:
            import psutil
            
            # CPU
            instance.cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # 内存
            mem = psutil.virtual_memory()
            instance.memory_mb = mem.used / 1024 / 1024
            instance.memory_total_mb = mem.total / 1024 / 1024
            
            # 运行时间
            boot_time = psutil.boot_time()
            instance.uptime_seconds = int(time.time() - boot_time)
            
        except ImportError:
            pass
    
    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring:
            for instance in self.instances:
                if instance.status == 'running':
                    self._check_instance_status(instance)
            # 每 5 秒刷新一次
            time.sleep(5)
            # 更新 UI
            if self.winfo_exists():
                self.after(0, self._refresh_list)
    
    def _on_instance_action(self, action: str, instance: InstanceInfo):
        """处理实例操作"""
        if action == 'connect':
            self._connect_instance(instance)
        elif action == 'start':
            self._start_instance(instance)
        elif action == 'stop':
            self._stop_instance(instance)
        elif action == 'restart':
            self._restart_instance(instance)
        elif action == 'delete':
            self._delete_instance(instance)
        elif action == 'reconnect':
            self._reconnect_instance(instance)
    
    def _show_add_dialog(self):
        """显示添加实例对话框"""
        dialog = ttk.Toplevel(self)
        dialog.title("添加实例")
        dialog.geometry("400x300")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        ttk.Label(dialog, text="实例名称:").pack(anchor=W, padx=10, pady=(10, 0))
        name_var = ttk.StringVar()
        ttk.Entry(dialog, textvariable=name_var).pack(fill=X, padx=10, pady=5)
        
        ttk.Label(dialog, text="连接类型:").pack(anchor=W, padx=10, pady=(10, 0))
        type_var = ttk.StringVar(value="ssh")
        ttk.Combobox(dialog, textvariable=type_var,
                    values=["ssh", "tailscale"],
                    state="readonly").pack(fill=X, padx=10, pady=5)
        
        ttk.Label(dialog, text="主机地址:").pack(anchor=W, padx=10, pady=(10, 0))
        host_var = ttk.StringVar()
        ttk.Entry(dialog, textvariable=host_var).pack(fill=X, padx=10, pady=5)
        
        def do_add():
            name = name_var.get().strip()
            host = host_var.get().strip()
            conn_type = type_var.get()
            
            if not name or not host:
                messagebox.showwarning("警告", "请填写完整信息", parent=dialog)
                return
            
            instance = InstanceInfo(
                id=f"{conn_type}_{int(time.time())}",
                name=name,
                host=host,
                type=conn_type,
                status='offline'
            )
            
            self.instances.append(instance)
            self._save_instances()
            self._refresh_list()
            dialog.destroy()
        
        ttk.Button(dialog, text="添加", command=do_add,
                  bootstyle="primary" if TTKBOOTSTRAP_AVAILABLE else None).pack(pady=20)
    
    def _connect_instance(self, instance: InstanceInfo):
        """连接远程实例"""
        manager = getattr(self.app, "instance_manager", None) if self.app else None
        if manager:
            try:
                ok = bool(manager.connect_instance(instance.id))
                if ok:
                    instance.status = "running"
                    self._refresh_list()
                    return
            except Exception as e:
                messagebox.showwarning("连接", f"通过核心模块连接失败，已回退本地逻辑: {e}")
        # 回退行为
        messagebox.showinfo("连接", f"正在连接到 {instance.name}...")
    
    def _start_instance(self, instance: InstanceInfo):
        """启动实例"""
        if instance.type == 'local':
            # 启动本地 OpenClaw
            try:
                subprocess.Popen("openclaw gateway start", shell=True)
                instance.status = 'running'
                manager = getattr(self.app, "instance_manager", None) if self.app else None
                if manager:
                    try:
                        manager.connect_instance(instance.id)
                    except Exception:
                        pass
                self._refresh_list()
            except Exception as e:
                messagebox.showerror("错误", f"启动失败: {e}")
    
    def _stop_instance(self, instance: InstanceInfo):
        """停止实例"""
        if messagebox.askyesno("确认", f"确定要停止 {instance.name} 吗?"):
            if instance.type == 'local':
                try:
                    subprocess.run("openclaw gateway stop", shell=True, timeout=10)
                    instance.status = 'stopped'
                    manager = getattr(self.app, "instance_manager", None) if self.app else None
                    if manager:
                        try:
                            manager.disconnect_instance(instance.id)
                        except Exception:
                            pass
                    self._refresh_list()
                except Exception as e:
                    messagebox.showerror("错误", f"停止失败: {e}")
    
    def _restart_instance(self, instance: InstanceInfo):
        """重启实例"""
        self._stop_instance(instance)
        time.sleep(2)
        self._start_instance(instance)
    
    def _delete_instance(self, instance: InstanceInfo):
        """删除实例"""
        if messagebox.askyesno("确认", f"确定要删除 {instance.name} 吗?\n此操作不可恢复。"):
            manager = getattr(self.app, "instance_manager", None) if self.app else None
            if manager:
                try:
                    manager.remove_instance(instance.id)
                except Exception:
                    pass
            self.instances.remove(instance)
            self._save_instances()
            self._refresh_list()
    
    def _reconnect_instance(self, instance: InstanceInfo):
        """重新连接实例"""
        manager = getattr(self.app, "instance_manager", None) if self.app else None
        if manager:
            try:
                manager.connect_instance(instance.id)
                instance.status = "running"
            except Exception:
                pass
        self._check_instance_status(instance)
        self._refresh_list()
    
    def on_show(self):
        """面板显示时调用"""
        self._refresh_all()
    
    def destroy(self):
        """销毁面板"""
        self.monitoring = False
        super().destroy()
