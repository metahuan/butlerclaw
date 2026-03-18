from __future__ import annotations

import os
import shutil

from ..models import (
    DiagnosticCategory,
    DiagnosticCheck,
    DiagnosticGroup,
    DiagnosticResult,
    DiagnosticSeverity,
    DiagnosticStatus,
)


class DiskSpaceCheck:
    """
    检查用户目录所在磁盘的剩余空间。
    """

    id = "performance.disk_space"
    name = "磁盘剩余空间"
    category = DiagnosticCategory.PERFORMANCE
    group = DiagnosticGroup.ENV
    severity = DiagnosticSeverity.WARN

    def run(self) -> DiagnosticResult:
        try:
            usage = shutil.disk_usage(os.path.expanduser("~"))
        except Exception as e:
            return DiagnosticResult(
                id=self.id,
                name=self.name,
                category=self.category,
                severity=self.severity,
                status=DiagnosticStatus.WARN,
                message="获取磁盘空间信息失败。",
                details=str(e),
            )

        free_gb = usage.free / (1024 ** 3)
        if free_gb < 2:
            status = DiagnosticStatus.WARN
            msg = f"剩余空间约 {free_gb:.1f} GB，建议至少保留 2GB 以上。"
        else:
            status = DiagnosticStatus.PASS
            msg = f"剩余空间约 {free_gb:.1f} GB。"

        return DiagnosticResult(
            id=self.id,
            name=self.name,
            category=self.category,
            group=self.group,
            severity=self.severity,
            status=status,
            message=msg,
        )

