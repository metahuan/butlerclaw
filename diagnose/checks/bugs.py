from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Dict, List

from ..models import (
    DiagnosticCategory,
    DiagnosticGroup,
    DiagnosticResult,
    DiagnosticSeverity,
    DiagnosticStatus,
)

CONFIG_DIR = os.path.expanduser("~/.openclaw")
CONFIG_PATH = os.path.join(CONFIG_DIR, "openclaw.json")


class OpenClawBugHintsCheck:
    """
    OpenClaw 常见问题与潜在 Bug 诊断（总结性检查）。

    结合配置、Node 与 CLI 等信息，给出一些高层次的“容易踩坑”的提示：
    - 完全没有配置文件时的影响
    - 配置文件解析错误 / 结构异常
    - models.providers 缺失或为空
    - Node 主版本过低
    - CLI 缺失或版本过旧（在前面检查失败的情况下再次提醒）
    """

    id = "bugs.common_hints"
    name = "OpenClaw 常见问题诊断"
    category = DiagnosticCategory.BUGS
    group = DiagnosticGroup.BUGS
    severity = DiagnosticSeverity.WARN

    def _load_config(self) -> Dict[str, Any] | None:
        if not os.path.isfile(CONFIG_PATH):
            return None
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"__parse_error__": True}

    def _get_node_major(self) -> int | None:
        try:
            r = subprocess.run(
                "node --version",
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=5,
            )
            if r.returncode != 0 or not (r.stdout or "").strip():
                return None
            ver = (r.stdout or "").strip().lstrip("v")
            major = int(ver.split(".")[0])
            return major
        except Exception:
            return None

    def _has_cli(self) -> bool:
        try:
            r = subprocess.run(
                "openclaw --version",
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=5,
            )
            return r.returncode == 0 and bool((r.stdout or "").strip())
        except Exception:
            return False

    def run(self) -> DiagnosticResult:
        hints: List[str] = []
        status = DiagnosticStatus.PASS

        # 1. 配置文件与 models.providers 相关问题
        cfg = self._load_config()
        if cfg is None:
            hints.append(
                "⚠️ 未找到 openclaw.json："
                "首次使用前需要通过安装向导或手动创建配置，否则大部分功能将不可用。"
            )
            status = DiagnosticStatus.WARN
        elif cfg.get("__parse_error__"):
            hints.append(
                "❌ openclaw.json 无法被正常解析为 JSON："
                "这会导致 OpenClaw 启动或调用配置相关功能时直接报错，"
                "建议备份后重新生成或修复该文件。"
            )
            status = DiagnosticStatus.FAIL
        else:
            models = cfg.get("models")
            providers = (models or {}).get("providers") if isinstance(models, dict) else None
            if models is None:
                hints.append(
                    "⚠️ 配置中缺少 models 字段："
                    "这可能导致模型相关功能无法正常工作。"
                )
                status = DiagnosticStatus.WARN
            elif not isinstance(models, dict):
                hints.append(
                    "❌ models 字段应为对象："
                    "当前类型异常，可能导致运行时抛出类型错误。"
                )
                status = DiagnosticStatus.FAIL
            elif providers is None:
                hints.append(
                    "⚠️ 配置中缺少 models.providers："
                    "将无法找到可用的模型提供商。"
                )
                status = max(status, DiagnosticStatus.WARN, key=lambda s: ["pass", "warn", "fail"].index(s.value))  # type: ignore[arg-type]
            elif not isinstance(providers, dict):
                hints.append(
                    "❌ models.providers 应为对象："
                    "结构异常会直接导致部分功能报错。"
                )
                status = DiagnosticStatus.FAIL
            else:
                if not providers:
                    hints.append(
                        "⚠️ models.providers 为空："
                        "尚未配置任何模型提供商，OpenClaw 将无法调用大模型。"
                    )
                    status = DiagnosticStatus.WARN

        # 2. Node 主版本过低
        node_major = self._get_node_major()
        if node_major is None:
            hints.append(
                "⚠️ 未能确认 Node.js 版本："
                "如果你在使用 OpenClaw 时遇到奇怪的兼容性问题，"
                "请确保已安装 Node 18 及以上版本。"
            )
            status = max(status, DiagnosticStatus.WARN, key=lambda s: ["pass", "warn", "fail"].index(s.value))  # type: ignore[arg-type]
        elif node_major < 18:
            hints.append(
                f"⚠️ 当前 Node 主版本为 {node_major}："
                "低于推荐的 Node 18 版本，可能在依赖安装、网络请求等方面出现不兼容问题。"
            )
            status = DiagnosticStatus.WARN

        # 3. CLI 缺失或潜在问题
        if not self._has_cli():
            hints.append(
                "❌ 未检测到 openclaw CLI："
                "请通过 npm 或安装向导安装 openclaw，否则命令行相关功能无法使用。"
            )
            status = DiagnosticStatus.FAIL

        if not hints:
            hints.append(
                "未发现明显的配置或环境层面的常见问题，如果仍然遇到 Bug，"
                "建议在反馈时附上诊断报告与最近的日志文件。"
            )

        return DiagnosticResult(
            id=self.id,
            name=self.name,
            category=self.category,
            group=self.group,
            severity=self.severity,
            status=status,
            message="\n".join(hints),
        )

