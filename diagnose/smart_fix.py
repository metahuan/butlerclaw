#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw Butler - 智能修复助手

功能：
1. 分析问题并提供修复方案
2. 自动修复（无需用户确认）
3. 引导修复（需要用户确认）
4. 手动修复（提供详细指导）
5. 生成修复脚本
"""

import os
import re
import json
import shutil
import subprocess
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class FixLevel(Enum):
    """修复级别"""
    AUTO = "auto"           # 自动修复，无需确认
    GUIDED = "guided"       # 引导修复，需要确认
    MANUAL = "manual"       # 手动修复，提供指导
    NOT_FIXABLE = "not_fixable"  # 无法修复


@dataclass
class FixResult:
    """修复结果"""
    success: bool
    message: str
    level: FixLevel
    requires_restart: bool = False
    backup_path: Optional[str] = None
    details: Optional[str] = None


@dataclass
class FixAction:
    """修复动作"""
    name: str
    description: str
    level: FixLevel
    action: Callable[[], FixResult]
    can_auto_fix: bool = False


class SmartFixAssistant:
    """智能修复助手"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.expanduser("~/.openclaw/openclaw.json")
        self.config_path = config_path
        self.config_dir = os.path.dirname(config_path)
        self._fix_strategies = self._init_fix_strategies()
    
    def analyze_and_fix(self, issue: Dict) -> FixResult:
        """
        分析问题并提供修复方案
        
        Args:
            issue: 问题信息，包含 name, status, message, category 等
            
        Returns:
            FixResult: 修复结果
        """
        issue_type = self._classify_issue(issue)
        strategy = self._fix_strategies.get(issue_type)
        
        if not strategy:
            return FixResult(
                success=False,
                message=f"暂不支持自动修复: {issue.get('name', '未知问题')}",
                level=FixLevel.NOT_FIXABLE,
                details="请查看诊断详情手动处理"
            )
        
        return strategy(issue)
    
    def _classify_issue(self, issue: Dict) -> str:
        """分类问题类型"""
        name = issue.get("name", "").lower()
        message = issue.get("message", "").lower()
        category = issue.get("category", "").lower()
        
        # 配置文件问题
        if "config" in category or "json" in message:
            if "unrecognized" in message or "unknown" in message:
                return "config_unknown_keys"
            if "parse" in message or "invalid" in message:
                return "config_invalid_json"
            if "missing" in message:
                return "config_missing_structure"
        
        # 环境问题
        if "node" in name or "nodejs" in message:
            return "env_node_missing"
        if "npm" in name:
            return "env_npm_issue"
        if "path" in name:
            return "env_path_issue"
        
        # 工具问题
        if "openclaw" in name and "cli" in name:
            return "tool_openclaw_missing"
        
        # 权限问题
        if "permission" in message or "eacces" in message:
            return "security_permission"
        
        # API Key 问题
        if "api key" in message or "apikey" in name:
            return "config_api_key"
        
        return "unknown"
    
    def _init_fix_strategies(self) -> Dict[str, Callable]:
        """初始化修复策略"""
        return {
            "config_unknown_keys": self._fix_config_unknown_keys,
            "config_invalid_json": self._fix_config_invalid_json,
            "config_missing_structure": self._fix_config_missing_structure,
            "config_api_key": self._fix_config_api_key,
            "env_node_missing": self._fix_env_node_missing,
            "env_npm_issue": self._fix_env_npm_issue,
            "tool_openclaw_missing": self._fix_tool_openclaw_missing,
            "security_permission": self._fix_security_permission,
        }
    
    def _backup_config(self) -> Optional[str]:
        """备份配置文件"""
        if not os.path.exists(self.config_path):
            return None
        
        try:
            timestamp = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.config_path}.bak.{timestamp}"
            shutil.copy2(self.config_path, backup_path)
            return backup_path
        except Exception as e:
            print(f"备份失败: {e}")
            return None
    
    def _fix_config_unknown_keys(self, issue: Dict) -> FixResult:
        """修复配置文件中的未知键"""
        backup = self._backup_config()
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 移除 models 下的未知键
            if "models" in data and isinstance(data["models"], dict):
                # 保留标准键
                standard_keys = {"providers", "aliases", "defaults"}
                models = data["models"]
                removed_keys = []
                
                for key in list(models.keys()):
                    if key not in standard_keys:
                        del models[key]
                        removed_keys.append(key)
                
                if removed_keys:
                    with open(self.config_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    
                    return FixResult(
                        success=True,
                        message=f"已移除未识别的配置键: {', '.join(removed_keys)}",
                        level=FixLevel.AUTO,
                        requires_restart=False,
                        backup_path=backup,
                        details="这些键是旧版本或第三方工具添加的，当前版本不支持"
                    )
            
            return FixResult(
                success=True,
                message="配置文件已检查，未发现需要移除的键",
                level=FixLevel.AUTO,
                backup_path=backup
            )
            
        except Exception as e:
            return FixResult(
                success=False,
                message=f"修复失败: {str(e)}",
                level=FixLevel.MANUAL,
                backup_path=backup,
                details="请手动编辑配置文件，或点击'一键修复'重置为默认配置"
            )
    
    def _fix_config_invalid_json(self, issue: Dict) -> FixResult:
        """修复无效的 JSON 配置"""
        backup = self._backup_config()
        
        try:
            # 尝试读取并重新格式化
            with open(self.config_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 尝试解析
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                # 如果解析失败，创建最小配置
                minimal = {"models": {"providers": {}}}
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(minimal, f, ensure_ascii=False, indent=2)
                
                return FixResult(
                    success=True,
                    message="配置文件已损坏，已重置为最小配置",
                    level=FixLevel.GUIDED,
                    requires_restart=True,
                    backup_path=backup,
                    details="原配置已备份，您需要重新配置模型和API Key"
                )
            
            # 如果能解析，重新格式化保存
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return FixResult(
                success=True,
                message="配置文件已修复并重新格式化",
                level=FixLevel.AUTO,
                backup_path=backup
            )
            
        except Exception as e:
            return FixResult(
                success=False,
                message=f"修复失败: {str(e)}",
                level=FixLevel.MANUAL,
                backup_path=backup,
                details="请手动检查配置文件语法，或使用在线JSON校验工具"
            )
    
    def _fix_config_missing_structure(self, issue: Dict) -> FixResult:
        """修复缺失的配置结构"""
        backup = self._backup_config()
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        data = {}
            else:
                data = {}
            
            if not isinstance(data, dict):
                data = {}
            
            # 确保必要的结构存在
            changed = False
            
            if "models" not in data:
                data["models"] = {}
                changed = True
            
            if "providers" not in data.get("models", {}):
                data["models"]["providers"] = {}
                changed = True
            
            if changed:
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                return FixResult(
                    success=True,
                    message="已重建缺失的配置结构",
                    level=FixLevel.AUTO,
                    backup_path=backup,
                    details="models 和 providers 结构已创建"
                )
            
            return FixResult(
                success=True,
                message="配置结构已完整",
                level=FixLevel.AUTO,
                backup_path=backup
            )
            
        except Exception as e:
            return FixResult(
                success=False,
                message=f"修复失败: {str(e)}",
                level=FixLevel.MANUAL,
                backup_path=backup
            )
    
    def _fix_config_api_key(self, issue: Dict) -> FixResult:
        """修复 API Key 配置"""
        return FixResult(
            success=False,
            message="API Key 需要手动配置",
            level=FixLevel.MANUAL,
            details="请使用'仅配置模型'功能设置 API Key，建议使用环境变量方式存储"
        )
    
    def _fix_env_node_missing(self, issue: Dict) -> FixResult:
        """修复 Node.js 缺失"""
        import platform
        
        system = platform.system()
        
        if system == "Windows":
            guide = """
Windows 安装 Node.js:
1. 访问 https://nodejs.org
2. 下载 LTS 版本安装包
3. 运行安装程序，按向导完成安装
4. 重新打开终端，运行 'node --version' 验证
"""
        elif system == "Darwin":
            guide = """
macOS 安装 Node.js:
方法1 - Homebrew:
  brew install node

方法2 - 官方安装包:
  访问 https://nodejs.org 下载安装包
"""
        else:
            guide = """
Linux 安装 Node.js:
Ubuntu/Debian:
  sudo apt update && sudo apt install nodejs npm

CentOS/RHEL:
  sudo yum install nodejs npm

Arch:
  sudo pacman -S nodejs npm
"""
        
        return FixResult(
            success=False,
            message="Node.js 未安装，需要手动安装",
            level=FixLevel.MANUAL,
            details=guide
        )
    
    def _fix_env_npm_issue(self, issue: Dict) -> FixResult:
        """修复 npm 问题"""
        return FixResult(
            success=False,
            message="npm 问题需要手动处理",
            level=FixLevel.MANUAL,
            details="""
npm 常见问题解决:
1. 清除 npm 缓存: npm cache clean --force
2. 更新 npm: npm install -g npm@latest
3. 检查网络连接
4. 配置镜像源: npm config set registry https://registry.npmmirror.com
"""
        )
    
    def _fix_tool_openclaw_missing(self, issue: Dict) -> FixResult:
        """修复 OpenClaw CLI 缺失"""
        try:
            result = subprocess.run(
                "npm install -g openclaw@latest",
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=300
            )
            
            if result.returncode == 0:
                return FixResult(
                    success=True,
                    message="OpenClaw CLI 安装成功",
                    level=FixLevel.AUTO,
                    requires_restart=True,
                    details="请重新运行诊断确认安装成功"
                )
            else:
                error = result.stderr or result.stdout or "未知错误"
                if "permission" in error.lower() or "eacces" in error.lower():
                    return FixResult(
                        success=False,
                        message="权限不足，无法安装 OpenClaw CLI",
                        level=FixLevel.MANUAL,
                        details="""
请以管理员身份运行以下命令:
  npm install -g openclaw@latest

或使用 nvm 管理 Node.js 版本，避免权限问题
"""
                    )
                
                return FixResult(
                    success=False,
                    message=f"安装失败: {error[:100]}",
                    level=FixLevel.MANUAL
                )
                
        except Exception as e:
            return FixResult(
                success=False,
                message=f"安装过程出错: {str(e)}",
                level=FixLevel.MANUAL
            )
    
    def _fix_security_permission(self, issue: Dict) -> FixResult:
        """修复权限问题"""
        import platform
        
        system = platform.system()
        
        if system == "Windows":
            guide = """
Windows 权限问题解决:
1. 以管理员身份运行程序
2. 右键点击程序 → 以管理员身份运行
3. 或修改目录权限:
   - 右键 ~/.openclaw 文件夹
   - 属性 → 安全 → 编辑权限
"""
        else:
            guide = """
Linux/macOS 权限问题解决:
1. 修改目录所有者:
   sudo chown -R $(whoami) ~/.openclaw

2. 或使用 nvm 管理 Node.js:
   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
   nvm install node
"""
        
        return FixResult(
            success=False,
            message="权限不足，需要手动修复",
            level=FixLevel.MANUAL,
            details=guide
        )
    
    def generate_fix_script(self, issues: List[Dict], platform: str = None) -> str:
        """生成修复脚本"""
        if platform is None:
            import platform as plat
            platform = plat.system().lower()
        
        script_lines = []
        
        if platform == "windows":
            script_lines.append("@echo off")
            script_lines.append("echo OpenClaw 修复脚本")
            script_lines.append("echo =================")
            script_lines.append("")
        else:
            script_lines.append("#!/bin/bash")
            script_lines.append("echo 'OpenClaw 修复脚本'")
            script_lines.append("echo '================='")
            script_lines.append("")
        
        for issue in issues:
            issue_type = self._classify_issue(issue)
            
            if issue_type == "config_unknown_keys":
                script_lines.append("echo '修复: 移除配置文件中的未知键'")
                if platform == "windows":
                    script_lines.append("powershell -Command \"& { $cfg = Get-Content ~/.openclaw/openclaw.json | ConvertFrom-Json; if ($cfg.models) { $valid = @('providers','aliases','defaults'); $cfg.models.PSObject.Properties | Where-Object { $_.Name -notin $valid } | ForEach-Object { $cfg.models.PSObject.Properties.Remove($_.Name) }; $cfg | ConvertTo-Json -Depth 10 | Set-Content ~/.openclaw/openclaw.json } }\"")
                else:
                    script_lines.append("python3 -c \"import json; f=open('$HOME/.openclaw/openclaw.json'); d=json.load(f); f.close(); d['models']={k:v for k,v in d.get('models',{}).items() if k in ['providers','aliases','defaults']}; json.dump(d,open('$HOME/.openclaw/openclaw.json','w'),indent=2)\"")
            
            elif issue_type == "tool_openclaw_missing":
                script_lines.append("echo '修复: 安装 OpenClaw CLI'")
                script_lines.append("npm install -g openclaw@latest")
        
        script_lines.append("")
        script_lines.append("echo '修复完成'")
        script_lines.append("pause" if platform == "windows" else "read -p '按回车键继续...'")
        
        return "\n".join(script_lines)
    
    def get_available_fixes(self, issues: List[Dict]) -> List[FixAction]:
        """获取可用的修复动作列表"""
        fixes = []
        
        for issue in issues:
            issue_type = self._classify_issue(issue)
            
            if issue_type in self._fix_strategies:
                # 预估修复级别
                if issue_type in ["config_unknown_keys", "config_missing_structure"]:
                    level = FixLevel.AUTO
                    can_auto = True
                elif issue_type in ["config_invalid_json"]:
                    level = FixLevel.GUIDED
                    can_auto = False
                else:
                    level = FixLevel.MANUAL
                    can_auto = False
                
                fixes.append(FixAction(
                    name=issue.get("name", "未知问题"),
                    description=issue.get("message", ""),
                    level=level,
                    action=lambda i=issue: self.analyze_and_fix(i),
                    can_auto_fix=can_auto
                ))
        
        return fixes


# 便捷函数
def fix_issue(issue: Dict) -> FixResult:
    """修复单个问题的便捷函数"""
    assistant = SmartFixAssistant()
    return assistant.analyze_and_fix(issue)


def generate_fix_script(issues: List[Dict], platform: str = None) -> str:
    """生成修复脚本的便捷函数"""
    assistant = SmartFixAssistant()
    return assistant.generate_fix_script(issues, platform)


def get_fix_suggestions(issues: List[Dict]) -> List[FixAction]:
    """获取修复建议的便捷函数"""
    assistant = SmartFixAssistant()
    return assistant.get_available_fixes(issues)
