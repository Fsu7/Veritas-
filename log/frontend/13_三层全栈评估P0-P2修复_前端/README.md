# 三层全栈评估 P0-P2 修复 — 前端

## 功能描述

### 解决了什么问题
基于《三层全栈综合技术评估报告-2026-06-18》指出的前端问题，系统性修复了以下阻断性与建议性缺陷：
- **P0-8 View 层直接调用 API**：`CompareView` 和 `ReportView` 绕过 Store 直接调用 `analysisApi`，违反 Pinia 架构规范
- **P0-9 View 层直接修改 Store State**：`SearchView` 直接赋值 `paperStore.sortBy = sort`，绕过 Action
- **P1-3 缺少 404 路由**：未匹配路由时无友好提示，显示空白页
- **P1-4 ReportView 时间字段错误**：`generatedAt` 引用错误字段，导致显示异常
- **P2-3 AgentFlowChart XSS 漏洞**：ECharts tooltip 中 `intermediateResult` 未转义，可能执行恶意脚本
- **P2-4 Agent 状态色硬编码**：状态颜色散落在组件内，无法统一管理

### 实现了什么功能
1. `sessionStore` 新增 `comparePapers`、`generateReport`、`saveReportContent` 三个 Action
2. `paperStore` 新增 `setSortBy` Action
3. `CompareView` 和 `ReportView` 改用 Store Action 调用 API
4. `SearchView` 排序改为调用 `paperStore.setSortBy(sort)`
5. 新建 `NotFoundView` 404 页面组件
6. 路由配置添加 catch-all 404 路由
7. `AgentFlowChart` 新增 `escapeHtml` 函数，tooltip 内容转义
8. 新建 `constants/agent.ts` 提取 Agent 状态色常量

### 业务价值
- 统一 API 调用入口到 Store Action，便于添加缓存、重试、错误处理等横切逻辑
- 封装 State 修改为 Action，保证状态变更可追踪、可测试
- 404 路由提升用户体验，避免空白页困惑
- XSS 防护避免恶意脚本注入
- 状态色常量统一管理，便于主题切换和一致性维护

## 实现逻辑

### 修改的核心文件列表
| 文件 | 修复项 | 变更说明 |
|------|--------|----------|
| `stores/sessionStore.ts` | P0-8 | 新增 `comparePapers`、`generateReport`、`saveReportContent` Action |
| `views/CompareView.vue` | P0-8 | 移除 `analysisApi` import，改用 `sessionStore.comparePapers/generateReport` |
| `views/ReportView.vue` | P0-8, P1-4 | 改用 `sessionStore.saveReportContent`；修复 `generatedAt` 字段引用 |
| `stores/paperStore.ts` | P0-9 | 新增 `setSortBy` Action |
| `views/SearchView.vue` | P0-9 | `handleSortChange` 改用 `paperStore.setSortBy`；`v-model` 改为 `:model-value` |
| `router/index.ts` | P1-3 | 添加 404 catch-all 路由 |
| `views/NotFoundView.vue` | P1-3 | 新建 404 页面组件 |
| `components/agent/AgentFlowChart.vue` | P2-3, P2-4 | 新增 `escapeHtml`；状态色改用常量 |
| `constants/agent.ts` | P2-4 | 新建，提取 `AGENT_STATUS_COLORS` 常量 |

### 使用的算法或设计模式
- **Action 委托模式**：View 不直接调用 API，委托给 Store Action 处理
- **单向数据流**：View → Action → State → View，状态变更必须经过 Action
- **常量提取模式**：魔法值（状态色）提取为常量模块，统一管理
- **HTML 转义防护**：用户内容注入 HTML 前必须转义

### 关键代码逻辑说明

#### P0-8 Store Action 封装
```typescript
// sessionStore.ts
async comparePapers(sessionId: string, paperIds: string[]) {
  const result = await analysisApi.comparePapers(sessionId, paperIds)
  return result.value
},
async generateReport(sessionId: string, paperIds: string[]) {
  const result = await analysisApi.generateReport(sessionId, paperIds)
  return result.value
}
```

#### P0-9 setSortBy Action
```typescript
// paperStore.ts
setSortBy(sort: string) {
  this.sortBy = sort
}
```

#### P2-3 XSS 防护
```typescript
// AgentFlowChart.vue
function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}
// tooltip 中使用
formatter: (params) => {
  const escaped = escapeHtml(data.intermediateResult || '')
  return `...${escaped}...`
}
```

#### P2-4 状态色常量
```typescript
// constants/agent.ts
export const AGENT_STATUS_COLORS = {
  waiting:   '#C0C4CC',
  running:   '#409EFF',
  completed: '#67C23A',
  failed:    '#F56C6C'
} as const
```

## 接口变更

### Request
本次修复未改变 API 请求契约，仅调整前端调用层级。

### Response
本次修复未改变 API 响应格式。

## 测试结果
- **TypeScript 类型检查**：`npm run typecheck` 全部通过
- **编译检查**：无类型错误、无未定义引用
- 是否通过：是

## 相关文件
- `Veritas/frontend/src/stores/sessionStore.ts`
- `Veritas/frontend/src/stores/paperStore.ts`
- `Veritas/frontend/src/views/CompareView.vue`
- `Veritas/frontend/src/views/ReportView.vue`
- `Veritas/frontend/src/views/SearchView.vue`
- `Veritas/frontend/src/views/NotFoundView.vue`（新建）
- `Veritas/frontend/src/router/index.ts`
- `Veritas/frontend/src/components/agent/AgentFlowChart.vue`
- `Veritas/frontend/src/constants/agent.ts`（新建）
- 评估报告：`log/阶段审阅报告/三层全栈综合技术评估报告-2026-06-18.md`
- 修复计划：`.trae/documents/全栈P0-P2问题修复计划-2026-06-18.md`
