from typing import List, Tuple

from app.skill import skill_service, agent_skill_service


def inject_skills_into_prompt(agent_id: str, base_prompt: str) -> Tuple[str, List[str]]:
    """
    将绑定到 agent_id 的已启用技能以 XML 格式追加到系统提示词末尾。
    返回 (新提示词, 技能名称列表)。
    """
    skill_ids = agent_skill_service.get_binding(agent_id)
    if not skill_ids:
        return base_prompt, []

    all_skills = {s["id"]: s for s in skill_service.list_skills()}
    active_skills = []
    for sid in skill_ids:
        skill = all_skills.get(sid)
        if skill and skill.get("enabled", True):
            active_skills.append(skill)

    if not active_skills:
        return base_prompt, []

    skill_names = [s["name"] for s in active_skills]

    blocks = []
    for s in active_skills:
        blocks.append(
            f"<skill>\n"
            f"<name>{s['name']}</name>\n"
            f"<description>{s.get('description', '')}</description>\n"
            f"<instructions>\n{s.get('content', '')}\n</instructions>\n"
            f"</skill>"
        )

    xml = "<available_skills>\n" + "\n".join(blocks) + "\n</available_skills>"
    return f"{base_prompt}\n\n{xml}", skill_names
