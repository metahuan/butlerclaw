"""
core 模块

Butlerclaw 核心功能模块：
- instance_manager: 多实例管理
- cost_tracker: 成本控制
- team_collab: 团队协作
"""

from .instance_manager import (
    InstanceManager,
    InstanceInfo,
    InstanceStatus,
    InstanceType,
    ResourceUsage,
    CommandResult,
)

from .cost_tracker import (
    CostTracker,
    CostBudget,
    CostAlertLevel,
    APICallRecord,
    CostAlert,
    ModelPricing,
)

from .team_collab import (
    TeamCollaborationManager,
    UserRole,
    AuditAction,
    SyncStatus,
    TeamMember,
    AuditLogEntry,
    SharedSkill,
    ConfigSyncItem,
)

__all__ = [
    # 实例管理
    "InstanceManager",
    "InstanceInfo",
    "InstanceStatus",
    "InstanceType",
    "ResourceUsage",
    "CommandResult",
    # 成本控制
    "CostTracker",
    "CostBudget",
    "CostAlertLevel",
    "APICallRecord",
    "CostAlert",
    "ModelPricing",
    # 团队协作
    "TeamCollaborationManager",
    "UserRole",
    "AuditAction",
    "SyncStatus",
    "TeamMember",
    "AuditLogEntry",
    "SharedSkill",
    "ConfigSyncItem",
]
