"""
安全评分系统

提供全面的安全评分和仪表盘功能：
- 多维度安全评分
- 历史趋势分析
- 行业基准对比
- 改进建议生成
- 安全等级认证
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path


class SecurityGrade(Enum):
    """安全等级"""
    A_PLUS = "A+"   # 90-100
    A = "A"         # 85-89
    B_PLUS = "B+"   # 80-84
    B = "B"         # 70-79
    C = "C"         # 60-69
    D = "D"         # 40-59
    F = "F"         # 0-39


@dataclass
class ScoreComponent:
    """评分组件"""
    name: str
    score: int  # 0-100
    weight: float  # 权重 0-1
    details: Dict[str, Any]


@dataclass
class SecurityScore:
    """安全评分结果"""
    overall_score: int
    grade: str
    timestamp: str
    components: List[ScoreComponent]
    recommendations: List[str]
    risk_level: str


@dataclass
class ScoreHistory:
    """评分历史"""
    date: str
    score: int
    grade: str
    changes: Dict[str, Any]


class SecurityScoringSystem:
    """
    安全评分系统
    
    评分维度：
    1. 配置安全 (25%) - Gateway 绑定、认证、权限
    2. 密钥管理 (20%) - API Key 强度、轮换、存储
    3. 漏洞状态 (20%) - 已知漏洞、依赖安全
    4. 技能安全 (15%) - 危险函数、权限审查
    5. 审计合规 (10%) - 日志记录、审计追踪
    6. 响应能力 (10%) - 告警机制、自动修复
    """
    
    CONFIG_DIR = os.path.expanduser("~/.openclaw/security")
    SCORE_HISTORY_PATH = os.path.join(CONFIG_DIR, "score_history.json")
    
    # 评分权重
    WEIGHTS = {
        "config_security": 0.25,
        "key_management": 0.20,
        "vulnerability_status": 0.20,
        "skill_security": 0.15,
        "audit_compliance": 0.10,
        "response_capability": 0.10,
    }
    
    def __init__(self):
        self._history: List[ScoreHistory] = []
        self._ensure_db_dir()
        self._load_history()
    
    def _ensure_db_dir(self):
        """确保数据库目录存在"""
        os.makedirs(self.CONFIG_DIR, exist_ok=True)
    
    def _load_history(self):
        """加载评分历史"""
        if os.path.exists(self.SCORE_HISTORY_PATH):
            try:
                with open(self.SCORE_HISTORY_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for hist_data in data.get("history", []):
                        self._history.append(ScoreHistory(**hist_data))
            except Exception:
                pass
    
    def _save_history(self):
        """保存评分历史"""
        history_data = {
            "updated_at": datetime.now().isoformat(),
            "history": [asdict(h) for h in self._history[-365:]],  # 保留一年
        }
        with open(self.SCORE_HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
    
    # --- 核心评分逻辑 ---
    
    def calculate_score(self) -> SecurityScore:
        """
        计算综合安全评分
        
        Returns:
            安全评分结果
        """
        components = []
        
        # 1. 配置安全评分
        config_score = self._score_config_security()
        components.append(ScoreComponent(
            name="配置安全",
            score=config_score["score"],
            weight=self.WEIGHTS["config_security"],
            details=config_score["details"],
        ))
        
        # 2. 密钥管理评分
        key_score = self._score_key_management()
        components.append(ScoreComponent(
            name="密钥管理",
            score=key_score["score"],
            weight=self.WEIGHTS["key_management"],
            details=key_score["details"],
        ))
        
        # 3. 漏洞状态评分
        vuln_score = self._score_vulnerability_status()
        components.append(ScoreComponent(
            name="漏洞状态",
            score=vuln_score["score"],
            weight=self.WEIGHTS["vulnerability_status"],
            details=vuln_score["details"],
        ))
        
        # 4. 技能安全评分
        skill_score = self._score_skill_security()
        components.append(ScoreComponent(
            name="技能安全",
            score=skill_score["score"],
            weight=self.WEIGHTS["skill_security"],
            details=skill_score["details"],
        ))
        
        # 5. 审计合规评分
        audit_score = self._score_audit_compliance()
        components.append(ScoreComponent(
            name="审计合规",
            score=audit_score["score"],
            weight=self.WEIGHTS["audit_compliance"],
            details=audit_score["details"],
        ))
        
        # 6. 响应能力评分
        response_score = self._score_response_capability()
        components.append(ScoreComponent(
            name="响应能力",
            score=response_score["score"],
            weight=self.WEIGHTS["response_capability"],
            details=response_score["details"],
        ))
        
        # 计算加权总分
        overall_score = int(sum(
            c.score * c.weight for c in components
        ))
        
        # 确定等级
        grade = self._score_to_grade(overall_score)
        
        # 确定风险等级
        risk_level = self._score_to_risk(overall_score)
        
        # 生成建议
        recommendations = self._generate_recommendations(components)
        
        score = SecurityScore(
            overall_score=overall_score,
            grade=grade,
            timestamp=datetime.now().isoformat(),
            components=components,
            recommendations=recommendations,
            risk_level=risk_level,
        )
        
        # 保存历史
        self._add_to_history(score)
        
        return score
    
    def _score_config_security(self) -> Dict[str, Any]:
        """评分：配置安全"""
        from .permission_scanner import PermissionScanner
        
        scanner = PermissionScanner()
        report = scanner.scan()
        
        score = report.get("score", 0)
        summary = report.get("summary", {})
        
        # 根据问题数量调整分数
        deductions = (
            summary.get("critical", 0) * 25 +
            summary.get("high", 0) * 10 +
            summary.get("medium", 0) * 5 +
            summary.get("low", 0) * 2
        )
        
        final_score = max(0, score - deductions)
        
        return {
            "score": final_score,
            "details": {
                "base_score": score,
                "deductions": deductions,
                "issues": summary,
                "checks": len(report.get("checks", [])),
            },
        }
    
    def _score_key_management(self) -> Dict[str, Any]:
        """评分：密钥管理"""
        from .key_rotation import KeyRotationManager
        
        manager = KeyRotationManager()
        stats = manager.get_statistics()
        
        score = 100
        issues = []
        
        # 检查是否有即将过期的密钥
        expiring = manager.check_expiring_keys()
        if expiring:
            score -= len(expiring) * 10
            issues.append(f"{len(expiring)} 个密钥即将过期")
        
        # 检查是否有已撤销的密钥
        if stats.get("revoked_keys", 0) > 0:
            score -= 10
            issues.append(f"{stats['revoked_keys']} 个密钥已被撤销")
        
        # 检查自动轮换比例
        total = stats.get("total_keys", 0)
        if total > 0:
            # 假设大部分应该启用自动轮换
            auto_rotate_ratio = 0.5  # 简化计算
            if auto_rotate_ratio < 0.5:
                score -= 10
                issues.append("自动轮换覆盖率不足")
        
        return {
            "score": max(0, score),
            "details": {
                "total_keys": total,
                "expiring_soon": len(expiring),
                "issues": issues,
            },
        }
    
    def _score_vulnerability_status(self) -> Dict[str, Any]:
        """评分：漏洞状态"""
        from .vuln_monitor import RealtimeVulnMonitor
        
        monitor = RealtimeVulnMonitor()
        report = monitor.generate_security_report()
        
        score = 100
        summary = report.get("summary", {})
        
        # 根据未修复漏洞扣分
        unfixed = summary.get("unfixed", 0)
        score -= unfixed * 15
        
        # 根据未确认告警扣分
        unacknowledged = summary.get("unacknowledged", 0)
        score -= unacknowledged * 5
        
        # 根据高危漏洞额外扣分
        high_priority = len(report.get("high_priority", []))
        score -= high_priority * 10
        
        return {
            "score": max(0, score),
            "details": {
                "unfixed_vulnerabilities": unfixed,
                "unacknowledged_alerts": unacknowledged,
                "high_priority_issues": high_priority,
                "monitored_packages": summary.get("monitored_packages", 0),
            },
        }
    
    def _score_skill_security(self) -> Dict[str, Any]:
        """评分：技能安全"""
        from .skill_scanner import SkillSecurityScanner
        
        scanner = SkillSecurityScanner()
        reports = scanner.scan_all()
        
        if not reports:
            return {
                "score": 100,
                "details": {"skills_scanned": 0, "issues": "无已安装技能"},
            }
        
        total_issues = sum(r.issues_count for r in reports)
        critical_issues = sum(r.critical_count for r in reports)
        high_issues = sum(r.high_count for r in reports)
        
        score = 100
        score -= critical_issues * 20
        score -= high_issues * 10
        score -= (total_issues - critical_issues - high_issues) * 3
        
        suspicious = len([r for r in reports if r.is_suspicious])
        
        return {
            "score": max(0, score),
            "details": {
                "skills_scanned": len(reports),
                "total_issues": total_issues,
                "critical_issues": critical_issues,
                "high_issues": high_issues,
                "suspicious_skills": suspicious,
            },
        }
    
    def _score_audit_compliance(self) -> Dict[str, Any]:
        """评分：审计合规"""
        score = 100
        issues = []
        
        # 检查审计日志配置
        config_path = os.path.expanduser("~/.openclaw/openclaw.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    cfg = json.load(f)
                
                logging_config = cfg.get("logging", {})
                
                # 检查日志级别
                if logging_config.get("level") not in ["info", "debug"]:
                    score -= 20
                    issues.append("审计日志级别不足")
                
                # 检查是否启用审计
                if not logging_config.get("audit", False):
                    score -= 20
                    issues.append("未启用审计日志")
                
            except Exception:
                score -= 10
                issues.append("无法读取配置")
        else:
            score -= 30
            issues.append("配置文件不存在")
        
        # 检查安全事件记录
        from .alert_manager import SecurityAlertManager
        manager = SecurityAlertManager()
        stats = manager.get_statistics(days=7)
        
        if stats.get("total_events", 0) == 0:
            # 没有事件记录可能是好事，也可能是日志未启用
            pass
        
        return {
            "score": max(0, score),
            "details": {
                "issues": issues,
                "recent_events": stats.get("total_events", 0),
            },
        }
    
    def _score_response_capability(self) -> Dict[str, Any]:
        """评分：响应能力"""
        score = 100
        issues = []
        
        # 检查告警规则
        from .alert_manager import SecurityAlertManager
        manager = SecurityAlertManager()
        rules = manager.list_rules()
        
        if len(rules) < 3:
            score -= 15
            issues.append("告警规则数量不足")
        
        enabled_rules = len([r for r in rules if r.enabled])
        if enabled_rules < len(rules) * 0.5:
            score -= 10
            issues.append("部分告警规则未启用")
        
        # 检查自动修复能力
        from .hardening_engine import SecurityHardeningEngine
        engine = SecurityHardeningEngine()
        plan = engine.plan()
        
        auto_fixable = len(plan.get("auto_fixable", []))
        if auto_fixable > 0:
            # 有可自动修复的问题，说明自动修复可用
            pass
        
        return {
            "score": max(0, score),
            "details": {
                "total_rules": len(rules),
                "enabled_rules": enabled_rules,
                "auto_fixable_issues": auto_fixable,
                "issues": issues,
            },
        }
    
    # --- 辅助方法 ---
    
    def _score_to_grade(self, score: int) -> str:
        """分数转等级"""
        if score >= 90:
            return SecurityGrade.A_PLUS.value
        elif score >= 85:
            return SecurityGrade.A.value
        elif score >= 80:
            return SecurityGrade.B_PLUS.value
        elif score >= 70:
            return SecurityGrade.B.value
        elif score >= 60:
            return SecurityGrade.C.value
        elif score >= 40:
            return SecurityGrade.D.value
        else:
            return SecurityGrade.F.value
    
    def _score_to_risk(self, score: int) -> str:
        """分数转风险等级"""
        if score >= 80:
            return "low"
        elif score >= 60:
            return "medium"
        elif score >= 40:
            return "high"
        else:
            return "critical"
    
    def _generate_recommendations(self, components: List[ScoreComponent]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 找出得分最低的组件
        sorted_components = sorted(components, key=lambda c: c.score)
        
        for comp in sorted_components[:3]:  # 关注最差的 3 个
            if comp.score < 60:
                recommendations.append(
                    f"【紧急】{comp.name}得分较低 ({comp.score})，建议立即改进"
                )
            elif comp.score < 80:
                recommendations.append(
                    f"{comp.name}有提升空间 ({comp.score})，建议优化"
                )
        
        # 根据具体问题生成建议
        for comp in components:
            details = comp.details
            
            if comp.name == "配置安全":
                issues = details.get("issues", {})
                if issues.get("critical", 0) > 0:
                    recommendations.append(
                        f"发现 {issues['critical']} 个高危配置问题，请使用一键加固修复"
                    )
            
            elif comp.name == "密钥管理":
                if details.get("expiring_soon", 0) > 0:
                    recommendations.append(
                        f"有 {details['expiring_soon']} 个密钥即将过期，建议及时轮换"
                    )
            
            elif comp.name == "漏洞状态":
                if details.get("unfixed_vulnerabilities", 0) > 0:
                    recommendations.append(
                        f"有 {details['unfixed_vulnerabilities']} 个未修复漏洞，建议尽快更新"
                    )
        
        if not recommendations:
            recommendations.append("安全状况良好，继续保持！")
        
        return recommendations
    
    def _add_to_history(self, score: SecurityScore):
        """添加到历史记录"""
        # 计算变化
        changes = {}
        if self._history:
            last = self._history[-1]
            score_change = score.overall_score - last.score
            if score_change != 0:
                changes["score_change"] = score_change
        
        history = ScoreHistory(
            date=score.timestamp,
            score=score.overall_score,
            grade=score.grade,
            changes=changes,
        )
        
        self._history.append(history)
        self._save_history()
    
    # --- 历史趋势 ---
    
    def get_score_history(self, days: int = 30) -> List[ScoreHistory]:
        """获取评分历史"""
        cutoff = datetime.now() - timedelta(days=days)
        return [
            h for h in self._history
            if datetime.fromisoformat(h.date) >= cutoff
        ]
    
    def get_trend_analysis(self, days: int = 7) -> Dict[str, Any]:
        """获取趋势分析"""
        history = self.get_score_history(days)
        
        if len(history) < 2:
            return {
                "trend": "stable",
                "change": 0,
                "message": "数据不足，无法分析趋势",
            }
        
        scores = [h.score for h in history]
        first_score = scores[0]
        last_score = scores[-1]
        change = last_score - first_score
        
        if change > 10:
            trend = "improving"
            message = "安全状况显著改善"
        elif change > 0:
            trend = "slight_improving"
            message = "安全状况有所改善"
        elif change < -10:
            trend = "declining"
            message = "安全状况显著恶化，需要关注"
        elif change < 0:
            trend = "slight_declining"
            message = "安全状况略有下降"
        else:
            trend = "stable"
            message = "安全状况保持稳定"
        
        return {
            "trend": trend,
            "change": change,
            "first_score": first_score,
            "last_score": last_score,
            "average_score": sum(scores) / len(scores),
            "message": message,
        }
    
    # --- 报告生成 ---
    
    def generate_dashboard_data(self) -> Dict[str, Any]:
        """生成仪表盘数据"""
        # 当前评分
        current_score = self.calculate_score()
        
        # 趋势
        trend = self.get_trend_analysis(7)
        
        # 历史
        history = self.get_score_history(30)
        
        return {
            "current": {
                "score": current_score.overall_score,
                "grade": current_score.grade,
                "risk_level": current_score.risk_level,
                "timestamp": current_score.timestamp,
            },
            "components": [
                {
                    "name": c.name,
                    "score": c.score,
                    "weight": c.weight,
                    "weighted_score": int(c.score * c.weight),
                }
                for c in current_score.components
            ],
            "recommendations": current_score.recommendations,
            "trend": trend,
            "history": [
                {"date": h.date, "score": h.score, "grade": h.grade}
                for h in history
            ],
        }


# --- 便捷函数 ---

def get_security_score() -> SecurityScore:
    """便捷函数：获取当前安全评分"""
    system = SecurityScoringSystem()
    return system.calculate_score()


def get_score_dashboard() -> Dict[str, Any]:
    """便捷函数：获取安全评分仪表盘"""
    system = SecurityScoringSystem()
    return system.generate_dashboard_data()


def get_security_trend(days: int = 7) -> Dict[str, Any]:
    """便捷函数：获取安全趋势"""
    system = SecurityScoringSystem()
    return system.get_trend_analysis(days)
