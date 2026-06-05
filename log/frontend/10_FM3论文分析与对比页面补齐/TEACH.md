# 技术教学文档 — FM3 论文分析与对比页面补齐

## 开发思路

### 需求分析过程
本次任务背景是 FM3 审阅报告标记 6 项缺失 + 多个 TypeScript 编译错误阻塞全量验证。审阅报告本质是基于现有代码与 14 项验收清单的逐项核对,发现问题主要集中在:

1. **业务功能未实现** — CompareView/ReportView 早期为占位代码,后期填了业务逻辑但有引用错误(如 `compareTableColumns` 未声明)
2. **类型定义 vs 实际使用不匹配** — `AnalysisResult` 类型未声明时间字段(`createdAt`/`updatedAt`/`completedAt`),导致 ReportView 派生 `generatedAt` 时类型缺失
3. **事件签名不一致** — PaperCard 的 `select` 事件传 Paper 对象,`analyze`/`favorite` 传 paperId,违反"同类型事件同签名"原则
4. **未使用 import 噪声** — TypeScript 严格模式(`noUnusedLocals`)将累积的 import 警告

我使用 Plan 模式分两阶段:Phase 1 探索代码全貌(已读取 14+ 文件),Phase 2 制定决策完整 plan(详见 [FM3-frontend-completion-plan.md](../../../../.trae/documents/FM3-frontend-completion-plan.md))。关键决策:

- 决策 A2:`generatedAt` 简化为 `Date.now()`(综述加载完成时刻),不扩展 `AnalysisResult` 类型(避免后端同步改动)
- 决策 A3:`paperCount` 改用 `result.result.citations` 去重统计(与综述实际引用数对齐)
- 决策 A4:`profileTags` 展示 4 维画像(教育/知识/领域/风格),充分利用 userStore

### 技术选型考虑

1. **computed vs 函数**:`compareTableColumns` / `profileTags` / `paperCount` / `generatedAt` 全部用 `computed()`
   - 自动追踪 `paperStore.selectedPapers` / `userStore.profile` 变化
   - 模板中直接引用,无需 `.value`
   - 多次访问自动缓存,避免重复计算

2. **el-table 列定义两种写法**:
   - ❌ 错: `:columns="compareTableColumns"` + 子组件省略(Element Plus 不支持 columns 属性)
   - ✅ 对: 模板中直接 `<el-table-column v-for="col in compareTableColumns" :prop="col.prop" :label="col.label" />`(标准用法)

3. **类型放宽与运行时守卫**:ECharts `ECElementEvent.data` 类型为 `OptionDataItem`(可能是 `string` 或对象)。采用"unknown 接收 + 断言 + 守卫链"模式:
   ```typescript
   function handleNodeClick(params: { dataType?: string; data?: unknown }) {
     if (params.dataType !== 'node') return
     const data = params.data as { value?: { rawName?: string } } | null | undefined
     const rawName = data?.value?.rawName
     if (!rawName) return
   }
   ```

### 架构设计思路

```
CompareView
├── paperStore.selectedPapers (2-5 篇)
│   ├── 比较按钮 → analysisApi.comparePapers
│   ├── generateReport (含 userStore.profile)
│   └── 跳转到 /report/{analysisId}
├── 对比结果 CompareResult
│   ├── table (dimension × values[])
│   │   ├── 渲染为 compareTableData (computed 扁平化)
│   │   └── compareTableColumns (computed 动态列)
│   ├── summary
│   └── conflicts[] → el-alert warning
└── degraded 标签 + degradedReason 说明

ReportView
├── sessionStore.fetchAnalysisResult (analysisId)
├── userStore.profile 派生 profileTags
├── citations → splitReportSegments (text + citation 类型)
├── markdown → renderMarkdown (v-html + html:false XSS 防护)
└── el-link 点击 → 跳转 PaperDetail

AgentFlowView
├── ECharts 按需导入(echarts/core + GraphChart + TooltipComponent + CanvasRenderer)
├── AGENT_NODES (6 节点) + 边关系
├── agentStore.agentStates 订阅 → 颜色变化 (waiting/running/completed/failed)
├── 节点点击 → el-drawer 显示 intermediateResult
└── onUnmounted → echarts.dispose() + disconnectSSE()
```

## 实现步骤

1. **修复 CompareView 表格列定义(E1)**
   - 在 `<script setup>` 添加 `CompareTableColumn` interface + `compareTableColumns` computed
   - 模板中移除 el-table 的 `:columns` 属性,仅保留子组件 `el-table-column` v-for

2. **修复 ReportView 字段派生(E2/E3/E4/E5)**
   - 移除无用的 `sessionStore as _ignored` 别名 import
   - 精简 icon import 为 `View, Connection`
   - 新增 `useUserStore` 注入
   - 重写 `profileTags` 从 `userStore.profile` 派生 4 维标签
   - 修复 `paperCount` 从 `result.result.citations` 去重
   - 新增 `generatedAt` computed 返回 `Date.now().toISOString()`
   - 模板中移除未使用的 `<el-icon><Position/></el-icon>`

3. **修复 PaperCard formatMeta(E6)**
   - 模板 `formatMeta(paper)` → `formatMeta()`(函数已通过 `props.paper` 访问)
   - 同步 `select` 事件签名为 `paperId: string`(与 analyze/favorite 一致)
   - SearchView `handleSelect` 签名同步修改

4. **修复衍生未使用变量**
   - `AnalysisCard.vue` 移除 `const props =`(改用直接 `withDefaults` 链)
   - `main.ts` 移除 `import ElementPlus`(未使用)
   - `AgentFlowView.vue` `handleNodeClick` 类型放宽
   - `CompareView.vue` 移除 `onUnmounted`/`Warning`/`Conflict`/`sessionStore` 未使用 import

5. **全量验证**
   - `npm run typecheck` → 0 errors
   - `npm run test:run` → 87/87 用例通过
   - `npm run build` → 4.21s,dist/ 完整

## 解决了什么问题

### 核心问题 1:TypeScript 严格模式下未使用 import 警告
- **解决方案对比**:
  - 方案 A:`tsconfig.json` 关闭 `noUnusedLocals`(❌ 失去静态检查)
  - 方案 B:逐个清理未使用 import(✅ 选择,代码即文档)
- **最终方案优势**:保持 TS 严格模式,代码整洁度提升

### 核心问题 2:PaperCard 事件签名不一致
- **现象**:`@select` 传 Paper 对象,`@analyze`/`@favorite` 传 paperId
- **影响**:父组件 `handleSelect` / `handleAnalyze` 签名不一致,易混淆
- **解决方案**:统一为 `paperId: string`,PaperDetailView 通过 `router.push({ params: { paperId } })` 直接使用

### 核心问题 3:ReportView 缺少 userStore 注入
- **现象**:`profileTags` 硬编码为"按用户画像生成",无法个性化显示
- **解决方案**:注入 `useUserStore`,从 `profile` 4 维度真实派生,空值守卫返回空数组

### 核心问题 4:ECharts 事件类型与组件期望类型不匹配
- **现象**:`chart.on('click', handleNodeClick)` 类型错误,`ECElementEvent.data` 是 `OptionDataItem` 而非对象
- **解决方案**:接收 `data?: unknown`,运行时类型断言 + 守卫链 `data?.value?.rawName`

## 变更内容

### 新增文件
- 无

### 修改文件
- `src/views/CompareView.vue` (+22 行 `compareTableColumns` computed)
- `src/views/ReportView.vue` (+30 行 useUserStore 注入 + profileTags/paperCount/generatedAt 派生, -3 行未使用 import)
- `src/views/SearchView.vue` (handleSelect 签名修改)
- `src/views/AgentFlowView.vue` (handleNodeClick 类型放宽)
- `src/components/paper/PaperCard.vue` (select 事件签名 + formatMeta 调用)
- `src/components/analysis/AnalysisCard.vue` (移除未使用的 `const props =`)
- `src/main.ts` (移除未使用 `ElementPlus` 导入)

### 配置变更
- 无

## 关键技术点

### 1. computed 派生 vs 函数调用的选择
- `compareTableColumns` 使用 `computed`:`paperStore.selectedPapers` 变化时自动重新计算列定义
- `formatMeta()`(PaperCard) 使用函数:依赖 `props.paper`,Vue 自动响应 Props 变化

### 2. 类型防御编程
- ECharts 事件类型用 `unknown` 接收 + 运行时断言
- `userStore.profile` 用空值守卫 `if (!p) return []`
- `result.value` 链式 `?.` 可选链

### 3. v-for + computed 实现动态表格
```vue
<el-table :data="compareTableData">
  <el-table-column
    v-for="col in compareTableColumns"
    :key="col.prop"
    :prop="col.prop"
    :label="col.label"
    :min-width="col.minWidth"
    :fixed="col.fixed"
  />
</el-table>
```
- `compareTableData`:扁平化 `CompareRow[]` 为 `{ dimension, paper_0, paper_1, ... }`
- `compareTableColumns`:根据 `paperStore.selectedPapers` 动态生成列

### 4. Markdown 渲染 XSS 防护
```typescript
export const md = new MarkdownIt({
  html: false,        // 禁用原始 HTML,过滤 <script> 等危险标签
  linkify: true,      // URL 自动转链接
  typographer: true,  // 智能引号
  breaks: true        // 换行转 <br>
})
```

### 5. SSE JWT Token 通过 URL Query 传递
```typescript
getAgentStreamUrl: (analysisId: string): string => {
  const token = localStorage.getItem('token') || ''
  return `/api/analysis/${analysisId}/agent-stream?token=${encodeURIComponent(token)}`
}
```
- EventSource 浏览器 API 不支持自定义 Header
- 后端需支持 `?token=` 鉴权(FM2 High 已通知 Java 后端)

## 经验总结

### 开发过程中的收获
1. **TypeScript 严格模式是质量保障** — 7 个未使用变量问题一次性暴露,清理后代码更可维护
2. **computed 是 Vue 响应式的核心** — 派生状态首选 computed,而非手动 watch + ref
3. **类型放宽时必须有运行时守卫** — `unknown` + 断言 + 守卫链是 TS 最佳实践

### 踩过的坑及如何避免
1. **ECharts ECElementEvent 类型推断不一致**
   - 现象:在 `chart.on('click', handler)` 中 handler 的 params 类型是 `ECElementEvent`
   - 解决:接收 `data?: unknown`,运行时断言 `{ value?: { rawName?: string } }`
   - 教训:第三方库事件类型多变,不要假设结构稳定

2. **el-table 误用 columns 属性**
   - 现象:模仿 ant-design-table 的 `:columns` API
   - 解决:Element Plus 的 el-table 仅支持子组件 `el-table-column` v-for
   - 教训:切换 UI 库时检查 API 差异

3. **PaperCard select 事件传 Paper 对象 vs paperId**
   - 现象:与同组件的 analyze/favorite 签名不一致
   - 解决:统一为 paperId,父组件 `router.push` 直接用
   - 教训:同组件 emit 命名相似的应保持签名一致

### 最佳实践建议
1. **审计先行**:FM3 收尾时先用 `veritas-frontend-review` skill 全量扫描,生成结构化报告,再针对性修复
2. **Plan Mode**:复杂修复(>3 个文件)先 Plan 模式规划,获得用户确认后再实施
3. **三件套验证**:每次修改都运行 `typecheck` + `test:run` + `build`,避免累积技术债
4. **测试驱动**:PaperCard 的 16 个单元测试是修复 select 签名不一致的"质量防护网",能立刻发现回归
5. **清理 import**:每次提交前运行 typecheck,清理未使用 import,避免噪声累积

## 待办(FM4 准备)
- 后端 SSE `?token=` 鉴权支持确认(需 Java 后端同步)
- EChunks 体积优化(echarts 456KB + element-plus 922KB,可考虑按需引入)
- PaperCard / ReportView 视图级测试补充
- PaperDetailView 提取 formatAuthors/formatMeta 到 utils(FM2 遗留)
