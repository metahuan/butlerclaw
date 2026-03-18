from __future__ import annotations

import urllib.request

from ..models import (
    DiagnosticCategory,
    DiagnosticCheck,
    DiagnosticResult,
    DiagnosticSeverity,
    DiagnosticStatus,
)


class NpmRegistryConnectivityCheck:
    """
    检查到 npm registry 的基础网络连通性。
    """

    id = "network.npm_registry"
    name = "npm registry 连通性"
    category = DiagnosticCategory.NETWORK
    severity = DiagnosticSeverity.WARN

    def run(self) -> DiagnosticResult:
        url = "https://registry.npmjs.org"
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                code = getattr(resp, "status", None)
        except Exception as e:
            return DiagnosticResult(
                id=self.id,
                name=self.name,
                category=self.category,
                severity=self.severity,
                status=DiagnosticStatus.WARN,
                message="访问 npm registry 失败，可能影响安装/更新。",
                details=str(e),
            )

        msg = f"可以访问 npm registry（状态码: {code}）。"
        return DiagnosticResult(
            id=self.id,
            name=self.name,
            category=self.category,
            severity=self.severity,
            status=DiagnosticStatus.PASS,
            message=msg,
        )

