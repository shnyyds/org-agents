from typing import Dict, Any
from app.state import AgentState
from app.utils.logger import public_service_logger as logger
from app.core.llm import get_llm
from langchain_core.messages import AIMessage
from app.utils.messages import get_first_user_message, get_last_user_message
from app.utils.agent_knowledge import inject_knowledge_into_prompt
from app.utils.streaming import stream_llm_text

llm = get_llm()

async def lead_gen_agent_node(state: AgentState) -> Dict[str, Any]:
    logger.info("Sales: Service Consultation Agent gathering requirements.")
    query = get_last_user_message(state)
    prompt, kb_names = inject_knowledge_into_prompt(
        "lead_gen",
        query,
        f"你是一位资深公共服务咨询专员。请根据用户需求分析服务需求并提供2个潜在的服务方案建议（包含方案名称和简述）：\n需求：{query}",
    )
    content = await stream_llm_text(
        llm=llm,
        prompt=prompt,
        state=state,
        node_name="lead_gen",
        active_agent="服务咨询专员",
        prefix="服务咨询专员：已分析服务需求：\n",
    )
    return {
        "messages": [AIMessage(content=content)],
        "results": {"leads": content},
        "active_agent": "服务咨询专员",
        "execution_log": [{"agent": "服务咨询专员", "status": f"服务需求分析完成{'（已参考' + '、'.join(kb_names) + '）' if kb_names else ''}", "department": "SALES"}],
        "next_step": "quote"
    }

async def quote_agent_node(state: AgentState) -> Dict[str, Any]:
    logger.info("Sales: Solution Design Agent creating proposal.")
    leads = state.get("results", {}).get("leads")
    original_query = get_first_user_message(state, "No requirement found")

    if leads:
        base_prompt = f"请根据以下服务需求分析生成一份专业的服务方案设计书摘要：\n需求分析：{leads}"
    else:
        base_prompt = f"请直接根据用户的原始服务需求生成一份专业的服务方案设计书摘要：\n需求：{original_query}"
    prompt, kb_names = inject_knowledge_into_prompt("quote", original_query or leads or "", base_prompt)

    content = await stream_llm_text(
        llm=llm,
        prompt=prompt,
        state=state,
        node_name="quote",
        active_agent="方案设计专员",
        prefix="方案设计专员：服务方案已生成：\n",
    )
    return {
        "messages": [AIMessage(content=content)],
        "results": {"quote": content},
        "active_agent": "方案设计专员",
        "execution_log": [{"agent": "方案设计专员", "status": f"服务方案设计完成{'（已参考' + '、'.join(kb_names) + '）' if kb_names else ''}", "department": "SALES"}],
        "next_step": "cad"
    }

async def cad_agent_node(state: AgentState) -> Dict[str, Any]:
    logger.info("Sales: Implementation Plan Agent generating execution plan.")
    quote = state.get("results", {}).get("quote")
    original_query = get_first_user_message(state, "No requirement found")

    if quote:
        base_prompt = f"请根据以下服务方案，生成一份精简的实施计划和时间表：\n方案信息：{quote}"
    else:
        base_prompt = f"请直接根据用户的原始服务需求，生成一份精简的实施计划和时间表：\n需求：{original_query}"
    prompt, kb_names = inject_knowledge_into_prompt("cad", original_query or quote or "", base_prompt)

    content = await stream_llm_text(
        llm=llm,
        prompt=prompt,
        state=state,
        node_name="cad",
        active_agent="实施计划专员",
        prefix="实施计划专员：实施计划已产出：\n",
    )
    return {
        "messages": [AIMessage(content=content)],
        "results": {"cad_drawing": content},
        "active_agent": "实施计划专员",
        "execution_log": [{"agent": "实施计划专员", "status": f"实施计划输出完成{'（已参考' + '、'.join(kb_names) + '）' if kb_names else ''}", "department": "SALES"}],
        "next_step": "end"
    }
