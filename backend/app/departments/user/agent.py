from typing import List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from app.state import AgentState
from app.core.llm import get_llm
from app.departments.base import DepartmentLeadAgent
from app.departments.user.sub_agents import device_agent_node, user_repair_agent_node
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
import json
from app.utils.logger import public_service_logger as logger
from app.utils.messages import get_last_user_message
from app.utils.labels import format_sub_agent_plan
from app.utils.streaming import stream_llm_text

class UserLeadAgent(DepartmentLeadAgent):
    def __init__(self):
        super().__init__(name="UserLead", department="USER")
        self.llm = get_llm()

    def setup_workflow(self):
        self.workflow.add_node("user_lead_plan", self.user_lead_plan_node)
        self.workflow.add_node("dispatch_sub_agent", self.dispatch_sub_agent_node)
        self.workflow.add_node("device", device_agent_node)
        self.workflow.add_node("repair_portal", user_repair_agent_node)
        
        self.workflow.set_entry_point("user_lead_plan")
        self.workflow.add_edge("user_lead_plan", "dispatch_sub_agent")
        
        self.workflow.add_conditional_edges(
            "dispatch_sub_agent",
            self.route_sub_agent,
            {
                "device": "device",
                "repair_portal": "repair_portal",
                "finish": END
            }
        )
        
        self.workflow.add_edge("device", "dispatch_sub_agent")
        self.workflow.add_edge("repair_portal", "dispatch_sub_agent")

    async def user_lead_plan_node(self, state: AgentState) -> Dict[str, Any]:
        """
        部长开场节点：动态编排用户端流程。
        """
        # 优先检查是否已经有预设好的 sub_plan (来自直接对话模式)
        if state.get("sub_plan") and state.get("context", {}).get("target_type") == "agent":
            target_agent = state["sub_plan"][0]
            logger.info(f"User Lead: Direct agent mode detected for {target_agent}. Skipping dynamic planning.")
            return {
                "sub_plan": state["sub_plan"],
                "sub_plan_step": 0,
                "active_agent": "用户端部长",
                "messages": [AIMessage(content=f"👨‍💼 用户端部长：收到！由于您直接指挥【{target_agent}】，我将立即为您转接该智能体。")],
                "execution_log": [{"agent": "用户端部长", "status": f"直接转接至子智能体: {target_agent}", "department": "USER"}]
            }

        query = get_last_user_message(state, "No query found")
        system_prompt = """
        你是一位公共服务用户管理部部长。请根据任务需求动态编排流程。
        可选子智能体：
        - device: 服务状态智能体 (IoT状态查询)
        - repair_portal: 申报入口智能体 (自主申报工单)
        
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
            node_name="user_lead_plan",
            active_agent="用户端部长",
        )
        try:
            content = response_text.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            plan_data = json.loads(content)
            sub_plan = plan_data.get("sub_plan", ["device"])
            reason = plan_data.get("reason", "标准用户端服务流程")
        except:
            sub_plan = ["device"]
            reason = "按默认流程执行"

        thought_msg = f"👨‍💼 用户端部长：\n收到 CEO 任务。我已完成内部资源评估：\n"
        thought_msg += f"1. 执行路径：{format_sub_agent_plan(sub_plan)}\n"
        thought_msg += f"2. 编排策略：{reason}\n"
        thought_msg += "正在启动部门内部流水线..."

        return {
            "sub_plan": sub_plan,
            "sub_plan_step": 0,
            "messages": [AIMessage(content=thought_msg)],
            "active_agent": "用户端部长",
            "execution_log": [{"agent": "用户端部长", "status": f"制定内部子计划: {format_sub_agent_plan(sub_plan)}", "department": "USER"}],
            "current_department": "USER"
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
        if next_step in ["device", "repair_portal"]:
            return next_step
        return "finish"

    async def run(self, state: AgentState) -> Dict[str, Any]:
        logger.info("User Lead: Managing customer portal.")
        app = self.workflow.compile()
        final_state = await app.ainvoke(state)
        
        summary = f"用户端报告：服务设施状态正常（{final_state['results'].get('device_status')}）。"
        return {
            "messages": [AIMessage(content=summary)],
            "results": {"USER": final_state.get("results", {})},
            "active_agent": "服务状态智能体"
        }

user_lead = UserLeadAgent()
