import os
import json
from datetime import datetime
from typing import Any, Dict, List

from .models import PermissionCheck, RiskLevel


class PermissionScanner:
    """
    OpenClaw 权限体检扫描器（最小实现版）。

    注意：当前实现仅做极简配置检查，主要用于 ButlerClaw UI 集成演示。
    """

    CONFIG_PATH = os.path.expanduser("~/.openclaw/openclaw.json")

    def scan(self) -> Dict[str, Any]:
        checks: List[PermissionCheck] = []

        checks.append(self._check_config_exists())
        checks.append(self._check_gateway_bind())
        checks.append(self._check_auth_config())

        return self._generate_report(checks)

    # --- 具体检查项 ---

    def _check_config_exists(self) -> PermissionCheck:
        if not os.path.exists(self.CONFIG_PATH):
            return PermissionCheck(
                name="配置文件存在性",
                level=RiskLevel.MEDIUM,
                message="未找到 openclaw.json 配置文件",
                details=f"期待路径: {self.CONFIG_PATH}",
                fix_suggestion="建议通过安装向导或 CLI 初始化生成配置文件。",
                auto_fixable=False,
            )

        return PermissionCheck(
            name="配置文件存在性",
            level=RiskLevel.SAFE,
            message="已检测到 openclaw.json 配置文件",
            details=f"路径: {self.CONFIG_PATH}",
        )

    def _check_gateway_bind(self) -> PermissionCheck:
        cfg = self._load_config()
        gateway = cfg.get("gateway", {}) if isinstance(cfg, dict) else {}
        bind = gateway.get("bind", "auto")

        if bind in ("0.0.0.0", "lan"):
            return PermissionCheck(
                name="Gateway 绑定模式",
                level=RiskLevel.CRITICAL,
                message=f"Gateway 绑定到 {bind}，可能存在公网暴露风险",
                details="当前配置允许局域网或公网访问 Gateway，可能导致未授权访问。",
                fix_suggestion="建议将 gateway.bind 改为 'loopback' 或仅通过安全隧道访问。",
                auto_fixable=False,
            )

        return PermissionCheck(
            name="Gateway 绑定模式",
            level=RiskLevel.SAFE,
            message=f"Gateway 绑定模式为 {bind}",
            details="未检测到明显公网暴露风险。",
        )

    def _check_auth_config(self) -> PermissionCheck:
        cfg = self._load_config()
        gateway = cfg.get("gateway", {}) if isinstance(cfg, dict) else {}
        auth = gateway.get("auth", {}) if isinstance(gateway, dict) else {}

        has_token = bool(auth.get("token"))
        has_password = bool(auth.get("password"))

        if not has_token and not has_password:
            return PermissionCheck(
                name="Gateway 认证配置",
                level=RiskLevel.CRITICAL,
                message="未配置任何认证信息，可能允许匿名访问。",
                details="gateway.auth.token 与 gateway.auth.password 均为空。",
                fix_suggestion="建议至少配置 gateway.auth.token，避免匿名访问。",
                auto_fixable=False,
            )

        return PermissionCheck(
            name="Gateway 认证配置",
            level=RiskLevel.SAFE,
            message="已配置 Gateway 认证信息",
            details=f"Token: {'已配置' if has_token else '未配置'}, Password: {'已配置' if has_password else '未配置'}",
        )

    # --- 工具方法 ---

    def _load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.CONFIG_PATH):
            return {}
        try:
            with open(self.CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _generate_report(self, checks: List[PermissionCheck]) -> Dict[str, Any]:
        # 简化版评分：有 CRITICAL => 0，有 HIGH => 40，有 MEDIUM => 70，否则 100
        levels = {c.level for c in checks}
        if RiskLevel.CRITICAL in levels:
            score = 0
        elif RiskLevel.HIGH in levels:
            score = 40
        elif RiskLevel.MEDIUM in levels:
            score = 70
        else:
            score = 100

        return {
            "score": score,
            "checks": checks,
            "timestamp": datetime.now().isoformat(),
        }

