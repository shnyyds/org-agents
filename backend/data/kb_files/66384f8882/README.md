# 智慧城市公共服务多智能体（Multi-Agent）协作系统

本项目旨在通过 **LangGraph** 状态机编排技术，构建一个面向智慧城市公共服务的全流程、全自动化的多智能体协同系统。通过 CEO 总智能体作为中央控制器，协调 6 大职能部门（市场、技术、销售、维修、客服、用户端），实现从客户咨询、方案设计到安装维保的全生命周期闭环管理。

## 核心架构设计

### 1. CEO 双层编排模式
*   **中央大脑 (Orchestrator)**：CEO 智能体负责任务解析、跨部门意图判断、流程串并行决策。
*   **部门长自治 (Department Lead)**：各部门长智能体独立编排内部子智能体。通过 `DepartmentLeadAgent` 基类统一实现。

### 2. 状态流转与持久化 (LangGraph)
*   **全局状态 (AgentState)**：统一的状态定义，包含消息历史、意图分析结果、各部门执行结果及全局上下文。
*   **Checkpointer**：支持任务进度的持久化，确保长时间运行的任务可恢复。

### 3. 基础设施支持
*   **向量数据库 (Qdrant)**：统一的 RAG 支持，提供智慧城市公共服务标准、FAQ、维修案例等知识检索。
*   **结构化日志 (Loguru)**：全局日志追踪，记录每个 Agent 的决策链路。

## 🚀 快速启动 (Quick Start)

### 1. 环境准备 (Conda)
```bash
# 创建并激活 Conda 环境
conda activate elevator_env

# 安装后端依赖
cd backend
pip install -r requirements.txt

# 配置环境变量 (首次启动需配置)
cp .env.example .env
# 编辑 .env 填入 DashScope API Key (sk-...)
```

### 2. 启动后端服务 (FastAPI)
```bash
# 确保在 backend 目录下
cd backend

# 1. (可选) 启动 Qdrant 向量数据库 (如需使用知识库)
# docker-compose up -d qdrant

# 2. 启动 FastAPI 后端 (Mac/Linux)
export PYTHONPATH=$PYTHONPATH:.
python app/main.py
```
> **注意**: 如果端口 8000 被占用，可使用 `lsof -ti:8000 | xargs kill -9` 清理后再启动。

### 3. 启动前端界面 (Vite)
```bash
# 进入前端目录
cd frontend

# 安装依赖 (首次启动需安装)
npm install

# 启动开发服务器
npm run dev -- --host 0.0.0.0 --port 5173
```
- **后端地址**: [http://localhost:8000](http://localhost:8000)
- **前端地址**: [http://localhost:5173](http://localhost:5173)

---

## 核心架构设计
*   **CEO 智能编排**：自动解析用户意图，支持跨部门触发（如：销售成单自动派发维修任务）。
*   **技术部闭环 Pipeline**：实现 PRD -> 开发 -> 四维检测 -> (失败回流) -> 运维的完整流水线。
*   **RAG 知识库集成**：所有智能体均可实时检索 Qdrant 中的智慧城市公共服务标准与历史案例。
*   **现代 UI 交互**：基于 React + Tailwind CSS 的专业监控与聊天面板，支持 **SSE 实时流式状态输出**，可实时监控每个智能体的工作细节。

## 部门实现详情

### 技术部 (TECH) - 全自动化 Pipeline
技术部通过 `TechLeadAgent` 实现了一个完整的串行编排流，包含以下子智能体：
1.  **产品岗 (Product Agent)**: 解析原始需求，生成 PRD 文档与 UI 设计方案。
2.  **开发岗 (Developer Agent)**: 基于 PRD 文档编写核心业务代码。
3.  **检测岗 (Tester Agent)**: 执行安全、规范、功能、兼容性检测。若检测不合格（模拟失败），会自动回流至开发岗进行修正。
4.  **运维岗 (DevOps Agent)**: 执行分布式部署，输出部署报告与监控状态。

### 其他部门状态 (V1 骨架)
*   **市场部 (MARKET)**: 行业分析 -> 宣传文案生成。
*   **销售部 (SALES)**: 线索获取 -> 自动报价 -> CAD 出图。
*   **维修部 (REPAIR)**: 派单管理 -> 故障大师识别 -> 维修工执行。
*   **客服部 (CS)**: FAQ 咨询 -> 紧急救援识别 -> 人工转接。
*   **用户端 (USER)**: 设备状态查询 -> 报修入口。

## 目录结构说明
*   `backend/app/core`: 核心抽象类（如 `BaseAgent`, `DepartmentLeadAgent`）
*   `backend/app/departments`: 6大部门的具体实现
*   `backend/app/db`: 数据库连接与初始化工具
*   `backend/app/utils`: 包含全局日志、提示词管理等通用工具
*   `docs/`: 项目原始设计文档与排期表备份

## 技术栈 (Technology Stack)

### 后端 (Backend)
*   **核心引擎**：[LangGraph](https://github.com/langchain-ai/langgraph) (用于状态机编排)
*   **智能体框架**：[LangChain](https://github.com/langchain-ai/langchain)
*   **大语言模型**：Qwen 3.5 Plus (via Aliyun DashScope)
*   **向量数据库**：Qdrant (用于存储行业标准、FAQ、维修案例等知识库)
*   **目录结构**：
    *   `app/core`: 核心抽象类（如 `BaseAgent`）
    *   `app/departments`: 各部门智能体（Market, Tech, Sales, Repair, CS, User）
    *   `app/db`: 数据库连接（Qdrant）
    *   `app/utils`: 通用工具（提示词解析、日志）
*   **编程语言**：Python 3.10+

### 前端 (Frontend)
*   **核心框架**：React + Vite (现代、快速、响应式)
*   **UI 组件库**：Tailwind CSS + Headless UI (打造专业、现代的工业风格界面)
*   **交互平台集成**：飞书 API, 钉钉 API, 微信小程序 (多入口接入)
*   **数据可视化**：ECharts / Recharts (用于 CEO 监控看板)

### 基础设施 (Infrastructure)
*   **容器化**：Docker & Docker Compose (分布式部署)
*   **CI/CD**：GitHub Actions / GitLab CI
*   **监控**：Prometheus + Grafana

## 组织架构 (Organizational Structure)

1.  **市场部**：行业分析、竞品监控、宣传内容生成。
2.  **技术部**：产品 PRD、多岗开发、自动化检测、运维部署。
3.  **销售部**：线索获取、自动报价、CAD 出图、合同管理。
4.  **维修部**：智能派单、故障识别（颜色分级）、执行记录。
5.  **客服部**：FAQ 自助查询、紧急救援、人工兜底。
6.  **用户端**：设备监控、自主报修、咨询入口。

## 开发计划 (Development Roadmap)

### V1.0 基础版本 (Month 1: MVP)
*   搭建 CEO 智能体骨架与 LangGraph 基础图。
*   实现 6 大部门的 Mock 执行逻辑与 Web 端演示入口。
*   完成知识库 (RAG) 基础分块与投喂。

### V2.0 完整版本 (Month 2: Production Ready)
*   替换所有 Mock 为真实工具集成（如真实网络搜索、CAD 绘图库）。
*   深度打通所有 xlink 跨部门联动流程。
*   优化性能（查询 ≤3s）与安全加密机制。

---
*本项目由 Trae IDE 辅助开发，致力于提升智慧城市公共服务智能化协作效率。*
