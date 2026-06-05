# FM3-Task29 SSE 事件解析 + agentStore 更新 + 状态接收

## 任务概述
将 `sessionStore.connectAgentStream` 中的内嵌 EventSource 替换为 `useSSE` composable，注入 3 个回调完成 agentStore 更新、completed 状态、错误聚合。

## 里程碑
FM3：论文分析与对比页面完成（v0.3）

## 涉及模块
- `stores/sessionStore.ts`（修改）
- `composables/useSSE.ts`（task28 已建）
- `stores/agentStore.ts`（task27 已扩展）

## 文件变更
| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `Veritas/frontend/src/stores/sessionStore.ts` | connectAgentStream 改用 useSSE + 注入回调 |

## 功能要求
1. **FR-001** connectAgentStream 内部 useSSE；onAgentUpdate 调 agentStore.bulkSetStates；onCompleted → disconnectSSE + completed
2. **FR-002** sessionStore 不再 new EventSource
3. **FR-003** 错误聚合：5 次后一次性 ElMessage.error，不刷屏
4. **FR-004** 保留 connectAgentStream/disconnectSSE 签名
5. **FR-005** cleanup 静默

## 跨系统一致性
- SSE payload camelCase；agentStore 同步 camelCase

## 验收标准
- [ ] sessionStore 通过 useSSE 接入
- [ ] agent_state_update 正确更新 agentStore
- [ ] 5 次重连失败后 ElMessage.error 仅 1 次

## 验证命令
```bash
cd Veritas/frontend && npx vue-tsc --noEmit
cd Veritas/frontend && npx vitest run src/__tests__/stores/sessionStore.spec.ts
```
