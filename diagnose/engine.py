"""
diagnose.engine

诊断引擎核心：负责注册与调度各类 DiagnosticCheck。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from .models import (
    DiagnosticCategory,
    DiagnosticCheck,
    DiagnosticResult,
)


@dataclass
class DiagnosticEngine:
    """
    诊断引擎：管理并执行一组诊断检查项。

    - 支持按分类注册 / 执行检查。
    - 对 UI 保持无依赖，仅返回结构化的 DiagnosticResult 列表。
    """

    _checks: Dict[str, DiagnosticCheck] = field(default_factory=dict)

    def register_check(self, check: DiagnosticCheck) -> None:
        """注册单个检查项，使用其 id 作为键（后注册的同 id 会覆盖之前的）。"""
        self._checks[check.id] = check

    def register_checks(self, checks: Sequence[DiagnosticCheck]) -> None:
        """批量注册检查项。"""
        for c in checks:
            self.register_check(c)

    def get_check(self, check_id: str) -> Optional[DiagnosticCheck]:
        """按 id 获取已注册的检查项。"""
        return self._checks.get(check_id)

    def get_checks(self) -> List[DiagnosticCheck]:
        """返回当前所有注册的检查项列表。"""
        return list(self._checks.values())

    def get_checks_by_category(self, category: DiagnosticCategory) -> List[DiagnosticCheck]:
        """按分类获取检查项。"""
        return [c for c in self._checks.values() if c.category == category]

    def run_all(self) -> List[DiagnosticResult]:
        """
        顺序执行所有已注册检查。

        当前实现为串行执行，便于与 Tk 线程模型兼容；
        若未来需要并行执行，可在此处扩展并发逻辑。
        """
        results: List[DiagnosticResult] = []
        for check in self._checks.values():
            try:
                res = check.run()
            except Exception as e:  # 防御性：单个检查异常不影响整体
                from .models import DiagnosticSeverity, DiagnosticStatus

                res = DiagnosticResult(
                    id=check.id,
                    name=check.name,
                    category=check.category,
                    severity=DiagnosticSeverity.ERROR,
                    status=DiagnosticStatus.FAIL,
                    message=f"运行检查时出现异常：{e}",
                    details="该异常来自诊断引擎内部，请在反馈时附上完整日志。",
                )
            results.append(res)
        return results

    def run_by_category(self, category: DiagnosticCategory) -> List[DiagnosticResult]:
        """仅执行指定分类下的检查。"""
        return [c.run() for c in self.get_checks_by_category(category)]

