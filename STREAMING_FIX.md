# 流式输出修复说明

## 问题诊断

之前的系统虽然使用了 SSE (Server-Sent Events) 进行流式传输，但存在以下问题：

1. **后端问题**：部分节点使用 `llm.ainvoke()` 而不是 `stream_llm_text()`，导致等待完整响应
2. **前端问题**：接收到流式数据后，直接将 `content` 和 `targetContent` 设置为相同值，导致 `isAnimating: false`，没有触发打字机动画

## 修复方案

### 后端修复（已完成）

将所有使用 `llm.ainvoke()` 的节点改为使用 `stream_llm_text()`：

**修改的文件：**
- `backend/app/ceo.py` - CEO 总智能体的 `analyze_intent_node`
- `backend/app/departments/market/agent.py` - 市场部的 `market_lead_plan_node`
- `backend/app/departments/tech/agent.py` - 技术部的 `tech_lead_plan_node`
- `backend/app/departments/sales/agent.py` - 销售部的 `sales_lead_plan_node`
- `backend/app/departments/repair/agent.py` - 维修部的 `repair_lead_plan_node`
- `backend/app/departments/cs/agent.py` - 客服部的 `cs_lead_plan_node`
- `backend/app/departments/user/agent.py` - 用户管理的 `user_lead_plan_node`

**修改示例：**
```python
# 之前
response = await self.llm.ainvoke(messages)
content = response.content.strip()

# 之后
response_text = await stream_llm_text(
    llm=self.llm,
    prompt=messages,
    state=state,
    node_name="market_lead_plan",
    active_agent="市场部部长",
)
content = response_text.strip()
```

### 前端修复（已完成）

修改 `frontend/src/App.jsx` 中的流式数据处理逻辑：

**修改位置：** 第 1408-1443 行

**关键改动：**
```javascript
// 之前：直接更新 content 和 targetContent 为相同值
content: (lastMessage.content || '') + data.content,
targetContent: (lastMessage.targetContent || '') + data.content,
isAnimating: false,

// 之后：只更新 targetContent，让 content 通过动画追上
targetContent: (lastMessage.targetContent || '') + data.content,
isAnimating: true,
// content 保持不变，由 useEffect 定时器逐步更新
```

## 工作原理

### 后端流式输出流程

```
用户查询
  ↓
FastAPI /chat/stream 端点
  ↓
LangGraph astream_events 监听
  ↓
各节点调用 stream_llm_text()
  ↓
llm.astream() 逐块生成内容
  ↓
每个 chunk 通过 stream_writer 发送 SSE
  ↓
前端接收 SSE 事件
```

### 前端打字机动画流程

```
接收 SSE 'stream' 事件
  ↓
更新 targetContent += data.content
设置 isAnimating = true
  ↓
useEffect 定时器（每 24ms）
  ↓
逐步增加 content 长度
  ↓
content 追上 targetContent 时
设置 isAnimating = false
```

## 测试方法

1. 启动后端：
```bash
cd backend
python app/main.py
```

2. 启动前端：
```bash
cd frontend
npm run dev
```

3. 在浏览器中打开前端，发送一个查询，观察：
   - 每个智能体的输出应该像打字机一样逐字显示
   - 不应该出现"等待完整响应后一次性显示"的情况
   - 流式输出应该是平滑的，没有明显的卡顿

## 技术细节

### stream_llm_text 函数

位置：`backend/app/utils/streaming.py`

核心功能：
- 使用 `llm.astream()` 进行流式调用
- 通过 `stream_writer` 实时发送每个 chunk
- 支持 prefix 和 suffix
- 返回完整的文本内容

### 前端动画参数

位置：`frontend/src/App.jsx` 第 1275-1314 行

- **定时器间隔**：24ms（约 42 FPS）
- **步长计算**：`Math.max(1, Math.ceil((targetContent.length - content.length) / 18))`
- **自适应速度**：内容越长，步长越大，确保动画不会太慢

## 注意事项

1. **后端必须使用 stream_llm_text**：所有需要流式输出的节点都必须使用这个函数
2. **前端动画性能**：定时器每 24ms 执行一次，在大量消息时可能影响性能
3. **网络延迟**：SSE 传输受网络影响，可能出现延迟或丢包
4. **浏览器兼容性**：SSE 在所有现代浏览器中都支持，但 IE 不支持

## 未来优化建议

1. **使用 WebSocket**：替代 SSE，支持双向通信和更好的错误处理
2. **动画优化**：使用 requestAnimationFrame 替代 setInterval
3. **批量更新**：合并多个小 chunk，减少状态更新频率
4. **断点续传**：支持网络中断后恢复流式传输
