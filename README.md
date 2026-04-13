# OrgAgents — 万象智团

> 为小公司或有才华的个人打造世界 500 强的硅基团队

一个基于 LangGraph 和 React 构建的企业级多智能体协作系统，模拟真实企业组织架构，实现 CEO 总智能体统筹调度，各部门智能体协同工作的完整业务流程。支持单部门独立拆分出售。

## 📋 目录

- [系统架构](#系统架构)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [核心功能](#核心功能)
- [快速开始](#快速开始)
- [单部门独立模式](#单部门独立模式)
- [详细文档](#详细文档)

## 🏗️ 系统架构

### 三层智能体架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                           CEO 总智能体                                │
│                (意图分析 + 跨部门编排 + 任务总结)                       │
└──────────────────────────────────────────────────────────────────────┘
         │            │            │            │           │          │
         ▼            ▼            ▼            ▼           ▼          ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐
    │ 市场部  │ │ 技术部  │ │ 业务部  │ │ 运维部  │ │ 客服部  │ │ 用户端 │
    │  部长   │ │  部长   │ │  部长   │ │  部长   │ │  部长   │ │  部长  │
    └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └───┬────┘
         │           │           │           │           │          │
     ┌───┴───┐  ┌──┬─┴─┬──┐ ┌──┬┴──┐   ┌──┬┴──┐   ┌──┬┴──┐   ┌──┴──┐
     ▼       ▼  ▼  ▼   ▼  ▼ ▼  ▼   ▼   ▼  ▼   ▼   ▼  ▼   ▼   ▼     ▼
   需求   宣传 产 开  测 运 咨 方  实  派 诊  现  FAQ 应 人  服务  自主
   分析   推广 品 发  试 维 询 案  施  单 断  场      急 工  状态  申报
   专员   专员 岗 岗  岗 岗 员 员  员  员 员  员      员 员
```

### 工作流程

1. **用户输入** → CEO 总智能体分析意图
2. **CEO 编排** → 制定跨部门执行计划（plan）
3. **部门调度** → 依次调用相关部门
4. **部门编排** → 各部门部长制定内部子计划（sub_plan）
5. **子智能体执行** → 按子计划依次执行具体任务
6. **结果汇总** → CEO 生成高层总结报告

### StarCore Edict 流水线（技术部）

技术部（星核StarCore）支持 Edict 模式——编排逻辑写在 SOUL.md 提示词里，由 OpenClaw subagent 链式调用驱动，后端只需调入口 agent，整条链在一次调用里跑完：

```
用户 → 首席助理 ChiefAssistant (分拣: 闲聊/任务)
         ├─ 闲聊 → 直接回复
         └─ 任务 → subagent 调用 策略中心 StrategyHub
                      │
                      └─ subagent → 评审委 ReviewBoard (准奏/封驳，最多3轮)
                      │
                      └─ subagent → 星核部长 TechLead (派发)
                                       ├─ subagent → 蓝图BlueForm (产品)
                                       ├─ subagent → 灵码SmartCode (开发)
                                       ├─ subagent → 检博士CheckDoc (测试)
                                       └─ subagent → 运小盾OpsShield (运维)
                                       │
                                       └── 汇总 → 策略中心 → 首席助理 → 用户
```

触发条件：`target_agent=TECH` + `target_type=orchestrator` + `LLM_BACKEND=openclaw`，其他情况走原有 step_executor 流程。

## 🛠️ 技术栈

### 后端
- **框架**: FastAPI (异步 Web 框架)
- **智能体编排**: LangGraph (状态图工作流)
- **LLM**: LangChain + 通义千问 (Qwen) / OpenClaw Gateway (可切换)
- **向量数据库**: Qdrant (知识库检索)
- **流式输出**: SSE (Server-Sent Events)

### 前端
- **框架**: React 18 + Vite
- **UI**: Tailwind CSS + Lucide Icons
- **状态管理**: React Hooks
- **流式渲染**: SSE 客户端

## 📁 项目结构

```
org-agents/
│
├── backend/                          # 后端服务
│   ├── app/
│   │   ├── main.py                   # FastAPI 主入口，定义所有 API 端点
│   │   ├── ceo.py                    # CEO 总智能体，负责意图分析和跨部门编排
│   │   ├── state.py                  # AgentState 定义，LangGraph 状态管理
│   │   ├── session_store.py          # 会话状态存储，支持分步执行和取消
│   │   ├── step_executor.py          # 分步执行引擎，逐节点执行并支持暂停/确认
│   │   ├── skill.py                    # 技能服务（CRUD）+ 智能体-技能绑定服务
│   │   ├── agent_config.py           # 智能体配置服务（提示词、名称、描述）
│   │   ├── kb.py                     # 知识库服务，管理文档和向量检索
│   │   ├── agent_kb.py               # 智能体-知识库绑定服务
│   │   │
│   │   ├── core/                     # 核心模块
│   │   │   ├── llm.py                # LLM 配置和初始化（支持 OpenClaw 模式跳过）
│   │   │   ├── openclaw.py           # OpenClaw Gateway 流式调用（/v1/chat/completions SSE）
│   │   │   ├── backend_selector.py   # LLM 后端选择器（langchain / openclaw 切换）
│   │   │   ├── agent.py              # 基础智能体类定义
│   │   │   └── registry.py           # 智能体注册表，管理所有子智能体
│   │   │
│   │   ├── departments/              # 部门智能体（配置驱动，统一架构）
│   │   │   ├── base.py               # 通用部门长基类（所有部门共用）
│   │   │   └── registry.py           # 部门与子智能体配置注册表
│   │   │
│   │   ├── utils/                    # 工具模块
│   │   │   ├── streaming.py          # LangChain 流式输出
│   │   │   ├── openclaw_streaming.py # OpenClaw Gateway 流式输出适配器
│   │   │   ├── logger.py             # 日志配置
│   │   │   ├── messages.py           # 消息处理工具
│   │   │   ├── labels.py             # 标签和格式化工具
│   │   │   ├── agent_knowledge.py    # 知识库注入与提示词解析
│   │   │   ├── agent_skills.py       # 技能注入（XML 格式追加到系统提示词）
│   │   │   └── retriever.py          # 向量检索工具
│   │   │
│   │   └── db/                       # 数据库
│   │       └── qdrant.py             # Qdrant 向量数据库客户端
│   │
│   ├── data/                         # 数据存储
│   │   ├── knowledge_bases.json      # 知识库元数据
│   │   ├── agent_kb_bindings.json    # 智能体-知识库绑定关系
│   │   ├── agent_configs.json        # 智能体自定义配置（覆盖默认值）
│   │   ├── skills.json               # 技能库数据
│   │   ├── agent_skill_bindings.json # 智能体-技能绑定关系
│   │   └── kb_files/                 # 知识库文档文件
│   │
│   ├── scripts/                      # 脚本工具
│   │   ├── ingest_docs.py            # 文档导入脚本
│   │   └── install_openclaw_agents.sh # OpenClaw Agent 一键注册脚本
│   │
│   ├── agents/                       # OpenClaw Agent SOUL.md 定义
│   │   ├── GLOBAL.md                 # 全局规则（通信协议、防停滞、安全红线）
│   │   ├── groups/                   # 层级共享规则
│   │   │   ├── coordination.md       # 协调层（首席助理、策略中心、评审委）
│   │   │   └── execution.md          # 执行层（产品、开发、测试、运维）
│   │   ├── org_chief_assistant/SOUL.md # 首席助理（Edict 入口，需求分拣）
│   │   ├── org_strategy_hub/SOUL.md  # 策略中心（计划制定+审核+下发）
│   │   ├── org_review_board/SOUL.md  # 评审委（四维审核）
│   │   ├── org_ceo/SOUL.md           # CEO 总智能体
│   │   ├── org_tech_lead/SOUL.md     # 星核StarCore（任务派发）
│   │   ├── org_product/SOUL.md       # 蓝图BlueForm
│   │   ├── org_developer/SOUL.md     # 灵码SmartCode
│   │   └── ...                       # 共 27 个 Agent
│   │
│   ├── tests/                        # 测试
│   │   └── test_system.py            # 系统测试
│   │
│   ├── requirements.txt              # Python 依赖
│   ├── .env.example                  # 环境变量示例
│   └── Dockerfile                    # Docker 配置
│
├── frontend/                         # 前端应用
│   ├── src/
│   │   ├── main.jsx                  # React 入口
│   │   └── App.jsx                   # 主应用组件（包含所有 UI 逻辑）
│   │
│   ├── index.html                    # HTML 模板
│   ├── package.json                  # Node.js 依赖
│   ├── .env.orgagents                # OrgAgents 模式环境变量
│   ├── .env.starcore                 # StarCore 模式环境变量
│   └── vite.config.js                # Vite 配置
│
├── docs/                             # 文档
│   ├── 开发计划.md                    # 开发计划
│   └── 项目框架图.svg                 # 架构图
│
├── docker-compose.yml                # Docker Compose 配置
└── README.md                         # 项目说明文档
```

## 📄 核心文件详解

### 后端核心文件

#### `backend/app/main.py`
**FastAPI 主入口，定义所有 API 端点**

主要功能：
- `/chat/stream` - 流式对话端点（SSE），支持分步执行与确认，含 Edict 流水线模式
- `/chat/stop` - 停止正在执行的流式会话
- `/chat` - 普通对话端点
- `/knowledge-bases/*` - 知识库管理 API
- `/agent-kb-bindings/*` - 智能体-知识库绑定 API
- `/agent-configs/*` - 智能体配置管理 API
- `/skills/*` - 技能库 CRUD API
- `/agent-skill-bindings/*` - 智能体-技能绑定 API
- `/registry` - 获取智能体注册表（含技能绑定信息）

---

#### `backend/app/step_executor.py`
**分步执行引擎**

替代 LangGraph 编译图执行，实现逐节点执行、暂停确认、动态计划扩展：
- 每个可暂停节点执行完后等待用户确认（继续/重新生成/修改）
- 支持会话取消（配合 `/chat/stop` 端点）
- 动态扩展执行计划（CEO 分析后展开部门序列，部门长规划后展开子智能体序列）

---

#### `backend/app/session_store.py`
**会话状态存储**

在分步执行的暂停点之间保存中间状态：
- `SessionData` 存储执行计划、游标、状态等
- 支持会话取消标记（`cancelled` 字段）
- 自动清理过期会话

---

#### `backend/app/skill.py`
**技能服务（CRUD）+ 智能体-技能绑定服务**

- `SkillService` - 技能的增删改查，持久化到 `skills.json`
- `AgentSkillService` - 智能体与技能的绑定关系管理，持久化到 `agent_skill_bindings.json`
- 配合 `utils/agent_skills.py` 的 `inject_skills_into_prompt()` 将已启用技能以 XML 格式注入系统提示词

---

#### `backend/app/agent_config.py`
**智能体配置服务**

统一管理所有智能体的提示词、名称和描述：
- `DEFAULT_SYSTEM_PROMPTS` - 系统提示词（定义角色和行为）
- `DEFAULT_USER_PROMPTS` - 用户提示词模板（格式化输入）
- `DEFAULT_CONTEXT_TURNS` - 默认上下文轮数（LLM 调用时携带的历史对话轮数）
- 支持通过 API 自定义覆盖默认配置，持久化到 `agent_configs.json`

---

#### `backend/app/departments/registry.py`
**部门与子智能体配置注册表**

所有部门（含技术部）统一使用配置驱动：
- `DEPARTMENT_CONFIGS` - 部门配置（子智能体列表、默认计划）
- `SUB_AGENT_CONFIGS` - 子智能体配置（显示名、链式输入、结果键）
- `create_sub_agent_node()` - 工厂函数，根据配置自动生成节点

---

#### `backend/app/departments/base.py`
**通用部门长基类**

所有部门部长共用同一个类 `DepartmentLeadAgent`：
- 自动从 registry 读取配置并构建工作流
- `_lead_plan_node` - 调用 LLM 制定子智能体执行计划
- `_dispatch_node` / `_route_sub_agent` - 按计划依次分发到子智能体

---

#### `backend/app/ceo.py`
**CEO 总智能体，负责意图分析和跨部门编排**

核心节点：
1. `analyze_intent_node` - 分析用户意图，制定跨部门执行计划
2. `dispatch_to_department_node` - 调度到具体部门
3. `trigger_actions_node` - 处理跨部门触发（如销售成单 → 维修派单）
4. `summarize_result_node` - 生成 CEO 级别的高层总结

---

#### `backend/app/utils/streaming.py`
**流式输出核心函数**

`stream_llm_text` 函数：
```python
async def stream_llm_text(llm, prompt, state, node_name, active_agent) -> str:
    writer = state.get("context", {}).get("stream_writer")
    async for chunk in llm.astream(prompt):
        if writer:
            await writer({"type": "stream", "content": chunk.content, ...})
    return full_text
```

---

### 前端核心文件

#### `frontend/src/App.jsx`
**主应用组件（包含所有 UI 逻辑）**

核心功能：
1. **会话管理** - 多会话切换、创建
2. **流式渲染** - SSE 接收并实时显示
3. **分步确认** - 每个智能体执行后可继续/重新生成/修改
4. **停止按钮** - 流式输出期间可随时中断（AbortController + `/chat/stop`）
5. **流程树可视化** - 展示智能体执行流程
6. **知识库管理** - 创建、绑定、测试知识库
7. **智能体配置** - 自定义提示词和名称
8. **技能管理** - 创建、编辑、删除技能，绑定到子智能体
9. **Edict 流水线可视化** - 实时显示 Edict 各节点执行状态（EdictPipelineFlow 组件）
10. **多模式支持** - orgagents / starcore / full 三种应用模式，通过 `VITE_APP_MODE` 切换

**应用模式**：

| 模式 | 说明 | CEO 入口 | 包含部门 |
|------|------|----------|----------|
| `orgagents` | 万象智团（默认） | 有 | 全部（不含 TECH） |
| `starcore` | 星核 StarCore | 无 | 仅 TECH |
| `full` | 完整模式 | 有 | 全部 6 个部门 |

---

## 🚀 核心功能

### 1. 三层智能体协作

- **CEO 层**：意图分析 + 跨部门编排
- **部门层**：动态编排子智能体（所有部门统一配置驱动）
- **执行层**：具体任务执行（文本回答，支持知识库增强）

### 2. 配置驱动的统一架构

- 所有部门（含技术部）使用同一套 `DepartmentLeadAgent` 基类
- 子智能体通过 `SUB_AGENT_CONFIGS` 配置自动生成，无需手写代码
- 支持链式传递（`input_from`）和自定义结果键
- 提示词、名称、描述均可通过 API 在线修改

### 3. 分步执行与确认

- 每个智能体节点执行完后暂停，等待用户确认
- 支持三种操作：继续执行、重新生成、修改建议
- 会话状态持久化，支持多轮交互

### 4. 停止按钮

- 流式输出期间可随时点击停止
- 前端通过 AbortController 断开 SSE 连接
- 后端通过 `/chat/stop` 标记会话取消
- 停止后可继续发送新消息

### 5. 真实流式输出

- 使用 `llm.astream()` 进行真实模型流式调用
- 每个 token 生成后立即通过 SSE 发送到前端
- 前端直接显示，无需模拟动画

### 6. 知识库增强

- 支持上传文档并自动向量化
- 智能体可绑定多个知识库
- 自动检索相关文档并注入 prompt
- 支持召回测试和分块预览

### 7. 技能系统

- 创建可复用的技能（指令/规范/参考文档）
- 将技能绑定到任意子智能体
- 已启用的技能以 XML 格式自动注入系统提示词
- 前端可视化管理技能库和绑定关系

### 8. 可视化流程树
- 实时展示智能体执行流程
- 树形结构展示部门和子智能体
- 每次新消息自动清空并重新记录

### 9. 多会话管理

- 支持同时与多个智能体对话
- 每个会话独立的历史记录
- 可切换到 CEO、部门部长、子智能体

### 10. 会话上下文记忆

- 每个智能体（CEO、部门长、子智能体）调用 LLM 时可携带历史对话上下文
- 可在智能体配置界面中独立配置"上下文轮数"（context_turns，默认 3）
- 设为 0 则无上下文记忆，与传统单轮对话行为一致
- 各智能体配置互不影响，部门长和子智能体可设置不同的上下文深度

## 🦞 OpenClaw 深度整合

### 架构概述

系统支持双后端切换：默认使用 LangChain 直调 DashScope，也可切换为 OpenClaw Agent 体系。

```
┌─────────────────────────────────────────────────────────────────┐
│                    org-agents 后端 (FastAPI)                      │
│                                                                   │
│  step_executor.py → 各节点函数 → if use_openclaw():              │
│                                     │                             │
│                        ┌────────────┴────────────┐               │
│                        ▼                         ▼               │
│               LangChain 分支              OpenClaw 分支           │
│            (stream_llm_text)        (stream_openclaw_text)       │
│                   │                          │                    │
│                   ▼                          ▼                    │
│            DashScope API            OpenClaw Gateway              │
│            (直连流式)           /v1/chat/completions (SSE 流式)   │
│                                          │                        │
│                                          ▼                        │
│                                   27 个独立 Agent                 │
│                                 (SOUL.md + 独立工作区)            │
└─────────────────────────────────────────────────────────────────┘
```

### 切换机制

通过环境变量 `LLM_BACKEND` 控制，默认 `langchain`，零回归风险：

| 环境变量 | 说明 |
|----------|------|
| `LLM_BACKEND=langchain` | 默认，所有 LLM 调用走 LangChain + DashScope |
| `LLM_BACKEND=openclaw` | 全局切换为 OpenClaw Gateway 流式调用 |
| `OPENCLAW_AGENTS=product,developer` | 仅指定 agent 走 OpenClaw，其余仍走 LangChain |

注意：`analyze_intent_node`（CEO 意图分析）始终使用 LangChain，因为需要可靠的 JSON 解析。

### 流式实现原理

OpenClaw Gateway 内置了 OpenAI 兼容的 HTTP 端点 `/v1/chat/completions`，支持 `stream: true`：

```
Python 后端                    OpenClaw Gateway                  LLM Provider
    │                               │                               │
    │  POST /v1/chat/completions    │                               │
    │  stream: true                 │                               │
    │  model: "org_faq"             │                               │
    │ ─────────────────────────────>│                               │
    │                               │  调用 org_faq Agent            │
    │                               │  (加载 SOUL.md + 工作区)       │
    │                               │ ─────────────────────────────>│
    │                               │                               │
    │   data: {"delta":"你"}        │<── token ─────────────────────│
    │<──────────────────────────────│                               │
    │   → SSE emit to frontend      │                               │
    │                               │                               │
    │   data: {"delta":"好"}        │<── token ─────────────────────│
    │<──────────────────────────────│                               │
    │   → SSE emit to frontend      │                               │
    │          ...                   │          ...                  │
    │   data: [DONE]                │                               │
    │<──────────────────────────────│                               │
```

每个 token 从 LLM → Gateway → Python 后端 → 前端，全链路真实流式，无模拟。

### 关键文件

| 文件 | 作用 |
|------|------|
| `core/openclaw.py` | `stream_openclaw_gateway()` — 通过 httpx 异步流式调用 Gateway SSE 端点 |
| `core/backend_selector.py` | `use_openclaw(agent_id)` — 读取环境变量决定使用哪个后端 |
| `utils/openclaw_streaming.py` | `stream_openclaw_text()` — 与 `stream_llm_text()` 签名一致的适配器 |
| `departments/registry.py` | `create_sub_agent_node()` 内 `if use_openclaw()` 分支 |
| `departments/base.py` | `_lead_plan_node()` 内 `if use_openclaw()` 分支 |
| `ceo.py` | `summarize_result_node()` 内 `if use_openclaw()` 分支 |
| `agents/org_*/SOUL.md` | 27 个 Agent 的角色定义 |
| `agents/GLOBAL.md` | 全局规则（通信协议、防停滞、安全红线），安装时复制为各 workspace 的 AGENTS.md |
| `scripts/install_openclaw_agents.sh` | 一键注册脚本（workspace + subagent 白名单 + GLOBAL.md 复制） |

### Agent ID 映射

所有 Agent 加 `org_` 前缀，避免与 edict 项目的 Agent 冲突：

| 角色 | Agent ID | SOUL.md 路径 |
|------|----------|-------------|
| CEO | `org_ceo` | `agents/org_ceo/SOUL.md` |
| 首席助理 | `org_chief_assistant` | `agents/org_chief_assistant/SOUL.md` |
| 策略中心 | `org_strategy_hub` | `agents/org_strategy_hub/SOUL.md` |
| 评审委 | `org_review_board` | `agents/org_review_board/SOUL.md` |
| 市场部部长 | `org_market_lead` | `agents/org_market_lead/SOUL.md` |
| 技术部部长 | `org_tech_lead` | `agents/org_tech_lead/SOUL.md` |
| 蓝图BlueForm | `org_product` | `agents/org_product/SOUL.md` |
| 灵码SmartCode | `org_developer` | `agents/org_developer/SOUL.md` |
| ... | ... | 共 27 个 |

### Subagent 白名单

OpenClaw 的 subagent 白名单控制 Agent 间的调用权限：

```
org_ceo              → [org_market_lead, org_tech_lead, org_sales_lead, ...]
org_chief_assistant  → [org_strategy_hub]
org_strategy_hub     → [org_review_board, org_tech_lead]
org_review_board     → [org_strategy_hub, org_tech_lead]
org_tech_lead        → [org_strategy_hub, org_review_board, org_product, org_developer, org_tester, org_devops]
org_product          → [org_tech_lead]  (子智能体只能回报给部门长)
```

### 设置步骤

#### 1. 启用 Gateway 的 OpenAI 兼容端点

OpenClaw 0.2.0 默认关闭了 HTTP `/v1/chat/completions` 端点，需要手动开启：

```bash
# 方法一：用 jq 一键写入配置
jq '.gateway.http.endpoints.chatCompletions.enabled = true' ~/.openclaw/openclaw.json > /tmp/oc.json && mv /tmp/oc.json ~/.openclaw/openclaw.json

# 方法二：手动编辑 ~/.openclaw/openclaw.json，在 gateway 节点下添加：
# "http": {"endpoints": {"chatCompletions": {"enabled": true}}}

# 重启 gateway 使配置生效
openclaw gateway restart
```

验证端点是否可用：
```bash
TOKEN=$(jq -r '.gateway.auth.token' ~/.openclaw/openclaw.json)
curl -s -X POST http://127.0.0.1:18789/v1/chat/completions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"org_chief_assistant","stream":false,"messages":[{"role":"user","content":"你好"}]}' | head -5
```

如果返回 `Method Not Allowed`，说明配置未生效，检查 JSON 格式和 gateway 是否重启。

#### 2. 注册 Agent

```bash
cd backend
bash scripts/install_openclaw_agents.sh
```

脚本会为 27 个 Agent 创建独立工作区（`~/.openclaw/workspace-org_<id>/`），复制 SOUL.md 和 GLOBAL.md，配置 subagent 白名单。

#### 3. 配置环境变量

在 `backend/.env` 中添加：

```bash
LLM_BACKEND=openclaw
OPENCLAW_GATEWAY_URL=http://localhost:18789
# OPENCLAW_GATEWAY_TOKEN 可不填，会自动从 ~/.openclaw/openclaw.json 读取
```

#### 4. 验证

```bash
# 验证 Gateway 流式端点
curl -N -s -X POST http://localhost:18789/v1/chat/completions \
  -H "Authorization: Bearer <your_gateway_token>" \
  -H "Content-Type: application/json" \
  -d '{"model":"org_faq","stream":true,"messages":[{"role":"user","content":"你好"}]}'

# 启动后端
python app/main.py

# 前端发送请求，观察逐 token 流式输出
```

## 🎯 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- Docker (可选)

### 1. 后端启动

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API Key

# 启动服务
python app/main.py
```

后端将运行在 `http://localhost:8000`

### 2. 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev:orgagents -- --host 0.0.0.0 --port 5173
npm run dev:starcore -- --host 0.0.0.0 --port 5174

# 构建生产版本
npm run build:orgagents
npm run build:starcore
```

前端5173将运行在 `http://localhost:5173`

前端5174将运行在 `http://localhost:5174`

### 3. Docker 启动（可选）

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 📚 详细文档

### 单部门独立模式

系统支持将任意部门单独拆出，作为独立产品交付给客户。无需修改后端，仅通过前端 URL 参数控制。

#### 基本用法

在前端地址后追加 `?mode=department&dept=部门代码` 即可进入单部门模式：

```
# 完整模式（默认，CEO + 全部 6 个部门）
http://localhost:5173/

# 单独出售技术部
http://localhost:5173/?mode=department&dept=TECH

# 单独出售客服部
http://localhost:5173/?mode=department&dept=CS

# 单独出售运维部
http://localhost:5173/?mode=department&dept=REPAIR

# 单独出售市场部
http://localhost:5173/?mode=department&dept=MARKET

# 单独出售业务部
http://localhost:5173/?mode=department&dept=SALES

# 单独出售用户端
http://localhost:5173/?mode=department&dept=USER
```

#### 自定义品牌名称（白标交付）

追加 `&brand=` 参数可替换系统标题，适合给不同客户做白标：

```
http://localhost:5173/?mode=department&dept=TECH&brand=XX科技智能助手
http://localhost:5173/?mode=department&dept=CS&brand=智能客服系统
http://localhost:5173/?mode=department&dept=REPAIR&brand=智慧运维平台
```

不传 `brand` 时，默认使用 `{部门名}智能助手` 作为标题。

#### 部门代码对照表

| 代码 | 部门 | 自定义名称 | 包含的子智能体 |
|------|------|------------|----------------|
| `MARKET` | 市场部 | 市场智脑MarketMind | 需求分析专员、宣传推广专员 |
| `TECH` | 技术部 | 星核StarCore | 产品岗、开发岗、检测岗、运维部署 |
| `SALES` | 业务部 | 销售领航SalesPilot | 服务咨询专员、方案设计专员、实施计划专员 |
| `REPAIR` | 运维部 | 维修大师ServiceMaster | 派单经理、问题识别专家、现场执行 |
| `CS` | 客服部 | 客户中心ClientLink | FAQ智能助手、应急调度、人工客服座席 |
| `USER` | 用户端 | 智享家SmartLife | 服务状态、自主申报入口 |

#### 单部门模式与完整模式的区别

| 特性 | 完整模式 | 单部门模式 |
|------|----------|------------|
| CEO 入口 | 有 | 隐藏 |
| 部门列表 | 全部 6 个 | 仅目标部门 |
| 默认对话 | CEO 对话 | 部门长对话 |
| 新手教程 | 显示 | 跳过 |
| 子智能体列表 | 默认折叠 | 默认展开 |
| 后端接口 | 不变 | 不变 |
| 品牌标题 | 固定 | 可通过 `brand` 参数自定义 |

### API 文档

启动后端后访问：
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 主要 API 端点

#### 对话相关
- `POST /chat/stream` - 流式对话（SSE），支持分步确认
- `POST /chat/stop` - 停止正在执行的流式会话
- `POST /chat` - 普通对话

#### 知识库管理
- `GET /knowledge-bases` - 获取所有知识库
- `POST /knowledge-bases` - 创建知识库
- `POST /knowledge-bases/{kb_id}/documents` - 上传文档
- `POST /knowledge-bases/{kb_id}/recall-test` - 召回测试

#### 智能体管理
- `GET /registry` - 获取智能体注册表
- `GET /agent-kb-bindings/{agent_id}` - 获取智能体绑定的知识库
- `PUT /agent-kb-bindings/{agent_id}` - 更新绑定关系
- `GET /agent-configs/{agent_id}` - 获取智能体配置
- `PUT /agent-configs/{agent_id}` - 更新智能体配置（提示词、名称、上下文轮数等）

#### 技能管理
- `GET /skills` - 获取所有技能
- `POST /skills` - 创建技能
- `GET /skills/{skill_id}` - 获取单个技能
- `PUT /skills/{skill_id}` - 更新技能
- `DELETE /skills/{skill_id}` - 删除技能
- `GET /agent-skill-bindings/{agent_id}` - 获取智能体绑定的技能
- `PUT /agent-skill-bindings/{agent_id}` - 更新智能体-技能绑定

## 🧪 测试

### 流式输出测试

```bash
# 测试模型流式输出
python test_streaming.py

# 测试端到端流式输出
python test_e2e_streaming.py
```

### 系统测试

```bash
cd backend
python -m pytest tests/
```

## 🔧 配置说明

### 环境变量 (.env)

```bash
# LLM 配置
OPENAI_API_KEY=sk-xxx                                    # API Key
OPENAI_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME=qwen-plus                                     # 模型名称
EMBEDDING_MODEL=text-embedding-v4                        # 向量模型

# LLM 后端切换（OpenClaw 整合）
LLM_BACKEND=langchain                                    # langchain（默认）或 openclaw
OPENCLAW_GATEWAY_URL=http://localhost:18789               # OpenClaw Gateway 地址
OPENCLAW_GATEWAY_TOKEN=your_gateway_token_here            # Gateway Token（可选，自动读取）
OPENCLAW_TIMEOUT=300                                     # OpenClaw 请求超时（秒，默认 120，Edict 链路建议 300）
# OPENCLAW_AGENTS=product,developer                      # 仅指定 agent 走 OpenClaw（可选）

# Qdrant 配置
QDRANT_HOST=localhost                                    # Qdrant 主机
QDRANT_PORT=6333                                         # Qdrant 端口
QDRANT_COLLECTION=public_service_kb                      # 默认集合名

# 日志配置
LOG_LEVEL=INFO                                           # 日志级别
```

## 📊 性能优化

### 后端优化
- 使用 `asyncio` 异步处理
- LangGraph 并发执行独立节点
- Qdrant 向量检索缓存

### 前端优化
- React 虚拟滚动（长对话）
- SSE 连接复用
- 消息批量更新

## 🐛 常见问题

### 1. 流式输出不工作

**问题**：看到的是假流（固定间隔、固定大小）

**解决**：
- 检查 `AgentState` 是否正确定义 `context` 字段
- 确认所有节点都使用 `stream_llm_text` 而不是 `llm.ainvoke`
- 查看 `streamable_nodes` 是否包含该节点

### 2. 知识库检索失败

**问题**：智能体无法使用知识库内容

**解决**：
- 确认 Qdrant 服务正常运行
- 检查智能体是否绑定了知识库
- 查看文档是否成功向量化

### 3. 前端连接超时

**问题**：SSE 连接中断

**解决**：
- 检查后端是否正常运行
- 查看浏览器控制台错误
- 确认防火墙/代理设置

### 4. OpenClaw Gateway 返回 405 Method Not Allowed

**问题**：后端调用 `/v1/chat/completions` 返回 405

**解决**：
OpenClaw 0.2.0 默认关闭了 HTTP chat completions 端点，需要手动开启：
```bash
jq '.gateway.http.endpoints.chatCompletions.enabled = true' ~/.openclaw/openclaw.json > /tmp/oc.json && mv /tmp/oc.json ~/.openclaw/openclaw.json
openclaw gateway restart
```

### 5. OpenClaw 清理会话记录

```bash
# 只清会话记忆（保留 agent 注册）
rm -f ~/.openclaw/memory/*.sqlite

# 全部重置（需要重新跑 install_openclaw_agents.sh）
openclaw reset --scope full --yes
```

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发流程
1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📝 更新日志

### v1.6.0 (2026-04-10)
- ✅ StarCore Edict 流水线模式
  - 新增 3 个编排层 Agent：首席助理 ChiefAssistant、策略中心 StrategyHub、评审委 ReviewBoard
  - 编排逻辑写在 SOUL.md 提示词里，由 OpenClaw subagent 链式调用驱动
  - 整条链（首席助理→策略中心→评审委→星核部长→子智能体）在一次 OpenClaw 调用里跑完
  - 评审委四维审核（可行性/完整性/风险/资源），封驳循环最多 3 轮
  - 新增 GLOBAL.md 全局规则（通信协议、防停滞、安全红线）
  - 新增 groups/ 层级共享规则（协调层 + 执行层）
  - 前端新增 Edict 流水线可视化组件，实时显示各节点执行状态
  - 前端 TECH 部门默认对话入口改为首席助理
  - 后端 `/chat/stream` 新增 edict 模式分支，绕过 step_executor 直接流式调用
  - OpenClaw 超时从 120s 提升到 300s
  - 需要在 `openclaw.json` 中开启 `gateway.http.endpoints.chatCompletions.enabled = true`
  - Agent 总数从 24 增至 27

### v1.5.0 (2026-04-09)
- ✅ OpenClaw 深度整合（详见 [OpenClaw 深度整合](#-openclaw-深度整合) 章节）
  - 新增双后端切换：`LLM_BACKEND=langchain|openclaw`，默认 langchain，零回归
  - 通过 OpenClaw Gateway `/v1/chat/completions` SSE 端点实现真正的逐 token 流式输出
  - 24 个 Agent 注册为独立 OpenClaw Agent，各有 SOUL.md 和独立工作区
  - Subagent 白名单控制 Agent 间调用权限
  - 一键注册脚本 `install_openclaw_agents.sh`
  - 支持按 Agent 粒度切换后端：`OPENCLAW_AGENTS=product,developer`
  - CEO 意图分析节点保留 LangChain（JSON 解析可靠性）

### v1.4.5 (2026-04-08)
- ✅ 技能系统（Skills）
  - 新增技能库管理：创建、编辑、删除技能，每个技能包含名称、描述和指令内容
  - 新增智能体-技能绑定：任意子智能体可绑定多个技能
  - 技能自动注入：绑定的已启用技能以 XML 格式追加到智能体系统提示词末尾
  - 前端新增「技能库管理」面板（SkillManager 组件），支持可视化创建和编辑技能
  - 注册表 `/registry` 端点增强，返回每个智能体已绑定的技能信息
  - 新增 API 端点：`/skills` CRUD、`/agent-skill-bindings/{agent_id}` 绑定管理

### v1.4.0 (2026-04-07)
- ✅ 会话上下文记忆
  - 所有智能体（CEO、部门长、子智能体）调用 LLM 时支持携带历史对话上下文
  - 新增 `context_turns` 配置项，可在智能体配置界面通过滑块调整（0-50，默认 3）
  - 新增 `get_history_messages()` 工具函数，从 state 中提取最近 N 轮对话
  - 各智能体独立配置，互不影响

### v1.3.0 (2026-04-07)
- ✅ 统一架构重构
  - 所有部门（含技术部）统一使用配置驱动的 `DepartmentLeadAgent` 基类
  - 子智能体通过 `SUB_AGENT_CONFIGS` 配置自动生成，删除所有独立 `agent.py` / `sub_agents.py`
  - 新增 `departments/registry.py` 集中管理部门和子智能体配置
  - 新增 `agent_config.py` 统一管理提示词，支持在线修改
- ✅ 新增停止按钮
  - 流式输出期间显示红色停止按钮，点击立即中断
  - 前端 AbortController 断开 SSE + 后端 `/chat/stop` 取消执行
  - 停止后界面恢复可输入状态，可继续发新消息
- ✅ 新增分步执行引擎 (`step_executor.py`)
  - 替代 LangGraph 编译图执行，逐节点执行并支持暂停/确认
  - 动态计划扩展（CEO → 部门序列，部门长 → 子智能体序列）
  - 会话状态持久化 (`session_store.py`)

### v1.2.0 (2026-04-03)
- ✅ 优化需求澄清循环机制
  - 技术部智能体支持最多3次需求澄清
  - 每次用户回复后重新分析需求清晰度
  - 显示剩余澄清次数，避免无限循环
  - 达到最大次数后自动使用现有信息继续执行
- ✅ 新增分步执行确认机制
  - 每个智能体执行完成后暂停等待用户确认
  - 支持继续、重新生成、修改建议三种操作
  - 会话状态持久化，支持多轮交互
- ✅ 改进流式输出体验
  - 优化 SSE 事件处理逻辑
  - 新增执行阶段状态追踪
  - 完善错误处理和会话恢复

### v1.1.0 (2026-04-02)
- ✅ 单部门独立模式（支持拆分出售单个部门）

### v1.0.0 (2026-03-31)
- ✅ 实现三层智能体架构
- ✅ 真实流式输出
- ✅ 知识库增强
- ✅ 可视化流程树
- ✅ 多会话管理

## 📄 许可证

MIT License

## 👥 作者

OrgAgents 开发团队

---

**说明**：OrgAgents 是一个通用的企业级多智能体协作框架，适用于各类行业场景，包括但不限于：
- 企业智能办公
- 市政服务管理
- 公共设施运维
- 政务服务系统
- 智慧园区管理

通过三层智能体架构（CEO → 部门长 → 子智能体），任何小团队或个人都可以拥有一支完整的 AI 协作团队。

## 🙏 致谢

- [OpenClaw](https://github.com/nicepkg/openclaw) - 多 Agent 管理平台，提供独立工作区、SOUL.md、subagent 白名单
- [LangChain](https://github.com/langchain-ai/langchain)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [Qdrant](https://qdrant.tech/)
