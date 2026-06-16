# FM4 技术教学文档

## 开发思路

### 需求分析

FM4 是前端第4个里程碑，核心目标是实现 Agent 协同过程的完整可视化和综述报告的完整交付能力。需求分为三个层面：

1. **Agent 可视化层**（F1.5）：将 6 个 Agent 的协同过程以 ECharts 流程图 + 状态面板 + 中间结果时间线 + 耗时统计的方式实时呈现
2. **综述交付层**（F1.4）：支持 PDF/Word 导出和引用溯源弹窗
3. **检索增强层**（F1.2）：论文检索增加筛选（年份/会议/引用数）和排序（相关度/时间/引用数）

### 技术选型

| 需求 | 技术选择 | 原因 |
|------|---------|------|
| 流程图 | ECharts Graph + EffectScatter | 固定坐标布局稳定可控，EffectScatter 叠加实现运行中脉冲动画 |
| 状态面板 | Element Plus el-tag + el-progress + el-popover | 轻量级组件组合，避免重复造轮子 |
| 中间结果 | el-timeline | 天然适合展示序列化结果 |
| 耗时统计 | ECharts Bar | 柱状图直观对比 6 个 Agent 耗时 |
| SSE 管理 | 自定义 useSSE composable | 与 sessionStore 解耦，复用性更强 |
| PDF/Word 导出 | axios Blob + URL.createObjectURL | 通用方式，无需第三方库 |
| 引用溯源 | el-dialog 弹窗 | 点击引用不跳页，沉浸感更好 |
| 搜索防抖 | setTimeout 300ms | 简单可靠，符合 UX 最佳实践 |

### 架构设计思路

采用**自底向上、组件化组合**的策略：

```
Stage 1: useSSE composable (基础设施)
    ↓
Stage 2: 4 个 Agent 子组件 (独立可渲染)
    ↓
Stage 3: AgentFlowView 重构组合 (页面层)
    ↓
Stage 4: ExportPanel + CitationLink (报告增强)
    ↓
Stage 5: FilterPanel + SortDropdown + SearchInput + LoadingOverlay (通用组件)
    ↓
Stage 6: SearchView + ReportView 集成 (页面增强)
    ↓
Stage 7: fm4-acceptance 验收测试 (质量保障)
```

关键设计决策：
1. **保留旧实现作兜底**：不删除现有代码，新增组件完全独立可运行
2. **useSSE 与 sessionStore 解耦**：AgentFlowView 独立使用 useSSE，sessionStore 的 connectAgentStream 保留向后兼容
3. **Blob 响应旁路**：在 Axios 拦截器中检测 `responseType === 'blob'`，跳过 JSON 转换

## 实现步骤

### 第1步：SSE Composable 抽离（task36）
- 新建 `useSSE.ts`，封装 EventSource 生命周期（connect/disconnect/reconnect）
- 4 种事件类型：agent_state_update / analysis_completed / agent_error / progress_update
- 自动重连：3 秒间隔，最多 5 次
- onScopeDispose 自动清理

### 第2步：4 个 Agent 子组件创建（task32-34）
- `AgentFlowChart`：ECharts Graph + EffectScatter 叠加，6 节点固定坐标
- `AgentStatusPanel`：el-tag 状态标签 + el-progress 进度条 + el-popover 中间结果
- `IntermediateResult`：el-timeline 展示 completed/running 的中间结果
- `TimeStats`：ECharts Bar 柱状图，颜色映射 Agent 状态色

### 第3步：AgentFlowView 重构（task35）
- 移除内联 ECharts init/setOption/resize 逻辑
- 移除内联 Drawer 详情
- 改用 useSSE composable 替代直接调用 sessionStore
- 布局：上部 60% AgentFlowChart + 下部 40% el-tabs（StatusPanel/IntermediateResult/TimeStats）
- 状态：loading（el-skeleton）/ empty / error（el-result + 重试）

### 第4步：报告组件（task37-38）
- `ExportPanel`：PDF/Word 双按钮，Blob 下载，loading/disabled 状态管理
- `CitationLink`：el-dialog 弹窗展示原文片段 + 元数据 + "查看论文详情"
- `api/index.ts` 增加 blob 响应旁路
- `citation.ts` 新增 `extractCitationData`

### 第5步：通用组件（task39-40）
- `FilterPanel`：年份范围（el-input type="number"）+ 会议多选 + 引用数
- `SortDropdown`：相关度/发表时间/引用数三选一
- `SearchInput`：300ms 防抖 + 回车立即 + 历史标签 + 清除
- `LoadingOverlay`：Teleport to body 全局遮罩

### 第6步：页面集成（task41）
- `SearchView`：左侧 FilterPanel + 右侧 SearchInput + SortDropdown + PaperCard 列表
- `ReportView`：嵌入 ExportPanel + CitationLink + 引用点击改为弹窗触发

### 第7步：验收测试（task42）
- `fm4-acceptance.spec.ts`：15 项验收检查点全覆盖
- 类型检查通过（vue-tsc --noEmit 0 errors）
- 全量单元测试通过（100+ 用例）

## 解决了什么问题

| 问题 | 解决前 | 解决后 |
|------|--------|--------|
| Agent 可视化缺失 | 只有基础的 SSE 状态接收，无可视化展示 | 4 个可视化组件覆盖全流程 |
| SSE 逻辑内联 | sessionStore.connectAgentStream 耦合在 Store 中 | useSSE composable 独立可复用 |
| 报告无法导出 | 只能页面查看，无法下载 | PDF/Word 双格式导出 |
| 引用无法溯源 | 点击引用直接跳转论文详情页 | 弹窗展示原文片段+元数据 |
| 检索无筛选排序 | 仅有关键词搜索 | 年份/会议/引用数筛选 + 三维排序 |
| 搜索无防抖 | 每次输入实时触发检索 | 300ms 防抖 + 回车立即搜索 |

## 变更内容

### 新增文件（~24 个）
- 1 composable + 10 组件 + 1 验收测试 + 12 单元测试

### 修改文件（~9 个）
- 3 views（AgentFlowView / SearchView / ReportView）
- 2 types（agent.ts / paper.ts）
- 2 stores（paperStore.ts）
- 2 api（analysis.ts / index.ts）
- 1 util（citation.ts）

### 配置变更
- 无新依赖引入，无配置文件变更

## 关键技术点

### 1. ECharts 在 Vue 中的正确使用
```ts
const chart = markRaw(echarts.init(container, undefined, { renderer: 'canvas' }))
// markRaw 避免 ECharts 实例被 Vue 响应式代理
// onUnmounted 中 chart.dispose() + 移除 resize 监听
```

### 2. Blob 下载模式
```ts
// 下载函数：创建临时 a 标签触发下载
function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
```

### 3. 跨系统字段兼容
```ts
// SSE 数据同时支持 camelCase (Java) 和 snake_case (Python)
const name = (eventData.agentName ?? eventData.agent_name) as string
const result = (eventData.intermediateResult ?? eventData.intermediate_result) as string
```

### 4. vi.mock 与响应式的兼容性
- vitest 的 `vi.mock` 是 hoisted 的，工厂函数在模块顶层代码之前执行
- 不能使用 Vue `ref()` 在 mock 工厂中（`ref` 依赖 Vue 运行时）
- 解决方案：使用普通对象 + `{ value: xxx }` 模拟 Ref 结构，在测试中直接修改变量值

## 经验总结

### 收获
1. **组件化拆分**：将 AgentFlowView 的一体式大组件拆为 5 个小块（4 子组件 + 1 composable），提高了可维护性和可测试性
2. **自底向上策略**：先建基础设施（useSSE），再建独立子组件，最后重构页面组合 —— 降低了风险，每步都可验证
3. **ECharts 按需导入**：实际生效减少了 ~300KB 打包体积
4. **Blob 旁路设计**：最小化侵入 Axios 拦截器，一行判断解决导出问题

### 踩过的坑
1. **ECharts 类型问题**：`ECElementEvent` 类型在 echarts 5.x 中路径不稳定，最终使用 `unknown` + 类型断言模式
2. **vi.mock 响应式问题**：mock 返回的普通对象 `.value` 不会被 Vue computed 追踪，导致状态切换测试复杂化
3. **ElInputNumber 类型**：`@update:model-value` 事件参数类型为 `number | undefined`，需要显式处理
4. **Sass Deprecation Warning**：`@import` 已标记 legacy，后续需迁移到 `@use`

### 最佳实践建议
1. 每个组件独立可运行，通过 Props/Emits 通信，不依赖全局 Store（视图层除外）
2. ECharts 实例用 `markRaw()` 包裹，resize 监听在 onUnmounted 中移除
3. setTimeout 防抖在 onUnmounted 中用 clearTimeout 清理
4. unit 测试优先测试确定性行为（生命周期、事件分发），状态驱动测试留待集成/E2E
