from typing import List, Tuple

from app.agent_kb import agent_kb_service
from app.kb import kb_service


def build_agent_knowledge_context(agent_id: str, query: str) -> Tuple[str, List[str]]:
    kb_ids = agent_kb_service.get_binding(agent_id)
    if not kb_ids or not query.strip():
        return "", []

    results = kb_service.search_kbs(query=query, kb_ids=kb_ids, limit=6)
    if not results:
        return "已检索已配置知识库，但本次未命中有效资料，请结合通用专业能力完成任务。", []

    kb_names = []
    lines = []
    for idx, item in enumerate(results, 1):
        kb_name = item.get("kb_name", "未知知识库")
        if kb_name not in kb_names:
            kb_names.append(kb_name)
        lines.append(
            f"{idx}. 知识库：{kb_name}｜文件：{item.get('source', '未知来源')}｜内容：{item.get('content', '')}"
        )

    context = (
        f"已经检索到以下知识库资料：{ '、'.join(kb_names) }。\n"
        "请参考这些资料完成任务，优先吸收检索结果中的约束、术语和事实，再给出你的专业输出。\n"
        "检索结果：\n"
        + "\n".join(lines)
    )
    return context, kb_names


def inject_knowledge_into_prompt(agent_id: str, query: str, base_prompt: str) -> Tuple[str, List[str]]:
    context, kb_names = build_agent_knowledge_context(agent_id, query)
    if not context:
        return base_prompt, []
    return f"{base_prompt}\n\n{context}", kb_names
