#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw Butler - 健康度仪表盘 UI 组件

功能：
1. 健康度评分显示
2. 环形进度条
3. 分类得分展示
4. 历史趋势图表
"""

import tkinter as tk
from tkinter import ttk
import math


class CircularProgress(tk.Canvas):
    """环形进度条组件"""
    
    def __init__(self, parent, size=120, thickness=12, **kwargs):
        super().__init__(parent, width=size, height=size, bg="white", highlightthickness=0, **kwargs)
        self.size = size
        self.thickness = thickness
        self.center = size // 2
        self.radius = (size - thickness) // 2
        
        # 默认颜色
        self.bg_color = "#e0e0e0"
        self.fg_color = "#4CAF50"
        
        # 绘制背景圆环
        self._draw_bg()
        
        # 进度弧
        self.arc_id = None
        
        # 中心文字
        self.text_id = self.create_text(
            self.center, self.center,
            text="0%",
            font=("Microsoft YaHei", 16, "bold"),
            fill="#333"
        )
    
    def _draw_bg(self):
        """绘制背景圆环"""
        x0 = self.thickness // 2
        y0 = self.thickness // 2
        x1 = self.size - x0
        y1 = self.size - y0
        
        self.create_oval(
            x0, y0, x1, y1,
            outline=self.bg_color,
            width=self.thickness
        )
    
    def set_progress(self, percentage: int, color: str = None):
        """设置进度"""
        if color:
            self.fg_color = color
        
        # 删除旧的进度弧
        if self.arc_id:
            self.delete(self.arc_id)
        
        # 计算角度
        angle = (percentage / 100) * 360
        
        # 绘制进度弧
        x0 = self.thickness // 2
        y0 = self.thickness // 2
        x1 = self.size - x0
        y1 = self.size - y0
        
        # 从顶部开始（-90度）
        start_angle = 90
        
        self.arc_id = self.create_arc(
            x0, y0, x1, y1,
            start=start_angle,
            extent=-angle,
            outline=self.fg_color,
            width=self.thickness,
            style="arc"
        )
        
        # 更新文字
        self.itemconfig(self.text_id, text=f"{percentage}%")
    
    def set_color(self, color: str):
        """设置进度条颜色"""
        self.fg_color = color


class HealthScoreCard(tk.Frame):
    """健康度评分卡片"""
    
    def __init__(self, parent, title: str, score: int, color: str, **kwargs):
        super().__init__(parent, bg="white", highlightbackground="#ddd", 
                        highlightthickness=1, padx=15, pady=10, **kwargs)
        
        # 标题
        tk.Label(
            self, text=title, font=("Microsoft YaHei", 10),
            bg="white", fg="#666"
        ).pack()
        
        # 分数
        score_frame = tk.Frame(self, bg="white")
        score_frame.pack(pady=5)
        
        tk.Label(
            score_frame, text=str(score), font=("Microsoft YaHei", 24, "bold"),
            bg="white", fg=color
        ).pack(side=tk.LEFT)
        
        tk.Label(
            score_frame, text="/100", font=("Microsoft YaHei", 12),
            bg="white", fg="#999"
        ).pack(side=tk.LEFT, pady=(8, 0))
        
        # 进度条
        self.progress = ttk.Progressbar(self, length=100, mode="determinate", maximum=100)
        self.progress.pack()
        self.progress["value"] = score


class HealthDashboard(tk.Frame):
    """健康度仪表盘"""
    
    def __init__(self, parent, on_diagnose=None, on_fix=None, **kwargs):
        super().__init__(parent, bg="#f5f5f5", **kwargs)
        
        self.on_diagnose = on_diagnose
        self.on_fix = on_fix
        
        self._build_ui()
    
    def _build_ui(self):
        """构建UI"""
        # 主容器
        main_container = tk.Frame(self, bg="#f5f5f5")
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 标题
        header = tk.Frame(main_container, bg="#f5f5f5")
        header.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(
            header, text="🦞 龙虾健康中心", font=("Microsoft YaHei", 20, "bold"),
            bg="#f5f5f5", fg="#333"
        ).pack(side=tk.LEFT)
        
        # 诊断按钮
        if self.on_diagnose:
            ttk.Button(
                header, text="开始诊断", command=self.on_diagnose
            ).pack(side=tk.RIGHT, padx=5)
        
        # 健康度评分区域
        score_frame = tk.Frame(main_container, bg="white", highlightbackground="#ddd", 
                              highlightthickness=1)
        score_frame.pack(fill=tk.X, pady=10)
        
        # 左侧：环形进度条
        left_frame = tk.Frame(score_frame, bg="white", padx=30, pady=20)
        left_frame.pack(side=tk.LEFT)
        
        self.circular_progress = CircularProgress(left_frame, size=150, thickness=15)
        self.circular_progress.pack()
        
        # 等级标签
        self.grade_label = tk.Label(
            left_frame, text="-", font=("Microsoft YaHei", 14, "bold"),
            bg="white", fg="#333"
        )
        self.grade_label.pack(pady=5)
        
        self.grade_desc_label = tk.Label(
            left_frame, text="等待诊断", font=("Microsoft YaHei", 10),
            bg="white", fg="#666"
        )
        self.grade_desc_label.pack()
        
        # 右侧：分类得分
        right_frame = tk.Frame(score_frame, bg="white", padx=20, pady=20)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        tk.Label(
            right_frame, text="分类得分", font=("Microsoft YaHei", 12, "bold"),
            bg="white", fg="#333"
        ).pack(anchor=tk.W, pady=(0, 10))
        
        # 分类得分网格
        self.category_grid = tk.Frame(right_frame, bg="white")
        self.category_grid.pack(fill=tk.X)
        
        # 初始化空的分类卡片
        self.category_cards = {}
        
        # 操作按钮区
        action_frame = tk.Frame(score_frame, bg="white", padx=20, pady=20)
        action_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        if self.on_fix:
            self.fix_button = ttk.Button(
                action_frame, text="一键修复", command=self.on_fix, state=tk.DISABLED
            )
            self.fix_button.pack(pady=5)
        
        ttk.Button(
            action_frame, text="查看历史", command=self._show_history
        ).pack(pady=5)
        
        ttk.Button(
            action_frame, text="导出报告", command=self._export_report
        ).pack(pady=5)
        
        # 问题列表区域
        issues_frame = tk.LabelFrame(
            main_container, text="发现问题", font=("Microsoft YaHei", 11),
            bg="white", padx=10, pady=10
        )
        issues_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 问题列表表头
        header_frame = tk.Frame(issues_frame, bg="white")
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(
            header_frame, text="问题", width=25, font=("Microsoft YaHei", 9, "bold"),
            bg="white", anchor=tk.W
        ).pack(side=tk.LEFT)
        
        tk.Label(
            header_frame, text="状态", width=10, font=("Microsoft YaHei", 9, "bold"),
            bg="white", anchor=tk.W
        ).pack(side=tk.LEFT)
        
        tk.Label(
            header_frame, text="建议", width=30, font=("Microsoft YaHei", 9, "bold"),
            bg="white", anchor=tk.W
        ).pack(side=tk.LEFT)
        
        tk.Label(
            header_frame, text="操作", width=15, font=("Microsoft YaHei", 9, "bold"),
            bg="white", anchor=tk.W
        ).pack(side=tk.LEFT)
        
        # 问题列表容器
        self.issues_container = tk.Frame(issues_frame, bg="white")
        self.issues_container.pack(fill=tk.BOTH, expand=True)
        
        # 初始化空状态
        self.empty_label = tk.Label(
            self.issues_container, text="暂无诊断数据，请点击\"开始诊断\"",
            font=("Microsoft YaHei", 10), bg="white", fg="#999"
        )
        self.empty_label.pack(pady=30)
    
    def update_score(self, total_score: int, grade: str, grade_label: str, grade_color: str):
        """更新健康度评分"""
        self.circular_progress.set_progress(total_score, grade_color)
        self.grade_label.config(text=grade, fg=grade_color)
        self.grade_desc_label.config(text=grade_label)
        
        # 启用修复按钮
        if hasattr(self, 'fix_button') and total_score < 100:
            self.fix_button.config(state=tk.NORMAL)
    
    def update_categories(self, categories: list):
        """更新分类得分"""
        # 清空现有卡片
        for widget in self.category_grid.winfo_children():
            widget.destroy()
        
        # 创建新卡片
        for i, cat in enumerate(categories):
            name = cat.get("name", "未知")
            score = cat.get("score", 0)
            
            # 根据分数确定颜色
            if score >= 80:
                color = "#4CAF50"
            elif score >= 60:
                color = "#FFC107"
            else:
                color = "#F44336"
            
            card = HealthScoreCard(self.category_grid, name, score, color)
            card.grid(row=i // 3, column=i % 3, padx=5, pady=5, sticky="nsew")
    
    def update_issues(self, issues: list, on_view=None, on_fix_single=None):
        """更新问题列表"""
        # 清空现有问题
        for widget in self.issues_container.winfo_children():
            widget.destroy()
        
        if not issues:
            self.empty_label = tk.Label(
                self.issues_container, text="✅ 未发现明显问题",
                font=("Microsoft YaHei", 10), bg="white", fg="#4CAF50"
            )
            self.empty_label.pack(pady=30)
            return
        
        # 添加问题行
        for issue in issues:
            row = tk.Frame(self.issues_container, bg="white")
            row.pack(fill=tk.X, pady=2)
            
            name = issue.get("name", "未知")
            status = issue.get("status", "未知")
            message = issue.get("message", "")[:40]
            
            # 状态图标和颜色
            if status == "fail":
                status_text = "❌ 错误"
                status_color = "#F44336"
            elif status == "warn":
                status_text = "⚠️ 警告"
                status_color = "#FF9800"
            else:
                status_text = "ℹ️ 信息"
                status_color = "#2196F3"
            
            tk.Label(
                row, text=name, width=25, font=("Microsoft YaHei", 9),
                bg="white", anchor=tk.W
            ).pack(side=tk.LEFT)
            
            tk.Label(
                row, text=status_text, width=10, font=("Microsoft YaHei", 9),
                bg="white", fg=status_color, anchor=tk.W
            ).pack(side=tk.LEFT)
            
            tk.Label(
                row, text=message, width=30, font=("Microsoft YaHei", 9),
                bg="white", fg="#666", anchor=tk.W
            ).pack(side=tk.LEFT)
            
            # 操作按钮
            btn_frame = tk.Frame(row, bg="white")
            btn_frame.pack(side=tk.LEFT)
            
            if on_view:
                ttk.Button(
                    btn_frame, text="查看", width=6,
                    command=lambda i=issue: on_view(i)
                ).pack(side=tk.LEFT, padx=2)
            
            if on_fix_single and status in ("fail", "warn"):
                ttk.Button(
                    btn_frame, text="修复", width=6,
                    command=lambda i=issue: on_fix_single(i)
                ).pack(side=tk.LEFT, padx=2)
    
    def _show_history(self):
        """显示历史记录"""
        # TODO: 实现历史记录弹窗
        pass
    
    def _export_report(self):
        """导出报告"""
        # TODO: 实现导出功能
        pass


# 便捷函数
def create_health_dashboard(parent, on_diagnose=None, on_fix=None) -> HealthDashboard:
    """创建健康度仪表盘的便捷函数"""
    return HealthDashboard(parent, on_diagnose, on_fix)
