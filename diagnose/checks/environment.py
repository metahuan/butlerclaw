from __future__ import annotations

import subprocess
from typing import Optional

from ..models import (
    DiagnosticCategory,
    DiagnosticCheck,
    DiagnosticGroup,
    DiagnosticResult,
    DiagnosticSeverity,
    DiagnosticStatus,
)


class NodeVersionCheck:
    """
    检查 Node.js 是否可用及版本是否满足建议要求。
    """

    id = "env.node"
    name = "Node.js 环境"
    category = DiagnosticCategory.ENV
    group = DiagnosticGroup.ENV
    severity = DiagnosticSeverity.ERROR

    def _run_node_version(self) -> Optional[str]:
        try:
            r = subprocess.run(
                "node --version",
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=8,
            )
            if r.returncode == 0 and (r.stdout or "").strip():
                return (r.stdout or "").strip()
            return None
        except Exception:
            return None

    def run(self) -> DiagnosticResult:
        ver = self._run_node_version()
        if not ver:
            return DiagnosticResult(
                id=self.id,
                name=self.name,
                category=self.category,
                severity=self.severity,
                status=DiagnosticStatus.FAIL,
                message="未检测到 node 命令，请检查是否已安装 Node.js。",
                details="执行 `node --version` 失败或无输出。",
            )

        # 简单主版本判断
        major = 0
        clean = ver.strip().lstrip("v")
        try:
            major = int(clean.split(".")[0])
        except Exception:
            pass

        if major and major < 18:
            status = DiagnosticStatus.WARN
            msg = f"已检测到 Node.js: {ver}，建议使用 Node 18+ 以获得更佳兼容性。"
        else:
            status = DiagnosticStatus.PASS
            msg = f"已检测到 Node.js: {ver}。"

        return DiagnosticResult(
            id=self.id,
            name=self.name,
            category=self.category,
            group=self.group,
            severity=self.severity,
            status=status,
            message=msg,
            details=f"`node --version` 输出: {ver}",
        )


class NpmCheck:
    """
    检查 npm 是否可用及版本信息。
    """

    id = "env.npm"
    name = "npm 环境"
    category = DiagnosticCategory.ENV
    group = DiagnosticGroup.ENV
    severity = DiagnosticSeverity.WARN

    def run(self) -> DiagnosticResult:
        try:
            r = subprocess.run(
                "npm --version",
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
                message="检测 npm 时出现异常。",
                details=str(e),
            )

        if r.returncode == 0 and (r.stdout or "").strip():
            ver = (r.stdout or "").strip()
            return DiagnosticResult(
                id=self.id,
                name=self.name,
                category=self.category,
                group=self.group,
                severity=self.severity,
                status=DiagnosticStatus.PASS,
                message=f"已检测到 npm: {ver}",
                details=f"`npm --version` 输出: {ver}",
            )

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
            message="未检测到 npm，请检查 Node.js 安装或环境变量。",
            details=details.strip(),
        )


class PathCheck:
    """
    检查 PATH 中是否可以找到 node / npm。
    """

    id = "env.path"
    name = "PATH 环境变量"
    category = DiagnosticCategory.ENV
    group = DiagnosticGroup.ENV
    severity = DiagnosticSeverity.WARN

    def run(self) -> DiagnosticResult:
        import shutil

        node_path = shutil.which("node")
        npm_path = shutil.which("npm")

        missing = []
        if not node_path:
            missing.append("node")
        if not npm_path:
            missing.append("npm")

        if not missing:
            msg = f"PATH 中可以找到 node（{node_path}）与 npm（{npm_path}）。"
            status = DiagnosticStatus.PASS
        else:
            msg = (
                f"PATH 中未找到: {', '.join(missing)}，"
                "可能导致命令无法在终端中正常调用。"
            )
            status = DiagnosticStatus.WARN

        details = f"node 路径: {node_path or '未找到'}\nnpm 路径: {npm_path or '未找到'}"

        return DiagnosticResult(
            id=self.id,
            name=self.name,
            category=self.category,
            group=self.group,
            severity=self.severity,
            status=status,
            message=msg,
            details=details,
        )

