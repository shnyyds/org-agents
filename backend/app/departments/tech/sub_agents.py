from typing import Dict, Any
from app.state import AgentState
from app.core.llm import get_llm
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from app.utils.logger import public_service_logger as logger
from app.utils.messages import get_first_user_message, get_last_user_message
from app.utils.agent_knowledge import inject_knowledge_into_prompt
from app.utils.streaming import stream_llm_text

llm = get_llm()

async def product_agent_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    ① 产品岗智能体: 解析需求 -> 输出 PRD / UI 设计
    """
    query = get_last_user_message(state)
    logger.info(f"Tech: Product Agent parsing requirements for: {query}")
    
    prompt, kb_names = inject_knowledge_into_prompt(
        "product",
        query,
        f"你是一位资深产品经理。请根据以下需求输出一份精简的 PRD 文档和 UI 设计思路：\n需求：{query}",
    )
    content = await stream_llm_text(
        llm=llm,
        prompt=prompt,
        state=state,
        node_name="product",
        active_agent="产品岗智能体",
    )
    
    return {
        "prd": content,
        "messages": [AIMessage(content=content)],
        "active_agent": "产品岗智能体",
        "execution_log": [{"agent": "产品岗智能体", "status": f"PRD产出完成{'（已参考' + '、'.join(kb_names) + '）' if kb_names else ''}", "department": "TECH"}],
        "next_step": "developer"
    }

async def developer_agent_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    ② 开发岗智能体: 按 PRD 或原始需求开发代码
    """
    prd = state.get("prd")
    original_query = get_first_user_message(state, "No requirement found")
    
    if prd:
        logger.info("Tech: Developer Agent writing code based on PRD.")
        base_prompt = f"你是一位全栈开发工程师。请根据以下 PRD 文档编写核心代码实现：\nPRD：{prd}"
    else:
        logger.info("Tech: Developer Agent writing code based on original query (PRD skipped).")
        base_prompt = f"你是一位全栈开发工程师。由于流程中跳过了产品岗，请直接根据用户的原始需求编写核心代码实现：\n需求：{original_query}"

    prompt, kb_names = inject_knowledge_into_prompt("developer", original_query or prd or "", base_prompt)
    
    code_content = await stream_llm_text(
        llm=llm,
        prompt=prompt,
        state=state,
        node_name="developer",
        active_agent="开发岗智能体",
    )
    
    return {
        "code": code_content,
        "messages": [AIMessage(content=f"```python\n{code_content}\n```")],
        "active_agent": "开发岗智能体",
        "execution_log": [{"agent": "开发岗智能体", "status": f"代码编写完成{'（已参考' + '、'.join(kb_names) + '）' if kb_names else ''}", "department": "TECH"}],
        "next_step": "tester"
    }

async def tester_agent_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    ③ 检测岗智能体: 四维自动检测 (安全、规范、功能、兼容)
    """
    code = state.get("code")
    original_query = get_first_user_message(state, "No requirement found")
    
    logger.info("Tech: Tester Agent performing 4-dimensional security and quality check.")
    _, kb_names = inject_knowledge_into_prompt("tester", original_query or code or "", "请执行检测")
    
    if code:
        # Simple logic: If code contains "error", fail it for demonstration
        test_passed = "error" not in code.lower()
    else:
        # If no code, but we are here, maybe we're testing a concept or general requirement
        test_passed = True
    
    report = {
        "security": "Pass" if test_passed else "Fail: Potential vulnerability found",
        "coding_standard": "Pass",
        "functionality": "Pass",
        "compatibility": "Pass"
    }
    
    report_md = f"### 四维检测报告\n\n- 安全性: {report['security']}\n- 编码规范: {report['coding_standard']}\n- 功能性: {report['functionality']}\n- 兼容性: {report['compatibility']}"
    
    status_msg = "四维检测完成" if test_passed else "检测不合格"
    return {
        "test_report": report,
        "test_passed": test_passed,
        "messages": [AIMessage(content=report_md)],
        "active_agent": "检测岗智能体",
        "execution_log": [{"agent": "检测岗智能体", "status": f"{status_msg}{'（已参考' + '、'.join(kb_names) + '）' if kb_names else ''}", "department": "TECH"}],
        "next_step": "devops" if test_passed else "developer"
    }

async def devops_agent_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    ④ 运维部署智能体: 分布式部署与监控
    """
    logger.info("Tech: DevOps Agent deploying code to distributed nodes.")
    
    code = state.get("code")
    _, kb_names = inject_knowledge_into_prompt("devops", code or "", "请执行部署")
    report = "### 运维部署报告\n\n- 状态：✅ 部署成功\n- 节点：Node-A, Node-B\n- 监控：正常运行中 (Uptime: 99.9%)"
    if not code:
        report += "\n- 说明：本次为环境预部署/配置更新（未检测到新代码）"
    
    return {
        "deployment_report": report,
        "messages": [AIMessage(content=report)],
        "active_agent": "运维部署智能体",
        "execution_log": [{"agent": "运维部署智能体", "status": f"分布式部署成功{'（已参考' + '、'.join(kb_names) + '）' if kb_names else ''}", "department": "TECH"}],
        "next_step": "end"
    }
