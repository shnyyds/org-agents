"""
OpenClaw Gateway HTTP 流式调用。
通过 /v1/chat/completions SSE 端点实现真正的逐 token 流式输出。
需要在 openclaw.json 中开启: gateway.http.endpoints.chatCompletions.enabled = true
"""
import json
import os
from typing import AsyncIterator, Optional

import httpx

from app.utils.logger import public_service_logger as logger

_GATEWAY_URL = os.getenv("OPENCLAW_GATEWAY_URL", "http://localhost:18789")
_GATEWAY_TOKEN = os.getenv("OPENCLAW_GATEWAY_TOKEN", "")
_OPENCLAW_TIMEOUT = int(os.getenv("OPENCLAW_TIMEOUT", "300"))


def _resolve_token() -> str:
    """从环境变量或 openclaw.json 读取 gateway token。"""
    if _GATEWAY_TOKEN:
        return _GATEWAY_TOKEN
    config_path = os.path.expanduser("~/.openclaw/openclaw.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("gateway", {}).get("auth", {}).get("token", "")
    except Exception:
        return ""


_cached_token: Optional[str] = None


def _get_token() -> str:
    global _cached_token
    if _cached_token is None:
        _cached_token = _resolve_token()
    return _cached_token


async def stream_openclaw_gateway(
    agent_id: str,
    message: str,
    *,
    system_prompt: Optional[str] = None,
    timeout: Optional[int] = None,
) -> AsyncIterator[str]:
    """
    调用 OpenClaw Gateway 的 /v1/chat/completions 流式端点。
    逐 token yield 文本 delta。
    """
    timeout_val = timeout or _OPENCLAW_TIMEOUT
    token = _get_token()

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": message})

    payload = {
        "model": f"agent:{agent_id}",
        "stream": True,
        "messages": messages,
    }

    logger.info(f"OpenClaw Gateway: streaming agent={agent_id}, msg_len={len(message)}")

    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_val, connect=10)) as client:
        async with client.stream(
            "POST",
            f"{_GATEWAY_URL}/v1/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        ) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                raise RuntimeError(
                    f"OpenClaw Gateway error {resp.status_code}: {body.decode()[:500]}"
                )

            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    choice = chunk.get("choices", [{}])[0]
                    delta = choice.get("delta", {})
                    content = delta.get("content", "")

                    # Log non-content events (tool_calls, sub-agent spawns, etc.)
                    if not content:
                        tool_calls = delta.get("tool_calls")
                        finish = choice.get("finish_reason")
                        if tool_calls or finish:
                            logger.info(f"[OpenClaw SSE] non-content event: tool_calls={tool_calls}, finish_reason={finish}")

                    if content:
                        yield content
                except (json.JSONDecodeError, IndexError, KeyError):
                    continue


# ── Edict 流水线阶段检测 ──

_STAGE_MARKERS = [
    ("🌟 星核StarCore·任务完成报告", "completed"),
    ("📋 首席助理", "chief_assistant"),
    ("📋 策略中心", "strategy_hub"),
    ("🔍 评审委", "review_board"),
    ("📮 星核StarCore·技术执行报告", "tech_lead_summary"),
    ("📮 星核·任务令", "tech_lead_dispatch"),
    ("📮 蓝图BlueForm", "product"),
    ("📮 灵码SmartCode", "developer"),
    ("📮 检博士CheckDoc", "tester"),
    ("📮 运小盾OpsShield", "devops"),
]


def detect_pipeline_stage(text: str) -> str | None:
    """通过解析结构化标记识别当前流水线阶段。"""
    for marker, stage in _STAGE_MARKERS:
        if marker in text:
            return stage
    return None
