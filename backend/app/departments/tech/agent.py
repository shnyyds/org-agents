from typing import List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from app.state import AgentState
from app.core.llm import get_llm
from app.departments.base import DepartmentLeadAgent
from app.departments.tech.sub_agents import product_agent_node, developer_agent_node, tester_agent_node, devops_agent_node
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from app.utils.logger import public_service_logger as logger
from app.utils.messages import get_last_user_message
from app.utils.labels import format_sub_agent_plan
from app.utils.streaming import stream_llm_text
import json

class TechLeadAgent(DepartmentLeadAgent):
    """
    技术部部门长智能体
    内部串行编排：产品 -> 开发 -> 检测 -> (不合格回流开发) -> 运维
    """
    def __init__(self):
        super().__init__(name="TechLead", department="TECH")

    def setup_workflow(self):
        """
        TECH Internal Workflow: 
        1. Lead Plan (Init & Dynamic Routing)
        2. Sub-Agent Dispatcher
        3. Sub-Agents: product, developer, tester, devops
        """
        self.llm = get_llm()
        
        # Add Nodes
        self.workflow.add_node("tech_lead_plan", self.tech_lead_plan_node)
        self.workflow.add_node("dispatch_sub_agent", self.dispatch_sub_agent_node)
        self.workflow.add_node("product", product_agent_node)
        self.workflow.add_node("developer", developer_agent_node)
        self.workflow.add_node("tester", tester_agent_node)
        self.workflow.add_node("devops", devops_agent_node)
        
        # Set Entry Point
        self.workflow.set_entry_point("tech_lead_plan")
        
        # Edges
        self.workflow.add_edge("tech_lead_plan", "dispatch_sub_agent")
        
        # Conditional Edges from Dispatcher
        self.workflow.add_conditional_edges(
            "dispatch_sub_agent",
            self.route_sub_agent,
            {
                "product": "product",
                "developer": "developer",
                "tester": "tester",
                "devops": "devops",
                "finish": END
            }
        )
        
        # All sub-agents go back to dispatcher to check for next step in sub_plan
        self.workflow.add_edge("product", "dispatch_sub_agent")
        
        # Developer goes to tester after work, or dispatcher if no tester planned
        self.workflow.add_edge("developer", "dispatch_sub_agent")
        
        # Special case: Tester can return to Developer on fail, or go back to dispatcher on pass
        self.workflow.add_conditional_edges(
            "tester",
            self.decide_tester_outcome,
            {
                "pass": "dispatch_sub_agent",
                "fail": "developer"
            }
        )
        
        self.workflow.add_edge("devops", "dispatch_sub_agent")

    async def tech_lead_plan_node(self, state: AgentState) -> Dict[str, Any]:
        """
        部长开场节点：动态分析需求，制定部门内部的执行子计划（sub_plan）。
        """
        # 优先检查是否已经有预设好的 sub_plan (来自直接对话模式)
        if state.get("sub_plan") and state.get("context", {}).get("target_type") == "agent":
            target_agent = state["sub_plan"][0]
            logger.info(f"Tech Lead: Direct agent mode detected for {target_agent}. Skipping dynamic planning.")
            return {
                "sub_plan": state["sub_plan"],
                "sub_plan_step": 0,
                "active_agent": "星核StarCore",
                "messages": [AIMessage(content=f"👨‍💼 星核StarCore：收到！由于您直接指挥【{target_agent}】，我将立即为您转接该智能体。")],
                "execution_log": [{"agent": "星核StarCore", "status": f"直接转接至子智能体: {target_agent}", "department": "TECH"}]
            }

        # Get the original user query
        query = get_last_user_message(state, "No query found")
        intent_analysis = state.get("intent_analysis", {})

        logger.info(f"Tech Lead: Dynamically planning for query: {query}")

        system_prompt = f"""
        你是星核StarCore，公共服务技术部的核心调度者。你的任务是根据用户的原始指令和 CEO 的意图分析，动态编排技术部内部的执行流程。

        CEO 意图分析：{json.dumps(intent_analysis, ensure_ascii=False)}

        可选子智能体：
        - product: 蓝图BlueForm (PRD产出/需求分析)
        - developer: 灵码SmartCode (核心代码编写)
        - tester: 检博士CheckDoc (代码质量/安全检测)
        - devops: 运小盾OpsShield (部署/上线)
        
        注意：如果用户明确说明不需要某个岗位（如“不需要产品”、“不测试”），请在 sub_plan 中排除它。
        
        请按以下 JSON 格式返回：
        {{
            "sub_plan": ["岗位代码1", "岗位代码2", ...],
            "reason": "编排理由"
        }}
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=query)
        ]

        try:
            logger.info("Tech Lead: Calling LLM for sub-plan...")
            # Use streaming for real-time output
            response_text = await stream_llm_text(
                llm=self.llm,
                prompt=messages,
                state=state,
                node_name="tech_lead_plan",
                active_agent="星核StarCore",
            )
            content = response_text.strip()
            logger.info(f"Tech Lead: LLM Raw Response: {content}")

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()

            plan_data = json.loads(content)
            sub_plan = plan_data.get("sub_plan", ["product", "developer", "tester", "devops"])
            reason = plan_data.get("reason", "标准技术实现流程")
            logger.info(f"Tech Lead: Decided sub_plan: {sub_plan}, reason: {reason}")
        except Exception as e:
            logger.error(f"Tech Lead: Error parsing sub-plan: {str(e)}")
            sub_plan = ["developer"] if "只要写代码" in query else ["product", "developer", "tester", "devops"]
            reason = "解析失败，触发安全降级编排"

        thought_msg = f"👨‍💼 星核StarCore：\n收到 CEO 任务。我已完成内部资源评估：\n"
        thought_msg += f"1. 执行路径：{format_sub_agent_plan(sub_plan)}\n"
        thought_msg += f"2. 编排策略：{reason}\n"
        thought_msg += "正在启动部门内部流水线..."

        return {
            "sub_plan": sub_plan,
            "sub_plan_step": 0,
            "messages": [AIMessage(content=thought_msg)],
            "active_agent": "星核StarCore",
            "execution_log": [{"agent": "星核StarCore", "status": f"制定内部子计划: {format_sub_agent_plan(sub_plan)}", "department": "TECH"}],
            "current_department": "TECH"
        }

    async def dispatch_sub_agent_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Dispatcher: Moves to the next sub-agent in the sub_plan.
        """
        sub_plan = state.get("sub_plan", [])
        step = state.get("sub_plan_step", 0)
        
        if step >= len(sub_plan):
            return {"next_step": "finish"}
            
        next_agent_id = sub_plan[step]
        return {
            "sub_plan_step": step + 1,
            "active_agent": next_agent_id,
            "next_step": next_agent_id
        }

    def route_sub_agent(self, state: AgentState) -> str:
        """
        Routes to the specific sub-agent node or finishes the department work.
        """
        next_step = state.get("next_step")
        if next_step in ["product", "developer", "tester", "devops"]:
            return next_step
        return "finish"

    def decide_tester_outcome(self, state: AgentState) -> str:
        """
        Special logic for tester: can fail and loop back to developer.
        """
        if not state.get("test_passed", True):
            logger.warning("Tech Lead: Tester failed. Looping back to developer.")
            return "fail"
        return "pass"

    def decide_next_step(self, state: AgentState) -> str:
        # Legacy method for base class compatibility, not used in the new dynamic flow
        return "pass"

    def decide_next_step(self, state: AgentState) -> str:
        """
        Logic for deciding if testing passed.
        """
        if state.get("test_passed", True):
            logger.info("Tech Lead: Testing passed. Proceeding to DevOps.")
            return "pass"
        else:
            logger.warning("Tech Lead: Testing failed. Returning to Developer.")
            return "fail"

    async def run(self, state: AgentState) -> Dict[str, Any]:
        """
        Executes the TECH department workflow.
        """
        logger.info("Tech Lead: Orchestrating tech pipeline.")
        app = self.workflow.compile()
        final_state = await app.ainvoke(state)
        
        # Summary for CEO
        summary = f"""
技术部执行完毕：
- PRD 产出：已完成
- 代码编写：已完成
- 测试报告：{json.dumps(final_state.get('test_report', {}), ensure_ascii=False)}
- 部署状态：{final_state.get('deployment_report', '未部署')}
        """
        
        return {
            "messages": [AIMessage(content=summary)],
            "results": {
                "TECH": {
                    "prd": final_state.get("prd"),
                    "code": final_state.get("code"),
                    "test_report": final_state.get("test_report"),
                    "deployment_report": final_state.get("deployment_report")
                }
            },
            "active_agent": final_state.get("active_agent")
        }

# Factory instance
tech_lead = TechLeadAgent()
