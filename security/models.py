import enum
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


class RiskLevel(enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SAFE = "safe"


@dataclass
class PermissionCheck:
    name: str
    level: RiskLevel
    message: str
    details: str = ""
    fix_suggestion: str = ""
    auto_fixable: bool = False


@dataclass
class SkillSecurityReport:
    id: str
    name: str
    trust_level: str = "unknown"
    is_suspicious: bool = False
    permissions: Optional[str] = None
    network_calls: Optional[str] = None
    file_operations: Optional[str] = None
    # The following fields are produced by `SkillSecurityScanner` and consumed by
    # `SecurityScoringSystem` and the UI diagnostics suite.
    issues_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    signature_valid: bool = False
    details: Optional[Dict[str, Any]] = None


@dataclass
class VulnerabilityHit:
    id: str
    name: str
    severity: str
    description: str = ""
    fix_action: str = ""
    miit_notice: str = ""

