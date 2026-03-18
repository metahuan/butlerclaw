# OpenClaw 社区分享指南

## OpenClaw 官方社区渠道

根据官方文档 https://docs.openclaw.ai

### 1. GitHub (主要渠道) ⭐ 推荐
- **仓库**: https://github.com/openclaw/openclaw
- **Discussions**: https://github.com/openclaw/openclaw/discussions
- **Issues**: 功能请求和问题报告

**分享方式**:
1. 访问 https://github.com/openclaw/openclaw/discussions
2. 点击 "New discussion"
3. 选择 "Show and tell" 类别
4. 粘贴分享文案

### 2. Discord
- 需要加入 OpenClaw Discord 服务器
- 常见频道：
  - `#general` - 一般讨论
  - `#showcase` 或 `#share` - 项目展示
  - `#help` - 求助

**如何找到 Discord 链接**:
1. 访问 OpenClaw GitHub 主页
2. 查看 README 中的 Discord 徽章
3. 或访问 https://discord.com/invite/clawd (根据你的文档)

---

## 推荐的分享文案（针对 OpenClaw 社区）

### GitHub Discussions 版本

**标题**: `[Show and Tell] Butlerclaw - Desktop Manager for OpenClaw with Multi-Instance Support`

**内容**:

```markdown
## 🎯 Butlerclaw - OpenClaw Ecosystem Butler

I've built a desktop companion tool for OpenClaw power users who manage multiple instances or want better cost visibility.

### What is it?

Butlerclaw is a cross-platform GUI application that provides:

**Multi-Instance Management**
- Discover and manage local OpenClaw instances
- Connect to remote instances via SSH
- WebSocket support for real-time monitoring
- Execute commands across multiple instances

**Cost Control**
- Track API usage and costs by model/provider
- Set daily/monthly budgets with alerts
- Visualize spending trends
- Export cost reports

**Team Collaboration**
- Team-based configuration sharing
- Role-based access control (Admin/Member/Guest)
- Audit logs for configuration changes

**Modern UI**
- Clean interface with dark/light/auto themes
- Built with Python + ttkbootstrap + WebView
- Cross-platform: Windows, macOS, Linux

### Why I built it

As I started running OpenClaw on multiple machines (local laptop, remote VPS, Tailscale network), I found myself:
- Forgetting which instance was running where
- Losing track of API costs across different setups
- Manually syncing configurations between team members

Butlerclaw solves these pain points.

### Tech Stack

- **Backend**: Python 3.8+, asyncio, SQLAlchemy
- **UI**: ttkbootstrap (modern tkinter), WebView for charts
- **Remote**: paramiko (SSH), websockets
- **Observability**: Structured logging, metrics, health checks

### Current Status

- **Version**: v2.0.0-alpha
- **License**: MIT
- **GitHub**: https://github.com/<your-username>/butlerclaw

### Looking for Feedback

I'd love to hear from the OpenClaw community:

1. **Multi-instance management** - Is this a common need? What features would be most useful?
2. **Cost tracking** - Would you use budget alerts? What metrics matter most?
3. **Integration** - Any specific OpenClaw features you'd like to see integrated?
4. **Contributions** - The project is open source and welcomes PRs!

### Screenshots

[Add screenshots here]

### Quick Start

```bash
git clone https://github.com/<your-username>/butlerclaw.git
cd butlerclaw
pip install -r requirements.txt
python openclaw_assistant.py
```

Thanks for checking it out! 🦞
```

---

### Discord 版本（简洁版）

```
🎉 Built something for OpenClaw power users!

Butlerclaw - Desktop manager for multiple OpenClaw instances:

✅ Manage local + remote (SSH/WebSocket) instances  
✅ Track API costs with budget alerts
✅ Team collaboration with shared configs
✅ Modern UI with dark mode

Perfect if you run OpenClaw on multiple machines or want better cost visibility.

🔗 https://github.com/<your-username>/butlerclaw
📦 v2.0.0-alpha | MIT License

Would love feedback from the community!
```

---

## 分享步骤

### 步骤 1: 准备
- [ ] 确认 GitHub 仓库是 Public
- [ ] README 显示正常
- [ ] 添加 2-3 张截图到 README

### 步骤 2: GitHub Discussions (推荐先做这个)
1. 访问 https://github.com/openclaw/openclaw/discussions
2. 点击 "New discussion"
3. 选择 "Show and tell"
4. 粘贴上面的文案
5. 添加截图
6. 发布

### 步骤 3: Discord (如果有)
1. 加入 OpenClaw Discord (链接在 GitHub README)
2. 找到合适的频道（#general, #showcase）
3. 粘贴简洁版文案

### 步骤 4: 跟进
- 回复评论和问题
- 记录功能请求
- 根据反馈迭代

---

## 截图建议

分享时附上以下截图：

1. **主界面** - 显示实例列表
2. **成本面板** - 显示图表和统计
3. **暗色主题** - 展示 UI 美观度

截图保存到 `docs/screenshots/`，并在 README 中引用。

---

## 预期效果

- **Stars**: 目标 50+ 在首周
- **Issues**: 收集用户反馈
- **Discussions**: 建立社区联系
- **Contributors**: 吸引早期贡献者

---

准备好后，直接访问 https://github.com/openclaw/openclaw/discussions 发布即可！
