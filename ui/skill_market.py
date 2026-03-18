#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw Butler - 技能市场 UI 组件

功能：
1. 技能列表展示
2. 技能详情面板
3. 安装队列显示
4. 批量操作
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog


class SkillListItem(tk.Frame):
    """技能列表项"""
    
    def __init__(self, parent, skill_info, on_select=None, on_install=None, **kwargs):
        super().__init__(parent, bg="white", highlightbackground="#ddd", 
                        highlightthickness=1, padx=10, pady=8, **kwargs)
        
        self.skill_info = skill_info
        self.on_select = on_select
        self.on_install = on_install
        
        # 选择复选框
        self.selected_var = tk.BooleanVar(value=False)
        self.check = tk.Checkbutton(
            self, variable=self.selected_var, bg="white",
            command=self._on_checkbox_change
        )
        self.check.pack(side=tk.LEFT, padx=(0, 8))
        
        # 图标
        icon = skill_info.get("icon", "📦")
        tk.Label(self, text=icon, font=("", 20), bg="white").pack(side=tk.LEFT, padx=(0, 10))
        
        # 信息区
        info_frame = tk.Frame(self, bg="white")
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 名称行
        name_frame = tk.Frame(info_frame, bg="white")
        name_frame.pack(fill=tk.X)
        
        name = skill_info.get("name", skill_info.get("id", "未知"))
        tk.Label(
            name_frame, text=name, font=("Microsoft YaHei", 10, "bold"),
            bg="white", fg="#333"
        ).pack(side=tk.LEFT)
        
        # 版本
        version = skill_info.get("version", "")
        if version:
            tk.Label(
                name_frame, text=f"v{version}", font=("", 8),
                bg="white", fg="#888"
            ).pack(side=tk.LEFT, padx=(6, 0))
        
        # 状态标签
        status = skill_info.get("status", "")
        if status == "installed":
            tk.Label(
                name_frame, text="✓ 已安装", font=("", 9),
                bg="white", fg="#4CAF50"
            ).pack(side=tk.RIGHT)
        elif status == "update_available":
            tk.Label(
                name_frame, text="↑ 有更新", font=("", 9),
                bg="white", fg="#FF9800"
            ).pack(side=tk.RIGHT)
        
        # 描述
        desc = skill_info.get("description", "")
        summary = desc[:50] + "..." if len(desc) > 50 else desc
        tk.Label(
            info_frame, text=summary, font=("Microsoft YaHei", 9),
            bg="white", fg="#666", anchor=tk.W
        ).pack(fill=tk.X)
        
        # 元信息
        meta = skill_info.get("meta", {})
        meta_text = []
        if "downloads" in meta:
            meta_text.append(f"⬇ {meta['downloads']}")
        if "stars" in meta:
            meta_text.append(f"⭐ {meta['stars']}")
        
        if meta_text:
            tk.Label(
                info_frame, text="  ".join(meta_text), font=("", 8),
                bg="white", fg="#999"
            ).pack(anchor=tk.W)
        
        # 安装按钮（如果未安装）
        if status != "installed" and on_install:
            ttk.Button(
                self, text="安装", width=8,
                command=lambda: on_install(skill_info)
            ).pack(side=tk.RIGHT, padx=(10, 0))
        
        # 绑定点击事件
        self.bind("<Button-1>", self._on_click)
        for child in self.winfo_children():
            if isinstance(child, tk.Frame):
                for widget in child.winfo_children():
                    widget.bind("<Button-1>", self._on_click)
    
    def _on_click(self, event):
        """点击事件"""
        if self.on_select:
            self.on_select(self.skill_info)
    
    def _on_checkbox_change(self):
        """复选框变化"""
        pass
    
    def is_selected(self) -> bool:
        """是否被选中"""
        return self.selected_var.get()


class SkillDetailPanel(tk.Frame):
    """技能详情面板"""
    
    def __init__(self, parent, on_install=None, on_add_to_queue=None, **kwargs):
        super().__init__(parent, bg="white", highlightbackground="#ddd", 
                        highlightthickness=1, padx=15, pady=15, **kwargs)
        
        self.on_install = on_install
        self.on_add_to_queue = on_add_to_queue
        self.current_skill = None
        
        self._build_ui()
    
    def _build_ui(self):
        """构建UI"""
        # 空状态
        self.empty_label = tk.Label(
            self, text="选择一个技能查看详情", font=("Microsoft YaHei", 12),
            bg="white", fg="#999"
        )
        self.empty_label.pack(expand=True)
        
        # 内容区
        self.content_frame = tk.Frame(self, bg="white")
        
        # 头部
        header = tk.Frame(self.content_frame, bg="white")
        header.pack(fill=tk.X, pady=(0, 15))
        
        self.icon_label = tk.Label(header, text="📦", font=("", 40), bg="white")
        self.icon_label.pack(side=tk.LEFT, padx=(0, 15))
        
        name_frame = tk.Frame(header, bg="white")
        name_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        self.name_label = tk.Label(
            name_frame, text="", font=("Microsoft YaHei", 16, "bold"),
            bg="white", fg="#333"
        )
        self.name_label.pack(anchor=tk.W)
        
        self.id_label = tk.Label(
            name_frame, text="", font=("Microsoft YaHei", 10),
            bg="white", fg="#666"
        )
        self.id_label.pack(anchor=tk.W)
        
        # 版本和作者
        meta_frame = tk.Frame(self.content_frame, bg="white")
        meta_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            meta_frame, text="版本：", font=("Microsoft YaHei", 9),
            bg="white", fg="#666"
        ).pack(side=tk.LEFT)
        
        self.version_label = tk.Label(
            meta_frame, text="", font=("Microsoft YaHei", 9),
            bg="white", fg="#333"
        )
        self.version_label.pack(side=tk.LEFT)
        
        tk.Label(
            meta_frame, text="作者：", font=("Microsoft YaHei", 9),
            bg="white", fg="#666", padx=(20, 0)
        ).pack(side=tk.LEFT)
        
        self.author_label = tk.Label(
            meta_frame, text="", font=("Microsoft YaHei", 9),
            bg="white", fg="#333"
        )
        self.author_label.pack(side=tk.LEFT)
        
        # 描述
        desc_frame = tk.Frame(self.content_frame, bg="white")
        desc_frame.pack(fill=tk.X, pady=15)
        
        tk.Label(
            desc_frame, text="功能简介", font=("Microsoft YaHei", 11, "bold"),
            bg="white", fg="#333"
        ).pack(anchor=tk.W)
        
        self.desc_text = tk.Text(
            desc_frame, height=6, wrap=tk.WORD, font=("Microsoft YaHei", 9),
            bg="white", fg="#333", relief=tk.FLAT, padx=5, pady=5
        )
        self.desc_text.pack(fill=tk.X)
        self.desc_text.config(state=tk.DISABLED)
        
        # 依赖检查
        self.dependency_frame = tk.LabelFrame(
            self.content_frame, text="依赖检查", font=("Microsoft YaHei", 10),
            bg="white", padx=10, pady=10
        )
        self.dependency_frame.pack(fill=tk.X, pady=10)
        
        self.dependency_label = tk.Label(
            self.dependency_frame, text="点击检查依赖", font=("Microsoft YaHei", 9),
            bg="white", fg="#666"
        )
        self.dependency_label.pack()
        
        # 操作按钮
        btn_frame = tk.Frame(self.content_frame, bg="white")
        btn_frame.pack(fill=tk.X, pady=15)
        
        self.install_btn = ttk.Button(
            btn_frame, text="一键安装", command=self._on_install
        )
        self.install_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.queue_btn = ttk.Button(
            btn_frame, text="添加到队列", command=self._on_add_to_queue
        )
        self.queue_btn.pack(side=tk.LEFT)
    
    def show_skill(self, skill_info: dict):
        """显示技能详情"""
        self.current_skill = skill_info
        
        # 隐藏空状态，显示内容
        self.empty_label.pack_forget()
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 更新内容
        self.name_label.config(text=skill_info.get("name", "未知"))
        self.id_label.config(text=skill_info.get("id", ""))
        self.version_label.config(text=skill_info.get("version", "未知"))
        self.author_label.config(text=skill_info.get("author", "未知"))
        
        # 更新描述
        self.desc_text.config(state=tk.NORMAL)
        self.desc_text.delete("1.0", tk.END)
        self.desc_text.insert("1.0", skill_info.get("description", "暂无描述"))
        self.desc_text.config(state=tk.DISABLED)
        
        # 更新按钮状态
        status = skill_info.get("status", "")
        if status == "installed":
            self.install_btn.config(text="已安装", state=tk.DISABLED)
        else:
            self.install_btn.config(text="一键安装", state=tk.NORMAL)
    
    def _on_install(self):
        """安装按钮点击"""
        if self.on_install and self.current_skill:
            self.on_install(self.current_skill)
    
    def _on_add_to_queue(self):
        """添加到队列按钮点击"""
        if self.on_add_to_queue and self.current_skill:
            self.on_add_to_queue(self.current_skill)
    
    def update_dependency_status(self, status: str, message: str):
        """更新依赖检查状态"""
        colors = {
            "checking": "#FFC107",
            "satisfied": "#4CAF50",
            "missing": "#F44336",
            "optional": "#2196F3"
        }
        self.dependency_label.config(text=message, fg=colors.get(status, "#333"))


class InstallQueuePanel(tk.Frame):
    """安装队列面板"""
    
    def __init__(self, parent, on_cancel=None, on_retry=None, **kwargs):
        super().__init__(parent, bg="#f5f5f5", **kwargs)
        
        self.on_cancel = on_cancel
        self.on_retry = on_retry
        self.task_widgets = {}
        
        self._build_ui()
    
    def _build_ui(self):
        """构建UI"""
        # 头部
        header = tk.Frame(self, bg="#f5f5f5")
        header.pack(fill=tk.X, padx=10, pady=5)
        
        self.title_label = tk.Label(
            header, text="安装队列 (0个任务)", font=("Microsoft YaHei", 11, "bold"),
            bg="#f5f5f5", fg="#333"
        )
        self.title_label.pack(side=tk.LEFT)
        
        # 整体进度
        self.progress_label = tk.Label(
            header, text="0%", font=("Microsoft YaHei", 10),
            bg="#f5f5f5", fg="#666"
        )
        self.progress_label.pack(side=tk.RIGHT)
        
        self.overall_progress = ttk.Progressbar(header, length=150, mode="determinate")
        self.overall_progress.pack(side=tk.RIGHT, padx=10)
        
        # 任务列表
        self.tasks_container = tk.Frame(self, bg="white", highlightbackground="#ddd", 
                                       highlightthickness=1)
        self.tasks_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 空状态
        self.empty_label = tk.Label(
            self.tasks_container, text="暂无安装任务",
            font=("Microsoft YaHei", 10), bg="white", fg="#999"
        )
        self.empty_label.pack(pady=20)
    
    def add_task(self, task_id: str, skill_name: str):
        """添加任务到显示"""
        # 隐藏空状态
        self.empty_label.pack_forget()
        
        # 创建任务行
        task_frame = tk.Frame(self.tasks_container, bg="white", padx=10, pady=5)
        task_frame.pack(fill=tk.X)
        
        # 状态图标
        status_label = tk.Label(
            task_frame, text="⏳", font=("", 12), bg="white"
        )
        status_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # 技能名称
        name_label = tk.Label(
            task_frame, text=skill_name, font=("Microsoft YaHei", 10),
            bg="white", fg="#333", width=20, anchor=tk.W
        )
        name_label.pack(side=tk.LEFT)
        
        # 状态文本
        state_label = tk.Label(
            task_frame, text="等待中", font=("Microsoft YaHei", 9),
            bg="white", fg="#666", width=12
        )
        state_label.pack(side=tk.LEFT, padx=10)
        
        # 进度条
        progress = ttk.Progressbar(task_frame, length=150, mode="determinate")
        progress.pack(side=tk.LEFT, padx=10)
        
        # 操作按钮
        btn_frame = tk.Frame(task_frame, bg="white")
        btn_frame.pack(side=tk.RIGHT)
        
        cancel_btn = ttk.Button(
            btn_frame, text="取消", width=6,
            command=lambda: self._on_cancel_task(task_id)
        )
        cancel_btn.pack(side=tk.LEFT)
        
        # 保存引用
        self.task_widgets[task_id] = {
            "frame": task_frame,
            "status_label": status_label,
            "state_label": state_label,
            "progress": progress,
            "cancel_btn": cancel_btn
        }
        
        self._update_title()
    
    def update_task(self, task_id: str, status: str, progress: int = None, message: str = None):
        """更新任务状态"""
        if task_id not in self.task_widgets:
            return
        
        widgets = self.task_widgets[task_id]
        
        # 状态图标和文本
        status_icons = {
            "pending": "⏳",
            "downloading": "📥",
            "installing": "⚙️",
            "completed": "✅",
            "failed": "❌",
            "cancelled": "🚫"
        }
        
        status_texts = {
            "pending": "等待中",
            "downloading": "下载中",
            "installing": "安装中",
            "completed": "已完成",
            "failed": "失败",
            "cancelled": "已取消"
        }
        
        widgets["status_label"].config(text=status_icons.get(status, "•"))
        widgets["state_label"].config(text=message or status_texts.get(status, status))
        
        # 更新进度
        if progress is not None:
            widgets["progress"]["value"] = progress
        
        # 完成或失败后禁用取消按钮
        if status in ("completed", "failed", "cancelled"):
            widgets["cancel_btn"].config(state=tk.DISABLED)
    
    def remove_task(self, task_id: str):
        """移除任务"""
        if task_id in self.task_widgets:
            self.task_widgets[task_id]["frame"].destroy()
            del self.task_widgets[task_id]
            self._update_title()
    
    def update_overall_progress(self, percentage: int):
        """更新整体进度"""
        self.overall_progress["value"] = percentage
        self.progress_label.config(text=f"{percentage}%")
    
    def _update_title(self):
        """更新标题"""
        count = len(self.task_widgets)
        self.title_label.config(text=f"安装队列 ({count}个任务)")
        
        if count == 0:
            self.empty_label.pack(pady=20)
    
    def _on_cancel_task(self, task_id: str):
        """取消任务"""
        if self.on_cancel:
            self.on_cancel(task_id)


class SkillMarket(tk.Frame):
    """技能市场主界面"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg="#f5f5f5", **kwargs)
        
        self._build_ui()
    
    def _build_ui(self):
        """构建UI"""
        # 顶部工具栏
        toolbar = tk.Frame(self, bg="#f5f5f5")
        toolbar.pack(fill=tk.X, padx=10, pady=10)
        
        # 搜索框
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(toolbar, text="搜索", command=self._on_search).pack(side=tk.LEFT, padx=(0, 10))
        
        # 分类筛选
        self.category_var = tk.StringVar(value="全部")
        category_combo = ttk.Combobox(
            toolbar, textvariable=self.category_var,
            values=["全部", "工具", "开发", "效率", "媒体", "其他"],
            state="readonly", width=12
        )
        category_combo.pack(side=tk.LEFT, padx=(0, 10))
        category_combo.bind("<<ComboboxSelected>>", self._on_category_change)
        
        # 筛选标签
        self.filter_var = tk.StringVar(value="可安装")
        filter_combo = ttk.Combobox(
            toolbar, textvariable=self.filter_var,
            values=["全部", "已安装", "可安装", "有更新"],
            state="readonly", width=12
        )
        filter_combo.pack(side=tk.LEFT, padx=(0, 10))
        filter_combo.bind("<<ComboboxSelected>>", self._on_filter_change)
        
        # 批量操作
        ttk.Button(toolbar, text="批量安装", command=self._on_batch_install).pack(side=tk.RIGHT)
        
        # 主内容区
        content = tk.Frame(self, bg="#f5f5f5")
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 左侧技能列表
        list_frame = tk.Frame(content, bg="white", highlightbackground="#ddd", 
                             highlightthickness=1)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 列表头部
        list_header = tk.Frame(list_frame, bg="white", padx=10, pady=8)
        list_header.pack(fill=tk.X)
        
        tk.Label(
            list_header, text="技能列表", font=("Microsoft YaHei", 11, "bold"),
            bg="white", fg="#333"
        ).pack(side=tk.LEFT)
        
        self.count_label = tk.Label(
            list_header, text="(0)", font=("Microsoft YaHei", 10),
            bg="white", fg="#666"
        )
        self.count_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # 技能列表容器
        self.skills_canvas = tk.Canvas(list_frame, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.skills_canvas.yview)
        self.skills_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.skills_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.skills_inner = tk.Frame(self.skills_canvas, bg="white")
        self.skills_canvas.create_window((0, 0), window=self.skills_inner, anchor=tk.NW, width=400)
        
        def on_configure(event):
            self.skills_canvas.configure(scrollregion=self.skills_canvas.bbox("all"))
        
        self.skills_inner.bind("<Configure>", on_configure)
        
        # 右侧详情面板
        self.detail_panel = SkillDetailPanel(
            content, on_install=self._on_install_skill, on_add_to_queue=self._on_add_to_queue
        )
        self.detail_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # 底部安装队列
        self.queue_panel = InstallQueuePanel(self, on_cancel=self._on_cancel_task)
        self.queue_panel.pack(fill=tk.X, padx=10, pady=10)
    
    def load_skills(self, skills: list):
        """加载技能列表"""
        # 清空现有列表
        for widget in self.skills_inner.winfo_children():
            widget.destroy()
        
        # 添加技能项
        for skill in skills:
            item = SkillListItem(
                self.skills_inner, skill,
                on_select=self._on_skill_select,
                on_install=self._on_install_skill
            )
            item.pack(fill=tk.X, padx=5, pady=2)
        
        # 更新计数
        self.count_label.config(text=f"({len(skills)})")
    
    def _on_skill_select(self, skill_info: dict):
        """技能选中"""
        self.detail_panel.show_skill(skill_info)
    
    def _on_install_skill(self, skill_info: dict):
        """安装技能"""
        # TODO: 实现安装逻辑
        pass
    
    def _on_add_to_queue(self, skill_info: dict):
        """添加到队列"""
        # TODO: 实现添加到队列逻辑
        pass
    
    def _on_cancel_task(self, task_id: str):
        """取消任务"""
        # TODO: 实现取消逻辑
        pass
    
    def _on_search(self):
        """搜索"""
        # TODO: 实现搜索逻辑
        pass
    
    def _on_category_change(self, event):
        """分类改变"""
        # TODO: 实现筛选逻辑
        pass
    
    def _on_filter_change(self, event):
        """筛选改变"""
        # TODO: 实现筛选逻辑
        pass
    
    def _on_batch_install(self):
        """批量安装"""
        # TODO: 实现批量安装逻辑
        pass


# 便捷函数
def create_skill_market(parent) -> SkillMarket:
    """创建技能市场的便捷函数"""
    return SkillMarket(parent)
