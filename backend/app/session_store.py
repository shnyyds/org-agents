"""
In-memory session state store for step-by-step execution.
Stores intermediate AgentState between user confirmations.
"""

from typing import Dict, Any, Optional, List
import time


class SessionData:
    """Stores intermediate execution state between confirmations."""

    __slots__ = (
        "state", "execution_plan", "cursor", "mode",
        "target_agent", "target_type", "last_node",
        "created_at", "updated_at",
    )

    def __init__(
        self,
        state: Dict[str, Any],
        execution_plan: List[str],
        cursor: int = 0,
        mode: str = "ceo",
        target_agent: str = "CEO",
        target_type: str = "orchestrator",
        last_node: str = "",
    ):
        self.state = state
        self.execution_plan = execution_plan
        self.cursor = cursor
        self.mode = mode
        self.target_agent = target_agent
        self.target_type = target_type
        self.last_node = last_node
        self.created_at = time.time()
        self.updated_at = time.time()


_sessions: Dict[str, SessionData] = {}


def save_session(session_id: str, data: SessionData) -> None:
    data.updated_at = time.time()
    _sessions[session_id] = data


def get_session(session_id: str) -> Optional[SessionData]:
    return _sessions.get(session_id)


def delete_session(session_id: str) -> None:
    _sessions.pop(session_id, None)


def cleanup_stale_sessions(max_age_seconds: int = 3600) -> int:
    """Remove sessions older than max_age_seconds. Returns count removed."""
    now = time.time()
    stale = [k for k, v in _sessions.items() if now - v.updated_at > max_age_seconds]
    for k in stale:
        del _sessions[k]
    return len(stale)
