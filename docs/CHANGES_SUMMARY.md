# OpenClaw Butler - API Key 安全优化修改总结

## 修改文件

### 1. openclaw_installer_v2.py

#### 新增功能函数（文件顶部）
- `get_api_key_env_var_name(provider)` - 生成环境变量名称
- `get_api_key_from_env(provider)` - 从环境变量读取 API Key
- `set_api_key_to_env(provider, api_key, permanent)` - 设置环境变量
- `get_api_key_secure(provider, config)` - 安全获取 API Key（优先环境变量）

#### 修改 ConfigDialog 类
- **新增 UI 元素**: 保存方式选择（环境变量/配置文件）
- **修改 `load_existing_config()`**: 优先从环境变量读取 API Key
- **新增 `on_save_method_change()`**: 更新保存方式提示
- **修改 `on_model_change()`**: 调用更新保存方式提示
- **修改 `save_config()`**: 支持保存到环境变量或配置文件
- **修改 `test_connection()`**: 显示 API Key 来源

### 2. openclaw_assistant.py

#### 修改 InstallPanel 类
- **修改 `_is_model_configured()`**: 同时检查环境变量和配置文件

## 新增文件

- `API_KEY_SECURITY_GUIDE.md` - 用户使用指南

## 使用方式

### 通过界面配置
1. 打开 OpenClaw 管家
2. 点击"仅配置模型"
3. 选择"环境变量 (推荐)"
4. 输入 API Key 并保存

### 手动设置环境变量

```powershell
# Windows
$env:OPENCLAW_API_KEY_DEEPSEEK = "sk-your-api-key"

# 或永久设置
[Environment]::SetEnvironmentVariable("OPENCLAW_API_KEY_DEEPSEEK", "sk-your-api-key", "User")
```

## 环境变量命名规则

```
OPENCLAW_API_KEY_<PROVIDER_UPPERCASE>
```

例如：
- `OPENCLAW_API_KEY_DEEPSEEK`
- `OPENCLAW_API_KEY_MOONSHOT`
- `OPENCLAW_API_KEY_OPENAI`

## 优先级

1. 环境变量（最高优先级）
2. 配置文件（向后兼容）

## 向后兼容

- 现有配置完全兼容
- 环境变量优先于配置文件
- 可以同时使用两种方式
