# Task18/19/20 前端实现计划 — PaperDetailView + AnalysisCard + SessionStore增强

## 概览

按顺序执行3个任务，实现FM3里程碑（论文分析+对比页面可用）的前端核心功能：

| 任务 | 核心交付 | 文件变更 |
|------|---------|---------|
| Task18 | PaperDetailView论文详情页 | 修改 `PaperDetailView.vue` |
| Task19 | AnalysisCard + PlainExplanation组件 | 新建 `AnalysisCard.vue` + `PlainExplanation.vue`，修改 `PaperDetailView.vue` |
| Task20 | sessionStore增强 + 全链路测试 | 修改 `sessionStore.ts` + `PaperDetailView.vue`，新建 `fullChain.spec.ts` |

---

## Task18: PaperDetailView 论文详情页

### 当前状态
- `PaperDetailView.vue` 为空壳占位（`<h2>论文详情页</h2><p>页面开发中...</p>`）
- 所有依赖已就绪：paperApi、analysisApi、sessionStore、paperStore、userStore、router、types

### 实现步骤

#### Step 1: PaperDetailView 完整实现

**Script Setup 结构**（按规范顺序）：
1. **Imports** — `vue-router`, `paperApi`, `analysisApi`, `usePaperStore`, `useSessionStore`, `useUserStore`, Element Plus组件, types
2. **Refs** — `paper: Ref<Paper|null>`, `paperLoading`, `paperError`, `analysisResult: Ref<AnalysisResult|null>`, `analyzing`, `analysisError`, `pollTimer`
3. **Computed** — `paperId` (from route.params), `isFavorited`, `showPlainExplanation`
4. **Methods** — `fetchPaperDetail()`, `handleFavorite()`, `handleAnalyze()`, `pollAnalysisStatus()`
5. **Lifecycle** — `onMounted(fetchPaperDetail)`, `onUnmounted(cleanup)`

**Template 结构**：
```
<div class="paper-detail-view">
  <!-- Loading骨架屏 -->
  <el-skeleton v-if="paperLoading" :rows="5" animated />

  <!-- Error状态 -->
  <el-result v-else-if="paperError" icon="error" title="加载失败" ... />

  <!-- Empty状态（论文不存在） -->
  <el-result v-else-if="!paper" icon="warning" title="论文未找到" ... />

  <!-- 正常内容 -->
  <template v-else>
    <!-- 返回导航 -->
    <el-page-header @back="router.back()" :title="paper.title" content="论文详情" />

    <!-- 论文元数据卡片 -->
    <el-card class="paper-detail-view__info">
      <h1>{{ paper.title }}</h1>
      <div class="paper-detail-view__meta">作者 · 年份 · 会议 · 引用数</div>
      <div class="paper-detail-view__abstract">{{ paper.abstract }}</div>
      <div class="paper-detail-view__keywords">关键词标签</div>
      <div class="paper-detail-view__actions">
        收藏按钮 + 查看PDF按钮 + 触发AI分析按钮
      </div>
    </el-card>

    <!-- AI分析区域 -->
    <el-card class="paper-detail-view__analysis">
      <!-- 未分析 -->
      <el-empty v-if="!analysisResult && !analyzing" description="尚未进行分析" />
      <!-- 分析中 -->
      <div v-else-if="analyzing" v-loading="true">AI正在分析论文...</div>
      <!-- 分析完成（5维度占位，task19替换为AnalysisCard） -->
      <div v-else-if="analysisResult?.result?.analysis">
        5维度文本展示 + 通俗解释 + 操作按钮
      </div>
      <!-- 分析失败 -->
      <el-alert v-else-if="analysisError" type="error" ... />
    </el-card>
  </template>
</div>
```

**关键实现细节**：
- `fetchPaperDetail()`: try-catch包裹paperApi.getDetail(paperId)，404设置paperError
- `handleAnalyze()`: sessionStore.createSession → analysisApi.analyzePaper → pollAnalysisStatus
- `pollAnalysisStatus()`: 递归setTimeout（3s间隔），completed/failed时停止，onUnmounted清理
- `showPlainExplanation`: beginner/intermediate用户可见
- AI标注："AI生成，仅供参考"
- BEM命名 + CSS变量 + 8px间距系统

---

## Task19: AnalysisCard + PlainExplanation 组件

### 实现步骤

#### Step 2: 创建 PlainExplanation.vue

**Script Setup**：
1. **Props**: `defineProps<{ content: string }>()`
2. 无Emits、无状态（纯展示组件）

**Template**：
```html
<el-card class="plain-explanation__card">
  <el-alert type="info" :closable="false" show-icon class="plain-explanation">
    <template #title>
      <el-text tag="b" class="plain-explanation__title">💡 通俗理解：</el-text>
    </template>
    <el-text class="plain-explanation__content">{{ content }}</el-text>
  </el-alert>
</el-card>
```

**Style**: BEM命名，scoped CSS，CSS变量，8px间距

#### Step 3: 创建 AnalysisCard.vue

**Script Setup**：
1. **Imports** — PlainExplanation, AnalysisResult type
2. **Props**: `defineProps<{ analysis: AnalysisResult; showPlainExplanation?: boolean }>()` (showPlainExplanation默认false)
3. **Emits**: `defineEmits<{ (e: 'generate-report', analysisId: string): void; (e: 'select-compare', analysisId: string): void }>()`
4. **Constants**: dimensions数组 `[{key, label, icon}]`

**dimensions常量**：
```ts
const DIMENSIONS = [
  { key: 'researchQuestion', label: '研究问题', icon: '🎯' },
  { key: 'coreMethod', label: '核心方法', icon: '🔧' },
  { key: 'keyExperiments', label: '主要实验', icon: '🧪' },
  { key: 'coreFindings', label: '核心结论', icon: '📊' },
  { key: 'limitations', label: '局限性', icon: '⚠️' },
] as const
```

**Template**：
```html
<el-card class="analysis-card">
  <div class="analysis-card__header">
    <span>🤖 AI智能分析</span>
    <el-text type="info" size="small">AI生成，仅供参考</el-text>
    <el-tag v-if="analysis.degraded" type="warning" size="small">部分降级</el-tag>
    <el-text v-if="analysis.degradedReason" type="warning" size="small">{{ analysis.degradedReason }}</el-text>
  </div>

  <div v-if="analysis.result?.analysis">
    <div v-for="dim in DIMENSIONS" class="analysis-card__dimension">
      <h4 class="analysis-card__dimension-title">{{ dim.icon }} {{ dim.label }}</h4>
      <p class="analysis-card__dimension-content">{{ analysis.result.analysis[dim.key] }}</p>
    </div>
  </div>

  <PlainExplanation
    v-if="showPlainExplanation && analysis.result?.analysis?.plainExplanation"
    :content="analysis.result.analysis.plainExplanation"
  />

  <div class="analysis-card__actions">
    <el-button type="primary" size="small" @click="emit('generate-report', analysis.analysisId)">生成综述</el-button>
    <el-button size="small" @click="emit('select-compare', analysis.analysisId)">选择对比</el-button>
  </div>
</el-card>
```

**Style**: BEM命名，scoped CSS，CSS变量，8px间距

#### Step 4: 修改 PaperDetailView.vue — 替换5维度占位为AnalysisCard

- import AnalysisCard + PlainExplanation
- 将task18的5维度占位文本替换为 `<AnalysisCard :analysis="analysisResult" :showPlainExplanation="showPlainExplanation" @generate-report="handleGenerateReport" @select-compare="handleSelectCompare" />`
- 移除原占位文本和操作按钮
- 新增 `handleGenerateReport(analysisId)` → router.push({name:'Report', params:{analysisId}})
- 新增 `handleSelectCompare(analysisId)` → router.push({name:'Compare'})

---

## Task20: sessionStore增强 + 全链路测试

### 实现步骤

#### Step 5: 增强 sessionStore.ts

**新增状态**：
```ts
const analysisStatus = ref<'idle'|'creating_session'|'starting_analysis'|'polling'|'connecting_sse'|'completed'|'failed'>('idle')
const analysisError = ref<string | null>(null)
const pollTimer = ref<ReturnType<typeof setTimeout> | null>(null)
const eventSource = ref<EventSource | null>(null)
const reconnectAttempts = ref(0)
```

**新增Getters**：
```ts
const isAnalyzing = computed(() => ['creating_session','starting_analysis','polling','connecting_sse'].includes(analysisStatus.value))
const isAnalysisCompleted = computed(() => analysisStatus.value === 'completed')
const isAnalysisFailed = computed(() => analysisStatus.value === 'failed')
```

**新增方法**：

1. **startAnalysis(topic, paperId)** — 编排完整分析流程：
   - cleanup() → analysisStatus='creating_session' → createSession(topic) → analysisStatus='starting_analysis' → analysisApi.analyzePaper({paperId}) → currentAnalysisId → analysisStatus='polling' → pollAnalysisStatus + connectAgentStream → 返回最终结果
   - 任何步骤失败 → analysisStatus='failed', analysisError=error.message

2. **pollAnalysisStatus(analysisId, interval=3000)** — 递归setTimeout轮询：
   - 调用analysisApi.getStatus(analysisId)
   - completed → 存入analysisResults Map, analysisStatus='completed'
   - failed → analysisStatus='failed', analysisError='分析失败'
   - pending/processing → setTimeout递归
   - 最大60次（3分钟超时）

3. **connectAgentStream(analysisId)** — SSE连接：
   - new EventSource(analysisApi.getAgentStreamUrl(analysisId))
   - 监听agent_state_update → agentStore.updateAgentState
   - 监听analysis_completed → disconnectSSE + analysisStatus='completed'
   - onerror → 重连逻辑（3s/5次）

4. **disconnectSSE()** — 关闭EventSource

5. **cleanup()** — 清理pollTimer + eventSource + agentStore.resetStates() + 重置状态

#### Step 6: 重构 PaperDetailView.vue 分析逻辑

- 移除内联轮询逻辑（pollAnalysisStatus等）
- handleAnalyze简化为：`await sessionStore.startAnalysis(paper.value.title, paperId)`
- 使用sessionStore.isAnalyzing替代analyzing ref
- 使用sessionStore.analysisStatus显示阶段提示
- onUnmounted调用sessionStore.cleanup()

#### Step 7: 创建全链路集成测试

**文件**: `src/__tests__/integration/fullChain.spec.ts`

**测试流程**（全部使用vi.mock模拟API）：
1. 注册新用户 → 验证userStore.token非空
2. 登录 → 验证isLoggedIn=true
3. 搜索论文 → 验证paperStore.searchResults非空
4. 获取论文详情 → 验证paper数据完整
5. 触发分析 → 验证sessionStore.analysisStatus变化(idle→creating_session→starting_analysis→polling→completed)
6. 验证analysisResult包含5维度数据

---

## 文件变更汇总

| 操作 | 文件路径 | 任务 |
|------|---------|------|
| 修改 | `src/views/PaperDetailView.vue` | Task18 → Task19 → Task20 |
| 新建 | `src/components/analysis/AnalysisCard.vue` | Task19 |
| 新建 | `src/components/analysis/PlainExplanation.vue` | Task19 |
| 修改 | `src/stores/sessionStore.ts` | Task20 |
| 新建 | `src/__tests__/integration/fullChain.spec.ts` | Task20 |

## 执行顺序

```
Task18 (PaperDetailView完整实现)
  ↓
Task19 (AnalysisCard + PlainExplanation + PaperDetailView替换占位)
  ↓
Task20 (sessionStore增强 + PaperDetailView重构 + 全链路测试)
```

## 验证命令

```bash
cd Veritas/frontend
npx vue-tsc --noEmit                    # TypeScript类型检查
npx vitest run                           # 全部测试
npx vitest run src/components/analysis/  # AnalysisCard测试
npx vitest run src/__tests__/integration/ # 全链路测试
```

## 关键约束

- 单组件≤300行
- BEM命名 + scoped CSS + CSS变量 + 8px间距
- 组件结构顺序：imports → Props/Emits → ref/reactive → computed → methods → lifecycle
- AnalysisCard是纯展示+事件上行组件，不直接操作Store/API
- PlainExplanation是纯展示组件，无事件
- sessionStore中不使用useSSE composable（手动实现EventSource）
- 轮询使用递归setTimeout而非setInterval
- AI内容标注"AI生成，仅供参考"
- 禁止console.log敏感信息
