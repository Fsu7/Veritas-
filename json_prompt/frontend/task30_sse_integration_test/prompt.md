# FM3-Task30 SSE 联调 + 综述生成完整流程 + Bug 修复

## 任务概述
扩展 `__tests__/integration/fullChain.spec.ts` 联调测试：mock EventSource 模拟 SSE 推送，覆盖正常/降级/重试 3 场景，修复 SSE 迁移到 useSSE 后的 4 个回归 Bug。

## 里程碑
FM3：论文分析与对比页面完成（v0.3）

## 涉及模块
- `__tests__/integration/fullChain.spec.ts`（修改）
- `composables/useSSE.ts`、`stores/sessionStore.ts`、`stores/agentStore.ts`（bug 修复）

## 文件变更
| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `Veritas/frontend/src/__tests__/integration/fullChain.spec.ts` | 扩展 3 场景 + bug 修复用例 |
| 修改 | `Veritas/frontend/src/stores/sessionStore.ts` | bug 修复（按需） |
| 修改 | `Veritas/frontend/src/composables/useSSE.ts` | bug 修复（按需） |

## 功能要求
1. **FR-001** mock EventSource：可手动 trigger 事件
2. **FR-002** 场景 1 正常流：6 Agent agent_state_update → completed
3. **FR-003** 场景 2 降级：generator failed → degraded
4. **FR-004** 场景 3 重试：5 次 onerror → 再 connect → completed
5. **FR-005** Bug 修复：cleanup disconnect / 重复 initStates / ReportView 卸载 / useSSE null analysisId
6. **FR-006** 测试隔离

## 跨系统一致性
- SSE JSON camelCase；AgentName/AgentStatus 与后端一致

## 验收标准
- [ ] 3 场景全部通过
- [ ] 4 个 Bug 全部修复 + 测试覆盖
- [ ] 测试隔离正确
- [ ] `npx vitest run` 全通过

## 验证命令
```bash
cd Veritas/frontend && npx vue-tsc --noEmit
cd Veritas/frontend && npx vitest run src/__tests__/integration/fullChain.spec.ts
cd Veritas/frontend && npx vitest run
```
