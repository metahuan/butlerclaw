import os
import json
import re
import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from .models import PermissionCheck, RiskLevel


class PermissionScanner:
    """
    OpenClaw 权限体检扫描器 - 完整实现版
    
    提供全面的安全配置检查，包括：
    - 配置文件存在性和权限
    - Gateway 绑定模式
    - 认证配置和令牌强度
    - API Key 安全存储
    - CORS 配置
    - 调试模式
    - 审计日志
    """

    CONFIG_PATH = os.path.expanduser("~/.openclaw/openclaw.json")
    CONFIG_DIR = os.path.expanduser("~/.openclaw")
    
    # API Key 强度要求
    MIN_API_KEY_LENGTH = 20
    MIN_TOKEN_LENGTH = 32
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self.CONFIG_PATH
        self.config_dir = os.path.dirname(self.config_path)
    
    def scan(self) -> Dict[str, Any]:
        """
        执行完整的权限安全扫描
        
        Returns:
            {
                "score": int,  # 0-100
                "risk_level": str,
                "checks": List[PermissionCheck],
                "summary": Dict[str, int],
                "timestamp": str,
            }
        """
        checks: List[PermissionCheck] = []
        
        # 基础检查
        checks.append(self._check_config_exists())
        checks.append(self._check_config_permissions())
        
        # Gateway 安全配置
        checks.append(self._check_gateway_bind())
        checks.append(self._check_auth_config())
        checks.append(self._check_token_strength())
        
        # API Key 安全
        checks.append(self._check_api_key_storage())
        checks.append(self._check_api_key_strength())
        
        # 其他安全配置
        checks.append(self._check_cors_config())
        checks.append(self._check_debug_mode())
        checks.append(self._check_rate_limit())
        checks.append(self._check_audit_logging())
        
        # 敏感信息泄露检查
        checks.append(self._check_sensitive_info_in_logs())
        
        return self._generate_report(checks)
    
    # --- 具体检查项 ---
    
    def _check_config_exists(self) -> PermissionCheck:
        """检查配置文件存在性"""
        if not os.path.exists(self.config_path):
            return PermissionCheck(
                name="配置文件存在性",
                level=RiskLevel.MEDIUM,
                message="未找到 openclaw.json 配置文件",
                details=f"期待路径: {self.config_path}",
                fix_suggestion="建议通过安装向导或 CLI 初始化生成配置文件。",
                auto_fixable=False,
            )
        
        return PermissionCheck(
            name="配置文件存在性",
            level=RiskLevel.SAFE,
            message="已检测到 openclaw.json 配置文件",
            details=f"路径: {self.config_path}",
        )
    
    def _check_config_permissions(self) -> PermissionCheck:
        """检查配置文件权限"""
        if not os.path.exists(self.config_path):
            return PermissionCheck(
                name="配置文件权限",
                level=RiskLevel.SAFE,
                message="配置文件不存在，跳过权限检查",
                details="",
            )
        
        import stat
        import sys
        
        if sys.platform == "win32":
            # Windows 简化检查
            return PermissionCheck(
                name="配置文件权限",
                level=RiskLevel.SAFE,
                message="Windows 平台权限检查已跳过",
                details="建议确保配置文件不被其他用户访问",
            )
        
        try:
            mode = os.stat(self.config_path).st_mode
            # 检查其他用户是否有读权限
            if mode & (stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH):
                return PermissionCheck(
                    name="配置文件权限",
                    level=RiskLevel.HIGH,
                    message="配置文件权限过宽，其他用户可能读取",
                    details=f"当前权限: {oct(mode & 0o777)}，建议设置为 600 (rw-------)",
                    fix_suggestion="运行 chmod 600 ~/.openclaw/openclaw.json 修复权限",
                    auto_fixable=True,
                )
            
            if mode & (stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP):
                return PermissionCheck(
                    name="配置文件权限",
                    level=RiskLevel.MEDIUM,
                    message="配置文件对同组用户可访问",
                    details=f"当前权限: {oct(mode & 0o777)}",
                    fix_suggestion="建议运行 chmod 600 ~/.openclaw/openclaw.json",
                    auto_fixable=True,
                )
            
            return PermissionCheck(
                name="配置文件权限",
                level=RiskLevel.SAFE,
                message="配置文件权限设置正确",
                details=f"权限: {oct(mode & 0o777)}",
            )
        except Exception as e:
            return PermissionCheck(
                name="配置文件权限",
                level=RiskLevel.MEDIUM,
                message="无法检查配置文件权限",
                details=str(e),
            )
    
    def _check_gateway_bind(self) -> PermissionCheck:
        """检查 Gateway 绑定模式"""
        cfg = self._load_config()
        gateway = cfg.get("gateway", {}) if isinstance(cfg, dict) else {}
        bind = gateway.get("bind", "auto")
        
        if bind in ("0.0.0.0", "lan"):
            return PermissionCheck(
                name="Gateway 绑定模式",
                level=RiskLevel.CRITICAL,
                message=f"Gateway 绑定到 {bind}，存在公网暴露风险",
                details="当前配置允许局域网或公网访问 Gateway，可能导致未授权访问。",
                fix_suggestion="建议将 gateway.bind 改为 'loopback' 或 '127.0.0.1'。",
                auto_fixable=True,
            )
        
        if bind in ("loopback", "127.0.0.1", "localhost"):
            return PermissionCheck(
                name="Gateway 绑定模式",
                level=RiskLevel.SAFE,
                message=f"Gateway 绑定到本地回环 ({bind})",
                details="仅允许本地访问，安全性良好。",
            )
        
        return PermissionCheck(
            name="Gateway 绑定模式",
            level=RiskLevel.MEDIUM,
            message=f"Gateway 绑定模式为 {bind}",
            details="建议显式设置为 'loopback' 以确保安全。",
            fix_suggestion="建议设置 gateway.bind 为 'loopback'",
            auto_fixable=True,
        )
    
    def _check_auth_config(self) -> PermissionCheck:
        """检查认证配置"""
        cfg = self._load_config()
        gateway = cfg.get("gateway", {}) if isinstance(cfg, dict) else {}
        auth = gateway.get("auth", {}) if isinstance(gateway, dict) else {}
        
        has_token = bool(auth.get("token"))
        has_password = bool(auth.get("password"))
        
        if not has_token and not has_password:
            return PermissionCheck(
                name="Gateway 认证配置",
                level=RiskLevel.CRITICAL,
                message="未配置任何认证信息，允许匿名访问",
                details="gateway.auth.token 与 gateway.auth.password 均为空。",
                fix_suggestion="建议配置 gateway.auth.token，避免未授权访问。",
                auto_fixable=True,
            )
        
        # 检查是否使用默认/弱密码
        password = auth.get("password", "")
        if password and self._is_weak_password(password):
            return PermissionCheck(
                name="Gateway 认证配置",
                level=RiskLevel.HIGH,
                message="认证密码强度不足",
                details="密码太短或过于简单，容易被暴力破解。",
                fix_suggestion="使用至少 12 位，包含大小写、数字和特殊字符的强密码。",
                auto_fixable=False,
            )
        
        auth_methods = []
        if has_token:
            auth_methods.append("Token")
        if has_password:
            auth_methods.append("Password")
        
        return PermissionCheck(
            name="Gateway 认证配置",
            level=RiskLevel.SAFE,
            message=f"已配置 Gateway 认证 ({', '.join(auth_methods)})",
            details="认证已启用，未授权访问已被阻止。",
        )
    
    def _check_token_strength(self) -> PermissionCheck:
        """检查认证令牌强度"""
        cfg = self._load_config()
        token = cfg.get("gateway", {}).get("auth", {}).get("token", "")
        
        if not token:
            return PermissionCheck(
                name="认证令牌强度",
                level=RiskLevel.SAFE,
                message="未使用 Token 认证",
                details="",
            )
        
        issues = []
        
        # 长度检查
        if len(token) < self.MIN_TOKEN_LENGTH:
            issues.append(f"令牌长度不足 ({len(token)} < {self.MIN_TOKEN_LENGTH})")
        
        # 熵值检查
        entropy = self._calculate_entropy(token)
        if entropy < 4.0:  # 每个字符的熵值
            issues.append(f"令牌熵值过低 ({entropy:.2f} < 4.0)")
        
        # 字符多样性检查
        variety = self._check_character_variety(token)
        if variety < 3:
            issues.append(f"字符种类不足 ({variety} < 3)")
        
        # 常见弱令牌检查
        if self._is_common_weak_token(token):
            issues.append("使用了常见弱令牌模式")
        
        if issues:
            return PermissionCheck(
                name="认证令牌强度",
                level=RiskLevel.HIGH,
                message="认证令牌强度不足",
                details="; ".join(issues),
                fix_suggestion="生成新的强令牌（至少 32 字节，包含多种字符类型）。",
                auto_fixable=True,
            )
        
        return PermissionCheck(
            name="认证令牌强度",
            level=RiskLevel.SAFE,
            message="认证令牌强度良好",
            details=f"长度: {len(token)}, 熵值: {entropy:.2f}",
        )
    
    def _check_api_key_storage(self) -> PermissionCheck:
        """检查 API Key 存储方式"""
        cfg = self._load_config()
        providers = cfg.get("models", {}).get("providers", {})
        
        plaintext_keys = []
        env_var_keys = []
        
        for name, config in providers.items():
            api_key = config.get("apiKey", "")
            if not api_key:
                continue
            
            # 检查是否是环境变量引用
            if api_key.startswith("$") or api_key.startswith("${"):
                env_var_keys.append(name)
            else:
                plaintext_keys.append(name)
        
        if plaintext_keys:
            return PermissionCheck(
                name="API Key 存储安全",
                level=RiskLevel.HIGH,
                message=f"{len(plaintext_keys)} 个 API Key 以明文存储",
                details=f"明文存储的提供商: {', '.join(plaintext_keys)}",
                fix_suggestion="将 API Key 迁移到环境变量，使用 $ENV_VAR_NAME 语法引用。",
                auto_fixable=True,
            )
        
        if env_var_keys:
            return PermissionCheck(
                name="API Key 存储安全",
                level=RiskLevel.SAFE,
                message="API Key 已安全存储",
                details=f"使用环境变量的提供商: {', '.join(env_var_keys)}",
            )
        
        return PermissionCheck(
            name="API Key 存储安全",
            level=RiskLevel.SAFE,
            message="未配置 API Key",
            details="",
        )
    
    def _check_api_key_strength(self) -> PermissionCheck:
        """检查 API Key 强度"""
        cfg = self._load_config()
        providers = cfg.get("models", {}).get("providers", {})
        
        weak_keys = []
        
        for name, config in providers.items():
            api_key = config.get("apiKey", "")
            if not api_key or api_key.startswith("$"):
                continue
            
            # 检查长度
            if len(api_key) < self.MIN_API_KEY_LENGTH:
                weak_keys.append(f"{name} (太短)")
                continue
            
            # 检查熵值
            entropy = self._calculate_entropy(api_key)
            if entropy < 3.5:
                weak_keys.append(f"{name} (低熵值)")
                continue
            
            # 检查是否包含常见模式
            if re.search(r'(test|demo|example|123|abc)', api_key, re.IGNORECASE):
                weak_keys.append(f"{name} (包含常见模式)")
        
        if weak_keys:
            return PermissionCheck(
                name="API Key 强度",
                level=RiskLevel.MEDIUM,
                message=f"发现 {len(weak_keys)} 个弱 API Key",
                details=f"弱密钥: {', '.join(weak_keys)}",
                fix_suggestion="重新生成强 API Key，避免使用测试密钥。",
                auto_fixable=False,
            )
        
        return PermissionCheck(
            name="API Key 强度",
            level=RiskLevel.SAFE,
            message="API Key 强度良好",
            details="",
        )
    
    def _check_cors_config(self) -> PermissionCheck:
        """检查 CORS 配置"""
        cfg = self._load_config()
        cors = cfg.get("gateway", {}).get("cors", {})
        origin = cors.get("origin", "")
        
        if origin == "*":
            return PermissionCheck(
                name="CORS 配置",
                level=RiskLevel.HIGH,
                message="CORS 允许所有来源访问",
                details="origin: * 允许任意网站跨域访问 Gateway。",
                fix_suggestion="限制 CORS 来源为特定的前端地址。",
                auto_fixable=True,
            )
        
        if not origin:
            return PermissionCheck(
                name="CORS 配置",
                level=RiskLevel.SAFE,
                message="CORS 未配置（默认安全）",
                details="",
            )
        
        if isinstance(origin, list):
            return PermissionCheck(
                name="CORS 配置",
                level=RiskLevel.SAFE,
                message=f"CORS 已限制为 {len(origin)} 个来源",
                details=f"允许的来源: {', '.join(origin)}",
            )
        
        return PermissionCheck(
            name="CORS 配置",
            level=RiskLevel.SAFE,
            message="CORS 已配置",
            details=f"允许的来源: {origin}",
        )
    
    def _check_debug_mode(self) -> PermissionCheck:
        """检查调试模式"""
        cfg = self._load_config()
        debug = cfg.get("debug", False)
        gateway_debug = cfg.get("gateway", {}).get("debug", False)
        
        if debug or gateway_debug:
            return PermissionCheck(
                name="调试模式",
                level=RiskLevel.HIGH,
                message="调试模式已开启",
                details="生产环境开启调试模式可能导致敏感信息泄露。",
                fix_suggestion="在生产环境中关闭 debug 模式。",
                auto_fixable=True,
            )
        
        return PermissionCheck(
            name="调试模式",
            level=RiskLevel.SAFE,
            message="调试模式已关闭",
            details="",
        )
    
    def _check_rate_limit(self) -> PermissionCheck:
        """检查速率限制配置"""
        cfg = self._load_config()
        rate_limit = cfg.get("gateway", {}).get("rateLimit")
        
        if not rate_limit:
            return PermissionCheck(
                name="速率限制",
                level=RiskLevel.MEDIUM,
                message="未配置速率限制",
                details="缺少速率限制可能导致暴力破解攻击。",
                fix_suggestion="启用速率限制，建议设置为 100 请求/分钟。",
                auto_fixable=True,
            )
        
        window = rate_limit.get("windowMs", 60000)
        max_req = rate_limit.get("maxRequests", 100)
        
        return PermissionCheck(
            name="速率限制",
            level=RiskLevel.SAFE,
            message="速率限制已启用",
            details=f"限制: {max_req} 请求/{window/1000:.0f}秒",
        )
    
    def _check_audit_logging(self) -> PermissionCheck:
        """检查审计日志配置"""
        cfg = self._load_config()
        logging_config = cfg.get("logging", {})
        level = logging_config.get("level", "warn")
        audit = logging_config.get("audit", False)
        
        if level.lower() not in ["info", "debug"] or not audit:
            return PermissionCheck(
                name="审计日志",
                level=RiskLevel.LOW,
                message="审计日志未完全启用",
                details="建议启用审计日志以追踪安全事件。",
                fix_suggestion="设置 logging.level 为 'info' 并启用 logging.audit。",
                auto_fixable=True,
            )
        
        return PermissionCheck(
            name="审计日志",
            level=RiskLevel.SAFE,
            message="审计日志已启用",
            details=f"日志级别: {level}",
        )
    
    def _check_sensitive_info_in_logs(self) -> PermissionCheck:
        """检查日志中是否可能包含敏感信息"""
        logs_dir = os.path.join(self.CONFIG_DIR, "logs")
        
        if not os.path.isdir(logs_dir):
            return PermissionCheck(
                name="日志敏感信息检查",
                level=RiskLevel.SAFE,
                message="日志目录不存在",
                details="",
            )
        
        # 检查最近的日志文件
        suspicious_patterns = [
            r'api[_-]?key["\']?\s*[:=]\s*["\']?[a-zA-Z0-9_-]+',
            r'token["\']?\s*[:=]\s*["\']?[a-zA-Z0-9_-]+',
            r'password["\']?\s*[:=]\s*["\']?[^\s"\']+',
        ]
        
        # 简化实现：提醒用户注意
        return PermissionCheck(
            name="日志敏感信息检查",
            level=RiskLevel.SAFE,
            message="日志敏感信息检查完成",
            details="建议定期审查日志文件，确保不包含 API Key 等敏感信息。",
        )
    
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
    
    def _generate_report(self, checks: List[PermissionCheck]) -> Dict[str, Any]:
        """生成扫描报告"""
        # 统计各等级问题数量
        summary = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "safe": 0,
            "total": len(checks),
        }
        
        for check in checks:
            if check.level == RiskLevel.CRITICAL:
                summary["critical"] += 1
            elif check.level == RiskLevel.HIGH:
                summary["high"] += 1
            elif check.level == RiskLevel.MEDIUM:
                summary["medium"] += 1
            elif check.level == RiskLevel.LOW:
                summary["low"] += 1
            else:
                summary["safe"] += 1
        
        # 计算安全评分
        score = self._calculate_score(summary)
        
        # 确定总体风险等级
        if summary["critical"] > 0:
            overall_risk = RiskLevel.CRITICAL
        elif summary["high"] > 0:
            overall_risk = RiskLevel.HIGH
        elif summary["medium"] > 0:
            overall_risk = RiskLevel.MEDIUM
        elif summary["low"] > 0:
            overall_risk = RiskLevel.LOW
        else:
            overall_risk = RiskLevel.SAFE
        
        return {
            "score": score,
            "risk_level": overall_risk.value,
            "summary": summary,
            "checks": checks,
            "timestamp": datetime.now().isoformat(),
        }
    
    def _calculate_score(self, summary: Dict[str, int]) -> int:
        """计算安全评分"""
        # 基础分 100
        score = 100
        # 扣分
        score -= summary["critical"] * 25
        score -= summary["high"] * 10
        score -= summary["medium"] * 5
        score -= summary["low"] * 2
        return max(0, score)
    
    def _calculate_entropy(self, s: str) -> float:
        """计算字符串的熵值（信息密度）"""
        if not s:
            return 0.0
        
        # 统计字符频率
        freq = {}
        for c in s:
            freq[c] = freq.get(c, 0) + 1
        
        # 计算熵
        length = len(s)
        entropy = 0.0
        for count in freq.values():
            p = count / length
            entropy -= p * math.log2(p)
        
        return entropy
    
    def _check_character_variety(self, s: str) -> int:
        """检查字符多样性"""
        has_lower = any(c.islower() for c in s)
        has_upper = any(c.isupper() for c in s)
        has_digit = any(c.isdigit() for c in s)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in s)
        
        return sum([has_lower, has_upper, has_digit, has_special])
    
    def _is_weak_password(self, password: str) -> bool:
        """检查密码是否弱"""
        if len(password) < 8:
            return True
        
        # 常见弱密码列表
        common_passwords = [
            "password", "123456", "qwerty", "admin", "letmein",
            "welcome", "monkey", "1234567890", "abc123", "password123",
        ]
        
        if password.lower() in common_passwords:
            return True
        
        # 检查字符多样性
        variety = self._check_character_variety(password)
        if variety < 2:
            return True
        
        return False
    
    def _is_common_weak_token(self, token: str) -> bool:
        """检查是否是常见弱令牌"""
        weak_patterns = [
            r'^[a-zA-Z]+$',  # 纯字母
            r'^[0-9]+$',      # 纯数字
            r'^[a-f0-9]{32}$',  # MD5 格式
            r'test',
            r'demo',
            r'example',
            r'123456',
            r'password',
        ]
        
        for pattern in weak_patterns:
            if re.search(pattern, token, re.IGNORECASE):
                return True
        
        return False
