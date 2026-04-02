from typing import List, Dict, Any

# Map of departments to their sub-agents
DEPARTMENT_SUB_AGENTS = {
    "MARKET": [
        {"id": "analyze_industry", "name": "需求分析专员", "description": "负责公众需求与服务趋势分析"},
        {"id": "generate_content", "name": "宣传推广专员", "description": "负责多渠道文案与宣传内容生成"}
    ],
    "TECH": [
        {"id": "product", "name": "蓝图BlueForm", "description": "需求解析与 PRD/UI 输出"},
        {"id": "developer", "name": "灵码SmartCode", "description": "多语言代码编写与实现"},
        {"id": "tester", "name": "检博士CheckDoc", "description": "安全/规范/功能/兼容性四维检测"},
        {"id": "devops", "name": "运小盾OpsShield", "description": "分布式部署与全量监控"}
    ],
    "SALES": [
        {"id": "lead_gen", "name": "服务咨询专员", "description": "服务需求分析与方案建议"},
        {"id": "quote", "name": "方案设计专员", "description": "服务方案设计与规划"},
        {"id": "cad", "name": "实施计划专员", "description": "生成实施计划与时间表"}
    ],
    "REPAIR": [
        {"id": "manager", "name": "派单经理智能体", "description": "智能工单分配与排期"},
        {"id": "master", "name": "问题识别专家", "description": "AI 辅助问题分级与方案建议"},
        {"id": "worker", "name": "现场执行智能体", "description": "运维过程记录与反馈"}
    ],
    "CS": [
        {"id": "faq", "name": "FAQ智能助手", "description": "日常高频问题即时解答"},
        {"id": "emergency", "name": "应急调度智能体", "description": "紧急场景识别与应急响应"},
        {"id": "human", "name": "人工客服座席", "description": "复杂问题的人工介入接管"}
    ],
    "USER": [
        {"id": "device", "name": "服务状态智能体", "description": "服务设施监控与异常预警"},
        {"id": "repair_portal", "name": "自主申报入口", "description": "用户自主提单与进度查询"}
    ]
}

def get_sub_agents(dept_id: str) -> List[Dict[str, str]]:
    return DEPARTMENT_SUB_AGENTS.get(dept_id, [])


def get_all_sub_agent_ids() -> List[str]:
    ids: List[str] = []
    for agents in DEPARTMENT_SUB_AGENTS.values():
        ids.extend(agent["id"] for agent in agents)
    return ids
