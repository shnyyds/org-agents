from typing import List, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
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


def get_history_messages(state: AgentState, max_turns: int) -> List[BaseMessage]:
    """
    从 state["messages"] 中提取最近 max_turns 轮对话历史。
    1轮 = 1条 HumanMessage + 1条 AIMessage。
    排除最后一条用户消息（那条会单独作为当前 query）。
    返回 List[BaseMessage]。
    """
    if max_turns <= 0:
        return []

    messages = state.get("messages", [])
    if not messages:
        return []

    # 找到最后一条 HumanMessage 的索引，排除它
    last_human_idx = -1
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], HumanMessage):
            last_human_idx = i
            break

    if last_human_idx < 0:
        return []

    # 取最后一条 HumanMessage 之前的所有消息
    history_pool = messages[:last_human_idx]
    if not history_pool:
        return []

    # 从后往前收集轮次（一轮 = user + assistant）
    turns: List[List[BaseMessage]] = []
    current_turn: List[BaseMessage] = []
    for msg in reversed(history_pool):
        if isinstance(msg, AIMessage):
            current_turn.insert(0, msg)
        elif isinstance(msg, HumanMessage):
            current_turn.insert(0, msg)
            turns.append(current_turn)
            current_turn = []
            if len(turns) >= max_turns:
                break

    turns.reverse()
    result: List[BaseMessage] = []
    for turn in turns:
        result.extend(turn)
    return result
