#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core.cost_tracker

成本控制模块：
- API 调用拦截与记录
- 用量统计（按模型/时间段）
- 预算设置与告警
- 成本报表生成
"""

from __future__ import annotations

import os
import json
import time
import logging
import threading
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class CostAlertLevel(Enum):
    """成本告警级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class APICallRecord:
    """API 调用记录"""
    timestamp: datetime
    model: str
    provider: str
    tokens_input: int
    tokens_output: int
    cost_usd: float
    duration_ms: float
    endpoint: str
    success: bool
    error_message: str = ""


@dataclass
class CostBudget:
    """成本预算"""
    daily_limit: float = 0.0  # 0 表示无限制
    monthly_limit: float = 0.0
    alert_threshold_1: float = 0.5  # 50% 告警
    alert_threshold_2: float = 0.8  # 80% 告警
    alert_threshold_3: float = 0.95  # 95% 告警


@dataclass
class CostAlert:
    """成本告警"""
    timestamp: datetime
    level: CostAlertLevel
    message: str
    current_cost: float
    budget_limit: float
    percentage: float


@dataclass
class ModelPricing:
    """模型定价"""
    model_id: str
    provider: str
    input_price_per_1k: float  # USD per 1K tokens
    output_price_per_1k: float  # USD per 1K tokens


class CostTracker:
    """
    成本追踪器 - 核心接口
    
    追踪 API 调用成本，提供预算管理和告警功能
    """
    
    # 默认模型定价（USD per 1K tokens）
    DEFAULT_PRICING = {
        "gpt-4": ModelPricing("gpt-4", "openai", 0.03, 0.06),
        "gpt-4-turbo": ModelPricing("gpt-4-turbo", "openai", 0.01, 0.03),
        "gpt-3.5-turbo": ModelPricing("gpt-3.5-turbo", "openai", 0.0005, 0.0015),
        "claude-3-opus": ModelPricing("claude-3-opus", "anthropic", 0.015, 0.075),
        "claude-3-sonnet": ModelPricing("claude-3-sonnet", "anthropic", 0.003, 0.015),
        "claude-3-haiku": ModelPricing("claude-3-haiku", "anthropic", 0.00025, 0.00125),
        "moonshot-v1-8k": ModelPricing("moonshot-v1-8k", "moonshot", 0.001, 0.002),
        "moonshot-v1-32k": ModelPricing("moonshot-v1-32k", "moonshot", 0.002, 0.004),
        "deepseek-chat": ModelPricing("deepseek-chat", "deepseek", 0.00014, 0.00028),
        "gemini-pro": ModelPricing("gemini-pro", "google", 0.0005, 0.0015),
    }
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = config_dir or os.path.expanduser("~/.openclaw")
        self._records: List[APICallRecord] = []
        self._pricing: Dict[str, ModelPricing] = dict(self.DEFAULT_PRICING)
        self._budget = CostBudget()
        self._alerts: List[CostAlert] = []
        self._callbacks: List[Callable[[CostAlert], None]] = []
        self._lock = threading.Lock()
        self._daily_cost_cache: Dict[str, float] = {}
        
        # 加载配置
        self._load_config()
    
    # ========== API 调用记录接口 ==========
    
    def record_call(
        self,
        model: str,
        tokens_input: int,
        tokens_output: int,
        provider: str = "",
        duration_ms: float = 0.0,
        endpoint: str = "",
        success: bool = True,
        error_message: str = ""
    ) -> float:
        """
        记录 API 调用
        
        Args:
            model: 模型 ID
            tokens_input: 输入 token 数
            tokens_output: 输出 token 数
            provider: 提供商
            duration_ms: 调用耗时
            endpoint: API 端点
            success: 是否成功
            error_message: 错误信息
        
        Returns:
            本次调用成本（USD）
        """
        cost = self._calculate_cost(model, tokens_input, tokens_output)
        
        record = APICallRecord(
            timestamp=datetime.now(),
            model=model,
            provider=provider,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_usd=cost,
            duration_ms=duration_ms,
            endpoint=endpoint,
            success=success,
            error_message=error_message
        )
        
        with self._lock:
            self._records.append(record)
            
            # 检查预算告警
            self._check_budget_alerts()
        
        # 保存记录
        self._save_records()
        
        return cost
    
    def _calculate_cost(self, model: str, tokens_input: int, tokens_output: int) -> float:
        """计算调用成本"""
        pricing = self._pricing.get(model)
        if not pricing:
            # 使用默认定价
            pricing = ModelPricing(model, "unknown", 0.001, 0.002)
        
        input_cost = (tokens_input / 1000) * pricing.input_price_per_1k
        output_cost = (tokens_output / 1000) * pricing.output_price_per_1k
        
        return input_cost + output_cost
    
    # ========== 统计查询接口 ==========
    
    def get_daily_cost(self, date: Optional[datetime] = None) -> float:
        """获取指定日期的成本"""
        if date is None:
            date = datetime.now()
        
        date_key = date.strftime("%Y-%m-%d")
        
        with self._lock:
            total = 0.0
            for record in self._records:
                if record.timestamp.strftime("%Y-%m-%d") == date_key:
                    total += record.cost_usd
            return total
    
    def get_monthly_cost(self, year_month: Optional[str] = None) -> float:
        """获取指定月份的成本"""
        if year_month is None:
            year_month = datetime.now().strftime("%Y-%m")
        
        with self._lock:
            total = 0.0
            for record in self._records:
                if record.timestamp.strftime("%Y-%m") == year_month:
                    total += record.cost_usd
            return total
    
    def get_cost_by_model(self, days: int = 30) -> Dict[str, float]:
        """按模型统计成本"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with self._lock:
            costs = defaultdict(float)
            for record in self._records:
                if record.timestamp >= cutoff_date:
                    costs[record.model] += record.cost_usd
            return dict(costs)
    
    def get_cost_by_provider(self, days: int = 30) -> Dict[str, float]:
        """按提供商统计成本"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with self._lock:
            costs = defaultdict(float)
            for record in self._records:
                if record.timestamp >= cutoff_date:
                    provider = record.provider or "unknown"
                    costs[provider] += record.cost_usd
            return dict(costs)
    
    def get_usage_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        获取使用统计
        
        Returns:
            {
                "total_calls": int,
                "total_cost_usd": float,
                "total_tokens_input": int,
                "total_tokens_output": int,
                "avg_latency_ms": float,
                "success_rate": float,
                "by_model": Dict[str, Dict],
                "by_day": Dict[str, float]
            }
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with self._lock:
            records = [r for r in self._records if r.timestamp >= cutoff_date]
            
            if not records:
                return {
                    "total_calls": 0,
                    "total_cost_usd": 0.0,
                    "total_tokens_input": 0,
                    "total_tokens_output": 0,
                    "avg_latency_ms": 0.0,
                    "success_rate": 0.0,
                    "by_model": {},
                    "by_day": {}
                }
            
            total_calls = len(records)
            total_cost = sum(r.cost_usd for r in records)
            total_tokens_input = sum(r.tokens_input for r in records)
            total_tokens_output = sum(r.tokens_output for r in records)
            avg_latency = sum(r.duration_ms for r in records) / total_calls
            success_rate = sum(1 for r in records if r.success) / total_calls
            
            # 按模型统计
            by_model = defaultdict(lambda: {"calls": 0, "cost": 0.0, "tokens": 0})
            for record in records:
                by_model[record.model]["calls"] += 1
                by_model[record.model]["cost"] += record.cost_usd
                by_model[record.model]["tokens"] += record.tokens_input + record.tokens_output
            
            # 按天统计
            by_day = defaultdict(float)
            for record in records:
                day_key = record.timestamp.strftime("%Y-%m-%d")
                by_day[day_key] += record.cost_usd
            
            return {
                "total_calls": total_calls,
                "total_cost_usd": round(total_cost, 4),
                "total_tokens_input": total_tokens_input,
                "total_tokens_output": total_tokens_output,
                "avg_latency_ms": round(avg_latency, 2),
                "success_rate": round(success_rate, 4),
                "by_model": dict(by_model),
                "by_day": dict(by_day)
            }
    
    # ========== 预算管理接口 ==========
    
    def set_budget(
        self,
        daily_limit: float = 0.0,
        monthly_limit: float = 0.0,
        alert_thresholds: Optional[List[float]] = None
    ):
        """设置预算"""
        self._budget.daily_limit = daily_limit
        self._budget.monthly_limit = monthly_limit
        
        if alert_thresholds and len(alert_thresholds) >= 3:
            self._budget.alert_threshold_1 = alert_thresholds[0]
            self._budget.alert_threshold_2 = alert_thresholds[1]
            self._budget.alert_threshold_3 = alert_thresholds[2]
        
        self._save_config()
    
    def get_budget(self) -> CostBudget:
        """获取当前预算设置"""
        return self._budget
    
    def _check_budget_alerts(self):
        """检查预算告警"""
        # 检查日预算
        if self._budget.daily_limit > 0:
            daily_cost = self.get_daily_cost()
            percentage = daily_cost / self._budget.daily_limit
            
            if percentage >= self._budget.alert_threshold_3:
                self._trigger_alert(
                    CostAlertLevel.CRITICAL,
                    f"日预算即将耗尽: ${daily_cost:.2f} / ${self._budget.daily_limit:.2f} ({percentage*100:.1f}%)",
                    daily_cost,
                    self._budget.daily_limit,
                    percentage
                )
            elif percentage >= self._budget.alert_threshold_2:
                self._trigger_alert(
                    CostAlertLevel.WARNING,
                    f"日预算使用超过 80%: ${daily_cost:.2f} / ${self._budget.daily_limit:.2f} ({percentage*100:.1f}%)",
                    daily_cost,
                    self._budget.daily_limit,
                    percentage
                )
            elif percentage >= self._budget.alert_threshold_1:
                self._trigger_alert(
                    CostAlertLevel.INFO,
                    f"日预算使用超过 50%: ${daily_cost:.2f} / ${self._budget.daily_limit:.2f} ({percentage*100:.1f}%)",
                    daily_cost,
                    self._budget.daily_limit,
                    percentage
                )
        
        # 检查月预算
        if self._budget.monthly_limit > 0:
            monthly_cost = self.get_monthly_cost()
            percentage = monthly_cost / self._budget.monthly_limit
            
            if percentage >= self._budget.alert_threshold_3:
                self._trigger_alert(
                    CostAlertLevel.CRITICAL,
                    f"月预算即将耗尽: ${monthly_cost:.2f} / ${self._budget.monthly_limit:.2f} ({percentage*100:.1f}%)",
                    monthly_cost,
                    self._budget.monthly_limit,
                    percentage
                )
    
    def _trigger_alert(
        self,
        level: CostAlertLevel,
        message: str,
        current_cost: float,
        budget_limit: float,
        percentage: float
    ):
        """触发告警"""
        alert = CostAlert(
            timestamp=datetime.now(),
            level=level,
            message=message,
            current_cost=current_cost,
            budget_limit=budget_limit,
            percentage=percentage
        )
        
        self._alerts.append(alert)
        
        # 调用回调
        for callback in self._callbacks:
            try:
                callback(alert)
            except Exception as e:
                print(f"[警告] 告警回调执行失败: {e}")
    
    def on_alert(self, callback: Callable[[CostAlert], None]):
        """注册告警回调"""
        self._callbacks.append(callback)
    
    def get_alerts(self, level: Optional[CostAlertLevel] = None) -> List[CostAlert]:
        """获取告警列表"""
        if level:
            return [a for a in self._alerts if a.level == level]
        return self._alerts.copy()
    
    def clear_alerts(self):
        """清空告警"""
        self._alerts.clear()
    
    # ========== 定价管理接口 ==========
    
    def set_model_pricing(self, model_id: str, input_price: float, output_price: float, provider: str = ""):
        """设置模型定价"""
        self._pricing[model_id] = ModelPricing(
            model_id=model_id,
            provider=provider,
            input_price_per_1k=input_price,
            output_price_per_1k=output_price
        )
        self._save_config()
    
    def get_model_pricing(self, model_id: str) -> Optional[ModelPricing]:
        """获取模型定价"""
        return self._pricing.get(model_id)
    
    # ========== 报表生成接口 ==========
    
    def generate_daily_report(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """生成日报"""
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%Y-%m-%d")
        
        with self._lock:
            records = [r for r in self._records if r.timestamp.strftime("%Y-%m-%d") == date_str]
        
        return self._generate_report(f"日报 ({date_str})", records)
    
    def generate_monthly_report(self, year_month: Optional[str] = None) -> Dict[str, Any]:
        """生成月报"""
        if year_month is None:
            year_month = datetime.now().strftime("%Y-%m")
        
        with self._lock:
            records = [r for r in self._records if r.timestamp.strftime("%Y-%m") == year_month]
        
        return self._generate_report(f"月报 ({year_month})", records)
    
    def _generate_report(self, title: str, records: List[APICallRecord]) -> Dict[str, Any]:
        """生成报表"""
        if not records:
            return {
                "title": title,
                "summary": "无数据",
                "total_cost": 0.0,
                "total_calls": 0
            }
        
        total_cost = sum(r.cost_usd for r in records)
        total_calls = len(records)
        successful_calls = sum(1 for r in records if r.success)
        
        by_model = defaultdict(lambda: {"calls": 0, "cost": 0.0})
        for record in records:
            by_model[record.model]["calls"] += 1
            by_model[record.model]["cost"] += record.cost_usd
        
        return {
            "title": title,
            "summary": f"总调用: {total_calls}, 总成本: ${total_cost:.4f}, 成功率: {successful_calls/total_calls*100:.1f}%",
            "total_cost": round(total_cost, 4),
            "total_calls": total_calls,
            "success_rate": round(successful_calls / total_calls, 4),
            "by_model": dict(by_model),
            "generated_at": datetime.now().isoformat()
        }
    
    # ========== 持久化接口 ==========
    
    def _load_config(self):
        """加载配置"""
        try:
            config_path = os.path.join(self.config_dir, "cost_tracker.json")
            
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # 加载预算
                budget_data = data.get("budget", {})
                self._budget = CostBudget(
                    daily_limit=budget_data.get("daily_limit", 0.0),
                    monthly_limit=budget_data.get("monthly_limit", 0.0),
                    alert_threshold_1=budget_data.get("alert_threshold_1", 0.5),
                    alert_threshold_2=budget_data.get("alert_threshold_2", 0.8),
                    alert_threshold_3=budget_data.get("alert_threshold_3", 0.95),
                )
                
                # 加载定价
                pricing_data = data.get("pricing", {})
                for model_id, p in pricing_data.items():
                    self._pricing[model_id] = ModelPricing(
                        model_id=model_id,
                        provider=p.get("provider", ""),
                        input_price_per_1k=p.get("input_price_per_1k", 0.0),
                        output_price_per_1k=p.get("output_price_per_1k", 0.0)
                    )
        except Exception as e:
            print(f"[警告] 加载成本追踪器配置失败: {e}")
    
    def _save_config(self):
        """保存配置"""
        try:
            config_path = os.path.join(self.config_dir, "cost_tracker.json")
            os.makedirs(self.config_dir, exist_ok=True)
            
            data = {
                "budget": {
                    "daily_limit": self._budget.daily_limit,
                    "monthly_limit": self._budget.monthly_limit,
                    "alert_threshold_1": self._budget.alert_threshold_1,
                    "alert_threshold_2": self._budget.alert_threshold_2,
                    "alert_threshold_3": self._budget.alert_threshold_3,
                },
                "pricing": {
                    model_id: {
                        "provider": p.provider,
                        "input_price_per_1k": p.input_price_per_1k,
                        "output_price_per_1k": p.output_price_per_1k
                    }
                    for model_id, p in self._pricing.items()
                },
                "updated_at": datetime.now().isoformat()
            }
            
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[警告] 保存成本追踪器配置失败: {e}")
    
    def _save_records(self):
        """保存调用记录到日志文件（JSON Lines 格式）"""
        try:
            records_dir = os.path.join(self.config_dir, "cost_records")
            os.makedirs(records_dir, exist_ok=True)
            
            # 按日期分文件存储
            today = datetime.now().strftime("%Y-%m-%d")
            records_file = os.path.join(records_dir, f"{today}.jsonl")
            
            # 追加写入今天的记录
            with self._lock:
                records_to_save = self._records.copy()
            
            with open(records_file, "a", encoding="utf-8") as f:
                for record in records_to_save:
                    # 只保存今天的新记录（避免重复）
                    if record.timestamp.strftime("%Y-%m-%d") == today:
                        record_dict = {
                            "timestamp": record.timestamp.isoformat(),
                            "model": record.model,
                            "provider": record.provider,
                            "tokens_input": record.tokens_input,
                            "tokens_output": record.tokens_output,
                            "cost_usd": record.cost_usd,
                            "duration_ms": record.duration_ms,
                            "endpoint": record.endpoint,
                            "success": record.success,
                            "error_message": record.error_message
                        }
                        f.write(json.dumps(record_dict, ensure_ascii=False) + "\n")
            
            logger.debug(f"已保存 {len(records_to_save)} 条记录到 {records_file}")
            
        except Exception as e:
            logger.error(f"保存调用记录失败: {e}")
    
    def _load_records_from_file(self, date_str: Optional[str] = None) -> List[APICallRecord]:
        """从文件加载调用记录"""
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        records = []
        records_file = os.path.join(self.config_dir, "cost_records", f"{date_str}.jsonl")
        
        try:
            if os.path.exists(records_file):
                with open(records_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            record = APICallRecord(
                                timestamp=datetime.fromisoformat(data["timestamp"]),
                                model=data["model"],
                                provider=data["provider"],
                                tokens_input=data["tokens_input"],
                                tokens_output=data["tokens_output"],
                                cost_usd=data["cost_usd"],
                                duration_ms=data["duration_ms"],
                                endpoint=data["endpoint"],
                                success=data["success"],
                                error_message=data.get("error_message", "")
                            )
                            records.append(record)
                        except (json.JSONDecodeError, KeyError) as e:
                            logger.warning(f"解析记录失败: {e}, line={line[:100]}")
                            continue
        except Exception as e:
            logger.error(f"加载记录文件失败: {e}")
        
        return records
    
    def get_cost_trend(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        获取成本趋势数据
        
        Args:
            days: 查询天数
            
        Returns:
            每日成本数据列表
        """
        trend = []
        today = datetime.now()
        
        for i in range(days - 1, -1, -1):
            date = today - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            
            # 从文件加载历史记录
            records = self._load_records_from_file(date_str)
            
            daily_cost = sum(r.cost_usd for r in records)
            daily_calls = len(records)
            
            trend.append({
                "date": date_str,
                "cost_usd": round(daily_cost, 4),
                "calls": daily_calls
            })
        
        return trend
    
    def get_top_expensive_models(self, limit: int = 5, days: int = 7) -> List[Dict[str, Any]]:
        """
        获取成本最高的模型
        
        Args:
            limit: 返回数量
            days: 查询天数
            
        Returns:
            模型成本列表
        """
        model_costs = {}
        today = datetime.now()
        
        for i in range(days):
            date = today - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            records = self._load_records_from_file(date_str)
            
            for record in records:
                if record.model not in model_costs:
                    model_costs[record.model] = {"cost": 0.0, "calls": 0}
                model_costs[record.model]["cost"] += record.cost_usd
                model_costs[record.model]["calls"] += 1
        
        # 排序并返回
        sorted_models = sorted(
            [{"model": m, **v} for m, v in model_costs.items()],
            key=lambda x: x["cost"],
            reverse=True
        )
        
        return sorted_models[:limit]
    
    def cleanup_old_records(self, keep_days: int = 90):
        """
        清理旧记录文件
        
        Args:
            keep_days: 保留天数
        """
        try:
            records_dir = os.path.join(self.config_dir, "cost_records")
            if not os.path.exists(records_dir):
                return
            
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            deleted_count = 0
            
            for filename in os.listdir(records_dir):
                if not filename.endswith(".jsonl"):
                    continue
                
                try:
                    file_date = datetime.strptime(filename.replace(".jsonl", ""), "%Y-%m-%d")
                    if file_date < cutoff_date:
                        filepath = os.path.join(records_dir, filename)
                        os.remove(filepath)
                        deleted_count += 1
                        logger.info(f"删除旧记录文件: {filename}")
                except ValueError:
                    continue
            
            logger.info(f"清理完成，删除 {deleted_count} 个旧记录文件")
            
        except Exception as e:
            logger.error(f"清理旧记录失败: {e}")


# 便捷函数
def get_cost_tracker() -> CostTracker:
    """获取全局成本追踪器"""
    return CostTracker()
