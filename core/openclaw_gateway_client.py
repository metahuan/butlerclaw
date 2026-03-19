#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core.openclaw_gateway_client

统一封装对 OpenClaw Gateway 的 HTTP 调用，并将 token 用量喂给 CostTracker。

使用方式（示例）::

    from core.openclaw_gateway_client import call_chat_completions

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": "你好，帮我总结一下今天的待办。"}
        ],
    }
    resp = call_chat_completions(payload)
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

import requests

from .cost_tracker import get_cost_tracker


_tracker = get_cost_tracker()


def _get_gateway_base_url() -> str:
    """
    获取 Gateway 基础 URL。

    优先级：
    1. 环境变量 BUTLERCLAW_GATEWAY_URL
    2. 默认 127.0.0.1:18789
    """
    env_url = os.environ.get("BUTLERCLAW_GATEWAY_URL")
    if env_url:
        return env_url.rstrip("/")
    return "http://127.0.0.1:18789"


def call_chat_completions(
    payload: Dict[str, Any],
    base_url: Optional[str] = None,
    timeout: int = 60,
) -> Dict[str, Any]:
    """
    调用 OpenClaw Gateway 的 /gateway/chat/completions，并记录 token 用量。

    Args:
        payload: 发送给 Gateway 的 JSON 负载（与 openclaw gateway API 保持一致）
        base_url: Gateway 基础地址，默认为环境变量或 http://127.0.0.1:18789
        timeout: 请求超时时间（秒）

    Returns:
        解析后的 JSON 响应 dict
    """
    if base_url is None:
        base_url = _get_gateway_base_url()

    url = f"{base_url.rstrip('/')}/gateway/chat/completions"

    start = time.time()
    resp = requests.post(url, json=payload, timeout=timeout)
    duration_ms = (time.time() - start) * 1000
    data: Dict[str, Any] = {}

    try:
        data = resp.json()
    except Exception:
        # 非 JSON 响应时直接返回空 dict，并在 CostTracker 中记录错误
        _tracker.record_call(
            model=payload.get("model", "unknown"),
            tokens_input=0,
            tokens_output=0,
            provider="openclaw-gateway",
            duration_ms=duration_ms,
            endpoint="/gateway/chat/completions",
            success=False,
            error_message=resp.text[:500],
        )
        return {}

    # 从响应中提取 usage 信息（字段名需与实际 Gateway 响应保持一致）
    model = data.get("model") or payload.get("model") or "unknown"
    usage = data.get("usage") or {}
    input_tokens = int(usage.get("prompt_tokens", 0) or 0)
    output_tokens = int(usage.get("completion_tokens", 0) or 0)

    # 只要有 tokens，就记录一次调用
    _tracker.record_call(
        model=model,
        tokens_input=input_tokens,
        tokens_output=output_tokens,
        provider="openclaw-gateway",
        duration_ms=duration_ms,
        endpoint="/gateway/chat/completions",
        success=resp.ok,
        error_message=("" if resp.ok else str(data.get("error", "")))[:500],
    )

    return data


