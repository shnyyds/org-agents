import asyncio
from typing import Any, Optional


def _normalize_chunk_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return str(content)


async def stream_llm_text(
    *,
    llm: Any,
    prompt: Any,
    state: dict,
    node_name: str,
    active_agent: str,
    prefix: str = "",
    suffix: str = "",
    timeout: Optional[float] = None,
) -> str:
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

    async def consume_stream():
        async for chunk in llm.astream(prompt):
            await emit(_normalize_chunk_content(getattr(chunk, "content", chunk)))

    if prefix:
        await emit(prefix)

    if timeout is not None:
        await asyncio.wait_for(consume_stream(), timeout=timeout)
    else:
        await consume_stream()

    if suffix:
        await emit(suffix)

    return "".join(parts)
