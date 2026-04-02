from typing import Dict, Any
from app.state import AgentState
from app.utils.logger import public_service_logger as logger
from app.core.llm import get_llm
from langchain_core.messages import AIMessage
from app.utils.messages import get_last_user_message
from app.utils.agent_knowledge import inject_knowledge_into_prompt
from app.utils.streaming import stream_llm_text

llm = get_llm()

async def device_agent_node(state: AgentState) -> Dict[str, Any]:
    logger.info("User: Device Agent checking status.")
    query = get_last_user_message(state)
    prompt, kb_names = inject_knowledge_into_prompt(
        "device",
        query,
        "你是一位公共服务 IoT 服务状态智能体。请生成一份简短的服务设施实时状态报告（包含在线状态、运行楼层和上次维保日期）。",
    )
    content = await stream_llm_text(
        llm=llm,
        prompt=prompt,
        state=state,
        node_name="device",
        active_agent="服务状态智能体",
        prefix="服务状态智能体：IoT 实时监测报告：\n",
    )
    return {
        "messages": [AIMessage(content=content)],
        "results": {"device_status": "Online", "report": content}, 
        "active_agent": "服务状态智能体",
        "execution_log": [{"agent": "服务状态智能体", "status": f"IoT实时状态查询完成{'（已参考' + '、'.join(kb_names) + '）' if kb_names else ''}", "department": "USER"}],
        "next_step": "end"
    }

async def user_repair_agent_node(state: AgentState) -> Dict[str, Any]:
    logger.info("User: Repair Portal Agent creating work order.")
    query = get_last_user_message(state)
    prompt, kb_names = inject_knowledge_into_prompt(
        "repair_portal",
        query,
        f"你是一位公共服务自主申报智能体。请根据用户描述生成一份电子申报工单确认信息：\n描述：{query}",
    )
    content = await stream_llm_text(
        llm=llm,
        prompt=prompt,
        state=state,
        node_name="repair_portal",
        active_agent="申报入口智能体",
        prefix="申报入口智能体：自主申报申请已确认：\n",
    )
    return {
        "messages": [AIMessage(content=content)],
        "results": {"order_id": "REPAIR-2024-0001", "confirmation": content}, 
        "active_agent": "申报入口智能体",
        "execution_log": [{"agent": "申报入口智能体", "status": f"自主申报工单已生成{'（已参考' + '、'.join(kb_names) + '）' if kb_names else ''}", "department": "USER"}],
        "next_step": "end"
    }
