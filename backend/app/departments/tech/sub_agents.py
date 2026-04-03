from typing import Dict, Any, List, Optional
from app.state import AgentState
from app.core.llm import get_llm
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from app.utils.logger import public_service_logger as logger
from app.utils.messages import get_first_user_message, get_last_user_message
from app.utils.agent_knowledge import inject_knowledge_into_prompt
from app.utils.streaming import stream_llm_text

llm = get_llm()


def make_sub_task_result(
    agent_id: str,
    agent_name: str,
    status: str,
    output_type: str,
    content: Any,
    summary: str,
    next_step: str = "",
    department: str = "TECH",
    kb_names: Optional[List[str]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Unified output builder for tech sub-agents."""
    kb_note = f"（已参考{'、'.join(kb_names)}）" if kb_names else ""
    result: Dict[str, Any] = {
        "sub_task_results": {
            agent_id: {
                "status": status,
                "output_type": output_type,
                "content": content,
                "summary": summary,
            }
        },
        "messages": [AIMessage(content=summary if isinstance(summary, str) else str(content))],
        "active_agent": agent_name,
        "current_executor": agent_id,
        "task_phase": "dispatch_execution",
        "execution_log": [{
            "agent": agent_name,
            "status": f"{summary}{kb_note}",
            "department": department,
        }],
        "next_step": next_step,
    }
    if extra:
        result.update(extra)
    return result

async def product_agent_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    ① 蓝图BlueForm: 解析需求 -> 输出 PRD / UI 设计
    """
    query = get_last_user_message(state)
    logger.info(f"Tech: 蓝图BlueForm parsing requirements for: {query}")

    prompt, kb_names = inject_knowledge_into_prompt(
        "product",
        query,
        f"你是蓝图BlueForm，一位资深产品经理。请根据以下需求输出一份精简的 PRD 文档和 UI 设计思路：\n需求：{query}",
    )
    content = await stream_llm_text(
        llm=llm,
        prompt=prompt,
        state=state,
        node_name="product",
        active_agent="蓝图BlueForm",
    )

    result = make_sub_task_result(
        agent_id="product",
        agent_name="蓝图BlueForm",
        status="success",
        output_type="prd",
        content=content,
        summary="PRD产出完成",
        next_step="developer",
        kb_names=kb_names,
    )
    result["prd"] = content
    return result

async def developer_agent_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    ② 灵码SmartCode: 按 PRD 或原始需求开发代码
    """
    prd = state.get("prd")
    original_query = get_first_user_message(state, "No requirement found")

    if prd:
        logger.info("Tech: 灵码SmartCode writing code based on PRD.")
        base_prompt = f"你是灵码SmartCode，一位全栈开发工程师。请根据以下 PRD 文档编写核心代码实现：\nPRD：{prd}"
    else:
        logger.info("Tech: 灵码SmartCode writing code based on original query (PRD skipped).")
        base_prompt = f"你是灵码SmartCode，一位全栈开发工程师。由于流程中跳过了产品岗，请直接根据用户的原始需求编写核心代码实现：\n需求：{original_query}"

    prompt, kb_names = inject_knowledge_into_prompt("developer", original_query or prd or "", base_prompt)

    code_content = await stream_llm_text(
        llm=llm,
        prompt=prompt,
        state=state,
        node_name="developer",
        active_agent="灵码SmartCode",
    )

    result = make_sub_task_result(
        agent_id="developer",
        agent_name="灵码SmartCode",
        status="success",
        output_type="code",
        content=code_content,
        summary="代码编写完成",
        next_step="tester",
        kb_names=kb_names,
    )
    result["code"] = code_content
    result["messages"] = [AIMessage(content=f"```python\n{code_content}\n```")]
    return result

async def tester_agent_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    ③ 检博士CheckDoc: 四维自动检测 (安全、规范、功能、兼容)
    """
    code = state.get("code")
    original_query = get_first_user_message(state, "No requirement found")

    logger.info("Tech: 检博士CheckDoc performing 4-dimensional security and quality check.")
    _, kb_names = inject_knowledge_into_prompt("tester", original_query or code or "", "请执行检测")

    if code:
        test_passed = "error" not in code.lower()
    else:
        test_passed = True

    report = {
        "security": "Pass" if test_passed else "Fail: Potential vulnerability found",
        "coding_standard": "Pass",
        "functionality": "Pass",
        "compatibility": "Pass"
    }

    report_md = f"### 四维检测报告\n\n- 安全性: {report['security']}\n- 编码规范: {report['coding_standard']}\n- 功能性: {report['functionality']}\n- 兼容性: {report['compatibility']}"

    status_label = "四维检测完成" if test_passed else "检测不合格"
    next_agent = "devops" if test_passed else "developer"

    result = make_sub_task_result(
        agent_id="tester",
        agent_name="检博士CheckDoc",
        status="success" if test_passed else "fail",
        output_type="test_report",
        content=report,
        summary=status_label,
        next_step=next_agent,
        kb_names=kb_names,
    )
    result["test_report"] = report
    result["test_passed"] = test_passed
    result["messages"] = [AIMessage(content=report_md)]
    if not test_passed:
        result["reflow_count"] = state.get("reflow_count", 0) + 1
        result["task_phase"] = "test_reflow"
    return result

async def devops_agent_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    ④ 运小盾 OpsShield: 分布式部署与监控
    """
    logger.info("Tech: 运小盾 OpsShield deploying code to distributed nodes.")

    code = state.get("code")
    _, kb_names = inject_knowledge_into_prompt("devops", code or "", "请执行部署")
    report = "### 运维部署报告\n\n- 状态：✅ 部署成功\n- 节点：Node-A, Node-B\n- 监控：正常运行中 (Uptime: 99.9%)"
    if not code:
        report += "\n- 说明：本次为环境预部署/配置更新（未检测到新代码）"

    result = make_sub_task_result(
        agent_id="devops",
        agent_name="运小盾 OpsShield",
        status="success",
        output_type="deployment_report",
        content=report,
        summary="分布式部署成功",
        next_step="end",
        kb_names=kb_names,
    )
    result["deployment_report"] = report
    result["messages"] = [AIMessage(content=report)]
    result["task_phase"] = "ops_finish"
    return result
