#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw 安装助手 - 重新设计的技能管理模块

设计改进：
1. 左右分栏布局：列表 + 详情
2. 已安装 / 可安装分区显示
3. 搜索 + 分类筛选
4. 明确的操作按钮（非隐藏点击）
5. 技能详情面板
"""

import os
import sys
import json
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

from skills_manager import SkillManager

try:
    import hub_skills_api
except ImportError:
    hub_skills_api = None
try:
    import hub_auth
except ImportError:
    hub_auth = None


CONFIG_DIR = os.path.expanduser("~/.openclaw")
CONFIG_PATH = os.path.join(CONFIG_DIR, "openclaw.json")


# 技能分类定义
SKILL_CATEGORIES = {
    "all": "全部",
    "tool": "工具",
    "dev": "开发",
    "productivity": "效率",
    "media": "媒体",
    "other": "其他"
}


class SkillCard(tk.Frame):
    """技能卡片组件 - 使用 Canvas 绘制提升性能"""
    
    def __init__(self, parent, skill_info, on_select=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.skill = skill_info
        self.on_select = on_select
        self._selected = False
        
        # 使用普通 Frame 而不是 ttk.Frame，性能更好
        self.configure(
            bg="white",
            highlightbackground="#ddd",
            highlightthickness=1,
            padx=8,
            pady=6
        )
        
        # 图标
        icon = skill_info.get("icon", "📦")
        self.icon_label = tk.Label(self, text=icon, font=("", 18), bg="white")
        self.icon_label.pack(side=tk.LEFT, padx=(0, 8))
        
        # 信息区
        info_frame = tk.Frame(self, bg="white")
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 名称和版本行
        name_frame = tk.Frame(info_frame, bg="white")
        name_frame.pack(fill=tk.X)
        
        name = skill_info.get("name", skill_info.get("id", "未知"))
        self.name_label = tk.Label(
            name_frame, text=name, font=("", 10, "bold"),
            bg="white", fg="#333"
        )
        self.name_label.pack(side=tk.LEFT)
        
        # 版本标签
        version = skill_info.get("version", "?")
        tk.Label(
            name_frame, text=f"v{version}", font=("", 8),
            bg="white", fg="#888"
        ).pack(side=tk.LEFT, padx=(6, 0))
        
        # 状态标记（已安装/有更新）
        if skill_info.get("installed"):
            tk.Label(
                name_frame, text="✓", font=("", 10),
                bg="white", fg="#4CAF50"
            ).pack(side=tk.RIGHT)
        
        # 简介 - 限制长度避免换行过多
        desc = skill_info.get("description", "")
        summary = desc[:45] + "..." if len(desc) > 45 else desc
        self.desc_label = tk.Label(
            info_frame, text=summary, font=("", 8),
            bg="white", fg="#666", anchor=tk.W
        )
        self.desc_label.pack(fill=tk.X)
        
        # 绑定点击事件 - 只绑定到自身
        self.bind("<Button-1>", self._on_click)
        self.icon_label.bind("<Button-1>", self._on_click)
        for child in info_frame.winfo_children():
            for widget in child.winfo_children():
                widget.bind("<Button-1>", self._on_click)
    
    def _on_click(self, event):
        if self.on_select:
            self.on_select(self.skill)
    
    def set_selected(self, selected):
        """设置选中状态"""
        self._selected = selected
        color = "#e3f2fd" if selected else "white"
        self.configure(bg=color, highlightbackground="#2196F3" if selected else "#ddd")
        for widget in self.winfo_children():
            if isinstance(widget, tk.Label):
                widget.configure(bg=color)
            elif isinstance(widget, tk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, (tk.Label, tk.Frame)):
                        child.configure(bg=color)
                        for sub in child.winfo_children():
                            if isinstance(sub, tk.Label):
                                sub.configure(bg=color)


class SkillDetailPanel(ttk.Frame):
    """技能详情面板 - 右侧显示详细信息"""
    
    def __init__(self, parent, on_install=None, on_uninstall=None, on_update=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.skill = None
        self.on_install = on_install
        self.on_uninstall = on_uninstall
        self.on_update = on_update
        
        self._build_ui()
    
    def _build_ui(self):
        # 空状态提示
        self.empty_label = ttk.Label(self, text="选择一个技能查看详情", foreground="gray")
        self.empty_label.pack(expand=True)
        
        # 内容区（初始隐藏）
        self.content_frame = ttk.Frame(self)
        
        # 头部：图标 + 名称
        header = ttk.Frame(self.content_frame)
        header.pack(fill=tk.X, pady=(0, 15))
        
        self.icon_label = ttk.Label(header, text="📦", font=("", 32))
        self.icon_label.pack(side=tk.LEFT, padx=(0, 15))
        
        name_frame = ttk.Frame(header)
        name_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        self.name_label = ttk.Label(name_frame, text="", font=("", 16, "bold"))
        self.name_label.pack(anchor=tk.W)
        
        self.id_label = ttk.Label(name_frame, text="", foreground="gray")
        self.id_label.pack(anchor=tk.W)
        
        # 版本信息
        version_frame = ttk.Frame(self.content_frame)
        version_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(version_frame, text="版本：").pack(side=tk.LEFT)
        self.version_label = ttk.Label(version_frame, text="")
        self.version_label.pack(side=tk.LEFT)
        
        # 描述区域（带翻译按钮）
        desc_header = ttk.Frame(self.content_frame)
        desc_header.pack(fill=tk.X, pady=(15, 5))
        
        ttk.Label(desc_header, text="功能简介", font=("", 11, "bold")).pack(side=tk.LEFT)
        
        # 中文翻译按钮
        self.translate_btn = ttk.Button(
            desc_header, 
            text="中文", 
            width=6,
            command=self._on_translate
        )
        self.translate_btn.pack(side=tk.RIGHT)
        self.translate_btn.pack_forget()  # 初始隐藏
        
        self.desc_text = scrolledtext.ScrolledText(self.content_frame, height=6, wrap=tk.WORD)
        self.desc_text.pack(fill=tk.X, pady=(0, 10))
        self.desc_text.config(state=tk.DISABLED)
        
        # 元信息
        meta_frame = ttk.LabelFrame(self.content_frame, text="信息", padding=10)
        meta_frame.pack(fill=tk.X, pady=10)
        
        self.meta_grid = ttk.Frame(meta_frame)
        self.meta_grid.pack(fill=tk.X)
        
        ttk.Label(self.meta_grid, text="分类：").grid(row=0, column=0, sticky=tk.W)
        self.category_label = ttk.Label(self.meta_grid, text="")
        self.category_label.grid(row=0, column=1, sticky=tk.W, padx=(5, 20))
        
        ttk.Label(self.meta_grid, text="作者：").grid(row=0, column=2, sticky=tk.W)
        self.author_label = ttk.Label(self.meta_grid, text="")
        self.author_label.grid(row=0, column=3, sticky=tk.W, padx=(5, 0))
        
        ttk.Label(self.meta_grid, text="下载：").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.downloads_label = ttk.Label(self.meta_grid, text="")
        self.downloads_label.grid(row=1, column=1, sticky=tk.W, padx=(5, 20), pady=(5, 0))
        
        ttk.Label(self.meta_grid, text="更新：").grid(row=1, column=2, sticky=tk.W, pady=(5, 0))
        self.updated_label = ttk.Label(self.meta_grid, text="")
        self.updated_label.grid(row=1, column=3, sticky=tk.W, padx=(5, 0), pady=(5, 0))
        
        # 操作按钮区
        self.action_frame = ttk.Frame(self.content_frame)
        self.action_frame.pack(fill=tk.X, pady=20)
        
        self.install_btn = ttk.Button(self.action_frame, text="安装", command=self._on_install)
        self.install_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.update_btn = ttk.Button(self.action_frame, text="更新", command=self._on_update)
        self.update_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.uninstall_btn = ttk.Button(self.action_frame, text="卸载", command=self._on_uninstall)
        self.uninstall_btn.pack(side=tk.LEFT)
    
    def show_skill(self, skill_info):
        """显示技能详情"""
        self.skill = skill_info
        self._original_desc = skill_info.get("description", skill_info.get("summary", "暂无描述"))
        self._translated_desc = None
        self._is_translated = False
        
        # 隐藏空状态，显示内容
        self.empty_label.pack_forget()
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 更新信息
        self.icon_label.config(text=skill_info.get("icon", "📦"))
        self.name_label.config(text=skill_info.get("name", skill_info.get("id", "未知")))
        self.id_label.config(text=skill_info.get("id", ""))
        
        # 版本显示
        version = skill_info.get("version", "?")
        if skill_info.get("has_update"):
            current = skill_info.get("current_version", "?")
            version = f"{current} → {version}"
            self.version_label.config(text=version, foreground="orange")
        else:
            self.version_label.config(text=version, foreground="black")
        
        # 描述 - 显示原文
        self._show_description(self._original_desc, show_translate_btn=True)
        
        # 元信息
        category = skill_info.get("category", "other")
        self.category_label.config(text=SKILL_CATEGORIES.get(category, category))
        self.author_label.config(text=skill_info.get("author", "未知"))
        
        downloads = skill_info.get("downloads", 0)
        if downloads > 1000:
            downloads_str = f"{downloads/1000:.1f}k"
        else:
            downloads_str = str(downloads)
        self.downloads_label.config(text=downloads_str)
        self.updated_label.config(text=skill_info.get("updated_at", "未知"))
        
        # 更新按钮状态
        self._update_buttons()
    
    def _update_buttons(self):
        """根据技能状态更新按钮显示"""
        if not self.skill:
            return
        
        installed = self.skill.get("installed", False)
        has_update = self.skill.get("has_update", False)
        
        if installed:
            self.install_btn.pack_forget()
            self.uninstall_btn.pack(side=tk.LEFT, padx=(0, 5))
            if has_update:
                self.update_btn.pack(side=tk.LEFT, padx=(0, 5))
            else:
                self.update_btn.pack_forget()
        else:
            self.install_btn.pack(side=tk.LEFT, padx=(0, 5))
            self.update_btn.pack_forget()
            self.uninstall_btn.pack_forget()
    
    def _on_install(self):
        if self.skill and self.on_install:
            self.on_install(self.skill)
    
    def _on_uninstall(self):
        if self.skill and self.on_uninstall:
            self.on_uninstall(self.skill)
    
    def _on_update(self):
        if self.skill and self.on_update:
            self.on_update(self.skill)
    
    def _show_description(self, text, show_translate_btn=True):
        """显示描述文本"""
        self.desc_text.config(state=tk.NORMAL)
        self.desc_text.delete("1.0", tk.END)
        self.desc_text.insert("1.0", text)
        self.desc_text.config(state=tk.DISABLED)
        
        # 控制翻译按钮显示
        if show_translate_btn and self._original_desc and len(self._original_desc) > 10:
            # 简单检测是否已经是中文
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in self._original_desc)
            if not has_chinese:
                self.translate_btn.pack(side=tk.RIGHT)
                self.translate_btn.config(text="中文", state=tk.NORMAL)
            else:
                self.translate_btn.pack_forget()
        else:
            self.translate_btn.pack_forget()
    
    def _on_translate(self):
        """翻译技能描述为中文"""
        if not self.skill:
            return
        
        # 如果已经有缓存的翻译结果，直接切换
        if self._translated_desc:
            self._is_translated = not self._is_translated
            if self._is_translated:
                self._show_description(self._translated_desc, show_translate_btn=True)
                self.translate_btn.config(text="原文")
            else:
                self._show_description(self._original_desc, show_translate_btn=True)
                self.translate_btn.config(text="中文")
            return
        
        # 开始翻译
        self.translate_btn.config(state=tk.DISABLED, text="翻译中...")
        
        def do_translate():
            try:
                text_to_translate = self._original_desc[:800]  # 限制长度
                
                # 使用简单的翻译映射表（内置常用技能描述）
                translation_map = {
                    # 常见关键词映射
                    "weather": "天气",
                    "github": "GitHub",
                    "discord": "Discord",
                    "telegram": "Telegram",
                    "gemini": "Gemini",
                    "skill": "技能",
                    "tool": "工具",
                    "agent": "智能体",
                    "cli": "命令行工具",
                    "api": "API",
                    "search": "搜索",
                    "install": "安装",
                    "create": "创建",
                    "manage": "管理",
                    "control": "控制",
                    "automation": "自动化",
                    "message": "消息",
                    "chat": "聊天",
                    "bot": "机器人",
                    "notification": "通知",
                    "reminder": "提醒",
                    "calendar": "日历",
                    "email": "邮件",
                    "file": "文件",
                    "folder": "文件夹",
                    "directory": "目录",
                    "path": "路径",
                    "config": "配置",
                    "setting": "设置",
                    "default": "默认",
                    "optional": "可选",
                    "required": "必需",
                    "enable": "启用",
                    "disable": "禁用",
                    "start": "启动",
                    "stop": "停止",
                    "run": "运行",
                    "execute": "执行",
                    "list": "列表",
                    "show": "显示",
                    "display": "展示",
                    "get": "获取",
                    "set": "设置",
                    "add": "添加",
                    "remove": "移除",
                    "delete": "删除",
                    "update": "更新",
                    "edit": "编辑",
                    "modify": "修改",
                    "generate": "生成",
                    "create": "创建",
                    "build": "构建",
                    "deploy": "部署",
                    "test": "测试",
                    "debug": "调试",
                    "log": "日志",
                    "error": "错误",
                    "warning": "警告",
                    "info": "信息",
                    "success": "成功",
                    "failed": "失败",
                    "pending": "待处理",
                    "processing": "处理中",
                    "completed": "已完成",
                    "cancelled": "已取消",
                    "active": "活跃",
                    "inactive": "非活跃",
                    "available": "可用",
                    "unavailable": "不可用",
                    "ready": "就绪",
                    "not ready": "未就绪",
                    "online": "在线",
                    "offline": "离线",
                    "connected": "已连接",
                    "disconnected": "已断开",
                    "sync": "同步",
                    "async": "异步",
                    "local": "本地",
                    "remote": "远程",
                    "server": "服务器",
                    "client": "客户端",
                    "host": "主机",
                    "port": "端口",
                    "url": "URL",
                    "uri": "URI",
                    "http": "HTTP",
                    "https": "HTTPS",
                    "web": "网页",
                    "browser": "浏览器",
                    "page": "页面",
                    "website": "网站",
                    "application": "应用",
                    "app": "应用",
                    "software": "软件",
                    "program": "程序",
                    "code": "代码",
                    "script": "脚本",
                    "function": "函数",
                    "method": "方法",
                    "class": "类",
                    "object": "对象",
                    "variable": "变量",
                    "constant": "常量",
                    "parameter": "参数",
                    "argument": "参数",
                    "return": "返回",
                    "value": "值",
                    "type": "类型",
                    "string": "字符串",
                    "number": "数字",
                    "integer": "整数",
                    "float": "浮点数",
                    "boolean": "布尔值",
                    "array": "数组",
                    "list": "列表",
                    "dict": "字典",
                    "map": "映射",
                    "json": "JSON",
                    "xml": "XML",
                    "yaml": "YAML",
                    "csv": "CSV",
                    "text": "文本",
                    "binary": "二进制",
                    "data": "数据",
                    "database": "数据库",
                    "query": "查询",
                    "insert": "插入",
                    "select": "选择",
                    "where": "条件",
                    "order": "排序",
                    "group": "分组",
                    "limit": "限制",
                    "offset": "偏移",
                    "join": "连接",
                    "table": "表",
                    "column": "列",
                    "row": "行",
                    "record": "记录",
                    "field": "字段",
                    "key": "键",
                    "primary key": "主键",
                    "foreign key": "外键",
                    "index": "索引",
                    "constraint": "约束",
                    "transaction": "事务",
                    "commit": "提交",
                    "rollback": "回滚",
                    "backup": "备份",
                    "restore": "恢复",
                    "import": "导入",
                    "export": "导出",
                    "upload": "上传",
                    "download": "下载",
                    "copy": "复制",
                    "paste": "粘贴",
                    "cut": "剪切",
                    "undo": "撤销",
                    "redo": "重做",
                    "find": "查找",
                    "replace": "替换",
                    "search": "搜索",
                    "filter": "筛选",
                    "sort": "排序",
                    "group": "分组",
                    "aggregate": "聚合",
                    "count": "计数",
                    "sum": "求和",
                    "average": "平均",
                    "min": "最小",
                    "max": "最大",
                    "first": "第一个",
                    "last": "最后一个",
                    "next": "下一个",
                    "previous": "上一个",
                    "current": "当前",
                    "new": "新建",
                    "old": "旧",
                    "existing": "现有",
                    "all": "全部",
                    "none": "无",
                    "any": "任意",
                    "some": "某些",
                    "many": "许多",
                    "few": "少量",
                    "several": "几个",
                    "multiple": "多个",
                    "single": "单个",
                    "double": "双精度",
                    "triple": "三精度",
                    "quadruple": "四精度",
                    "half": "一半",
                    "full": "完整",
                    "partial": "部分",
                    "complete": "完成",
                    "incomplete": "未完成",
                    "total": "总计",
                    "subtotal": "小计",
                    "grand total": "总计",
                    "sum": "总和",
                    "average": "平均值",
                    "mean": "均值",
                    "median": "中位数",
                    "mode": "众数",
                    "standard deviation": "标准差",
                    "variance": "方差",
                    "minimum": "最小值",
                    "maximum": "最大值",
                    "range": "范围",
                    "interval": "间隔",
                    "period": "周期",
                    "duration": "持续时间",
                    "frequency": "频率",
                    "rate": "速率",
                    "speed": "速度",
                    "velocity": "速度",
                    "acceleration": "加速度",
                    "distance": "距离",
                    "length": "长度",
                    "width": "宽度",
                    "height": "高度",
                    "depth": "深度",
                    "size": "大小",
                    "volume": "体积",
                    "area": "面积",
                    "weight": "重量",
                    "mass": "质量",
                    "density": "密度",
                    "pressure": "压力",
                    "temperature": "温度",
                    "humidity": "湿度",
                    "light": "光线",
                    "sound": "声音",
                    "color": "颜色",
                    "image": "图像",
                    "picture": "图片",
                    "photo": "照片",
                    "video": "视频",
                    "audio": "音频",
                    "music": "音乐",
                    "voice": "语音",
                    "speech": "语音",
                    "text": "文本",
                    "document": "文档",
                    "pdf": "PDF",
                    "word": "Word",
                    "excel": "Excel",
                    "powerpoint": "PowerPoint",
                    "presentation": "演示文稿",
                    "spreadsheet": "电子表格",
                    "chart": "图表",
                    "graph": "图形",
                    "diagram": "图表",
                    "flowchart": "流程图",
                    "mind map": "思维导图",
                    "timeline": "时间线",
                    "schedule": "时间表",
                    "plan": "计划",
                    "task": "任务",
                    "todo": "待办事项",
                    "checklist": "检查清单",
                    "template": "模板",
                    "form": "表单",
                    "survey": "调查",
                    "quiz": "测验",
                    "exam": "考试",
                    "test": "测试",
                    "assessment": "评估",
                    "evaluation": "评价",
                    "review": "评审",
                    "feedback": "反馈",
                    "comment": "评论",
                    "note": "笔记",
                    "annotation": "注释",
                    "highlight": "高亮",
                    "bookmark": "书签",
                    "tag": "标签",
                    "label": "标签",
                    "category": "分类",
                    "type": "类型",
                    "kind": "种类",
                    "sort": "种类",
                    "class": "类别",
                    "group": "组",
                    "set": "集合",
                    "collection": "集合",
                    "series": "系列",
                    "sequence": "序列",
                    "chain": "链",
                    "list": "列表",
                    "queue": "队列",
                    "stack": "栈",
                    "heap": "堆",
                    "tree": "树",
                    "graph": "图",
                    "network": "网络",
                    "web": "网络",
                    "grid": "网格",
                    "matrix": "矩阵",
                    "vector": "向量",
                    "tensor": "张量",
                    "scalar": "标量",
                    "point": "点",
                    "line": "线",
                    "curve": "曲线",
                    "surface": "表面",
                    "shape": "形状",
                    "form": "形式",
                    "structure": "结构",
                    "pattern": "模式",
                    "model": "模型",
                    "framework": "框架",
                    "architecture": "架构",
                    "design": "设计",
                    "layout": "布局",
                    "format": "格式",
                    "style": "样式",
                    "theme": "主题",
                    "skin": "皮肤",
                    "appearance": "外观",
                    "look": "外观",
                    "feel": "感觉",
                    "experience": "体验",
                    "interaction": "交互",
                    "interface": "界面",
                    "ui": "用户界面",
                    "user interface": "用户界面",
                    "gui": "图形用户界面",
                    "graphical user interface": "图形用户界面",
                    "cli": "命令行界面",
                    "command line interface": "命令行界面",
                    "api": "应用程序接口",
                    "application programming interface": "应用程序接口",
                    "sdk": "软件开发工具包",
                    "software development kit": "软件开发工具包",
                    "ide": "集成开发环境",
                    "integrated development environment": "集成开发环境",
                    "editor": "编辑器",
                    "viewer": "查看器",
                    "reader": "阅读器",
                    "player": "播放器",
                    "recorder": "录音机",
                    "camera": "相机",
                    "scanner": "扫描仪",
                    "printer": "打印机",
                    "monitor": "显示器",
                    "screen": "屏幕",
                    "display": "显示",
                    "projector": "投影仪",
                    "speaker": "扬声器",
                    "microphone": "麦克风",
                    "headphone": "耳机",
                    "earphone": "耳机",
                    "keyboard": "键盘",
                    "mouse": "鼠标",
                    "touchpad": "触摸板",
                    "trackpad": "触控板",
                    "joystick": "操纵杆",
                    "gamepad": "游戏手柄",
                    "controller": "控制器",
                    "remote": "遥控器",
                    "sensor": "传感器",
                    "detector": "检测器",
                    "meter": "测量仪",
                    "gauge": "仪表",
                    "scale": "秤",
                    "ruler": "尺子",
                    "compass": "指南针",
                    "gps": "全球定位系统",
                    "global positioning system": "全球定位系统",
                    "map": "地图",
                    "navigation": "导航",
                    "direction": "方向",
                    "route": "路线",
                    "path": "路径",
                    "way": "方式",
                    "method": "方法",
                    "approach": "方法",
                    "technique": "技术",
                    "technology": "技术",
                    "technique": "技巧",
                    "skill": "技能",
                    "ability": "能力",
                    "capability": "能力",
                    "capacity": "容量",
                    "power": "功率",
                    "energy": "能量",
                    "force": "力",
                    "strength": "强度",
                    "intensity": "强度",
                    "magnitude": "量级",
                    "level": "级别",
                    "degree": "程度",
                    "grade": "等级",
                    "rank": "排名",
                    "rating": "评分",
                    "score": "分数",
                    "point": "分数",
                    "mark": "标记",
                    "grade": "成绩",
                    "result": "结果",
                    "outcome": "结果",
                    "output": "输出",
                    "input": "输入",
                    "source": "来源",
                    "destination": "目标",
                    "target": "目标",
                    "goal": "目标",
                    "objective": "目标",
                    "purpose": "目的",
                    "aim": "目的",
                    "intention": "意图",
                    "plan": "计划",
                    "strategy": "策略",
                    "tactic": "战术",
                    "policy": "政策",
                    "rule": "规则",
                    "regulation": "规定",
                    "law": "法律",
                    "principle": "原则",
                    "standard": "标准",
                    "norm": "规范",
                    "criterion": "标准",
                    "benchmark": "基准",
                    "reference": "参考",
                    "example": "示例",
                    "sample": "样本",
                    "instance": "实例",
                    "case": "案例",
                    "scenario": "场景",
                    "situation": "情况",
                    "condition": "条件",
                    "state": "状态",
                    "status": "状态",
                    "mode": "模式",
                    "phase": "阶段",
                    "stage": "阶段",
                    "step": "步骤",
                    "process": "过程",
                    "procedure": "程序",
                    "operation": "操作",
                    "action": "动作",
                    "activity": "活动",
                    "event": "事件",
                    "incident": "事件",
                    "occurrence": "发生",
                    "happening": "发生",
                    "phenomenon": "现象",
                    "fact": "事实",
                    "truth": "真相",
                    "reality": "现实",
                    "actuality": "实际",
                    "existence": "存在",
                    "being": "存在",
                    "entity": "实体",
                    "object": "对象",
                    "thing": "事物",
                    "item": "项目",
                    "element": "元素",
                    "component": "组件",
                    "part": "部分",
                    "piece": "片段",
                    "section": "章节",
                    "segment": "段",
                    "portion": "部分",
                    "share": "份额",
                    "division": "部门",
                    "department": "部门",
                    "unit": "单元",
                    "module": "模块",
                    "block": "块",
                    "chunk": "块",
                    "bit": "位",
                    "byte": "字节",
                    "word": "字",
                    "character": "字符",
                    "symbol": "符号",
                    "sign": "标志",
                    "mark": "标记",
                    "token": "令牌",
                    "ticket": "票证",
                    "voucher": "凭证",
                    "coupon": "优惠券",
                    "certificate": "证书",
                    "license": "许可证",
                    "permit": "许可",
                    "authorization": "授权",
                    "permission": "权限",
                    "access": "访问",
                    "entry": "入口",
                    "exit": "出口",
                    "entrance": "入口",
                    "gateway": "网关",
                    "portal": "门户",
                    "door": "门",
                    "window": "窗口",
                    "opening": "开口",
                    "hole": "洞",
                    "gap": "间隙",
                    "space": "空间",
                    "room": "房间",
                    "area": "区域",
                    "zone": "区域",
                    "region": "地区",
                    "district": "区域",
                    "territory": "领土",
                    "land": "土地",
                    "ground": "地面",
                    "floor": "地板",
                    "ceiling": "天花板",
                    "roof": "屋顶",
                    "wall": "墙壁",
                    "door": "门",
                    "window": "窗户",
                    "gate": "大门",
                    "fence": "围栏",
                    "barrier": "障碍",
                    "obstacle": "障碍",
                    "hindrance": "阻碍",
                    "impediment": "阻碍",
                    "block": "块",
                    "stop": "停止",
                    "end": "结束",
                    "finish": "完成",
                    "complete": "完成",
                    "terminate": "终止",
                    "close": "关闭",
                    "shut": "关闭",
                    "open": "打开",
                    "start": "开始",
                    "begin": "开始",
                    "initiate": "启动",
                    "launch": "启动",
                    "boot": "启动",
                    "load": "加载",
                    "unload": "卸载",
                    "install": "安装",
                    "setup": "设置",
                    "configure": "配置",
                    "initialize": "初始化",
                    "prepare": "准备",
                    "ready": "就绪",
                    "available": "可用",
                    "accessible": "可访问",
                    "reachable": "可达",
                    "obtainable": "可获得",
                    "achievable": "可实现",
                    "possible": "可能",
                    "feasible": "可行",
                    "viable": "可行",
                    "workable": "可行",
                    "practical": "实用",
                    "useful": "有用",
                    "helpful": "有帮助",
                    "beneficial": "有益",
                    "advantageous": "有利",
                    "profitable": "有利可图",
                    "valuable": "有价值",
                    "worthwhile": "值得",
                    "important": "重要",
                    "significant": "重要",
                    "critical": "关键",
                    "crucial": "关键",
                    "vital": "至关重要",
                    "essential": "必需",
                    "necessary": "必要",
                    "required": "必需",
                    "needed": "需要",
                    "wanted": "想要",
                    "desired": "期望",
                    "preferred": "首选",
                    "favorite": "最爱",
                    "popular": "流行",
                    "trending": "趋势",
                    "fashionable": "时尚",
                    "stylish": "时髦",
                    "modern": "现代",
                    "contemporary": "当代",
                    "current": "当前",
                    "present": "现在",
                    "now": "现在",
                    "today": "今天",
                    "yesterday": "昨天",
                    "tomorrow": "明天",
                    "future": "未来",
                    "past": "过去",
                    "history": "历史",
                    "background": "背景",
                    "context": "上下文",
                    "environment": "环境",
                    "surroundings": "周围环境",
                    "setting": "设置",
                    "scene": "场景",
                    "view": "视图",
                    "perspective": "视角",
                    "angle": "角度",
                    "aspect": "方面",
                    "facet": "方面",
                    "side": "侧面",
                    "face": "面部",
                    "surface": "表面",
                    "exterior": "外部",
                    "interior": "内部",
                    "inside": "内部",
                    "outside": "外部",
                    "inner": "内部",
                    "outer": "外部",
                    "external": "外部",
                    "internal": "内部",
                    "domestic": "国内",
                    "foreign": "国外",
                    "international": "国际",
                    "global": "全球",
                    "worldwide": "全球",
                    "universal": "通用",
                    "general": "一般",
                    "common": "常见",
                    "usual": "通常",
                    "normal": "正常",
                    "regular": "常规",
                    "standard": "标准",
                    "typical": "典型",
                    "average": "平均",
                    "ordinary": "普通",
                    "plain": "简单",
                    "simple": "简单",
                    "easy": "容易",
                    "difficult": "困难",
                    "hard": "困难",
                    "complex": "复杂",
                    "complicated": "复杂",
                    "intricate": "错综复杂",
                    "sophisticated": "复杂",
                    "advanced": "高级",
                    "progressive": "渐进",
                    "developing": "发展中",
                    "evolving": "进化",
                    "growing": "成长",
                    "expanding": "扩展",
                    "extending": "延伸",
                    "spreading": "传播",
                    "distributing": "分发",
                    "sharing": "分享",
                    "exchanging": "交换",
                    "trading": "交易",
                    "buying": "购买",
                    "selling": "销售",
                    "purchasing": "采购",
                    "acquiring": "获取",
                    "obtaining": "获得",
                    "getting": "得到",
                    "receiving": "接收",
                    "accepting": "接受",
                    "taking": "拿取",
                    "grabbing": "抓取",
                    "catching": "捕捉",
                    "capturing": "捕获",
                    "seizing": "抓住",
                    "holding": "持有",
                    "keeping": "保持",
                    "retaining": "保留",
                    "maintaining": "维护",
                    "preserving": "保存",
                    "conserving": "保护",
                    "protecting": "保护",
                    "guarding": "守卫",
                    "defending": "防御",
                    "shielding": "屏蔽",
                    "covering": "覆盖",
                    "hiding": "隐藏",
                    "concealing": "隐藏",
                    "masking": "掩码",
                    "disguising": "伪装",
                    "pretending": "假装",
                    "acting": "行动",
                    "performing": "执行",
                    "doing": "做",
                    "making": "制作",
                    "creating": "创建",
                    "building": "构建",
                    "constructing": "构建",
                    "assembling": "组装",
                    "fabricating": "制造",
                    "manufacturing": "制造",
                    "producing": "生产",
                    "generating": "生成",
                    "forming": "形成",
                    "shaping": "塑造",
                    "molding": "塑造",
                    "casting": "铸造",
                    "forging": "锻造",
                    "stamping": "冲压",
                    "pressing": "按压",
                    "pushing": "推动",
                    "pulling": "拉动",
                    "dragging": "拖动",
                    "drawing": "绘制",
                    "painting": "绘画",
                    "sketching": "素描",
                    "designing": "设计",
                    "planning": "规划",
                    "organizing": "组织",
                    "arranging": "安排",
                    "ordering": "排序",
                    "sequencing": "排序",
                    "aligning": "对齐",
                    "positioning": "定位",
                    "placing": "放置",
                    "putting": "放置",
                    "setting": "设置",
                    "adjusting": "调整",
                    "calibrating": "校准",
                    "tuning": "调优",
                    "optimizing": "优化",
                    "improving": "改进",
                    "enhancing": "增强",
                    "upgrading": "升级",
                    "updating": "更新",
                    "refreshing": "刷新",
                    "reloading": "重新加载",
                    "restarting": "重新启动",
                    "rebooting": "重启",
                    "resetting": "重置",
                    "restoring": "恢复",
                    "recovering": "恢复",
                    "repairing": "修复",
                    "fixing": "修复",
                    "correcting": "纠正",
                    "rectifying": "纠正",
                    "resolving": "解决",
                    "solving": "解决",
                    "settling": "解决",
                    "deciding": "决定",
                    "determining": "确定",
                    "identifying": "识别",
                    "recognizing": "识别",
                    "detecting": "检测",
                    "sensing": "感知",
                    "feeling": "感觉",
                    "perceiving": "感知",
                    "observing": "观察",
                    "watching": "观看",
                    "looking": "查看",
                    "seeing": "看见",
                    "viewing": "查看",
                    "inspecting": "检查",
                    "examining": "检查",
                    "checking": "检查",
                    "testing": "测试",
                    "verifying": "验证",
                    "validating": "验证",
                    "confirming": "确认",
                    "approving": "批准",
                    "authorizing": "授权",
                    "permitting": "允许",
                    "allowing": "允许",
                    "letting": "让",
                    "enabling": "启用",
                    "activating": "激活",
                    "turning on": "打开",
                    "switching on": "开启",
                    "powering on": "上电",
                    "booting up": "启动",
                    "starting up": "启动",
                    "warming up": "预热",
                    "cooling down": "冷却",
                    "shutting down": "关闭",
                    "turning off": "关闭",
                    "switching off": "关闭",
                    "powering off": "断电",
                    "sleeping": "睡眠",
                    "hibernating": "休眠",
                    "suspending": "挂起",
                    "pausing": "暂停",
                    "resuming": "恢复",
                    "continuing": "继续",
                    "proceeding": "继续",
                    "advancing": "前进",
                    "moving forward": "前进",
                    "going ahead": "前进",
                    "progressing": "进展",
                    "developing": "发展",
                    "evolving": "演变",
                    "changing": "改变",
                    "transforming": "转换",
                    "converting": "转换",
                    "translating": "翻译",
                    "interpreting": "解释",
                    "explaining": "解释",
                    "describing": "描述",
                    "depicting": "描绘",
                    "portraying": "描绘",
                    "representing": "代表",
                    "symbolizing": "象征",
                    "meaning": "意思",
                    "signifying": "表示",
                    "indicating": "指示",
                    "showing": "显示",
                    "demonstrating": "演示",
                    "proving": "证明",
                    "evidencing": "证明",
                    "witnessing": "见证",
                    "testifying": "作证",
                    "attesting": "证明",
                    "certifying": "认证",
                    "guaranteeing": "保证",
                    "ensuring": "确保",
                    "assuring": "保证",
                    "securing": "保护",
                    "safeguarding": "保护",
                    "protecting": "保护",
                    "defending": "防御",
                    "guarding": "守卫",
                    "watching": "监视",
                    "monitoring": "监控",
                    "supervising": "监督",
                    "controlling": "控制",
                    "managing": "管理",
                    "handling": "处理",
                    "dealing": "处理",
                    "coping": "应对",
                    "addressing": "解决",
                    "treating": "处理",
                    "processing": "处理",
                    "analyzing": "分析",
                    "examining": "检查",
                    "studying": "研究",
                    "investigating": "调查",
                    "researching": "研究",
                    "exploring": "探索",
                    "discovering": "发现",
                    "finding": "找到",
                    "locating": "定位",
                    "positioning": "定位",
                    "placing": "放置",
                    "installing": "安装",
                    "deploying": "部署",
                    "implementing": "实现",
                    "executing": "执行",
                    "running": "运行",
                    "operating": "操作",
                    "working": "工作",
                    "functioning": "功能",
                    "performing": "执行",
                    "serving": "服务",
                    "providing": "提供",
                    "supplying": "供应",
                    "delivering": "交付",
                    "distributing": "分发",
                    "sharing": "分享",
                    "communicating": "交流",
                }
                
                # 简单的规则翻译
                translated = self._simple_translate(text_to_translate, translation_map)
                
                self._translated_desc = translated
                self._is_translated = True
                
                # 更新 UI
                self.after(0, lambda: self._show_description(translated, show_translate_btn=True))
                self.after(0, lambda: self.translate_btn.config(text="原文", state=tk.NORMAL))
            except Exception as e:
                self.after(0, lambda: self._show_description(f"[翻译错误: {e}]\n\n{self._original_desc}", show_translate_btn=True))
                self.after(0, lambda: self.translate_btn.config(text="重试", state=tk.NORMAL))
        
        threading.Thread(target=do_translate, daemon=True).start()
    
    def _simple_translate(self, text, translation_map):
        """简单的翻译函数 - 基于规则替换"""
        import re
        
        # 先进行整词匹配替换
        words = re.findall(r'\b\w+\b', text.lower())
        translated_words = []
        
        for word in words:
            if word in translation_map:
                translated_words.append(translation_map[word])
            else:
                translated_words.append(word)
        
        # 重建文本（保持原始格式）
        result = text
        for eng, chn in translation_map.items():
            # 使用正则表达式进行整词替换，忽略大小写
            pattern = r'\b' + re.escape(eng) + r'\b'
            result = re.sub(pattern, chn, result, flags=re.IGNORECASE)
        
        # 添加一些通用翻译规则
        result = result.replace("Use when", "使用场景：")
        result = result.replace("Use for", "用于")
        result = result.replace("Use to", "用于")
        result = result.replace("This skill", "此技能")
        result = result.replace("The skill", "该技能")
        result = result.replace("allows you to", "允许您")
        result = result.replace("enables you to", "使您能够")
        result = result.replace("helps you to", "帮助您")
        result = result.replace("provides", "提供")
        result = result.replace("supports", "支持")
        result = result.replace("via", "通过")
        result = result.replace("using", "使用")
        result = result.replace("with", "使用")
        result = result.replace("for", "用于")
        result = result.replace("and", "和")
        result = result.replace("or", "或")
        result = result.replace("not", "不")
        result = result.replace("from", "从")
        result = result.replace("to", "到")
        result = result.replace("in", "在")
        result = result.replace("on", "在")
        result = result.replace("at", "在")
        result = result.replace("by", "通过")
        result = result.replace("as", "作为")
        result = result.replace("of", "的")
        result = result.replace("the", "")
        result = result.replace("a", "")
        result = result.replace("an", "")
        
        # 清理多余空格
        result = re.sub(r'\s+', ' ', result).strip()
        
        return result


class SkillsPanelNew(ttk.Frame):
    """重新设计的技能管理面板"""
    
    def __init__(self, parent, app=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.all_skills = []  # 所有技能数据
        self.filtered_skills = []  # 筛选后的技能
        self.selected_skill = None
        
        self._build_ui()
        self._refresh()
    
    def _build_ui(self):
        """构建界面"""
        # 顶部标题
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(header, text="技能管理", font=("", 16, "bold")).pack(side=tk.LEFT)
        
        # 主体：左右分栏
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 左侧：技能列表
        left_frame = ttk.Frame(main_frame, width=450)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_frame.pack_propagate(False)
        
        # 搜索和筛选栏
        filter_frame = ttk.Frame(left_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 搜索框
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_search)
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.insert(0, "搜索技能...")
        search_entry.bind("<FocusIn>", lambda e: search_entry.delete(0, tk.END) if search_entry.get() == "搜索技能..." else None)
        search_entry.bind("<FocusOut>", lambda e: search_entry.insert(0, "搜索技能...") if not search_entry.get() else None)
        
        ttk.Button(filter_frame, text="刷新", command=self._refresh, width=8).pack(side=tk.LEFT, padx=(5, 0))
        
        # 分类标签
        category_frame = ttk.Frame(left_frame)
        category_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.category_var = tk.StringVar(value="all")
        for key, label in SKILL_CATEGORIES.items():
            rb = ttk.Radiobutton(category_frame, text=label, variable=self.category_var, 
                                value=key, command=self._on_category_change)
            rb.pack(side=tk.LEFT, padx=(0, 10))
        
        # 创建带分割的列表区
        list_container = ttk.Frame(left_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        # 技能总览区（已装 / 未装 统计）
        self.installed_frame = ttk.LabelFrame(list_container, text="技能总览", padding=5)
        self.installed_frame.pack(fill=tk.X, pady=(0, 10))
        
        installed_container = ttk.Frame(self.installed_frame)
        installed_container.pack(fill=tk.BOTH, expand=True)
        
        self.installed_canvas = tk.Canvas(installed_container, height=150)
        installed_scrollbar = ttk.Scrollbar(
            installed_container, orient=tk.VERTICAL, command=self.installed_canvas.yview
        )
        self.installed_canvas.configure(yscrollcommand=installed_scrollbar.set)
        self.installed_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        installed_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.installed_inner = ttk.Frame(self.installed_canvas)
        self.installed_canvas.create_window(
            (0, 0), window=self.installed_inner, anchor=tk.NW, width=430
        )
        self.installed_inner.bind(
            "<Configure>",
            lambda e: self.installed_canvas.configure(
                scrollregion=self.installed_canvas.bbox("all")
            ),
        )
        
        # 可安装技能区
        self.available_frame = ttk.LabelFrame(list_container, text="发现更多技能", padding=5)
        self.available_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建可滚动区域
        self.canvas = tk.Canvas(self.available_frame)
        scrollbar = ttk.Scrollbar(self.available_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.skills_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.skills_frame, anchor=tk.NW, width=430)
        
        self.skills_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        # 右侧：技能详情
        right_frame = ttk.LabelFrame(main_frame, text="技能详情", width=350)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        right_frame.pack_propagate(False)
        
        self.detail_panel = SkillDetailPanel(
            right_frame,
            on_install=self._install_skill,
            on_uninstall=self._uninstall_skill,
            on_update=self._update_skill
        )
        self.detail_panel.pack(fill=tk.BOTH, expand=True)
        
        # 底部日志区
        log_frame = ttk.LabelFrame(self, text="操作日志", padding=5)
        log_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=5, font=("Consolas", 9))
        self.log_text.pack(fill=tk.X)

    def _widget_alive(self, widget) -> bool:
        """判断控件是否仍可用（避免异步回调操作已销毁控件）"""
        if widget is None:
            return False
        try:
            return bool(widget.winfo_exists())
        except tk.TclError:
            return False
    
    def _log(self, msg):
        """添加日志"""
        if not self._widget_alive(getattr(self, "log_text", None)):
            return
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        try:
            self.log_text.insert(tk.END, f"[{timestamp}] {msg}\n")
            self.log_text.see(tk.END)
        except tk.TclError:
            # 面板关闭后的异步回调可直接忽略
            return
    
    def _on_search(self, *args):
        """搜索过滤 - 添加防抖"""
        # 取消之前的延迟调用
        if hasattr(self, '_search_after_id'):
            self.after_cancel(self._search_after_id)
        # 延迟300ms执行搜索
        self._search_after_id = self.after(300, self._filter_skills)
    
    def _on_category_change(self):
        """分类切换"""
        self._filter_skills()
    
    def _filter_skills(self):
        """根据搜索和分类筛选技能"""
        # 可能在 __init__ 早期（分类变量尚未创建时）就被搜索回调触发，这里做防御判断
        if not hasattr(self, "category_var"):
            return

        search_term = self.search_var.get().lower()
        if search_term == "搜索技能...":
            search_term = ""
        
        category = self.category_var.get()
        
        # 使用列表推导式提高性能
        self.filtered_skills = [
            skill for skill in self.all_skills
            if (category == "all" or skill.get("category") == category)
            and (not search_term or 
                 search_term in skill.get("name", "").lower() or
                 search_term in skill.get("id", "").lower() or
                 search_term in skill.get("description", "").lower())
        ]
        
        self._update_skill_list()
    
    def _update_skill_list(self):
        """更新技能列表显示 - 使用缓存优化性能

        约定：
        - 「技能总览」列表展示当前筛选视图中的所有技能（已装 + 未装），
          已安装技能只是在卡片上打勾标记。
        - 「发现更多技能」模块保留为独立来源（如 Hub），不再混入 CLI 的 68 个技能。
        """
        # 面板销毁后，异步回调可能仍在触发，直接跳过 UI 更新
        if not self._widget_alive(getattr(self, "installed_frame", None)):
            return
        if not self._widget_alive(getattr(self, "available_frame", None)):
            return

        # 当前筛选视图下需要展示在「技能总览」中的技能
        overview_skills = list(self.filtered_skills)

        # 统计全局安装/未安装数量，用于总览标题
        total_installed = sum(1 for s in self.all_skills if s.get("installed"))
        total_available = max(len(self.all_skills) - total_installed, 0)

        # 更新标签文本（总览统计）
        self.installed_frame.config(
            text=f"技能总览（已装{total_installed}个/未装{total_available}个）"
        )

        # 「发现更多技能」目前不绑定 CLI 列表，这里仅重置为 0，实际数据由后续 Hub 集成时再填充
        self.available_frame.config(text="发现更多技能 (0)")

        # 使用延迟更新避免界面卡顿
        # 顶部总览：展示所有技能（已装/未装混排，由 SkillCard 自行渲染勾选标记）
        self._update_list_async(self.installed_inner, overview_skills, self.installed_canvas)
        # 底部发现更多：暂时清空
        self._update_list_async(self.skills_frame, [], self.canvas)
    
    def _update_list_async(self, parent, skills, canvas_widget):
        """异步更新列表，分批渲染避免卡顿"""
        if not self._widget_alive(parent) or not self._widget_alive(canvas_widget):
            return

        # 清空现有列表
        for widget in parent.winfo_children():
            widget.destroy()
        
        if not skills:
            tk.Label(parent, text="暂无技能", bg="white", fg="gray").pack(pady=20)
            parent.update_idletasks()
            canvas_widget.configure(scrollregion=canvas_widget.bbox("all"))
            return
        
        # 创建卡片并分批渲染
        def create_cards_batch(start_idx=0, batch_size=10):
            if not self._widget_alive(parent) or not self._widget_alive(canvas_widget):
                return
            end_idx = min(start_idx + batch_size, len(skills))
            
            for i in range(start_idx, end_idx):
                skill = skills[i]
                card = SkillCard(parent, skill, on_select=self._on_skill_select)
                card.pack(fill=tk.X, pady=1, padx=2)
            
            try:
                parent.update_idletasks()
                canvas_widget.configure(scrollregion=canvas_widget.bbox("all"))
            except tk.TclError:
                return
            
            # 如果还有剩余，继续下一批
            if end_idx < len(skills):
                self.after(10, lambda: create_cards_batch(end_idx, batch_size))
        
        # 开始第一批渲染
        create_cards_batch(0, 15)
    
    def _on_skill_select(self, skill):
        """选择技能 - 优化选中状态显示"""
        self.selected_skill = skill
        
        # 更新所有卡片的选中状态
        for container in [self.installed_inner, self.skills_frame]:
            for widget in container.winfo_children():
                if isinstance(widget, SkillCard):
                    widget.set_selected(widget.skill.get("id") == skill.get("id"))
        
        # 更新详情面板
        self.detail_panel.show_skill(skill)
    
    def _get_openclaw_cmd(self):
        """获取 openclaw 命令路径"""
        import shutil
        
        # 1. 从系统 PATH 中找
        openclaw_path = shutil.which("openclaw")
        if openclaw_path:
            return openclaw_path
        
        # 2. 尝试 npx
        if shutil.which("npx"):
            return "npx openclaw"
        
        # 3. 尝试从 npm 全局安装目录找
        npm_prefix = self._get_npm_prefix()
        if npm_prefix:
            npm_openclaw = os.path.join(npm_prefix, "openclaw.cmd")
            if os.path.isfile(npm_openclaw):
                return npm_openclaw
        
        # 4. 尝试常见路径
        possible_paths = [
            os.path.expanduser("~/AppData/Roaming/npm/openclaw.cmd"),
            os.path.expanduser("~/AppData/Local/npm/openclaw.cmd"),
            "C:/Users/" + os.environ.get("USERNAME", "") + "/AppData/Roaming/npm/openclaw.cmd",
        ]
        for path in possible_paths:
            if os.path.isfile(path):
                return path
        
        return None
    
    def _get_npm_prefix(self):
        """获取 npm 全局安装前缀"""
        try:
            result = subprocess.run(
                ["npm", "config", "get", "prefix"],
                capture_output=True,
                text=True,
                timeout=5,
                encoding="utf-8",
                errors="ignore"
            )
            if result.returncode == 0:
                prefix = result.stdout.strip()
                if prefix:
                    return prefix
        except:
            pass
        return None
    
    def _install_skill(self, skill):
        """安装技能。来源为 Hub 时：请求下载接口 → 下载到本地 → 从本地文件安装；否则走 openclaw CLI install."""
        skill_id = skill.get("id")
        self._log(f"开始安装技能: {skill_id}")
        
        if skill.get("source") == "hub":
            self._install_skill_from_hub(skill_id)
            return
        
        openclaw_cmd = self._get_openclaw_cmd()
        if not openclaw_cmd:
            self._log("✗ 错误: 未找到 openclaw 命令")
            return
        
        def worker():
            try:
                proc = subprocess.run(
                    f"{openclaw_cmd} skills install {skill_id}",
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore"
                )
                if proc.returncode == 0:
                    self.after(0, lambda: self._log(f"✓ 技能 {skill_id} 安装成功"))
                    self.after(0, self._refresh)
                else:
                    error = proc.stderr or "未知错误"
                    self.after(0, lambda: self._log(f"✗ 安装失败: {error}"))
            except Exception as e:
                self.after(0, lambda: self._log(f"✗ 安装异常: {e}"))
        
        threading.Thread(target=worker, daemon=True).start()
    
    def _install_skill_from_hub(self, skill_id: str):
        """从 Hub 下载技能包并用本地安装器安装（请求 Hub 下载接口 + 从本地文件安装）"""
        if not hub_skills_api or not hub_skills_api.is_hub_configured():
            self.after(0, lambda: self._log("✗ 未配置 Hub 地址，无法安装"))
            return
        token = hub_auth.get_token() if hub_auth else None
        
        def worker():
            try:
                self.after(0, lambda: self._log("正在获取下载链接..."))
                url, err = hub_skills_api.get_download_url(skill_id, token)
                if err:
                    self.after(0, lambda: self._log(f"✗ 获取下载链接失败: {err}"))
                    return
                self.after(0, lambda: self._log("正在下载技能包..."))
                path, err = hub_skills_api.download_to_temp(url)
                if err:
                    self.after(0, lambda: self._log(f"✗ 下载失败: {err}"))
                    return
                import shutil
                # 重命名为 {skill_id}.zip，解压后目录名为 skill_id，便于 SkillManager 识别
                target_zip = os.path.join(os.path.dirname(path), f"{skill_id}.zip")
                try:
                    shutil.move(path, target_zip)
                except OSError:
                    shutil.copy2(path, target_zip)
                    try:
                        os.remove(path)
                    except OSError:
                        pass
                openclaw_dir = os.path.expanduser("~/.openclaw")
                skills_dir = os.path.join(openclaw_dir, "workspace", "skills")
                os.makedirs(skills_dir, exist_ok=True)
                try:
                    from skills.error_handler import OfflineInstaller
                    installer = OfflineInstaller(skills_dir=skills_dir)
                    result = installer.install_from_file(target_zip)
                finally:
                    try:
                        if os.path.isfile(target_zip):
                            os.remove(target_zip)
                    except OSError:
                        pass
                if result.get("success"):
                    self.after(0, lambda: self._log(f"✓ 技能 {skill_id} 安装成功"))
                    self.after(0, self._refresh)
                else:
                    self.after(0, lambda: self._log(f"✗ 安装失败: {result.get('error', '未知错误')}"))
            except Exception as e:
                self.after(0, lambda: self._log(f"✗ 安装异常: {e}"))
        
        threading.Thread(target=worker, daemon=True).start()
    
    def _uninstall_skill(self, skill):
        """卸载技能"""
        skill_id = skill.get("id")
        if not messagebox.askyesno("确认卸载", f"确定要卸载技能 {skill_id} 吗？"):
            return

        self._log(f"开始卸载技能: {skill_id}")

        # 当前版本 openclaw CLI 的 `skills` 命令只支持 list/info/check，
        # 并不存在 `skills uninstall` 子命令，直接调用会出现
        # “too many arguments for 'skills'” 之类错误。
        # 为避免误导，这里直接给出明确提示并中止卸载动作。
        self._log(
            "✗ 卸载失败: 当前 OpenClaw 版本不支持 `openclaw skills uninstall` 命令。\n"
            "  请暂时通过以下方式手动管理技能：\n"
            "  - 对 workspace 技能：删除 ~/.openclaw/workspace/skills/<skill_id> 目录；\n"
            "  - 对 CLI 自带技能：后续待官方提供卸载/禁用命令后再集成一键卸载。"
        )
    
    def _update_skill(self, skill):
        """更新技能"""
        skill_id = skill.get("id")
        self._log(f"开始更新技能: {skill_id}")
        
        openclaw_cmd = self._get_openclaw_cmd()
        if not openclaw_cmd:
            self._log("✗ 错误: 未找到 openclaw 命令")
            return
        
        def worker():
            try:
                proc = subprocess.run(
                    f"{openclaw_cmd} skills update {skill_id}",
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore"
                )
                if proc.returncode == 0:
                    self.after(0, lambda: self._log(f"✓ 技能 {skill_id} 更新成功"))
                    self.after(0, self._refresh)
                else:
                    # 尝试重新安装
                    proc = subprocess.run(
                        f"{openclaw_cmd} skills install {skill_id}",
                        shell=True,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="ignore"
                    )
                    if proc.returncode == 0:
                        self.after(0, lambda: self._log(f"✓ 技能 {skill_id} 更新成功"))
                        self.after(0, self._refresh)
                    else:
                        error = proc.stderr or "未知错误"
                        self.after(0, lambda: self._log(f"✗ 更新失败: {error}"))
            except Exception as e:
                self.after(0, lambda: self._log(f"✗ 更新异常: {e}"))
        
        threading.Thread(target=worker, daemon=True).start()
    
    def _refresh(self):
        """
        刷新技能列表。

        优先使用 `openclaw skills list --json` 作为单一数据源，直接获得:
        - 全部技能列表
        - 哪些已安装（installed 标记）

        若 CLI 不可用或调用失败，则回退到 SkillManager + Hub 的组合逻辑。
        """
        self._log("正在刷新技能列表...")

        def worker():
            # 优先尝试从 openclaw CLI 获取技能列表
            openclaw_cmd = self._get_openclaw_cmd()
            if openclaw_cmd:
                try:
                    proc = subprocess.run(
                        f"{openclaw_cmd} skills list --json",
                        shell=True,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="ignore",
                        timeout=30,
                    )
                    if proc.returncode == 0 and (proc.stdout or "").strip():
                        import json as _json

                        raw = (proc.stdout or "").strip()
                        try:
                            data = _json.loads(raw)
                        except Exception as e:
                            self.after(
                                0,
                                lambda: self._log(
                                    f"[警告] 解析 openclaw skills list JSON 失败，将回退到本地视图: {e}"
                                ),
                            )
                        else:
                            if isinstance(data, dict) and "skills" in data:
                                items = data.get("skills") or []
                            elif isinstance(data, list):
                                items = data
                            else:
                                items = []

                            skills = []
                            for s in items:
                                if not isinstance(s, dict):
                                    continue
                                sid = s.get("id") or s.get("name")
                                if not sid:
                                    continue

                                # 根据 missing 字段判断是否“就绪/已装”：
                                # openclaw skills list 的 installed 统计，即 missing 下 bins/anyBins/env/config/os 全为空。
                                missing = s.get("missing") or {}
                                miss_bins = missing.get("bins") or []
                                miss_any = missing.get("anyBins") or []
                                miss_env = missing.get("env") or []
                                miss_cfg = missing.get("config") or []
                                miss_os = missing.get("os") or []
                                installed = (
                                    not miss_bins
                                    and not miss_any
                                    and not miss_env
                                    and not miss_cfg
                                    and not miss_os
                                )

                                skill = {
                                    "id": sid,
                                    "name": s.get("name", sid),
                                    "description": s.get("description")
                                    or s.get("summary")
                                    or "",
                                    "version": s.get("version")
                                    or s.get("installedVersion")
                                    or "?",
                                    "icon": s.get("emoji") or "📦",
                                    "category": s.get("category") or "other",
                                    "installed": installed,
                                    "source": s.get("source", "cli"),
                                }
                                skills.append(skill)

                            self.all_skills = skills
                            installed_count = sum(
                                1 for sk in skills if sk.get("installed")
                            )
                            available_count = max(len(skills) - installed_count, 0)

                            self.after(
                                0,
                                lambda: self._log(
                                    f"✓ 从 openclaw CLI 加载技能完成：总计 {len(skills)} 个，"
                                    f"已装 {installed_count} 个，未装 {available_count} 个"
                                ),
                            )
                            self.after(0, self._filter_skills)
                            return
                    else:
                        self.after(
                            0,
                            lambda: self._log(
                                "[警告] 调用 openclaw skills list 失败，将回退到本地视图。"
                            ),
                        )
                except Exception as e:
                    self.after(
                        0,
                        lambda: self._log(
                            f"[警告] 调用 openclaw skills list 异常，将回退到本地视图: {e}"
                        ),
                    )

            # 回退逻辑：使用 SkillManager + Hub
            try:
                manager = SkillManager()
                manager_skills = manager.get_skills(force_refresh=True) or []
                installed_list = [s for s in manager_skills if s.get("installed")]
                installed_ids = {s["id"] for s in installed_list}

                hub_skills = []
                if hub_skills_api and hub_skills_api.is_hub_configured():
                    hub_data, _ = hub_skills_api.get_skills(page=1, size=100)
                    for s in hub_data:
                        s["installed"] = s["id"] in installed_ids
                        hub_skills.append(s)
                else:
                    self.after(
                        0,
                        lambda: self._log(
                            "[提示] 未配置 Hub 地址，发现更多技能为空。可设置 BUTLERCLAW_HUB_URL 或 openclaw.json 中 hubBaseUrl"
                        ),
                    )

                self.all_skills = installed_list + hub_skills

                installed_count = len(
                    [s for s in self.all_skills if s.get("installed")]
                )
                available_count = max(len(self.all_skills) - installed_count, 0)

                self.after(
                    0,
                    lambda: self._log(
                        f"✓ 已加载技能视图：总计 {len(self.all_skills)} 个，"
                        f"已装 {installed_count} 个，未装 {available_count} 个"
                    ),
                )
                self.after(0, self._filter_skills)
            except Exception as e:
                self.after(
                    0, lambda: self._log(f"[错误] 获取技能列表失败: {e}")
                )
                self.all_skills = []
                self.after(0, self._filter_skills)

        threading.Thread(target=worker, daemon=True).start()


# 测试运行
if __name__ == "__main__":
    root = tk.Tk()
    root.title("OpenClaw 技能管理 - 新设计")
    root.geometry("900x650")
    
    panel = SkillsPanelNew(root)
    panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    root.mainloop()
