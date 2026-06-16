# AgentFlowView页面重构 — 组合4个子组件 + SSE联调

## 任务概述
重构AgentFlowView.vue，组合AgentFlowChart+AgentStatusPanel+IntermediateResult+TimeStats四个子组件，实现SSE→agentStore→ECharts更新联调，上部流程图(60%)+下部面板(40%)布局，loading/empty/error状态完整。

## 里程碑
FM4：综述生成与Agent可视化完成（Day 4）

## 涉及模块
- F1.5 Agent可视化模块

## 文件变更
| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | Veritas/frontend/src/views/AgentFlowView.vue | 重构：移除内联逻辑，改用4个子组件 |

## 功能要求

### FR-001 [P0] 页面布局
上部AgentFlowChart(60%)+下部AgentStatusPanel+IntermediateResult+TimeStats(40%)。

### FR-002 [P0] SSE连接管理
sessionStore.connectAgentStream → agentStore.updateAgentState → 子组件Props更新。

### FR-003 [P0] 组件卸载清理
onUnmounted断开SSE+重置agentStore。

### FR-004 [P0] Loading状态
骨架屏/v-loading+'正在连接Agent服务...'。

### FR-005 [P1] Empty状态
无数据时显示'等待开始分析'。

### FR-006 [P1] Error状态
连接失败ElMessage.error+重试按钮。

### FR-007 [P2] 节点点击联动
流程图节点点击→状态面板高亮+中间结果滚动。

## 验收标准
- [ ] 4个子组件正确组合
- [ ] SSE实时更新
- [ ] 卸载无内存泄漏
- [ ] Loading/Empty/Error状态完整
- [ ] 节点点击联动
