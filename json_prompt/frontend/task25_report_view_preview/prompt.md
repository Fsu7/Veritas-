# FM3-Task25 ReportView 基础 + ReportPreview + markdown-it 渲染

## 任务概述
实现 `views/ReportView.vue`（占位→完整）、`components/report/ReportPreview.vue`（新建）、`utils/markdown.ts`（新建）。覆盖路由解析、Markdown 渲染（XSS 安全）、引用链接 [Author, Year] 自定义、综述元信息。

## 里程碑
FM3：论文分析与对比页面完成（v0.3）

## 涉及模块
- `views/ReportView.vue`（修改）
- `components/report/ReportPreview.vue`（新增）
- `utils/markdown.ts`（新增）
- `stores/sessionStore.ts`（fetchAnalysisResult）
- `stores/userStore.ts`（画像摘要）

## 文件变更
| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | `Veritas/frontend/src/utils/markdown.ts` | markdown-it 实例 + 引用规则 |
| 新增 | `Veritas/frontend/src/components/report/ReportPreview.vue` | Markdown 渲染 + 引用链接 |
| 修改 | `Veritas/frontend/src/views/ReportView.vue` | 完整综述页 |

## 功能要求
1. **FR-001** utils/markdown.ts：`createMarkdownRenderer()`，html:false + 引用自定义规则；`renderMarkdown(content, paperIdMap?)` 同步渲染
2. **FR-002** ReportPreview：4 态（loading/empty/normal/error）；v-html 渲染；事件委托 `.citation-link` → emit('citation-click', paperId)
3. **FR-003** ReportView：fetchAnalysisResult → 4 维度元信息 + ReportPreview + AI 标注 + 「返回」「查看 Agent 流程」
4. **FR-004** 报告样式：行高 1.8、标题层级、代码块、引用块
5. **FR-005** 可访问性：role/aria-label

## 跨系统一致性
- `analysisId` ↔ `analysis_id`，`paperId` ↔ `paper_id`，`updatedAt` ↔ `updated_at`

## 验收标准
- [ ] XSS 测试通过（`<script>` 被转义）
- [ ] 引用链接触发 emit
- [ ] 4 维度元信息正确
- [ ] 组件代码 ≤ 300 行

## 验证命令
```bash
cd Veritas/frontend && npx vue-tsc --noEmit
cd Veritas/frontend && npx vitest run src/__tests__/utils/markdown.spec.ts
```
