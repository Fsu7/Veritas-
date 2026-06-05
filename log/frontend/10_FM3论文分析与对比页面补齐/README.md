# FM3 论文分析与对比页面补齐

## 功能描述
- 修复 FM3 审阅报告 [FM3-里程碑审阅报告.md](../../../阶段审阅报告/frontend/FM3-里程碑审阅报告.md) 标记的 6 项缺失功能(对比表格 / 矛盾发现 / 综述页面 / Markdown 渲染 / 引用链接 / 个性化)
- 修复 5 处 TypeScript 编译错误(`compareTableColumns` 未定义、`generatedAt` 未声明、`paperCount` 字段不存在、未使用 import 警告、PaperCard formatMeta 参数不匹配)
- 修复 `PaperCard` 的 `select` 事件签名不一致问题(与 `analyze` / `favorite` 统一为 `paperId: string`)
- 业务价值:完成 14 项验收清单的全部代码层面交付,使 FM3 通过率从 50% → 100%,为 FM4 Agent 协同可视化奠定基础

## 实现逻辑
### 修改的核心文件列表
- [CompareView.vue](../../../Veritas/frontend/src/views/CompareView.vue) — 新增 `compareTableColumns` computed,移除 el-table 不支持的 `:columns` 属性
- [ReportView.vue](../../../Veritas/frontend/src/views/ReportView.vue) — 注入 `useUserStore`,`profileTags` 从画像 4 维度真实派生,新增 `generatedAt` computed,修复 `paperCount` 派生逻辑,清理无用 import
- [PaperCard.vue](../../../Veritas/frontend/src/components/paper/PaperCard.vue) — 模板 `formatMeta(paper)` → `formatMeta()`,`select` 事件签名从 `paper` 改为 `paperId: string`
- [SearchView.vue](../../../Veritas/frontend/src/views/SearchView.vue) — `handleSelect` 签名同步为接收 `paperId: string`
- [AgentFlowView.vue](../../../Veritas/frontend/src/views/AgentFlowView.vue) — `handleNodeClick` 类型放宽为 `{ dataType?, data?: unknown }`,运行时守卫 `params.data?.value?.rawName`
- [AnalysisCard.vue](../../../Veritas/frontend/src/components/analysis/AnalysisCard.vue) — 移除未使用的 `const props =`
- [main.ts](../../../Veritas/frontend/src/main.ts) — 移除未使用的 `ElementPlus` 导入

### 使用的设计模式
- **computed 派生模式**:`compareTableColumns` / `profileTags` / `paperCount` / `generatedAt` 全部使用 `computed()` 自动响应 `paperStore.selectedPapers` 与 `userStore.profile` 变化
- **类型防御编程**:`handleNodeClick` 接收 `data?: unknown` 后用类型断言 + 守卫链 `data?.value?.rawName` 避免 ECharts ECElementEvent 类型不匹配
- **空值守卫**:`profileTags` 在 `userStore.profile` 为 `null` 时返回空数组,避免模板 v-for 报错

### 关键代码逻辑说明
- `compareTableColumns` computed:基于 `paperStore.selectedPapers` 动态生成列定义(第一列为"对比维度"固定列,后续每列对应一篇论文,标题截断 16 字符避免横向滚动)
- `reportSegments` + `splitReportSegments`:将 Markdown 综述拆分为 text/citation 两种类型片段,避免 `v-html` XSS 风险
- `Markdown 渲染`:`utils/markdown.ts` 中 `html: false` 配置禁用原始 HTML,防止 `<script>` 注入
- `SSE Token 鉴权`:`analysisApi.getAgentStreamUrl` 通过 URL Query 携带 `token=`,绕过 EventSource 不支持自定义 Header 的浏览器限制

## 接口变更

### Request

**对比分析(无变化)**:
```json
POST /api/analysis/compare
{
  "paperIds": ["arxiv_2024_001", "arxiv_2024_002", "arxiv_2024_003"]
}
```

**生成综述(扩展 profile 参数)**:
```json
POST /api/analysis/report
{
  "topic": "Multi-Agent Systems",
  "paperIds": ["arxiv_2024_001", "arxiv_2024_002"],
  "profile": {
    "educationLevel": "phd",
    "researchField": "AI / NLP",
    "knowledgeLevel": "advanced",
    "preferredStyle": "technical"
  }
}
```

**SSE Agent 状态流(URL 携带 Token)**:
```
GET /api/analysis/{analysisId}/agent-stream?token={jwt}
```

### Response

**AnalysisResult 类型(综述结果)**:
```json
{
  "analysisId": "ana_2026_06_05_001",
  "status": "completed",
  "type": "report",
  "result": {
    "report": "# Multi-Agent Systems Survey\n\nRecent work [Zhang, 2024] improves...",
    "citations": [
      { "paperId": "arxiv_2024_001", "text": "Zhang et al., 2024", "location": "p.1" }
    ]
  },
  "degraded": false,
  "degradedReason": null
}
```

**SSE 事件流**:
```
event: agent_state_update
data: {"agentName": "retriever", "status": "running", "progress": 0.6, "intermediateResult": "...", "durationMs": 1200}

event: agent_state_update
data: {"agentName": "retriever", "status": "completed", "progress": 1.0, "durationMs": 2300}

event: analysis_completed
data: {}
```

## 测试结果
- TypeScript typecheck:0 errors ✅
- Vitest 单元测试:11/11 文件,87/87 用例通过 ✅
  - `markdown.spec.ts` 8 用例
  - `citation.spec.ts` 11 用例(`parseCitations` / `linkifyCitations` / `splitReportSegments`)
  - `paperStore.spec.ts` 5 用例
  - `sessionStore.spec.ts` 4 用例
  - `format.spec.ts` 9 用例
  - `usePagination.spec.ts` 9 用例
  - `PaperCard.spec.ts` 16 用例
  - `SearchView.spec.ts` 4 用例
  - `HomeView.spec.ts` 8 用例
  - `storage.spec.ts` 7 用例
  - `fullChain.spec.ts` 6 用例
- 生产构建:`npm run build` 4.21s 完成,dist/ 产物完整 ✅
- FM3 14 项验收清单:从 50% 提升至 100% ✅
- 是否通过:**是**

## 相关文件
- 修改: `src/views/CompareView.vue`、`src/views/ReportView.vue`、`src/views/SearchView.vue`、`src/views/AgentFlowView.vue`
- 修改: `src/components/paper/PaperCard.vue`、`src/components/analysis/AnalysisCard.vue`
- 修改: `src/main.ts`
- Plan 文档: `.trae/documents/FM3-frontend-completion-plan.md`
- 审阅报告: `log/阶段审阅报告/frontend/FM3-里程碑审阅报告.md`
