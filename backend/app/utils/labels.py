DEPARTMENT_LABELS = {
    "CEO": "CEO 总智能体",
    "MARKET": "市场部",
    "TECH": "技术部",
    "SALES": "销售部",
    "REPAIR": "维修部",
    "CS": "客服部",
    "USER": "用户端",
}

SUB_AGENT_LABELS = {
    "analyze_industry": "行业分析大师",
    "generate_content": "宣传推广大师",
    "product": "产品岗智能体",
    "developer": "开发岗智能体",
    "tester": "检测岗智能体",
    "devops": "运维部署智能体",
    "lead_gen": "获客智能体",
    "quote": "业务报价智能体",
    "cad": "CAD设计智能体",
    "manager": "维修经理智能体",
    "master": "维修大师智能体",
    "worker": "维修工智能体",
    "faq": "FAQ 智能助手",
    "emergency": "紧急救援智能体",
    "human": "人工客服座席",
    "device": "设备管理智能体",
    "repair_portal": "报修入口智能体",
}


def format_department_plan(plan):
    return " -> ".join(DEPARTMENT_LABELS.get(item, item) for item in plan)


def format_sub_agent_plan(plan):
    return " -> ".join(SUB_AGENT_LABELS.get(item, item) for item in plan)


def get_department_label(dept_code: str) -> str:
    return DEPARTMENT_LABELS.get(dept_code, dept_code)
