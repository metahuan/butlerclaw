from typing import List

from .models import VulnerabilityHit
from .vulnerability_db import get_vulnerabilities


class VulnerabilityPatcher:
    """
    漏洞扫描与修复建议（最小实现版）。

    当前实现仅返回内置漏洞库条目，未真正比对本机环境。
    """

    def scan(self) -> List[VulnerabilityHit]:
        """
        扫描并返回命中的漏洞列表。

        目前直接返回漏洞库中的所有条目，用于 UI 集成演示。
        """
        return list(get_vulnerabilities())

