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

## 🛠️ 技术栈

### 后端
- **框架**: FastAPI (异步 Web 框架)
- **智能体编排**: LangGraph (状态图工作流)
- **LLM**: LangChain + 通义千问 (Qwen)
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
│   │   ├── kb.py                     # 知识库服务，管理文档和向量检索
│   │   ├── agent_kb.py               # 智能体-知识库绑定服务
│   │   │
│   │   ├── core/                     # 核心模块
│   │   │   ├── llm.py                # LLM 配置和初始化
│   │   │   ├── agent.py              # 基础智能体类定义
│   │   │   └── registry.py           # 智能体注册表，管理所有子智能体
│   │   │
│   │   ├── departments/              # 部门智能体
│   │   │   ├── base.py               # 部门部长基类
│   │   │   │
│   │   │   ├── market/               # 市场部
│   │   │   │   ├── agent.py          # 市场部部长（动态编排）
│   │   │   │   └── sub_agents.py     # 需求分析、宣传推广智能体
│   │   │   │
│   │   │   ├── tech/                 # 技术部
│   │   │   │   ├── agent.py          # 技术部部长（流水线编排）
│   │   │   │   └── sub_agents.py     # 产品、开发、测试、运维智能体
│   │   │   │
│   │   │   ├── sales/                # 业务部
│   │   │   │   ├── agent.py          # 业务部部长
│   │   │   │   └── sub_agents.py     # 服务咨询、方案设计智能体
│   │   │   │
│   │   │   ├── repair/               # 运维部
│   │   │   │   ├── agent.py          # 运维部部长
│   │   │   │   └── sub_agents.py     # 派单、问题识别、现场执行智能体
│   │   │   │
│   │   │   ├── cs/                   # 客服部
│   │   │   │   ├── agent.py          # 客服部部长
│   │   │   │   └── sub_agents.py     # FAQ、应急调度、人工客服智能体
│   │   │   │
│   │   │   └── user/                 # 用户管理
│   │   │       ├── agent.py          # 用户端部长
│   │   │       └── sub_agents.py     # 服务状态、自主申报智能体
│   │   │
│   │   ├── utils/                    # 工具模块
│   │   │   ├── streaming.py          # 流式输出核心函数
│   │   │   ├── logger.py             # 日志配置
│   │   │   ├── messages.py           # 消息处理工具
│   │   │   ├── labels.py             # 标签和格式化工具
│   │   │   ├── agent_knowledge.py    # 知识库注入工具
│   │   │   └── retriever.py          # 向量检索工具
│   │   │
│   │   └── db/                       # 数据库
│   │       └── qdrant.py             # Qdrant 向量数据库客户端
│   │
│   ├── data/                         # 数据存储
│   │   ├── knowledge_bases.json      # 知识库元数据
│   │   ├── agent_kb_bindings.json    # 智能体-知识库绑定关系
│   │   └── kb_files/                 # 知识库文档文件
│   │
│   ├── scripts/                      # 脚本工具
│   │   └── ingest_docs.py            # 文档导入脚本
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
│   └── vite.config.js                # Vite 配置
│
├── docs/                             # 文档
│   ├── 开发计划.md                    # 开发计划
│   └── 项目框架图.svg                 # 架构图
│
├── test_streaming.py                 # 流式输出测试脚本
├── test_e2e_streaming.py             # 端到端流式测试脚本
├── docker-compose.yml                # Docker Compose 配置
└── README.md                         # 项目说明文档
```

## 📄 核心文件详解

### 后端核心文件

#### `backend/app/main.py`
**FastAPI 主入口，定义所有 API 端点**

主要功能：
- `/chat/stream` - 流式对话端点（SSE）
- `/chat` - 普通对话端点
- `/knowledge-bases/*` - 知识库管理 API
- `/agent-kb-bindings/*` - 智能体-知识库绑定 API
- `/registry` - 获取智能体注册表

关键实现：
```python
@app.post("/chat/stream")
async def chat_stream(input: UserInput):
    # 创建 SSE 事件生成器
    async def event_generator():
        # 监听 LangGraph astream_events
        async for event in runnable.astream_events(initial_state, version="v2"):
            # 处理流式事件并发送到前端
            if event["event"] == "on_chat_model_stream":
                await emit_sse({"type": "stream", "content": chunk.content})
```

---

#### `backend/app/ceo.py`
**CEO 总智能体，负责意图分析和跨部门编排**

核心节点：
1. `analyze_intent_node` - 分析用户意图，制定跨部门执行计划
2. `dispatch_to_department_node` - 调度到具体部门
3. `trigger_actions_node` - 处理跨部门触发（如销售成单 → 维修派单）
4. `summarize_result_node` - 生成 CEO 级别的高层总结

工作流程：
```python
workflow = StateGraph(AgentState)
workflow.add_node("analyze_intent", analyze_intent_node)
workflow.add_node("dispatch_to_department", dispatch_to_department_node)
workflow.add_node("MARKET", market_lead.workflow.compile())
workflow.add_node("TECH", tech_lead.workflow.compile())
# ... 其他部门
workflow.add_node("summarize_result", summarize_result_node)
```

---

#### `backend/app/state.py`
**AgentState 定义，LangGraph 状态管理**

核心字段：
```python
class AgentState(TypedDict, total=False):
    messages: List[BaseMessage]           # 对话历史
    context: Dict[str, Any]               # 上下文（包含 stream_writer）
    plan: List[str]                       # CEO 制定的部门执行计划
    plan_step: int                        # 当前执行到第几个部门
    sub_plan: List[str]                   # 部门内部的子智能体计划
    sub_plan_step: int                    # 当前执行到第几个子智能体
    results: Dict[str, Any]               # 各部门的执行结果
    execution_log: List[Dict[str, Any]]   # 执行日志（用于流程树）
```

---

#### `backend/app/departments/base.py`
**部门部长基类**

所有部门部长都继承此类：
```python
class DepartmentLeadAgent:
    def __init__(self, name: str, department: str):
        self.name = name
        self.department = department
        self.workflow = StateGraph(AgentState)
        self.setup_workflow()  # 子类实现具体编排逻辑

    def setup_workflow(self):
        # 子类实现：添加节点、定义边、设置路由
        raise NotImplementedError
```

---

#### `backend/app/departments/tech/agent.py`
**技术部部长（流水线编排）**

特点：串行流水线，支持测试失败回流

工作流程：
```
tech_lead_plan → product → developer → tester → devops
                                          ↓ (失败)
                                      developer
```

核心逻辑：
```python
def decide_tester_outcome(self, state: AgentState) -> str:
    if not state.get("test_passed", True):
        return "fail"  # 回流到 developer
    return "pass"      # 继续到 devops
```

---

#### `backend/app/departments/tech/sub_agents.py`
**技术部子智能体**

包含 4 个子智能体：
1. `product_agent_node` - 产品岗：生成 PRD 文档
2. `developer_agent_node` - 开发岗：编写代码
3. `tester_agent_node` - 测试岗：代码质量检测
4. `devops_agent_node` - 运维岗：部署上线

每个智能体都使用 `stream_llm_text` 实现真实流式输出。

---

#### `backend/app/utils/streaming.py`
**流式输出核心函数**

`stream_llm_text` 函数：
```python
async def stream_llm_text(
    llm: Any,
    prompt: Any,
    state: dict,
    node_name: str,
    active_agent: str,
) -> str:
    writer = state.get("context", {}).get("stream_writer")

    async for chunk in llm.astream(prompt):  # 真实模型流式调用
        content = chunk.content
        if writer:
            await writer({
                "type": "stream",
                "content": content,
                "node": node_name,
                "active_agent": active_agent,
            })

    return full_text
```

---

#### `backend/app/kb.py`
**知识库服务**

功能：
- 创建/更新/删除知识库
- 上传文档并自动分块
- 向量化存储到 Qdrant
- 召回测试（检索相关文档）

核心方法：
```python
class KnowledgeBaseService:
    def add_document(self, kb_id, filename, content, separator, chunk_size, chunk_overlap):
        # 1. 文本分块
        chunks = self._split_text(content, separator, chunk_size, chunk_overlap)
        # 2. 向量化
        embeddings = self.embedding_model.embed_documents(chunks)
        # 3. 存储到 Qdrant
        self.qdrant_client.upsert(collection_name=kb_id, points=points)
```

---

#### `backend/app/utils/agent_knowledge.py`
**知识库注入工具**

自动为智能体注入相关知识：
```python
def inject_knowledge_into_prompt(agent_id: str, query: str, base_prompt: str):
    # 1. 获取该智能体绑定的知识库
    kb_ids = agent_kb_service.get_binding(agent_id)

    # 2. 从知识库中检索相关文档
    for kb_id in kb_ids:
        docs = kb_service.recall_test(kb_id, query, top_k=3)

    # 3. 注入到 prompt
    enhanced_prompt = f"{base_prompt}\n\n参考资料：\n{docs}"
    return enhanced_prompt
```

---

### 前端核心文件

#### `frontend/src/App.jsx`
**主应用组件（包含所有 UI 逻辑）**

核心功能：
1. **会话管理** - 多会话切换、创建、删除
2. **流式渲染** - SSE 接收并实时显示
3. **流程树可视化** - 展示智能体执行流程
4. **智能体注册表** - 展示所有可用智能体
5. **知识库管理** - 创建、绑定、测试知识库

关键实现：
```javascript
const handleSend = async () => {
  // 清空流程树，准备记录新的执行流程
  updateConversation(conversationId, (conversation) => ({
    ...conversation,
    executionLog: [],
    loading: true,
  }));

  // 建立 SSE 连接
  const response = await fetch(`${API_URL}/chat/stream`, {
    method: 'POST',
    body: JSON.stringify({ query, target_agent, target_type }),
  });

  // 读取流式数据
  const reader = response.body.getReader();
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    // 解析 SSE 事件
    const data = JSON.parse(line.slice(6));

    if (data.type === 'stream') {
      // 直接追加内容，实现真实流式输出
      updateConversation(conversationId, (conversation) => ({
        ...conversation,
        messages: [...messages, { content: content + data.content }],
      }));
    }
  }
};
```

---

## 🚀 核心功能

### 1. 三层智能体协作

- **CEO 层**：意图分析 + 跨部门编排
- **部门层**：动态/流水线编排子智能体
- **执行层**：具体任务执行（产品、开发、测试等）

### 2. 真实流式输出

- 使用 `llm.astream()` 进行真实模型流式调用
- 每个 token 生成后立即通过 SSE 发送到前端
- 前端直接显示，无需模拟动画
- 支持多节点并发流式输出

### 3. 知识库增强

- 支持上传文档并自动向量化
- 智能体可绑定多个知识库
- 自动检索相关文档并注入 prompt
- 支持召回测试和分块预览

### 4. 可视化流程树

- 实时展示智能体执行流程
- 树形结构展示部门和子智能体
- 每次新消息自动清空并重新记录

### 5. 多会话管理

- 支持同时与多个智能体对话
- 每个会话独立的历史记录
- 可切换到 CEO、部门部长、子智能体

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
npm run dev -- --host 0.0.0.0 --port 5173
```

前端将运行在 `http://localhost:5173`

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

| 代码 | 部门 | 包含的子智能体 |
|------|------|----------------|
| `MARKET` | 市场部 | 需求分析专员、宣传推广专员 |
| `TECH` | 技术部 | 产品岗、开发岗、检测岗、运维部署 |
| `SALES` | 业务部 | 服务咨询专员、方案设计专员、实施计划专员 |
| `REPAIR` | 运维部 | 派单经理、问题识别专家、现场执行 |
| `CS` | 客服部 | FAQ智能助手、应急调度、人工客服座席 |
| `USER` | 用户端 | 服务状态、自主申报入口 |

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
- `POST /chat/stream` - 流式对话（SSE）
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

# Qdrant 配置
QDRANT_URL=http://localhost:6333                         # Qdrant 地址
QDRANT_API_KEY=                                          # API Key（可选）

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

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发流程
1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📝 更新日志

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

- [LangChain](https://github.com/langchain-ai/langchain)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [Qdrant](https://qdrant.tech/)
