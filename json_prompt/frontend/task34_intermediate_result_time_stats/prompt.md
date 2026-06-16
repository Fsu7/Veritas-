# IntermediateResult中间结果组件 + TimeStats耗时统计组件

## 任务概述
创建IntermediateResult.vue（el-timeline时间线展示各Agent产出摘要）和TimeStats.vue（ECharts Bar柱状图展示各Agent执行耗时）两个组件。

## 里程碑
FM4：综述生成与Agent可视化完成（Day 3）

## 涉及模块
- F1.5 Agent可视化模块

## 文件变更
| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | Veritas/frontend/src/components/agent/IntermediateResult.vue | 中间结果时间线组件 |
| 新增 | Veritas/frontend/src/components/agent/TimeStats.vue | 耗时统计柱状图组件 |

## 功能要求

### FR-001 [P0] IntermediateResult时间线
el-timeline展示各Agent产出摘要：时间戳+Agent名+摘要文本。仅展示completed/running的Agent。

### FR-002 [P1] 自动滚动
新Agent完成时自动滚动到最新节点。

### FR-003 [P1] 空状态
无中间结果时显示'等待Agent产出结果'。

### FR-004 [P0] TimeStats柱状图
ECharts Bar展示各Agent耗时，X轴Agent名，Y轴耗时(秒)，颜色与状态色一致。

### FR-005 [P1] 条件展示
分析中显示部分结果，完成后显示完整柱状图。

### FR-006 [P0] resize自适应+卸载清理
resize时ECharts自适应，卸载dispose实例。

## 验收标准
- [ ] 时间线正确展示中间结果
- [ ] 自动滚动到底部
- [ ] 空状态提示友好
- [ ] 柱状图正确展示耗时
- [ ] ECharts Bar按需导入
- [ ] 卸载无内存泄漏
