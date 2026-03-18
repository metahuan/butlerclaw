#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ButlerClaw Hub 登录与本地登录态（方案 A：桌面直调 Hub 登录 API）

- 登录：POST Hub /api/auth/login，将 token 等写入 ~/.openclaw/hub.json
- 会员信息以 Hub 为准，桌面只读并缓存
"""

import os
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Tuple

HUB_CONFIG_DIR = os.path.expanduser("~/.openclaw")
HUB_CONFIG_PATH = os.path.join(HUB_CONFIG_DIR, "hub.json")


def _get_hub_base_url() -> str:
    """从环境变量或 openclaw.json 读取 Hub 基础 URL"""
    url = os.environ.get("BUTLERCLAW_HUB_URL", "").strip()
    if url:
        return url.rstrip("/")
    config_path = os.path.join(HUB_CONFIG_DIR, "openclaw.json")
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


def load_hub_config() -> Dict:
    """读取 hub.json，返回包含 token、userId、username、membershipLevel 等的字典；不存在或异常返回空字典"""
    if not os.path.isfile(HUB_CONFIG_PATH):
        return {}
    try:
        with open(HUB_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_hub_config(data: Dict) -> None:
    """写入 hub.json，仅当前用户可读（0o600）"""
    os.makedirs(HUB_CONFIG_DIR, exist_ok=True)
    with open(HUB_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    try:
        os.chmod(HUB_CONFIG_PATH, 0o600)
    except OSError:
        pass


def login(email: str, password: str) -> Tuple[bool, str]:
    """
    使用邮箱和密码调用 Hub 登录接口，成功则写入 hub.json。

    Returns:
        (success, message): 成功时 message 为空或提示文案；失败时为错误信息。
    """
    base = _get_hub_base_url()
    if not base:
        return False, "未配置 Hub 地址（请设置 BUTLERCLAW_HUB_URL 或 openclaw.json 中 hubBaseUrl）"

    url = f"{base}/api/auth/login"
    body = json.dumps({"email": email.strip(), "password": password}).encode("utf-8")

    try:
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8"))
            msg = err_body.get("error") or e.reason or str(e.code)
        except Exception:
            msg = e.reason or str(e.code)
        return False, msg or "登录失败"
    except Exception as e:
        return False, str(e) or "网络错误"

    token = data.get("token")
    if not token:
        return False, "登录成功但未返回 token"

    # 与 Hub 返回字段一致；getUserInfo 会带 membershipLevel、membershipExpireAt 等
    to_save = {
        "token": token,
        "userId": data.get("userId"),
        "username": data.get("username", ""),
        "membershipLevel": data.get("membershipLevel", "free"),
        "membershipExpireAt": data.get("membershipExpireAt"),
        "updatedAt": data.get("updatedAt"),
    }
    save_hub_config(to_save)
    return True, ""


def get_token() -> Optional[str]:
    """返回当前缓存的 token，未登录或无效时为 None"""
    cfg = load_hub_config()
    return (cfg.get("token") or "").strip() or None


def is_logged_in() -> bool:
    """是否已登录（本地有 token）"""
    return bool(get_token())


def get_cached_user() -> Optional[Dict]:
    """返回缓存的用户信息（username、membershipLevel、membershipExpireAt 等），未登录返回 None"""
    cfg = load_hub_config()
    if not (cfg.get("token") or "").strip():
        return None
    return {
        "userId": cfg.get("userId"),
        "username": cfg.get("username", ""),
        "membershipLevel": cfg.get("membershipLevel", "free"),
        "membershipExpireAt": cfg.get("membershipExpireAt"),
    }


def refresh_user() -> Optional[Dict]:
    """请求 GET /api/auth/me 刷新用户信息并写回 hub.json，失败返回 None"""
    token = get_token()
    if not token:
        return None
    base = _get_hub_base_url()
    if not base:
        return get_cached_user()

    url = f"{base}/api/auth/me"
    try:
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return get_cached_user()

    # 更新缓存
    cfg = load_hub_config()
    cfg["username"] = data.get("username", cfg.get("username", ""))
    cfg["membershipLevel"] = data.get("membershipLevel", "free")
    cfg["membershipExpireAt"] = data.get("membershipExpireAt")
    save_hub_config(cfg)
    return get_cached_user()


def logout() -> None:
    """清除本地登录态（清空 token 及相关字段）"""
    save_hub_config({})


def is_hub_configured() -> bool:
    """是否已配置 Hub 地址"""
    return bool(_get_hub_base_url())
