from typing import Any, Dict, List, Optional
import json
import os
import secrets
import stat
import sys
from datetime import datetime
from pathlib import Path

from .models import RiskLevel, PermissionCheck


class SecurityHardeningEngine:
    """
    安全加固引擎 - 完整实现版
    
    提供主动安全加固能力，包括：
    - 配置安全加固
    - 权限修复
    - 密钥轮换
    - 审计日志配置
    """

    CONFIG_PATH = os.path.expanduser("~/.openclaw/openclaw.json")
    CONFIG_DIR = os.path.expanduser("~/.openclaw")
    
    # 高危配置检查规则
    HIGH_RISK_RULES = [
        {
            "id": "gateway_bind_exposure",
            "name": "Gateway 绑定暴露",
            "description": "Gateway 绑定到 0.0.0.0 或 lan 可能导致未授权访问",
            "risk_level": RiskLevel.CRITICAL,
            "check": lambda cfg: cfg.get("gateway", {}).get("bind") in ["0.0.0.0", "lan"],
            "fix_action": "restrict_gateway_bind",
        },
        {
            "id": "missing_auth",
            "name": "缺少认证配置",
            "description": "未配置任何认证信息，允许匿名访问",
            "risk_level": RiskLevel.CRITICAL,
            "check": lambda cfg: not cfg.get("gateway", {}).get("auth", {}).get("token") 
                               and not cfg.get("gateway", {}).get("auth", {}).get("password"),
            "fix_action": "enable_auth",
        },
        {
            "id": "weak_token",
            "name": "弱认证令牌",
            "description": "认证令牌长度不足或熵值过低",
            "risk_level": RiskLevel.HIGH,
            "check": lambda cfg: _is_weak_token(cfg.get("gateway", {}).get("auth", {}).get("token", "")),
            "fix_action": "rotate_token",
        },
        {
            "id": "api_key_exposure",
            "name": "API Key 泄露风险",
            "description": "配置文件中存储明文 API Key",
            "risk_level": RiskLevel.HIGH,
            "check": lambda cfg: _has_plaintext_api_keys(cfg),
            "fix_action": "migrate_to_env",
        },
        {
            "id": "insecure_cors",
            "name": "不安全的 CORS 配置",
            "description": "CORS 允许所有来源访问",
            "risk_level": RiskLevel.MEDIUM,
            "check": lambda cfg: cfg.get("gateway", {}).get("cors", {}).get("origin") == "*",
            "fix_action": "restrict_cors",
        },
        {
            "id": "missing_rate_limit",
            "name": "缺少速率限制",
            "description": "未配置请求速率限制，可能遭受暴力破解",
            "risk_level": RiskLevel.MEDIUM,
            "check": lambda cfg: not cfg.get("gateway", {}).get("rateLimit"),
            "fix_action": "enable_rate_limit",
        },
        {
            "id": "debug_mode",
            "name": "调试模式开启",
            "description": "生产环境不应开启调试模式",
            "risk_level": RiskLevel.HIGH,
            "check": lambda cfg: cfg.get("debug") == True or cfg.get("gateway", {}).get("debug") == True,
            "fix_action": "disable_debug",
        },
        {
            "id": "missing_audit_log",
            "name": "缺少审计日志",
            "description": "未启用安全审计日志",
            "risk_level": RiskLevel.LOW,
            "check": lambda cfg: cfg.get("logging", {}).get("level") not in ["info", "debug"],
            "fix_action": "enable_audit_logging",
        },
    ]

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self.CONFIG_PATH
        self.config_dir = os.path.dirname(self.config_path)
        self._backup_dir = os.path.join(self.config_dir, "backups")

    def plan(self) -> Dict[str, Any]:
        """
        生成安全加固计划
        
        Returns:
            {
                "score": int,  # 当前安全评分 0-100
                "risk_level": str,  # overall risk level
                "actions": List[Dict],  # 建议的加固动作
                "auto_fixable": List[Dict],  # 可自动修复的问题
                "manual_required": List[Dict],  # 需要手动处理的问题
            }
        """
        cfg = self._load_config()
        actions = []
        auto_fixable = []
        manual_required = []
        
        critical_count = 0
        high_count = 0
        medium_count = 0
        
        for rule in self.HIGH_RISK_RULES:
            try:
                if rule["check"](cfg):
                    action = {
                        "id": rule["id"],
                        "name": rule["name"],
                        "summary": rule["description"],
                        "risk_level": rule["risk_level"].value,
                        "fix_action": rule["fix_action"],
                        "auto_fixable": rule["fix_action"] in self._get_auto_fixable_actions(),
                    }
                    actions.append(action)
                    
                    if action["auto_fixable"]:
                        auto_fixable.append(action)
                    else:
                        manual_required.append(action)
                    
                    # 统计风险等级
                    if rule["risk_level"] == RiskLevel.CRITICAL:
                        critical_count += 1
                    elif rule["risk_level"] == RiskLevel.HIGH:
                        high_count += 1
                    elif rule["risk_level"] == RiskLevel.MEDIUM:
                        medium_count += 1
            except Exception as e:
                # 单个规则检查失败不应影响整体
                actions.append({
                    "id": rule["id"],
                    "name": rule["name"],
                    "summary": f"检查失败: {str(e)}",
                    "risk_level": RiskLevel.MEDIUM.value,
                    "fix_action": "manual_review",
                    "auto_fixable": False,
                })
        
        # 计算安全评分
        score = self._calculate_score(critical_count, high_count, medium_count)
        
        # 确定总体风险等级
        if critical_count > 0:
            overall_risk = RiskLevel.CRITICAL
        elif high_count > 0:
            overall_risk = RiskLevel.HIGH
        elif medium_count > 0:
            overall_risk = RiskLevel.MEDIUM
        else:
            overall_risk = RiskLevel.SAFE
        
        return {
            "score": score,
            "risk_level": overall_risk.value,
            "critical_count": critical_count,
            "high_count": high_count,
            "medium_count": medium_count,
            "actions": actions,
            "auto_fixable": auto_fixable,
            "manual_required": manual_required,
            "timestamp": datetime.now().isoformat(),
        }

    def execute_fix(self, action_id: str) -> Dict[str, Any]:
        """
        执行指定的加固动作
        
        Args:
            action_id: 加固动作 ID
            
        Returns:
            {
                "success": bool,
                "message": str,
                "backup_path": Optional[str],
                "requires_restart": bool,
            }
        """
        # 先备份配置
        backup_path = self._backup_config()
        
        fix_methods = {
            "restrict_gateway_bind": self._fix_restrict_gateway_bind,
            "enable_auth": self._fix_enable_auth,
            "rotate_token": self._fix_rotate_token,
            "migrate_to_env": self._fix_migrate_to_env,
            "restrict_cors": self._fix_restrict_cors,
            "enable_rate_limit": self._fix_enable_rate_limit,
            "disable_debug": self._fix_disable_debug,
            "enable_audit_logging": self._fix_enable_audit_logging,
        }
        
        fix_method = fix_methods.get(action_id)
        if not fix_method:
            return {
                "success": False,
                "message": f"未知的加固动作: {action_id}",
                "backup_path": backup_path,
                "requires_restart": False,
            }
        
        try:
            result = fix_method()
            result["backup_path"] = backup_path
            return result
        except Exception as e:
            return {
                "success": False,
                "message": f"加固失败: {str(e)}",
                "backup_path": backup_path,
                "requires_restart": False,
            }

    def one_click_harden(self) -> Dict[str, Any]:
        """
        一键安全加固 - 自动修复所有可自动修复的问题
        
        Returns:
            {
                "fixed": List[Dict],  # 已修复的问题
                "failed": List[Dict],  # 修复失败的问题
                "skipped": List[Dict],  # 跳过的问题（需手动处理）
                "backup_path": str,
                "requires_restart": bool,
            }
        """
        plan = self.plan()
        fixed = []
        failed = []
        skipped = []
        requires_restart = False
        
        # 备份配置
        backup_path = self._backup_config()
        
        # 自动修复所有可自动修复的问题
        for action in plan["auto_fixable"]:
            result = self.execute_fix(action["id"])
            if result["success"]:
                fixed.append({
                    "id": action["id"],
                    "name": action["name"],
                    "message": result["message"],
                })
                if result.get("requires_restart"):
                    requires_restart = True
            else:
                failed.append({
                    "id": action["id"],
                    "name": action["name"],
                    "message": result["message"],
                })
        
        # 记录需手动处理的问题
        for action in plan["manual_required"]:
            skipped.append({
                "id": action["id"],
                "name": action["name"],
                "reason": "需要手动处理",
            })
        
        return {
            "fixed": fixed,
            "failed": failed,
            "skipped": skipped,
            "backup_path": backup_path,
            "requires_restart": requires_restart,
            "timestamp": datetime.now().isoformat(),
        }

    def fix_permissions(self) -> Dict[str, Any]:
        """
        修复配置文件和目录权限
        
        Returns:
            {
                "success": bool,
                "message": str,
                "details": List[str],
            }
        """
        details = []
        
        if sys.platform == "win32":
            # Windows 权限处理
            try:
                import win32security
                import win32api
                import win32con
                
                # 获取当前用户 SID
                user_sid = win32security.GetTokenInformation(
                    win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY),
                    win32security.TokenUser
                )[0]
                
                # 修复配置目录权限
                if os.path.isdir(self.config_dir):
                    sd = win32security.GetFileSecurity(self.config_dir, win32security.DACL_SECURITY_INFORMATION)
                    dacl = win32security.ACL()
                    dacl.AddAccessAllowedAce(
                        win32security.ACL_REVISION,
                        win32con.FILE_ALL_ACCESS,
                        user_sid
                    )
                    sd.SetSecurityDescriptorDacl(1, dacl, 0)
                    win32security.SetFileSecurity(self.config_dir, win32security.DACL_SECURITY_INFORMATION, sd)
                    details.append(f"✅ 已修复配置目录权限: {self.config_dir}")
                
                # 修复配置文件权限
                if os.path.isfile(self.config_path):
                    sd = win32security.GetFileSecurity(self.config_path, win32security.DACL_SECURITY_INFORMATION)
                    dacl = win32security.ACL()
                    dacl.AddAccessAllowedAce(
                        win32security.ACL_REVISION,
                        win32con.FILE_ALL_ACCESS,
                        user_sid
                    )
                    sd.SetSecurityDescriptorDacl(1, dacl, 0)
                    win32security.SetFileSecurity(self.config_path, win32security.DACL_SECURITY_INFORMATION, sd)
                    details.append(f"✅ 已修复配置文件权限: {self.config_path}")
                    
            except ImportError:
                details.append("ℹ️ Windows 权限修复需要 pywin32 模块")
            except Exception as e:
                details.append(f"⚠️ Windows 权限修复失败: {str(e)}")
        else:
            # Unix/Linux/macOS 权限处理
            try:
                # 配置目录权限 700 (rwx------)
                if os.path.isdir(self.config_dir):
                    os.chmod(self.config_dir, stat.S_IRWXU)
                    details.append(f"✅ 已设置配置目录权限为 700: {self.config_dir}")
                
                # 配置文件权限 600 (rw-------)
                if os.path.isfile(self.config_path):
                    os.chmod(self.config_path, stat.S_IRUSR | stat.S_IWUSR)
                    details.append(f"✅ 已设置配置文件权限为 600: {self.config_path}")
                
                # 日志目录权限 700
                logs_dir = os.path.join(self.config_dir, "logs")
                if os.path.isdir(logs_dir):
                    os.chmod(logs_dir, stat.S_IRWXU)
                    details.append(f"✅ 已设置日志目录权限为 700: {logs_dir}")
                    
            except Exception as e:
                details.append(f"⚠️ 权限修复失败: {str(e)}")
        
        return {
            "success": len([d for d in details if d.startswith("✅")]) > 0,
            "message": "权限修复完成" if details else "无需修复",
            "details": details,
        }

    # --- 具体修复方法 ---

    def _fix_restrict_gateway_bind(self) -> Dict[str, Any]:
        """限制 Gateway 绑定到本地回环"""
        cfg = self._load_config()
        if "gateway" not in cfg:
            cfg["gateway"] = {}
        cfg["gateway"]["bind"] = "loopback"
        self._save_config(cfg)
        return {
            "success": True,
            "message": "已将 Gateway 绑定模式设置为 loopback (127.0.0.1)",
            "requires_restart": True,
        }

    def _fix_enable_auth(self) -> Dict[str, Any]:
        """启用认证并生成安全令牌"""
        cfg = self._load_config()
        if "gateway" not in cfg:
            cfg["gateway"] = {}
        if "auth" not in cfg["gateway"]:
            cfg["gateway"]["auth"] = {}
        
        # 生成 32 字节的安全令牌
        token = secrets.token_urlsafe(32)
        cfg["gateway"]["auth"]["token"] = token
        self._save_config(cfg)
        
        return {
            "success": True,
            "message": f"已启用认证，生成新令牌: {token[:8]}...{token[-8:]}",
            "requires_restart": True,
            "warning": "请保存此令牌，重启后需要用它来访问 Gateway",
        }

    def _fix_rotate_token(self) -> Dict[str, Any]:
        """轮换认证令牌"""
        cfg = self._load_config()
        old_token = cfg.get("gateway", {}).get("auth", {}).get("token", "")
        
        # 生成新令牌
        new_token = secrets.token_urlsafe(32)
        cfg["gateway"]["auth"]["token"] = new_token
        self._save_config(cfg)
        
        return {
            "success": True,
            "message": f"令牌已轮换\n旧令牌: {old_token[:8]}...\n新令牌: {new_token[:8]}...",
            "requires_restart": True,
        }

    def _fix_migrate_to_env(self) -> Dict[str, Any]:
        """将 API Key 迁移到环境变量"""
        cfg = self._load_config()
        providers = cfg.get("models", {}).get("providers", {})
        
        env_vars = []
        for name, config in providers.items():
            if "apiKey" in config and config["apiKey"]:
                env_var_name = f"OPENCLAW_API_KEY_{name.upper()}"
                env_vars.append(f"{env_var_name}={config['apiKey']}")
                # 从配置中移除明文 key，改为从环境变量读取
                config["apiKey"] = f"${env_var_name}"
        
        self._save_config(cfg)
        
        # 生成环境变量设置脚本
        script_content = "# OpenClaw API Keys - 请添加到您的环境变量中\n"
        script_content += "# Windows (PowerShell):\n"
        for env_var in env_vars:
            script_content += f"[Environment]::SetEnvironmentVariable('{env_var.split('=')[0]}', '{env_var.split('=')[1]}', 'User')\n"
        script_content += "\n# Linux/macOS (Bash):\n"
        script_content += "# 添加到 ~/.bashrc 或 ~/.zshrc:\n"
        for env_var in env_vars:
            script_content += f"export {env_var}\n"
        
        env_script_path = os.path.join(self.config_dir, "api_keys_env.sh")
        with open(env_script_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        
        return {
            "success": True,
            "message": f"API Key 已迁移到环境变量配置\n请查看: {env_script_path}",
            "requires_restart": True,
            "script_path": env_script_path,
        }

    def _fix_restrict_cors(self) -> Dict[str, Any]:
        """限制 CORS 来源"""
        cfg = self._load_config()
        if "gateway" not in cfg:
            cfg["gateway"] = {}
        if "cors" not in cfg["gateway"]:
            cfg["gateway"]["cors"] = {}
        
        # 默认只允许本地来源
        cfg["gateway"]["cors"]["origin"] = ["http://localhost:3000", "http://127.0.0.1:3000"]
        self._save_config(cfg)
        
        return {
            "success": True,
            "message": "已将 CORS 限制为本地来源",
            "requires_restart": True,
        }

    def _fix_enable_rate_limit(self) -> Dict[str, Any]:
        """启用速率限制"""
        cfg = self._load_config()
        if "gateway" not in cfg:
            cfg["gateway"] = {}
        
        cfg["gateway"]["rateLimit"] = {
            "windowMs": 60000,  # 1 分钟
            "maxRequests": 100,  # 最多 100 请求
            "skipSuccessfulRequests": False,
        }
        self._save_config(cfg)
        
        return {
            "success": True,
            "message": "已启用速率限制 (100 请求/分钟)",
            "requires_restart": True,
        }

    def _fix_disable_debug(self) -> Dict[str, Any]:
        """关闭调试模式"""
        cfg = self._load_config()
        cfg["debug"] = False
        if "gateway" in cfg:
            cfg["gateway"]["debug"] = False
        self._save_config(cfg)
        
        return {
            "success": True,
            "message": "已关闭调试模式",
            "requires_restart": True,
        }

    def _fix_enable_audit_logging(self) -> Dict[str, Any]:
        """启用审计日志"""
        cfg = self._load_config()
        if "logging" not in cfg:
            cfg["logging"] = {}
        
        cfg["logging"]["level"] = "info"
        cfg["logging"]["audit"] = True
        cfg["logging"]["auditLogPath"] = os.path.join(self.config_dir, "logs", "audit.log")
        self._save_config(cfg)
        
        # 确保日志目录存在
        audit_dir = os.path.dirname(cfg["logging"]["auditLogPath"])
        os.makedirs(audit_dir, exist_ok=True)
        
        return {
            "success": True,
            "message": "已启用审计日志",
            "requires_restart": True,
        }

    # --- 工具方法 ---

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            return {}
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_config(self, cfg: Dict[str, Any]) -> None:
        """保存配置文件"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)

    def _backup_config(self) -> Optional[str]:
        """备份配置文件"""
        if not os.path.exists(self.config_path):
            return None
        
        os.makedirs(self._backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(self._backup_dir, f"openclaw.json.bak.{timestamp}")
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as src:
                with open(backup_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read())
            return backup_path
        except Exception:
            return None

    def _get_auto_fixable_actions(self) -> List[str]:
        """返回可自动修复的动作列表"""
        return [
            "restrict_gateway_bind",
            "enable_auth",
            "rotate_token",
            "restrict_cors",
            "enable_rate_limit",
            "disable_debug",
            "enable_audit_logging",
        ]

    def _calculate_score(self, critical: int, high: int, medium: int) -> int:
        """计算安全评分"""
        # 基础分 100，按风险等级扣分
        score = 100
        score -= critical * 30  # 每个高危扣 30
        score -= high * 15      # 每个中高危扣 15
        score -= medium * 5     # 每个中危扣 5
        return max(0, score)


# --- 辅助函数 ---

def _is_weak_token(token: str) -> bool:
    """检查令牌是否弱"""
    if not token:
        return True
    if len(token) < 20:
        return True
    # 检查熵值（字符种类）
    has_lower = any(c.islower() for c in token)
    has_upper = any(c.isupper() for c in token)
    has_digit = any(c.isdigit() for c in token)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in token)
    
    variety = sum([has_lower, has_upper, has_digit, has_special])
    return variety < 3 or len(token) < 32


def _has_plaintext_api_keys(cfg: Dict) -> bool:
    """检查是否有明文 API Key"""
    providers = cfg.get("models", {}).get("providers", {})
    for name, config in providers.items():
        api_key = config.get("apiKey", "")
        if api_key and not api_key.startswith("$"):
            # 不以 $ 开头（环境变量语法）则认为是明文
            return True
    return False
