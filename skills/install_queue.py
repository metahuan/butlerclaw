#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw Butler - 技能安装队列管理器

功能：
1. 管理安装队列（添加、移除、重试）
2. 批量安装技能
3. 进度追踪
4. 依赖检查
5. 错误处理和重试
"""

import os
import json
import time
import threading
import subprocess
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
from queue import Queue, PriorityQueue


class InstallStatus(Enum):
    """安装状态"""
    PENDING = "pending"         # 等待中
    DOWNLOADING = "downloading" # 下载中
    INSTALLING = "installing"   # 安装中
    COMPLETED = "completed"     # 完成
    FAILED = "failed"          # 失败
    CANCELLED = "cancelled"    # 已取消
    RETRYING = "retrying"      # 重试中


@dataclass
class InstallTask:
    """安装任务"""
    id: str
    skill_id: str
    skill_name: str
    status: InstallStatus
    priority: int
    progress: int
    error: Optional[str]
    start_time: Optional[str]
    end_time: Optional[str]
    retry_count: int
    max_retries: int
    dependencies: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "status": self.status.value,
            "priority": self.priority,
            "progress": self.progress,
            "error": self.error,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "dependencies": self.dependencies
        }


@dataclass
class QueueStats:
    """队列统计"""
    total: int
    pending: int
    downloading: int
    installing: int
    completed: int
    failed: int
    overall_progress: float
    
    def to_dict(self) -> Dict:
        return asdict(self)


class InstallQueueManager:
    """技能安装队列管理器"""
    
    def __init__(self, max_concurrent: int = 1):
        self.max_concurrent = max_concurrent
        self.queue = PriorityQueue()
        self.tasks: Dict[str, InstallTask] = {}
        self.current_tasks: Dict[str, InstallTask] = {}
        self.completed_tasks: List[InstallTask] = []
        
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # 回调函数
        self.on_task_start: Optional[Callable[[InstallTask], None]] = None
        self.on_task_progress: Optional[Callable[[InstallTask, int], None]] = None
        self.on_task_complete: Optional[Callable[[InstallTask], None]] = None
        self.on_task_failed: Optional[Callable[[InstallTask, str], None]] = None
        self.on_queue_update: Optional[Callable[[QueueStats], None]] = None
    
    def start(self):
        """启动队列处理器"""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._stop_event.clear()
            self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
            self._worker_thread.start()
    
    def stop(self):
        """停止队列处理器"""
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
    
    def add_task(
        self,
        skill_id: str,
        skill_name: str = None,
        priority: int = 5,
        dependencies: List[str] = None
    ) -> InstallTask:
        """
        添加安装任务到队列
        
        Args:
            skill_id: 技能ID
            skill_name: 技能名称（可选）
            priority: 优先级（1-10，数字越小优先级越高）
            dependencies: 依赖的技能ID列表
            
        Returns:
            InstallTask: 创建的任务
        """
        task_id = f"{skill_id}_{int(time.time() * 1000)}"
        
        task = InstallTask(
            id=task_id,
            skill_id=skill_id,
            skill_name=skill_name or skill_id,
            status=InstallStatus.PENDING,
            priority=priority,
            progress=0,
            error=None,
            start_time=None,
            end_time=None,
            retry_count=0,
            max_retries=3,
            dependencies=dependencies or []
        )
        
        with self._lock:
            self.tasks[task_id] = task
            # 优先级队列使用负值（数值越小优先级越高）
            self.queue.put((priority, task_id))
        
        self._notify_queue_update()
        return task
    
    def batch_add(
        self,
        skill_ids: List[str],
        priority: int = 5
    ) -> List[InstallTask]:
        """批量添加安装任务"""
        tasks = []
        for skill_id in skill_ids:
            task = self.add_task(skill_id, priority=priority)
            tasks.append(task)
        return tasks
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            if task_id in self.current_tasks:
                # 正在执行的任务无法直接取消，标记为取消中
                task = self.current_tasks[task_id]
                task.status = InstallStatus.CANCELLED
                return True
            
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if task.status == InstallStatus.PENDING:
                    task.status = InstallStatus.CANCELLED
                    return True
        
        return False
    
    def retry_task(self, task_id: str) -> bool:
        """重试失败的任务"""
        with self._lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            if task.status != InstallStatus.FAILED:
                return False
            
            if task.retry_count >= task.max_retries:
                return False
            
            task.status = InstallStatus.PENDING
            task.retry_count += 1
            task.error = None
            task.progress = 0
            
            self.queue.put((task.priority, task_id))
        
        self._notify_queue_update()
        return True
    
    def remove_task(self, task_id: str) -> bool:
        """从队列中移除任务"""
        with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if task.status in (InstallStatus.PENDING, InstallStatus.FAILED, InstallStatus.CANCELLED):
                    del self.tasks[task_id]
                    return True
        return False
    
    def get_task(self, task_id: str) -> Optional[InstallTask]:
        """获取任务信息"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[InstallTask]:
        """获取所有任务"""
        with self._lock:
            return list(self.tasks.values())
    
    def get_stats(self) -> QueueStats:
        """获取队列统计"""
        with self._lock:
            tasks = list(self.tasks.values())
            
            total = len(tasks)
            pending = sum(1 for t in tasks if t.status == InstallStatus.PENDING)
            downloading = sum(1 for t in tasks if t.status == InstallStatus.DOWNLOADING)
            installing = sum(1 for t in tasks if t.status == InstallStatus.INSTALLING)
            completed = sum(1 for t in tasks if t.status == InstallStatus.COMPLETED)
            failed = sum(1 for t in tasks if t.status == InstallStatus.FAILED)
            
            # 计算整体进度
            if total == 0:
                overall_progress = 0.0
            else:
                total_progress = sum(t.progress for t in tasks)
                overall_progress = total_progress / (total * 100)
            
            return QueueStats(
                total=total,
                pending=pending,
                downloading=downloading,
                installing=installing,
                completed=completed,
                failed=failed,
                overall_progress=overall_progress
            )
    
    def _process_queue(self):
        """处理队列的主循环"""
        while not self._stop_event.is_set():
            try:
                # 获取任务
                priority, task_id = self.queue.get(timeout=1)
                
                with self._lock:
                    if task_id not in self.tasks:
                        continue
                    
                    task = self.tasks[task_id]
                    
                    # 检查任务状态
                    if task.status != InstallStatus.PENDING:
                        continue
                    
                    # 检查并发限制
                    if len(self.current_tasks) >= self.max_concurrent:
                        # 放回队列
                        self.queue.put((priority, task_id))
                        time.sleep(0.5)
                        continue
                    
                    # 检查依赖
                    if not self._check_dependencies(task):
                        # 依赖未满足，放回队列
                        self.queue.put((priority + 1, task_id))  # 降低优先级
                        time.sleep(1)
                        continue
                    
                    # 开始执行任务
                    task.status = InstallStatus.INSTALLING
                    task.start_time = datetime.now().isoformat()
                    self.current_tasks[task_id] = task
                
                # 执行安装
                self._execute_install(task)
                
            except Exception as e:
                print(f"队列处理错误: {e}")
                time.sleep(1)
    
    def _check_dependencies(self, task: InstallTask) -> bool:
        """检查依赖是否满足"""
        if not task.dependencies:
            return True
        
        with self._lock:
            for dep_id in task.dependencies:
                # 检查依赖是否已完成
                dep_completed = any(
                    t.skill_id == dep_id and t.status == InstallStatus.COMPLETED
                    for t in self.tasks.values()
                )
                if not dep_completed:
                    return False
        
        return True
    
    def _execute_install(self, task: InstallTask):
        """执行安装"""
        try:
            # 通知开始
            if self.on_task_start:
                self.on_task_start(task)
            
            # 更新进度
            self._update_progress(task, 10)
            
            # 执行安装命令
            cmd = f"npx skills add {task.skill_id} -y -g"
            
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )
            
            # 实时读取输出
            while True:
                output = process.stdout.readline()
                if output == "" and process.poll() is not None:
                    break
                
                if output:
                    # 解析进度
                    progress = self._parse_progress(output)
                    if progress > task.progress:
                        self._update_progress(task, progress)
            
            # 等待完成
            return_code = process.poll()
            
            if return_code == 0:
                # 安装成功
                self._update_progress(task, 100)
                task.status = InstallStatus.COMPLETED
                task.end_time = datetime.now().isoformat()
                
                if self.on_task_complete:
                    self.on_task_complete(task)
            else:
                # 安装失败
                stderr = process.stderr.read() if process.stderr else ""
                error_msg = stderr[:200] if stderr else f"安装失败，返回码 {return_code}"
                
                self._handle_install_error(task, error_msg)
            
        except Exception as e:
            self._handle_install_error(task, str(e))
        
        finally:
            # 清理
            with self._lock:
                if task.id in self.current_tasks:
                    del self.current_tasks[task.id]
                if task.status == InstallStatus.COMPLETED:
                    self.completed_tasks.append(task)
            
            self._notify_queue_update()
    
    def _parse_progress(self, output: str) -> int:
        """解析安装进度"""
        # 根据输出内容估算进度
        output_lower = output.lower()
        
        if "cloning" in output_lower or "downloading" in output_lower:
            return 30
        elif "installing" in output_lower:
            return 60
        elif "completed" in output_lower or "done" in output_lower:
            return 90
        
        return 0
    
    def _update_progress(self, task: InstallTask, progress: int):
        """更新进度"""
        task.progress = min(progress, 100)
        
        if self.on_task_progress:
            self.on_task_progress(task, task.progress)
        
        self._notify_queue_update()
    
    def _handle_install_error(self, task: InstallTask, error_msg: str):
        """处理安装错误"""
        task.error = error_msg
        
        # 检查是否可以重试
        if task.retry_count < task.max_retries:
            task.status = InstallStatus.RETRYING
            task.retry_count += 1
            
            # 延迟后重试
            time.sleep(2 ** task.retry_count)  # 指数退避
            
            with self._lock:
                self.queue.put((task.priority, task.id))
        else:
            task.status = InstallStatus.FAILED
            task.end_time = datetime.now().isoformat()
            
            if self.on_task_failed:
                self.on_task_failed(task, error_msg)
    
    def _notify_queue_update(self):
        """通知队列更新"""
        if self.on_queue_update:
            stats = self.get_stats()
            self.on_queue_update(stats)
    
    def pause(self):
        """暂停队列处理"""
        self._stop_event.set()
    
    def resume(self):
        """恢复队列处理"""
        self._stop_event.clear()
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self.start()
    
    def clear_completed(self):
        """清理已完成的任务"""
        with self._lock:
            completed_ids = [
                task_id for task_id, task in self.tasks.items()
                if task.status == InstallStatus.COMPLETED
            ]
            for task_id in completed_ids:
                del self.tasks[task_id]
        
        self._notify_queue_update()
    
    def export_queue_state(self) -> Dict:
        """导出队列状态"""
        return {
            "tasks": [task.to_dict() for task in self.tasks.values()],
            "stats": self.get_stats().to_dict(),
            "exported_at": datetime.now().isoformat()
        }
    
    def import_queue_state(self, state: Dict):
        """导入队列状态"""
        tasks_data = state.get("tasks", [])
        
        for task_data in tasks_data:
            if task_data.get("status") == InstallStatus.PENDING.value:
                self.add_task(
                    skill_id=task_data["skill_id"],
                    skill_name=task_data.get("skill_name"),
                    priority=task_data.get("priority", 5)
                )


# 便捷函数
_queue_manager: Optional[InstallQueueManager] = None


def get_queue_manager() -> InstallQueueManager:
    """获取全局队列管理器实例"""
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = InstallQueueManager()
        _queue_manager.start()
    return _queue_manager


def install_skill(skill_id: str, skill_name: str = None, priority: int = 5) -> InstallTask:
    """安装单个技能的便捷函数"""
    manager = get_queue_manager()
    return manager.add_task(skill_id, skill_name, priority)


def batch_install_skills(skill_ids: List[str], priority: int = 5) -> List[InstallTask]:
    """批量安装技能的便捷函数"""
    manager = get_queue_manager()
    return manager.batch_add(skill_ids, priority)


def get_install_progress() -> QueueStats:
    """获取安装进度的便捷函数"""
    manager = get_queue_manager()
    return manager.get_stats()
