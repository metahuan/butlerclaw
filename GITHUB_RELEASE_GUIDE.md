# GitHub 发布指南

## 项目准备完成 ✅

所有代码和文档已准备就绪，可以推送到 GitHub 开源。

---

## 快速开始

### 1. 安装 Git（如未安装）

**Windows:**
```powershell
winget install Git.Git
```

或从 https://git-scm.com/download/win 下载安装

### 2. 初始化 Git 仓库

在 PowerShell 中执行：

```powershell
cd "D:\公司产品\Butlerclaw"

# 初始化仓库
git init

# 添加所有文件
git add .

# 创建初始提交
git commit -m "🎉 Initial commit: Butlerclaw v2.0

- 多实例管理（本地+远程）
- 成本控制（API用量追踪、预算告警）
- 团队协作（权限管理、配置同步）
- 现代化UI（暗色/亮色主题）
- 完整的开源基础设施"
```

### 3. 创建 GitHub 仓库

1. 访问 https://github.com/new
2. 填写信息：
   - Repository name: `butlerclaw`
   - Description: `OpenClaw 生态专属管家 - 一站式安全管理、成本控制与多实例协作平台`
   - 选择 **Public**
   - 不要勾选 "Initialize this repository with a README"
3. 点击 **Create repository**

### 4. 推送到 GitHub

```powershell
# 添加远程仓库（替换 yourusername 为你的 GitHub 用户名）
git remote add origin https://github.com/yourusername/butlerclaw.git

# 推送代码
git push -u origin main
```

### 5. 创建首个 Release

```powershell
# 创建标签
git tag -a v2.0.0 -m "Butlerclaw v2.0.0 - 生态管家首发版"

# 推送标签
git push origin v2.0.0
```

GitHub Actions 将自动：
- 运行测试
- 构建 Windows/macOS/Linux 可执行文件
- 创建 GitHub Release
- 上传发布资源

---

## 项目结构

```
Butlerclaw/
├── .github/              # GitHub 配置
│   ├── workflows/        # CI/CD 工作流
│   └── ISSUE_TEMPLATE/   # Issue 模板
├── core/                 # 核心功能模块
│   ├── instance_manager.py   # 多实例管理
│   ├── cost_tracker.py       # 成本控制
│   ├── team_collab.py        # 团队协作
│   ├── api_interceptor.py    # API 拦截
│   ├── event_bus.py          # 事件总线
│   ├── models.py             # 数据库模型
│   └── __init__.py
├── panels/               # UI 面板
│   ├── instances_panel.py    # 实例管理面板
│   ├── cost_panel.py         # 成本控制面板
│   └── team_panel.py         # 团队协作面板
├── ui/                   # UI 组件
│   ├── app_v2.py             # 新主应用
│   └── webview_host.py       # WebView 容器
├── diagnose/             # 诊断模块
├── security/             # 安全模块
├── skills/               # 技能管理
├── scripts/              # 发布脚本
├── docs/                 # 文档
│   ├── PRD_v2.md             # 产品需求文档
│   ├── ARCHITECTURE_v2.md    # 架构设计文档
│   ├── UI_DESIGN_v2.md       # UI 设计文档
│   └── DEPLOY_GUIDE.md       # 部署指南
├── README.md             # 项目说明
├── LICENSE               # MIT 许可证
└── requirements.txt      # Python 依赖
```

---

## 发布前检查清单

- [ ] 替换 `README.md` 中的 `yourusername` 为实际 GitHub 用户名
- [ ] 替换 `yourusername` 为实际的支持邮箱
- [ ] 添加项目截图到 `docs/screenshots/`
- [ ] 创建项目 logo 并放到 `assets/logo.png`
- [ ] 在 GitHub 仓库设置中启用 Discussions
- [ ] 配置分支保护规则（可选）

---

## 后续开发计划

### Phase 1: 基础设施 (4-6周)
- [ ] 集成事件总线到主程序
- [ ] 数据库初始化和迁移
- [ ] 配置系统重构

### Phase 2: 多实例管理 (4-6周)
- [ ] 实例发现服务
- [ ] SSH 连接管理
- [ ] 统一仪表盘

### Phase 3: 成本控制 (3-4周)
- [ ] API 拦截器集成
- [ ] 成本面板完善
- [ ] 报表导出功能

### Phase 4: 团队协作 (4-6周)
- [ ] 团队管理界面
- [ ] 配置同步机制
- [ ] 权限控制实现

### Phase 5: 插件系统 (6-8周)
- [ ] 插件加载器
- [ ] 沙箱环境
- [ ] 插件市场

---

## 联系方式

- GitHub Issues: https://github.com/yourusername/butlerclaw/issues
- 邮箱: support@butlerclaw.dev

---

🎊 **Butlerclaw 准备就绪，等待开源发布！**
