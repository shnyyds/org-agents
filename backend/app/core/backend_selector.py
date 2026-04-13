"""
LLM 后端选择器。
通过环境变量 LLM_BACKEND 控制使用 LangChain 还是 OpenClaw。
"""
import os
from typing import Optional

_backend: Optional[str] = None
_openclaw_agents: Optional[set] = None


def _load():
    global _backend, _openclaw_agents
    if _backend is not None:
        return
    _backend = os.getenv("LLM_BACKEND", "langchain").lower()
    raw = os.getenv("OPENCLAW_AGENTS", "")
    _openclaw_agents = {a.strip() for a in raw.split(",") if a.strip()} if raw else None


def use_openclaw(agent_id: Optional[str] = None) -> bool:
    """
    返回当前是否应使用 OpenClaw 后端。

    - LLM_BACKEND=openclaw  → 全局启用
    - OPENCLAW_AGENTS=product,developer → 仅指定 agent 启用（LLM_BACKEND 须为 openclaw）
    """
    _load()
    if _backend != "openclaw":
        return False
    if _openclaw_agents is None:
        return True
    if agent_id is None:
        return True
    return agent_id in _openclaw_agents
