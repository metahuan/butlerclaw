from __future__ import annotations

from collections import defaultdict
from typing import Iterable, List

from ..models import DiagnosticCategory, DiagnosticResult, DiagnosticStatus


STATUS_ICON = {
    DiagnosticStatus.PASS: "✅",
    DiagnosticStatus.WARN: "⚠️",
    DiagnosticStatus.FAIL: "❌",
}


CATEGORY_LABEL = {
    DiagnosticCategory.ENV: "环境",
    DiagnosticCategory.CLI: "OpenClaw CLI",
    DiagnosticCategory.CONFIG: "配置与模型",
    DiagnosticCategory.NETWORK: "网络连通性",
    DiagnosticCategory.SECURITY: "安全",
    DiagnosticCategory.SKILLS: "技能与插件",
    DiagnosticCategory.PERFORMANCE: "性能与资源",
    DiagnosticCategory.BUGS: "常见问题与潜在 Bug",
}


def render_text_report(results: Iterable[DiagnosticResult]) -> str:
    """
    将一组诊断结果渲染为分组文本报告。
    """
    grouped: dict[DiagnosticCategory, List[DiagnosticResult]] = defaultdict(list)
    for r in results:
        grouped[r.category].append(r)

    lines: List[str] = []
    lines.append("=== OpenClaw 环境诊断 ===")

    # 固定按分类顺序输出
    order = [
        DiagnosticCategory.ENV,
        DiagnosticCategory.CLI,
        DiagnosticCategory.CONFIG,
        DiagnosticCategory.NETWORK,
        DiagnosticCategory.SECURITY,
        DiagnosticCategory.PERFORMANCE,
        DiagnosticCategory.SKILLS,
        DiagnosticCategory.BUGS,
    ]

    for cat in order:
        cat_results = grouped.get(cat, [])
        if not cat_results:
            continue
        label = CATEGORY_LABEL.get(cat, cat.value)
        lines.append("")
        lines.append(f"[{label}]")
        for res in cat_results:
            icon = STATUS_ICON.get(res.status, "•")
            lines.append(f"  {icon} {res.name}: {res.message}")

    lines.append("")
    lines.append("=== 诊断完成 ===")
    return "\n".join(lines)

