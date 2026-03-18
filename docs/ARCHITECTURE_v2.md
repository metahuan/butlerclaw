# Butlerclaw 架构设计 v2.0

> 本文档描述 Butlerclaw 从传统桌面应用向现代化、可扩展架构的演进方案。
> 
> 版本: v2.0  
> 日期: 2026-03-18  
> 作者: Architect Agent

---

## 目录

1. [现状分析](#1-现状分析)
2. [架构目标](#2-架构目标)
3. [总体架构](#3-总体架构)
4. [核心模块设计](#4-核心模块设计)
5. [接口设计](#5-接口设计)
6. [数据模型](#6-数据模型)
7. [迁移路径](#7-迁移路径)
8. [关键决策](#8-关键决策)

---

## 1. 现状分析

### 1.1 现有架构概览

Butlerclaw 当前是一个 Python + Tkinter 桌面应用，主要包含以下模块：

- **主程序**: `openclaw_assistant.py` (2500+ 行，单体结构)
- **安装器**: `openclaw_installer_v2.py` (跨平台安装向导)
- **技能管理**: `skills_manager.py`, `skills_panel_new.py`
- **Hub 集成**: `hub_skills_api.py`, `clawhub_api.py`
- **诊断模块**: `diagnose/` (引擎 + 检查项)
- **安全模块**: `security/` (扫描 + 加固)
- **技能安装**: `skills/` (队列 + 依赖检查)
- **UI 组件**: `ui/` (健康面板 + 技能市场)

### 1.2 技术债务识别

| 问题 | 影响 | 优先级 |
|------|------|--------|
| **单体主程序** (2500+ 行) | 难以维护、测试困难 | P0 |
| **紧耦合 UI 与业务逻辑** | 无法独立演化、难以单元测试 | P0 |
| **缺乏统一配置管理** | 配置分散在多个文件 | P1 |
| **无成本追踪机制** | 无法监控 API 调用成本 | P1 |
| **无多实例管理能力** | 无法管理多个 OpenClaw 实例 | P1 |
| **插件机制缺失** | 扩展性差 | P2 |
| **团队协作功能空白** | 无法共享配置 | P2 |

### 1.3 扩展瓶颈

1. **UI 层瓶颈**: Tkinter 难以实现复杂交互
2. **状态管理瓶颈**: 无统一状态管理
3. **通信瓶颈**: 缺乏实例间通信机制
4. **数据瓶颈**: 无本地数据持久化层

---

## 2. 架构目标

### 2.1 核心目标

- **单体应用** → **模块化架构**
- **单机运行** → **多实例管理**
- **无成本意识** → **成本追踪**
- **个人使用** → **团队协作**
- **封闭系统** → **插件扩展**

### 2.2 设计原则

| 原则 | 说明 |
|------|------|
| **向后兼容** | 现有配置、技能、脚本全部兼容 |
| **渐进演进** | 分阶段重构，非推倒重来 |
| **Python 优先** | 核心保持 Python 生态 |
| **事件驱动** | 模块间通过事件总线通信 |
| **依赖注入** | 组件通过容器管理依赖 |

---

## 3. 总体架构

### 3.1 架构分层

```
┌─────────────────────────────────────────────────────────────────┐
│                        表现层 (Presentation)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Tkinter UI │  │  Web UI     │  │  CLI / API 接口         │  │
│  │  (现有保留) │  │  (渐进增强) │  │  (新增)                 │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                        应用层 (Application)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ 安装管理    │  │ 技能市场    │  │ 诊断中心                │  │
│  │ InstallMgr  │  │ SkillMarket │  │ Diagnostics             │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ 成本控制    │  │ 实例管理    │  │ 团队协作                │  │
│  │ CostCtrl    │  │ InstanceMgr │  │ Collaboration           │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                        领域层 (Domain)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ 技能领域    │  │ 配置领域    │  │ 安全领域                │  │
│  │ Skill       │  │ Config      │  │ Security                │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ 实例领域    │  │ 成本领域    │  │ 用户领域                │  │
│  │ Instance    │  │ Cost        │  │ User/Team               │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                        基础设施层 (Infrastructure)               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ 事件总线    │  │ 配置存储    │  │ 插件系统                │  │
│  │ EventBus    │  │ ConfigStore │  │ PluginSystem            │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ 本地数据库  │  │ 网络通信    │  │ API 拦截器              │  │
│  │ SQLite      │  │ Network     │  │ ApiInterceptor          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. 核心模块设计

### 4.1 事件总线 (Event Bus)

统一的事件通信机制，解耦各模块。

```python
class EventBus:
    """异步事件总线，支持同步/异步处理器"""
    
    def subscribe(self, event_type: str, handler: Callable, priority: EventPriority)
    def unsubscribe(self, event_type: str, handler: Callable)
    async def emit(self, event: Event)
```

**核心事件类型:**

| 事件 | 说明 | 触发时机 |
|------|------|----------|
| `instance.discovered` | 发现新实例 | 网络扫描/广播发现 |
| `instance.connected` | 实例连接成功 | 建立通信通道 |
| `cost.api_called` | API 调用发生 | 请求拦截时 |
| `cost.threshold_exceeded` | 成本超限 | 超过预算阈值 |
| `config.changed` | 配置变更 | 配置保存后 |
| `skill.installed` | 技能安装完成 | 安装队列完成 |

### 4.2 多实例管理架构

**实例发现机制:**

1. **本地实例**: 通过文件锁/端口占用检测
2. **局域网实例**: mDNS (Bonjour) 或 SSDP 广播
3. **远程实例**: 配置列表 + 心跳检测
4. **云端实例**: 通过 Butlerclaw Hub 注册发现

### 4.3 成本追踪系统

**架构组件:**

- **API Interceptor**: 拦截 OpenClaw 的 API 调用
- **Cost Calculator**: 基于模型定价计算成本
- **Cost Store**: 持久化存储调用记录
- **Budget Alert**: 预算告警系统

### 4.4 团队协作层

**同步策略:**

- 单向推送 (Push)
- 双向同步 (Sync)
- 主从复制 (Master-Slave)

**权限模型:**

| 角色 | 权限 |
|------|------|
| Owner | 完全控制，可删除团队 |
| Admin | 管理成员、配置同步 |
| Member | 使用共享配置、发起同步请求 |
| Guest | 只读访问 |

### 4.5 插件化扩展机制

**插件类型:**

- UI Plugin: 扩展界面面板和菜单
- Service Plugin: 扩展后台服务
- Command Plugin: 扩展 CLI 命令
- Hook Plugin: 扩展事件钩子

---

## 5. 接口设计

### 5.1 实例管理接口

```python
class InstanceManager:
    def register_provider(self, provider: InstanceProvider)
    async def scan(self) -> List[InstanceInfo]
    async def execute_command(self, instance_id: str, command: str, args: Dict) -> Dict
    async def sync_config(self, instance_id: str, config: Dict)
    def get_instance_status(self, instance_id: str) -> InstanceStatus
```

### 5.2 成本追踪接口

```python
class CostTracker:
    async def record_call(self, call: ApiCall)
    async def get_usage(self, start: datetime, end: datetime, group_by: str) -> Dict
    async def set_budget(self, budget: CostBudget)
    async def get_budget_status(self, budget_id: str) -> BudgetStatus

class ApiInterceptor:
    async def intercept_request(self, provider: str, model: str, request_data: Dict) -> Dict
    async def intercept_response(self, provider: str, model: str, request_data: Dict, response_data: Dict, duration_ms: int)
```

### 5.3 团队协作接口

```python
class TeamManager:
    async def create_team(self, name: str, owner_id: str) -> Team
    async def invite_member(self, team_id: str, email: str, role: Role)
    async def sync_config(self, team_id: str, config_type: str, config_data: Dict, direction: str)
    def check_permission(self, user_id: str, team_id: str, permission: Permission) -> bool
```

### 5.4 插件接口

```python
class Plugin(ABC):
    async def initialize(self, context: PluginContext)
    async def shutdown(self)

class UIPlugin(Plugin):
    def register_panels(self) -> List[Dict]
    def register_menu_items(self) -> List[Dict]
```

---

## 6. 数据模型

### 6.1 数据库 Schema (SQLite)

```sql
-- 实例表
CREATE TABLE instances (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    address TEXT,
    port INTEGER,
    version TEXT,
    status TEXT DEFAULT 'unknown',
    capabilities TEXT,
    metadata TEXT,
    last_seen TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- API 调用记录表
CREATE TABLE api_calls (
    id TEXT PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    operation TEXT NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0,
    duration_ms INTEGER,
    success BOOLEAN DEFAULT 1,
    instance_id TEXT
);

-- 成本预算表
CREATE TABLE cost_budgets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    period TEXT NOT NULL,
    limit_usd REAL NOT NULL,
    alert_threshold REAL DEFAULT 0.8,
    current_usage REAL DEFAULT 0,
    reset_at TIMESTAMP
);

-- 团队表
CREATE TABLE teams (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    sync_strategy TEXT DEFAULT 'sync',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 团队成员表
CREATE TABLE team_members (
    team_id TEXT,
    user_id TEXT,
    email TEXT,
    role TEXT NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (team_id, user_id)
);

-- 共享配置表
CREATE TABLE shared_configs (
    id TEXT PRIMARY KEY,
    team_id TEXT,
    config_type TEXT NOT NULL,
    config_data TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    updated_by TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 7. 迁移路径

### 7.1 阶段规划

**Phase 1: 基础设施 (4-6 周)**
- 建立事件总线
- 创建 SQLite 数据库层
- 重构配置管理
- 保持现有 UI 不变

**Phase 2: 多实例管理 (4-6 周)**
- 实现实例发现机制
- 实现实例间通信
- 添加实例管理 UI 面板
- 集成到现有界面

**Phase 3: 成本追踪 (3-4 周)**
- 实现 API 拦截器
- 创建成本统计面板
- 添加预算告警
- 成本报告导出

**Phase 4: 团队协作 (4-6 周)**
- 实现团队管理
- 配置同步机制
- 权限系统
- 团队 UI 面板

**Phase 5: 插件系统 (6-8 周)**
- 插件加载器
- 插件 API 定义
- 沙箱机制
- 插件市场集成

### 7.2 向后兼容策略

1. **配置文件兼容**: 新配置系统读取旧配置并自动迁移
2. **UI 渐进增强**: 新功能以独立面板形式添加
3. **API 兼容**: 保留现有模块接口，内部逐步重构
4. **数据迁移**: 提供一键迁移脚本

### 7.3 目录结构演进

```
Butlerclaw/
├── butlerclaw/                    # 新核心包
│   ├── core/                      # 基础设施
│   ├── domain/                    # 领域层
│   ├── application/               # 应用层
│   ├── infrastructure/            # 基础设施实现
│   ├── plugin/                    # 插件系统
│   └── ui/                        # 新 UI 层
├── legacy/                        # 旧代码兼容层
│   ├── openclaw_assistant.py
│   ├── skills_manager.py
│   └── ...
├── plugins/                       # 插件目录
├── docs/                          # 文档
└── tests/                         # 测试
```

---

## 8. 关键决策

### 8.1 技术选型决策

| 决策 | 选项 | 选择 | 理由 |
|------|------|------|------|
| 数据库 | SQLite / JSON | **SQLite** | 支持复杂查询、事务、索引 |
| 事件系统 | 同步 / 异步 | **异步** | 避免阻塞 UI，支持并发 |
| UI 框架 | Tkinter / Web / Qt | **Tkinter + WebView** | 渐进增强，保持向后兼容 |
| 通信协议 | HTTP / WebSocket / gRPC | **HTTP + WebSocket** | 简单、通用、易调试 |
| 插件隔离 | 进程 / 线程 / 协程 | **线程 + 沙箱** | 平衡安全与性能 |

### 8.2 架构决策记录 (ADR)

**ADR-001: 使用事件总线替代直接调用**
- **背景**: 模块间直接调用导致紧耦合
- **决策**: 引入异步事件总线
- **后果**: 增加复杂性，但提高可扩展性

**ADR-002: 分层架构 (DDD)**
- **背景**: 需要清晰的模块边界
- **决策**: 采用领域驱动设计的分层架构
- **后果**: 代码量增加，但可维护性提升

**ADR-003: 保持 Tkinter 主界面**
- **背景**: 重写 UI 成本高
- **决策**: 保留 Tkinter，新功能以面板形式添加
- **后果**: 长期需考虑迁移到 Web 技术栈

**ADR-004: SQLite 作为主要存储**
- **背景**: 需要结构化数据存储
- **决策**: 使用 SQLite，JSON 文件作为备份
- **后果**: 引入数据库依赖，但查询能力增强

### 8.3 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 重构引入 Bug | 高 | 保持兼容层，渐进替换 |
| 性能下降 | 中 | 异步处理，缓存优化 |
| 学习成本 | 中 | 完善文档，提供示例 |
| 社区接受度 | 低 | 保持向后兼容，可选升级 |

---

## 附录

### A. 术语表

| 术语 | 说明 |
|------|------|
| OpenClaw | AI Agent 运行时平台 |
| Butlerclaw | OpenClaw 的桌面管理工具 |
| Skill | OpenClaw 的功能扩展模块 |
| Instance | OpenClaw 运行时实例 |
| Hub | 技能市场与云服务 |

### B. 参考资料

- OpenClaw 文档
- DDD 领域驱动设计
- Clean Architecture
- Python asyncio 最佳实践

---

*本文档为 Butlerclaw v2.0 架构设计，将持续迭代更新。*
