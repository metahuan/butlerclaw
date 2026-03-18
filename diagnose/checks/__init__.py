"""
diagnose.checks

各类具体诊断检查的实现。
"""

from .environment import NodeVersionCheck, NpmCheck, PathCheck  # noqa: F401
from .cli import OpenClawCliCheck  # noqa: F401
from .config import (
    ConfigFileExistCheck,
    ConfigJsonStructureCheck,
    ConfigApiKeyCheck,
    ConfigMigrationCheck,
)  # noqa: F401
from .network import NpmRegistryConnectivityCheck  # noqa: F401
from .performance import DiskSpaceCheck  # noqa: F401
from .security import SecurityPermissionCheck  # noqa: F401
from .skills import SkillsHealthCheck  # noqa: F401
from .bugs import OpenClawBugHintsCheck  # noqa: F401

