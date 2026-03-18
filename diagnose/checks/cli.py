from __future__ import annotations

import subprocess

from ..models import (
    DiagnosticCategory,
    DiagnosticCheck,
    DiagnosticGroup,
    DiagnosticResult,
    DiagnosticSeverity,
    DiagnosticStatus,
)


class OpenClawCliCheck:
    """
    检查 OpenClaw CLI 是否可用，并简单对比当前版本与 npm 最新版本。
    """

    id = "cli.openclaw"
    name = "OpenClaw CLI"
    category = DiagnosticCategory.CLI
    group = DiagnosticGroup.TOOLS
    severity = DiagnosticSeverity.ERROR

    def _parse_version(self, s: str) -> tuple[int, ...]:
        s = (s or "").strip().lstrip("v")
        parts = []
        for p in s.split("."):
            try:
                parts.append(int(p))
            except ValueError:
                parts.append(0)
        return tuple(parts) if parts else (0,)

    def run(self) -> DiagnosticResult:
        try:
            r = subprocess.run(
                "openclaw --version",
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=8,
            )
        except Exception as e:
            return DiagnosticResult(
                id=self.id,
                name=self.name,
                category=self.category,
                group=self.group,
                severity=self.severity,
                status=DiagnosticStatus.FAIL,
                message="检测 OpenClaw CLI 时出现异常。",
                details=str(e),
            )

        if not (r.returncode == 0 and (r.stdout or "").strip()):
            details = ""
            if r.stdout:
                details += f"stdout:\n{r.stdout}\n"
            if r.stderr:
                details += f"stderr:\n{r.stderr}\n"
            return DiagnosticResult(
                id=self.id,
                name=self.name,
                category=self.category,
                group=self.group,
                severity=self.severity,
                status=DiagnosticStatus.FAIL,
                message="未检测到 openclaw 命令，请通过安装向导或 npm 安装。",
                details=details.strip(),
            )

        cur_ver = (r.stdout or "").strip()

        # 默认认为版本状态通过；若能成功从 npm 获取最新版本，再做比较给出提示
        status = DiagnosticStatus.PASS
        message = f"已检测到 OpenClaw CLI: {cur_ver}"
        details = f"`openclaw --version` 输出: {cur_ver}"

        try:
            r2 = subprocess.run(
                "npm view openclaw version",
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=10,
            )
            if r2.returncode == 0 and (r2.stdout or "").strip():
                latest = (r2.stdout or "").strip()
                cur_tuple = self._parse_version(cur_ver)
                latest_tuple = self._parse_version(latest)
                details += f"\nnpm 最新版本: {latest}"
                if latest_tuple > cur_tuple:
                    status = DiagnosticStatus.WARN
                    message = (
                        f"已检测到 OpenClaw CLI: {cur_ver}，npm 上有更新版本 {latest}，"
                        "可在版本管理或终端中更新。"
                    )
        except Exception:
            # 获取最新版本失败不视为致命错误，仅略过
            pass

        return DiagnosticResult(
            id=self.id,
            name=self.name,
            category=self.category,
            group=self.group,
            severity=self.severity,
            status=status,
            message=message,
            details=details,
        )


