# Task 48：通用空状态与错误状态组件

> **里程碑**：FM5 功能完善与UI打磨（Week 11 Day 6）
> **优先级**：P1
> **涉及模块**：全局（通用组件）

---

## 一、任务概述

创建通用空状态与错误状态组件，统一各页面的空状态和错误状态展示。当前各页面分散使用 el-empty 和 el-result 展示空状态和错误状态，文案不统一、重试逻辑分散、视觉风格不一致。

**目标**：新建 EmptyState 组件（图标+标题+描述+可选操作按钮+slot）和 ErrorState 组件（图标+标题+错误详情+重试按钮+slot），并将各页面的 el-empty/el-result 替换为统一组件。

---

## 二、涉及模块

| 模块 | 路径 | 职责 |
|------|------|------|
| EmptyState | `src/components/common/EmptyState.vue` | 通用空状态（新建） |
| ErrorState | `src/components/common/ErrorState.vue` | 通用错误状态（新建） |
| SearchView | `src/views/SearchView.vue` | 替换 el-empty |
| ReportView | `src/views/ReportView.vue` | 替换 el-result |
| AgentFlowView | `src/views/AgentFlowView.vue` | 替换 el-empty + el-result |
| CompareView | `src/views/CompareView.vue` | 替换 el-empty |
| PaperDetailView | `src/views/PaperDetailView.vue` | 替换 el-result |
| FavoritesView | `src/views/FavoritesView.vue` | 替换 el-empty |

---

## 三、文件变更表

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| create | `Veritas/frontend/src/components/common/EmptyState.vue` | 新建空状态组件 |
| create | `Veritas/frontend/src/components/common/ErrorState.vue` | 新建错误状态组件 |
| modify | `Veritas/frontend/src/views/SearchView.vue` | 替换 el-empty |
| modify | `Veritas/frontend/src/views/ReportView.vue` | 替换 el-result |
| modify | `Veritas/frontend/src/views/AgentFlowView.vue` | 替换 el-empty + el-result |
| modify | `Veritas/frontend/src/views/CompareView.vue` | 替换 el-empty |
| modify | `Veritas/frontend/src/views/PaperDetailView.vue` | 替换 el-result |
| modify | `Veritas/frontend/src/views/FavoritesView.vue` | 替换 el-empty |

---

## 四、功能要求

| 编号 | 描述 | 优先级 |
|------|------|--------|
| FR-001 | EmptyState Props：icon/title/description/actionText + emit('action') + default slot | P0 |
| FR-002 | ErrorState Props：icon/title/description/retryText/showRetry + emit('retry') + default slot | P0 |
| FR-003 | EmptyState 视觉：居中布局、图标 48px、标题 16px 加粗、描述 14px 灰色 | P1 |
| FR-004 | ErrorState 视觉：居中布局、图标 48px warning、标题 16px 加粗、描述 14px 灰色 | P1 |
| FR-005 | SearchView 替换为 EmptyState | P0 |
| FR-006 | ReportView 替换为 ErrorState | P0 |
| FR-007 | AgentFlowView 替换为 EmptyState + ErrorState | P0 |
| FR-008 | CompareView 替换为 EmptyState | P0 |
| FR-009 | PaperDetailView 替换为 ErrorState | P0 |
| FR-010 | FavoritesView 替换为 EmptyState + 操作入口 | P0 |

---

## 五、关键技术约束

1. **纯展示组件**：EmptyState/ErrorState 不调用 API/Store，通过 emit 事件通知父组件
2. **CSS 变量**：使用 `var(--text-color-secondary)` 等 CSS 变量，禁止硬编码颜色
3. **slot 支持**：支持 default slot 自定义内容/操作按钮
4. **视觉统一**：图标尺寸 48px、标题 16px、描述 14px、居中布局
5. **全部替换**：所有页面的 el-empty/el-result 必须替换为统一组件

---

## 六、验收检查点

- [ ] AC-001：EmptyState 组件渲染正确（Props+事件+slot） — automated_test
- [ ] AC-002：ErrorState 组件渲染正确（Props+事件+slot） — automated_test
- [ ] AC-003：各页面空状态文案统一（使用 EmptyState） — manual_test
- [ ] AC-004：各页面错误状态有重试按钮（使用 ErrorState） — manual_test
- [ ] AC-005：SearchView/ReportView/AgentFlowView/CompareView/PaperDetailView/FavoritesView 全部替换 — code_review
- [ ] AC-006：视觉风格一致（图标/字号/颜色/间距统一） — manual_test
- [ ] AC-007：所有新增/修改的代码通过 lint 和 build 验证 — code_review

---

## 七、验证命令

```bash
cd Veritas/frontend && npm run test -- --run EmptyState ErrorState
cd Veritas/frontend && npm run lint
cd Veritas/frontend && npm run build
```

---

## 八、参考文档

- `AGENTS.md` — 项目全景上下文与前端约束
- `docs/frontend/前端模块系统架构文档.md` — 前端架构规范、组件设计规范
- `docs/frontend/前端模块项目里程碑文档.md` — FM5 里程碑任务分解（Week 11 Day 6）
- `docs/开发规范文档.md` — 前端编码规范、组件设计原则
- `docs/架构决策记录(ADR).md` — 架构决策
