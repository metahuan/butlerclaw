import os
from typing import List

from .models import SkillSecurityReport


class SkillSecurityScanner:
    """
    技能安全扫描器（最小实现版）。

    当前实现仅基于技能安装目录与简单规则做静态标记，
    主要用于 ButlerClaw UI 集成演示。
    """

    def __init__(self, skills_root: str | None = None) -> None:
        # 默认从 ~/.openclaw/skills 目录扫描
        self.skills_root = skills_root or os.path.expanduser("~/.openclaw/skills")

    def scan_all(self) -> List[SkillSecurityReport]:
        if not os.path.isdir(self.skills_root):
            return []

        reports: List[SkillSecurityReport] = []

        for name in sorted(os.listdir(self.skills_root)):
            path = os.path.join(self.skills_root, name)
            if not os.path.isdir(path):
                continue

            trust_level = self._infer_trust_level(name)
            is_suspicious = trust_level in ("suspicious",)

            reports.append(
                SkillSecurityReport(
                    id=name,
                    name=name,
                    trust_level=trust_level,
                    is_suspicious=is_suspicious,
                    permissions=None,
                    network_calls=None,
                    file_operations=None,
                )
            )

        return reports

    def _infer_trust_level(self, name: str) -> str:
        """
        极简版来源推断：
        - 带有 "official" / "openclaw" 关键字 => official
        - 带有 "github" / "git" => community
        - 其他 => unknown
        """
        lname = name.lower()
        if "official" in lname or "openclaw" in lname:
            return "official"
        if "github" in lname or "git" in lname:
            return "community"
        return "unknown"

