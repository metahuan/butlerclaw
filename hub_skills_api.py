#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ButlerClaw Hub 技能 API 客户端

- 技能列表从运营平台云数据库 skills 集合读取（通过 Hub GET /api/skills）
- 安装时请求下载接口获取临时 URL，下载到本地后使用 OpenClaw 本地安装
"""

import os
import json
import urllib.request
import urllib.error
import urllib.parse
import tempfile
from typing import List, Dict, Optional, Tuple


def _get_hub_base_url() -> str:
    """从环境变量或本地配置读取 Hub 基础 URL"""
    url = os.environ.get("BUTLERCLAW_HUB_URL", "").strip()
    if url:
        return url.rstrip("/")
    config_path = os.path.join(os.path.expanduser("~/.openclaw"), "openclaw.json")
    if os.path.isfile(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            url = (cfg.get("hubBaseUrl") or cfg.get("hub_base_url") or "").strip()
            if url:
                return url.rstrip("/")
        except Exception:
            pass
    return ""


def get_skills(
    page: int = 1,
    size: int = 50,
    category: Optional[str] = None,
    sort: str = "downloads",
) -> Tuple[List[Dict], Dict]:
    """
    从 Hub 获取技能列表（对应云数据库 skills 集合）。

    Returns:
        (data, pagination): data 为技能列表，每项含 id/name/description/icon/category/downloads/rating/version/author 等；
        pagination 为 { page, size, total }。失败时返回 ([], {})。
    """
    base = _get_hub_base_url()
    if not base:
        return [], {}

    params = {"page": page, "size": size, "sort": sort}
    if category and category != "all":
        params["category"] = category
    qs = urllib.parse.urlencode(params)
    url = f"{base}/api/skills?{qs}"

    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return [], {}

    raw_list = body.get("data") or []
    pagination = body.get("pagination") or {}

    # 映射为面板使用的字段；Hub 返回的可能是 skillId 或 id
    data = []
    for doc in raw_list:
        if isinstance(doc, dict):
            data.append(_map_cloud_skill(doc))
    return data, pagination


# Hub 上传分类与面板 SKILL_CATEGORIES 的 key 对应
_CATEGORY_MAP = {
    "工具": "tool",
    "开发": "dev",
    "效率": "productivity",
    "媒体": "media",
    "安全": "other",
    "其他": "other",
    "通讯": "other",
}


def _map_cloud_skill(doc: Dict) -> Dict:
    """将云端文档转为面板技能项格式，并标记来源为 Hub"""
    skill_id = str(doc.get("skillId") or doc.get("id") or doc.get("_id") or "")
    name = str(doc.get("name") or skill_id or "未知")
    raw_cat = str(doc.get("category") or "其他")
    category = _CATEGORY_MAP.get(raw_cat) or (raw_cat if raw_cat in ("tool", "dev", "productivity", "media", "other") else "other")
    item = {
        "id": skill_id,
        "name": name,
        "description": str(doc.get("description") or ""),
        "icon": str(doc.get("icon") or "📦"),
        "category": category,
        "downloads": int(doc.get("downloads") or 0),
        "rating": float(doc.get("rating") or 5),
        "version": str(doc.get("version") or "?"),
        "author": str(doc.get("author") or doc.get("authorId") or ""),
        "source": "hub",
        "installed": False,
    }
    if doc.get("longDescription") is not None:
        item["longDescription"] = str(doc["longDescription"])
    if doc.get("updated_at"):
        item["updated_at"] = str(doc["updated_at"])
    return item


def get_download_url(skill_id: str, token: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    获取技能包临时下载链接。付费技能需传入已登录用户的 token。

    Returns:
        (url, error): 成功时 url 为临时链接、error 为 None；失败时 url 为 None、error 为错误信息。
    """
    base = _get_hub_base_url()
    if not base:
        return None, "未配置 Hub 地址（BUTLERCLAW_HUB_URL 或 openclaw.json hubBaseUrl）"

    url = f"{base}/api/skills/{urllib.parse.quote(skill_id, safe='')}/download"
    try:
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        if body.get("url"):
            return body["url"], None
        return None, body.get("error") or "未返回下载链接"
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8"))
            msg = err_body.get("error") or e.reason or str(e.code)
        except Exception:
            msg = e.reason or str(e.code)
        if e.code == 401:
            return None, "请先登录并购买该技能"
        if e.code == 403:
            return None, "请先购买该技能后再下载"
        return None, msg
    except Exception as e:
        return None, str(e)


def download_to_temp(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    将下载链接保存为临时文件。

    Returns:
        (path, error): 成功返回临时文件路径（调用方负责删除），失败返回 (None, 错误信息)。
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ButlerClaw/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
        suffix = ".zip"
        if url.rstrip("/").endswith(".skill"):
            suffix = ".skill"
        fd, path = tempfile.mkstemp(suffix=suffix, prefix="butlerclaw_skill_")
        os.close(fd)
        with open(path, "wb") as f:
            f.write(raw)
        return path, None
    except Exception as e:
        return None, str(e)


def is_hub_configured() -> bool:
    """是否已配置 Hub 基础 URL"""
    return bool(_get_hub_base_url())
