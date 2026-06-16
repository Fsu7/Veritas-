# AgentFlowChart组件 — ECharts Graph流程图拆分与增强

## 任务概述
从AgentFlowView.vue中拆分出独立AgentFlowChart.vue组件，使用ECharts Graph展示6-Agent工作流节点与连线，实现状态颜色实时变化、running节点脉冲动画、tooltip详情展示、resize自适应、点击节点emit事件。

## 里程碑
FM4：综述生成与Agent可视化完成（Day 1）

## 涉及模块
- F1.5 Agent可视化模块

## 文件变更
| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | Veritas/frontend/src/components/agent/AgentFlowChart.vue | ECharts Graph流程图组件 |
| 修改 | Veritas/frontend/src/views/AgentFlowView.vue | 拆分重构，使用AgentFlowChart子组件 |

## 功能要求

### FR-001 [P0] 6-Agent工作流流程图
ECharts Graph展示6个Agent节点：协调者→检索员→分析员→对比员→生成员→审核员，含5条连线和1条条件分支(分析员→对比员/分析员→生成员)。节点使用固定坐标布局。

### FR-002 [P0] 状态颜色实时变化
根据agentStore.agentStates动态设置节点颜色：waiting(#C0C4CC灰)/running(#409EFF蓝)/completed(#67C23A绿)/failed(#F56C6C红)。watch监听agentStates调用setOption更新。

### FR-003 [P1] running节点脉冲动画
running状态节点添加脉冲/呼吸动画效果，区分于静态节点。

### FR-004 [P1] tooltip详情展示
hover节点显示tooltip：Agent名称、当前状态、进度百分比、已耗时、中间结果摘要。

### FR-005 [P0] resize自适应
监听window resize + ResizeObserver，调用ECharts resize()。

### FR-006 [P0] 点击节点emit事件
点击节点emit node-click事件，传递agentName。

### FR-007 [P0] 组件卸载清理
onUnmounted中dispose ECharts实例，移除resize监听。

## 关键约束
- ECharts按需导入（Graph/Tooltip/EffectScatter），禁止全量导入
- 组件只通过Props接收agentStates，不直接调用API
- 状态传达必须配合文字+图标，不仅靠颜色
- 组件卸载必须销毁ECharts实例和resize监听

## 验收标准
- [ ] 流程图正确展示6节点+5连线+条件分支
- [ ] 状态颜色随SSE实时变化
- [ ] running节点有脉冲动画
- [ ] hover显示tooltip详情
- [ ] resize自适应
- [ ] 点击节点触发node-click事件
- [ ] 组件卸载无内存泄漏
- [ ] ECharts按需导入
- [ ] AgentFlowView成功拆分使用子组件
