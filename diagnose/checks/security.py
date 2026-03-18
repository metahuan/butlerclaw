from __future__ import annotations

import json
import os
import stat
import sys

from ..models import (
    DiagnosticCategory,
    DiagnosticCheck,
    DiagnosticGroup,
    DiagnosticResult,
    DiagnosticSeverity,
    DiagnosticStatus,
)

CONFIG_DIR = os.path.expanduser("~/.openclaw")
CONFIG_PATH = os.path.join(CONFIG_DIR, "openclaw.json")
LOGS_DIR = os.path.join(CONFIG_DIR, "logs")


class SecurityPermissionCheck:
    """
    检查配置目录 / 配置文件 / 日志目录的基础权限与敏感信息风险。
    """

    id = "security.permissions"
    name = "配置与日志安全性"
    category = DiagnosticCategory.SECURITY
    group = DiagnosticGroup.STATE
    severity = DiagnosticSeverity.WARN

    def run(self) -> DiagnosticResult:
        messages: list[str] = []

        if sys.platform != "win32":
            # 检查目录权限
            if os.path.isdir(CONFIG_DIR):
                mode = os.stat(CONFIG_DIR).st_mode
                if mode & (stat.S_IRWXO | stat.S_IRWXG):
                    messages.append("⚠️ 配置目录权限较宽，其他用户可能访问，建议 chmod 700。")
                else:
                    messages.append("✅ 配置目录权限看起来较为严格。")

            # 检查配置文件权限
            if os.path.isfile(CONFIG_PATH):
                mode = os.stat(CONFIG_PATH).st_mode
                if mode & (stat.S_IRWXO | stat.S_IRWXG):
                    messages.append("⚠️ 配置文件可能被其他用户读取，建议 chmod 600。")
                else:
                    messages.append("✅ 配置文件权限较为严格。")

            # 检查日志目录
            if os.path.isdir(LOGS_DIR):
                mode = os.stat(LOGS_DIR).st_mode
                if mode & (stat.S_IRWXO | stat.S_IRWXG):
                    messages.append("⚠️ 日志目录其他用户可访问，建议收紧权限。")
                else:
                    messages.append("✅ 日志目录权限较为严格。")
        else:
            messages.append("ℹ️ Windows 下不检查文件权限（可关注配置文件与 API Key 的安全）。")

        # 检查配置中是否含有 API Key
        if os.path.isfile(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                providers = (data.get("models") or {}).get("providers") or {}
                has_key = any(
                    isinstance(c, dict) and (c.get("apiKey") or "").strip()
                    for c in providers.values()
                )
                if has_key:
                    messages.append(
                        "⚠️ 配置中含 API Key，请勿将 openclaw.json 分享或上传到公开位置。"
                    )
            except Exception:
                # 安全检查失败不终止整体诊断
                messages.append("⚠️ 读取配置以检查 API Key 时发生异常。")

        if not messages:
            messages.append("未发现明显的配置或日志安全风险。")

        # 只要有⚠️信息，就按 WARN 处理
        status = (
            DiagnosticStatus.WARN
            if any("⚠️" in m for m in messages)
            else DiagnosticStatus.PASS
        )

        return DiagnosticResult(
            id=self.id,
            name=self.name,
            category=self.category,
            group=self.group,
            severity=self.severity,
            status=status,
            message="\n".join(messages),
        )

