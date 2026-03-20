"""
等保 2.0 合规检查模块

提供网络安全等级保护 2.0 的合规性检查：
- 安全物理环境检查
- 安全通信网络检查
- 安全区域边界检查
- 安全计算环境检查
- 安全管理中心检查
- 安全管理制度检查
- 安全管理机构检查
- 安全管理人员检查
- 安全建设管理检查
- 安全运维管理检查
"""

import os
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class ComplianceLevel(Enum):
    """合规等级"""
    LEVEL1 = "一级"  # 自主保护
    LEVEL2 = "二级"  # 指导保护
    LEVEL3 = "三级"  # 监督保护
    LEVEL4 = "四级"  # 强制保护


class CheckStatus(Enum):
    """检查状态"""
    PASS = "pass"           # 通过
    FAIL = "fail"           # 不通过
    PARTIAL = "partial"     # 部分通过
    NOT_APPLICABLE = "na"   # 不适用
    MANUAL = "manual"       # 需人工检查


@dataclass
class ComplianceCheck:
    """合规检查项"""
    id: str
    category: str
    name: str
    description: str
    requirement: str
    level: str  # 适用的等保级别
    status: str
    evidence: str
    fix_suggestion: str
    reference: str


@dataclass
class ComplianceReport:
    """合规报告"""
    level: str
    total_checks: int
    passed: int
    failed: int
    partial: int
    not_applicable: int
    manual: int
    compliance_rate: float
    checks: List[ComplianceCheck]
    gaps: List[str]
    recommendations: List[str]


class ComplianceChecker:
    """
    等保 2.0 合规检查器
    
    检查项基于：
    - GB/T 22239-2019 信息安全技术 网络安全等级保护基本要求
    - GB/T 28448-2019 网络安全等级保护测评要求
    """
    
    # 检查项定义
    CHECKS = [
        # === 安全计算环境 ===
        {
            "id": "SEC-COMP-001",
            "category": "安全计算环境",
            "name": "身份鉴别",
            "description": "应对登录的用户进行身份标识和鉴别，身份标识具有唯一性",
            "requirement": "配置强身份认证，禁止匿名访问",
            "level": "二级",
            "check_func": "_check_identity_auth",
        },
        {
            "id": "SEC-COMP-002",
            "category": "安全计算环境",
            "name": "访问控制",
            "description": "应对登录的用户分配账户和权限",
            "requirement": "实施最小权限原则，分离管理权限和操作权限",
            "level": "二级",
            "check_func": "_check_access_control",
        },
        {
            "id": "SEC-COMP-003",
            "category": "安全计算环境",
            "name": "安全审计",
            "description": "应启用安全审计功能，审计覆盖到每个用户",
            "requirement": "启用审计日志，记录重要操作",
            "level": "二级",
            "check_func": "_check_security_audit",
        },
        {
            "id": "SEC-COMP-004",
            "category": "安全计算环境",
            "name": "数据完整性",
            "description": "应采用校验技术保证重要数据在传输和存储过程中的完整性",
            "requirement": "使用 HTTPS/TLS 传输，配置文件完整性校验",
            "level": "二级",
            "check_func": "_check_data_integrity",
        },
        {
            "id": "SEC-COMP-005",
            "category": "安全计算环境",
            "name": "数据保密性",
            "description": "应采用密码技术保证重要数据在传输和存储过程中的保密性",
            "requirement": "敏感数据加密存储，API Key 不明文保存",
            "level": "二级",
            "check_func": "_check_data_confidentiality",
        },
        {
            "id": "SEC-COMP-006",
            "category": "安全计算环境",
            "name": "个人信息保护",
            "description": "应仅采集和保存业务必需的用户个人信息",
            "requirement": "最小化收集个人信息，明确告知用途",
            "level": "二级",
            "check_func": "_check_personal_info_protection",
        },
        
        # === 安全区域边界 ===
        {
            "id": "SEC-BOUND-001",
            "category": "安全区域边界",
            "name": "边界防护",
            "description": "应保证跨越边界的访问和数据流通过边界设备提供的受控接口进行通信",
            "requirement": "限制 Gateway 绑定，防止未授权访问",
            "level": "二级",
            "check_func": "_check_boundary_protection",
        },
        {
            "id": "SEC-BOUND-002",
            "category": "安全区域边界",
            "name": "访问控制",
            "description": "应在网络边界根据访问控制策略设置访问控制规则",
            "requirement": "配置访问控制列表，限制访问来源",
            "level": "二级",
            "check_func": "_check_network_access_control",
        },
        {
            "id": "SEC-BOUND-003",
            "category": "安全区域边界",
            "name": "入侵防范",
            "description": "应在关键网络节点处检测、防止或限制从外部发起的网络攻击行为",
            "requirement": "启用速率限制，防止暴力破解",
            "level": "二级",
            "check_func": "_check_intrusion_prevention",
        },
        
        # === 安全通信网络 ===
        {
            "id": "SEC-COMM-001",
            "category": "安全通信网络",
            "name": "通信传输",
            "description": "应采用校验技术或密码技术保证通信过程中数据的完整性",
            "requirement": "使用 HTTPS/TLS 加密通信",
            "level": "二级",
            "check_func": "_check_communication_security",
        },
        
        # === 安全管理中心 ===
        {
            "id": "SEC-MGMT-001",
            "category": "安全管理中心",
            "name": "系统管理",
            "description": "应对系统管理员进行身份鉴别，只允许其通过特定的命令或操作界面进行系统管理操作",
            "requirement": "管理操作需要身份认证，记录管理日志",
            "level": "二级",
            "check_func": "_check_system_management",
        },
        {
            "id": "SEC-MGMT-002",
            "category": "安全管理中心",
            "name": "集中管控",
            "description": "应对分散在各个设备上的审计数据进行收集汇总和集中分析",
            "requirement": "集中收集安全日志，统一分析",
            "level": "二级",
            "check_func": "_check_centralized_control",
        },
        
        # === 安全管理制度 ===
        {
            "id": "SEC-POLICY-001",
            "category": "安全管理制度",
            "name": "安全策略",
            "description": "应制定网络安全工作的总体方针和安全策略",
            "requirement": "制定安全策略文档，定期更新",
            "level": "二级",
            "check_func": "_check_security_policy",
        },
        
        # === 安全管理机构 ===
        {
            "id": "SEC-ORG-001",
            "category": "安全管理机构",
            "name": "岗位设置",
            "description": "应设立网络安全管理工作的职能部门，设立安全主管、安全管理各个方面的负责人岗位",
            "requirement": "明确安全责任人，建立安全组织",
            "level": "二级",
            "check_func": "_check_organization",
        },
        
        # === 安全运维管理 ===
        {
            "id": "SEC-OPS-001",
            "category": "安全运维管理",
            "name": "漏洞和风险管理",
            "description": "应采取必要的措施识别安全漏洞和隐患，对发现的安全漏洞和隐患及时进行修补",
            "requirement": "定期漏洞扫描，及时修复漏洞",
            "level": "二级",
            "check_func": "_check_vulnerability_management",
        },
        {
            "id": "SEC-OPS-002",
            "category": "安全运维管理",
            "name": "备份与恢复管理",
            "description": "应识别需要定期备份的重要业务信息、系统数据及软件系统等",
            "requirement": "定期备份配置和数据，测试恢复流程",
            "level": "二级",
            "check_func": "_check_backup_management",
        },
        {
            "id": "SEC-OPS-003",
            "category": "安全运维管理",
            "name": "应急处置",
            "description": "应报告所发现的安全弱点和可疑事件",
            "requirement": "建立应急响应机制，及时报告安全事件",
            "level": "二级",
            "check_func": "_check_incident_response",
        },
    ]
    
    def __init__(self, target_level: str = "二级"):
        self.target_level = target_level
        self.config_path = os.path.expanduser("~/.openclaw/openclaw.json")
    
    def run_compliance_check(self) -> ComplianceReport:
        """
        执行合规检查
        
        Returns:
            合规报告
        """
        checks = []
        
        for check_def in self.CHECKS:
            # 检查是否适用于目标级别
            if not self._is_level_applicable(check_def["level"], self.target_level):
                continue
            
            # 执行检查
            check_func = getattr(self, check_def["check_func"])
            result = check_func()
            
            check = ComplianceCheck(
                id=check_def["id"],
                category=check_def["category"],
                name=check_def["name"],
                description=check_def["description"],
                requirement=check_def["requirement"],
                level=check_def["level"],
                status=result["status"],
                evidence=result.get("evidence", ""),
                fix_suggestion=result.get("fix_suggestion", ""),
                reference=result.get("reference", ""),
            )
            
            checks.append(check)
        
        # 统计
        passed = len([c for c in checks if c.status == CheckStatus.PASS.value])
        failed = len([c for c in checks if c.status == CheckStatus.FAIL.value])
        partial = len([c for c in checks if c.status == CheckStatus.PARTIAL.value])
        not_applicable = len([c for c in checks if c.status == CheckStatus.NOT_APPLICABLE.value])
        manual = len([c for c in checks if c.status == CheckStatus.MANUAL.value])
        
        applicable = passed + failed + partial
        compliance_rate = (passed / applicable * 100) if applicable > 0 else 100
        
        # 差距分析
        gaps = [f"{c.id}: {c.name}" for c in checks if c.status == CheckStatus.FAIL.value]
        
        # 建议
        recommendations = self._generate_recommendations(checks)
        
        return ComplianceReport(
            level=self.target_level,
            total_checks=len(checks),
            passed=passed,
            failed=failed,
            partial=partial,
            not_applicable=not_applicable,
            manual=manual,
            compliance_rate=compliance_rate,
            checks=checks,
            gaps=gaps,
            recommendations=recommendations,
        )
    
    # --- 具体检查方法 ---
    
    def _check_identity_auth(self) -> Dict[str, Any]:
        """检查身份鉴别"""
        cfg = self._load_config()
        auth = cfg.get("gateway", {}).get("auth", {})
        
        has_token = bool(auth.get("token"))
        has_password = bool(auth.get("password"))
        
        if has_token or has_password:
            return {
                "status": CheckStatus.PASS.value,
                "evidence": "已配置认证机制",
            }
        
        return {
            "status": CheckStatus.FAIL.value,
            "evidence": "未配置任何认证",
            "fix_suggestion": "配置 gateway.auth.token 启用身份认证",
        }
    
    def _check_access_control(self) -> Dict[str, Any]:
        """检查访问控制"""
        cfg = self._load_config()
        
        # 检查是否有访问控制配置
        cors = cfg.get("gateway", {}).get("cors", {})
        rate_limit = cfg.get("gateway", {}).get("rateLimit")
        
        if cors or rate_limit:
            return {
                "status": CheckStatus.PASS.value,
                "evidence": "已配置访问控制机制",
            }
        
        return {
            "status": CheckStatus.PARTIAL.value,
            "evidence": "访问控制配置不完整",
            "fix_suggestion": "配置 CORS 和速率限制",
        }
    
    def _check_security_audit(self) -> Dict[str, Any]:
        """检查安全审计"""
        cfg = self._load_config()
        logging = cfg.get("logging", {})
        
        if logging.get("level") in ["info", "debug"] and logging.get("audit", False):
            return {
                "status": CheckStatus.PASS.value,
                "evidence": "已启用审计日志",
            }
        
        return {
            "status": CheckStatus.FAIL.value,
            "evidence": "审计日志未完全启用",
            "fix_suggestion": "设置 logging.level 为 info 并启用 logging.audit",
        }
    
    def _check_data_integrity(self) -> Dict[str, Any]:
        """检查数据完整性"""
        # 简化检查：检查是否有 HTTPS
        return {
            "status": CheckStatus.MANUAL.value,
            "evidence": "需人工确认是否使用 HTTPS/TLS",
            "fix_suggestion": "确保所有通信使用 HTTPS",
        }
    
    def _check_data_confidentiality(self) -> Dict[str, Any]:
        """检查数据保密性"""
        cfg = self._load_config()
        providers = cfg.get("models", {}).get("providers", {})
        
        plaintext_keys = []
        for name, config in providers.items():
            api_key = config.get("apiKey", "")
            if api_key and not api_key.startswith("$"):
                plaintext_keys.append(name)
        
        if not plaintext_keys:
            return {
                "status": CheckStatus.PASS.value,
                "evidence": "敏感数据已加密或使用环境变量",
            }
        
        return {
            "status": CheckStatus.FAIL.value,
            "evidence": f"{len(plaintext_keys)} 个 API Key 明文存储",
            "fix_suggestion": "将 API Key 迁移到环境变量",
        }
    
    def _check_personal_info_protection(self) -> Dict[str, Any]:
        """检查个人信息保护"""
        # 简化：OpenClaw 本身不收集个人信息
        return {
            "status": CheckStatus.PASS.value,
            "evidence": "系统不收集用户个人信息",
        }
    
    def _check_boundary_protection(self) -> Dict[str, Any]:
        """检查边界防护"""
        cfg = self._load_config()
        bind = cfg.get("gateway", {}).get("bind", "auto")
        
        if bind in ("loopback", "127.0.0.1", "localhost"):
            return {
                "status": CheckStatus.PASS.value,
                "evidence": "Gateway 绑定到本地回环",
            }
        
        if bind in ("0.0.0.0", "lan"):
            return {
                "status": CheckStatus.FAIL.value,
                "evidence": f"Gateway 绑定到 {bind}，存在暴露风险",
                "fix_suggestion": "将 gateway.bind 设置为 loopback",
            }
        
        return {
            "status": CheckStatus.PARTIAL.value,
            "evidence": f"Gateway 绑定到 {bind}",
        }
    
    def _check_network_access_control(self) -> Dict[str, Any]:
        """检查网络访问控制"""
        cfg = self._load_config()
        cors = cfg.get("gateway", {}).get("cors", {})
        
        if cors.get("origin") and cors.get("origin") != "*":
            return {
                "status": CheckStatus.PASS.value,
                "evidence": "已配置 CORS 限制",
            }
        
        return {
            "status": CheckStatus.PARTIAL.value,
            "evidence": "CORS 配置不完整",
            "fix_suggestion": "配置具体的 CORS 来源",
        }
    
    def _check_intrusion_prevention(self) -> Dict[str, Any]:
        """检查入侵防范"""
        cfg = self._load_config()
        rate_limit = cfg.get("gateway", {}).get("rateLimit")
        
        if rate_limit:
            return {
                "status": CheckStatus.PASS.value,
                "evidence": "已启用速率限制",
            }
        
        return {
            "status": CheckStatus.FAIL.value,
            "evidence": "未启用速率限制",
            "fix_suggestion": "配置 gateway.rateLimit 防止暴力破解",
        }
    
    def _check_communication_security(self) -> Dict[str, Any]:
        """检查通信安全"""
        return {
            "status": CheckStatus.MANUAL.value,
            "evidence": "需人工确认是否使用 HTTPS",
            "fix_suggestion": "确保使用 HTTPS/TLS 加密通信",
        }
    
    def _check_system_management(self) -> Dict[str, Any]:
        """检查系统管理"""
        cfg = self._load_config()
        
        # 检查是否有管理认证
        auth = cfg.get("gateway", {}).get("auth", {})
        if auth.get("token") or auth.get("password"):
            return {
                "status": CheckStatus.PASS.value,
                "evidence": "管理操作需要认证",
            }
        
        return {
            "status": CheckStatus.FAIL.value,
            "evidence": "管理操作未设置认证",
        }
    
    def _check_centralized_control(self) -> Dict[str, Any]:
        """检查集中管控"""
        # 简化：检查是否有日志目录
        logs_dir = os.path.expanduser("~/.openclaw/logs")
        if os.path.exists(logs_dir):
            return {
                "status": CheckStatus.PASS.value,
                "evidence": "日志集中存储",
            }
        
        return {
            "status": CheckStatus.PARTIAL.value,
            "evidence": "日志管理需完善",
        }
    
    def _check_security_policy(self) -> Dict[str, Any]:
        """检查安全策略"""
        # 检查是否有安全相关文档
        security_files = [
            "SECURITY.md",
            "CODE_OF_CONDUCT.md",
        ]
        
        found = [f for f in security_files if os.path.exists(f)]
        
        if found:
            return {
                "status": CheckStatus.PASS.value,
                "evidence": f"发现安全文档: {', '.join(found)}",
            }
        
        return {
            "status": CheckStatus.MANUAL.value,
            "evidence": "需人工确认安全策略文档",
        }
    
    def _check_organization(self) -> Dict[str, Any]:
        """检查组织机构"""
        return {
            "status": CheckStatus.MANUAL.value,
            "evidence": "需人工确认安全组织架构",
        }
    
    def _check_vulnerability_management(self) -> Dict[str, Any]:
        """检查漏洞管理"""
        # 检查是否有漏洞监控
        monitor_file = os.path.expanduser("~/.openclaw/security/vuln_monitor.json")
        
        if os.path.exists(monitor_file):
            return {
                "status": CheckStatus.PASS.value,
                "evidence": "已启用漏洞监控",
            }
        
        return {
            "status": CheckStatus.FAIL.value,
            "evidence": "未启用漏洞监控",
            "fix_suggestion": "启用实时漏洞监控",
        }
    
    def _check_backup_management(self) -> Dict[str, Any]:
        """检查备份管理"""
        backup_dir = os.path.expanduser("~/.openclaw/backups")
        
        if os.path.exists(backup_dir):
            backups = os.listdir(backup_dir)
            if backups:
                return {
                    "status": CheckStatus.PASS.value,
                    "evidence": f"发现 {len(backups)} 个备份文件",
                }
        
        return {
            "status": CheckStatus.FAIL.value,
            "evidence": "未找到备份文件",
            "fix_suggestion": "定期备份配置文件",
        }
    
    def _check_incident_response(self) -> Dict[str, Any]:
        """检查应急响应"""
        # 检查是否有安全事件记录
        events_file = os.path.expanduser("~/.openclaw/security/security_events.json")
        
        if os.path.exists(events_file):
            return {
                "status": CheckStatus.PASS.value,
                "evidence": "已启用安全事件监控",
            }
        
        return {
            "status": CheckStatus.PARTIAL.value,
            "evidence": "安全事件监控需完善",
        }
    
    # --- 辅助方法 ---
    
    def _is_level_applicable(self, check_level: str, target_level: str) -> bool:
        """检查检查项是否适用于目标级别"""
        levels = ["一级", "二级", "三级", "四级"]
        
        check_idx = levels.index(check_level) if check_level in levels else -1
        target_idx = levels.index(target_level) if target_level in levels else -1
        
        if check_idx == -1 or target_idx == -1:
            return True
        
        return check_idx <= target_idx
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            return {}
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    
    def _generate_recommendations(self, checks: List[ComplianceCheck]) -> List[str]:
        """生成合规建议"""
        recommendations = []
        
        failed_checks = [c for c in checks if c.status == CheckStatus.FAIL.value]
        
        if not failed_checks:
            recommendations.append("恭喜！当前配置符合等保 2.0 基本要求")
            return recommendations
        
        # 按类别分组
        by_category = {}
        for check in failed_checks:
            if check.category not in by_category:
                by_category[check.category] = []
            by_category[check.category].append(check)
        
        # 生成建议
        for category, checks in by_category.items():
            recommendations.append(
                f"【{category}】有 {len(checks)} 项不合规，建议优先整改"
            )
        
        # 具体建议
        critical_fixes = [
            c for c in failed_checks
            if c.id in ["SEC-COMP-001", "SEC-COMP-003", "SEC-BOUND-001"]
        ]
        
        if critical_fixes:
            recommendations.append(
                f"优先修复 {len(critical_fixes)} 项关键控制点：" +
                ", ".join([c.name for c in critical_fixes])
            )
        
        return recommendations
    
    # --- 报告生成 ---
    
    def generate_compliance_report(self) -> Dict[str, Any]:
        """生成合规报告"""
        report = self.run_compliance_check()
        
        return {
            "generated_at": datetime.now().isoformat(),
            "target_level": report.level,
            "summary": {
                "total_checks": report.total_checks,
                "passed": report.passed,
                "failed": report.failed,
                "partial": report.partial,
                "not_applicable": report.not_applicable,
                "manual": report.manual,
                "compliance_rate": round(report.compliance_rate, 2),
            },
            "gaps": report.gaps,
            "recommendations": report.recommendations,
            "details": [
                {
                    "id": c.id,
                    "category": c.category,
                    "name": c.name,
                    "status": c.status,
                    "evidence": c.evidence,
                    "fix_suggestion": c.fix_suggestion,
                }
                for c in report.checks
            ],
        }


# --- 便捷函数 ---

def check_compliance(level: str = "二级") -> ComplianceReport:
    """便捷函数：执行合规检查"""
    checker = ComplianceChecker(target_level=level)
    return checker.run_compliance_check()


def get_compliance_report(level: str = "二级") -> Dict[str, Any]:
    """便捷函数：获取合规报告"""
    checker = ComplianceChecker(target_level=level)
    return checker.generate_compliance_report()


def get_compliance_gap_analysis(level: str = "二级") -> List[str]:
    """便捷函数：获取合规差距分析"""
    report = check_compliance(level)
    return report.gaps
