#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw Butler - 健康度评分系统

功能：
1. 计算整体健康度评分 (0-100)
2. 各项分类评分
3. 等级评定 (A-F)
4. 历史记录管理
"""

import json
import os
from datetime import datetime
from enum import Enum
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict


class HealthGrade(Enum):
    """健康度等级"""
    A = ("A", "优秀", "#4CAF50", 90, 100)
    B = ("B", "良好", "#8BC34A", 80, 89)
    C = ("C", "一般", "#FFC107", 70, 79)
    D = ("D", "及格", "#FF9800", 60, 69)
    F = ("F", "需修复", "#F44336", 0, 59)
    
    def __init__(self, grade: str, label: str, color: str, min_score: int, max_score: int):
        self.grade = grade
        self.label = label
        self.color = color
        self.min_score = min_score
        self.max_score = max_score
    
    @classmethod
    def from_score(cls, score: int) -> "HealthGrade":
        """根据分数获取等级"""
        for grade in cls:
            if grade.min_score <= score <= grade.max_score:
                return grade
        return cls.F


@dataclass
class CategoryScore:
    """分类评分"""
    name: str
    score: int
    weight: int
    max_score: int
    issues: List[Dict]
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class HealthScoreResult:
    """健康度评分结果"""
    total_score: int
    grade: HealthGrade
    timestamp: str
    categories: List[CategoryScore]
    summary: str
    recommendations: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "total_score": self.total_score,
            "grade": self.grade.grade,
            "grade_label": self.grade.label,
            "grade_color": self.grade.color,
            "timestamp": self.timestamp,
            "categories": [c.to_dict() for c in self.categories],
            "summary": self.summary,
            "recommendations": self.recommendations
        }


class HealthScoreCalculator:
    """健康度评分计算器"""
    
    # 分类权重配置
    CATEGORY_WEIGHTS = {
        "environment": 25,    # 环境检查
        "configuration": 25,  # 配置检查
        "tools": 20,          # 工具检查
        "security": 15,       # 安全检查
        "performance": 15     # 性能检查
    }
    
    def __init__(self):
        self.categories = {}
    
    def calculate(self, diagnose_results: List[Dict]) -> HealthScoreResult:
        """
        计算健康度评分
        
        Args:
            diagnose_results: 诊断结果列表
            
        Returns:
            HealthScoreResult: 健康度评分结果
        """
        # 按分类分组
        categorized = self._categorize_results(diagnose_results)
        
        # 计算各分类得分
        category_scores = []
        for category, weight in self.CATEGORY_WEIGHTS.items():
            score, max_score, issues = self._calculate_category_score(
                category, categorized.get(category, [])
            )
            category_scores.append(CategoryScore(
                name=self._get_category_name(category),
                score=score,
                weight=weight,
                max_score=max_score,
                issues=issues
            ))
        
        # 计算总分
        total_score = self._calculate_total_score(category_scores)
        
        # 确定等级
        grade = HealthGrade.from_score(total_score)
        
        # 生成总结和建议
        summary = self._generate_summary(total_score, grade, category_scores)
        recommendations = self._generate_recommendations(category_scores)
        
        return HealthScoreResult(
            total_score=total_score,
            grade=grade,
            timestamp=datetime.now().isoformat(),
            categories=category_scores,
            summary=summary,
            recommendations=recommendations
        )
    
    def _categorize_results(self, results: List[Dict]) -> Dict[str, List[Dict]]:
        """将诊断结果按分类分组"""
        categorized = {}
        for result in results:
            category = result.get("category", "other")
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(result)
        return categorized
    
    def _calculate_category_score(
        self, category: str, results: List[Dict]
    ) -> Tuple[int, int, List[Dict]]:
        """
        计算单个分类的得分
        
        Returns:
            (得分, 满分, 问题列表)
        """
        if not results:
            return 100, 100, []
        
        total_weight = 0
        earned_weight = 0
        issues = []
        
        for result in results:
            weight = result.get("weight", 10)
            status = result.get("status", "unknown")
            
            total_weight += weight
            
            if status == "pass":
                earned_weight += weight
            elif status == "warn":
                earned_weight += weight * 0.5
                issues.append({
                    "name": result.get("name", "未知"),
                    "status": "warn",
                    "message": result.get("message", ""),
                    "severity": "medium"
                })
            elif status == "fail":
                issues.append({
                    "name": result.get("name", "未知"),
                    "status": "fail",
                    "message": result.get("message", ""),
                    "severity": "high"
                })
        
        score = int((earned_weight / total_weight) * 100) if total_weight > 0 else 100
        return score, 100, issues
    
    def _calculate_total_score(self, category_scores: List[CategoryScore]) -> int:
        """计算总分"""
        total_weight = sum(self.CATEGORY_WEIGHTS.values())
        weighted_sum = sum(
            (cs.score * cs.weight) for cs in category_scores
        )
        return int(weighted_sum / total_weight)
    
    def _get_category_name(self, category: str) -> str:
        """获取分类显示名称"""
        names = {
            "environment": "环境检查",
            "configuration": "配置检查",
            "tools": "工具检查",
            "security": "安全检查",
            "performance": "性能检查",
            "other": "其他"
        }
        return names.get(category, category)
    
    def _generate_summary(
        self, score: int, grade: HealthGrade, categories: List[CategoryScore]
    ) -> str:
        """生成总结"""
        summary = f"整体健康度: {score}分 ({grade.grade}级 - {grade.label})\n\n"
        
        # 找出最低分的分类
        sorted_categories = sorted(categories, key=lambda x: x.score)
        
        summary += "各分类得分:\n"
        for cat in sorted_categories:
            status_icon = "✅" if cat.score >= 80 else "⚠️" if cat.score >= 60 else "❌"
            summary += f"  {status_icon} {cat.name}: {cat.score}分\n"
        
        return summary
    
    def _generate_recommendations(self, categories: List[CategoryScore]) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        for cat in categories:
            if cat.score < 60:
                recommendations.append(
                    f"🔴 优先处理 {cat.name}: 得分较低({cat.score}分)，"
                    f"建议立即修复 {len(cat.issues)} 个问题"
                )
            elif cat.score < 80:
                recommendations.append(
                    f"🟡 关注 {cat.name}: 有提升空间({cat.score}分)，"
                    f"建议处理 {len(cat.issues)} 个警告"
                )
        
        if not recommendations:
            recommendations.append("✅ 系统健康状况良好，继续保持！")
        
        return recommendations


class HealthScoreHistory:
    """健康度历史记录管理"""
    
    def __init__(self, history_dir: str = None):
        if history_dir is None:
            history_dir = os.path.expanduser("~/.openclaw/health-history")
        self.history_dir = history_dir
        os.makedirs(history_dir, exist_ok=True)
        self.history_file = os.path.join(history_dir, "history.json")
    
    def save(self, result: HealthScoreResult):
        """保存评分结果"""
        history = self._load_history()
        history.append(result.to_dict())
        
        # 只保留最近 100 条记录
        if len(history) > 100:
            history = history[-100:]
        
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    
    def _load_history(self) -> List[Dict]:
        """加载历史记录"""
        if not os.path.exists(self.history_file):
            return []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    
    def get_history(self, limit: int = 30) -> List[Dict]:
        """获取历史记录"""
        history = self._load_history()
        return history[-limit:]
    
    def get_trend(self, days: int = 30) -> List[Dict]:
        """获取健康度趋势"""
        history = self._load_history()
        
        # 按日期分组，取每天最新的记录
        daily_scores = {}
        for record in history:
            date = record.get("timestamp", "")[:10]  # YYYY-MM-DD
            if date:
                daily_scores[date] = record
        
        # 转换为列表并排序
        trend = [
            {"date": date, "score": record["total_score"], "grade": record["grade"]}
            for date, record in sorted(daily_scores.items())
        ]
        
        return trend[-days:]
    
    def compare_with_last(self, current: HealthScoreResult) -> Dict:
        """与上次诊断对比"""
        history = self._load_history()
        if not history:
            return {"is_first": True, "changes": []}
        
        last = history[-1]
        
        changes = []
        
        # 总分变化
        score_diff = current.total_score - last.get("total_score", 0)
        if score_diff > 0:
            changes.append(f"✅ 健康度提升 {score_diff} 分")
        elif score_diff < 0:
            changes.append(f"⚠️ 健康度下降 {abs(score_diff)} 分")
        
        # 分类变化
        current_categories = {c.name: c.score for c in current.categories}
        last_categories = {c["name"]: c["score"] for c in last.get("categories", [])}
        
        for name, score in current_categories.items():
            if name in last_categories:
                diff = score - last_categories[name]
                if diff > 10:
                    changes.append(f"✅ {name} 提升 {diff} 分")
                elif diff < -10:
                    changes.append(f"⚠️ {name} 下降 {abs(diff)} 分")
        
        return {
            "is_first": False,
            "last_score": last.get("total_score", 0),
            "last_grade": last.get("grade", "?"),
            "current_score": current.total_score,
            "current_grade": current.grade.grade,
            "score_diff": score_diff,
            "changes": changes
        }


# 便捷函数
def calculate_health_score(diagnose_results: List[Dict]) -> HealthScoreResult:
    """计算健康度评分的便捷函数"""
    calculator = HealthScoreCalculator()
    return calculator.calculate(diagnose_results)


def save_health_score(result: HealthScoreResult, history_dir: str = None):
    """保存健康度评分的便捷函数"""
    history = HealthScoreHistory(history_dir)
    history.save(result)


def get_health_trend(days: int = 30, history_dir: str = None) -> List[Dict]:
    """获取健康度趋势的便捷函数"""
    history = HealthScoreHistory(history_dir)
    return history.get_trend(days)
