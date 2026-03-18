## OpenClaw 技能商城（Skills Marketplace）设计方案

本文档设计 OpenClaw 助手中的「技能商城」能力，面向三类角色：**用户、开发者、平台**。目标是在现有技能管理基础上，升级为一个可扩展、可运营的插件生态。

---

## 一、目标与愿景

- **对用户**：像应用商店一样，方便地发现、安装、更新、管理各类 OpenClaw 技能/插件。
- **对开发者**：提供清晰的技能规范和发布流程，让开发者可以快速把自己的能力打包为可分发的 Skill，并被用户一键安装。
- **对平台**：形成一个统一的技能目录与审核机制，便于运营、推荐和安全控制。

---

## 二、角色与使用场景

### 2.1 用户（使用技能的人）

- 浏览/搜索技能：
  - 按分类、标签、关键字过滤。
  - 查看评分、安装量、更新时间等信息。
- 安装/卸载技能：
  - 一键安装/卸载。
  - 看到安装日志和错误信息（与当前 SkillsPanel 日志打通）。
- 更新技能：
  - 看到哪些技能有新版本。
  - 支持单个更新以及“一键更新全部”。

### 2.2 开发者（技能作者）

- 按约定规范开发技能：
  - 统一的 `skill.json` 元数据。
  - 清晰的入口文件与对 OpenClaw 的调用方式。
- 发布技能：
  - 通过 CLI 或 Web Portal 提交技能信息与代码仓库地址。
  - 接受平台的基础校验与审核。

### 2.3 平台运营

- 维护技能目录与分类：
  - 人工或半自动维护推荐区、分类标签。
- 安全与合规：
  - 基础静态扫描与权限审计。
  - 明确的「官方技能」、「社区技能」标识与审核流程。

---

## 三、整体架构概览

### 3.1 组件划分

- **前端（桌面助手 UI）**
  - `技能商城` 视图：
    - 技能发现（Discover）
    - 技能详情（Skill Detail）
    - 我的技能（My Skills，整合现有 SkillsPanel）
  - 通过 `SkillManager` 和「技能目录 API」拿到技能列表与状态。

- **本地控制层**
  - `SkillManager`（已存在）：
    - 负责「本地已安装技能」的数据源。
    - 调用 `openclaw skill install/uninstall/update` CLI。
  - 技能缓存与日志：
    - 保存最近一次拉取技能目录结果。
    - 技能操作日志用于 UI 展示。

- **远端服务（可从静态 JSON 起步）**
  - 技能目录服务：
    - `GET /skills`：技能列表。
    - `GET /skills/{id}`：技能详情。
    - `GET /skills/{id}/versions`：版本历史。
  - 未来可以从简单的 Git 仓库 JSON 文件演进到真正的服务端应用。

### 3.2 数据流

1. 助手启动时或用户点击「刷新」：
   - 调用技能目录 API，获取「可用技能列表」。
   - 从 `SkillManager` 获取本地安装状态。
   - 合并为 UI 所需的统一数据结构。
2. 用户点击安装/卸载/更新：
   - 助手调用 `openclaw` CLI 执行实际操作。
   - 将 CLI 输出写入「技能操作日志」控件。
   - 操作成功后刷新技能列表与本地状态。

---

## 四、技能规范（Skill Specification）

### 4.1 文件结构示例

一个技能仓库的最小结构：

```text
my-skill/
  skill.json          # 元数据（必需）
  README.md           # 用于详情页展示的说明（推荐）
  CHANGELOG.md        # 版本更新记录（可选）
  src/
    index.ts          # 技能入口，调用 OpenClaw 提供的 SDK
```

### 4.2 skill.json 字段设计

```json
{
  "id": "my-awesome-skill",
  "name": "我的超酷技能",
  "version": "1.0.0",
  "author": "your-name",
  "description": "一句话简介",
  "summary": "更长一点的简介，显示在商城列表中。",
  "categories": ["dev", "productivity"],
  "tags": ["openai", "debug", "workflow"],
  "homepage": "https://example.com",
  "repository": "https://github.com/you/my-awesome-skill",
  "license": "MIT",
  "icon": "🧩",

  "entry": "dist/index.js",
  "engines": {
    "openclaw": ">=2026.3.0",
    "node": ">=18.0.0"
  },

  "permissions": [
    "network",
    "filesystem.read",
    "filesystem.write.temp",
    "openclaw.context"
  ]
}
```

关键点：

- `id`：全局唯一，推荐 `kebab-case`。
- `categories`：与助手 UI 中的分类筛选对应（dev/productivity/media/tool/other）。
- `permissions`：技能可能使用到的敏感能力。
- `engines.openclaw`：标明兼容的 OpenClaw 版本范围，便于助手过滤不兼容技能。

---

## 五、技能商城 UI 设计（助手侧）

### 5.1 顶部导航与布局

- 在助手中将现有 “技能管理” 扩展为两个 Tab：
  - **「技能商城」**：展示所有可用技能（来自目录）。
  - **「我的技能」**：展示本地已安装技能（现有列表升级版）。

### 5.2 技能商城（Discover）视图

- **搜索与筛选区**：
  - 搜索框（按名称 / id / 标签 / 描述）。
  - 分类标签（dev / productivity / media / tool / other）。
  - 筛选项：
    - 已安装 / 未安装。
    - 有更新。
    - 官方技能 / 社区技能。

- **技能卡片列表**（类似现有 `SkillCard`，但信息更丰富）：
  - 图标 + 名称 + 版本。
  - 状态标签：
    - `官方`、`有更新`、`已安装`。
  - 简要描述（截断）。
  - 点击卡片进入「技能详情」。

### 5.3 技能详情视图

在右侧详情面板或新弹窗中展示：

- 基本信息：
  - 名称、id、版本、作者。
  - 图标、分类、标签。
  - 官方/社区标识。
- 内容展示：
  - `README.md` 渲染为 HTML/文本（截断 + “查看更多”）。
  - 权限说明：根据 `permissions` 列表，用人话解释技能能干什么。
  - 更新记录：最近版本号和更新日期（链接到 `CHANGELOG.md` 或仓库 release）。
- 操作按钮：
  - 已安装：
    - `卸载` / `更新`。
  - 未安装：
    - `安装`。
  - 链接：
    - `打开文档`（homepage 或 README）。
    - `打开仓库`。

### 5.4 我的技能（My Skills）视图

- 仅展示已安装技能：
  - 列表分组：
    - 正常
    - 有更新
    - 出错/损坏（如安装过但元数据无法读取）
  - 支持：
    - 一键更新全部。
    - 快速打开本地日志（与现有「技能操作日志」打通）。

---

## 六、技能目录与服务端设计

### 6.1 技能目录数据结构

目录中的一个技能条目（服务端存储视角）：

```json
{
  "id": "my-awesome-skill",
  "name": "我的超酷技能",
  "version": "1.0.0",
  "author": "your-name",
  "summary": "一句话简介",
  "categories": ["dev"],
  "tags": ["openai", "debug"],
  "icon": "🧩",

  "repository": "https://github.com/you/my-awesome-skill",
  "homepage": "https://example.com",
  "license": "MIT",

  "isOfficial": false,
  "downloads": 1234,
  "updatedAt": "2026-03-10T12:00:00Z"
}
```

### 6.2 API 设计（可从静态 JSON 起步）

- `GET /skills`
  - 参数：
    - `q`：搜索关键字。
    - `category`：分类。
    - `tags`：标签。
  - 返回：技能列表。

- `GET /skills/{id}`
  - 返回：完整元数据 + README 渲染链接。

- `GET /skills/{id}/versions`
  - 返回：版本历史信息（version/date/changelog-url）。

**第一阶段实现建议**：

- 不必一开始搭完整服务端，而是：
  - 维护一个 Git 仓库 `openclaw-skills-index`，里面有一个 `index.json`。
  - 助手使用 `https://raw.githubusercontent.com/.../index.json` 作为技能目录读取来源。

---

## 七、开发者发布流程设计

### 7.1 发布路径（CLI 优先）

1. 开发者本地完成技能开发，保证：
   - 仓库中包含合法的 `skill.json`。
   - `README.md` 说明清晰。
2. 通过 CLI 执行：

```bash
openclaw skill publish --repo https://github.com/you/my-awesome-skill
```

3. CLI 将：
   - 拉取 `skill.json` 并进行本地校验。
   - 将元数据提交到技能目录服务。
4. 平台收到提交后：
   - 自动校验：
     - JSON 结构。
     - 版本号格式。
     - 权限列表合法性。
   - 进入审核队列。

### 7.2 审核规则（初稿）

- **必需字段检查**：`id/name/version/description/entry/permissions` 等。
- **安全检查**（自动）：
  - 对仓库进行静态扫描，查找：
    - 明显的恶意代码（如直接删除用户目录）。
    - 非声明权限的敏感操作。
- **人工审查**：
  - 首批技能可以完全人工过目。
  - 通过后标记为「已审核」，允许被技能商城展示。

---

## 八、安全与权限模型

### 8.1 权限类型

初步列出几类常见权限（可逐步扩展）：

- `network`：访问外网。
- `filesystem.read`：读取用户文件。
- `filesystem.write.temp`：写入临时目录。
- `openclaw.context`：读取当前对话上下文。
- `openclaw.execute`：调用 OpenClaw 的命令运行能力。

### 8.2 用户侧提示

- 在技能详情页中，以清晰的列表展示：

> 本技能需要的权限：
>
> - 访问网络（network）
> - 读取临时文件（filesystem.read）
> - 访问当前对话上下文（openclaw.context）

- 对高风险权限显示醒目警告：
  - 如 `filesystem.write`、`execute shell command` 等。

---

## 九、迭代路线图（Roadmap）

### 阶段 1：MVP（本地模拟目录）

- 在现有 `SkillsPanel` 基础上：
  - 增加「技能商城 / 我的技能」Tab。
  - 从本地 `skills_index.json` 读取「模拟目录」。
  - 用更丰富的 SkillCard 与详情面板展示数据。
- 不涉及真正的远端发布，只支持本地/官方预置技能展示。

### 阶段 2：远端目录 + 简单发布

- 搭建简单的 skills-index 仓库或服务：
  - 助手改为从远端 JSON 拉取列表。
- 增加 `openclaw skill publish` 基础命令：
  - 仅校验 `skill.json` 并提交元数据。
- 平台侧以手动方式维护 index.json，完成最小可用链路。

### 阶段 3：完整生态 & 审核

- 扩展目录服务为独立后端：
  - 提供 API。
  - 维护下载量、评分、评论等。
- 引入审核与安全扫描：
  - 自动静态检查 + 人工审核流程。
- 用户侧增加：
  - 技能评分。
  - 安装量、安装趋势。

---

## 十、与「龙虾管家」其他模块的协同

- **与诊断中心（龙虾健康中心）协同**：
  - 技能健康检查（SkillsHealthCheck）可以读取「技能商城」元数据：
    - 提示哪些技能长期未更新。
    - 提示已安装技能中存在被撤回的技能。
- **与版本/更新面板协同**：
  - 技能也可以在「版本管理」面板中列出“插件更新”信息。

---

本设计文档是技能商城的第一版方案，后续可根据实际实现进度与生态反馈进行调整与细化。***
