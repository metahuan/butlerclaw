# OpenClaw Butler - API Key 安全配置指南

## 更新说明

现已支持**环境变量**存储 API Key，比明文存储在配置文件中更加安全！

## 使用方式

### 方式一：通过界面配置（推荐）

1. 打开 OpenClaw 管家
2. 点击"仅配置模型"
3. 选择"环境变量 (推荐)"作为保存方式
4. 输入 API Key 并保存

程序会自动设置环境变量，API Key 不会写入配置文件。

### 方式二：手动设置环境变量

#### Windows (PowerShell)

```powershell
# 临时设置（当前会话有效）
$env:OPENCLAW_API_KEY_DEEPSEEK = "sk-your-api-key-here"
$env:OPENCLAW_API_KEY_MOONSHOT = "sk-your-api-key-here"

# 永久设置（用户级别）
[Environment]::SetEnvironmentVariable("OPENCLAW_API_KEY_DEEPSEEK", "sk-your-api-key-here", "User")
[Environment]::SetEnvironmentVariable("OPENCLAW_API_KEY_MOONSHOT", "sk-your-api-key-here", "User")

# 永久设置后需要重启程序或重新打开终端
```

#### Windows (CMD)

```cmd
# 临时设置
set OPENCLAW_API_KEY_DEEPSEEK=sk-your-api-key-here

# 永久设置
setx OPENCLAW_API_KEY_DEEPSEEK "sk-your-api-key-here"
```

#### macOS / Linux

```bash
# 临时设置（当前会话）
export OPENCLAW_API_KEY_DEEPSEEK="sk-your-api-key-here"
export OPENCLAW_API_KEY_MOONSHOT="sk-your-api-key-here"

# 永久设置（添加到 ~/.bashrc 或 ~/.zshrc）
echo 'export OPENCLAW_API_KEY_DEEPSEEK="sk-your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

## 环境变量命名规则

```
OPENCLAW_API_KEY_<PROVIDER>
```

其中 `<PROVIDER>` 是提供商名称的大写形式：

| 提供商 | 环境变量名称 |
|--------|-------------|
| deepseek | `OPENCLAW_API_KEY_DEEPSEEK` |
| moonshot | `OPENCLAW_API_KEY_MOONSHOT` |
| alibaba | `OPENCLAW_API_KEY_ALIBABA` |
| openai | `OPENCLAW_API_KEY_OPENAI` |
| anthropic | `OPENCLAW_API_KEY_ANTHROPIC` |
| google | `OPENCLAW_API_KEY_GOOGLE` |

## 优先级说明

程序读取 API Key 的优先级：

1. **环境变量**（最高优先级）
2. 配置文件中的 `apiKey`（向后兼容）

如果环境变量已设置，程序会优先使用环境变量中的值。

## 安全建议

1. **生产环境**：务必使用环境变量存储 API Key
2. **团队协作**：不要将包含 API Key 的配置文件提交到 Git
3. **定期更换**：定期更换 API Key，降低泄露风险
4. **权限控制**：限制配置文件的读取权限（Linux/macOS: `chmod 600`）

## 迁移指南

### 从配置文件迁移到环境变量

1. 打开 OpenClaw 管家
2. 点击"仅配置模型"
3. 选择"环境变量 (推荐)"保存方式
4. 输入 API Key 并保存
5. 程序会自动从配置文件中移除明文存储的 API Key

### 验证环境变量是否生效

```powershell
# Windows
$env:OPENCLAW_API_KEY_DEEPSEEK

# macOS/Linux
echo $OPENCLAW_API_KEY_DEEPSEEK
```

## 故障排除

### 环境变量设置后程序无法读取

**Windows**: 设置永久环境变量后，需要**重启程序**或**重新打开终端**才能生效。

**macOS/Linux**: 执行 `source ~/.bashrc` 或重新登录。

### 如何检查当前使用的 API Key 来源

在配置界面点击"测试连接"，会显示 API Key 的来源（环境变量或配置文件）。

## 向后兼容

- 现有配置文件中的 API Key 仍然有效
- 环境变量优先级高于配置文件
- 可以同时使用两种方式（不同 provider 可以分别设置）
