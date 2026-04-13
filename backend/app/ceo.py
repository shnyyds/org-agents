from typing import List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from app.state import AgentState
from app.core.llm import get_llm
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import os

# Initialize LLM lazily to avoid crash when LLM_BACKEND=openclaw and no API key
_ceo_llm = None


def _get_ceo_llm():
    global _ceo_llm
    if _ceo_llm is None:
        _ceo_llm = get_llm()
    if _ceo_llm is None:
        raise RuntimeError(
            "LLM not available. analyze_intent_node requires OPENAI_API_KEY "
            "even when LLM_BACKEND=openclaw."
        )
    return _ceo_llm

# --- Node Definitions ---

import json
from app.utils.logger import public_service_logger as logger
from app.utils.labels import format_department_plan, get_department_label
from app.utils.streaming import stream_llm_text
from app.utils.agent_knowledge import resolve_agent_prompt
from app.utils.messages import get_history_messages
from app.core.backend_selector import use_openclaw
from app.agent_config import agent_config_service

async def analyze_intent_node(state: AgentState) -> Dict[str, Any]:
    '''
    CEO Node: Analyzes the user's query to determine the department and intent using Qwen.
    '''
    last_message = state["messages"][-1].content
    logger.info(f"CEO Orchestrator: Analyzing user query: '{last_message}'")

    system_prompt = resolve_agent_prompt("CEO", '''
    你是一位企业级多智能体协作系统的 CEO 总智能体。你的任务是解析用户的意图，并制定一个跨部门的执行计划。

    可选部门：
    - MARKET (市场部): 需求分析、公众调研、宣传内容生成。
    - TECH (技术部): 产品文档、代码开发、自动化检测、运维部署。
    - SALES (业务部): 服务咨询、方案设计、项目管理。
    - REPAIR (运维部): 派单、问题识别、设施维护、执行记录。
    - CS (客服部): 常见问题咨询、应急响应、人工转接。
    - USER (用户管理): 服务状态查询、自主申报、咨询入口。

    请分析用户需求是否涉及多个部门。例如："分析需求并开发系统"涉及 MARKET 和 TECH。

    请按以下 JSON 格式返回分析结果：
    {
        "plan": ["部门代码1", "部门代码2", ...],
        "intent": "具体意图描述",
        "urgency": "Low/Medium/High",
        "entities": {"key": "value"}
    }
    ''', query=last_message)

    messages = [
        SystemMessage(content=system_prompt),
    ]

    # 注入上下文历史
    context_turns = agent_config_service.get_effective_config("CEO").get("context_turns", 0)
    history = get_history_messages(state, context_turns)
    messages.extend(history)

    messages.append(HumanMessage(content=last_message))

    # Use streaming for real-time output
    response_text = await stream_llm_text(
        llm=_get_ceo_llm(),
        prompt=messages,
        state=state,
        node_name="analyze_intent",
        active_agent="CEO 总智能体",
    )

    try:
        content = response_text.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()

        analysis = json.loads(content)
        logger.info(f"CEO Orchestrator: Analysis result: {analysis}")
        
        plan = analysis.get("plan", [])
        if not plan: # Fallback to a single department if plan is missing
            plan = [analysis.get("department", "CS")]

        # Generate a human-readable thought process message
        thought_msg = f"已收到您的指令。我为您制定了以下执行计划：\n"
        thought_msg += f"1. 意图：{analysis.get('intent', '通用咨询')}\n"
        thought_msg += f"2. 流程：{format_department_plan(plan)}\n"
        thought_msg += "正在调派相关部门智能体执行，请稍候..."

        return {
            "intent_analysis": analysis,
            "plan": plan,
            "plan_step": 0,
            "active_agent": "CEO 总智能体",
            "messages": [AIMessage(content=thought_msg)], # Push the thought message
            "execution_log": [{"agent": "CEO 总智能体", "status": f"制定执行计划: {format_department_plan(plan)}", "department": "CEO"}],
            "next_step": "dispatch"
        }
    except Exception as e:
        logger.error(f"CEO Orchestrator: Failed to parse intent analysis. Error: {e}")
        return {
            "intent_analysis": {"intent": "unknown"},
            "plan": ["CS"],
            "plan_step": 0,
            "next_step": "dispatch"
        }

from app.departments.registry import get_department_lead

market_lead = get_department_lead("MARKET")
tech_lead = get_department_lead("TECH")
sales_lead = get_department_lead("SALES")
repair_lead = get_department_lead("REPAIR")
cs_lead = get_department_lead("CS")
user_lead = get_department_lead("USER")

async def dispatch_to_department_node(state: AgentState) -> Dict[str, Any]:
    """
    CEO Node: Prepares to dispatch the task to the current department in the plan.
    It identifies the next department and updates the current_department state.
    """
    plan = state.get("plan", [])
    step = state.get("plan_step", 0)
    
    if step >= len(plan):
        return {"next_step": "summarize", "current_department": "CEO"}
        
    dept = plan[step]
    logger.info(f"CEO Orchestrator: Step {step+1}/{len(plan)} - Routing to {dept}")
    
    return {
        "plan_step": step + 1,
        "current_department": dept,
        "active_agent": f"{get_department_label(dept)}部长",
        "execution_log": [{"agent": "CEO 总智能体", "status": f"正在调派 {get_department_label(dept)} 执行任务", "department": "CEO"}]
    }

def route_to_department(state: AgentState) -> str:
    """
    Routes to the specific department node or finishes.
    """
    dept = state.get("current_department")
    plan = state.get("plan", [])
    step = state.get("plan_step", 0)
    
    # If we just updated current_department in dispatch_to_department_node, 
    # we use that to route.
    if dept in ["MARKET", "TECH", "SALES", "REPAIR", "CS", "USER"]:
        return dept
    
    return "finish"

async def trigger_actions_node(state: AgentState) -> Dict[str, Any]:
    """
    CEO Node: Handles cross-department triggers (e.g., Sales -> Repair).
    """
    results = state.get("results", {})
    current_dept = state.get("current_department")
    
    # Trigger 1: Sales成单 -> 触发维修派单
    if current_dept == "SALES" and "quote" in results.get("SALES", {}):
        logger.info("CEO: Sales completed. Triggering Repair Department for installation.")
        # Trigger Repair Agent automatically
        repair_result = await repair_lead.run(state)
        # Update results with repair output
        new_results = results.copy()
        new_results["REPAIR_TRIGGERED"] = repair_result.get("results", {})
        
        return {
            "results": new_results,
            "messages": [AIMessage(content="CEO: 销售已成单，已自动触发维修部进行安装排期。")]
        }
    
    # Trigger 2: 客服部识别紧急救援 -> 立即触发维修部 (Already implied in CS logic)
    
    return {}

async def summarize_result_node(state: AgentState) -> Dict[str, Any]:
    """
    CEO Node: Provides a high-level executive summary.
    Removes technical details like code or PRDs, focusing on business value.
    """
    plan = state.get("plan", [])
    intent = state.get("intent_analysis", {}).get("intent", "处理用户指令")
    
    # Use LLM to generate a clean, executive summary based on the execution history
    # but strictly instruction it to be concise and non-technical.
    summary_prompt = f"""
    你是一位公共服务行业公司的 CEO。
    各职能部门（{', '.join(get_department_label(item) for item in plan)}）已经完成了以下任务：{intent}。

    请根据各部门的协作情况，输出一份简洁的【CEO 任务总结】。

    要求：
    1. 语气专业、果断，具有领导力。
    2. 严禁包含任何代码、JSON、PRD 文档原文或技术细节。
    3. 重点说明任务是否完成，以及对客户/业务的价值。
    4. 字数控制在 150 字以内。

    格式示例：
    🏢 CEO 任务总结
    ━
    [总结正文...]
    ━
    🏁 指令已闭环执行。
    """

    if use_openclaw("CEO"):
        from app.utils.openclaw_streaming import stream_openclaw_text
        summary_text = await stream_openclaw_text(
            agent_id="org_ceo",
            message=summary_prompt,
            state=state,
            node_name="summarize_result",
            active_agent="CEO 总智能体",
        )
    else:
        summary_text = await stream_llm_text(
            llm=_get_ceo_llm(),
            prompt=summary_prompt,
            state=state,
            node_name="summarize_result",
            active_agent="CEO 总智能体",
        )
    
    return {
        "messages": [AIMessage(content=summary_text)],
        "active_agent": "CEO 总智能体",
        "execution_log": [{"agent": "CEO 总智能体", "status": "全流程执行完毕，已汇总高层报告", "department": "CEO"}],
        "is_task_complete": True
    }

# --- Graph Construction ---

def create_ceo_graph():
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("analyze_intent", analyze_intent_node)
    workflow.add_node("dispatch_to_department", dispatch_to_department_node)
    
    # Add Department Sub-graphs as nodes
    # Each run() method of lead agents should be accessible or use the workflow directly
    workflow.add_node("MARKET", market_lead.workflow.compile())
    workflow.add_node("TECH", tech_lead.workflow.compile())
    workflow.add_node("SALES", sales_lead.workflow.compile())
    workflow.add_node("REPAIR", repair_lead.workflow.compile())
    workflow.add_node("CS", cs_lead.workflow.compile())
    workflow.add_node("USER", user_lead.workflow.compile())
    
    workflow.add_node("trigger_actions", trigger_actions_node)
    workflow.add_node("summarize_result", summarize_result_node)
    
    # Set entry point
    workflow.set_entry_point("analyze_intent")
    
    # Define edges
    workflow.add_edge("analyze_intent", "dispatch_to_department")
    
    # Route from dispatcher to specific department or finish
    workflow.add_conditional_edges(
        "dispatch_to_department",
        route_to_department,
        {
            "MARKET": "MARKET",
            "TECH": "TECH",
            "SALES": "SALES",
            "REPAIR": "REPAIR",
            "CS": "CS",
            "USER": "USER",
            "finish": "trigger_actions"
        }
    )
    
    # After each department finishes, go back to dispatcher to check for next plan step
    workflow.add_edge("MARKET", "dispatch_to_department")
    workflow.add_edge("TECH", "dispatch_to_department")
    workflow.add_edge("SALES", "dispatch_to_department")
    workflow.add_edge("REPAIR", "dispatch_to_department")
    workflow.add_edge("CS", "dispatch_to_department")
    workflow.add_edge("USER", "dispatch_to_department")
    
    workflow.add_edge("trigger_actions", "summarize_result")
    workflow.add_edge("summarize_result", END)
    
    # Compile
    app_graph = workflow.compile()
    return app_graph

# Example usage (for testing)
if __name__ == "__main__":
    ceo_app = create_ceo_graph()
    print("CEO Graph created successfully.")
