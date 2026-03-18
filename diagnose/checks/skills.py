from __future__ import annotations

from typing import Any, Dict, List

from skills_manager import SkillManager

from ..models import (
    DiagnosticCategory,
    DiagnosticGroup,
    DiagnosticResult,
    DiagnosticSeverity,
    DiagnosticStatus,
)


class SkillsHealthCheck:
    """
    使用 SkillManager 检查已安装技能的基本健康状态。

    - 统计已安装技能数量。
    - 标出有可用更新的技能数量。
    - 如有异常（获取列表失败等），返回失败状态。
    """

    id = "skills.health"
    name = "技能与插件健康情况"
    category = DiagnosticCategory.SKILLS
    group = DiagnosticGroup.TOOLS
    severity = DiagnosticSeverity.WARN

    def run(self) -> DiagnosticResult:
        try:
            manager = SkillManager()
            skills: List[Dict[str, Any]] = manager.get_skills(force_refresh=False)
        except Exception as e:
            return DiagnosticResult(
                id=self.id,
                name=self.name,
                category=self.category,
                group=self.group,
                severity=self.severity,
                status=DiagnosticStatus.FAIL,
                message="获取技能列表时出现异常，请检查 OpenClaw CLI 与网络。",
                details=str(e),
            )

        installed = [s for s in skills if s.get("installed")]
        updatable = [s for s in installed if s.get("has_update")]

        if not installed:
            return DiagnosticResult(
                id=self.id,
                name=self.name,
                category=self.category,
                group=self.group,
                severity=self.severity,
                status=DiagnosticStatus.WARN,
                message="当前未检测到已安装技能，可在技能管理中安装常用技能。",
            )

        if updatable:
            msg = (
                f"检测到 {len(installed)} 个已安装技能，其中 {len(updatable)} 个有可用更新，"
                "建议在技能管理中更新以获得最新能力。"
            )
            status = DiagnosticStatus.WARN
        else:
            msg = f"检测到 {len(installed)} 个已安装技能，均为最新版本。"
            status = DiagnosticStatus.PASS

        return DiagnosticResult(
            id=self.id,
            name=self.name,
            category=self.category,
            group=self.group,
            severity=self.severity,
            status=status,
            message=msg,
        )

