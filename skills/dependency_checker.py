#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw Butler - 技能依赖检查器

功能：
1. 检查技能安装前的依赖
2. 自动修复依赖
3. 生成依赖报告
"""

import os
import re
import json
import shutil
import subprocess
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class DependencyStatus(Enum):
    """依赖状态"""
    SATISFIED = "satisfied"      # 已满足
    MISSING = "missing"          # 缺失
    VERSION_MISMATCH = "version_mismatch"  # 版本不匹配
    OPTIONAL = "optional"        # 可选


@dataclass
class DependencyCheck:
    """依赖检查结果"""
    name: str
    type: str  # node, npm_package, system_bin, env_var, disk_space
    status: DependencyStatus
    required: str
    found: Optional[str]
    message: str
    auto_fixable: bool
    fix_command: Optional[str]


@dataclass
class DependencyReport:
    """依赖检查报告"""
    skill_id: str
    can_install: bool
    checks: List[DependencyCheck]
    auto_fixable: List[DependencyCheck]
    manual_required: List[DependencyCheck]
    summary: str
    
    def to_dict(self) -> Dict:
        return {
            "skill_id": self.skill_id,
            "can_install": self.can_install,
            "checks": [
                {
                    "name": c.name,
                    "type": c.type,
                    "status": c.status.value,
                    "required": c.required,
                    "found": c.found,
                    "message": c.message,
                    "auto_fixable": c.auto_fixable,
                    "fix_command": c.fix_command
                }
                for c in self.checks
            ],
            "auto_fixable_count": len(self.auto_fixable),
            "manual_required_count": len(self.manual_required),
            "summary": self.summary
        }


class DependencyChecker:
    """技能依赖检查器"""
    
    # 常见技能依赖配置（可以从 skill 的 SKILL.md 中解析）
    SKILL_DEPENDENCIES = {
        "skill-vetter": {
            "node_version": ">=14.0.0",
            "packages": [],
            "bins": ["node", "npm"],
            "env": [],
            "size_mb": 5
        },
        "playwright-mcp": {
            "node_version": ">=16.0.0",
            "packages": ["@playwright/mcp"],
            "bins": ["node", "npx"],
            "env": ["PLAYWRIGHT_BROWSERS_PATH"],
            "size_mb": 100
        },
        "api-gateway": {
            "node_version": ">=14.0.0",
            "packages": [],
            "bins": ["node", "npm"],
            "env": [],
            "size_mb": 10
        },
        "ontology": {
            "node_version": ">=14.0.0",
            "packages": [],
            "bins": ["node"],
            "env": [],
            "size_mb": 5
        }
    }
    
    def __init__(self):
        self.checks = []
    
    def check_before_install(self, skill_id: str, custom_requirements: Dict = None) -> DependencyReport:
        """
        安装前检查依赖
        
        Args:
            skill_id: 技能ID
            custom_requirements: 自定义依赖要求（可选）
            
        Returns:
            DependencyReport: 依赖检查报告
        """
        # 获取依赖要求
        requirements = custom_requirements or self.SKILL_DEPENDENCIES.get(skill_id, {})
        
        checks = []
        
        # 检查 Node.js 版本
        if "node_version" in requirements:
            checks.append(self._check_node_version(requirements["node_version"]))
        
        # 检查 npm 包
        if "packages" in requirements:
            for package in requirements["packages"]:
                checks.append(self._check_npm_package(package))
        
        # 检查系统命令
        if "bins" in requirements:
            for bin_name in requirements["bins"]:
                checks.append(self._check_system_bin(bin_name))
        
        # 检查环境变量
        if "env" in requirements:
            for env_var in requirements["env"]:
                checks.append(self._check_env_var(env_var))
        
        # 检查磁盘空间
        if "size_mb" in requirements:
            checks.append(self._check_disk_space(requirements["size_mb"]))
        
        # 分类
        auto_fixable = [c for c in checks if c.auto_fixable and c.status != DependencyStatus.SATISFIED]
        manual_required = [c for c in checks if not c.auto_fixable and c.status != DependencyStatus.SATISFIED]
        
        # 判断是否可以安装
        can_install = len([c for c in checks if c.status == DependencyStatus.MISSING and not c.auto_fixable]) == 0
        
        # 生成总结
        summary = self._generate_summary(checks, can_install)
        
        return DependencyReport(
            skill_id=skill_id,
            can_install=can_install,
            checks=checks,
            auto_fixable=auto_fixable,
            manual_required=manual_required,
            summary=summary
        )
    
    def _check_node_version(self, required: str) -> DependencyCheck:
        """检查 Node.js 版本"""
        try:
            result = subprocess.run(
                "node --version",
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=10
            )
            
            if result.returncode != 0:
                return DependencyCheck(
                    name="Node.js",
                    type="node",
                    status=DependencyStatus.MISSING,
                    required=required,
                    found=None,
                    message="Node.js 未安装",
                    auto_fixable=False,
                    fix_command=None
                )
            
            version = result.stdout.strip().lstrip("v")
            
            # 版本比较
            if self._version_satisfies(version, required):
                return DependencyCheck(
                    name="Node.js",
                    type="node",
                    status=DependencyStatus.SATISFIED,
                    required=required,
                    found=version,
                    message=f"Node.js 版本符合要求 ({version})",
                    auto_fixable=False,
                    fix_command=None
                )
            else:
                return DependencyCheck(
                    name="Node.js",
                    type="node",
                    status=DependencyStatus.VERSION_MISMATCH,
                    required=required,
                    found=version,
                    message=f"Node.js 版本过低: {version}，需要 {required}",
                    auto_fixable=False,
                    fix_command="请访问 https://nodejs.org 下载并安装最新 LTS 版本"
                )
                
        except Exception as e:
            return DependencyCheck(
                name="Node.js",
                type="node",
                status=DependencyStatus.MISSING,
                required=required,
                found=None,
                message=f"检查 Node.js 时出错: {str(e)}",
                auto_fixable=False,
                fix_command=None
            )
    
    def _check_npm_package(self, package: str) -> DependencyCheck:
        """检查 npm 包"""
        try:
            result = subprocess.run(
                f"npm list -g {package}",
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=10
            )
            
            if result.returncode == 0:
                return DependencyCheck(
                    name=f"npm包: {package}",
                    type="npm_package",
                    status=DependencyStatus.SATISFIED,
                    required=package,
                    found="已安装",
                    message=f"npm 包 {package} 已安装",
                    auto_fixable=False,
                    fix_command=None
                )
            else:
                return DependencyCheck(
                    name=f"npm包: {package}",
                    type="npm_package",
                    status=DependencyStatus.MISSING,
                    required=package,
                    found=None,
                    message=f"npm 包 {package} 未安装",
                    auto_fixable=True,
                    fix_command=f"npm install -g {package}"
                )
                
        except Exception as e:
            return DependencyCheck(
                name=f"npm包: {package}",
                type="npm_package",
                status=DependencyStatus.MISSING,
                required=package,
                found=None,
                message=f"检查 npm 包时出错: {str(e)}",
                auto_fixable=False,
                fix_command=None
            )
    
    def _check_system_bin(self, bin_name: str) -> DependencyCheck:
        """检查系统命令"""
        try:
            # 使用 where (Windows) 或 which (Unix)
            cmd = f"where {bin_name}" if os.name == "nt" else f"which {bin_name}"
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=10
            )
            
            if result.returncode == 0:
                path = result.stdout.strip().split("\n")[0]
                return DependencyCheck(
                    name=f"命令: {bin_name}",
                    type="system_bin",
                    status=DependencyStatus.SATISFIED,
                    required=bin_name,
                    found=path,
                    message=f"命令 {bin_name} 已安装 ({path})",
                    auto_fixable=False,
                    fix_command=None
                )
            else:
                return DependencyCheck(
                    name=f"命令: {bin_name}",
                    type="system_bin",
                    status=DependencyStatus.MISSING,
                    required=bin_name,
                    found=None,
                    message=f"命令 {bin_name} 未找到",
                    auto_fixable=False,
                    fix_command=f"请安装 {bin_name}"
                )
                
        except Exception as e:
            return DependencyCheck(
                name=f"命令: {bin_name}",
                type="system_bin",
                status=DependencyStatus.MISSING,
                required=bin_name,
                found=None,
                message=f"检查命令时出错: {str(e)}",
                auto_fixable=False,
                fix_command=None
            )
    
    def _check_env_var(self, env_var: str) -> DependencyCheck:
        """检查环境变量"""
        value = os.getenv(env_var)
        
        if value:
            return DependencyCheck(
                name=f"环境变量: {env_var}",
                type="env_var",
                status=DependencyStatus.SATISFIED,
                required=env_var,
                found=value[:20] + "..." if len(value) > 20 else value,
                message=f"环境变量 {env_var} 已设置",
                auto_fixable=False,
                fix_command=None
            )
        else:
            return DependencyCheck(
                name=f"环境变量: {env_var}",
                type="env_var",
                status=DependencyStatus.OPTIONAL,
                required=env_var,
                found=None,
                message=f"环境变量 {env_var} 未设置（可选）",
                auto_fixable=False,
                fix_command=f"set {env_var}=value" if os.name == "nt" else f"export {env_var}=value"
            )
    
    def _check_disk_space(self, required_mb: int) -> DependencyCheck:
        """检查磁盘空间"""
        try:
            # 获取配置目录所在磁盘的空间
            path = os.path.expanduser("~/.openclaw")
            os.makedirs(path, exist_ok=True)
            
            if os.name == "nt":
                # Windows
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(path),
                    ctypes.pointer(free_bytes),
                    None,
                    None
                )
                free_mb = free_bytes.value / (1024 * 1024)
            else:
                # Unix
                stat = shutil.disk_usage(path)
                free_mb = stat.free / (1024 * 1024)
            
            if free_mb >= required_mb:
                return DependencyCheck(
                    name="磁盘空间",
                    type="disk_space",
                    status=DependencyStatus.SATISFIED,
                    required=f"{required_mb} MB",
                    found=f"{int(free_mb)} MB",
                    message=f"磁盘空间充足 ({int(free_mb)} MB 可用)",
                    auto_fixable=False,
                    fix_command=None
                )
            else:
                return DependencyCheck(
                    name="磁盘空间",
                    type="disk_space",
                    status=DependencyStatus.MISSING,
                    required=f"{required_mb} MB",
                    found=f"{int(free_mb)} MB",
                    message=f"磁盘空间不足: 需要 {required_mb} MB，仅剩 {int(free_mb)} MB",
                    auto_fixable=False,
                    fix_command="请清理磁盘空间或更换安装位置"
                )
                
        except Exception as e:
            return DependencyCheck(
                name="磁盘空间",
                type="disk_space",
                status=DependencyStatus.OPTIONAL,
                required=f"{required_mb} MB",
                found="未知",
                message=f"无法检查磁盘空间: {str(e)}",
                auto_fixable=False,
                fix_command=None
            )
    
    def _version_satisfies(self, version: str, requirement: str) -> bool:
        """检查版本是否满足要求"""
        try:
            # 解析版本号
            v_parts = [int(x) for x in version.split(".")[:2]]
            
            # 解析要求
            req = requirement.strip()
            if req.startswith(">="):
                req_version = req[2:].strip()
                req_parts = [int(x) for x in req_version.split(".")[:2]]
                return v_parts >= req_parts
            elif req.startswith(">"):
                req_version = req[1:].strip()
                req_parts = [int(x) for x in req_version.split(".")[:2]]
                return v_parts > req_parts
            else:
                # 精确匹配
                req_parts = [int(x) for x in req.split(".")[:2]]
                return v_parts == req_parts
        except Exception:
            return False
    
    def _generate_summary(self, checks: List[DependencyCheck], can_install: bool) -> str:
        """生成总结"""
        satisfied = len([c for c in checks if c.status == DependencyStatus.SATISFIED])
        optional = len([c for c in checks if c.status == DependencyStatus.OPTIONAL])
        missing = len([c for c in checks if c.status == DependencyStatus.MISSING])
        version_mismatch = len([c for c in checks if c.status == DependencyStatus.VERSION_MISMATCH])
        
        if can_install:
            return f"✅ 依赖检查通过 ({satisfied}/{len(checks)} 项满足)"
        else:
            issues = []
            if missing > 0:
                issues.append(f"{missing} 项缺失")
            if version_mismatch > 0:
                issues.append(f"{version_mismatch} 项版本不匹配")
            return f"❌ 依赖检查未通过: {', '.join(issues)}"
    
    def auto_fix_dependencies(self, report: DependencyReport) -> Tuple[bool, List[str]]:
        """
        自动修复依赖
        
        Returns:
            (是否全部修复成功, 错误信息列表)
        """
        errors = []
        
        for check in report.auto_fixable:
            if check.fix_command:
                try:
                    result = subprocess.run(
                        check.fix_command,
                        shell=True,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="ignore",
                        timeout=120
                    )
                    
                    if result.returncode != 0:
                        errors.append(f"{check.name}: {result.stderr[:100]}")
                        
                except Exception as e:
                    errors.append(f"{check.name}: {str(e)}")
        
        return len(errors) == 0, errors


# 便捷函数
def check_skill_dependencies(skill_id: str, custom_requirements: Dict = None) -> DependencyReport:
    """检查技能依赖的便捷函数"""
    checker = DependencyChecker()
    return checker.check_before_install(skill_id, custom_requirements)


def can_install_skill(skill_id: str) -> bool:
    """快速检查是否可以安装技能的便捷函数"""
    report = check_skill_dependencies(skill_id)
    return report.can_install
