from typing import Dict, Any
from app.state import AgentState
from app.utils.logger import public_service_logger as logger
from app.core.llm import get_llm
from langchain_core.messages import AIMessage
from app.utils.messages import get_first_user_message, get_last_user_message
from app.utils.agent_knowledge import inject_knowledge_into_prompt
from app.utils.streaming import stream_llm_text

llm = get_llm()

async def repair_manager_agent_node(state: AgentState) -> Dict[str, Any]:
    logger.info("Repair: Manager Agent assigning worker.")
    query = get_last_user_message(state)
    prompt, kb_names = inject_knowledge_into_prompt(
        "manager",
        query,
        f"你是一位公共服务运维部经理。请根据以下任务描述，生成一份派单说明（包含运维人员工号和预估到达时间）：\n任务：{query}",
    )
    content = await stream_llm_text(
        llm=llm,
        prompt=prompt,
        state=state,
        node_name="manager",
        active_agent="运维经理智能体",
        prefix="运维经理：派单任务已下达：\n",
    )
    return {
        "messages": [AIMessage(content=content)],
        "results": {"worker": "Worker-001", "assignment": content}, 
        "active_agent": "运维经理智能体",
        "execution_log": [{"agent": "运维经理智能体", "status": f"智能派单完成{'（已参考' + '、'.join(kb_names) + '）' if kb_names else ''}", "department": "REPAIR"}],
        "next_step": "master"
    }

async def repair_master_agent_node(state: AgentState) -> Dict[str, Any]:
    logger.info("Repair: Master Agent identifying fault.")
    assignment = state.get("results", {}).get("assignment")
    original_query = get_first_user_message(state, "No requirement found")
    
    if assignment:
        base_prompt = f"你是一位公共服务问题诊断专家。请根据以下派单信息，分析可能的问题原因及严重等级：\n派单：{assignment}"
    else:
        base_prompt = f"你是一位公共服务问题诊断专家。请直接根据用户的原始报修描述，分析可能的问题原因及严重等级：\n报修：{original_query}"
    prompt, kb_names = inject_knowledge_into_prompt("master", original_query or assignment or "", base_prompt)
        
    content = await stream_llm_text(
        llm=llm,
        prompt=prompt,
        state=state,
        node_name="master",
        active_agent="维修大师智能体",
        prefix="维修大师：问题诊断报告：\n",
    )
    return {
        "messages": [AIMessage(content=content)],
        "results": {"fault_analysis": content}, 
        "active_agent": "维修大师智能体",
        "execution_log": [{"agent": "维修大师智能体", "status": f"问题智能识别(紧急){'（已参考' + '、'.join(kb_names) + '）' if kb_names else ''}", "department": "REPAIR"}],
        "next_step": "worker"
    }

async def repair_worker_agent_node(state: AgentState) -> Dict[str, Any]:
    logger.info("Repair: Worker Agent performing repair.")
    analysis = state.get("results", {}).get("fault_analysis")
    original_query = get_first_user_message(state, "No requirement found")
    
    if analysis:
        base_prompt = f"你是一位公共服务运维人员。请根据以下诊断报告，简述你的现场维修过程及使用的备件：\n诊断：{analysis}"
    else:
        base_prompt = f"你是一位公共服务运维人员。请直接根据用户的原始报修/维保需求，简述你的现场执行过程及使用的备件：\n需求：{original_query}"
    prompt, kb_names = inject_knowledge_into_prompt("worker", original_query or analysis or "", base_prompt)
        
    content = await stream_llm_text(
        llm=llm,
        prompt=prompt,
        state=state,
        node_name="worker",
        active_agent="运维人员智能体",
        prefix="运维人员：现场执行记录：\n",
    )
    return {
        "messages": [AIMessage(content=content)],
        "results": {"repair_log": content}, 
        "active_agent": "运维人员智能体",
        "execution_log": [{"agent": "运维人员智能体", "status": f"现场维修执行完成{'（已参考' + '、'.join(kb_names) + '）' if kb_names else ''}", "department": "REPAIR"}],
        "next_step": "end"
    }
