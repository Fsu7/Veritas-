# useSSE composable抽取 — SSE逻辑独立化 + 事件解析增强

## 任务概述
将sessionStore中SSE逻辑抽取为独立useSSE.ts composable，封装connect/disconnect/reconnect，支持4种事件类型，自动重连(3s间隔最多5次)，组件卸载自动断开。

## 里程碑
FM4：综述生成与Agent可视化完成（Day 5）

## 涉及模块
- F1.5 Agent可视化模块

## 文件变更
| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | Veritas/frontend/src/composables/useSSE.ts | SSE composable |
| 修改 | Veritas/frontend/src/stores/sessionStore.ts | SSE逻辑迁移至useSSE |
| 修改 | Veritas/frontend/src/views/AgentFlowView.vue | 适配useSSE |

## 功能要求

### FR-001 [P0] connect(url)
创建EventSource连接，URL含?token=JWT鉴权。

### FR-002 [P0] disconnect()
关闭连接，清除定时器，重置状态。

### FR-003 [P0] 4种SSE事件解析
agent_state_update/analysis_completed/agent_error/progress_update。

### FR-004 [P0] 自动重连
3s间隔，最多5次，超过放弃。

### FR-005 [P0] 组件卸载自动断开
onScopeDispose确保无幽灵连接。

### FR-006 [P0] sessionStore迁移
使用useSSE替代内联EventSource，外部接口不变。

### FR-007 [P1] onEvent回调可配置
允许调用方自定义事件处理逻辑。

## 验收标准
- [ ] useSSE可独立使用
- [ ] 4种事件正确解析
- [ ] 自动重连3s/5次
- [ ] 卸载无幽灵连接
- [ ] sessionStore功能不变
- [ ] onEvent回调可配置
