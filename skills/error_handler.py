#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw Butler - 技能安装错误处理器

功能：
1. 智能错误识别和分类
2. 提供解决方案
3. 重试策略
4. 离线安装支持
"""

import re
import os
import json
import shutil
import subprocess
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class ErrorType(Enum):
    """错误类型"""
    RATE_LIMIT = "rate_limit"           # API 速率限制
    NETWORK_ERROR = "network_error"     # 网络错误
    PERMISSION_DENIED = "permission_denied"  # 权限不足
    SKILL_NOT_FOUND = "skill_not_found" # 技能不存在
    DEPENDENCY_MISSING = "dependency_missing"  # 依赖缺失
    TIMEOUT = "timeout"                 # 超时
    UNKNOWN = "unknown"                 # 未知错误


@dataclass
class ErrorAnalysis:
    """错误分析结果"""
    error_type: ErrorType
    message: str
    solutions: List[str]
    retry_strategy: Dict
    can_auto_retry: bool


@dataclass
class RetryStrategy:
    """重试策略"""
    should_retry: bool
    delay_seconds: int
    max_retries: int
    requires_manual_fix: bool
    alternative_actions: List[str]


class InstallErrorHandler:
    """技能安装错误处理器"""
    
    # 错误模式匹配
    ERROR_PATTERNS = {
        ErrorType.RATE_LIMIT: {
            "patterns": [
                "rate limit exceeded",
                "403",
                "api rate limit",
                "too many requests",
                "你已被限制"
            ],
            "message": "GitHub API 速率限制",
            "solutions": [
                "等待1小时后重试",
                "配置 GitHub Token 提高限额",
                "使用代理访问 GitHub",
                "尝试离线安装"
            ],
            "retry_strategy": {
                "should_retry": True,
                "delay_seconds": 3600,
                "max_retries": 3,
                "requires_manual_fix": False
            }
        },
        ErrorType.NETWORK_ERROR: {
            "patterns": [
                "connection refused",
                "timeout",
                "reset",
                "could not connect",
                "network is unreachable",
                "connection reset",
                "failed to connect",
                "unable to access"
            ],
            "message": "网络连接问题",
            "solutions": [
                "检查网络连接",
                "配置代理服务器",
                "使用离线安装",
                "更换网络环境"
            ],
            "retry_strategy": {
                "should_retry": True,
                "delay_seconds": 30,
                "max_retries": 5,
                "requires_manual_fix": False
            }
        },
        ErrorType.PERMISSION_DENIED: {
            "patterns": [
                "permission denied",
                "eacces",
                "access denied",
                "operation not permitted",
                "权限",
                "拒绝访问"
            ],
            "message": "权限不足",
            "solutions": [
                "以管理员身份运行程序",
                "修改目录权限: chmod -R 755 ~/.openclaw",
                "使用 nvm 管理 Node.js",
                "更改 npm 全局安装目录"
            ],
            "retry_strategy": {
                "should_retry": False,
                "delay_seconds": 0,
                "max_retries": 0,
                "requires_manual_fix": True
            }
        },
        ErrorType.SKILL_NOT_FOUND: {
            "patterns": [
                "not found",
                "404",
                "repository not found",
                "does not exist",
                "repository .* does not exist"
            ],
            "message": "技能不存在或无法访问",
            "solutions": [
                "检查技能名称拼写",
                "搜索正确的技能ID: npx skills find <关键词>",
                "查看 ClawHub 上的可用技能列表",
                "确认技能是否已被删除或设为私有"
            ],
            "retry_strategy": {
                "should_retry": False,
                "delay_seconds": 0,
                "max_retries": 0,
                "requires_manual_fix": True
            }
        },
        ErrorType.DEPENDENCY_MISSING: {
            "patterns": [
                "command not found",
                "is not recognized",
                "cannot find",
                "missing dependency",
                "module not found"
            ],
            "message": "依赖缺失",
            "solutions": [
                "安装缺失的依赖",
                "检查 PATH 环境变量",
                "重新安装 Node.js",
                "使用依赖检查器查看详细依赖"
            ],
            "retry_strategy": {
                "should_retry": False,
                "delay_seconds": 0,
                "max_retries": 0,
                "requires_manual_fix": True
            }
        },
        ErrorType.TIMEOUT: {
            "patterns": [
                "timeout",
                "timed out",
                "operation timed out",
                "deadline exceeded"
            ],
            "message": "操作超时",
            "solutions": [
                "检查网络稳定性",
                "增加超时时间",
                "稍后重试",
                "使用更快的网络"
            ],
            "retry_strategy": {
                "should_retry": True,
                "delay_seconds": 60,
                "max_retries": 3,
                "requires_manual_fix": False
            }
        }
    }
    
    def __init__(self):
        self.error_history = []
    
    def analyze_error(self, error_output: str, skill_id: str = None) -> ErrorAnalysis:
        """
        分析错误输出
        
        Args:
            error_output: 错误输出文本
            skill_id: 技能ID（可选）
            
        Returns:
            ErrorAnalysis: 错误分析结果
        """
        error_lower = error_output.lower()
        
        # 尝试匹配已知错误模式
        for error_type, info in self.ERROR_PATTERNS.items():
            for pattern in info["patterns"]:
                if pattern.lower() in error_lower:
                    return ErrorAnalysis(
                        error_type=error_type,
                        message=info["message"],
                        solutions=info["solutions"],
                        retry_strategy=info["retry_strategy"],
                        can_auto_retry=info["retry_strategy"]["should_retry"]
                    )
        
        # 未知错误
        return ErrorAnalysis(
            error_type=ErrorType.UNKNOWN,
            message="未知错误",
            solutions=[
                "查看详细错误日志",
                "尝试重新安装",
                "检查网络连接",
                "联系技能开发者"
            ],
            retry_strategy={
                "should_retry": True,
                "delay_seconds": 30,
                "max_retries": 2,
                "requires_manual_fix": False
            },
            can_auto_retry=True
        )
    
    def get_retry_strategy(self, error_type: ErrorType) -> RetryStrategy:
        """获取重试策略"""
        info = self.ERROR_PATTERNS.get(error_type)
        
        if info:
            strategy = info["retry_strategy"]
            return RetryStrategy(
                should_retry=strategy["should_retry"],
                delay_seconds=strategy["delay_seconds"],
                max_retries=strategy["max_retries"],
                requires_manual_fix=strategy["requires_manual_fix"],
                alternative_actions=info["solutions"]
            )
        
        # 默认策略
        return RetryStrategy(
            should_retry=True,
            delay_seconds=30,
            max_retries=2,
            requires_manual_fix=False,
            alternative_actions=["稍后重试", "查看日志"]
        )
    
    def should_retry(self, error_output: str, retry_count: int) -> Tuple[bool, int]:
        """
        判断是否应该重试
        
        Returns:
            (是否重试, 延迟秒数)
        """
        analysis = self.analyze_error(error_output)
        strategy = self.get_retry_strategy(analysis.error_type)
        
        if not strategy.should_retry:
            return False, 0
        
        if retry_count >= strategy.max_retries:
            return False, 0
        
        # 指数退避
        delay = strategy.delay_seconds * (2 ** retry_count)
        return True, delay
    
    def generate_error_report(self, skill_id: str, error_output: str, retry_count: int = 0) -> Dict:
        """生成错误报告"""
        analysis = self.analyze_error(error_output, skill_id)
        strategy = self.get_retry_strategy(analysis.error_type)
        
        return {
            "skill_id": skill_id,
            "error_type": analysis.error_type.value,
            "error_message": analysis.message,
            "solutions": analysis.solutions,
            "can_auto_retry": analysis.can_auto_retry,
            "retry_count": retry_count,
            "max_retries": strategy.max_retries,
            "should_retry": strategy.should_retry and retry_count < strategy.max_retries,
            "requires_manual_fix": strategy.requires_manual_fix,
            "alternative_actions": strategy.alternative_actions,
            "raw_error": error_output[:500]  # 限制长度
        }


class OfflineInstaller:
    """离线安装支持"""
    
    def __init__(self, skills_dir: str = None):
        if skills_dir is None:
            skills_dir = os.path.expanduser("~/.openclaw/skills")
        self.skills_dir = skills_dir
    
    def install_from_file(self, file_path: str) -> Dict:
        """
        从本地文件安装技能
        
        支持格式:
        - .skill (OpenClaw 技能包)
        - .zip (ZIP 压缩包)
        - .tar.gz (tar.gz 压缩包)
        - 文件夹 (解压后的技能目录)
        """
        if not os.path.exists(file_path):
            return {"success": False, "error": f"文件不存在: {file_path}"}
        
        try:
            # 获取技能名称
            skill_name = os.path.splitext(os.path.basename(file_path))[0]
            target_dir = os.path.join(self.skills_dir, skill_name)
            
            # 如果目标目录已存在，先备份
            if os.path.exists(target_dir):
                backup_dir = f"{target_dir}.bak"
                if os.path.exists(backup_dir):
                    shutil.rmtree(backup_dir)
                shutil.move(target_dir, backup_dir)
            
            # 根据文件类型处理
            if file_path.endswith(".skill") or file_path.endswith(".zip"):
                shutil.unpack_archive(file_path, target_dir)
            elif file_path.endswith(".tar.gz"):
                shutil.unpack_archive(file_path, target_dir, "gztar")
            elif os.path.isdir(file_path):
                shutil.copytree(file_path, target_dir)
            else:
                return {"success": False, "error": f"不支持的文件格式: {file_path}"}
            
            # 验证安装
            skill_md = os.path.join(target_dir, "SKILL.md")
            if not os.path.exists(skill_md):
                return {
                    "success": False,
                    "error": "安装包中未找到 SKILL.md，可能不是有效的技能包",
                    "target_dir": target_dir
                }
            
            return {
                "success": True,
                "message": f"技能 {skill_name} 安装成功",
                "target_dir": target_dir,
                "skill_name": skill_name
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def install_from_folder(self, folder_path: str) -> Dict:
        """从本地文件夹安装技能"""
        return self.install_from_file(folder_path)
    
    def export_skill_package(self, skill_id: str, output_path: str = None) -> Dict:
        """
        导出技能包
        
        将已安装的技能打包为 .skill 文件，便于离线分发
        """
        skill_dir = os.path.join(self.skills_dir, skill_id)
        
        if not os.path.exists(skill_dir):
            return {"success": False, "error": f"技能 {skill_id} 未安装"}
        
        try:
            if output_path is None:
                output_path = f"{skill_id}.skill"
            
            # 创建 ZIP 包
            shutil.make_archive(
                output_path.replace(".skill", ""),
                "zip",
                skill_dir
            )
            
            # 重命名为 .skill
            zip_path = output_path.replace(".skill", ".zip")
            if os.path.exists(output_path):
                os.remove(output_path)
            os.rename(zip_path, output_path)
            
            return {
                "success": True,
                "message": f"技能包已导出: {output_path}",
                "output_path": output_path
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_offline_bundle(self, skill_ids: List[str], output_path: str = None) -> Dict:
        """
        创建离线安装包
        
        将多个技能及其依赖打包为一个离线安装包
        """
        import tempfile
        
        try:
            # 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                bundle_dir = os.path.join(temp_dir, "openclaw-skills-bundle")
                os.makedirs(bundle_dir)
                
                # 复制技能
                exported_skills = []
                failed_skills = []
                
                for skill_id in skill_ids:
                    skill_dir = os.path.join(self.skills_dir, skill_id)
                    if os.path.exists(skill_dir):
                        target = os.path.join(bundle_dir, skill_id)
                        shutil.copytree(skill_dir, target)
                        exported_skills.append(skill_id)
                    else:
                        failed_skills.append(skill_id)
                
                # 创建清单文件
                manifest = {
                    "name": "OpenClaw Skills Bundle",
                    "version": "1.0",
                    "skills": exported_skills,
                    "created_at": __import__('datetime').datetime.now().isoformat()
                }
                
                with open(os.path.join(bundle_dir, "manifest.json"), "w") as f:
                    json.dump(manifest, f, indent=2)
                
                # 打包
                if output_path is None:
                    output_path = f"openclaw-skills-bundle-{len(exported_skills)}.zip"
                
                shutil.make_archive(
                    output_path.replace(".zip", ""),
                    "zip",
                    bundle_dir
                )
                
                return {
                    "success": True,
                    "message": f"离线安装包已创建: {output_path}",
                    "output_path": output_path,
                    "exported_skills": exported_skills,
                    "failed_skills": failed_skills
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def install_offline_bundle(self, bundle_path: str) -> Dict:
        """安装离线安装包"""
        if not os.path.exists(bundle_path):
            return {"success": False, "error": f"安装包不存在: {bundle_path}"}
        
        try:
            import tempfile
            
            # 解压到临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                extract_dir = os.path.join(temp_dir, "bundle")
                shutil.unpack_archive(bundle_path, extract_dir)
                
                # 读取清单
                manifest_path = os.path.join(extract_dir, "manifest.json")
                if os.path.exists(manifest_path):
                    with open(manifest_path, "r") as f:
                        manifest = json.load(f)
                    skills = manifest.get("skills", [])
                else:
                    # 没有清单，尝试直接安装所有子目录
                    skills = [d for d in os.listdir(extract_dir) 
                             if os.path.isdir(os.path.join(extract_dir, d))]
                
                # 安装技能
                installed = []
                failed = []
                
                for skill_id in skills:
                    skill_source = os.path.join(extract_dir, skill_id)
                    skill_target = os.path.join(self.skills_dir, skill_id)
                    
                    try:
                        if os.path.exists(skill_target):
                            shutil.rmtree(skill_target)
                        shutil.copytree(skill_source, skill_target)
                        installed.append(skill_id)
                    except Exception as e:
                        failed.append({"skill": skill_id, "error": str(e)})
                
                return {
                    "success": len(failed) == 0,
                    "message": f"已安装 {len(installed)} 个技能",
                    "installed": installed,
                    "failed": failed
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}


# 便捷函数
def handle_install_error(error_output: str, skill_id: str = None, retry_count: int = 0) -> Dict:
    """处理安装错误的便捷函数"""
    handler = InstallErrorHandler()
    return handler.generate_error_report(skill_id, error_output, retry_count)


def should_retry_install(error_output: str, retry_count: int) -> Tuple[bool, int]:
    """判断是否应重试安装的便捷函数"""
    handler = InstallErrorHandler()
    return handler.should_retry(error_output, retry_count)


def install_skill_offline(file_path: str) -> Dict:
    """离线安装技能的便捷函数"""
    installer = OfflineInstaller()
    return installer.install_from_file(file_path)
