# 🚀 贡献者指南

感谢你对 Butlerclaw 的兴趣！我们欢迎各种形式的贡献。

## 🧱 开发环境

- **Python**：建议使用 Python 3.8–3.12（推荐 3.11+/与 CI 一致的版本）
- **依赖安装**：

```bash
git clone https://github.com/metahuan/butlerclaw.git
cd butlerclaw

python -m venv venv
venv\Scripts\activate  # Windows
# 或
source venv/bin/activate  # macOS / Linux

pip install -r requirements-dev.txt
```

启动应用：

```bash
python openclaw_assistant.py
```

## 🎯 如何贡献

### 1. 报告 Bug

使用 [Bug Report Template](../issues/new?template=bug_report.md) 提交 Issue。  
请尽量提供：

- 操作系统、Python 版本、Butlerclaw 版本
- 复现步骤
- 期望结果 vs 实际结果

### 2. 提出功能建议

使用 [Feature Request Template](../issues/new?template=feature_request.md) 提交 Issue。  
建议说明：

- 你的使用场景
- 目前的痛点
- 你期望 Butlerclaw 帮你做到什么

### 3. 提交代码

1. Fork 本仓库
2. 从 `main` 创建你的功能分支（例如：`git checkout -b feat/team-panel-improvement`）
3. 提交更改（推荐使用类似 `feat: ...` / `fix: ...` / `docs: ...` 的提交信息）
4. 推送到你的远程分支（`git push origin feat/team-panel-improvement`）
5. 打开 Pull Request，简要说明改动动机与主要修改点

> PR 在合并前需要通过 CI（测试 + 代码风格检查）。

### 4. 改进文档

文档改进也是重要的贡献！  
你可以：

- 补充/修正文档内容
- 优化 README / 安装说明 / 使用指南
- 翻译或本地化（中英文皆可）

## 📋 代码规范

- 遵循 PEP 8 Python 代码规范
- 添加适当的文档字符串，解释关键设计或非直观逻辑
- 避免引入未使用的依赖
- 在可能的情况下，为新功能补上或更新测试

## 🧪 测试

```bash
# 运行测试
pytest tests/ -v

# 检查代码风格
flake8 .
```

建议在提交 PR 前本地至少跑一遍测试与 flake8。

## 💬 语言与交流

- Issue / PR 可使用 **中文或英文**  
- 建议使用英文标题，方便更多开发者快速了解问题/改动

## 📞 需要帮助？

- 💬 [GitHub Discussions](../discussions)
- 🐛 [Issues](../issues)

---

再次感谢你的贡献！🙏
