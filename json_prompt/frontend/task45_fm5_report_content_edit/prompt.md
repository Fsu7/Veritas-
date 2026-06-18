# Task 45：综述内容编辑功能

> **里程碑**：FM5 功能完善与UI打磨（Week 11 Day 3）
> **优先级**：P1
> **涉及模块**：F1.4 综述生成模块

---

## 一、任务概述

实现综述内容编辑功能。当前 ReportView 仅展示 AI 生成的综述内容（segments 分段渲染+Markdown 备份渲染），无编辑能力。

**目标**：新增 ReportEditor 组件（Markdown 编辑器+实时预览+工具栏），ReportView 增加"编辑"按钮切换编辑/预览模式，编辑后可保存（调用后端 API）和导出（ExportPanel 支持 customContent），编辑后引用标注仍可点击溯源。

---

## 二、涉及模块

| 模块 | 路径 | 职责 |
|------|------|------|
| ReportView | `src/views/ReportView.vue` | 综述报告页（增加编辑模式） |
| ReportEditor | `src/components/report/ReportEditor.vue` | Markdown 编辑器（新建） |
| ExportPanel | `src/components/report/ExportPanel.vue` | 导出面板（支持 customContent） |
| analysisApi | `src/api/analysis.ts` | 分析 API（新增 saveReportContent） |
| markdown utils | `src/utils/markdown.ts` | Markdown 渲染（新增 renderMarkdownWithCitations） |
| citation utils | `src/utils/citation.ts` | 引用处理（复用） |

---

## 三、文件变更表

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| modify | `Veritas/frontend/src/views/ReportView.vue` | 增加"编辑"按钮切换模式；编辑模式用 ReportEditor；保存/取消按钮 |
| create | `Veritas/frontend/src/components/report/ReportEditor.vue` | 新建 Markdown 编辑器：textarea+预览+工具栏 |
| modify | `Veritas/frontend/src/components/report/ExportPanel.vue` | 新增 customContent prop，导出时优先使用 |
| modify | `Veritas/frontend/src/api/analysis.ts` | 新增 saveReportContent(analysisId, content) |
| modify | `Veritas/frontend/src/utils/markdown.ts` | 新增 renderMarkdownWithCitations 函数 |

---

## 四、功能要求

| 编号 | 描述 | 优先级 |
|------|------|--------|
| FR-001 | ReportView 增加"编辑"按钮切换编辑/预览模式 | P0 |
| FR-002 | ReportEditor：textarea 编辑 + 实时预览 + 工具栏 | P0 |
| FR-003 | 工具栏支持加粗/斜体/标题/列表/引用（光标位置插入） | P1 |
| FR-004 | 编辑模式支持"保存"（调用 API）和"取消"（恢复原内容） | P0 |
| FR-005 | ExportPanel 支持 customContent，编辑后导出自定义内容 | P0 |
| FR-006 | 编辑后引用标注仍可点击溯源（renderMarkdownWithCitations） | P1 |

---

## 五、关键技术约束

1. **分层规范**：ReportView 可直接调用 analysisApi.saveReportContent（不涉及全局状态）
2. **XSS 防护**：ReportEditor 预览必须用 markdown-it html:false（禁止 v-html 渲染未净化 HTML）
3. **手动保存**：禁止自动保存，必须用户点击"保存"按钮（避免误操作和频繁 API 调用）
4. **CSS 变量**：使用 `var(--spacing-md)` 等 CSS 变量
5. **内容状态管理**：editingContent（编辑中）+ originalContent（原始），保存成功后 originalContent = editingContent

---

## 六、验收检查点

- [ ] AC-001：点击"编辑"按钮进入编辑模式，显示 ReportEditor — manual_test
- [ ] AC-002：编辑内容后预览区实时更新（Markdown 正确渲染） — manual_test
- [ ] AC-003：保存编辑内容后调用后端 API 成功，ElMessage 提示 — automated_test
- [ ] AC-004：编辑后导出 PDF/Word 包含编辑内容（非原始内容） — manual_test
- [ ] AC-005：编辑后引用标注 [Author, Year] 仍可点击溯源 — manual_test
- [ ] AC-006：取消编辑后恢复原内容，无数据丢失 — automated_test
- [ ] AC-007：所有新增/修改的代码通过 lint 和 build 验证 — code_review

---

## 七、验证命令

```bash
cd Veritas/frontend && npm run test -- --run ReportEditor ReportView
cd Veritas/frontend && npm run lint
cd Veritas/frontend && npm run build
```

---

## 八、参考文档

- `AGENTS.md` — 项目全景上下文与前端约束
- `docs/frontend/前端模块系统架构文档.md` — 前端架构规范、F1.4 综述生成模块设计
- `docs/frontend/前端模块项目里程碑文档.md` — FM5 里程碑任务分解（Week 11 Day 3）
- `docs/开发规范文档.md` — 前端编码规范
- `docs/架构决策记录(ADR).md` — 架构决策
