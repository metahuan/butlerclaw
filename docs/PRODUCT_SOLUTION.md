# OpenClaw 安装助手 - 产品级解决方案

## 问题分析

打包后的 exe 在不同用户环境下运行时，主要面临以下问题：

1. **环境变量差异** - 不同用户的 PATH、HOME 等环境变量不同
2. **OpenClaw 安装位置不确定** - 可能通过 npm 全局安装、npx 运行，或自定义路径
3. **配置文件位置不确定** - `~/.openclaw` 目录的实际路径因用户而异
4. **外部命令依赖** - 依赖 `openclaw skills list` 命令获取技能数据

## 解决方案

### 1. 内置技能数据（核心改进）

不再依赖 `openclaw skills list` 命令，而是内置常用技能数据：

```python
BUNDLED_SKILLS = [
    {
        "id": "weather",
        "name": "天气查询",
        "description": "获取当前天气和预报...",
        "icon": "☔",
        "category": "tool",
        "source": "openclaw-bundled"
    },
    # ... 更多技能
]
```

**优点：**
- ✅ 无需联网即可查看技能列表
- ✅ 不依赖 OpenClaw CLI 命令
- ✅ 在任何用户环境下都能正常工作
- ✅ 启动速度快

### 2. 跨平台用户目录检测

```python
def _get_user_home(self):
    """获取用户主目录 - 跨平台兼容"""
    for env_var in ['USERPROFILE', 'HOME']:
        path = os.environ.get(env_var)
        if path and os.path.isdir(path):
            return path
    return os.path.expanduser("~")
```

### 3. 智能命令查找

安装/卸载/更新技能时，智能查找 openclaw 命令：

```python
def _get_openclaw_cmd(self):
    # 1. 从系统 PATH 中找
    # 2. 尝试 npx openclaw
    # 3. 尝试 npm 全局安装目录
    # 4. 尝试常见路径
```

### 4. 优雅降级

即使找不到 OpenClaw 命令，程序也能正常工作：
- 可以查看所有技能
- 可以搜索技能
- 只是无法安装/卸载（会提示用户安装 OpenClaw）

## 文件变更

### skills_manager.py（重写）
- 内置 18 个常用技能数据
- 移除对 `openclaw skills list` 的依赖
- 改进用户目录检测逻辑
- 添加跨平台兼容性

### skills_panel_new.py（优化）
- 移除 `_fetch_skills_from_cli()` 方法
- 简化 `_refresh()` 方法
- 保留安装/卸载/更新功能（使用智能命令查找）

### OpenClaw安装助手.spec（优化）
- 添加隐藏导入
- 排除不必要的模块（减小体积）
- 优化打包配置

### build_product.bat（新建）
- 产品级打包脚本
- 包含测试步骤
- 生成产品文档

## 使用说明

### 开发测试
```bash
python openclaw_assistant.py
```

### 产品打包
```bash
build_product.bat
```

### 发布检查清单
- [ ] 在干净环境（未安装 OpenClaw）测试 exe 能否正常运行
- [ ] 检查技能列表是否正确显示（应显示内置的 18 个技能）
- [ ] 测试搜索功能
- [ ] 测试翻译功能
- [ ] 在安装 OpenClaw 的环境测试安装/卸载功能

## 用户场景

### 场景 1：用户未安装 OpenClaw
- 可以查看所有内置技能
- 可以搜索技能
- 点击"安装"会提示需要先安装 OpenClaw

### 场景 2：用户已安装 OpenClaw
- 可以查看所有技能
- 已安装的技能会显示"已安装"标记
- 可以安装/卸载/更新技能

### 场景 3：用户通过 npx 使用 OpenClaw
- 程序会自动检测 npx
- 安装/卸载/更新功能正常工作

## 后续优化建议

1. **自动检测 OpenClaw 安装状态**
   - 启动时检测系统中是否安装了 OpenClaw
   - 如未安装，提供一键安装按钮

2. **在线更新技能数据**
   - 定期从服务器获取最新技能列表
   - 合并到内置数据中

3. **技能详情缓存**
   - 缓存技能的详细描述和图标
   - 提升加载速度

4. **多语言支持**
   - 内置多语言技能描述
   - 根据系统语言自动切换
