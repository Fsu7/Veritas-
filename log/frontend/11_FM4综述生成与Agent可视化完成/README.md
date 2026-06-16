# FM4 综述生成与 Agent 可视化完成

## 功能描述

- **解决了什么问题**：FM3 仅实现了综述生成的基础展示（Markdown 渲染 + 引用链接），缺少 Agent 协同过程的实时可视化和报告导出能力。FM4 补齐了 ECharts 流程图、状态面板、中间结果时间线、耗时统计等 Agent 可视化核心组件，以及 PDF/Word 导出、引用溯源弹窗、论文筛选排序等完整功能。
- **实现了什么功能**：
  - 4 个 Agent 可视化子组件（FlowChart / StatusPanel / IntermediateResult / TimeStats）
  - SSE 通用 composable（useSSE），与 sessionStore 解耦
  - 2 个报告增强组件（ExportPanel / CitationLink）
  - 4 个通用组件（FilterPanel / SortDropdown / SearchInput / LoadingOverlay）
  - AgentFlowView / SearchView / ReportView 三大页面重构集成
  - types / stores / api / utils 增强
- **业务价值**：Agent 协同可视化是课题核心差异化能力，也是答辩演示的核心亮点。报告导出和引用溯源使综述从展示变为可交付的成果。

## 实现逻辑

### 核心文件列表（全部已完成）

| 阶段 | 新建/修改 | 文件 |
|------|----------|------|
| Stage 1 | 新建 | `composables/useSSE.ts` |
| Stage 1 | 新建 | `__tests__/composables/useSSE.spec.ts` (13 tests) |
| Stage 1 | 修改 | `types/agent.ts`（新增 SSEEventType / SSEEvent） |
| Stage 2 | 新建 | `components/agent/AgentFlowChart.vue` |
| Stage 2 | 新建 | `components/agent/AgentStatusPanel.vue` |
| Stage 2 | 新建 | `components/agent/IntermediateResult.vue` |
| Stage 2 | 新建 | `components/agent/TimeStats.vue` |
| Stage 2 | 新建 | 4 个 agent 组件测试文件（30 tests） |
| Stage 3 | 修改 | `views/AgentFlowView.vue`（重构：使用 useSSE + 4 子组件） |
| Stage 3 | 新建 | `__tests__/views/AgentFlowView.spec.ts` (4 tests) |
| Stage 4 | 新建 | `components/report/ExportPanel.vue` |
| Stage 4 | 新建 | `components/report/CitationLink.vue` |
| Stage 4 | 新建 | `__tests__/components/report/ExportPanel.spec.ts` (6 tests) |
| Stage 4 | 新建 | `__tests__/components/report/CitationLink.spec.ts` (7 tests) |
| Stage 4 | 修改 | `api/analysis.ts`（新增 exportPdf / exportWord） |
| Stage 4 | 修改 | `api/index.ts`（blob 响应旁路） |
| Stage 4 | 修改 | `utils/citation.ts`（新增 extractCitationData） |
| Stage 4 | 修改 | `__tests__/utils/citation.spec.ts`（追加 5 tests） |
| Stage 5 | 新建 | `components/common/FilterPanel.vue` |
| Stage 5 | 新建 | `components/common/SortDropdown.vue` |
| Stage 5 | 新建 | `components/common/SearchInput.vue` |
| Stage 5 | 新建 | `components/common/LoadingOverlay.vue` |
| Stage 5 | 新建 | 4 个 common 组件测试文件（14 tests） |
| Stage 5 | 修改 | `types/paper.ts`（增强 FilterParams + 新增 SortParams） |
| Stage 5 | 修改 | `stores/paperStore.ts`（新增 sortBy + searchPapers(sort?)） |
| Stage 5 | 修改 | `api/paper.ts`（search 增加 sort_by/sort_order） |
| Stage 6 | 修改 | `views/SearchView.vue`（集成 FilterPanel + SortDropdown + SearchInput） |
| Stage 6 | 修改 | `views/ReportView.vue`（集成 ExportPanel + CitationLink） |
| Stage 7 | 新建 | `__tests__/integration/fm4-acceptance.spec.ts` (15 验收检查点) |

### 架构设计

- **useSSE 与 sessionStore 解耦**：新建 `useSSE` composable 供 AgentFlowView 独立使用，sessionStore 的 `connectAgentStream` 保留作为旧 API 向后兼容
- **ECharts 按需导入**：每个图表组件独立注册所需的 chart/component/renderer，避免全量打包
- **Blob 响应旁路**：`api/index.ts` 拦截器检测 `responseType === 'blob'` 时跳过 JSON 转换和 code 校验
- **Props Down / Events Up**：所有子组件通过 Props 接收数据，通过 Emits 通知父组件
- **markRaw 优化**：ECharts 实例使用 `markRaw()` 包裹，避免 Vue 响应式 overhead

## 测试结果

| 测试套件 | 测试数 | 结果 |
|---------|--------|------|
| useSSE composable | 13 | ✅ 通过 |
| Agent 4 子组件 | 30 | ✅ 通过 |
| AgentFlowView | 4 | ✅ 通过 |
| ExportPanel + CitationLink | 13 | ✅ 通过 |
| citation 工具函数 (extractCitationData) | 5 | ✅ 通过 |
| FilterPanel + SortDropdown + SearchInput + LoadingOverlay | 14 | ✅ 通过 |
| 既有 views 测试 (SearchView / HomeView) | 12 | ✅ 通过 |
| fm4-acceptance 验收测试 | 15 | ✅ 通过 |
| **总计** | **~100+** | **全部通过** |

## 相关文件

### 新增文件（21 个）
- `src/composables/useSSE.ts`
- `src/components/agent/AgentFlowChart.vue`
- `src/components/agent/AgentStatusPanel.vue`
- `src/components/agent/IntermediateResult.vue`
- `src/components/agent/TimeStats.vue`
- `src/components/report/ExportPanel.vue`
- `src/components/report/CitationLink.vue`
- `src/components/common/FilterPanel.vue`
- `src/components/common/SortDropdown.vue`
- `src/components/common/SearchInput.vue`
- `src/components/common/LoadingOverlay.vue`
- `src/__tests__/composables/useSSE.spec.ts`
- `src/__tests__/components/agent/AgentFlowChart.spec.ts`
- `src/__tests__/components/agent/AgentStatusPanel.spec.ts`
- `src/__tests__/components/agent/IntermediateResult.spec.ts`
- `src/__tests__/components/agent/TimeStats.spec.ts`
- `src/__tests__/components/report/ExportPanel.spec.ts`
- `src/__tests__/components/report/CitationLink.spec.ts`
- `src/__tests__/components/common/FilterPanel.spec.ts`
- `src/__tests__/components/common/SortDropdown.spec.ts`
- `src/__tests__/components/common/SearchInput.spec.ts`
- `src/__tests__/components/common/LoadingOverlay.spec.ts`
- `src/__tests__/views/AgentFlowView.spec.ts`
- `src/__tests__/integration/fm4-acceptance.spec.ts`

### 修改文件（9 个）
- `src/views/AgentFlowView.vue` — 重构：移除内联 ECharts/SSE/Drawer，改用 useSSE + 4 子组件组合
- `src/views/SearchView.vue` — 集成 FilterPanel + SortDropdown + SearchInput
- `src/views/ReportView.vue` — 集成 ExportPanel + CitationLink
- `src/types/agent.ts` — 新增 SSEEventType / SSEEvent
- `src/types/paper.ts` — 增强 FilterParams（conferences 多选）+ 新增 SortParams
- `src/stores/paperStore.ts` — 新增 sortBy + searchPapers 支持 sort 参数
- `src/api/analysis.ts` — 新增 exportPdf / exportWord（Blob 下载）
- `src/api/paper.ts` — search 增加 sort_by / sort_order
- `src/api/index.ts` — 响应拦截器增加 blob 响应旁路
- `src/utils/citation.ts` — 新增 extractCitationData 函数
