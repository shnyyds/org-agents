"""
Step-by-step executor for the multi-agent system.
Replaces LangGraph's compiled graph execution with individual node calls,
enabling pause-after-every-node for user confirmation.
"""

from typing import Dict, Any, List, Optional, Callable, Awaitable
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from app.session_store import SessionData, save_session, delete_session
from app.utils.logger import public_service_logger as logger

# ---------------------------------------------------------------------------
# Lazy imports to avoid circular dependencies at module level
# ---------------------------------------------------------------------------

_registry_built = False
NODE_REGISTRY: Dict[str, Callable] = {}


def _build_registry():
    global _registry_built, NODE_REGISTRY
    if _registry_built:
        return
    # CEO nodes
    from app.ceo import (
        analyze_intent_node,
        dispatch_to_department_node,
        trigger_actions_node,
        summarize_result_node,
    )
    # 所有部门从 registry 获取
    from app.departments.registry import get_department_lead, create_sub_agent_node

    tech_lead = get_department_lead("TECH")
    market_lead = get_department_lead("MARKET")
    sales_lead = get_department_lead("SALES")
    repair_lead = get_department_lead("REPAIR")
    cs_lead = get_department_lead("CS")
    user_lead = get_department_lead("USER")

    NODE_REGISTRY.update({
        # CEO
        "analyze_intent": analyze_intent_node,
        "dispatch_to_department": dispatch_to_department_node,
        "trigger_actions": trigger_actions_node,
        "summarize_result": summarize_result_node,
        # TECH
        "tech_lead_plan": tech_lead._lead_plan_node,
        "tech_dispatch": tech_lead._dispatch_node,
        "product": create_sub_agent_node("product"),
        "developer": create_sub_agent_node("developer"),
        "tester": create_sub_agent_node("tester"),
        "devops": create_sub_agent_node("devops"),
        # MARKET
        "market_lead_plan": market_lead._lead_plan_node,
        "market_dispatch": market_lead._dispatch_node,
        "analyze_industry": create_sub_agent_node("analyze_industry"),
        "generate_content": create_sub_agent_node("generate_content"),
        # SALES
        "sales_lead_plan": sales_lead._lead_plan_node,
        "sales_dispatch": sales_lead._dispatch_node,
        "lead_gen": create_sub_agent_node("lead_gen"),
        "quote": create_sub_agent_node("quote"),
        "cad": create_sub_agent_node("cad"),
        # REPAIR
        "repair_lead_plan": repair_lead._lead_plan_node,
        "repair_dispatch": repair_lead._dispatch_node,
        "manager": create_sub_agent_node("manager"),
        "master": create_sub_agent_node("master"),
        "worker": create_sub_agent_node("worker"),
        # CS
        "cs_lead_plan": cs_lead._lead_plan_node,
        "cs_dispatch": cs_lead._dispatch_node,
        "faq": create_sub_agent_node("faq"),
        "emergency": create_sub_agent_node("emergency"),
        "human": create_sub_agent_node("human"),
        # USER
        "user_lead_plan": user_lead._lead_plan_node,
        "user_dispatch": user_lead._dispatch_node,
        "device": create_sub_agent_node("device"),
        "repair_portal": create_sub_agent_node("repair_portal"),
    })
    _registry_built = True


# Nodes that require RunnableConfig as second argument
NEEDS_CONFIG: set = set()

# Nodes that pause for user confirmation after completing
PAUSABLE_NODES = {
    "analyze_intent", "summarize_result",
    "tech_lead_plan", "product", "developer", "tester", "devops",
    "market_lead_plan", "analyze_industry", "generate_content",
    "sales_lead_plan", "lead_gen", "quote", "cad",
    "repair_lead_plan", "manager", "master", "worker",
    "cs_lead_plan", "faq", "emergency", "human",
    "user_lead_plan", "device", "repair_portal",
}

# Nodes that end the SSE stream and return to normal input mode
ENDS_FOR_USER_INPUT = set()

# Friendly display names
FRIENDLY_NAMES = {
    "analyze_intent": "CEO 总智能体",
    "dispatch_to_department": "CEO 总智能体",
    "trigger_actions": "CEO 总智能体",
    "summarize_result": "CEO 总智能体",
    "tech_lead_plan": "星核StarCore",
    "tech_dispatch": "星核StarCore",
    "product": "蓝图BlueForm",
    "developer": "灵码SmartCode",
    "tester": "检博士CheckDoc",
    "devops": "运小盾OpsShield",
    "market_lead_plan": "市场部部长",
    "market_dispatch": "市场部部长",
    "analyze_industry": "行业分析大师",
    "generate_content": "宣传推广大师",
    "sales_lead_plan": "业务部部长",
    "sales_dispatch": "业务部部长",
    "lead_gen": "获客智能体",
    "quote": "业务报价智能体",
    "cad": "CAD设计智能体",
    "repair_lead_plan": "运维部部长",
    "repair_dispatch": "运维部部长",
    "manager": "派单经理智能体",
    "master": "故障识别大师",
    "worker": "现场执行智能体",
    "cs_lead_plan": "客服部部长",
    "cs_dispatch": "客服部部长",
    "faq": "FAQ智能助手",
    "emergency": "救援调度智能体",
    "human": "人工客服座席",
    "user_lead_plan": "用户端部长",
    "user_dispatch": "用户端部长",
    "device": "设备健康智能体",
    "repair_portal": "自主报修入口",
}

# Department lead plan node mapping
DEPT_LEAD_PLAN = {
    "TECH": "tech_lead_plan",
    "MARKET": "market_lead_plan",
    "SALES": "sales_lead_plan",
    "REPAIR": "repair_lead_plan",
    "CS": "cs_lead_plan",
    "USER": "user_lead_plan",
}

DEPT_DISPATCH = {
    "TECH": "tech_dispatch",
    "MARKET": "market_dispatch",
    "SALES": "sales_dispatch",
    "REPAIR": "repair_dispatch",
    "CS": "cs_dispatch",
    "USER": "user_dispatch",
}

LEAD_PLAN_NODES = {
    "tech_lead_plan", "market_lead_plan", "sales_lead_plan",
    "repair_lead_plan", "cs_lead_plan", "user_lead_plan",
}

# ---------------------------------------------------------------------------
# Initial plan computation
# ---------------------------------------------------------------------------

def compute_initial_plan(mode: str, target_agent: str) -> List[str]:
    """Compute the starting execution plan based on mode."""
    if mode == "ceo":
        return ["analyze_intent"]
    elif mode == "department":
        entry = DEPT_LEAD_PLAN.get(target_agent)
        return [entry] if entry else ["cs_lead_plan"]
    else:  # agent direct chat
        return [target_agent]


# ---------------------------------------------------------------------------
# Dynamic plan expansion
# ---------------------------------------------------------------------------

def expand_plan_after_node(
    state: Dict[str, Any],
    plan: List[str],
    cursor: int,
    last_node: str,
) -> List[str]:
    """Expand the execution plan based on the output of the last completed node."""

    # After CEO intent analysis: expand with department sequence
    if last_node == "analyze_intent":
        departments = state.get("plan", [])
        expansion: List[str] = []
        for dept in departments:
            expansion.append("dispatch_to_department")
            entry = DEPT_LEAD_PLAN.get(dept)
            if entry:
                expansion.append(entry)
        expansion.append("trigger_actions")
        expansion.append("summarize_result")
        return plan[:cursor] + expansion

    # After any department lead plan: expand with sub-agent sequence
    if last_node in LEAD_PLAN_NODES:
        sub_plan = state.get("sub_plan", [])
        dept = state.get("current_department", "")
        dispatch_key = DEPT_DISPATCH.get(dept, "")
        remaining = plan[cursor:]
        expansion = []
        for agent_id in sub_plan:
            if dispatch_key:
                expansion.append(dispatch_key)
            expansion.append(agent_id)
        return plan[:cursor] + expansion + remaining

    return plan


# ---------------------------------------------------------------------------
# State merge
# ---------------------------------------------------------------------------

def merge_output(state: Dict[str, Any], output: Dict[str, Any]) -> None:
    """Merge a node's output dict into the running state."""
    if not isinstance(output, dict):
        return

    # Append messages
    msgs = output.get("messages", [])
    if msgs:
        state.setdefault("messages", [])
        state["messages"].extend(msgs)

    # Append execution_log
    logs = output.get("execution_log", [])
    if logs:
        state.setdefault("execution_log", [])
        state["execution_log"].extend(logs)

    # Merge results (ior)
    results = output.get("results")
    if results:
        state.setdefault("results", {})
        state["results"].update(results)

    # Merge sub_task_results (ior)
    sub_results = output.get("sub_task_results")
    if sub_results:
        state.setdefault("sub_task_results", {})
        state["sub_task_results"].update(sub_results)

    # All other keys: overwrite
    skip = {"execution_log", "messages", "results", "sub_task_results"}
    for k, v in output.items():
        if k not in skip:
            state[k] = v


# ---------------------------------------------------------------------------
# Helper: find next pausable node for display
# ---------------------------------------------------------------------------

def _find_next_pausable(plan: List[str], cursor: int) -> Optional[str]:
    """Find the next pausable node name starting from cursor, skipping silent nodes."""
    for i in range(cursor, len(plan)):
        if plan[i] in PAUSABLE_NODES:
            return plan[i]
    return None


# ---------------------------------------------------------------------------
# Core: execute one step (runs nodes until a pausable node completes)
# ---------------------------------------------------------------------------

async def execute_step(
    session_id: str,
    session: SessionData,
    emit_sse: Callable[[Dict[str, Any]], Awaitable[None]],
) -> None:
    """Execute nodes from cursor until a PAUSABLE node completes, then pause."""
    _build_registry()

    state = session.state
    plan = session.execution_plan
    cursor = session.cursor

    try:
        while cursor < len(plan):
            # Check if session was cancelled by user
            if session.cancelled:
                logger.info(f"StepExecutor: Session cancelled, stopping execution.")
                session.state = state
                session.execution_plan = plan
                session.cursor = cursor
                save_session(session_id, session)
                await emit_sse({"type": "stopped"})
                await emit_sse(None)
                return

            node_name = plan[cursor]
            node_func = NODE_REGISTRY.get(node_name)

            if not node_func:
                logger.warning(f"StepExecutor: Unknown node '{node_name}', skipping.")
                cursor += 1
                continue

            friendly = FRIENDLY_NAMES.get(node_name, node_name)
            logger.info(f"StepExecutor: Executing node '{node_name}' ({friendly})")

            # Emit thinking status
            await emit_sse({
                "type": "update",
                "active_agent": friendly,
                "status": "thinking",
                "node_name": node_name,
            })

            # Call the node function
            if node_name in NEEDS_CONFIG:
                output = await node_func(state, RunnableConfig())
            else:
                output = await node_func(state)

            # Merge output into state
            merge_output(state, output)
            cursor += 1

            # Dynamically expand plan based on output
            plan = expand_plan_after_node(state, plan, cursor, node_name)

            # Emit update with execution log and phase
            update_payload: Dict[str, Any] = {
                "type": "update",
                "active_agent": output.get("active_agent", friendly) if isinstance(output, dict) else friendly,
                "node_name": node_name,
                "execution_log": output.get("execution_log", []) if isinstance(output, dict) else [],
            }
            task_phase = output.get("task_phase") if isinstance(output, dict) else None
            req_status = output.get("requirement_confirmation_status") if isinstance(output, dict) else None
            if task_phase or req_status:
                await emit_sse({
                    "type": "phase_update",
                    "task_phase": task_phase or state.get("task_phase", "idle"),
                    "requirement_confirmation_status": req_status or state.get("requirement_confirmation_status", "pending"),
                    "current_executor": output.get("current_executor", "") if isinstance(output, dict) else "",
                })
            await emit_sse(update_payload)

            # If pausable: save state and emit confirmation request
            if node_name in PAUSABLE_NODES:
                is_final = cursor >= len(plan)
                display_next = _find_next_pausable(plan, cursor)

                session.state = state
                session.execution_plan = plan
                session.cursor = cursor
                session.last_node = node_name
                save_session(session_id, session)

                await emit_sse({
                    "type": "awaiting_confirmation",
                    "completed_node": node_name,
                    "completed_agent": FRIENDLY_NAMES.get(node_name, node_name),
                    "next_node": display_next,
                    "next_agent": FRIENDLY_NAMES.get(display_next, "") if display_next else None,
                    "is_final_node": is_final,
                })
                # Signal end of this SSE stream
                await emit_sse(None)
                return

            # Nodes that end the stream and return to normal input mode
            # (e.g., requirement_clarification — user needs to type a response)
            if node_name in ENDS_FOR_USER_INPUT:
                session.state = state
                session.execution_plan = plan
                session.cursor = cursor
                session.last_node = node_name
                save_session(session_id, session)

                last_msg = state.get("messages", [])
                final_text = last_msg[-1].content if last_msg and hasattr(last_msg[-1], "content") else ""
                await emit_sse({
                    "type": "final",
                    "response": final_text,
                    "task_phase": state.get("task_phase", "requirement_clarification"),
                    "requirement_confirmation_status": state.get("requirement_confirmation_status", "unclear"),
                })
                await emit_sse(None)
                return

        # All nodes completed
        final_msgs = [m for m in state.get("messages", []) if isinstance(m, AIMessage)]
        final_text = final_msgs[-1].content if final_msgs else "执行完毕。"
        await emit_sse({
            "type": "final",
            "response": final_text,
            "task_phase": "completed",
            "requirement_confirmation_status": state.get("requirement_confirmation_status", ""),
        })
        delete_session(session_id)

    except Exception as e:
        logger.error(f"StepExecutor error: {e}", exc_info=True)
        await emit_sse({"type": "error", "message": str(e)})

    # Signal end of SSE stream
    await emit_sse(None)
