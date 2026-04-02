from typing import Optional
from langchain_core.messages import HumanMessage
from app.state import AgentState


def get_first_user_message(state: AgentState, default: str = "No user query found") -> str:
    for message in state.get("messages", []):
        if isinstance(message, HumanMessage):
            return message.content
    return default


def get_last_user_message(state: AgentState, default: str = "No user query found") -> str:
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            return message.content
    return default
