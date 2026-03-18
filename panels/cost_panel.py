# -*- coding: utf-8 -*-
"""
成本控制仪表板 - 用量统计、预算设置、告警配置

功能:
- 多维度用量统计（API调用/Token消耗/存储）
- 预算设置与告警配置
- 成本趋势分析
- 团队成本分摊
"""

import os
import json
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    from ttkbootstrap.dialogs import Messagebox
    TTKBOOTSTRAP_AVAILABLE = True
except ImportError:
    import tkinter as tk
    from tkinter import ttk as ttk_module, messagebox
    ttk = ttk_module
    ttk.Canvas = tk.Canvas
    ttk.Toplevel = tk.Toplevel
    ttk.StringVar = tk.StringVar
    ttk.BooleanVar = tk.BooleanVar
    ttk.DoubleVar = tk.DoubleVar

    class Messagebox:
        @staticmethod
        def show_info(message, title="提示"):
            messagebox.showinfo(title, message)

        @staticmethod
        def showwarning(title, message):
            messagebox.showwarning(title, message)

        @staticmethod
        def askyesno(title, message):
            return messagebox.askyesno(title, message)

        @staticmethod
        def showerror(title, message):
            messagebox.showerror(title, message)

    TTKBOOTSTRAP_AVAILABLE = False

from tkinter import simpledialog
from tkinter.constants import (
    X, Y, BOTH, LEFT, RIGHT, TOP, BOTTOM,
    W, E, N, S, NW, NE, SW, SE, CENTER,
    VERTICAL, HORIZONTAL
)


@dataclass
class CostRecord:
    """成本记录"""
    timestamp: str
    model: str
    provider: str
    api_calls: int
    input_tokens: int
    output_tokens: int
    cost_cny: float
    skill_id: str = ""
    instance_id: str = ""


@dataclass
class BudgetConfig:
    """预算配置"""
    monthly_budget: float = 1000.0
    daily_limit: float = 100.0
    alert_threshold: float = 80.0  # 百分比
    enable_email_alert: bool = True
    enable_push_alert: bool = True
    alert_email: str = ""


@dataclass
class ModelPricing:
    """模型定价"""
    model: str
    provider: str
    input_price_per_1m: float  # 每百万输入token价格
    output_price_per_1m: float  # 每百万输出token价格


class MetricCard(ttk.Frame):
    """指标卡片组件"""
    
    def __init__(self, parent, title: str, value: str, change: str = "", 
                 change_positive: bool = True, **kwargs):
        super().__init__(parent, **kwargs)
        
        # 背景色
        if TTKBOOTSTRAP_AVAILABLE:
            self.configure(bootstyle="light")
        
        container = ttk.Frame(self, padding=15)
        container.pack(fill=BOTH, expand=True)
        
        ttk.Label(container, text=title, font=("Microsoft YaHei", 10),
                 foreground="#666").pack(anchor=W)
        
        ttk.Label(container, text=value, font=("Microsoft YaHei", 24, "bold")).pack(anchor=W, pady=5)
        
        if change:
            color = "#10B981" if change_positive else "#EF4444"
            symbol = "↑" if change_positive else "↓"
            ttk.Label(container, text=f"{symbol} {change}",
                     foreground=color, font=("Microsoft YaHei", 9)).pack(anchor=W)


class CostPanel(ttk.Frame):
    """成本控制仪表板面板"""
    
    # 模型定价表 (元/百万tokens)
    MODEL_PRICING = {
        "gpt-4o": ModelPricing("gpt-4o", "openai", 2.5, 10.0),
        "gpt-4o-mini": ModelPricing("gpt-4o-mini", "openai", 0.15, 0.6),
        "claude-3-5-sonnet": ModelPricing("claude-3-5-sonnet", "anthropic", 3.0, 15.0),
        "claude-3-haiku": ModelPricing("claude-3-haiku", "anthropic", 0.25, 1.25),
        "deepseek-chat": ModelPricing("deepseek-chat", "deepseek", 1.0, 2.0),
        "deepseek-reasoner": ModelPricing("deepseek-reasoner", "deepseek", 4.0, 16.0),
        "moonshot/kimi": ModelPricing("moonshot/kimi", "moonshot", 12.0, 12.0),
    }
    
    def __init__(self, parent, app=None, theme_manager=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.theme_manager = theme_manager
        
        # 数据
        self.cost_records: List[CostRecord] = []
        self.budget_config = BudgetConfig()
        self.current_month_cost = 0.0
        self.today_cost = 0.0
        
        # 加载数据
        self._load_data()
        
        self._build_ui()
        
        # 启动数据刷新
        self.refreshing = True
        self.refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self.refresh_thread.start()
    
    def _build_ui(self):
        """构建界面"""
        # 标题栏
        header = ttk.Frame(self)
        header.pack(fill=X, pady=(0, 10))
        
        ttk.Label(header, text="💰 成本控制仪表板",
                 font=("Microsoft YaHei", 16, "bold")).pack(side=LEFT)
        
        ttk.Button(header, text="⚙️ 设置",
                  command=self._show_settings_dialog,
                  bootstyle="secondary" if TTKBOOTSTRAP_AVAILABLE else None).pack(side=RIGHT)
        
        # 指标卡片区域
        metrics_frame = ttk.Frame(self)
        metrics_frame.pack(fill=X, pady=10)
        
        # 本月支出
        self.month_card = MetricCard(
            metrics_frame, "本月支出", "¥0.00", "0%", True
        )
        self.month_card.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 10))
        
        # 预算使用
        self.budget_card = MetricCard(
            metrics_frame, "预算使用", "0%", "剩余 ¥0", True
        )
        self.budget_card.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 10))
        
        # API调用
        self.api_card = MetricCard(
            metrics_frame, "本月API调用", "0", "", True
        )
        self.api_card.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 10))
        
        # Token消耗
        self.token_card = MetricCard(
            metrics_frame, "本月Token", "0M", "", True
        )
        self.token_card.pack(side=LEFT, fill=BOTH, expand=True)
        
        # 图表区域 (使用 WebView 或 Canvas)
        chart_frame = ttk.LabelFrame(self, text="📊 成本趋势", padding=10)
        chart_frame.pack(fill=BOTH, expand=True, pady=10)
        
        # 使用 Canvas 绘制简单图表
        self.chart_canvas = ttk.Canvas(chart_frame, height=200, bg="white")
        self.chart_canvas.pack(fill=BOTH, expand=True)
        
        # 绑定大小变化事件
        self.chart_canvas.bind("<Configure>", self._on_chart_resize)
        
        # 用量明细表格
        detail_frame = ttk.LabelFrame(self, text="📋 用量明细", padding=10)
        detail_frame.pack(fill=BOTH, expand=True, pady=10)
        
        # 表头
        headers = ["模型", "调用次数", "输入Token", "输出Token", "费用"]
        header_frame = ttk.Frame(detail_frame)
        header_frame.pack(fill=X)
        
        for i, header_text in enumerate(headers):
            ttk.Label(header_frame, text=header_text,
                     font=("Microsoft YaHei", 9, "bold"),
                     width=15 if i == 0 else 12).pack(side=LEFT, padx=5)
        
        # 表格内容
        self.table_frame = ttk.Frame(detail_frame)
        self.table_frame.pack(fill=BOTH, expand=True, pady=5)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(self.table_frame)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # 告警配置区域
        alert_frame = ttk.LabelFrame(self, text="🔔 告警配置", padding=10)
        alert_frame.pack(fill=X, pady=10)
        
        self.alert_vars = {
            'budget_80': ttk.BooleanVar(value=self.budget_config.alert_threshold <= 80),
            'daily_limit': ttk.BooleanVar(value=True),
            'weekly_report': ttk.BooleanVar(value=False),
        }
        
        ttk.Checkbutton(alert_frame, text="预算使用 80% 时邮件告警",
                       variable=self.alert_vars['budget_80']).pack(anchor=W)
        
        ttk.Checkbutton(alert_frame, text="单日支出超过限制时推送通知",
                       variable=self.alert_vars['daily_limit']).pack(anchor=W)
        
        ttk.Checkbutton(alert_frame, text="每周发送成本报表到邮箱",
                       variable=self.alert_vars['weekly_report']).pack(anchor=W)
        
        # 初始刷新
        self._update_metrics()
        self._draw_chart()
        self._update_table()
    
    def _on_chart_resize(self, event):
        """图表大小变化时重绘"""
        self._draw_chart()
    
    def _draw_chart(self):
        """绘制成本趋势图"""
        canvas = self.chart_canvas
        canvas.delete("all")
        
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        
        if width < 100 or height < 100:
            return
        
        # 获取最近30天的数据
        daily_costs = self._get_daily_costs(30)
        
        if not daily_costs:
            canvas.create_text(width//2, height//2, text="暂无数据",
                             font=("Microsoft YaHei", 12), fill="#999")
            return
        
        # 计算最大值用于缩放
        max_cost = max(daily_costs.values()) if daily_costs else 1
        max_cost = max(max_cost, 1)  # 避免除零
        
        # 绘制坐标轴
        margin = 40
        chart_width = width - 2 * margin
        chart_height = height - 2 * margin
        
        # Y轴
        canvas.create_line(margin, margin, margin, height - margin, fill="#ddd")
        # X轴
        canvas.create_line(margin, height - margin, width - margin, height - margin, fill="#ddd")
        
        # 绘制柱状图
        days = list(daily_costs.keys())[-30:]  # 最多显示30天
        bar_width = chart_width / len(days) * 0.8
        spacing = chart_width / len(days) * 0.2
        
        for i, day in enumerate(days):
            cost = daily_costs[day]
            bar_height = (cost / max_cost) * chart_height
            
            x = margin + i * (bar_width + spacing) + spacing / 2
            y = height - margin - bar_height
            
            # 根据费用选择颜色
            if cost > self.budget_config.daily_limit:
                color = "#EF4444"  # 红色：超过日限额
            elif cost > self.budget_config.daily_limit * 0.8:
                color = "#F59E0B"  # 橙色：接近限额
            else:
                color = "#3B82F6"  # 蓝色：正常
            
            canvas.create_rectangle(x, y, x + bar_width, height - margin,
                                   fill=color, outline="")
            
            # 显示日期（每5天显示一次）
            if i % 5 == 0:
                canvas.create_text(x + bar_width/2, height - margin + 15,
                                 text=day[-5:], font=("Microsoft YaHei", 8),
                                 fill="#666")
        
        # Y轴标签
        for i in range(6):
            value = max_cost * i / 5
            y = height - margin - (chart_height * i / 5)
            canvas.create_text(margin - 10, y, text=f"¥{value:.0f}",
                             font=("Microsoft YaHei", 8), fill="#666", anchor=E)
    
    def _get_daily_costs(self, days: int) -> Dict[str, float]:
        """获取每日成本"""
        daily = defaultdict(float)
        cutoff = datetime.now() - timedelta(days=days)
        
        for record in self.cost_records:
            record_time = datetime.fromisoformat(record.timestamp)
            if record_time > cutoff:
                day = record.timestamp[:10]  # YYYY-MM-DD
                daily[day] += record.cost_cny
        
        return dict(daily)
    
    def _update_metrics(self):
        """更新指标卡片"""
        # 计算本月数据
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        month_cost = 0.0
        today_cost = 0.0
        total_calls = 0
        total_input_tokens = 0
        total_output_tokens = 0
        
        for record in self.cost_records:
            record_time = datetime.fromisoformat(record.timestamp)
            if record_time >= month_start:
                month_cost += record.cost_cny
                total_calls += record.api_calls
                total_input_tokens += record.input_tokens
                total_output_tokens += record.output_tokens
            
            if record_time >= today_start:
                today_cost += record.cost_cny
        
        self.current_month_cost = month_cost
        self.today_cost = today_cost
        
        # 更新卡片
        # 本月支出
        for widget in self.month_card.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, ttk.Label) and child.cget("text").startswith("¥"):
                    child.config(text=f"¥{month_cost:.2f}")
                elif isinstance(child, ttk.Label) and "↑" in child.cget("text"):
                    # 计算环比变化
                    last_month = self._get_last_month_cost()
                    if last_month > 0:
                        change = (month_cost - last_month) / last_month * 100
                        child.config(text=f"{'↑' if change > 0 else '↓'} {abs(change):.1f}%")
        
        # 预算使用
        budget_used = (month_cost / self.budget_config.monthly_budget * 100) if self.budget_config.monthly_budget > 0 else 0
        remaining = max(0, self.budget_config.monthly_budget - month_cost)
        for widget in self.budget_card.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, ttk.Label) and child.cget("text").endswith("%"):
                    child.config(text=f"{budget_used:.1f}%")
                elif isinstance(child, ttk.Label) and "剩余" in child.cget("text"):
                    child.config(text=f"剩余 ¥{remaining:.2f}")
        
        # API调用
        for widget in self.api_card.winfo_children():
            for child in widget.winfo_children():
                if child.cget("text").isdigit() or child.cget("text").replace(",", "").isdigit():
                    child.config(text=f"{total_calls:,}")
        
        # Token消耗
        total_tokens = (total_input_tokens + total_output_tokens) / 1000000  # 转换为百万
        for widget in self.token_card.winfo_children():
            for child in widget.winfo_children():
                if "M" in child.cget("text"):
                    child.config(text=f"{total_tokens:.2f}M")
        
        # 检查告警
        self._check_alerts(budget_used, today_cost)
    
    def _get_last_month_cost(self) -> float:
        """获取上月成本"""
        now = datetime.now()
        if now.month == 1:
            last_month = now.replace(year=now.year - 1, month=12, day=1)
        else:
            last_month = now.replace(month=now.month - 1, day=1)
        
        next_month = (last_month.replace(day=28) + timedelta(days=4)).replace(day=1)
        
        cost = 0.0
        for record in self.cost_records:
            record_time = datetime.fromisoformat(record.timestamp)
            if last_month <= record_time < next_month:
                cost += record.cost_cny
        
        return cost
    
    def _check_alerts(self, budget_used: float, today_cost: float):
        """检查告警条件"""
        alerts = []
        
        # 预算告警
        if budget_used >= self.budget_config.alert_threshold and self.alert_vars['budget_80'].get():
            alerts.append(f"预算使用已达到 {budget_used:.1f}%")
        
        # 日限额告警
        if today_cost > self.budget_config.daily_limit and self.alert_vars['daily_limit'].get():
            alerts.append(f"今日支出 ¥{today_cost:.2f}，已超过日限额 ¥{self.budget_config.daily_limit:.2f}")
        
        # 显示告警
        if alerts and self.app:
            self.app.set_status(f"⚠️ {'; '.join(alerts)}")
    
    def _update_table(self):
        """更新用量明细表格"""
        # 清空现有内容
        for widget in self.table_frame.winfo_children():
            widget.destroy()
        
        # 按模型汇总
        model_stats = defaultdict(lambda: {'calls': 0, 'input': 0, 'output': 0, 'cost': 0.0})
        
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        for record in self.cost_records:
            record_time = datetime.fromisoformat(record.timestamp)
            if record_time >= month_start:
                stats = model_stats[record.model]
                stats['calls'] += record.api_calls
                stats['input'] += record.input_tokens
                stats['output'] += record.output_tokens
                stats['cost'] += record.cost_cny
        
        # 显示数据
        for model, stats in sorted(model_stats.items(), key=lambda x: x[1]['cost'], reverse=True):
            row = ttk.Frame(self.table_frame)
            row.pack(fill=X, pady=2)
            
            ttk.Label(row, text=model, width=15).pack(side=LEFT, padx=5)
            ttk.Label(row, text=f"{stats['calls']:,}", width=12).pack(side=LEFT, padx=5)
            ttk.Label(row, text=f"{stats['input']:,}", width=12).pack(side=LEFT, padx=5)
            ttk.Label(row, text=f"{stats['output']:,}", width=12).pack(side=LEFT, padx=5)
            ttk.Label(row, text=f"¥{stats['cost']:.2f}", width=12,
                     foreground="#EF4444" if stats['cost'] > 100 else "#333").pack(side=LEFT, padx=5)
    
    def _show_settings_dialog(self):
        """显示设置对话框"""
        dialog = ttk.Toplevel(self)
        dialog.title("成本控制设置")
        dialog.geometry("400x400")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        # 预算设置
        budget_frame = ttk.LabelFrame(dialog, text="预算设置", padding=10)
        budget_frame.pack(fill=X, padx=10, pady=10)
        
        ttk.Label(budget_frame, text="月度预算 (¥):").pack(anchor=W)
        budget_var = ttk.DoubleVar(value=self.budget_config.monthly_budget)
        ttk.Entry(budget_frame, textvariable=budget_var).pack(fill=X, pady=5)
        
        ttk.Label(budget_frame, text="日限额 (¥):").pack(anchor=W)
        daily_var = ttk.DoubleVar(value=self.budget_config.daily_limit)
        ttk.Entry(budget_frame, textvariable=daily_var).pack(fill=X, pady=5)
        
        ttk.Label(budget_frame, text="告警阈值 (%):").pack(anchor=W)
        threshold_var = ttk.DoubleVar(value=self.budget_config.alert_threshold)
        ttk.Entry(budget_frame, textvariable=threshold_var).pack(fill=X, pady=5)
        
        # 告警设置
        alert_frame = ttk.LabelFrame(dialog, text="告警设置", padding=10)
        alert_frame.pack(fill=X, padx=10, pady=10)
        
        email_var = ttk.BooleanVar(value=self.budget_config.enable_email_alert)
        ttk.Checkbutton(alert_frame, text="启用邮件告警",
                       variable=email_var).pack(anchor=W)
        
        ttk.Label(alert_frame, text="告警邮箱:").pack(anchor=W, pady=(5, 0))
        email_addr_var = ttk.StringVar(value=self.budget_config.alert_email)
        ttk.Entry(alert_frame, textvariable=email_addr_var).pack(fill=X, pady=5)
        
        def do_save():
            self.budget_config.monthly_budget = budget_var.get()
            self.budget_config.daily_limit = daily_var.get()
            self.budget_config.alert_threshold = threshold_var.get()
            self.budget_config.enable_email_alert = email_var.get()
            self.budget_config.alert_email = email_addr_var.get()

            # 同步写入 core.cost_tracker（若可用）
            tracker = getattr(self.app, "cost_tracker", None) if self.app else None
            if tracker:
                try:
                    t1 = 0.5
                    t2 = max(0.0, min(1.0, float(self.budget_config.alert_threshold) / 100.0))
                    t3 = min(0.99, max(t2, 0.95))
                    tracker.set_budget(
                        daily_limit=float(self.budget_config.daily_limit),
                        monthly_limit=float(self.budget_config.monthly_budget),
                        alert_thresholds=[t1, t2, t3],
                    )
                except Exception as e:
                    print(f"写入核心预算失败，已仅保存本地配置: {e}")

            self._save_data()
            self._update_metrics()
            dialog.destroy()
            
            if TTKBOOTSTRAP_AVAILABLE:
                Messagebox.show_info("设置已保存", "成功")
            else:
                Messagebox.showinfo("成功", "设置已保存")
        
        ttk.Button(dialog, text="保存", command=do_save,
                  bootstyle="primary" if TTKBOOTSTRAP_AVAILABLE else None).pack(pady=20)
    
    def _refresh_loop(self):
        """数据刷新循环"""
        while self.refreshing:
            # 模拟获取新数据
            self._simulate_new_data()
            
            # 更新 UI
            if self.winfo_exists():
                self.after(0, self._update_metrics)
                self.after(0, self._draw_chart)
                self.after(0, self._update_table)
            
            # 每 30 秒刷新一次
            time.sleep(30)
    
    def _simulate_new_data(self):
        """模拟新数据 (实际应从 API 获取)"""
        # 这里仅用于演示，实际应连接到真实的成本数据
        pass
    
    def _load_data(self):
        """加载数据"""
        # 优先使用 core.cost_tracker 真实数据
        tracker = getattr(self.app, "cost_tracker", None) if self.app else None
        if tracker:
            try:
                budget = tracker.get_budget()
                if getattr(budget, "monthly_limit", 0) > 0:
                    self.budget_config.monthly_budget = float(budget.monthly_limit)
                if getattr(budget, "daily_limit", 0) > 0:
                    self.budget_config.daily_limit = float(budget.daily_limit)
                # core 阈值是 0~1，这里用百分比
                self.budget_config.alert_threshold = float(getattr(budget, "alert_threshold_2", 0.8)) * 100

                # 将 core 记录映射为 UI 记录（USD -> CNY）
                usd_to_cny = 7.2
                self.cost_records = []
                for r in getattr(tracker, "_records", []):
                    ts = getattr(r, "timestamp", datetime.now())
                    self.cost_records.append(
                        CostRecord(
                            timestamp=ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                            model=getattr(r, "model", "unknown"),
                            provider=getattr(r, "provider", "") or "unknown",
                            api_calls=1,
                            input_tokens=int(getattr(r, "tokens_input", 0)),
                            output_tokens=int(getattr(r, "tokens_output", 0)),
                            cost_cny=float(getattr(r, "cost_usd", 0.0)) * usd_to_cny,
                        )
                    )

                # 成功走 core 数据则不走本地文件回退
                return
            except Exception as e:
                print(f"从核心模块加载成本数据失败，回退本地数据: {e}")

        config_path = os.path.expanduser("~/.openclaw/cost_data.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # 加载预算配置
                    if 'budget' in data:
                        self.budget_config = BudgetConfig(**data['budget'])
                    
                    # 加载成本记录
                    for record_data in data.get('records', []):
                        self.cost_records.append(CostRecord(**record_data))
        except Exception as e:
            print(f"加载成本数据失败: {e}")
        
        # 如果没有数据，生成一些示例数据
        if not self.cost_records:
            self._generate_sample_data()
    
    def _generate_sample_data(self):
        """生成示例数据"""
        import random
        
        models = ["gpt-4o", "claude-3-5-sonnet", "deepseek-chat"]
        
        for i in range(30):
            day = datetime.now() - timedelta(days=29-i)
            
            # 每天生成几条记录
            for _ in range(random.randint(5, 20)):
                model = random.choice(models)
                pricing = self.MODEL_PRICING.get(model, self.MODEL_PRICING["gpt-4o"])
                
                input_tokens = random.randint(1000, 100000)
                output_tokens = random.randint(500, 50000)
                
                input_cost = input_tokens / 1000000 * pricing.input_price_per_1m
                output_cost = output_tokens / 1000000 * pricing.output_price_per_1m
                
                record = CostRecord(
                    timestamp=day.isoformat(),
                    model=model,
                    provider=pricing.provider,
                    api_calls=1,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_cny=input_cost + output_cost
                )
                self.cost_records.append(record)
    
    def _save_data(self):
        """保存数据"""
        config_path = os.path.expanduser("~/.openclaw/cost_data.json")
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            data = {
                'budget': asdict(self.budget_config),
                'records': [asdict(r) for r in self.cost_records[-1000:]]  # 只保留最近1000条
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存成本数据失败: {e}")
    
    def on_show(self):
        """面板显示时调用"""
        self._update_metrics()
        self._draw_chart()
        self._update_table()
    
    def destroy(self):
        """销毁面板"""
        self.refreshing = False
        self._save_data()
        super().destroy()
