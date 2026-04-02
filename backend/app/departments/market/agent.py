from typing import List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from app.state import AgentState
from app.departments.base import DepartmentLeadAgent
from app.core.llm import get_llm
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.utils.logger import public_service_logger as logger
from app.utils.messages import get_last_user_message
from app.utils.labels import format_sub_agent_plan
from app.utils.agent_knowledge import inject_knowledge_into_prompt
from app.utils.streaming import stream_llm_text
import json

class MarketLeadAgent(DepartmentLeadAgent):
    """
    Market Department Lead Agent.
    Orchestrates industry analysis and content creation.
    """
    def __init__(self):
        super().__init__(name="MarketLead", department="MARKET")
        self.llm = get_llm()

    def setup_workflow(self):
        """
        MARKET Internal Workflow: Dynamic Routing
        """
        self.workflow.add_node("market_lead_plan", self.market_lead_plan_node)
        self.workflow.add_node("dispatch_sub_agent", self.dispatch_sub_agent_node)
        self.workflow.add_node("analyze_industry", self.analyze_industry_node)
        self.workflow.add_node("generate_content", self.generate_content_node)
        
        self.workflow.set_entry_point("market_lead_plan")
        
        self.workflow.add_edge("market_lead_plan", "dispatch_sub_agent")
        
        self.workflow.add_conditional_edges(
            "dispatch_sub_agent",
            self.route_sub_agent,
            {
                "analyze_industry": "analyze_industry",
                "generate_content": "generate_content",
                "finish": END
            }
        )
        
        self.workflow.add_edge("analyze_industry", "dispatch_sub_agent")
        self.workflow.add_edge("generate_content", "dispatch_sub_agent")

    async def market_lead_plan_node(self, state: AgentState) -> Dict[str, Any]:
        """
        部长开场节点：动态编排市场部流程。
        """
        # 优先检查是否已经有预设好的 sub_plan (来自直接对话模式)
        if state.get("sub_plan") and state.get("context", {}).get("target_type") == "agent":
            target_agent = state["sub_plan"][0]
            logger.info(f"Market Lead: Direct agent mode detected for {target_agent}. Skipping dynamic planning.")
            return {
                "sub_plan": state["sub_plan"],
                "sub_plan_step": 0,
                "active_agent": "市场部部长",
                "messages": [AIMessage(content=f"👨‍💼 市场部部长：收到！由于您直接指挥【{target_agent}】，我将立即为您转接该智能体。")],
                "execution_log": [{"agent": "市场部部长", "status": f"直接转接至子智能体: {target_agent}", "department": "MARKET"}]
            }

        query = get_last_user_message(state, "No query found")
        system_prompt = """
        你是一位企业级多智能体协作系统的市场部部长。请根据任务需求动态编排流程。
        可选子智能体：
        - analyze_industry: 需求分析专员 (公众需求/趋势分析)
        - generate_content: 宣传推广专员 (文案/内容生成)

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
            node_name="market_lead_plan",
            active_agent="市场部部长",
        )
        try:
            content = response_text.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            plan_data = json.loads(content)
            sub_plan = plan_data.get("sub_plan", ["analyze_industry", "generate_content"])
            reason = plan_data.get("reason", "标准市场策划流程")
        except:
            sub_plan = ["analyze_industry", "generate_content"]
            reason = "按默认流程执行"

        thought_msg = f"👨‍💼 市场部部长：\n收到 CEO 任务。我已完成内部资源评估：\n"
        thought_msg += f"1. 执行路径：{format_sub_agent_plan(sub_plan)}\n"
        thought_msg += f"2. 编排策略：{reason}\n"
        thought_msg += "正在启动部门内部流水线..."

        return {
            "sub_plan": sub_plan,
            "sub_plan_step": 0,
            "messages": [AIMessage(content=thought_msg)],
            "active_agent": "市场部部长",
            "execution_log": [{"agent": "市场部部长", "status": f"制定内部子计划: {format_sub_agent_plan(sub_plan)}", "department": "MARKET"}],
            "current_department": "MARKET"
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
        if next_step in ["analyze_industry", "generate_content"]:
            return next_step
        return "finish"

    async def analyze_industry_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Industry Analysis Agent (Node 1)
        """
        query = state["messages"][-1].content
        logger.info(f"Market: Analyzing industry for query: {query}")
        prompt, kb_names = inject_knowledge_into_prompt(
            "analyze_industry",
            query,
            f"你是一位公共服务需求分析师。请围绕以下需求给出公众需求趋势、服务特征和落地建议，输出结构化分析：\n需求：{query}",
        )
        analysis_result = (
            await stream_llm_text(
                llm=self.llm,
                prompt=prompt,
                state=state,
                node_name="analyze_industry",
                active_agent="需求分析专员",
            )
        ).strip()

        return {
            "messages": [AIMessage(content=analysis_result)],
            "results": {"industry_analysis": analysis_result},
            "active_agent": "需求分析专员",
            "execution_log": [{"agent": "需求分析专员", "status": f"需求全维度分析完成{'（已参考' + '、'.join(kb_names) + '）' if kb_names else ''}", "department": "MARKET"}],
            "next_step": "generate_content"
        }

    async def generate_content_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Content Generation Agent (Node 2)
        """
        analysis = state["results"].get("industry_analysis", {})
        logger.info(f"Market: Generating promotional content based on analysis.")
        
        prompt, kb_names = inject_knowledge_into_prompt("generate_content", json.dumps(analysis, ensure_ascii=False), f"""
        基于以下需求分析结果，生成一条适合在社交媒体发布的公共服务宣传文案：
        分析结果: {analysis}

        要求：
        - 语言生动、吸引人。
        - 突出"便民"与"高效"。
        - 包含适当的表情符号。
        """)

        prefix = f"市场部报告：\n\n【分析结果】\n{analysis}\n\n【宣传文案】\n"
        report_content = (
            await stream_llm_text(
                llm=self.llm,
                prompt=prompt,
                state=state,
                node_name="generate_content",
                active_agent="宣传推广专员",
                prefix=prefix,
            )
        ).strip()
        content = report_content[len(prefix):] if report_content.startswith(prefix) else report_content
        
        return {
            "messages": [AIMessage(content=report_content)],
            "results": {
                "MARKET": {
                    "industry_analysis": analysis,
                    "promotional_content": content
                }
            },
            "active_agent": "宣传推广专员",
            "execution_log": [{"agent": "宣传推广专员", "status": f"多渠道宣传内容生成{'（已参考' + '、'.join(kb_names) + '）' if kb_names else ''}", "department": "MARKET"}]
        }

# Factory instance
market_lead = MarketLeadAgent()
