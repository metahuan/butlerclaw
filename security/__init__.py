"""
ButlerClaw 安全中心模块包 - 完整实现版

提供全面的安全功能：
- 权限扫描 (PermissionScanner)
- 技能安全扫描 (SkillSecurityScanner)
- 漏洞数据库 (VulnerabilityDatabase)
- 安全加固引擎 (SecurityHardeningEngine)
- 密钥轮换管理 (KeyRotationManager)
- 安全事件告警 (SecurityAlertManager)
"""

from .permission_scanner import PermissionScanner
from .skill_scanner import SkillSecurityScanner
from .vulnerability_db import VulnerabilityDatabase, get_vulnerabilities, check_vulnerable
from .hardening_engine import SecurityHardeningEngine
from .key_rotation import (
    KeyRotationManager,
    KeyType,
    RotationStatus,
    rotate_gateway_token,
    rotate_api_key,
    check_key_health,
)
from .alert_manager import (
    SecurityAlertManager,
    EventSeverity,
    EventType,
    report_security_event,
    check_security_alerts,
    get_security_summary,
)
from .models import (
    RiskLevel,
    PermissionCheck,
    SkillSecurityReport,
    VulnerabilityHit,
)

__all__ = [
    # 核心类
    "PermissionScanner",
    "SkillSecurityScanner",
    "VulnerabilityDatabase",
    "SecurityHardeningEngine",
    "KeyRotationManager",
    "SecurityAlertManager",
    
    # 枚举
    "RiskLevel",
    "KeyType",
    "RotationStatus",
    "EventSeverity",
    "EventType",
    
    # 数据模型
    "PermissionCheck",
    "SkillSecurityReport",
    "VulnerabilityHit",
    
    # 便捷函数
    "get_vulnerabilities",
    "check_vulnerable",
    "rotate_gateway_token",
    "rotate_api_key",
    "check_key_health",
    "report_security_event",
    "check_security_alerts",
    "get_security_summary",
]
