# FM4 实施计划 — 综述生成与 Agent 可视化

> **项目**：XH-202630 科研文献智能助手
> **里程碑**：FM4（综述生成 + Agent 可视化）
> **范围**：task32-42（11 个 JSON prompt）
> **策略**：保留旧实现作兜底 → 并行创建子组件 → 统一重构 → 验收测试

---

## 1. 执行摘要

按依赖关系自底向上实施，共 5 个阶段、11 个任务。**不删除现有任何代码**，新增组件完全独立可运行。task35 重构时同步切换 AgentFlowView，task41 重构时同步切换 SearchView/ReportView。

### 阶段概览

| 阶段 | 任务 | 性质 | 关键产出 |
|------|------|------|---------|
| **Stage 1 基础设施** | task36 | 新建 composable | `composables/useSSE.ts` |
| **Stage 2 Agent 子组件** | task32, task33, task34 | 新建 4 个组件 | `components/agent/{AgentFlowChart,AgentStatusPanel,IntermediateResult,TimeStats}.vue` |
| **Stage 3 Agent 页面重构** | task35 | 重构 View | `views/AgentFlowView.vue` 切换为组合 |
| **Stage 4 报告组件** | task37, task38 | 新建 2 个组件 + 增强 citation | `components/report/{ExportPanel,CitationLink}.vue` + `utils/citation.ts` |
| **Stage 5 通用组件** | task39, task40 | 新建 4 个组件 + 增强 store/types | `components/common/{FilterPanel,SortDropdown,SearchInput,LoadingOverlay}.vue` + `stores/paperStore.ts` + `types/paper.ts` |
| **Stage 6 页面增强** | task41 | 重构 2 个 View | `views/SearchView.vue` + `views/ReportView.vue` 集成 FM4 组件 |
| **Stage 7 验收** | task42 | 集成测试 | `__tests__/integration/fm4-acceptance.spec.ts` |

---

## 2. 现状分析（Phase 1 已完成）

### 2.1 已有资产

| 文件 | 状态 | 复用策略 |
|------|------|---------|
| `types/agent.ts` | `AgentState/FlowData` 已定义 | 直接复用 |
| `types/paper.ts` | 有 `FilterParams` 但字段名/类型与 task39 不符 | task39 增强 |
| `types/analysis.ts` | `Citation` 已定义 | 直接复用 |
| `stores/agentStore.ts` | 已完整实现 | 直接复用 |
| `stores/paperStore.ts` | 有 `filters/updateFilters` | task39 增强字段 |
| `stores/sessionStore.ts` | 已内联 SSE | task36 抽取（保留旧逻辑 fallback） |
| `utils/citation.ts` | 有 `parseCitations/linkifyCitations/splitReportSegments` | task38 增强 `extractCitationData` |
| `utils/storage.ts` | 有 `getRecentSearches/saveRecentSearch/clearRecentSearches` | task40 直接复用 |
| `views/AgentFlowView.vue` | 已内联 ECharts Graph + SSE + Drawer | task35 保留 fallback 后切换 |
| `views/SearchView.vue` | 已用 `el-input` + `el-pagination` | task41 集成 SearchInput + 筛选 |
| `views/ReportView.vue` | 已用 `splitReportSegments` 渲染引用 | task41 切换为 CitationLink 弹窗 |
| `composables/useAuth.ts` | 已存在 | 模式参考 |
| `composables/usePagination.ts` | 已存在 | 直接复用 |
| `components/paper/PaperCard.vue` | 已实现 | 直接复用 |
| `api/analysis.ts` | 无 `exportPdf/exportWord` | task37 新增 |
| `api/paper.ts` | `search` 已支持 `FilterParams` | task39 调整字段映射 |
| `styles/variables.scss` | 已有 `--agent-*` 状态色 | 直接复用 |

### 2.2 关键设计决策

1. **保留 AgentFlowView 兜底**：在新组件验证通过前，AgentFlowView 保持当前内联实现可用。task35 切换时一次性整体替换为 `<AgentFlowChart>` 组合。
2. **sessionStore 渐进迁移**：task36 新建 `useSSE` composable，但 sessionStore 暂不切换。task35 切换时由 AgentFlowView 直接使用 `useSSE`，sessionStore 的 `connectAgentStream` 仍可作为旧 API 保留（向后兼容）。
3. **FilterParams 字段升级**：现有 `FilterParams.venue` 是单值字符串，task39 要求 `conferences: string[]`（多选会议）。采用扩展而非破坏：新增 `conferences` 字段（后端 API 接受 `conferences` 数组），保留 `venue` 作为兼容字段。
4. **SortParams 新类型**：task39 新增 `SortParams` 接口，paperStore 同步新增 `sortBy: SortParams` state。
5. **错误状态码规范**：`{code, message, data}` 已通过 `api/index.ts` 的 `snakeToCamel` 自动转换，前端按 camelCase 访问。
6. **测试目录结构**：vitest 已配置，新增测试文件放在 `src/__tests__/{components,composables,integration}/` 对应目录。
7. **Element Plus 按需导入**：`vitest.config.ts` 已配 `inline: ['element-plus']`，新组件用到的 el-* 标签可直接使用。
8. **vue-tsc 类型检查**：`package.json` 已配 `npm run typecheck`。

### 2.3 风险与对策

| 风险 | 对策 |
|------|------|
| ECharts 单元测试需 mock | 用 `vi.mock('echarts', ...)` 桩化 |
| sessionStore 中 `startAnalysis` 同时调用 SSE+轮询，task36 抽取 SSE 后旧逻辑不能破坏 | 保留 sessionStore 原方法，useSSE 仅供新 View 使用 |
| task39 改动 `FilterParams` 类型可能影响 paperStore 既有 API 调用方 | 改用「扩展字段」+ 后端 snake_case 透传，前端无 breaking change |
| task41 集成 4 个新组件到 SearchView，测试可能挂 | 每集成一步就单独跑 vitest |
| task42 验收测试可能需要 mock SSE/EventSource | 在 `beforeEach` 中 `vi.stubGlobal('EventSource', MockEventSource)` |

---

## 3. 详细实施计划

### Stage 1：基础设施（task36 — SSE Composable）

**目标**：抽离 SSE 通用逻辑，独立可复用。

#### 文件变更

1. **新建** `src/composables/useSSE.ts`
   - 导出 `useSSE(options?: { onEvent?: (e: SSEEvent) => void })`
   - 内部状态：`isConnected: Ref<boolean>` / `lastEvent: Ref<SSEEvent | null>` / `reconnectCount: Ref<number>` / `error: Ref<string | null>`
   - 方法：`connect(url: string)` / `disconnect()` / `reconnect()`
   - 4 种事件类型：`agent_state_update` / `analysis_completed` / `agent_error` / `progress_update`
   - 自动重连：3 秒间隔，最多 5 次
   - `onScopeDispose` 自动 disconnect

#### 新增类型（`types/agent.ts` 扩展）

```ts
export type SSEEventType = 'agent_state_update' | 'analysis_completed' | 'agent_error' | 'progress_update'

export interface SSEEvent {
  type: SSEEventType
  data: Record<string, unknown>
  timestamp: number
}
```

#### 测试

- `src/__tests__/composables/useSSE.spec.ts`
  - `connect` 建立 EventSource，`isConnected=true`
  - 4 种事件正确解析为 `SSEEvent`
  - `onerror` 触发重连（用 fake timers 验证 3s 间隔）
  - 第 6 次重连后停止
  - 组件卸载时自动 disconnect
  - 传入 `onEvent` 回调正确触发

#### 验证
- `npm run typecheck` 通过
- `npx vitest run src/__tests__/composables/useSSE.spec.ts` 全通过

---

### Stage 2：Agent 子组件（task32/33/34）

#### task32 — AgentFlowChart

**新建** `src/components/agent/AgentFlowChart.vue`

- Props: `{ agentStates: Record<string, AgentState> }`
- Emits: `{ 'node-click': [agentName: string] }`
- ECharts 按需导入：`GraphChart / TooltipComponent / EffectScatterComponent / CanvasRenderer`
- 6 节点固定坐标布局（与现有 `AgentFlowView.vue` 中 `AGENT_NODES` 一致）
- 6 条连线：coordinator→retriever、retriever→analyzer、analyzer→comparer、analyzer→generator、comparer→generator、generator→reviewer
- 状态色映射使用 `--agent-*` CSS 变量读不到（ECharts 不支持），用 hex 值映射（在源码中注释说明）
- running 状态节点：添加 `EffectScatter` 叠加层 + CSS 脉冲动画
- tooltip：formatter 返回 `名称/状态/进度/耗时/中间结果`
- resize：监听 window resize + ResizeObserver
- 卸载：`chart.dispose()` + 移除所有监听

**新建测试** `src/__tests__/components/agent/AgentFlowChart.spec.ts`
- 挂载后 6 节点渲染
- agentStates 变化时 `setOption` 被调用（mock echarts）
- 点击节点触发 `node-click` 事件
- 卸载时 `dispose` 被调用

#### task33 — AgentStatusPanel

**新建** `src/components/agent/AgentStatusPanel.vue`

- Props: `{ agentStates: Record<string, AgentState> }`
- Emits: `{ 'agent-click': [agentName: string] }`
- 6 个 Agent 标签（`el-tag` 圆角风格 + 自定义背景色 + 图标 + 文字 + 耗时）
- 中文名映射：coordinator→协调者 / retriever→检索员 / analyzer→分析员 / comparer→对比员 / generator→生成员 / reviewer→审核员
- 状态色：使用内联色（不依赖 CSS 变量，组件 scoped style 中用 hex 注释对应 `--agent-*`）
- 图标：waiting ⏳（Clock）/ running ⚙️（Loading 旋转）/ completed ✓（Check）/ failed ✗（Close）
- 状态色+图标+文字三重传达
- 响应式：lg 横排（`el-row + el-col :span="4"`）/ sm 2×3 网格（`:span="12"`）
- 点击标签：emit `agent-click` + 触发 `el-popover` 展示 `intermediateResult`
- 顶部 `el-progress` 进度条（值 = completed/6）
- 空状态：`el-empty description="等待开始分析"`

**新建测试** `src/__tests__/components/agent/AgentStatusPanel.spec.ts`
- 6 个 Agent 标签正确渲染
- agentStates 变化时标签状态文字+图标同步
- 点击标签触发 `agent-click` 事件
- 空 agentStates 时显示空状态

#### task34 — IntermediateResult + TimeStats

**新建** `src/components/agent/IntermediateResult.vue`

- Props: `{ agentStates: Record<string, AgentState> }`
- 使用 `el-timeline` 展示 `completed` / `running` 的 Agent
- 每节点：时间戳（`formatTime(durationMs)`）+ 中文名 + `intermediateResult` 摘要（超出 200 字截断）
- 新结果出现时 `nextTick + scrollTop` 自动滚动到底部
- 空状态：`el-empty description="等待Agent产出结果"`

**新建** `src/components/agent/TimeStats.vue`

- Props: `{ agentStates: Record<string, AgentState> }`
- ECharts Bar 按需导入：`BarChart / TooltipComponent / GridComponent / CanvasRenderer`
- X 轴：Agent 中文名
- Y 轴：耗时（秒）
- 柱体颜色：根据 status 动态映射
- 条件展示：全部 completed/failed 时显示完整；进行中显示部分柱 + 提示
- resize 自适应
- 卸载 dispose

**新建测试** `src/__tests__/components/agent/IntermediateResult.spec.ts`
- 展示已完成/执行中的 Agent（不展示 waiting）
- 空状态显示提示
- `intermediateResult` 超长截断

**新建测试** `src/__tests__/components/agent/TimeStats.spec.ts`
- 6 根柱渲染
- 全部完成后才完整显示（进行中显示部分）
- 卸载时 dispose

#### 验证
- `npm run typecheck` 通过
- 新建 4 个测试文件全部通过

---

### Stage 3：Agent 页面重构（task35）

**目标**：AgentFlowView 切换为组合子组件，使用 useSSE 替代内联 EventSource。

**修改** `src/views/AgentFlowView.vue`

- 移除内联 ECharts init / setOption / resize 逻辑
- 移除内联 `connectAgentStream` 调用 `sessionStore` 的方式，改为调用 `useSSE`
- 布局：上部 60% `<AgentFlowChart>` + 下部 40% `el-tabs` 切换 `<AgentStatusPanel>` / `<IntermediateResult>` / `<TimeStats>`
- 状态：loading（el-skeleton）/ empty（`agentStates` 全空）/ error（`useSSE.error` + ElMessage + 重试按钮）
- 卸载：`useSSE.disconnect()` + `agentStore.resetStates()`
- 节点点击联动：`<AgentFlowChart @node-click>` → `selectedAgent` 状态 → `<AgentStatusPanel>` 高亮 + `<IntermediateResult>` 滚动

**关键修改**（伪代码）：
```ts
const { isConnected, connect, disconnect } = useSSE({
  onEvent: (e) => {
    if (e.type === 'agent_state_update') {
      agentStore.updateAgentState(e.data.agentName as string, e.data as Partial<AgentState>)
    } else if (e.type === 'analysis_completed') {
      disconnect()
    }
  }
})

onMounted(async () => {
  await sessionStore.fetchAnalysisResult(analysisId.value).catch(() => {})
  connect(`/api/analysis/${analysisId.value}/agent-stream?token=${encodeURIComponent(userStore.token)}`)
})

onUnmounted(() => {
  disconnect()
  agentStore.resetStates()
})
```

**风险**：现有 SearchView.spec.ts/HomeView.spec.ts 可能因为 AgentFlowView 改动而引入不相关测试。**实测确认：这些测试与 AgentFlowView 无关**。

**测试** `src/__tests__/views/AgentFlowView.spec.ts`（新增）
- 渲染 4 个子组件
- SSE 错误时显示 error 状态
- 卸载时 disconnect + resetStates 被调用

#### 验证
- `npm run typecheck` 通过
- 现有所有测试不挂
- 新增测试通过

---

### Stage 4：报告组件（task37/38）

#### task37 — ExportPanel

**新建** `src/components/report/ExportPanel.vue`

- Props: `{ analysisId: string; reportTitle?: string }`
- Emits: `{ 'export-success': [format: string]; 'export-error': [error: string] }`
- 两个按钮：「导出PDF」「导出Word」
- 点击调用 `analysisApi.exportPdf / exportWord` → 接收 Blob → `URL.createObjectURL` + `<a download>` 触发下载
- 文件名：`综述报告_{topic}_{YYYYMMDD}.{pdf|docx}`（topic 来自 props.reportTitle）
- loading 状态：单次导出时按钮 loading，其他按钮 disabled
- 失败：`ElMessage.error(msg)` + emit `export-error`
- 底部：「AI 生成，仅供参考」使用 `el-text type="info" size="small"`

**修改** `src/api/analysis.ts` 新增：
```ts
exportPdf: (analysisId: string): Promise<Blob> =>
  http.get(`/analysis/${analysisId}/export/pdf`, { responseType: 'blob' }),

exportWord: (analysisId: string): Promise<Blob> =>
  http.get(`/analysis/${analysisId}/export/word`, { responseType: 'blob' }),
```

> 注意：默认 axios 拦截器把响应按 JSON 解析，Blob 响应需绕过 → 在调用前设置 `responseType: 'blob'`，并在拦截器中按 `responseType !== 'json'` 跳过 `snakeToCamel` 转换和 code 校验。**实施时修改 `api/index.ts` 拦截器**：检测 `config.responseType === 'blob'` 时直接返回 `response.data` 不做处理。

**新建测试** `src/__tests__/components/report/ExportPanel.spec.ts`
- PDF/Word 按钮渲染
- 点击 PDF 调用 `exportPdf`，文件下载触发
- 失败时 ElMessage.error 被调用
- 导出中按钮 loading + disabled

#### task38 — CitationLink

**新建** `src/components/report/CitationLink.vue`

- Props: `{ visible: boolean; citation: { paperId: string; title?: string; authors?: string[]; year?: number; text: string; venue?: string } | null }`
- Emits: `{ 'update:visible': [val: boolean]; 'go-detail': [paperId: string] }`
- 使用 `el-dialog v-model:visible`
- 标题：论文标题（无则显示 `paperId`）
- 正文：原文片段 `citation.text`（白底卡片）
- 底部：作者 / 年份 / 会议元数据 + 「查看论文详情」按钮 → `emit('go-detail', paperId)` 后关闭弹窗
- 数据缺失：显示「引用信息不可用」

**修改** `src/utils/citation.ts` 新增：
```ts
export interface CitationPopupData {
  paperId: string
  title?: string
  authors?: string[]
  year?: number
  text: string
  venue?: string
}

export function extractCitationData(
  raw: string,                  // [Author, Year] 形式
  citations: Citation[]
  papers?: Paper[]              // 可选论文列表
): CitationPopupData | null
```

**新建测试** `src/__tests__/components/report/CitationLink.spec.ts`
- visible=true 时弹窗显示
- citation 内容（标题/原文/元数据）正确渲染
- 点击详情触发 `go-detail` 事件

**新增** `src/__tests__/utils/citation.spec.ts` 追加测试
- `extractCitationData` 正确解析 `[Author, Year]`
- 缺 citations 时返回 null
- 多个 author 处理

#### 验证
- `npm run typecheck` 通过
- 新增 2 组件 + 1 工具测试全部通过

---

### Stage 5：通用组件（task39/40）

#### task39 — FilterPanel + SortDropdown + 类型增强

**修改** `src/types/paper.ts`：
```ts
export interface FilterParams {
  yearFrom?: number
  yearTo?: number
  /** 多选会议列表 */
  conferences?: string[]
  minCitations?: number
  /** 单值 venue 保留兼容 */
  venue?: string
}

export type SortField = 'relevance' | 'publishedDate' | 'citationCount'
export type SortOrder = 'asc' | 'desc'

export interface SortParams {
  field: SortField
  order: SortOrder
}

/** 默认 sort */
export const DEFAULT_SORT: SortParams = { field: 'relevance', order: 'desc' }
```

**修改** `src/stores/paperStore.ts`：
- 现有 `filters: FilterParams` 保留
- 新增 `sortBy: Ref<SortParams> = ref(DEFAULT_SORT)`
- `searchPapers` 方法支持第 3 参数 `sort?: SortParams`，构造 `sort_by=field&sort_order=order` 传给 API
- `updateFilters(newFilters)` 保留

**修改** `src/api/paper.ts`：
- `search` 类型签名增加 `sort_by?: SortField` / `sort_order?: SortOrder`

**新建** `src/components/common/FilterPanel.vue`

- Props: `{ filters: FilterParams; conferences?: string[] }`（conferences 默认常量：ACL/EMNLP/NAACL/COLING/NeurIPS/ICML/ICLR/AAAI/IJCAI）
- Emits: `{ 'update:filters': [filters: FilterParams]; 'reset': [] }`
- 年份范围：`el-date-picker type="yearrange"` （注：Element Plus 不支持 yearrange，使用两个 `el-date-picker type="year"`）
- 会议多选：`el-select multiple`
- 引用数：`el-input-number :min="0"`
- 重置按钮：清空所有筛选后 emit `reset`

**新建** `src/components/common/SortDropdown.vue`

- Props: `{ modelValue: SortParams }`
- Emits: `{ 'update:modelValue': [sort: SortParams] }`
- `el-select` 三个选项：相关度(relevance) / 发表时间(publishedDate) / 引用数(citationCount)

**新建测试**：
- `src/__tests__/components/common/FilterPanel.spec.ts`：年份/会议/引用数筛选 emit + 重置
- `src/__tests__/components/common/SortDropdown.spec.ts`：3 种排序切换 emit
- 追加 `src/__tests__/stores/paperStore.spec.ts`：新增 `sortBy` state + searchPapers 传参

#### task40 — SearchInput + LoadingOverlay

**新建** `src/components/common/SearchInput.vue`

- Props: `{ modelValue: string; placeholder?: string; loading?: boolean }`
- Emits: `{ 'update:modelValue': [val: string]; 'search': [query: string]; 'clear': [] }`
- 300ms 防抖：`watch(modelValue)` + `setTimeout` + `onUnmounted(clearTimeout)`
- 回车立即搜索：`@keyup.enter="emit('search', modelValue); clearTimeout(timer)"`
- `el-input clearable`，清除时 emit `clear`
- loading=true 时 `disabled` + loading 图标
- 历史标签（可选优化）：从 `getRecentSearches()` 读取，点击 tag 触发 search + 保存历史

**新建** `src/components/common/LoadingOverlay.vue`

- Props: `{ visible: boolean; text?: string; zIndex?: number }`
- 使用 `el-overlay` + `el-icon` 旋转 + `<p>{{ text }}</p>`
- 默认 z-index=2000
- 默认 text='加载中...'

**新建测试**：
- `src/__tests__/components/common/SearchInput.spec.ts`：300ms 防抖 + 回车立即 + 清除事件
- `src/__tests__/components/common/LoadingOverlay.spec.ts`：visible 切换 + text 渲染

#### 验证
- `npm run typecheck` 通过
- 新增 4 组件 + paperStore 增强测试全部通过

---

### Stage 6：页面增强（task41）

**修改** `src/views/SearchView.vue`：

- 布局：`<el-container>` + `<el-aside width="240px">` 左侧 `<FilterPanel>` + `<el-main>` 右侧 `<SearchInput>` + `<SortDropdown>` + `<PaperCard>` 列表 + 分页
- `searchPapers(query, page, sort?)` 支持传 sort
- `updateFilters` 事件触发 store `updateFilters`
- 已有功能（论文选择 / 分页 / 收藏）保留

**修改** `src/views/ReportView.vue`：

- 顶部元数据卡添加 3 个新操作：
  - 「导出PDF」「导出Word」按钮 → 调用 `<ExportPanel :analysis-id="analysisId">` 或直接在 ReportView 内联（更简单）。**决策：内联按钮 + 直接调 `analysisApi.exportPdf/exportWord`**，避免 ExportPanel 重复一层。**修改评估**：若希望 ExportPanel 复用，则需在 ReportView 引用 `<ExportPanel :analysis-id="analysisId" :report-title="...">`。**最终方案：使用 ExportPanel 组件以满足 task37/41 的解耦**。
- 「查看 Agent 协同过程」按钮（已有）保留
- 引用点击：`<el-link>` 改为触发 `<CitationLink v-model:visible="citeVisible" :citation="selectedCitation" @go-detail="handleGoDetail">`
- `selectedCitation` 由 `extractCitationData(segment, citations)` 计算
- 保留 `splitReportSegments` 渲染结构，**仅替换点击处理**为弹窗触发

**修改** `src/views/AgentFlowView.vue`（承接 task35）

**新增测试**：
- `src/__tests__/views/SearchView.spec.ts` 扩展：筛选/排序事件触发
- `src/__tests__/views/ReportView.spec.ts`（新建）：引用弹窗触发、导出按钮渲染

#### 验证
- `npm run typecheck` 通过
- 现有测试 + 新增测试全部通过

---

### Stage 7：FM4 验收测试（task42）

**新建** `src/__tests__/integration/fm4-acceptance.spec.ts`

实现 15 项验收检查点对应测试用例：
- AC-001/002 Agent 流程图 6 节点 + 状态色
- AC-003 状态面板
- AC-004 时间线 + 柱状图
- AC-005 resize/tooltip
- AC-006/007 PDF/Word 导出
- AC-008 引用溯源
- AC-009 筛选
- AC-010 排序
- AC-011 防抖（fake timers）
- AC-012 loading
- AC-013 ReportView 完整
- AC-014 SearchView 完整
- AC-015 SSE 联调（mock EventSource + 触发 agent_state_update → 检查 agentStore + ECharts setOption）

#### 验证
- `npm run typecheck` 通过
- `npx vitest run --reporter=verbose` **所有测试通过**

---

## 4. 文件清单（按 Stage 汇总）

### 新建（21 个）
| Stage | 文件 |
|-------|------|
| 1 | `src/composables/useSSE.ts` |
| 1 | `src/__tests__/composables/useSSE.spec.ts` |
| 2 | `src/components/agent/AgentFlowChart.vue` |
| 2 | `src/components/agent/AgentStatusPanel.vue` |
| 2 | `src/components/agent/IntermediateResult.vue` |
| 2 | `src/components/agent/TimeStats.vue` |
| 2 | 4 个 agent 组件测试 |
| 3 | `src/__tests__/views/AgentFlowView.spec.ts` |
| 4 | `src/components/report/ExportPanel.vue` |
| 4 | `src/components/report/CitationLink.vue` |
| 4 | 2 个 report 组件测试 |
| 4 | `src/__tests__/utils/citation.spec.ts`（追加） |
| 5 | `src/components/common/FilterPanel.vue` |
| 5 | `src/components/common/SortDropdown.vue` |
| 5 | `src/components/common/SearchInput.vue` |
| 5 | `src/components/common/LoadingOverlay.vue` |
| 5 | 4 个 common 组件测试 |
| 5 | `src/__tests__/stores/paperStore.spec.ts`（追加） |
| 6 | `src/__tests__/views/ReportView.spec.ts` |
| 7 | `src/__tests__/integration/fm4-acceptance.spec.ts` |

### 修改（9 个）
| Stage | 文件 | 变更内容 |
|-------|------|---------|
| 1 | `src/types/agent.ts` | 新增 `SSEEventType` / `SSEEvent` |
| 4 | `src/api/analysis.ts` | 新增 `exportPdf` / `exportWord` |
| 4 | `src/api/index.ts` | 拦截器支持 blob 响应 |
| 4 | `src/utils/citation.ts` | 新增 `extractCitationData` |
| 5 | `src/types/paper.ts` | 增强 `FilterParams` + 新增 `SortParams` |
| 5 | `src/stores/paperStore.ts` | 新增 `sortBy` + `searchPapers(sort?)` |
| 5 | `src/api/paper.ts` | search 类型增加 sort_by/sort_order |
| 6 | `src/views/SearchView.vue` | 集成 FilterPanel + SortDropdown + SearchInput |
| 6 | `src/views/ReportView.vue` | 集成 ExportPanel + CitationLink |
| 6 | `src/views/AgentFlowView.vue` | 切换为组合 4 个 agent 子组件 + useSSE |

---

## 5. 验证策略

每完成一个 Stage 执行：

```bash
cd "/Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend"

# 类型检查
npm run typecheck

# 单测（按 Stage 选择范围）
npx vitest run src/__tests__/composables/       # Stage 1
npx vitest run src/__tests__/components/agent/  # Stage 2
npx vitest run src/__tests__/views/             # Stage 3, 6
npx vitest run src/__tests__/components/report/ # Stage 4
npx vitest run src/__tests__/components/common/ # Stage 5
npx vitest run src/__tests__/utils/             # Stage 4, 5
npx vitest run src/__tests__/stores/            # Stage 5

# 最终全量
npx vitest run --reporter=verbose               # Stage 7
```

---

## 6. 风险与回退

| 风险 | 回退方案 |
|------|---------|
| AgentFlowView 重构后回归 | 保留 `git` 修改前可 `git checkout` 切回旧版 |
| FilterParams 字段不兼容旧调用方 | 搜索：现有 `paperStore.searchPapers` 调用方仅 2 处（SearchView/HomeView），都已纳入改造范围 |
| ECharts 在测试环境初始化失败 | 使用 `vi.mock('echarts/core', ...)` 全量桩化 |
| api/index.ts 拦截器改 blob 旁路破坏其他 API | 旁路条件为 `config.responseType === 'blob'`，不影响其他调用 |

---

## 7. 下一步建议

完成 FM4 后建议：

1. **FM5（论文管理 + 收藏）**：基于 paperStore.favorites 扩展论文收藏管理页、收藏夹列表
2. **响应式适配**：本次新组件均按桌面端设计，可补一个 `MobileDrawer` 适配移动端
3. **E2E 测试**：用 Playwright 跑一次完整业务流（注册→登录→搜索→筛选→分析→综述→导出）
4. **性能优化**：
   - `AgentFlowChart` 的 ECharts 实例可考虑用 `markRaw` 包裹避免响应式
   - `SearchInput` 历史标签可改用 `pinia-plugin-persistedstate` 替代 localStorage
5. **AI 接入真实数据**：当前所有 API mock 化，FM4 验收后需对接 Java 后端真实接口
6. **可访问性增强**：本次新组件已避免「仅靠颜色传达」，可加 `aria-label` 进一步优化
7. **国际化为后续工作**：当前仅中文，预留 vue-i18n 接入点

---

> **执行入口**：本计划批准后，按 Stage 1→2→3→4→5→6→7 顺序逐 Stage 实施。每个 Stage 完成后立即跑 typecheck + 关联 vitest，全部通过再进下一 Stage。
