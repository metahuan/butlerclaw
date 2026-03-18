# Butlerclaw 核心模块文档

## 概述

Butlerclaw 核心模块提供了多实例管理、成本控制和团队协作三大核心功能。

## 模块说明

### 1. 多实例管理模块 (core/instance_manager.py)

统一管理本地和远程 OpenClaw 实例。

#### 主要功能
- **本地实例发现**: 扫描进程、读取配置、发现工作区
- **远程实例连接**: 支持 SSH 和 WebSocket 连接
- **实例状态监控**: 心跳检测、资源使用监控
- **统一操作接口**: 跨实例命令执行、广播命令

#### 核心类
- `InstanceManager`: 实例管理器主类
- `InstanceInfo`: 实例信息数据类
- `InstanceStatus`: 实例状态枚举
- `InstanceType`: 实例类型枚举
- `ResourceUsage`: 资源使用情况
- `CommandResult`: 命令执行结果

#### 使用示例
```python
from core.instance_manager import InstanceManager, InstanceInfo, InstanceType

# 创建管理器
manager = InstanceManager()

# 添加实例
instance = InstanceInfo(
    id="local-1",
    name="本地实例",
    host="localhost",
    port=8080,
    type=InstanceType.LOCAL
)
manager.add_instance(instance)

# 执行命令
result = manager.execute_command("local-1", "echo 'Hello World'")
print(result.stdout)

# 获取资源使用情况
usage = manager.get_resource_usage("local-1")
print(f"CPU: {usage.cpu_percent}%")
```

### 2. 成本控制模块 (core/cost_tracker.py)

追踪 API 调用成本，提供预算管理和告警功能。

#### 主要功能
- **API 调用记录**: 自动拦截和记录 API 调用
- **用量统计**: 按模型、时间段统计用量
- **预算管理**: 设置日/月预算限制
- **成本告警**: 多级阈值告警
- **报表生成**: 支持 JSON 和 Markdown 格式

#### 核心类
- `CostTracker`: 成本追踪器主类
- `CostBudget`: 预算配置
- `CostAlertLevel`: 告警级别枚举
- `APICallRecord`: API 调用记录
- `ModelPricing`: 模型定价

#### 使用示例
```python
from core.cost_tracker import CostTracker, CostBudget

# 创建追踪器
tracker = CostTracker()

# 设置预算
budget = CostBudget(
    daily_limit=10.0,
    monthly_limit=100.0,
    alert_threshold_1=0.5,
    alert_threshold_2=0.8,
    alert_threshold_3=0.95
)
tracker.budget = budget

# 记录 API 调用
cost = tracker.record_call(
    model="gpt-3.5-turbo",
    tokens_input=100,
    tokens_output=50,
    duration_ms=1000,
    success=True
)

# 生成日报
report = tracker.generate_daily_report()
print(f"今日调用: {report['total_calls']}, 成本: ${report['total_cost']}")
```

### 3. 团队协作模块 (core/team_collab.py)

管理团队协作功能，包括权限控制、审计日志和共享技能。

#### 主要功能
- **权限模型**: 管理员/成员/访客三级权限
- **审计日志**: 记录所有操作，支持查询和导出
- **共享技能仓库**: 团队内共享和安装技能
- **配置同步**: 多设备配置同步

#### 核心类
- `TeamCollaborationManager`: 团队协作管理器主类
- `UserRole`: 用户角色枚举
- `TeamMember`: 团队成员
- `AuditAction`: 审计操作类型
- `AuditLogEntry`: 审计日志条目
- `SharedSkill`: 共享技能
- `ConfigSyncItem`: 配置同步项

#### 使用示例
```python
from core.team_collab import (
    TeamCollaborationManager,
    UserRole,
    TeamMember,
    AuditAction
)

# 创建管理器
manager = TeamCollaborationManager()

# 创建管理员
admin = TeamMember(
    id="admin-1",
    username="admin",
    email="admin@example.com",
    role=UserRole.ADMIN
)

# 登录
manager.login(admin)

# 添加团队成员
member = TeamMember(
    id="member-1",
    username="member",
    email="member@example.com",
    role=UserRole.MEMBER
)
manager.add_team_member(member)

# 记录操作
manager.log_action(
    action=AuditAction.SKILL_INSTALL,
    target_type="skill",
    target_id="skill-1",
    details={"name": "test-skill"}
)

# 查询审计日志
logs = manager.get_audit_logs(limit=10)
```

## 测试

运行单元测试：

```bash
cd D:\公司产品\Butlerclaw
python tests/test_core_modules.py
```

测试覆盖：
- 多实例管理模块: 5 个测试用例
- 成本控制模块: 5 个测试用例
- 团队协作模块: 6 个测试用例
- 集成测试: 1 个测试用例

## 集成到主程序

在 `openclaw_assistant.py` 中已集成三个核心模块：

```python
from core.instance_manager import InstanceManager, InstanceInfo, InstanceStatus, InstanceType
from core.cost_tracker import CostTracker, CostBudget, CostAlertLevel
from core.team_collab import TeamCollaborationManager, UserRole, TeamMember

# 初始化
instance_manager = InstanceManager()
cost_tracker = CostTracker()
team_manager = TeamCollaborationManager()
```

## 依赖

- Python 3.8+
- 可选依赖:
  - `paramiko`: SSH 连接支持
  - `websockets`: WebSocket 连接支持
  - `psutil`: 资源监控支持

## 配置

模块配置文件存储在 `~/.openclaw/` 目录：
- `instances.json`: 实例配置
- `cost_config.json`: 成本配置
- `team_members.json`: 团队成员
- `audit_logs/`: 审计日志
- `shared_skills/`: 共享技能
- `config_sync/`: 配置同步

## 注意事项

1. 所有模块都是线程安全的
2. 配置自动保存到文件
3. 审计日志定期归档
4. 成本数据保留 90 天