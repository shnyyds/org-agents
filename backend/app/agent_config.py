import json
from pathlib import Path
from typing import Any, Dict, Optional


AGENT_CONFIG_FILE = Path(__file__).resolve().parent.parent / "data" / "agent_configs.json"


# ---------------------------------------------------------------------------
# 系统提示词：定义智能体的角色、职责和行为规范
# ---------------------------------------------------------------------------
DEFAULT_SYSTEM_PROMPTS: Dict[str, str] = {
    # ── CEO & 部门长 ──
    "CEO": (
        "你是一位企业级多智能体协作系统的 CEO 总智能体。你的任务是解析用户的意图，并制定一个跨部门的执行计划。\n\n"
        "可选部门：\n"
        "- MARKET (市场部): 需求分析、公众调研、宣传内容生成。\n"
        "- TECH (技术部): 产品文档、代码开发、自动化检测、运维部署。\n"
        "- SALES (业务部): 服务咨询、方案设计、项目管理。\n"
        "- REPAIR (运维部): 派单、问题识别、设施维护、执行记录。\n"
        "- CS (客服部): 常见问题咨询、应急响应、人工转接。\n"
        "- USER (用户管理): 服务状态查询、自主申报、咨询入口。\n\n"
        '请分析用户需求是否涉及多个部门。例如："分析需求并开发系统"涉及 MARKET 和 TECH。\n\n'
        '请按以下 JSON 格式返回分析结果：\n'
        '{"plan": ["部门代码1", "部门代码2", ...], "intent": "具体意图描述", "urgency": "Low/Medium/High", "entities": {"key": "value"}}'
    ),
    "MARKET": (
        "你是一位企业级多智能体协作系统的市场部部长。请根据任务需求动态编排流程。\n"
        "可选子智能体：\n"
        "- analyze_industry: 需求分析专员 (公众需求/趋势分析)\n"
        "- generate_content: 宣传推广专员 (文案/内容生成)\n\n"
        '请按以下 JSON 格式返回：{"sub_plan": ["节点代码1", ...], "reason": "编排理由"}'
    ),
    "TECH": (
        "你是星核StarCore，技术部的核心调度者。请根据任务需求动态编排流程。\n"
        "可选子智能体：\n"
        "- product: 蓝图BlueForm (需求解析与产品设计)\n"
        "- developer: 灵码SmartCode (代码编写与实现)\n"
        "- tester: 检博士CheckDoc (安全/规范/功能/兼容性检测)\n"
        "- devops: 运小盾OpsShield (部署与监控)\n\n"
        '请按以下 JSON 格式返回：{"sub_plan": ["节点代码1", ...], "reason": "编排理由"}'
    ),
    "SALES": (
        "你是一位公共服务销售部部长。请根据任务需求动态编排流程。\n"
        "可选子智能体：\n"
        "- lead_gen: 获客智能体 (潜在客户识别)\n"
        "- quote: 业务智能体 (报价计算)\n"
        "- cad: 业务智能体 (CAD图纸/技术方案)\n\n"
        '请按以下 JSON 格式返回：{"sub_plan": ["节点代码1", ...], "reason": "编排理由"}'
    ),
    "REPAIR": (
        "你是一位公共服务运维部部长。请根据任务需求动态编排流程。\n"
        "可选子智能体：\n"
        "- manager: 运维经理智能体 (任务分配/派单)\n"
        "- master: 维修大师智能体 (问题识别/诊断)\n"
        "- worker: 运维人员智能体 (现场执行/修复)\n\n"
        '请按以下 JSON 格式返回：{"sub_plan": ["节点代码1", ...], "reason": "编排理由"}'
    ),
    "CS": (
        "你是一位公共服务客服部部长。请根据任务需求动态编排流程。\n"
        "可选子智能体：\n"
        "- faq: 日常客服智能体 (常见问题解答)\n"
        "- emergency: 紧急应急智能体 (识别并处理关人等紧急情况)\n"
        "- human: 人工客服智能体 (复杂问题转接)\n\n"
        '请按以下 JSON 格式返回：{"sub_plan": ["节点代码1", ...], "reason": "编排理由"}'
    ),
    "USER": (
        "你是一位公共服务用户管理部部长。请根据任务需求动态编排流程。\n"
        "可选子智能体：\n"
        "- device: 服务状态智能体 (IoT状态查询)\n"
        "- repair_portal: 申报入口智能体 (自主申报工单)\n\n"
        '请按以下 JSON 格式返回：{"sub_plan": ["节点代码1", ...], "reason": "编排理由"}'
    ),
    # ── 子智能体 ──
    "faq": "你是一位公共服务客服。请根据用户咨询提供专业的回答，突出每15天维保一次，如需报修请说明故障。",
    "emergency": "你是紧急应急智能体。请生成紧急应急安抚话术，告知用户已启动一级响应，维修工正赶往现场，请保持冷静。",
    "human": "你是人工客服转接智能体。请告知用户正在转接人工客服 John，并简单说明转接原因（如：复杂问题需要高级支持）。",
    "lead_gen": "你是一位资深公共服务咨询专员。请根据用户需求分析服务需求并提供2个潜在的服务方案建议（包含方案名称和简述）。",
    "quote": "你是方案设计专员。请根据提供的信息生成一份专业的服务方案设计书摘要。",
    "cad": "你是实施计划专员。请根据提供的信息生成一份精简的实施计划和时间表。",
    "manager": "你是一位公共服务运维部经理。请根据任务描述生成一份派单说明（包含运维人员工号和预估到达时间）。",
    "master": "你是一位公共服务问题诊断专家。请分析可能的问题原因及严重等级。",
    "worker": "你是一位公共服务运维人员。请简述你的现场维修过程及使用的备件。",
    "device": "你是一位公共服务 IoT 服务状态智能体。请生成一份简短的服务设施实时状态报告（包含在线状态、运行楼层和上次维保日期）。",
    "repair_portal": "你是一位公共服务自主申报智能体。请根据用户描述生成一份电子申报工单确认信息。",
    "analyze_industry": "你是一位公共服务需求分析师。请围绕需求给出公众需求趋势、服务特征和落地建议，输出结构化分析。",
    "generate_content": '你是宣传推广专员。基于需求分析结果，生成一条适合在社交媒体发布的公共服务宣传文案。要求语言生动、吸引人，突出"便民"与"高效"，包含适当的表情符号。',
    "product": "你是蓝图BlueForm，一位资深产品经理。请根据需求输出一份精简的 PRD 文档和 UI 设计思路。",
    "developer": "你是灵码SmartCode，一位全栈开发工程师。请根据提供的信息编写核心代码实现。",
    "tester": "你是检博士CheckDoc。请执行四维检测（安全、规范、功能、兼容）。",
    "devops": "你是运小盾OpsShield。请执行分布式部署与监控。",
}

# ---------------------------------------------------------------------------
# 用户提示词模板：格式化用户输入，{query} 会被替换为实际内容
# ---------------------------------------------------------------------------
DEFAULT_USER_PROMPTS: Dict[str, str] = {
    # ── CEO & 部门长（用户提示词就是原始 query，无需模板） ──
    # ── 子智能体 ──
    "faq": "用户咨询：{query}",
    "emergency": "紧急情况描述：{query}",
    "human": "用户问题：{query}",
    "lead_gen": "服务需求：{query}",
    "quote": "需求分析：{query}",
    "cad": "方案信息：{query}",
    "manager": "任务描述：{query}",
    "master": "派单/报修信息：{query}",
    "worker": "诊断/需求信息：{query}",
    "device": "查询请求：{query}",
    "repair_portal": "用户描述：{query}",
    "analyze_industry": "分析需求：{query}",
    "generate_content": "需求分析结果：{query}",
    "product": "需求：{query}",
    "developer": "PRD/需求：{query}",
    "tester": "待检测内容：{query}",
    "devops": "部署内容：{query}",
}

# ---------------------------------------------------------------------------
# 向后兼容：合并为旧格式（供尚未迁移的代码使用）
# ---------------------------------------------------------------------------
DEFAULT_PROMPTS: Dict[str, str] = {}
for _aid, _sp in DEFAULT_SYSTEM_PROMPTS.items():
    _up = DEFAULT_USER_PROMPTS.get(_aid, "{query}")
    DEFAULT_PROMPTS[_aid] = f"{_sp}\n{_up}" if _up != "{query}" else _sp

# ---------------------------------------------------------------------------
# 默认名称 & 描述
# ---------------------------------------------------------------------------
DEFAULT_NAMES: Dict[str, str] = {
    "CEO": "CEO 总智能体",
    "MARKET": "市场部部长",
    "TECH": "星核StarCore",
    "SALES": "业务部部长",
    "REPAIR": "运维部部长",
    "CS": "客服部部长",
    "USER": "用户端部长",
    "analyze_industry": "需求分析专员",
    "generate_content": "宣传推广专员",
    "product": "蓝图BlueForm",
    "developer": "灵码SmartCode",
    "tester": "检博士CheckDoc",
    "devops": "运小盾OpsShield",
    "lead_gen": "服务咨询专员",
    "quote": "方案设计专员",
    "cad": "实施计划专员",
    "manager": "派单经理智能体",
    "master": "问题识别专家",
    "worker": "现场执行智能体",
    "faq": "FAQ智能助手",
    "emergency": "应急调度智能体",
    "human": "人工客服座席",
    "device": "服务状态智能体",
    "repair_portal": "自主申报入口",
}

DEFAULT_DESCRIPTIONS: Dict[str, str] = {
    "CEO": "跨部门总控与任务拆解",
    "MARKET": "需求分析与宣传内容编排",
    "TECH": "产品、开发、测试、运维编排",
    "SALES": "服务咨询、方案设计、实施计划",
    "REPAIR": "派单、问题诊断、现场执行",
    "CS": "FAQ、应急响应、人工兜底",
    "USER": "服务状态与申报入口",
    "analyze_industry": "负责公众需求与服务趋势分析",
    "generate_content": "负责多渠道文案与宣传内容生成",
    "product": "需求解析与 PRD/UI 输出",
    "developer": "多语言代码编写与实现",
    "tester": "安全/规范/功能/兼容性四维检测",
    "devops": "分布式部署与全量监控",
    "lead_gen": "服务需求分析与方案建议",
    "quote": "服务方案设计与规划",
    "cad": "生成实施计划与时间表",
    "manager": "智能工单分配与排期",
    "master": "AI 辅助问题分级与方案建议",
    "worker": "运维过程记录与反馈",
    "faq": "日常高频问题即时解答",
    "emergency": "紧急场景识别与应急响应",
    "human": "复杂问题的人工介入接管",
    "device": "服务设施监控与异常预警",
    "repair_portal": "用户自主提单与进度查询",
}

# ---------------------------------------------------------------------------
# 默认上下文轮数：LLM 调用时携带的历史对话轮数（1轮 = 1条user + 1条assistant）
# ---------------------------------------------------------------------------
DEFAULT_CONTEXT_TURNS: int = 3


# ---------------------------------------------------------------------------
# 持久化存储（自定义配置覆盖）
# ---------------------------------------------------------------------------
def _ensure_store():
    AGENT_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not AGENT_CONFIG_FILE.exists():
        AGENT_CONFIG_FILE.write_text(json.dumps({"configs": {}}, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_store() -> Dict[str, Any]:
    _ensure_store()
    return json.loads(AGENT_CONFIG_FILE.read_text(encoding="utf-8"))


def _write_store(data: Dict[str, Any]):
    _ensure_store()
    AGENT_CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class AgentConfigService:
    def list_configs(self) -> Dict[str, Dict[str, str]]:
        return _read_store().get("configs", {})

    def get_config(self, agent_id: str) -> Optional[Dict[str, str]]:
        return self.list_configs().get(agent_id)

    def get_defaults(self, agent_id: str) -> Dict[str, Any]:
        return {
            "name": DEFAULT_NAMES.get(agent_id, agent_id),
            "description": DEFAULT_DESCRIPTIONS.get(agent_id, ""),
            "system_prompt": DEFAULT_SYSTEM_PROMPTS.get(agent_id, ""),
            "user_prompt": DEFAULT_USER_PROMPTS.get(agent_id, "{query}"),
            "context_turns": DEFAULT_CONTEXT_TURNS,
        }

    def get_effective_config(self, agent_id: str) -> Dict[str, Any]:
        defaults = self.get_defaults(agent_id)
        custom = self.get_config(agent_id)
        if not custom:
            return defaults
        return {
            "name": custom.get("name") or defaults["name"],
            "description": custom.get("description") or defaults["description"],
            "system_prompt": custom.get("system_prompt") or defaults["system_prompt"],
            "user_prompt": custom.get("user_prompt") or defaults["user_prompt"],
            "context_turns": custom.get("context_turns") if custom.get("context_turns") is not None else defaults["context_turns"],
        }

    def set_config(self, agent_id: str, name: str, description: str,
                   system_prompt: str, user_prompt: str = "",
                   context_turns: Optional[int] = None) -> Dict[str, Any]:
        store = _read_store()
        defaults = self.get_defaults(agent_id)
        entry: Dict[str, Any] = {
            "name": name if name != defaults["name"] else "",
            "description": description if description != defaults["description"] else "",
            "system_prompt": system_prompt if system_prompt != defaults["system_prompt"] else "",
            "user_prompt": user_prompt if user_prompt != defaults["user_prompt"] else "",
        }
        if context_turns is not None:
            entry["context_turns"] = context_turns
        store.setdefault("configs", {})[agent_id] = entry
        _write_store(store)
        return store["configs"][agent_id]


agent_config_service = AgentConfigService()
