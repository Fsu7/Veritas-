# FM3-Task27 agentStore 完整实现

## 任务概述
完善 `stores/agentStore.ts`（FM1 已部分实现）：新增 6 Agent 初始化、批量更新、错误聚合、durationMs 累加、扩展派生；同步扩展 `types/agent.ts` 联合类型与常量。

## 里程碑
FM3：论文分析与对比页面完成（v0.3）

## 涉及模块
- `stores/agentStore.ts`（修改）
- `types/agent.ts`（修改：AGENT_NAMES / AgentName / AgentStatus / DEFAULT_AGENT_STATE）

## 文件变更
| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `Veritas/frontend/src/stores/agentStore.ts` | initStates/bulkSetStates/errors/派生/resetStates 完善 |
| 修改 | `Veritas/frontend/src/types/agent.ts` | 联合类型与常量 |

## 功能要求
1. **FR-001** types/agent.ts：AGENT_NAMES 6 个 + AgentName 联合 + AgentStatus 联合 + DEFAULT_AGENT_STATE
2. **FR-002** initStates(analysisId)：写入 6 个 waiting 状态
3. **FR-003** bulkSetStates：批量更新 + 错误聚合 + durationMs 累加
4. **FR-004** 派生：completedCount/failedCount/getCompletedAgents/getFailedAgents/totalDurationMs
5. **FR-005** resetStates 完善：所有 ref 归零
6. **FR-006** 向后兼容：updateAgentState 内部走 bulkSetStates

## 跨系统一致性
- `agentName` ↔ `agent_name`、`intermediateResult` ↔ `intermediate_result`、`durationMs` ↔ `duration_ms`

## 验收标准
- [ ] AgentName 联合类型 6 个值
- [ ] initStates 写入 6 个 waiting
- [ ] bulkSetStates 错误聚合 + durationMs 累加
- [ ] updateAgentState 向后兼容

## 验证命令
```bash
cd Veritas/frontend && npx vue-tsc --noEmit
cd Veritas/frontend && npx vitest run src/__tests__/stores/agentStore.spec.ts
```
