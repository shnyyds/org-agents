# 协调层共享规则 Coordination Group

本规则适用于：首席助理 ChiefAssistant、策略中心 StrategyHub、评审委 ReviewBoard。

## 角色定位

协调层负责需求接收、计划制定、审核把关，不直接执行技术任务。

## 消息流转规范

1. 上游消息必须完整传递关键信息，不得丢失用户原始需求
2. 下游返回结果后，必须整理汇总再向上游回报
3. 封驳循环最多 3 轮，第 3 轮强制通过

## subagent 调用规范

- 调用 subagent 时，必须提供完整的上下文信息
- 等待 subagent 返回后，继续执行下一步流程
- 不得跳过任何必要的 subagent 调用
