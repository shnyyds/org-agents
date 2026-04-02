from typing import List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from app.state import AgentState
from app.core.llm import get_llm
from app.departments.base import DepartmentLeadAgent
from app.departments.repair.sub_agents import repair_manager_agent_node, repair_master_agent_node, repair_worker_agent_node
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
import json
from app.utils.logger import public_service_logger as logger
from app.utils.messages import get_last_user_message
from app.utils.labels import format_sub_agent_plan
from app.utils.streaming import stream_llm_text

class RepairLeadAgent(DepartmentLeadAgent):
    def __init__(self):
        super().__init__(name="RepairLead", department="REPAIR")
        self.llm = get_llm()

    def setup_workflow(self):
        self.workflow.add_node("repair_lead_plan", self.repair_lead_plan_node)
        self.workflow.add_node("dispatch_sub_agent", self.dispatch_sub_agent_node)
        self.workflow.add_node("manager", repair_manager_agent_node)
        self.workflow.add_node("master", repair_master_agent_node)
        self.workflow.add_node("worker", repair_worker_agent_node)
        
        self.workflow.set_entry_point("repair_lead_plan")
        self.workflow.add_edge("repair_lead_plan", "dispatch_sub_agent")
        
        self.workflow.add_conditional_edges(
            "dispatch_sub_agent",
            self.route_sub_agent,
            {
                "manager": "manager",
                "master": "master",
                "worker": "worker",
                "finish": END
            }
        )
        
        self.workflow.add_edge("manager", "dispatch_sub_agent")
        self.workflow.add_edge("master", "dispatch_sub_agent")
        self.workflow.add_edge("worker", "dispatch_sub_agent")

    async def repair_lead_plan_node(self, state: AgentState) -> Dict[str, Any]:
        """
        部长开场节点：动态编排运维部流程。
        """
        # 优先检查是否已经有预设好的 sub_plan (来自直接对话模式)
        if state.get("sub_plan") and state.get("context", {}).get("target_type") == "agent":
            target_agent = state["sub_plan"][0]
            logger.info(f"Repair Lead: Direct agent mode detected for {target_agent}. Skipping dynamic planning.")
            return {
                "sub_plan": state["sub_plan"],
                "sub_plan_step": 0,
                "active_agent": "运维部部长",
                "messages": [AIMessage(content=f"👨‍💼 运维部部长：收到！由于您直接指挥【{target_agent}】，我将立即为您转接该智能体。")],
                "execution_log": [{"agent": "运维部部长", "status": f"直接转接至子智能体: {target_agent}", "department": "REPAIR"}]
            }

        query = get_last_user_message(state, "No query found")
        system_prompt = """
        你是一位公共服务运维部部长。请根据任务需求动态编排流程。
        可选子智能体：
        - manager: 运维经理智能体 (任务分配/派单)
        - master: 维修大师智能体 (问题识别/诊断)
        - worker: 运维人员智能体 (现场执行/修复)
        
        请按以下 JSON 格式返回：
        {
            "sub_plan": ["节点代码1", "节点代码2", ...],
            "reason": "编排理由"
        }
        """
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=query)]
        response_text = await stream_llm_text(
            llm=self.llm,
            prompt=messages,
            state=state,
            node_name="repair_lead_plan",
            active_agent="运维部部长",
        )
        try:
            content = response_text.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            plan_data = json.loads(content)
            sub_plan = plan_data.get("sub_plan", ["manager", "master", "worker"])
            reason = plan_data.get("reason", "标准维保修复流程")
        except:
            sub_plan = ["manager", "master", "worker"]
            reason = "按默认流程执行"

        thought_msg = f"👨‍💼 运维部部长：\n收到 CEO 任务。我已完成内部资源评估：\n"
        thought_msg += f"1. 执行路径：{format_sub_agent_plan(sub_plan)}\n"
        thought_msg += f"2. 编排策略：{reason}\n"
        thought_msg += "正在启动部门内部流水线..."

        return {
            "sub_plan": sub_plan,
            "sub_plan_step": 0,
            "messages": [AIMessage(content=thought_msg)],
            "active_agent": "运维部部长",
            "execution_log": [{"agent": "运维部部长", "status": f"制定内部子计划: {format_sub_agent_plan(sub_plan)}", "department": "REPAIR"}],
            "current_department": "REPAIR"
        }

    async def dispatch_sub_agent_node(self, state: AgentState) -> Dict[str, Any]:
        sub_plan = state.get("sub_plan", [])
        step = state.get("sub_plan_step", 0)
        if step >= len(sub_plan):
            return {"next_step": "finish"}
        next_agent_id = sub_plan[step]
        return {"sub_plan_step": step + 1, "next_step": next_agent_id}

    def route_sub_agent(self, state: AgentState) -> str:
        next_step = state.get("next_step")
        if next_step in ["manager", "master", "worker"]:
            return next_step
        return "finish"

    async def run(self, state: AgentState) -> Dict[str, Any]:
        logger.info("Repair Lead: Orchestrating repair pipeline.")
        app = self.workflow.compile()
        final_state = await app.ainvoke(state)
        
        summary = f"运维部报告：问题识别为 {final_state['results'].get('severity')} 级，由 {final_state['results'].get('worker')} 修复完成。"
        return {
            "messages": [AIMessage(content=summary)],
            "results": {"REPAIR": final_state.get("results", {})},
            "active_agent": "运维人员智能体"
        }

repair_lead = RepairLeadAgent()
