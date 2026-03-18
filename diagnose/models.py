"""
diagnose.models

定义诊断引擎使用的核心数据模型与类型。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Iterable, List, Optional, Protocol


class DiagnosticCategory(str, Enum):
    ENV = "env"
    CLI = "cli"
    CONFIG = "config"
    NETWORK = "network"
    SECURITY = "security"
    SKILLS = "skills"
    PERFORMANCE = "performance"
    BUGS = "bugs"


class DiagnosticGroup(str, Enum):
    """
    用于 UI 顶部 4x2 区块过滤的更高层分组。

    一个分组可以包含多个 DiagnosticCategory。
    """

    ENV = "env"
    GATEWAY = "gateway"
    CHANNELS = "channels"
    MODELS = "models"
    CONFIG = "config"
    STATE = "state"
    TOOLS = "tools"
    AUTOMATION = "automation"
    BUGS = "bugs"


class DiagnosticSeverity(str, Enum):
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class DiagnosticStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class FixResult:
    """表示一次修复执行的结果。"""

    success: bool
    message: str = ""
    details: str = ""


FixCallable = Callable[[], FixResult]


@dataclass
class FixAction:
    """
    自动修复动作。

    - callable: 直接在 Python 内部执行的修复函数。
    - description: 面向用户的说明文字。
    - shell_command: 可选，若需要在外部 shell 中执行命令。
    - need_admin: 是否可能需要管理员 / sudo 权限。
    """

    callable: Optional[FixCallable] = None
    description: str = ""
    shell_command: Optional[str] = None
    need_admin: bool = False


@dataclass
class DiagnosticResult:
    """单项诊断的结果。"""

    id: str
    name: str
    category: DiagnosticCategory
    severity: DiagnosticSeverity
    status: DiagnosticStatus
    message: str
    # 可选的高层分组（用于龙虾健康中心的矩阵过滤）
    group: Optional[DiagnosticGroup] = None
    details: str = ""
    fix_suggestions: List[str] = field(default_factory=list)
    fix_action: Optional[FixAction] = None
    auto_safe: bool = False


class DiagnosticCheck(Protocol):
    """
    诊断检查项协议。

    任意实现该协议的类都可以被 DiagnosticEngine 注册与调用。
    """

    id: str
    name: str
    category: DiagnosticCategory
    severity: DiagnosticSeverity

    def run(self) -> DiagnosticResult:
        ...


ChecksIterable = Iterable[DiagnosticCheck]

