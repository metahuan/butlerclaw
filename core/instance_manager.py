#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core.instance_manager

多实例管理模块：
- 本地实例发现（进程扫描、配置读取）
- 远程实例连接（SSH/WebSocket）
- 实例状态监控（心跳检测、资源使用）
- 统一操作接口（跨实例命令执行）
"""

from __future__ import annotations

import os
import json
import time
import socket
import asyncio
import threading
import subprocess
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Union
from datetime import datetime

# 导入远程执行模块
try:
    from .remote_executor import (
        RemoteExecutor, SSHConnection, WebSocketConnection,
        SSHConfig, WSConfig, RemoteResult, get_remote_executor
    )
    REMOTE_EXECUTOR_AVAILABLE = True
except ImportError:
    REMOTE_EXECUTOR_AVAILABLE = False


class InstanceStatus(Enum):
    """实例状态枚举"""
    UNKNOWN = "unknown"
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    CONNECTING = "connecting"


class InstanceType(Enum):
    """实例类型枚举"""
    LOCAL = "local"
    REMOTE_SSH = "remote_ssh"
    REMOTE_WS = "remote_websocket"


@dataclass
class ResourceUsage:
    """资源使用情况"""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_mb: float = 0.0
    disk_percent: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class InstanceInfo:
    """实例信息"""
    id: str
    name: str
    host: str
    port: int
    type: InstanceType
    status: InstanceStatus = InstanceStatus.UNKNOWN
    version: str = ""
    last_heartbeat: Optional[datetime] = None
    resource_usage: Optional[ResourceUsage] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class CommandResult:
    """命令执行结果"""
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    execution_time_ms: float = 0.0
    instance_id: str = ""


class InstanceManager:
    """
    多实例管理器 - 核心接口
    
    统一管理本地和远程 OpenClaw 实例
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = config_dir or os.path.expanduser("~/.openclaw")
        self._instances: Dict[str, InstanceInfo] = {}
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
    
    # ========== 实例管理接口 ==========
    
    def discover_instances(self) -> List[InstanceInfo]:
        """
        发现本地实例
        
        TODO: 实现完整的进程扫描和配置读取
        - 扫描 OpenClaw 进程
        - 读取配置文件中的实例
        - 扫描工作目录
        """
        instances = []
        
        # 基础实现：扫描工作目录
        workspace_dir = os.path.join(self.config_dir, "workspace")
        if os.path.exists(workspace_dir):
            try:
                for item in os.listdir(workspace_dir):
                    item_path = os.path.join(workspace_dir, item)
                    if os.path.isdir(item_path):
                        instance_id = f"local-workspace-{item}"
                        instances.append(InstanceInfo(
                            id=instance_id,
                            name=f"工作区: {item}",
                            host="localhost",
                            port=0,
                            type=InstanceType.LOCAL,
                            status=InstanceStatus.ONLINE,
                            metadata={"workspace_path": item_path}
                        ))
            except Exception as e:
                print(f"[警告] 扫描工作目录失败: {e}")
        
        with self._lock:
            for instance in instances:
                if instance.id not in self._instances:
                    self._instances[instance.id] = instance
        
        return instances
    
    def add_instance(self, instance: InstanceInfo) -> bool:
        """添加实例"""
        try:
            with self._lock:
                self._instances[instance.id] = instance
            self._save_instances()
            return True
        except Exception as e:
            print(f"[错误] 添加实例失败: {e}")
            return False
    
    def remove_instance(self, instance_id: str) -> bool:
        """移除实例"""
        try:
            with self._lock:
                if instance_id in self._instances:
                    del self._instances[instance_id]
            self._save_instances()
            return True
        except Exception as e:
            print(f"[错误] 移除实例失败: {e}")
            return False
    
    def get_instance(self, instance_id: str) -> Optional[InstanceInfo]:
        """获取实例信息"""
        with self._lock:
            return self._instances.get(instance_id)
    
    def get_all_instances(self) -> List[InstanceInfo]:
        """获取所有实例"""
        with self._lock:
            return list(self._instances.values())
    
    def get_online_instances(self) -> List[InstanceInfo]:
        """获取在线实例"""
        with self._lock:
            return [i for i in self._instances.values() if i.status == InstanceStatus.ONLINE]
    
    # ========== 连接管理接口 ==========
    
    def connect_instance(self, instance_id: str) -> bool:
        """
        连接远程实例
        
        TODO: 实现 SSH 和 WebSocket 连接
        - SSH 连接（需要 paramiko）
        - WebSocket 连接（需要 websockets）
        """
        instance = self.get_instance(instance_id)
        if not instance:
            return False
        
        # 基础实现：本地实例直接返回在线
        if instance.type == InstanceType.LOCAL:
            instance.status = InstanceStatus.ONLINE
            return True
        
        # TODO: 实现远程连接
        print(f"[TODO] 远程连接功能待实现: {instance.type.value}")
        return False
    
    def disconnect_instance(self, instance_id: str) -> bool:
        """断开实例连接"""
        instance = self.get_instance(instance_id)
        if instance:
            instance.status = InstanceStatus.OFFLINE
        return True
    
    # ========== 命令执行接口 ==========
    
    def execute_command(self, instance_id: str, command: str, timeout: int = 60) -> CommandResult:
        """
        在实例上执行命令
        
        支持本地执行、SSH 远程执行、WebSocket 远程执行
        """
        instance = self.get_instance(instance_id)
        if not instance:
            return CommandResult(success=False, stderr="实例不存在")
        
        start_time = time.time()
        
        try:
            if instance.type == InstanceType.LOCAL:
                # 本地执行
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    encoding="utf-8",
                    errors="ignore"
                )
                
                return CommandResult(
                    success=result.returncode == 0,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exit_code=result.returncode,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    instance_id=instance_id
                )
            
            elif instance.type == InstanceType.REMOTE_SSH:
                # SSH 远程执行
                if not REMOTE_EXECUTOR_AVAILABLE:
                    return CommandResult(
                        success=False,
                        stderr="SSH 功能不可用，请安装依赖: pip install paramiko",
                        exit_code=-1,
                        instance_id=instance_id
                    )
                
                # 从实例元数据获取 SSH 配置
                ssh_config = SSHConfig(
                    host=instance.host,
                    port=instance.metadata.get("ssh_port", 22),
                    username=instance.metadata.get("ssh_user", ""),
                    password=instance.metadata.get("ssh_password"),
                    key_path=instance.metadata.get("ssh_key_path"),
                    timeout=timeout
                )
                
                executor = get_remote_executor()
                remote_result = executor.execute_ssh(ssh_config, command, timeout)
                
                return CommandResult(
                    success=remote_result.success,
                    stdout=remote_result.stdout,
                    stderr=remote_result.stderr,
                    exit_code=remote_result.exit_code,
                    execution_time_ms=remote_result.execution_time_ms,
                    instance_id=instance_id
                )
            
            elif instance.type == InstanceType.REMOTE_WS:
                # WebSocket 远程执行（异步）
                if not REMOTE_EXECUTOR_AVAILABLE:
                    return CommandResult(
                        success=False,
                        stderr="WebSocket 功能不可用，请安装依赖: pip install websockets",
                        exit_code=-1,
                        instance_id=instance_id
                    )
                
                # 构建 WebSocket URL
                ws_url = instance.metadata.get("ws_url", f"ws://{instance.host}:{instance.port}/ws")
                ws_config = WSConfig(
                    url=ws_url,
                    token=instance.metadata.get("ws_token"),
                    ping_interval=30
                )
                
                # 在同步上下文中运行异步代码
                try:
                    executor = get_remote_executor()
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    remote_result = loop.run_until_complete(
                        executor.execute_ws(ws_config, command, timeout)
                    )
                    loop.close()
                    
                    return CommandResult(
                        success=remote_result.success,
                        stdout=remote_result.stdout,
                        stderr=remote_result.stderr,
                        exit_code=remote_result.exit_code,
                        execution_time_ms=remote_result.execution_time_ms,
                        instance_id=instance_id
                    )
                except Exception as e:
                    return CommandResult(
                        success=False,
                        stderr=f"WebSocket 执行错误: {str(e)}",
                        exit_code=-1,
                        execution_time_ms=(time.time() - start_time) * 1000,
                        instance_id=instance_id
                    )
            
            else:
                return CommandResult(
                    success=False,
                    stderr=f"不支持的实例类型: {instance.type.value}",
                    exit_code=-1,
                    instance_id=instance_id
                )
        
        except subprocess.TimeoutExpired:
            return CommandResult(
                success=False,
                stderr="命令执行超时",
                exit_code=-1,
                execution_time_ms=(time.time() - start_time) * 1000,
                instance_id=instance_id
            )
        except Exception as e:
            return CommandResult(
                success=False,
                stderr=str(e),
                exit_code=-1,
                execution_time_ms=(time.time() - start_time) * 1000,
                instance_id=instance_id
            )
    
    def broadcast_command(self, command: str, timeout: int = 60) -> Dict[str, CommandResult]:
        """向所有在线实例广播命令"""
        results = {}
        for instance in self.get_online_instances():
            results[instance.id] = self.execute_command(instance.id, command, timeout)
        return results
    
    # ========== 监控接口 ==========
    
    def get_resource_usage(self, instance_id: str) -> Optional[ResourceUsage]:
        """
        获取实例资源使用情况
        
        TODO: 实现资源监控
        - CPU、内存、磁盘使用率
        - 网络流量统计
        """
        instance = self.get_instance(instance_id)
        if not instance or instance.type != InstanceType.LOCAL:
            return None
        
        try:
            import psutil
            
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            
            return ResourceUsage(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_mb=memory.used / 1024 / 1024,
                disk_percent=disk.percent
            )
        except ImportError:
            return ResourceUsage()
    
    def start_monitoring(self, interval: int = 30):
        """
        启动实例监控
        
        TODO: 实现心跳检测和状态监控
        """
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,), daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """停止实例监控"""
        self._running = False
    
    def _monitor_loop(self, interval: int):
        """监控循环"""
        while self._running:
            for instance in self.get_all_instances():
                # TODO: 实现心跳检测
                instance.last_heartbeat = datetime.now()
            time.sleep(interval)
    
    # ========== 持久化接口 ==========
    
    def _save_instances(self):
        """保存实例配置到文件"""
        try:
            config_path = os.path.join(self.config_dir, "instances.json")
            os.makedirs(self.config_dir, exist_ok=True)
            
            with self._lock:
                data = {
                    "instances": [
                        {
                            "id": i.id,
                            "name": i.name,
                            "host": i.host,
                            "port": i.port,
                            "type": i.type.value,
                            "status": i.status.value,
                            "version": i.version,
                            "metadata": i.metadata,
                            "created_at": i.created_at.isoformat(),
                            "updated_at": i.updated_at.isoformat(),
                        }
                        for i in self._instances.values()
                    ],
                    "updated_at": datetime.now().isoformat()
                }
            
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[警告] 保存实例配置失败: {e}")
    
    def load_instances(self):
        """从文件加载实例配置"""
        try:
            config_path = os.path.join(self.config_dir, "instances.json")
            
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                with self._lock:
                    for item in data.get("instances", []):
                        instance = InstanceInfo(
                            id=item["id"],
                            name=item["name"],
                            host=item["host"],
                            port=item.get("port", 0),
                            type=InstanceType(item.get("type", "local")),
                            status=InstanceStatus(item.get("status", "unknown")),
                            version=item.get("version", ""),
                            metadata=item.get("metadata", {}),
                            created_at=datetime.fromisoformat(item.get("created_at", datetime.now().isoformat())),
                            updated_at=datetime.fromisoformat(item.get("updated_at", datetime.now().isoformat())),
                        )
                        self._instances[instance.id] = instance
        except Exception as e:
            print(f"[警告] 加载实例配置失败: {e}")


# 便捷函数
def get_instance_manager() -> InstanceManager:
    """获取全局实例管理器"""
    return InstanceManager()
