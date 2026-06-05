# FM3-Task28 useSSE 组合函数（连接/断开/重连）

## 任务概述
实现 `composables/useSSE.ts` 全新组合函数，封装 EventSource 完整生命周期：连接/断开/重连/自动清理，6 Agent SSE 事件分发。同步在 `types/agent.ts` 新增 `AgentStateUpdate` 事件 payload 类型。

## 里程碑
FM3：论文分析与对比页面完成（v0.3）

## 涉及模块
- `composables/useSSE.ts`（新增）
- `types/agent.ts`（新增 AgentStateUpdate）
- `api/analysis.ts`（getAgentStreamUrl）

## 文件变更
| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | `Veritas/frontend/src/composables/useSSE.ts` | SSE composable |
| 修改 | `Veritas/frontend/src/types/agent.ts` | AgentStateUpdate 类型 |

## 功能要求
1. **FR-001** options: analysisId Ref + 3 回调 + autoConnect + reconnectInterval + maxReconnect
2. **FR-002** 返回 3 ref + 3 方法
3. **FR-003** connect：EventSource 生命周期 + 事件监听 + onerror 重连
4. **FR-004** disconnect：关闭 + 重置 attempts
5. **FR-005** onUnmounted/onScopeDispose 自动 disconnect；autoConnect=true 时 onMounted connect
6. **FR-006** AgentStateUpdate 类型 6 字段

## 跨系统一致性
- SSE JSON 字段 camelCase（前端 Axios 拦截器已转换或后端直接出 camelCase）
- `agentName` ↔ `agent_name`、`durationMs` ↔ `duration_ms`

## 验收标准
- [ ] connect/disconnect 行为正确
- [ ] 重连 3s 间隔、最多 5 次
- [ ] 组件卸载时 disconnect
- [ ] AgentStateUpdate 类型 6 字段

## 验证命令
```bash
cd Veritas/frontend && npx vue-tsc --noEmit
cd Veritas/frontend && npx vitest run src/__tests__/composables/useSSE.spec.ts
```
