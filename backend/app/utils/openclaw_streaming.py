"""
OpenClaw 真实流式输出适配器。
通过 Gateway /v1/chat/completions SSE 端点实现逐 token 流式推送。
"""
from typing import Optional

from app.core.openclaw import stream_openclaw_gateway


async def stream_openclaw_text(
    *,
    agent_id: str,
    message: str,
    state: dict,
    node_name: str,
    active_agent: str,
    prefix: str = "",
    suffix: str = "",
    timeout: Optional[float] = None,
    env_extras: Optional[dict] = None,
) -> str:
    """
    通过 OpenClaw Gateway 流式调用 agent，逐 token 推送 SSE 事件。
    签名与 stream_llm_text() 一致，前端无感知。
    """
    context = state.get("context", {})
    writer = context.get("stream_writer")
    streamed_nodes = context.get("streamed_nodes")
    parts: list[str] = []

    async def emit(text: str):
        if not text:
            return
        parts.append(text)
        if isinstance(streamed_nodes, set):
            streamed_nodes.add(node_name)
        if writer:
            await writer(
                {
                    "type": "stream",
                    "content": text,
                    "node": node_name,
                    "active_agent": active_agent,
                }
            )

    if prefix:
        await emit(prefix)

    async for delta in stream_openclaw_gateway(
        agent_id,
        message,
        timeout=int(timeout) if timeout else None,
    ):
        await emit(delta)

    if suffix:
        await emit(suffix)

    return "".join(parts)
