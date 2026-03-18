# Butlerclaw v2.0 UI 升级 - 迁移指南

## 概述

本文档指导如何将现有的 Butlerclaw 从 tkinter 升级到 v2.0 现代化 UI。

## 方案选择

我们选择了**混合方案 (方案C)**：
- **框架**: ttkbootstrap (现代化 tkinter)
- **复杂组件**: WebView2 嵌入

### 为什么选择混合方案?

1. **渐进升级**: 不需要重写整个应用
2. **风险可控**: 核心功能保持 tkinter 稳定
3. **性能平衡**: 复杂UI用 WebView，简单UI用原生
4. **开发效率**: 复用现有 React 组件

## 安装依赖

```bash
# 核心依赖
pip install ttkbootstrap>=1.10.0
pip install pywebview>=4.4
pip install pystray>=0.19
pip install Pillow>=10.0
pip install psutil>=5.9.0

# 可选依赖 (用于团队协作功能)
pip install pyperclip>=1.8.0
```

## 文件结构

```
Butlerclaw/
├── ui/
│   ├── __init__.py
│   ├── app_v2.py              # 主应用入口 (新)
│   ├── webview_host.py        # WebView 容器 (新)
│   └── theme.py               # 主题管理 (可选)
├── panels/
│   ├── __init__.py            # 更新导出
│   ├── install_panel.py       # 现有
│   ├── skills_panel.py        # 现有
│   ├── version_panel.py       # 现有
│   ├── diagnose_panel.py      # 现有
│   ├── settings_panel.py      # 现有
│   ├── instances_panel.py     # 新增 (多实例管理)
│   ├── cost_panel.py          # 新增 (成本控制)
│   └── team_panel.py          # 新增 (团队协作)
├── web_components/            # 嵌入式 Web 组件
│   ├── charts/               # 图表组件
│   ├── cards/                # 卡片组件
│   └── shared/               # 共享样式
└── docs/
    ├── UI_DESIGN_v2.md        # 设计文档
    └── MIGRATION_GUIDE.md     # 本文档
```

## 快速开始

### 1. 备份现有代码

```bash
# 备份现有主程序
cp openclaw_assistant.py openclaw_assistant.py.bak
```

### 2. 更新入口文件

将 `openclaw_assistant.py` 替换为以下内容：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Butlerclaw v2.0 - 入口文件
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入 v2 应用
try:
    from ui.app_v2 import main
    
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"启动失败: {e}")
    print("请确保已安装依赖:")
    print("  pip install ttkbootstrap pywebview pystray Pillow psutil")
    input("按回车键退出...")
```

### 3. 创建缺失的面板占位符

如果某些面板尚未实现，创建占位符：

```python
# panels/install_panel.py (占位符示例)
import tkinter as ttk
from tkinter import ttk as ttk_module

class InstallPanel(ttk.Frame):
    def __init__(self, parent, app=None, theme_manager=None, **kwargs):
        super().__init__(parent, **kwargs)
        ttk.Label(self, text="安装管理面板\n(待实现)", 
                 justify="center").pack(expand=True)
    
    def on_show(self):
        pass
```

## 面板迁移指南

### 现有面板适配

现有面板需要添加 `theme_manager` 参数：

```python
# 修改前
class SkillsPanel(ttk.Frame):
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app

# 修改后
class SkillsPanel(ttk.Frame):
    def __init__(self, parent, app=None, theme_manager=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.theme_manager = theme_manager
```

### 使用 ttkbootstrap 样式

```python
# 检查 ttkbootstrap 是否可用
try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    TTKBOOTSTRAP_AVAILABLE = True
except ImportError:
    import tkinter as ttk
    from tkinter import ttk as ttk_module
    TTKBOOTSTRAP_AVAILABLE = False

# 使用样式
if TTKBOOTSTRAP_AVAILABLE:
    btn = ttk.Button(parent, text="点击", bootstyle="primary")
else:
    btn = ttk.Button(parent, text="点击")
```

## 新功能面板

### 多实例管理 (InstancesPanel)

```python
from panels.instances_panel import InstancesPanel

# 在 PANEL_CLASSES 中添加
PANEL_CLASSES = {
    # ... 其他面板
    "instances": InstancesPanel,
}
```

功能：
- 本地和远程实例管理
- 实时状态监控 (CPU/内存/网络)
- SSH/Tailscale 远程连接

### 成本控制 (CostPanel)

```python
from panels.cost_panel import CostPanel

# 在 PANEL_CLASSES 中添加
PANEL_CLASSES = {
    # ... 其他面板
    "cost": CostPanel,
}
```

功能：
- 多维度用量统计
- 预算设置与告警
- 成本趋势图表

### 团队协作 (TeamPanel)

```python
from panels.team_panel import TeamPanel

# 在 PANEL_CLASSES 中添加
PANEL_CLASSES = {
    # ... 其他面板
    "team": TeamPanel,
}
```

功能：
- 成员管理
- 共享配置同步
- 操作日志审计

## 主题系统

### 自动主题检测

```python
from ui.app_v2 import ThemeManager

theme_manager = ThemeManager()
print(f"当前主题: {theme_manager.current_theme}")

# 获取主题配置
theme = theme_manager.get_theme()
print(f"主色: {theme['primary']}")
```

### 手动切换主题

```python
# 切换主题
new_theme = theme_manager.toggle_theme()

# 应用主题到窗口
theme_manager.apply_theme(window)
```

## WebView 集成

### 创建图表 WebView

```python
from ui.webview_host import ChartWebView

# 在面板中使用
chart = ChartWebView(parent_frame)
chart.pack(fill="both", expand=True)

# 更新数据
chart.update_data({
    "daily_costs": [45, 52, 38, 65, 48],
    "models": ["GPT-4o", "Claude 3.5"]
})
```

### 创建技能卡片 WebView

```python
from ui.webview_host import SkillCardWebView

skills = [
    {"id": "weather", "name": "天气", "icon": "🌤️", "description": "查询天气"},
    {"id": "github", "name": "GitHub", "icon": "🐙", "description": "GitHub 操作"},
]

webview = SkillCardWebView(parent_frame, skills=skills)
webview.pack(fill="both", expand=True)
```

## 常见问题

### Q: ttkbootstrap 安装失败?

```bash
# 确保 pip 是最新版本
pip install --upgrade pip

# 安装 ttkbootstrap
pip install ttkbootstrap>=1.10.0

# 如果仍失败，尝试从源码安装
pip install git+https://github.com/israel-dryer/ttkbootstrap.git
```

### Q: WebView 无法启动?

Windows: 需要 WebView2 Runtime
- 通常已随 Edge 浏览器安装
- 如未安装，下载：https://developer.microsoft.com/en-us/microsoft-edge/webview2/

macOS: 使用 WKWebView，无需额外安装

Linux: 需要 GTK 和 WebKit2GTK
```bash
# Ubuntu/Debian
sudo apt-get install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.0

# Fedora
sudo dnf install python3-gobject gtk3 webkit2gtk3
```

### Q: 如何回滚到旧版本?

```bash
# 恢复备份
cp openclaw_assistant.py.bak openclaw_assistant.py

# 删除新文件
rm -rf ui/app_v2.py panels/instances_panel.py panels/cost_panel.py panels/team_panel.py
```

## 性能优化建议

1. **延迟加载**: 面板首次显示时才初始化
2. **异步操作**: 网络请求使用线程
3. **缓存数据**: 避免重复读取配置文件
4. **WebView 复用**: 多个图表可以共享一个 WebView 窗口

## 后续开发计划

### Phase 1: 基础升级 (2周)
- [ ] 集成 ttkbootstrap
- [ ] 实现主题切换
- [ ] 重构侧边栏导航

### Phase 2: WebView 集成 (2周)
- [ ] 封装 WebView 组件
- [ ] 实现 Python-JS 通信
- [ ] 迁移技能卡片到 WebView

### Phase 3: 新功能开发 (3周)
- [ ] 多实例管理面板
- [ ] 成本控制仪表板
- [ ] 团队协作界面

### Phase 4: 优化与测试 (1周)
- [ ] 性能优化
- [ ] 响应式适配
- [ ] 跨平台测试

## 参考资源

- [ttkbootstrap 文档](https://ttkbootstrap.readthedocs.io/)
- [pywebview 文档](https://pywebview.flowrl.com/)
- [UI 设计文档](./UI_DESIGN_v2.md)
