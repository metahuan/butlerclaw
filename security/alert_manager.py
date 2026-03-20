"""
安全事件告警系统

提供实时的安全监控和告警功能：
- 安全事件检测
- 多渠道告警通知
- 告警规则管理
- 事件响应自动化
- 安全报告生成
"""

import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import threading
import time


class EventSeverity(Enum):
    """事件严重等级"""
    CRITICAL = "critical"  # 需要立即响应
    HIGH = "high"          # 需要尽快响应
    MEDIUM = "medium"      # 需要关注
    LOW = "low"            # 一般信息
    INFO = "info"          # 仅记录


class EventType(Enum):
    """事件类型"""
    # 认证相关
    AUTH_FAILURE = "auth_failure"
    AUTH_SUCCESS = "auth_success"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_REVOKED = "token_revoked"
    
    # 访问控制
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    
    # 网络
    SUSPICIOUS_IP = "suspicious_ip"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    DDOS_ATTEMPT = "ddos_attempt"
    
    # 配置
    CONFIG_CHANGED = "config_changed"
    INSECURE_CONFIG = "insecure_config"
    
    # 技能
    SKILL_INSTALLED = "skill_installed"
    SKILL_UNINSTALLED = "skill_uninstalled"
    SUSPICIOUS_SKILL = "suspicious_skill"
    
    # 系统
    PERMISSION_DENIED = "permission_denied"
    FILE_ACCESS_DENIED = "file_access_denied"
    
    # 密钥
    KEY_ROTATED = "key_rotated"
    KEY_EXPIRED = "key_expired"
    KEY_COMPROMISED = "key_compromised"


@dataclass
class SecurityEvent:
    """安全事件"""
    id: str
    timestamp: str
    event_type: str
    severity: str
    source: str
    message: str
    details: Dict[str, Any]
    acknowledged: bool = False
    resolved: bool = False
    resolution: str = ""


@dataclass
class AlertRule:
    """告警规则"""
    id: str
    name: str
    event_types: List[str]
    severity_levels: List[str]
    conditions: Dict[str, Any]
    actions: List[str]
    enabled: bool = True
    cooldown_minutes: int = 60
    last_triggered: Optional[str] = None


@dataclass
class AlertNotification:
    """告警通知"""
    id: str
    event_id: str
    timestamp: str
    channels: List[str]
    status: str  # pending, sent, failed
    content: str


class SecurityAlertManager:
    """
    安全事件告警管理器
    
    功能：
    1. 安全事件收集和存储
    2. 告警规则匹配
    3. 多渠道通知（UI、日志、Webhook）
    4. 告警抑制和聚合
    5. 事件响应自动化
    """
    
    CONFIG_DIR = os.path.expanduser("~/.openclaw")
    EVENTS_DB_PATH = os.path.join(CONFIG_DIR, "security_events.json")
    RULES_PATH = os.path.join(CONFIG_DIR, "alert_rules.json")
    
    # 默认告警规则
    DEFAULT_RULES = [
        {
            "id": "rule_auth_failure",
            "name": "认证失败告警",
            "event_types": ["auth_failure"],
            "severity_levels": ["high", "critical"],
            "conditions": {"threshold": 5, "window_minutes": 10},
            "actions": ["ui_alert", "log"],
            "cooldown_minutes": 30,
        },
        {
            "id": "rule_unauthorized_access",
            "name": "未授权访问告警",
            "event_types": ["unauthorized_access"],
            "severity_levels": ["critical"],
            "conditions": {},
            "actions": ["ui_alert", "log", "block_ip"],
            "cooldown_minutes": 5,
        },
        {
            "id": "rule_suspicious_skill",
            "name": "可疑技能告警",
            "event_types": ["suspicious_skill"],
            "severity_levels": ["high", "critical"],
            "conditions": {},
            "actions": ["ui_alert", "log", "quarantine_skill"],
            "cooldown_minutes": 0,
        },
        {
            "id": "rule_key_compromised",
            "name": "密钥泄露告警",
            "event_types": ["key_compromised"],
            "severity_levels": ["critical"],
            "conditions": {},
            "actions": ["ui_alert", "log", "auto_rotate_key"],
            "cooldown_minutes": 0,
        },
        {
            "id": "rule_rate_limit",
            "name": "速率限制告警",
            "event_types": ["rate_limit_exceeded"],
            "severity_levels": ["medium", "high"],
            "conditions": {"threshold": 10},
            "actions": ["log"],
            "cooldown_minutes": 60,
        },
    ]
    
    def __init__(self):
        self._events: List[SecurityEvent] = []
        self._rules: Dict[str, AlertRule] = {}
        self._handlers: Dict[str, Callable] = {}
        self._event_counters: Dict[str, List[datetime]] = {}
        self._lock = threading.Lock()
        
        self._ensure_db_dir()
        self._load_data()
        self._init_default_rules()
        self._register_default_handlers()
    
    def _ensure_db_dir(self):
        """确保数据库目录存在"""
        os.makedirs(self.CONFIG_DIR, exist_ok=True)
    
    def _load_data(self):
        """加载事件和规则数据"""
        # 加载事件
        if os.path.exists(self.EVENTS_DB_PATH):
            try:
                with open(self.EVENTS_DB_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for event_dict in data.get("events", []):
                        self._events.append(SecurityEvent(**event_dict))
            except Exception:
                pass
        
        # 加载规则
        if os.path.exists(self.RULES_PATH):
            try:
                with open(self.RULES_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for rule_dict in data.get("rules", []):
                        self._rules[rule_dict["id"]] = AlertRule(**rule_dict)
            except Exception:
                pass
    
    def _save_data(self):
        """保存事件和规则数据"""
        # 保存事件（只保留最近 1000 条）
        events_data = {
            "updated_at": datetime.now().isoformat(),
            "events": [asdict(e) for e in self._events[-1000:]],
        }
        with open(self.EVENTS_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(events_data, f, ensure_ascii=False, indent=2)
        
        # 保存规则
        rules_data = {
            "updated_at": datetime.now().isoformat(),
            "rules": [asdict(r) for r in self._rules.values()],
        }
        with open(self.RULES_PATH, "w", encoding="utf-8") as f:
            json.dump(rules_data, f, ensure_ascii=False, indent=2)
    
    def _init_default_rules(self):
        """初始化默认规则"""
        for rule_dict in self.DEFAULT_RULES:
            if rule_dict["id"] not in self._rules:
                self._rules[rule_dict["id"]] = AlertRule(**rule_dict)
        self._save_data()
    
    def _register_default_handlers(self):
        """注册默认告警处理器"""
        self.register_handler("ui_alert", self._handle_ui_alert)
        self.register_handler("log", self._handle_log_alert)
        self.register_handler("block_ip", self._handle_block_ip)
        self.register_handler("quarantine_skill", self._handle_quarantine_skill)
        self.register_handler("auto_rotate_key", self._handle_auto_rotate_key)
    
    # --- 事件管理 ---
    
    def report_event(
        self,
        event_type: EventType,
        severity: EventSeverity,
        source: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> SecurityEvent:
        """
        报告安全事件
        
        Args:
            event_type: 事件类型
            severity: 严重等级
            source: 事件来源
            message: 事件消息
            details: 详细信息
            
        Returns:
            创建的安全事件
        """
        event_id = self._generate_event_id()
        event = SecurityEvent(
            id=event_id,
            timestamp=datetime.now().isoformat(),
            event_type=event_type.value,
            severity=severity.value,
            source=source,
            message=message,
            details=details or {},
        )
        
        with self._lock:
            self._events.append(event)
            self._update_event_counter(event_type.value)
        
        # 保存事件
        self._save_data()
        
        # 触发告警规则
        self._process_event(event)
        
        return event
    
    def get_events(
        self,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 100,
    ) -> List[SecurityEvent]:
        """
        获取安全事件
        
        Args:
            event_type: 事件类型筛选
            severity: 严重等级筛选
            acknowledged: 确认状态筛选
            limit: 返回数量限制
            
        Returns:
            事件列表
        """
        events = self._events
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if severity:
            events = [e for e in events if e.severity == severity]
        
        if acknowledged is not None:
            events = [e for e in events if e.acknowledged == acknowledged]
        
        # 按时间倒序
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)
        
        return events[:limit]
    
    def acknowledge_event(self, event_id: str) -> bool:
        """确认事件"""
        for event in self._events:
            if event.id == event_id:
                event.acknowledged = True
                self._save_data()
                return True
        return False
    
    def resolve_event(self, event_id: str, resolution: str) -> bool:
        """解决事件"""
        for event in self._events:
            if event.id == event_id:
                event.resolved = True
                event.resolution = resolution
                self._save_data()
                return True
        return False
    
    def get_statistics(self, days: int = 7) -> Dict[str, Any]:
        """获取事件统计"""
        cutoff = datetime.now() - timedelta(days=days)
        recent_events = [
            e for e in self._events
            if datetime.fromisoformat(e.timestamp) >= cutoff
        ]
        
        # 按类型统计
        by_type = {}
        by_severity = {}
        
        for event in recent_events:
            by_type[event.event_type] = by_type.get(event.event_type, 0) + 1
            by_severity[event.severity] = by_severity.get(event.severity, 0) + 1
        
        return {
            "total_events": len(recent_events),
            "by_type": by_type,
            "by_severity": by_severity,
            "unacknowledged": len([e for e in recent_events if not e.acknowledged]),
            "unresolved": len([e for e in recent_events if not e.resolved]),
        }
    
    # --- 告警规则管理 ---
    
    def create_rule(self, rule: AlertRule) -> Dict[str, Any]:
        """创建告警规则"""
        if rule.id in self._rules:
            return {"success": False, "message": "规则已存在"}
        
        self._rules[rule.id] = rule
        self._save_data()
        
        return {"success": True, "message": "规则已创建"}
    
    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新告警规则"""
        if rule_id not in self._rules:
            return {"success": False, "message": "规则不存在"}
        
        rule = self._rules[rule_id]
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        
        self._save_data()
        return {"success": True, "message": "规则已更新"}
    
    def delete_rule(self, rule_id: str) -> Dict[str, Any]:
        """删除告警规则"""
        if rule_id not in self._rules:
            return {"success": False, "message": "规则不存在"}
        
        del self._rules[rule_id]
        self._save_data()
        return {"success": True, "message": "规则已删除"}
    
    def list_rules(self) -> List[AlertRule]:
        """列出所有规则"""
        return list(self._rules.values())
    
    # --- 告警处理器 ---
    
    def register_handler(self, action: str, handler: Callable):
        """注册告警处理器"""
        self._handlers[action] = handler
    
    def _process_event(self, event: SecurityEvent):
        """处理事件，触发告警规则"""
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            
            # 检查事件类型匹配
            if event.event_type not in rule.event_types:
                continue
            
            # 检查严重等级匹配
            if event.severity not in rule.severity_levels:
                continue
            
            # 检查冷却期
            if rule.last_triggered:
                last = datetime.fromisoformat(rule.last_triggered)
                cooldown = timedelta(minutes=rule.cooldown_minutes)
                if datetime.now() - last < cooldown:
                    continue
            
            # 检查阈值条件
            if not self._check_conditions(rule, event):
                continue
            
            # 触发告警
            self._trigger_alert(rule, event)
            
            # 更新最后触发时间
            rule.last_triggered = datetime.now().isoformat()
    
    def _check_conditions(self, rule: AlertRule, event: SecurityEvent) -> bool:
        """检查规则条件"""
        conditions = rule.conditions
        
        # 检查阈值
        if "threshold" in conditions:
            threshold = conditions["threshold"]
            window_minutes = conditions.get("window_minutes", 10)
            
            counter = self._event_counters.get(event.event_type, [])
            window = timedelta(minutes=window_minutes)
            now = datetime.now()
            recent = [t for t in counter if now - t < window]
            
            if len(recent) < threshold:
                return False
        
        return True
    
    def _trigger_alert(self, rule: AlertRule, event: SecurityEvent):
        """触发告警"""
        for action in rule.actions:
            handler = self._handlers.get(action)
            if handler:
                try:
                    handler(event, rule)
                except Exception as e:
                    print(f"告警处理失败 ({action}): {e}")
    
    def _update_event_counter(self, event_type: str):
        """更新事件计数器"""
        now = datetime.now()
        if event_type not in self._event_counters:
            self._event_counters[event_type] = []
        self._event_counters[event_type].append(now)
        
        # 清理旧记录（保留 1 小时）
        cutoff = now - timedelta(hours=1)
        self._event_counters[event_type] = [
            t for t in self._event_counters[event_type] if t > cutoff
        ]
    
    # --- 默认告警处理器 ---
    
    def _handle_ui_alert(self, event: SecurityEvent, rule: AlertRule):
        """UI 告警处理器"""
        # 这里可以触发 UI 通知
        print(f"[UI ALERT] {event.severity.upper()}: {event.message}")
    
    def _handle_log_alert(self, event: SecurityEvent, rule: AlertRule):
        """日志告警处理器"""
        log_entry = f"[{event.timestamp}] {event.severity.upper()} - {event.event_type}: {event.message}"
        
        # 写入安全日志
        log_path = os.path.join(self.CONFIG_DIR, "logs", "security.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
    
    def _handle_block_ip(self, event: SecurityEvent, rule: AlertRule):
        """阻止 IP 处理器"""
        ip = event.details.get("ip")
        if ip:
            # 添加到阻止列表
            blocklist_path = os.path.join(self.CONFIG_DIR, "blocklist.json")
            
            blocklist = []
            if os.path.exists(blocklist_path):
                with open(blocklist_path, "r") as f:
                    blocklist = json.load(f)
            
            if ip not in blocklist:
                blocklist.append({
                    "ip": ip,
                    "blocked_at": datetime.now().isoformat(),
                    "reason": event.message,
                })
                
                with open(blocklist_path, "w") as f:
                    json.dump(blocklist, f, indent=2)
    
    def _handle_quarantine_skill(self, event: SecurityEvent, rule: AlertRule):
        """隔离技能处理器"""
        skill_name = event.details.get("skill_name")
        if skill_name:
            # 移动到隔离目录
            skills_root = os.path.expanduser("~/.openclaw/skills")
            quarantine_dir = os.path.expanduser("~/.openclaw/quarantine")
            
            skill_path = os.path.join(skills_root, skill_name)
            quarantine_path = os.path.join(quarantine_dir, skill_name)
            
            if os.path.exists(skill_path):
                os.makedirs(quarantine_dir, exist_ok=True)
                import shutil
                shutil.move(skill_path, quarantine_path)
    
    def _handle_auto_rotate_key(self, event: SecurityEvent, rule: AlertRule):
        """自动轮换密钥处理器"""
        key_id = event.details.get("key_id")
        if key_id:
            try:
                from .key_rotation import KeyRotationManager
                manager = KeyRotationManager()
                manager.rotate_key(key_id, reason="auto_compromised")
            except Exception as e:
                print(f"自动轮换密钥失败: {e}")
    
    # --- 工具方法 ---
    
    def _generate_event_id(self) -> str:
        """生成事件 ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        import random
        random_suffix = ''.join(random.choices('0123456789abcdef', k=6))
        return f"SEC-{timestamp}-{random_suffix}"
    
    def generate_security_report(self, days: int = 7) -> Dict[str, Any]:
        """生成安全报告"""
        stats = self.get_statistics(days)
        recent_events = self.get_events(limit=50)
        
        # 风险分析
        risk_analysis = self._analyze_risks(recent_events)
        
        # 建议
        recommendations = self._generate_recommendations(stats, risk_analysis)
        
        return {
            "generated_at": datetime.now().isoformat(),
            "period_days": days,
            "statistics": stats,
            "risk_analysis": risk_analysis,
            "recommendations": recommendations,
            "recent_events": [
                {
                    "id": e.id,
                    "timestamp": e.timestamp,
                    "type": e.event_type,
                    "severity": e.severity,
                    "message": e.message,
                    "acknowledged": e.acknowledged,
                }
                for e in recent_events
            ],
        }
    
    def _analyze_risks(self, events: List[SecurityEvent]) -> Dict[str, Any]:
        """分析风险"""
        risks = []
        
        # 检查是否有持续的认证失败
        auth_failures = [e for e in events if e.event_type == EventType.AUTH_FAILURE.value]
        if len(auth_failures) >= 5:
            risks.append({
                "type": "brute_force",
                "level": "high",
                "description": f"检测到 {len(auth_failures)} 次认证失败，可能存在暴力破解攻击",
            })
        
        # 检查是否有未授权访问
        unauthorized = [e for e in events if e.event_type == EventType.UNAUTHORIZED_ACCESS.value]
        if unauthorized:
            risks.append({
                "type": "unauthorized_access",
                "level": "critical",
                "description": f"检测到 {len(unauthorized)} 次未授权访问尝试",
            })
        
        # 检查可疑技能
        suspicious_skills = [e for e in events if e.event_type == EventType.SUSPICIOUS_SKILL.value]
        if suspicious_skills:
            risks.append({
                "type": "suspicious_skill",
                "level": "high",
                "description": f"检测到 {len(suspicious_skills)} 个可疑技能",
            })
        
        return {
            "risk_count": len(risks),
            "risks": risks,
            "overall_risk": "high" if any(r["level"] == "critical" for r in risks) else 
                           ("medium" if risks else "low"),
        }
    
    def _generate_recommendations(self, stats: Dict, risk_analysis: Dict) -> List[str]:
        """生成安全建议"""
        recommendations = []
        
        if stats.get("unacknowledged", 0) > 0:
            recommendations.append(f"有 {stats['unacknowledged']} 个未确认的安全事件，建议及时处理")
        
        if risk_analysis.get("overall_risk") == "high":
            recommendations.append("检测到高风险安全威胁，建议立即审查并加强安全措施")
        
        if stats.get("by_type", {}).get("auth_failure", 0) > 10:
            recommendations.append("认证失败次数较多，建议检查是否有暴力破解攻击，并考虑启用 IP 阻止")
        
        if not recommendations:
            recommendations.append("当前安全状况良好，继续保持")
        
        return recommendations


# --- 便捷函数 ---

def report_security_event(
    event_type: EventType,
    severity: EventSeverity,
    source: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> SecurityEvent:
    """便捷函数：报告安全事件"""
    manager = SecurityAlertManager()
    return manager.report_event(event_type, severity, source, message, details)


def check_security_alerts() -> List[SecurityEvent]:
    """便捷函数：检查未确认的安全告警"""
    manager = SecurityAlertManager()
    return manager.get_events(acknowledged=False, limit=10)


def get_security_summary(days: int = 7) -> Dict[str, Any]:
    """便捷函数：获取安全摘要"""
    manager = SecurityAlertManager()
    return manager.generate_security_report(days)
