## OpenClaw 诊断模块（Health Center）设计方案

本文档描述 `diagnose/` 诊断模块的整体设计，用于支撑 OpenClaw 助手中的“诊断工具 / 360 管家”能力。

---

## 目标与定位

- **目标**：从单一脚本式诊断，升级为可扩展的“健康中心（Health Center）”：
  - 有总览：整体健康分、分类概览、一句话结论。
  - 有细节：按分类展示每一条检查项的状态、详情与修复建议。
  - 有动作：支持一键修复（对安全的项）、导出诊断报告、为用户提供下一步操作指引。
- **定位**：作为一个与 UI 解耦的 Python 包，提供统一的诊断引擎和数据结构，方便：
  - Tk GUI（当前助手界面）调用。
  - 未来若有 CLI / 日志 / 远程诊断，也可以复用。
  -真正的自动修复逻辑已经在数据结构里预留了 fix_action，等你以后要做收费版时，只需要在对应检查上填入 fix_action，并在这个位置把提示改成实际执行即可。
---

## 目录结构设计

```text
diagnose/
  __init__.py

  # 1. 核心模型 + 引擎
  models.py          # 通用类型：Result, Check, Category, Severity, FixAction...
  engine.py          # DiagnosticEngine：调度、运行 checks，聚合结果
  scoring.py         # 健康度评分算法（把结果 -> 分数 & 总评）

  # 2. 具体检查实现
  checks/
    __init__.py
    environment.py   # Node / npm / 系统信息等环境检查
    cli.py           # openclaw CLI 相关检查
    config.py        # openclaw.json 结构、内容、models.providers 等
    network.py       # npm registry / 常用 API 的连通性
    security.py      # 权限、敏感信息、配置泄露风险
    dependencies.py  # 依赖工具 / 库的检查（预留）
    skills.py        # 技能 / 插件健康检查（依赖 SkillManager）
    performance.py   # 性能 / 磁盘空间等简单性能相关检查

  # 3. 自动修复实现（Fixers）
  fixes/
    __init__.py
    config_fixer.py        # 修复 openclaw.json 结构、备份 + 重建 models.providers
    cli_fixer.py           # 安装 / 更新 openclaw CLI 的动作封装
    environment_fixer.py   # Node 相关的安装 / 升级指引（不直接安装）
    cache_fixer.py         # 日志 / 缓存清理逻辑（可与 SettingsPanel 复用）

  # 4. 报告与导出
  reporting/
    __init__.py
    text_reporter.py   # 把 results 渲染成纯文本（GUI 文本框 + 文本报告导出）
    json_reporter.py   # 导出 JSON 报告（便于上传调试）
```

---

## 核心模型与引擎设计

### 1. 数据模型（models.py）

- **DiagnosticCategory**：字符串常量或 Enum，例如：
  - `env`（环境）
  - `cli`（OpenClaw CLI）
  - `config`（配置与模型）
  - `network`（网络连通性）
  - `security`（安全）
  - `skills`（技能与插件）
  - `performance`（性能）
- **DiagnosticSeverity**：
  - `info` / `warn` / `error`
- **DiagnosticStatus**：
  - `pass` / `warn` / `fail`
- **FixAction**：
  - 描述可以被执行的修复行为：
    - 方式一：包装为 Python 可调用对象 `Callable[[], FixResult]`。
    - 方式二：仅描述 shell 命令 + 是否需要管理员权限，由调用方决定是否执行。
- **DiagnosticResult**：
  - `id`: 唯一标识（字符串）
  - `name`: 可读名称
  - `category`: 分类（使用 DiagnosticCategory）
  - `severity`: 严重程度
  - `status`: 检查状态（pass / warn / fail）
  - `message`: 面向普通用户的一句话描述
  - `details`: 供进阶用户和开发者查看的技术细节
  - `fix_suggestions: list[str]`: 文本形式的修复建议
  - `fix_action: Optional[FixAction]`: 可选的自动修复动作
  - `auto_safe: bool`: 是否适合被“一键修复”自动执行

- **DiagnosticCheck**（协议/基类）：
  - 属性：
    - `id`, `name`, `category`, `severity`
  - 方法：
    - `run() -> DiagnosticResult`

### 2. 诊断引擎（engine.py）

- **DiagnosticEngine** 主要职责：
  - 持有一组 `DiagnosticCheck` 实例。
  - 负责顺序（或未来并行）执行检查。
  - 按分类或全量返回结果。
- 对外接口：
  - `register_check(check: DiagnosticCheck) -> None`
  - `register_checks(checks: Iterable[DiagnosticCheck]) -> None`
  - `run_all() -> list[DiagnosticResult]`
  - `run_by_category(category: str) -> list[DiagnosticResult]`
  - 可选：`get_checks()` / `get_categories()` 等。

> 设计原则：引擎不依赖任何 UI（Tk / CLI），只依赖 models 与 checks 模块。

---

## 健康评分与总览（scoring.py）

- 输入：一组 `DiagnosticResult`。
- 输出：
  - 整体健康分数（0–100）。
  - 每个分类的子分数。
  - 一句话总结：如“环境正常，但配置存在风险”、“基本健康，建议完善 API Key 配置”等。
- 简单实现策略（可后续调优）：
  - 给不同 `severity` + `status` 组合分配权重。
  - 按照分类聚合，最后求加权平均。

---

## 各类检查实现（checks/）

### environment.py
- Node.js 版本存在性与版本建议。
- npm 是否可用（可选）。
- 磁盘空间是否足够。

### cli.py
- `openclaw` 命令是否存在。
- CLI 版本是否可解析 & 是否过旧。

### config.py
- 配置文件是否存在（`openclaw.json`）。
- JSON 是否可解析。
- `models.providers` 是否存在且为对象。
- 是否至少有一个 provider 配置了 `apiKey`。

### network.py
- 访问 `https://registry.npmjs.org` 是否成功。
- 未来可以扩展到其它必要服务。

### security.py
- 非 Windows：配置目录、配置文件、日志目录的权限检查。
- 是否包含 API Key，并给出“不上传配置文件”的提醒。

### dependencies.py
- 预留：检查 OpenClaw 依赖的其他工具 / 插件。

### skills.py
- 使用 `SkillManager`：
  - 查看已安装技能列表。
  - 检查是否存在“安装但 metadata 异常 / 配置缺失”的技能。

### performance.py
- 当前阶段：
  - 磁盘空间预警也可视作性能相关指标之一。
- 未来可以扩展：
  - 启动耗时统计（需要采集）。
  - 日志体积过大等问题。

---

## 自动修复模块（fixes/）

### config_fixer.py
- 负责：
  - 备份现有配置（添加 `.bak.<timestamp>` 后缀）。
  - 在配置缺失 / 损坏时生成最小配置结构：`{"models": {"providers": {}}}`。
  - 在结构异常时修复 `models` 与 `models.providers` 字段。

### cli_fixer.py
- 封装：
  - 通过 `npm install -g openclaw@latest` 安装 / 更新 CLI。
  - 解析输出中的权限错误关键词，返回清晰的提示。

### environment_fixer.py
- 不直接安装 Node.js，而是：
  - 根据平台（Windows / macOS / Linux）给出详细的安装指引和链接。

### cache_fixer.py
- 清理：
  - 日志目录。
  - 助手缓存目录。
- 与 `SettingsPanel._clear_cache` 共用核心逻辑，避免重复代码。

> 所有 Fixer 函数都返回统一的结果结构，供 UI 展示“修复成功 / 失败 / 提示”。

---

## 报告与导出（reporting/）

### text_reporter.py
- 输入：`List[DiagnosticResult]`。
- 输出：一段包含标题、分类分组、小结的多行文本。
- 用途：
  - 显示在 Tk 的 `ScrolledText` 中。
  - 导出为 `.txt` 报告。

### json_reporter.py
- 输入：`List[DiagnosticResult]` +（可选）评分结果。
- 输出：结构化的 JSON。
- 用途：
  - 导出为 `.json` 报告。
  - 便于用户反馈问题时附带环境信息。

---

## 与现有 DiagnosePanel 的集成路径

### 阶段 1：引擎接入（不大改 UI）
- 在 `DiagnosePanel._run_diagnose` 中：
  - 调用 `DiagnosticEngine.run_all()` 获取结果列表。
  - 使用 `text_reporter` 渲染出文本，填充到当前的结果框。
  - 记录 `_last_report` 以便导出。
- 在 `DiagnosePanel._auto_fix` 中：
  - 再跑一次诊断（或使用缓存结果）。
  - 过滤出 `auto_safe = True` 且 `status in {warn, fail}` 且存在 `fix_action` 的结果。
  - 顺序执行对应 `FixAction`，将执行日志追加到文本框。

### 阶段 2：UI 升级为“龙虾管家”
- 在面板顶部增加：
  - 健康度进度条（0–100）。
  - 一句话总结 Label。
- 中间区域：
  - 左侧展示各分类的通过率 / 问题数。
  - 右侧展示选中分类的具体问题列表（带状态图标 + 详情/修复按钮）。
- 底部：
  - 保留“开始诊断”、“导出诊断报告”、“一键修复”按钮。
  - 可增加“深度扫描”（用于未来更重的检查）。

---

## 开发步骤（Roadmap）

1. **实现基础模型与引擎**
   - 新建 `diagnose/` 包。
   - 实现 `models.py`：数据结构与类型。
   - 实现 `engine.py`：注册 + 调度检查的骨架。

2. **迁移现有诊断逻辑到 checks/**（保持现有行为）
   - 从 `DiagnosePanel._run_diagnose` 中拆出：环境 / CLI / 配置 / 网络 / 安全 / Bug 检查。
   - 将“一键修复”中的配置修复逻辑迁入 `config_fixer.py`，并在 checks 中返回相应 `FixAction`。

3. **将 DiagnosePanel 切换为使用引擎**
   - `_run_diagnose` 仅负责调用引擎 + 渲染文本。
   - `_auto_fix` 调用引擎结果中的 `FixAction`。

4. **引入 scoring 与健康总览**
   - 实现 `scoring.py`，根据结果计算分数与总结。
   - 在 UI 顶部增加健康度显示与 summarizing 文本。

5. **实现 reporting/** 模块**
   - 文本报告渲染移动到 `text_reporter.py`。
   - 新增 JSON 报告导出能力。

6. **进一步扩展 checks 与 fixes**
   - 增加 `skills.py`，对技能状态进行检查。
   - 增加更多安全 / 性能 / 依赖相关的规则。

