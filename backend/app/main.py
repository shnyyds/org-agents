from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import os
from dotenv import load_dotenv
from app.utils.logger import public_service_logger as logger
from app.state import AgentState
from app.kb import kb_service
from app.agent_kb import agent_kb_service

load_dotenv()

app = FastAPI(title="Elevator Industry Multi-Agent System")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserInput(BaseModel):
    query: str
    user_id: str
    session_id: Optional[str] = None
    target_agent: Optional[str] = "CEO" # Target: "CEO", "MARKET", "TECH", "product_agent", etc.
    target_type: Optional[str] = "orchestrator" # Type: "orchestrator" (Lead) or "agent" (Sub)
    history: Optional[List[Dict[str, str]]] = None


class KnowledgeBaseCreate(BaseModel):
    name: str
    icon: Optional[str] = "🤖"
    description: Optional[str] = ""
    permission: Optional[str] = "只有我"
    segment_mode: Optional[str] = "general"
    index_mode: Optional[str] = "high_quality"
    retrieval_mode: Optional[str] = "hybrid"
    separator: Optional[str] = "\n\n"
    chunk_size: Optional[int] = 800
    chunk_overlap: Optional[int] = 100
    semantic_weight: Optional[float] = 0.7
    keyword_weight: Optional[float] = 0.3
    top_k: Optional[int] = 5
    score_threshold: Optional[float] = 0.2
    embedding_model: Optional[str] = "text-embedding-v4"


class ChunkPreviewInput(BaseModel):
    text: str
    separator: Optional[str] = "\n\n"
    chunk_size: Optional[int] = 800
    chunk_overlap: Optional[int] = 100


class RecallTestInput(BaseModel):
    query: str
    top_k: Optional[int] = 5

@app.get("/")
async def root():
    return {"message": "Elevator Multi-Agent API is running."}


@app.get("/knowledge-bases")
async def list_knowledge_bases():
    return kb_service.list_kbs()


@app.post("/knowledge-bases")
async def create_knowledge_base(payload: KnowledgeBaseCreate):
    return kb_service.create_kb(payload.model_dump())


@app.get("/knowledge-bases/{kb_id}")
async def get_knowledge_base(kb_id: str):
    try:
        return kb_service.get_kb(kb_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.put("/knowledge-bases/{kb_id}")
async def update_knowledge_base(kb_id: str, payload: KnowledgeBaseCreate):
    try:
        return kb_service.update_kb(kb_id, payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/knowledge-bases/chunk-preview")
async def chunk_preview(payload: ChunkPreviewInput):
    return {
        "chunks": kb_service.preview_chunks(
            payload.text,
            payload.separator or "\n\n",
            payload.chunk_size or 800,
            payload.chunk_overlap or 100,
        )
    }


@app.post("/knowledge-bases/{kb_id}/documents")
async def upload_document(
    kb_id: str,
    file: UploadFile = File(...),
    separator: str = Form("\n\n"),
    chunk_size: int = Form(800),
    chunk_overlap: int = Form(100),
):
    try:
        content = await file.read()
        return kb_service.add_document(
            kb_id,
            file.filename,
            content,
            separator,
            chunk_size,
            chunk_overlap,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("知识库文档处理失败")
        raise HTTPException(status_code=500, detail=f"文档处理失败：{str(exc)}")


@app.post("/knowledge-bases/{kb_id}/recall-test")
async def recall_test(kb_id: str, payload: RecallTestInput):
    try:
        return kb_service.recall_test(kb_id, payload.query, payload.top_k or 5)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("知识库召回测试失败")
        raise HTTPException(status_code=500, detail=f"召回测试失败：{str(exc)}")


@app.get("/knowledge-bases/{kb_id}/documents/{document_id}/chunks")
async def get_document_chunks(kb_id: str, document_id: str):
    try:
        return kb_service.get_document_chunks(kb_id, document_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("知识库文档分段读取失败")
        raise HTTPException(status_code=500, detail=f"文档分段读取失败：{str(exc)}")

from app.ceo import create_ceo_graph
from langchain_core.messages import HumanMessage, AIMessage
import json
import asyncio
from fastapi.responses import StreamingResponse
from langgraph.graph import StateGraph, END
from app.departments.market.agent import market_lead

# Initialize CEO graph
ceo_app = create_ceo_graph()


def build_message_history(history: Optional[List[Dict[str, str]]], query: str):
    messages = []

    for item in history or []:
        role = item.get("role")
        content = item.get("content", "")
        if not content:
            continue

        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=query))
    return messages


def create_direct_agent_graph(agent_id: str):
    from app.departments.tech.sub_agents import (
        product_agent_node,
        developer_agent_node,
        tester_agent_node,
        devops_agent_node,
    )
    from app.departments.sales.sub_agents import (
        lead_gen_agent_node,
        quote_agent_node,
        cad_agent_node,
    )
    from app.departments.repair.sub_agents import (
        repair_manager_agent_node,
        repair_master_agent_node,
        repair_worker_agent_node,
    )
    from app.departments.cs.sub_agents import (
        faq_agent_node,
        emergency_agent_node,
        human_agent_node,
    )
    from app.departments.user.sub_agents import (
        device_agent_node,
        user_repair_agent_node,
    )

    direct_agents = {
        "product": product_agent_node,
        "developer": developer_agent_node,
        "tester": tester_agent_node,
        "devops": devops_agent_node,
        "analyze_industry": market_lead.analyze_industry_node,
        "generate_content": market_lead.generate_content_node,
        "lead_gen": lead_gen_agent_node,
        "quote": quote_agent_node,
        "cad": cad_agent_node,
        "manager": repair_manager_agent_node,
        "master": repair_master_agent_node,
        "worker": repair_worker_agent_node,
        "faq": faq_agent_node,
        "emergency": emergency_agent_node,
        "human": human_agent_node,
        "device": device_agent_node,
        "repair_portal": user_repair_agent_node,
    }

    node = direct_agents.get(agent_id)
    if not node:
        return None

    workflow = StateGraph(AgentState)
    workflow.add_node(agent_id, node)
    workflow.set_entry_point(agent_id)
    workflow.add_edge(agent_id, END)
    return workflow.compile()

@app.post("/chat")
async def chat(input: UserInput):
    """
    Main chat endpoint that routes queries through the CEO Orchestrator.
    """
    # Initial state
    initial_state = {
        "messages": build_message_history(input.history, input.query),
        "context": {"user_id": input.user_id, "session_id": input.session_id},
        "results": {},
        "execution_log": [],
        "plan": [],
        "plan_step": 0
    }
    
    # Run through the graph
    try:
        final_state = await ceo_app.ainvoke(initial_state)
        
        # Get the last AI message
        ai_messages = [m for m in final_state["messages"] if isinstance(m, AIMessage)]
        response_text = ai_messages[-1].content if ai_messages else "No response generated."
        
        return {
            "status": "success",
            "response": response_text,
            "department": final_state.get("current_department", "CEO"),
            "intent": final_state.get("intent_analysis", {}).get("intent", "unknown"),
            "analysis": final_state.get("intent_analysis", {}),
            "execution_log": final_state.get("execution_log", []),
            "active_agent": final_state.get("active_agent", "CEO")
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

from app.core.registry import DEPARTMENT_SUB_AGENTS, get_sub_agents
from app.core.registry import get_all_sub_agent_ids


class AgentKnowledgeBindingInput(BaseModel):
    kb_ids: List[str]

@app.get("/registry")
async def get_registry():
    """
    Returns the full registry of departments and their sub-agents.
    """
    bindings = agent_kb_service.list_bindings()
    kb_map = {kb["id"]: kb for kb in kb_service.list_kb_summaries()}

    registry = {}
    for dept_id, agents in DEPARTMENT_SUB_AGENTS.items():
        registry[dept_id] = []
        for agent in agents:
            kb_ids = bindings.get(agent["id"], [])
            registry[dept_id].append(
                {
                    **agent,
                    "knowledge_bases": [kb_map[kb_id] for kb_id in kb_ids if kb_id in kb_map],
                }
            )
    return registry


@app.get("/agent-kb-bindings/{agent_id}")
async def get_agent_kb_binding(agent_id: str):
    if agent_id not in get_all_sub_agent_ids():
        raise HTTPException(status_code=404, detail="Sub-agent not found")
    kb_ids = agent_kb_service.get_binding(agent_id)
    kb_map = {kb["id"]: kb for kb in kb_service.list_kb_summaries()}
    return {
        "agent_id": agent_id,
        "kb_ids": kb_ids,
        "knowledge_bases": [kb_map[kb_id] for kb_id in kb_ids if kb_id in kb_map],
    }


@app.put("/agent-kb-bindings/{agent_id}")
async def update_agent_kb_binding(agent_id: str, payload: AgentKnowledgeBindingInput):
    if agent_id not in get_all_sub_agent_ids():
        raise HTTPException(status_code=404, detail="Sub-agent not found")
    valid_kb_ids = {kb["id"] for kb in kb_service.list_kbs()}
    cleaned_kb_ids = [kb_id for kb_id in payload.kb_ids if kb_id in valid_kb_ids]
    agent_kb_service.set_binding(agent_id, cleaned_kb_ids)
    return await get_agent_kb_binding(agent_id)

@app.post("/chat/stream")
async def chat_stream(input: UserInput):
    """
    Streaming chat endpoint that supports multi-level routing:
    1. Target: CEO -> CEO Orchestrates Departments.
    2. Target: DEPT_LEAD -> User acts as CEO, Department Lead orchestrates sub-agents.
    3. Target: SUB_AGENT -> User acts as Dept Lead, Sub-agent performs specific task.
    """
    logger.info(f"Received stream request: {input.query} (Target: {input.target_agent}, Type: {input.target_type})")
    
    async def event_generator():
        streamed_nodes = set()
        event_queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
        current_node = "CEO"

        async def emit_sse(payload: Dict[str, Any]):
            await event_queue.put(f"data: {json.dumps(payload, ensure_ascii=False)}\n\n")

        initial_state = {
            "messages": build_message_history(input.history, input.query),
            "context": {
                "user_id": input.user_id,
                "session_id": input.session_id,
                "target_agent": input.target_agent,
                "target_type": input.target_type,
                "stream_writer": emit_sse,
                "streamed_nodes": streamed_nodes,
            },
            "results": {},
            "execution_log": [],
            "plan": [],
            "plan_step": 0,
            "sub_plan": [],
            "sub_plan_step": 0
        }
        current_state = initial_state.copy()

        friendly_names = {
            "analyze_intent": "CEO 总智能体", "product": "蓝图BlueForm", "developer": "灵码SmartCode",
            "tester": "检博士CheckDoc", "devops": "运小盾OpsShield", "analyze_industry": "行业分析大师",
            "generate_content": "宣传推广大师", "lead_gen": "获客智能体", "quote": "业务报价智能体",
            "cad": "CAD设计智能体", "manager": "派单经理智能体", "master": "故障识别大师",
            "worker": "现场执行智能体", "faq": "FAQ智能助手", "emergency": "救援调度智能体",
            "human": "人工客服座席", "device": "设备健康智能体", "repair_portal": "自主报修入口",
            "tech_lead_plan": "星核StarCore", "market_lead_plan": "市场部部长", "sales_lead_plan": "销售部部长",
            "repair_lead_plan": "维修部部长", "cs_lead_plan": "客服部部长", "user_lead_plan": "用户端部长"
        }
        streamable_nodes = {
            "analyze_intent",
            "summarize_result",
            "tech_lead_plan",
            "market_lead_plan",
            "sales_lead_plan",
            "repair_lead_plan",
            "cs_lead_plan",
            "user_lead_plan",
            "product",
            "developer",
            "tester",
            "devops",
            "analyze_industry",
            "generate_content",
            "lead_gen",
            "quote",
            "cad",
            "manager",
            "master",
            "worker",
            "faq",
            "emergency",
            "human",
            "device",
            "repair_portal",
        }

        def get_friendly_agent_name(node_name: str, fallback: str = "智能体") -> str:
            return friendly_names.get(node_name, fallback)

        async def run_graph():
            nonlocal current_node
            runnable = ceo_app

            if input.target_type == "orchestrator" and input.target_agent in ["MARKET", "TECH", "SALES", "REPAIR", "CS", "USER"]:
                from app.ceo import market_lead, tech_lead, sales_lead, repair_lead, cs_lead, user_lead
                leads = {
                    "MARKET": market_lead, "TECH": tech_lead, "SALES": sales_lead,
                    "REPAIR": repair_lead, "CS": cs_lead, "USER": user_lead
                }
                runnable = leads[input.target_agent].workflow.compile()
                current_node = f"{input.target_agent}部长"
                logger.info(f"Routing directly to Department Lead: {input.target_agent}")
            elif input.target_type == "agent":
                direct_agent_graph = create_direct_agent_graph(input.target_agent)
                if direct_agent_graph:
                    runnable = direct_agent_graph
                    current_node = input.target_agent
                    logger.info(f"Routing directly to Sub-Agent: {input.target_agent}")
                else:
                    logger.error(f"Unknown sub-agent: {input.target_agent}")

            try:
                logger.info("Starting astream_events loop...")
                async for event in runnable.astream_events(initial_state, version="v2"):
                    kind = event["event"]
                    name = event["name"]

                    if kind == "on_chain_start":
                        if name not in ["LangGraph", "route_to_department", "route_next_step", "MARKET", "TECH", "SALES", "REPAIR", "CS", "USER", "dispatch_sub_agent", "route_sub_agent"]:
                            logger.info(f">>> Node Start: {name}")
                            current_node = name
                            await emit_sse({"type": "update", "active_agent": name, "status": "thinking", "node_name": name})

                    if kind == "on_chat_model_stream":
                        content = event["data"]["chunk"].content
                        if content:
                            metadata = event.get("metadata", {})
                            node_name = metadata.get("langgraph_node", current_node)
                            if node_name not in streamable_nodes:
                                continue
                            if node_name not in streamed_nodes:
                                streamed_nodes.add(node_name)
                            agent_name = get_friendly_agent_name(node_name, current_state.get("active_agent", "智能体"))
                            await emit_sse({"type": "stream", "content": content, "node": node_name, "active_agent": agent_name})

                    if kind == "on_chain_end":
                        data = event["data"]
                        output = data.get("output", {})

                        content = ""
                        messages = output.get("messages", []) if isinstance(output, dict) else []
                        if messages:
                            content = messages[-1].content if hasattr(messages[-1], "content") else str(messages[-1])
                        elif isinstance(output, dict) and "prd" in output:
                            content = output["prd"]
                        elif isinstance(output, dict) and "code" in output:
                            content = f"```python\n{output['code']}\n```"

                        if isinstance(output, dict):
                            messages = output.get("messages", [])
                            if messages:
                                current_state.setdefault("messages", [])
                                current_state["messages"].extend(messages)

                            for k, v in output.items():
                                if k not in ["execution_log", "messages", "results"]:
                                    current_state[k] = v

                            if output.get("execution_log"):
                                current_state.setdefault("execution_log", [])
                                current_state["execution_log"].extend(output["execution_log"])

                            if output.get("results"):
                                current_state.setdefault("results", {})
                                current_state["results"].update(output["results"])

                        if name in ["LangGraph", "route_to_department", "route_next_step", "MARKET", "TECH", "SALES", "REPAIR", "CS", "USER", "dispatch_sub_agent", "route_sub_agent"]:
                            continue

                        if content or (isinstance(output, dict) and output.get("execution_log")):
                            active_agent_name = (output.get("active_agent") if isinstance(output, dict) else None) or get_friendly_agent_name(name, name)

                            # No need for fallback stream - stream_llm_text already sent real chunks via stream_writer
                            # Just mark the node as streamed if it's in streamable_nodes
                            if name in streamable_nodes:
                                streamed_nodes.add(name)

                            await emit_sse(
                                {
                                    "type": "update",
                                    "active_agent": active_agent_name,
                                    "execution_log": output.get("execution_log", []) if isinstance(output, dict) else [],
                                    "partial_content": "" if name in streamed_nodes else content,
                                    "node_name": name,
                                }
                            )

                final_ai_msg = [m for m in current_state.get("messages", []) if isinstance(m, AIMessage)]
                final_response = final_ai_msg[-1].content if final_ai_msg else "执行完毕。"
                await emit_sse({"type": "final", "response": final_response})
            except Exception as e:
                logger.error(f"Stream Error: {str(e)}", exc_info=True)
                await emit_sse({"type": "error", "message": str(e)})
            finally:
                await event_queue.put(None)

        task = asyncio.create_task(run_graph())
        while True:
            payload = await event_queue.get()
            if payload is None:
                break
            yield payload
        await task

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
