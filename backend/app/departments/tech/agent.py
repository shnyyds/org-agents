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
    执行链路：需求分析 -> (澄清?) -> 子计划生成 -> 分发执行 -> 检测回流 -> 运维收尾
    """
    def __init__(self):
        super().__init__(name="TechLead", department="TECH")

    def setup_workflow(self):
        """
        TECH Internal Workflow:
        1. Requirement Analysis (clarity check)
        2. Requirement Clarification (if unclear -> END, wait for user)
        3. Lead Plan (dynamic sub-plan generation)
        4. Sub-Agent Dispatcher
        5. Sub-Agents: product, developer, tester, devops
        """
        self.llm = get_llm()

        # Nodes
        self.workflow.add_node("requirement_analysis", self.requirement_analysis_node)
        self.workflow.add_node("requirement_clarification", self.requirement_clarification_node)
        self.workflow.add_node("tech_lead_plan", self.tech_lead_plan_node)
        self.workflow.add_node("dispatch_sub_agent", self.dispatch_sub_agent_node)
        self.workflow.add_node("product", product_agent_node)
        self.workflow.add_node("developer", developer_agent_node)
        self.workflow.add_node("tester", tester_agent_node)
        self.workflow.add_node("devops", devops_agent_node)

        # Entry point
        self.workflow.set_entry_point("requirement_analysis")

        # After analysis: route to clarification or planning
        self.workflow.add_conditional_edges(
            "requirement_analysis",
            self.route_after_analysis,
            {"clarify": "requirement_clarification", "plan": "tech_lead_plan"}
        )

        # Clarification ends the graph (user needs to respond)
        self.workflow.add_edge("requirement_clarification", END)

        # Plan -> dispatch
        self.workflow.add_edge("tech_lead_plan", "dispatch_sub_agent")

        # Conditional edges from dispatcher
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

        # Sub-agents loop back to dispatcher
        self.workflow.add_edge("product", "dispatch_sub_agent")
        self.workflow.add_edge("developer", "dispatch_sub_agent")
        self.workflow.add_conditional_edges(
            "tester",
            self.decide_tester_outcome,
            {"pass": "dispatch_sub_agent", "fail": "developer"}
        )
        self.workflow.add_edge("devops", "dispatch_sub_agent")

    # ------------------------------------------------------------------
    # Node: Requirement Analysis
    # ------------------------------------------------------------------

    async def requirement_analysis_node(self, state: AgentState) -> Dict[str, Any]:
        """
        判断用户需求是否足够清晰。
        直接对话模式或已确认需求时跳过分析。
        支持最多3次澄清循环。
        """
        query = get_last_user_message(state, "No query found")

        # Direct agent mode: skip analysis entirely
        if state.get("context", {}).get("target_type") == "agent":
            return {
                "task_phase": "sub_plan_generation",
                "requirement_confirmation_status": "confirmed",
                "original_requirement": query,
                "confirmed_requirement": query,
            }

        # Track clarification attempts
        clarification_count = state.get("context", {}).get("_clarification_count", 0)
        max_clarifications = 3

        # If user is responding to a previous clarification, re-analyze with accumulated context
        if state.get("task_phase") == "requirement_clarification":
            original = state.get("original_requirement", "")
            accumulated_context = f"{original}\n补充说明：{query}"

            # If we've reached max clarifications, force proceed
            if clarification_count >= max_clarifications:
                logger.info(f"Tech Lead: Max clarifications ({max_clarifications}) reached, proceeding with available info.")
                return {
                    "task_phase": "sub_plan_generation",
                    "requirement_confirmation_status": "confirmed",
                    "latest_supplement": query,
                    "confirmed_requirement": accumulated_context,
                    "context": {**state.get("context", {}), "_clarification_count": clarification_count},
                }

            # Re-analyze with accumulated context
            query = accumulated_context
            logger.info(f"Tech Lead: Re-analyzing requirement after clarification (attempt {clarification_count + 1}/{max_clarifications})")

        original = state.get("original_requirement") or query

        logger.info(f"Tech Lead: Analyzing requirement clarity for: {query}")

        system_prompt = """你是星核StarCore，技术部的核心调度者。
在开始任何技术工作之前，你需要先判断用户的需求是否足够清晰可执行。

判断标准：
1. 是否明确了要做什么（功能目标）
2. 是否有基本的技术方向或约束（语言、框架、平台等）
3. 是否存在严重歧义或缺失关键信息

请按以下 JSON 格式返回（不要包含其他内容）：
如果需求清晰：{"status": "clear", "confirmed_requirement": "整理后的需求描述", "reason": "判断理由"}
如果需求不清晰：{"status": "unclear", "questions": ["需要澄清的问题1", "问题2"], "reason": "判断理由"}"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=query)
        ]

        try:
            # Use ainvoke (not streaming) — this is internal analysis, not user-facing output
            response = await self.llm.ainvoke(messages)
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif content.startswith("```"):
                content = content[3:].rstrip("`").strip()

            analysis = json.loads(content)
            status = analysis.get("status", "clear")
            logger.info(f"Tech Lead: Requirement analysis result: {status}")
        except Exception as e:
            logger.error(f"Tech Lead: Requirement analysis parse error: {e}")
            status = "clear"
            analysis = {"status": "clear", "confirmed_requirement": query, "reason": "解析失败，默认视为清晰"}

        if status == "clear":
            confirmed = analysis.get("confirmed_requirement", query)
            return {
                "task_phase": "sub_plan_generation",
                "requirement_confirmation_status": "clear",
                "original_requirement": original,
                "confirmed_requirement": confirmed,
                "active_agent": "星核StarCore",
                "execution_log": [{"agent": "星核StarCore", "status": "需求分析完成，需求清晰", "department": "TECH"}],
            }
        else:
            questions = analysis.get("questions", ["请补充更多细节"])
            new_count = clarification_count + 1
            remaining = max_clarifications - new_count
            return {
                "task_phase": "requirement_analysis",
                "requirement_confirmation_status": "unclear",
                "original_requirement": original,
                "confirmed_requirement": "",
                "active_agent": "星核StarCore",
                "execution_log": [{"agent": "星核StarCore", "status": f"需求分析完成，需求不够清晰 (剩余澄清次数: {remaining})", "department": "TECH"}],
                "context": {
                    **state.get("context", {}),
                    "_clarification_questions": questions,
                    "_clarification_count": new_count,
                    "_clarification_remaining": remaining,
                },
            }

    # ------------------------------------------------------------------
    # Node: Requirement Clarification
    # ------------------------------------------------------------------

    async def requirement_clarification_node(self, state: AgentState) -> Dict[str, Any]:
        """
        需求不清晰时，生成追问消息，graph 在此 END 等待用户回复。
        显示剩余澄清次数。
        """
        questions = state.get("context", {}).get("_clarification_questions", ["请补充更多细节"])
        remaining = state.get("context", {}).get("_clarification_remaining", 2)
        question_text = "\n".join(f"  {i+1}. {q}" for i, q in enumerate(questions))

        msg = f"星核StarCore：在开始技术工作之前，我需要确认以下几点：\n{question_text}\n\n请补充以上信息，我将为您制定最优执行方案。（剩余澄清次数：{remaining}）"

        return {
            "task_phase": "requirement_clarification",
            "requirement_confirmation_status": "unclear",
            "messages": [AIMessage(content=msg)],
            "active_agent": "星核StarCore",
            "execution_log": [{"agent": "星核StarCore", "status": "等待用户补充需求", "department": "TECH"}],
        }

    # ------------------------------------------------------------------
    # Routing: after requirement analysis
    # ------------------------------------------------------------------

    def route_after_analysis(self, state: AgentState) -> str:
        status = state.get("requirement_confirmation_status", "clear")
        if status == "unclear":
            return "clarify"
        return "plan"

    # ------------------------------------------------------------------
    # Node: Tech Lead Plan (sub-plan generation)
    # ------------------------------------------------------------------

    async def tech_lead_plan_node(self, state: AgentState) -> Dict[str, Any]:
        """
        部长开场节点：动态分析需求，制定部门内部的执行子计划（sub_plan）。
        """
        # Direct agent mode: skip dynamic planning
        if state.get("sub_plan") and state.get("context", {}).get("target_type") == "agent":
            target_agent = state["sub_plan"][0]
            logger.info(f"Tech Lead: Direct agent mode detected for {target_agent}.")
            return {
                "sub_plan": state["sub_plan"],
                "sub_plan_step": 0,
                "task_phase": "dispatch_execution",
                "active_agent": "星核StarCore",
                "messages": [AIMessage(content=f"星核StarCore：收到！由于您直接指挥【{target_agent}】，我将立即为您转接该智能体。")],
                "execution_log": [{"agent": "星核StarCore", "status": f"直接转接至子智能体: {target_agent}", "department": "TECH"}]
            }

        query = state.get("confirmed_requirement") or get_last_user_message(state, "No query found")
        intent_analysis = state.get("intent_analysis", {})

        logger.info(f"Tech Lead: Dynamically planning for query: {query}")

        system_prompt = f"""你是星核StarCore，公共服务技术部的核心调度者。你的任务是根据用户的原始指令和 CEO 的意图分析，动态编排技术部内部的执行流程。

CEO 意图分析：{json.dumps(intent_analysis, ensure_ascii=False)}

可选子智能体：
- product: 蓝图BlueForm (PRD产出/需求分析)
- developer: 灵码SmartCode (核心代码编写)
- tester: 检博士CheckDoc (代码质量/安全检测)
- devops: 运小盾OpsShield (部署/上线)

注意：如果用户明确说明不需要某个岗位（如"不需要产品"、"不测试"），请在 sub_plan 中排除它。

请按以下 JSON 格式返回：
{{"sub_plan": ["岗位代码1", "岗位代码2", ...], "reason": "编排理由"}}"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=query)
        ]

        try:
            logger.info("Tech Lead: Calling LLM for sub-plan...")
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

        thought_msg = f"星核StarCore：\n收到任务。我已完成内部资源评估：\n"
        thought_msg += f"1. 执行路径：{format_sub_agent_plan(sub_plan)}\n"
        thought_msg += f"2. 编排策略：{reason}\n"
        thought_msg += "正在启动部门内部流水线..."

        return {
            "sub_plan": sub_plan,
            "sub_plan_step": 0,
            "task_phase": "sub_plan_generation",
            "confirmed_requirement": state.get("confirmed_requirement", query),
            "messages": [AIMessage(content=thought_msg)],
            "active_agent": "星核StarCore",
            "execution_log": [{"agent": "星核StarCore", "status": f"制定内部子计划: {format_sub_agent_plan(sub_plan)}", "department": "TECH"}],
            "current_department": "TECH"
        }

    # ------------------------------------------------------------------
    # Node: Dispatcher
    # ------------------------------------------------------------------

    async def dispatch_sub_agent_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Dispatcher: Moves to the next sub-agent in the sub_plan.
        """
        sub_plan = state.get("sub_plan", [])
        step = state.get("sub_plan_step", 0)

        if step >= len(sub_plan):
            return {
                "next_step": "finish",
                "task_phase": "completed",
                "current_executor": "",
            }

        next_agent_id = sub_plan[step]

        phase = "dispatch_execution"
        if next_agent_id == "devops":
            phase = "ops_finish"

        return {
            "sub_plan_step": step + 1,
            "active_agent": next_agent_id,
            "next_step": next_agent_id,
            "task_phase": phase,
            "current_executor": next_agent_id,
        }

    # ------------------------------------------------------------------
    # Routing helpers
    # ------------------------------------------------------------------

    def route_sub_agent(self, state: AgentState) -> str:
        next_step = state.get("next_step")
        if next_step in ["product", "developer", "tester", "devops"]:
            return next_step
        return "finish"

    def decide_tester_outcome(self, state: AgentState) -> str:
        if not state.get("test_passed", True):
            reflow_count = state.get("reflow_count", 0)
            max_reflow = state.get("max_reflow", 2)
            if reflow_count <= max_reflow:
                logger.warning(f"Tech Lead: Tester failed (reflow {reflow_count}/{max_reflow}). Looping back to developer.")
                return "fail"
            logger.warning("Tech Lead: Max reflow reached. Forcing pass to prevent infinite loop.")
        return "pass"

    def decide_next_step(self, state: AgentState) -> str:
        if state.get("test_passed", True):
            return "pass"
        return "fail"

    # ------------------------------------------------------------------
    # Run (for CEO invocation)
    # ------------------------------------------------------------------

    async def run(self, state: AgentState) -> Dict[str, Any]:
        logger.info("Tech Lead: Orchestrating tech pipeline.")
        app = self.workflow.compile()
        final_state = await app.ainvoke(state)

        summary = f"""技术部执行完毕：
- PRD 产出：已完成
- 代码编写：已完成
- 测试报告：{json.dumps(final_state.get('test_report', {}), ensure_ascii=False)}
- 部署状态：{final_state.get('deployment_report', '未部署')}"""

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
            "active_agent": final_state.get("active_agent"),
            "task_phase": final_state.get("task_phase", "completed"),
        }

# Factory instance
tech_lead = TechLeadAgent()

