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


def _resolve_prompt(agent_id: str, prompt_type: str, default_prompt: str = None, query: str = "") -> str:
    """通用提示词解析：优先用自定义配置，否则用 default_prompt 或全局默认值。"""
    from app.agent_config import agent_config_service, DEFAULT_SYSTEM_PROMPTS, DEFAULT_USER_PROMPTS

    defaults_map = DEFAULT_SYSTEM_PROMPTS if prompt_type == "system" else DEFAULT_USER_PROMPTS
    config = agent_config_service.get_config(agent_id)
    custom = config.get(f"{prompt_type}_prompt") if config else None

    if custom:
        prompt = custom
    elif default_prompt is not None:
        prompt = default_prompt
    else:
        prompt = defaults_map.get(agent_id, "")

    if "{query}" in prompt:
        prompt = prompt.replace("{query}", query)
    return prompt


def resolve_system_prompt(agent_id: str, default_prompt: str = None, query: str = "") -> str:
    """解析系统提示词（角色/职责/指令）。"""
    return _resolve_prompt(agent_id, "system", default_prompt, query)


def resolve_user_prompt(agent_id: str, default_prompt: str = None, query: str = "") -> str:
    """解析用户提示词模板，{query} 会被替换为实际内容。"""
    return _resolve_prompt(agent_id, "user", default_prompt, query)


# 向后兼容旧调用
def resolve_agent_prompt(agent_id: str, default_prompt: str = None, query: str = "") -> str:
    """向后兼容：返回合并后的提示词（系统+用户）。"""
    from app.agent_config import DEFAULT_PROMPTS
    config = None
    try:
        from app.agent_config import agent_config_service
        config = agent_config_service.get_config(agent_id)
    except Exception:
        pass

    if config and config.get("system_prompt"):
        prompt = config["system_prompt"]
        if "{query}" in prompt:
            prompt = prompt.replace("{query}", query)
        return prompt

    prompt = default_prompt if default_prompt is not None else DEFAULT_PROMPTS.get(agent_id, "")
    if "{query}" in prompt:
        prompt = prompt.replace("{query}", query)
    return prompt
