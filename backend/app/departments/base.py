"""
配置驱动的通用部门长基类。
标准部门（CS/SALES/REPAIR/USER/MARKET）只需提供部门代码即可自动构建完整的 LangGraph 工作流。
"""
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
import json

from app.state import AgentState
from app.core.agent import DepartmentLead
from app.core.llm import get_llm
from app.utils.logger import public_service_logger as logger
from app.utils.messages import get_last_user_message, get_history_messages
from app.utils.labels import format_sub_agent_plan
from app.utils.streaming import stream_llm_text
from app.utils.agent_knowledge import resolve_system_prompt
from app.agent_config import agent_config_service


class DepartmentLeadAgent(DepartmentLead):
    """
    通用部门长智能体。
    传入 department 代码后，自动从 registry 读取配置并构建工作流。
    """

    def __init__(self, department: str):
        from app.departments.registry import DEPARTMENT_CONFIGS, get_sub_agent_nodes

        cfg = DEPARTMENT_CONFIGS[department]
        super().__init__(name=cfg["name"], department=department)

        self._cfg = cfg
        self._display_name = cfg["display_name"]
        self._sub_agent_ids = cfg["sub_agents"]
        self._default_sub_plan = cfg["default_sub_plan"]
        self._default_reason = cfg["default_reason"]
        self._sub_agent_nodes = get_sub_agent_nodes(department)

        self.llm = get_llm()
        self.workflow = StateGraph(AgentState)
        self.setup_workflow()

    # ------------------------------------------------------------------
    # 工作流构建（自动）
    # ------------------------------------------------------------------

    def setup_workflow(self):
        plan_node_name = f"{self.department.lower()}_lead_plan"

        self.workflow.add_node(plan_node_name, self._lead_plan_node)
        self.workflow.add_node("dispatch_sub_agent", self._dispatch_node)

        for aid, node_fn in self._sub_agent_nodes.items():
            self.workflow.add_node(aid, node_fn)

        self.workflow.set_entry_point(plan_node_name)
        self.workflow.add_edge(plan_node_name, "dispatch_sub_agent")

        route_map = {aid: aid for aid in self._sub_agent_ids}
        route_map["finish"] = END
        self.workflow.add_conditional_edges(
            "dispatch_sub_agent", self._route_sub_agent, route_map
        )

        for aid in self._sub_agent_ids:
            self.workflow.add_edge(aid, "dispatch_sub_agent")

    # ------------------------------------------------------------------
    # 通用节点：部门长规划
    # ------------------------------------------------------------------

    async def _lead_plan_node(self, state: AgentState) -> Dict[str, Any]:
        # 直接对话模式：跳过动态规划
        if state.get("sub_plan") and state.get("context", {}).get("target_type") == "agent":
            target = state["sub_plan"][0]
            logger.info(f"{self._display_name}: Direct agent mode for {target}.")
            return {
                "sub_plan": state["sub_plan"],
                "sub_plan_step": 0,
                "active_agent": self._display_name,
                "messages": [AIMessage(content=f"👨‍💼 {self._display_name}：收到！由于您直接指挥【{target}】，我将立即为您转接该智能体。")],
                "execution_log": [{"agent": self._display_name, "status": f"直接转接至子智能体: {target}", "department": self.department}],
            }

        query = get_last_user_message(state, "No query found")
        system_prompt = resolve_system_prompt(self.department, query=query)

        # 获取上下文历史
        context_turns = agent_config_service.get_effective_config(self.department).get("context_turns", 0)
        history = get_history_messages(state, context_turns)

        messages = [SystemMessage(content=system_prompt), *history, HumanMessage(content=query)]

        response_text = await stream_llm_text(
            llm=self.llm,
            prompt=messages,
            state=state,
            node_name=f"{self.department.lower()}_lead_plan",
            active_agent=self._display_name,
        )

        try:
            content = response_text.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            plan_data = json.loads(content)
            sub_plan = plan_data.get("sub_plan", self._default_sub_plan)
            reason = plan_data.get("reason", self._default_reason)
        except Exception:
            sub_plan = list(self._default_sub_plan)
            reason = "按默认流程执行"

        thought = (
            f"👨‍💼 {self._display_name}：\n收到 CEO 任务。我已完成内部资源评估：\n"
            f"1. 执行路径：{format_sub_agent_plan(sub_plan)}\n"
            f"2. 编排策略：{reason}\n"
            "正在启动部门内部流水线..."
        )

        return {
            "sub_plan": sub_plan,
            "sub_plan_step": 0,
            "messages": [AIMessage(content=thought)],
            "active_agent": self._display_name,
            "execution_log": [{"agent": self._display_name, "status": f"制定内部子计划: {format_sub_agent_plan(sub_plan)}", "department": self.department}],
            "current_department": self.department,
        }

    # ------------------------------------------------------------------
    # 通用节点：分发 & 路由
    # ------------------------------------------------------------------

    async def _dispatch_node(self, state: AgentState) -> Dict[str, Any]:
        sub_plan = state.get("sub_plan", [])
        step = state.get("sub_plan_step", 0)
        if step >= len(sub_plan):
            return {"next_step": "finish"}
        return {"sub_plan_step": step + 1, "next_step": sub_plan[step]}

    def _route_sub_agent(self, state: AgentState) -> str:
        next_step = state.get("next_step")
        if next_step in self._sub_agent_ids:
            return next_step
        return "finish"

    # ------------------------------------------------------------------
    # run / orchestrate
    # ------------------------------------------------------------------

    async def run(self, state: AgentState) -> Dict[str, Any]:
        logger.info(f"{self._display_name}: Orchestrating pipeline.")
        app = self.workflow.compile()
        return await app.ainvoke(state)

    async def orchestrate(self, state: AgentState) -> Dict[str, Any]:
        return await self.run(state)
