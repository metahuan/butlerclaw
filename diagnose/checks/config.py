from __future__ import annotations

import json
import os
from typing import Any, Dict

from ..models import (
    DiagnosticCategory,
    DiagnosticCheck,
    DiagnosticGroup,
    DiagnosticResult,
    DiagnosticSeverity,
    DiagnosticStatus,
)

# 与 openclaw_assistant 中保持一致的默认配置路径
CONFIG_DIR = os.path.expanduser("~/.openclaw")
CONFIG_PATH = os.path.join(CONFIG_DIR, "openclaw.json")


class ConfigFileExistCheck:
    """
    检查 openclaw.json 配置文件是否存在。
    """

    id = "config.file_exist"
    name = "配置文件存在性"
    category = DiagnosticCategory.CONFIG
    group = DiagnosticGroup.CONFIG
    severity = DiagnosticSeverity.WARN

    def run(self) -> DiagnosticResult:
        if os.path.isfile(CONFIG_PATH):
            return DiagnosticResult(
                id=self.id,
                name=self.name,
                category=self.category,
                group=self.group,
                severity=self.severity,
                status=DiagnosticStatus.PASS,
                message=f"找到配置文件: {CONFIG_PATH}",
            )
        return DiagnosticResult(
            id=self.id,
            name=self.name,
            category=self.category,
            group=self.group,
            severity=self.severity,
            status=DiagnosticStatus.WARN,
            message=f"未找到配置文件: {CONFIG_PATH}",
        )


class ConfigJsonStructureCheck:
    """
    检查配置文件的 JSON 结构与 models.providers 部分。
    """

    id = "config.json_structure"
    name = "配置 JSON 结构"
    category = DiagnosticCategory.CONFIG
    group = DiagnosticGroup.CONFIG
    severity = DiagnosticSeverity.ERROR

    def run(self) -> DiagnosticResult:
        if not os.path.isfile(CONFIG_PATH):
            return DiagnosticResult(
                id=self.id,
                name=self.name,
                category=self.category,
                group=self.group,
                severity=self.severity,
                status=DiagnosticStatus.WARN,
                message="未找到配置文件，跳过结构检查。",
            )

        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data: Any = json.load(f)
        except json.JSONDecodeError as e:
            return DiagnosticResult(
                id=self.id,
                name=self.name,
                category=self.category,
                group=self.group,
                severity=self.severity,
                status=DiagnosticStatus.FAIL,
                message="配置文件 JSON 解析失败，可能导致程序报错。",
                details=str(e),
            )
        except Exception as e:
            return DiagnosticResult(
                id=self.id,
                name=self.name,
                category=self.category,
                group=self.group,
                severity=self.severity,
                status=DiagnosticStatus.FAIL,
                message="读取配置文件时发生异常。",
                details=str(e),
            )

        if not isinstance(data, dict):
            return DiagnosticResult(
                id=self.id,
                name=self.name,
                category=self.category,
                group=self.group,
                severity=self.severity,
                status=DiagnosticStatus.FAIL,
                message="配置文件根节点应为 JSON 对象，当前格式异常。",
            )

        models = data.get("models")
        if models is None:
            return DiagnosticResult(
                id=self.id,
                name=self.name,
                category=self.category,
                group=self.group,
                severity=self.severity,
                status=DiagnosticStatus.WARN,
                message="缺少 models 字段，可能导致模型相关功能报错。",
            )
        if not isinstance(models, dict):
            return DiagnosticResult(
                id=self.id,
                name=self.name,
                category=self.category,
                group=self.group,
                severity=self.severity,
                status=DiagnosticStatus.FAIL,
                message="models 字段应为对象，当前类型异常。",
            )

        providers = models.get("providers")
        if providers is None:
            return DiagnosticResult(
                id=self.id,
                name=self.name,
                category=self.category,
                group=self.group,
                severity=self.severity,
                status=DiagnosticStatus.WARN,
                message="缺少 models.providers，可能导致模型相关功能报错。",
            )
        if not isinstance(providers, dict):
            return DiagnosticResult(
                id=self.id,
                name=self.name,
                category=self.category,
                group=self.group,
                severity=self.severity,
                status=DiagnosticStatus.FAIL,
                message="models.providers 应为对象，当前类型异常。",
            )

        return DiagnosticResult(
            id=self.id,
            name=self.name,
            category=self.category,
            group=self.group,
            severity=self.severity,
            status=DiagnosticStatus.PASS,
            message="配置文件 JSON 结构与 models.providers 字段看起来正常。",
        )


class ConfigApiKeyCheck:
    """
    检查是否至少有一个模型提供商配置了 apiKey。
    """

    id = "config.api_key"
    name = "模型 API Key 配置"
    category = DiagnosticCategory.CONFIG
    group = DiagnosticGroup.MODELS
    severity = DiagnosticSeverity.WARN

    def run(self) -> DiagnosticResult:
        if not os.path.isfile(CONFIG_PATH):
            return DiagnosticResult(
                id=self.id,
                name=self.name,
                category=self.category,
                group=self.group,
                severity=self.severity,
                status=DiagnosticStatus.WARN,
                message="未找到配置文件，无法检查 API Key。",
            )

        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)
        except Exception as e:
            return DiagnosticResult(
                id=self.id,
                name=self.name,
                category=self.category,
                group=self.group,
                severity=self.severity,
                status=DiagnosticStatus.FAIL,
                message="读取配置文件时发生异常，无法检查 API Key。",
                details=str(e),
            )

        providers = (data.get("models") or {}).get("providers") or {}
        if not isinstance(providers, dict):
            return DiagnosticResult(
                id=self.id,
                name=self.name,
                category=self.category,
                group=self.group,
                severity=self.severity,
                status=DiagnosticStatus.FAIL,
                message="models.providers 结构异常，无法检查 API Key。",
            )

        has_any = False
        empty: list[str] = []
        for prov, cfg in providers.items():
            if isinstance(cfg, dict) and (cfg.get("apiKey") or "").strip():
                has_any = True
            else:
                empty.append(str(prov))

        if not has_any:
            return DiagnosticResult(
                id=self.id,
                name=self.name,
                category=self.category,
                group=self.group,
                severity=self.severity,
                status=DiagnosticStatus.WARN,
                message="未检测到任何 models.providers.*.apiKey，对话/模型功能将不可用。",
            )

        if empty:
            msg = f"已配置部分模型提供商的 apiKey，但以下提供商未配置：{', '.join(empty)}。"
        else:
            msg = "所有模型提供商均已配置 apiKey。"

        return DiagnosticResult(
            id=self.id,
            name=self.name,
            category=self.category,
            group=self.group,
            severity=self.severity,
            status=DiagnosticStatus.PASS,
            message=msg,
        )


class ConfigMigrationCheck:
    """
    检查配置中是否存在疑似旧版本字段，提示用户迁移到新的结构。

    示例：检测常见的旧字段（如 openaiApiKey 等），提醒迁移到 models.providers.xxx.apiKey。
    """

    id = "config.migration"
    name = "配置迁移与兼容性"
    category = DiagnosticCategory.CONFIG
    group = DiagnosticGroup.CONFIG
    severity = DiagnosticSeverity.WARN

    LEGACY_KEYS = [
        "openaiApiKey",
        "anthropicApiKey",
        "azureOpenaiApiKey",
        "model",
    ]

    def run(self) -> DiagnosticResult:
        if not os.path.isfile(CONFIG_PATH):
            return DiagnosticResult(
                id=self.id,
                name=self.name,
                category=self.category,
                group=self.group,
                severity=self.severity,
                status=DiagnosticStatus.WARN,
                message="未找到配置文件，跳过迁移检查。",
            )

        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)
        except Exception:
            return DiagnosticResult(
                id=self.id,
                name=self.name,
                category=self.category,
                group=self.group,
                severity=self.severity,
                status=DiagnosticStatus.WARN,
                message="配置文件无法解析，跳过旧字段迁移检查。",
            )

        if not isinstance(data, dict):
            return DiagnosticResult(
                id=self.id,
                name=self.name,
                category=self.category,
                group=self.group,
                severity=self.severity,
                status=DiagnosticStatus.WARN,
                message="配置根节点不是对象，跳过旧字段迁移检查。",
            )

        found = [k for k in self.LEGACY_KEYS if k in data]

        if not found:
            return DiagnosticResult(
                id=self.id,
                name=self.name,
                category=self.category,
                group=self.group,
                severity=self.severity,
                status=DiagnosticStatus.PASS,
                message="未检测到常见旧字段，配置结构看起来较为现代。",
            )

        msg = (
            f"检测到可能来自旧版本的配置字段: {', '.join(found)}。"
            " 建议将密钥与模型配置迁移到 models.providers.* 下，"
            "以获得更好的兼容性与未来支持。"
        )

        return DiagnosticResult(
            id=self.id,
            name=self.name,
            category=self.category,
            group=self.group,
            severity=self.severity,
            status=DiagnosticStatus.WARN,
            message=msg,
        )

