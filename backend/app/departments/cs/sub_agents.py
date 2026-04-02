from typing import Dict, Any
from app.state import AgentState
from app.utils.logger import public_service_logger as logger
from app.core.llm import get_llm
from langchain_core.messages import AIMessage
from app.utils.messages import get_last_user_message
from app.utils.agent_knowledge import inject_knowledge_into_prompt
from app.utils.streaming import stream_llm_text

llm = get_llm()

async def faq_agent_node(state: AgentState) -> Dict[str, Any]:
    logger.info("CS: FAQ Agent answering common questions.")
    query = get_last_user_message(state)
    prompt, kb_names = inject_knowledge_into_prompt(
        "faq",
        query,
        f"你是一位公共服务客服。请根据以下用户咨询提供专业的回答（突出每15天维保一次，如需报修请说明故障）：\n咨询：{query}",
    )
    content = await stream_llm_text(
        llm=llm,
        prompt=prompt,
        state=state,
        node_name="faq",
        active_agent="日常客服智能体",
    )
    return {
        "messages": [AIMessage(content=content)],
        "results": {"faq_answer": content}, 
        "active_agent": "日常客服智能体",
        "execution_log": [{"agent": "日常客服智能体", "status": f"FAQ知识库查询完成{'（已参考' + '、'.join(kb_names) + '）' if kb_names else ''}", "department": "CS"}],
        "next_step": "end"
    }

async def emergency_agent_node(state: AgentState) -> Dict[str, Any]:
    logger.info("CS: Emergency Agent triggered for rescue.")
    query = get_last_user_message(state)
    prompt, kb_names = inject_knowledge_into_prompt(
        "emergency",
        query,
        "请生成一段紧急应急安抚话术，告知用户已启动一级响应，维修工正赶往现场，请保持冷静。",
    )
    content = await stream_llm_text(
        llm=llm,
        prompt=prompt,
        state=state,
        node_name="emergency",
        active_agent="紧急应急智能体",
        prefix="⚠️ ",
    )
    return {
        "messages": [AIMessage(content=content)],
        "results": {"rescue_status": "Notified", "emergency_level": "Immediate"}, 
        "active_agent": "紧急应急智能体",
        "execution_log": [{"agent": "紧急应急智能体", "status": f"识别紧急场景(公共服务关人){'（已参考' + '、'.join(kb_names) + '）' if kb_names else ''}", "department": "CS"}],
        "next_step": "end"
    }

async def human_agent_node(state: AgentState) -> Dict[str, Any]:
    logger.info("CS: Human Support handover.")
    query = get_last_user_message(state)
    prompt, kb_names = inject_knowledge_into_prompt(
        "human",
        query,
        "请告知用户正在转接人工客服 John，并简单说明转接原因（如：复杂问题需要高级支持）。",
    )
    content = await stream_llm_text(
        llm=llm,
        prompt=prompt,
        state=state,
        node_name="human",
        active_agent="人工客服(兜底)",
    )
    return {
        "messages": [AIMessage(content=content)],
        "results": {"handover_id": "Agent-John"}, 
        "active_agent": "人工客服(兜底)",
        "execution_log": [{"agent": "人工客服(兜底)", "status": f"上下文完整移交{'（已参考' + '、'.join(kb_names) + '）' if kb_names else ''}", "department": "CS"}],
        "next_step": "end"
    }
