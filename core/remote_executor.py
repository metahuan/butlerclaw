#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core.remote_executor

远程执行模块：
- SSH 连接管理（连接池、密钥认证）
- WebSocket 远程连接
- 统一的远程命令执行接口
"""

from __future__ import annotations

import os
import json
import time
import socket
import asyncio
import threading
import subprocess
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Union
from datetime import datetime, timedelta
from pathlib import Path
import logging

# 可选依赖，延迟导入
PARAMIKO_AVAILABLE = False
WEBSOCKET_AVAILABLE = False

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    pass

try:
    import websockets
    WEBSOCKET_AVAILABLE = True
except ImportError:
    pass


logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    """连接状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class SSHConfig:
    """SSH 连接配置"""
    host: str
    port: int = 22
    username: str = ""
    password: Optional[str] = None
    key_path: Optional[str] = None
    key_password: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3


@dataclass
class WSConfig:
    """WebSocket 连接配置"""
    url: str
    token: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    ping_interval: int = 30
    reconnect_interval: int = 5
    max_reconnect: int = 10


@dataclass
class RemoteResult:
    """远程执行结果"""
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    execution_time_ms: float = 0.0
    connection_type: str = ""
    error_message: str = ""


class SSHConnection:
    """SSH 连接管理器（带连接池）"""
    
    def __init__(self, config: SSHConfig):
        self.config = config
        self._client: Optional[Any] = None
        self._sftp: Optional[Any] = None
        self._status = ConnectionStatus.DISCONNECTED
        self._lock = threading.RLock()
        self._last_used = datetime.now()
        self._connection_time: Optional[datetime] = None
        
    @property
    def status(self) -> ConnectionStatus:
        return self._status
    
    @property
    def is_connected(self) -> bool:
        with self._lock:
            if not PARAMIKO_AVAILABLE or not self._client:
                return False
            try:
                # 发送空包检测连接
                self._client.get_transport().send_ignore()
                return self._client.get_transport().is_active()
            except Exception:
                self._status = ConnectionStatus.ERROR
                return False
    
    def connect(self) -> bool:
        """建立 SSH 连接"""
        if not PARAMIKO_AVAILABLE:
            logger.error("SSH 功能需要 paramiko: pip install paramiko")
            self._status = ConnectionStatus.ERROR
            return False
        
        with self._lock:
            if self.is_connected:
                return True
            
            self._status = ConnectionStatus.CONNECTING
            
            for attempt in range(self.config.max_retries):
                try:
                    self._client = paramiko.SSHClient()
                    self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    
                    connect_kwargs = {
                        "hostname": self.config.host,
                        "port": self.config.port,
                        "username": self.config.username,
                        "timeout": self.config.timeout,
                        "allow_agent": False,
                        "look_for_keys": False,
                    }
                    
                    # 优先使用密钥认证
                    if self.config.key_path and os.path.exists(self.config.key_path):
                        private_key = paramiko.RSAKey.from_private_key_file(
                            self.config.key_path,
                            password=self.config.key_password
                        )
                        connect_kwargs["pkey"] = private_key
                    elif self.config.password:
                        connect_kwargs["password"] = self.config.password
                    else:
                        # 尝试使用系统 SSH agent
                        connect_kwargs["allow_agent"] = True
                        connect_kwargs["look_for_keys"] = True
                    
                    self._client.connect(**connect_kwargs)
                    self._status = ConnectionStatus.CONNECTED
                    self._connection_time = datetime.now()
                    self._last_used = datetime.now()
                    
                    logger.info(f"SSH 连接成功: {self.config.host}:{self.config.port}")
                    return True
                    
                except paramiko.AuthenticationException as e:
                    logger.error(f"SSH 认证失败: {e}")
                    self._status = ConnectionStatus.ERROR
                    return False
                except socket.timeout:
                    logger.warning(f"SSH 连接超时 (尝试 {attempt + 1}/{self.config.max_retries})")
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"SSH 连接错误: {e}")
                    time.sleep(1)
            
            self._status = ConnectionStatus.ERROR
            return False
    
    def disconnect(self):
        """断开 SSH 连接"""
        with self._lock:
            try:
                if self._sftp:
                    self._sftp.close()
                    self._sftp = None
                if self._client:
                    self._client.close()
                    self._client = None
            except Exception as e:
                logger.warning(f"断开 SSH 连接时出错: {e}")
            finally:
                self._status = ConnectionStatus.DISCONNECTED
                self._connection_time = None
    
    def execute(self, command: str, timeout: int = 60, get_pty: bool = False) -> RemoteResult:
        """在远程主机执行命令"""
        start_time = time.time()
        
        if not self.is_connected:
            if not self.connect():
                return RemoteResult(
                    success=False,
                    stderr=f"无法连接到 {self.config.host}",
                    exit_code=-1,
                    connection_type="ssh"
                )
        
        try:
            with self._lock:
                self._last_used = datetime.now()
                
                stdin, stdout, stderr = self._client.exec_command(
                    command,
                    timeout=timeout,
                    get_pty=get_pty
                )
                
                exit_code = stdout.channel.recv_exit_status()
                stdout_data = stdout.read().decode('utf-8', errors='ignore')
                stderr_data = stderr.read().decode('utf-8', errors='ignore')
                
                return RemoteResult(
                    success=exit_code == 0,
                    stdout=stdout_data,
                    stderr=stderr_data,
                    exit_code=exit_code,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    connection_type="ssh"
                )
                
        except socket.timeout:
            return RemoteResult(
                success=False,
                stderr=f"命令执行超时 ({timeout}s)",
                exit_code=-1,
                execution_time_ms=(time.time() - start_time) * 1000,
                connection_type="ssh"
            )
        except Exception as e:
            logger.error(f"SSH 执行错误: {e}")
            self._status = ConnectionStatus.ERROR
            return RemoteResult(
                success=False,
                stderr=str(e),
                exit_code=-1,
                execution_time_ms=(time.time() - start_time) * 1000,
                connection_type="ssh"
            )
    
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """上传文件到远程主机"""
        if not self.is_connected:
            if not self.connect():
                return False
        
        try:
            with self._lock:
                if not self._sftp:
                    self._sftp = self._client.open_sftp()
                self._sftp.put(local_path, remote_path)
                return True
        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            return False
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """从远程主机下载文件"""
        if not self.is_connected:
            if not self.connect():
                return False
        
        try:
            with self._lock:
                if not self._sftp:
                    self._sftp = self._client.open_sftp()
                self._sftp.get(remote_path, local_path)
                return True
        except Exception as e:
            logger.error(f"文件下载失败: {e}")
            return False


class WebSocketConnection:
    """WebSocket 连接管理器（异步）"""
    
    def __init__(self, config: WSConfig):
        self.config = config
        self._ws: Optional[Any] = None
        self._status = ConnectionStatus.DISCONNECTED
        self._lock = asyncio.Lock()
        self._reconnect_count = 0
        self._message_handlers: List[Callable] = []
        self._running = False
        self._receive_task: Optional[asyncio.Task] = None
        
    @property
    def status(self) -> ConnectionStatus:
        return self._status
    
    async def connect(self) -> bool:
        """建立 WebSocket 连接"""
        if not WEBSOCKET_AVAILABLE:
            logger.error("WebSocket 功能需要 websockets: pip install websockets")
            self._status = ConnectionStatus.ERROR
            return False
        
        async with self._lock:
            if self._status == ConnectionStatus.CONNECTED:
                return True
            
            self._status = ConnectionStatus.CONNECTING
            
            try:
                headers = self.config.headers.copy()
                if self.config.token:
                    headers["Authorization"] = f"Bearer {self.config.token}"
                
                self._ws = await websockets.connect(
                    self.config.url,
                    extra_headers=headers,
                    ping_interval=self.config.ping_interval
                )
                
                self._status = ConnectionStatus.CONNECTED
                self._reconnect_count = 0
                self._running = True
                
                # 启动接收任务
                self._receive_task = asyncio.create_task(self._receive_loop())
                
                logger.info(f"WebSocket 连接成功: {self.config.url}")
                return True
                
            except Exception as e:
                logger.error(f"WebSocket 连接失败: {e}")
                self._status = ConnectionStatus.ERROR
                return False
    
    async def disconnect(self):
        """断开 WebSocket 连接"""
        self._running = False
        
        async with self._lock:
            if self._receive_task:
                self._receive_task.cancel()
                try:
                    await self._receive_task
                except asyncio.CancelledError:
                    pass
                self._receive_task = None
            
            if self._ws:
                try:
                    await self._ws.close()
                except Exception:
                    pass
                self._ws = None
            
            self._status = ConnectionStatus.DISCONNECTED
    
    async def _receive_loop(self):
        """接收消息循环"""
        while self._running:
            try:
                if not self._ws:
                    break
                
                message = await asyncio.wait_for(
                    self._ws.recv(),
                    timeout=self.config.ping_interval * 2
                )
                
                # 解析消息
                try:
                    data = json.loads(message)
                    for handler in self._message_handlers:
                        try:
                            handler(data)
                        except Exception as e:
                            logger.error(f"消息处理器错误: {e}")
                except json.JSONDecodeError:
                    logger.warning(f"收到非 JSON 消息: {message}")
                    
            except asyncio.TimeoutError:
                # 发送 ping
                try:
                    if self._ws:
                        await self._ws.ping()
                except Exception:
                    break
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket 连接已关闭")
                break
            except Exception as e:
                logger.error(f"接收消息错误: {e}")
                break
        
        # 尝试重连
        if self._running and self._reconnect_count < self.config.max_reconnect:
            self._reconnect_count += 1
            logger.info(f"尝试重连 ({self._reconnect_count}/{self.config.max_reconnect})...")
            await asyncio.sleep(self.config.reconnect_interval)
            await self.connect()
    
    async def send(self, data: Dict[str, Any]) -> bool:
        """发送消息"""
        async with self._lock:
            if not self._ws or self._status != ConnectionStatus.CONNECTED:
                return False
            
            try:
                await self._ws.send(json.dumps(data))
                return True
            except Exception as e:
                logger.error(f"发送消息失败: {e}")
                return False
    
    async def execute(self, command: str, timeout: int = 60) -> RemoteResult:
        """通过 WebSocket 执行命令"""
        start_time = time.time()
        
        if self._status != ConnectionStatus.CONNECTED:
            if not await self.connect():
                return RemoteResult(
                    success=False,
                    stderr=f"无法连接到 {self.config.url}",
                    exit_code=-1,
                    connection_type="websocket"
                )
        
        # 发送执行请求
        request_id = f"exec_{int(time.time() * 1000)}"
        request = {
            "type": "execute",
            "id": request_id,
            "command": command,
            "timeout": timeout
        }
        
        if not await self.send(request):
            return RemoteResult(
                success=False,
                stderr="发送执行请求失败",
                exit_code=-1,
                execution_time_ms=(time.time() - start_time) * 1000,
                connection_type="websocket"
            )
        
        # 等待响应（简化实现，实际应使用 future）
        # TODO: 实现请求-响应匹配机制
        return RemoteResult(
            success=True,
            stdout="命令已发送，异步执行中",
            exit_code=0,
            execution_time_ms=(time.time() - start_time) * 1000,
            connection_type="websocket"
        )
    
    def on_message(self, handler: Callable[[Dict[str, Any]], None]):
        """注册消息处理器"""
        self._message_handlers.append(handler)


class RemoteExecutor:
    """远程执行器（统一管理 SSH 和 WebSocket 连接）"""
    
    def __init__(self):
        self._ssh_connections: Dict[str, SSHConnection] = {}
        self._ws_connections: Dict[str, WebSocketConnection] = {}
        self._lock = threading.RLock()
        self._cleanup_interval = 300  # 5分钟清理一次
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """启动清理线程"""
        def cleanup_loop():
            while True:
                time.sleep(self._cleanup_interval)
                self._cleanup_idle_connections()
        
        thread = threading.Thread(target=cleanup_loop, daemon=True)
        thread.start()
    
    def _cleanup_idle_connections(self, max_idle_seconds: int = 600):
        """清理空闲连接"""
        with self._lock:
            now = datetime.now()
            to_remove = []
            
            for conn_id, conn in self._ssh_connections.items():
                if (now - conn._last_used).seconds > max_idle_seconds:
                    conn.disconnect()
                    to_remove.append(conn_id)
            
            for conn_id in to_remove:
                del self._ssh_connections[conn_id]
                logger.info(f"清理空闲 SSH 连接: {conn_id}")
    
    def get_ssh_connection(self, config: SSHConfig) -> SSHConnection:
        """获取或创建 SSH 连接"""
        conn_id = f"{config.username}@{config.host}:{config.port}"
        
        with self._lock:
            if conn_id not in self._ssh_connections:
                self._ssh_connections[conn_id] = SSHConnection(config)
            
            return self._ssh_connections[conn_id]
    
    def get_ws_connection(self, config: WSConfig) -> WebSocketConnection:
        """获取或创建 WebSocket 连接"""
        conn_id = config.url
        
        with self._lock:
            if conn_id not in self._ws_connections:
                self._ws_connections[conn_id] = WebSocketConnection(config)
            
            return self._ws_connections[conn_id]
    
    def execute_ssh(self, config: SSHConfig, command: str, timeout: int = 60) -> RemoteResult:
        """通过 SSH 执行命令"""
        conn = self.get_ssh_connection(config)
        return conn.execute(command, timeout)
    
    async def execute_ws(self, config: WSConfig, command: str, timeout: int = 60) -> RemoteResult:
        """通过 WebSocket 执行命令"""
        conn = self.get_ws_connection(config)
        return await conn.execute(command, timeout)
    
    def close_all(self):
        """关闭所有连接"""
        with self._lock:
            for conn in self._ssh_connections.values():
                conn.disconnect()
            self._ssh_connections.clear()
            
            # WebSocket 连接需要异步关闭
            # TODO: 实现异步关闭
            self._ws_connections.clear()


# 全局执行器实例
_global_executor: Optional[RemoteExecutor] = None


def get_remote_executor() -> RemoteExecutor:
    """获取全局远程执行器"""
    global _global_executor
    if _global_executor is None:
        _global_executor = RemoteExecutor()
    return _global_executor


def check_dependencies() -> Dict[str, bool]:
    """检查依赖可用性"""
    return {
        "paramiko": PARAMIKO_AVAILABLE,
        "websockets": WEBSOCKET_AVAILABLE,
    }


if __name__ == "__main__":
    # 简单测试
    deps = check_dependencies()
    print(f"依赖检查: {deps}")
    
    if deps["paramiko"]:
        print("✅ SSH 功能可用")
    else:
        print("❌ SSH 功能需要: pip install paramiko")
    
    if deps["websockets"]:
        print("✅ WebSocket 功能可用")
    else:
        print("❌ WebSocket 功能需要: pip install websockets")
