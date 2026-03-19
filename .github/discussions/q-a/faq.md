# ❓ 常见问题解答 (FAQ)

## 入门问题

### Q: Butlerclaw 是什么？
**A:** Butlerclaw 是 OpenClaw 生态的专属管家，一个跨平台桌面应用，帮助用户管理 OpenClaw 的安装、配置、Agent 团队协作和成本控制。

### Q: 支持哪些平台？
**A:** Windows、macOS、Linux 都支持。

### Q: 需要付费吗？
**A:** Butlerclaw 完全免费开源（MIT 协议）。

## 使用问题

### Q: 如何添加远程 OpenClaw 实例？
**A:** 在"多实例管理"面板中，点击"添加实例"，支持 SSH 和 WebSocket 连接。

### Q: 团队协作功能如何使用？
**A:** 
1. 创建团队
2. 邀请成员
3. 创建 Agent 模板
4. 为成员分配权限
5. 一键部署到成员实例

### Q: 成本追踪准确吗？
**A:** 我们通过 OpenClaw Gateway 统计 token 用量，准确率 >95%。

## 技术问题

### Q: 数据存储在哪里？
**A:** 本地 SQLite 数据库，路径：`~/.butlerclaw/`

### Q: 支持哪些模型？
**A:** 
- 国产：Kimi、DeepSeek、通义千问
- 国际：GPT-4o、Claude、Gemini

---

**还有其他问题？** 请创建新的 Discussion 或提交 Issue！
