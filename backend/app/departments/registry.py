"""
部门与子智能体配置注册表。
所有部门的部门长和子智能体均由此配置驱动。
"""
import json
from typing import Dict, Any, List, Optional

from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from app.state import AgentState
from app.core.llm import get_llm
from app.utils.logger import public_service_logger as logger
from app.utils.messages import get_first_user_message, get_last_user_message, get_history_messages
from app.utils.agent_knowledge import (
    inject_knowledge_into_prompt,
    resolve_system_prompt,
    resolve_user_prompt,
)
from app.utils.agent_skills import inject_skills_into_prompt
from app.utils.streaming import stream_llm_text
from app.core.backend_selector import use_openclaw
from app.agent_config import agent_config_service

# ---------------------------------------------------------------------------
# 部门配置
# ---------------------------------------------------------------------------
DEPARTMENT_CONFIGS: Dict[str, Dict[str, Any]] = {
    "CS": {
        "name": "CSLead",
        "display_name": "客服部部长",
        "sub_agents": ["faq", "emergency", "human"],
        "default_sub_plan": ["faq"],
        "default_reason": "标准客户服务流程",
    },
    "SALES": {
        "name": "SalesLead",
        "display_name": "销售部部长",
        "sub_agents": ["lead_gen", "quote", "cad"],
        "default_sub_plan": ["lead_gen", "quote", "cad"],
        "default_reason": "标准销售转化流程",
    },
    "REPAIR": {
        "name": "RepairLead",
        "display_name": "运维部部长",
        "sub_agents": ["manager", "master", "worker"],
        "default_sub_plan": ["manager", "master", "worker"],
        "default_reason": "标准维保修复流程",
    },
    "USER": {
        "name": "UserLead",
        "display_name": "用户端部长",
        "sub_agents": ["device", "repair_portal"],
        "default_sub_plan": ["device"],
        "default_reason": "标准用户端服务流程",
    },
    "MARKET": {
        "name": "MarketLead",
        "display_name": "市场部部长",
        "sub_agents": ["analyze_industry", "generate_content"],
        "default_sub_plan": ["analyze_industry", "generate_content"],
        "default_reason": "标准市场策划流程",
    },
    "TECH": {
        "name": "TechLead",
        "display_name": "星核StarCore",
        "sub_agents": ["product", "developer", "tester", "devops"],
        "default_sub_plan": ["product", "developer", "tester", "devops"],
        "default_reason": "标准技术实现流程",
    },
}

# ---------------------------------------------------------------------------
# 子智能体配置
# ---------------------------------------------------------------------------
# input_from: 从 state["results"][key] 读取上游结果（链式智能体）
# result_keys: 写入 state["results"] 的键值，"$content" 表示用 LLM 输出替换
# prefix: 流式输出前缀
# ---------------------------------------------------------------------------
SUB_AGENT_CONFIGS: Dict[str, Dict[str, Any]] = {
    # ── CS ──
    "faq": {
        "display_name": "日常客服智能体",
        "department": "CS",
        "log_status": "FAQ知识库查询完成",
        "result_keys": {"faq_answer": "$content"},
        "next_step": "end",
    },
    "emergency": {
        "display_name": "紧急应急智能体",
        "department": "CS",
        "log_status": "识别紧急场景(公共服务关人)",
        "prefix": "⚠️ ",
        "result_keys": {"rescue_status": "Notified", "emergency_level": "Immediate"},
        "next_step": "end",
    },
    "human": {
        "display_name": "人工客服(兜底)",
        "department": "CS",
        "log_status": "上下文完整移交",
        "result_keys": {"handover_id": "Agent-John"},
        "next_step": "end",
    },
    # ── SALES ──
    "lead_gen": {
        "display_name": "服务咨询专员",
        "department": "SALES",
        "log_status": "服务需求分析完成",
        "prefix": "服务咨询专员：已分析服务需求：\n",
        "result_keys": {"leads": "$content"},
        "next_step": "quote",
    },
    "quote": {
        "display_name": "方案设计专员",
        "department": "SALES",
        "log_status": "服务方案设计完成",
        "prefix": "方案设计专员：服务方案已生成：\n",
        "input_from": "leads",
        "result_keys": {"quote": "$content"},
        "next_step": "cad",
    },
    "cad": {
        "display_name": "实施计划专员",
        "department": "SALES",
        "log_status": "实施计划输出完成",
        "prefix": "实施计划专员：实施计划已产出：\n",
        "input_from": "quote",
        "result_keys": {"cad_drawing": "$content"},
        "next_step": "end",
    },
    # ── REPAIR ──
    "manager": {
        "display_name": "运维经理智能体",
        "department": "REPAIR",
        "log_status": "智能派单完成",
        "prefix": "运维经理：派单任务已下达：\n",
        "result_keys": {"worker": "Worker-001", "assignment": "$content"},
        "next_step": "master",
    },
    "master": {
        "display_name": "维修大师智能体",
        "department": "REPAIR",
        "log_status": "问题智能识别(紧急)",
        "prefix": "维修大师：问题诊断报告：\n",
        "input_from": "assignment",
        "result_keys": {"fault_analysis": "$content"},
        "next_step": "worker",
    },
    "worker": {
        "display_name": "运维人员智能体",
        "department": "REPAIR",
        "log_status": "现场维修执行完成",
        "prefix": "运维人员：现场执行记录：\n",
        "input_from": "fault_analysis",
        "result_keys": {"repair_log": "$content"},
        "next_step": "end",
    },
    # ── USER ──
    "device": {
        "display_name": "服务状态智能体",
        "department": "USER",
        "log_status": "IoT实时状态查询完成",
        "prefix": "服务状态智能体：IoT 实时监测报告：\n",
        "result_keys": {"device_status": "Online", "report": "$content"},
        "next_step": "end",
    },
    "repair_portal": {
        "display_name": "申报入口智能体",
        "department": "USER",
        "log_status": "自主申报工单已生成",
        "prefix": "申报入口智能体：自主申报申请已确认：\n",
        "result_keys": {"order_id": "REPAIR-2024-0001", "confirmation": "$content"},
        "next_step": "end",
    },
    # ── MARKET ──
    "analyze_industry": {
        "display_name": "需求分析专员",
        "department": "MARKET",
        "log_status": "需求全维度分析完成",
        "result_keys": {"industry_analysis": "$content"},
        "next_step": "generate_content",
    },
    "generate_content": {
        "display_name": "宣传推广专员",
        "department": "MARKET",
        "log_status": "多渠道宣传内容生成",
        "input_from": "industry_analysis",
        "result_keys": {},
        "custom_results": True,
        "next_step": "end",
    },
    # ── TECH ──
    "product": {
        "display_name": "蓝图BlueForm",
        "department": "TECH",
        "log_status": "需求解析完成",
        "result_keys": {"product_output": "$content"},
        "next_step": "developer",
    },
    "developer": {
        "display_name": "灵码SmartCode",
        "department": "TECH",
        "log_status": "代码编写完成",
        "input_from": "product_output",
        "result_keys": {"developer_output": "$content"},
        "next_step": "tester",
    },
    "tester": {
        "display_name": "检博士CheckDoc",
        "department": "TECH",
        "log_status": "四维检测完成",
        "input_from": "developer_output",
        "result_keys": {"tester_output": "$content"},
        "next_step": "devops",
    },
    "devops": {
        "display_name": "运小盾OpsShield",
        "department": "TECH",
        "log_status": "部署监控完成",
        "input_from": "tester_output",
        "result_keys": {"devops_output": "$content"},
        "next_step": "end",
    },
}

# ---------------------------------------------------------------------------
# 子智能体节点工厂
# ---------------------------------------------------------------------------
_LLM_NOT_SET = object()
_llm = _LLM_NOT_SET


def _get_llm():
    global _llm
    if _llm is _LLM_NOT_SET:
        _llm = get_llm()
    return _llm


def _build_openclaw_message(
    sys_prompt: str,
    usr_prompt: str,
    history: list = None,
    kb_context: str = "",
    skills_text: str = "",
) -> str:
    """将系统提示词、历史、知识库、技能、用户提示词拼接为单一消息字符串。"""
    parts = [sys_prompt]
    if kb_context:
        parts.append(f"\n\n【参考知识库】\n{kb_context}")
    if skills_text:
        parts.append(f"\n\n【已装载技能】\n{skills_text}")
    if history:
        parts.append("\n\n【对话历史】")
        for msg in history:
            role = "用户" if getattr(msg, "type", "") == "human" else "助手"
            parts.append(f"{role}: {msg.content}")
    parts.append(f"\n\n【用户指令】\n{usr_prompt}")
    return "\n".join(parts)


def create_sub_agent_node(agent_id: str):
    """
    根据配置生成子智能体节点函数。
    使用 SystemMessage + HumanMessage 分离系统提示词和用户提示词。
    """
    cfg = SUB_AGENT_CONFIGS[agent_id]
    display_name = cfg["display_name"]
    department = cfg["department"]
    log_status = cfg["log_status"]
    prefix = cfg.get("prefix", "")
    result_keys = cfg.get("result_keys", {})
    next_step = cfg.get("next_step", "end")
    input_from = cfg.get("input_from")
    custom_results = cfg.get("custom_results", False)

    async def agent_node(state: AgentState) -> Dict[str, Any]:
        llm = _get_llm()
        logger.info(f"{department}: {display_name} executing.")

        # 确定输入内容
        if input_from:
            prev_result = state.get("results", {}).get(input_from)
            original_query = get_first_user_message(state, "No requirement found")
            query_content = prev_result or original_query
            query_for_kb = original_query or prev_result or ""
        else:
            query_content = get_last_user_message(state)
            prev_result = None
            original_query = query_content
            query_for_kb = query_content

        # 构建系统提示词（含知识库注入）
        sys_prompt = resolve_system_prompt(agent_id, query=query_for_kb)
        sys_prompt, kb_names = inject_knowledge_into_prompt(agent_id, query_for_kb, sys_prompt)

        # 技能注入
        sys_prompt, skill_names = inject_skills_into_prompt(agent_id, sys_prompt)

        # 构建用户提示词
        usr_prompt = resolve_user_prompt(agent_id, query=query_content)

        # 获取上下文历史
        context_turns = agent_config_service.get_effective_config(agent_id).get("context_turns", 0)
        history = get_history_messages(state, context_turns)

        messages = [SystemMessage(content=sys_prompt), *history, HumanMessage(content=usr_prompt)]

        if use_openclaw(agent_id):
            from app.utils.openclaw_streaming import stream_openclaw_text
            oc_message = _build_openclaw_message(sys_prompt, usr_prompt, history)
            content = await stream_openclaw_text(
                agent_id=f"org_{agent_id}",
                message=oc_message,
                state=state,
                node_name=agent_id,
                active_agent=display_name,
                prefix=prefix,
            )
        else:
            content = await stream_llm_text(
                llm=llm,
                prompt=messages,
                state=state,
                node_name=agent_id,
                active_agent=display_name,
                prefix=prefix,
            )

        # 构建 results
        kb_note = f"（已参考{'、'.join(kb_names)}）" if kb_names else ""
        skill_note = f"（已装载技能{'、'.join(skill_names)}）" if skill_names else ""
        results = {}
        if custom_results and agent_id == "generate_content":
            results = {
                "MARKET": {
                    "industry_analysis": prev_result or "",
                    "promotional_content": content,
                }
            }
        else:
            for k, v in result_keys.items():
                results[k] = content if v == "$content" else v

        return {
            "messages": [AIMessage(content=content)],
            "results": results,
            "active_agent": display_name,
            "execution_log": [{"agent": display_name, "status": f"{log_status}{kb_note}{skill_note}", "department": department}],
            "next_step": next_step,
        }

    agent_node.__name__ = f"{agent_id}_agent_node"
    agent_node.__qualname__ = f"{agent_id}_agent_node"
    return agent_node


def get_sub_agent_nodes(department: str) -> Dict[str, Any]:
    """返回某个部门下所有子智能体的 {agent_id: node_function} 映射。"""
    cfg = DEPARTMENT_CONFIGS[department]
    return {aid: create_sub_agent_node(aid) for aid in cfg["sub_agents"]}


# ---------------------------------------------------------------------------
# 部门实例（延迟创建，避免循环导入）
# ---------------------------------------------------------------------------
_department_leads: Dict[str, Any] = {}


def get_department_lead(department: str):
    """获取部门长实例（单例）。"""
    if department not in _department_leads:
        from app.departments.base import DepartmentLeadAgent
        _department_leads[department] = DepartmentLeadAgent(department)
    return _department_leads[department]
