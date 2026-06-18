# 技术教学文档 — 前端 P0-P2 修复

## 开发思路

### 需求分析过程
本次修复源于《三层全栈综合技术评估报告》对前端的全面审查。评估识别出 6 项问题（P0×2、P1×2、P2×2），涵盖架构规范、用户体验、安全防护三个维度。

分析优先级：
1. **架构规范优先**：P0-8/9 违反 Pinia 单向数据流原则，是架构性缺陷
2. **用户体验次之**：P1-3/4 影响用户感知
3. **安全防护**：P2-3 XSS 是安全漏洞
4. **代码质量**：P2-4 常量提取提升可维护性

### 技术选型考虑

#### P0-8/9 架构修复方案对比
| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| View → Store Action → API | 符合 Pinia 规范、可测试 | 需编写 Action | ✅ |
| View → API（原方案） | 代码少 | 不可测试、无横切逻辑 | ❌ |
| View → Composable → API | 灵活 | 与项目 Pinia 架构不一致 | ❌ |

#### P2-3 XSS 防护方案对比
| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| 手动 `escapeHtml` | 简单直接 | 需手动调用 | ✅ |
| DOMPurify 库 | 最安全 | 引入额外依赖 | ❌（过度设计） |
| ECharts `encodeHTML` | ECharts 内置 | 仅限 ECharts 内部 | ❌（不够通用） |

### 架构设计思路
- **Pinia 单向数据流**：View → Action → State → View，所有状态变更必须经过 Action
- **API 调用集中化**：API 调用封装在 Store Action 中，View 不直接调用 API
- **常量模块化**：魔法值提取为独立常量模块，便于统一管理和主题切换
- **防御性编程**：用户内容注入 HTML 前必须转义

### 遇到的问题及解决方案

#### 问题1：CompareView 移除 analysisApi 后 linter 报错
- **现象**：移除 `analysisApi` import 后，第 72 行和 104 行找不到 `analysisApi`
- **原因**：代码中仍直接调用 `analysisApi.comparePapers(...)` 和 `analysisApi.generateReport(...)`
- **解决**：将调用改为 `sessionStore.comparePapers(...)` 和 `sessionStore.generateReport(...)`

#### 问题2：AgentFlowChart 状态色类型不匹配
- **现象**：`STATUS_COLORS = AGENT_STATUS_COLORS` 导致索引类型不匹配
- **原因**：`AGENT_STATUS_COLORS` 是 `as const` 断言的字面量类型，与 `Record<string, string>` 不兼容
- **解决**：添加类型注解 `const STATUS_COLORS: Record<string, string> = AGENT_STATUS_COLORS`

#### 问题3：escapeHtml 函数未定义
- **现象**：tooltip 中使用 `escapeHtml` 但函数未定义
- **原因**：新增了 `escapeHtml` 调用但忘记定义函数
- **解决**：在 `formatDuration` 函数后添加 `escapeHtml` 函数定义

## 实现步骤

### 1. P0-8 View 层 API 调用迁移（sessionStore + CompareView + ReportView）
1. 在 `sessionStore` 新增三个 Action：
   - `comparePapers(sessionId, paperIds)`：调用 `analysisApi.comparePapers`
   - `generateReport(sessionId, paperIds)`：调用 `analysisApi.generateReport`
   - `saveReportContent(sessionId, content)`：调用 `analysisApi.saveReport`
2. `CompareView` 移除 `analysisApi` import，改用 `sessionStore.comparePapers/generateReport`
3. `ReportView` 移除 `analysisApi` import，改用 `sessionStore.saveReportContent`

### 2. P0-9 View 层 State 修改封装（paperStore + SearchView）
1. `paperStore` 新增 `setSortBy(sort: string)` Action
2. `SearchView` 的 `handleSortChange` 改为调用 `paperStore.setSortBy(sort)`
3. `v-model="paperStore.sortBy"` 改为 `:model-value="paperStore.sortBy"`（避免直接修改）

### 3. P1-3 404 路由（router + NotFoundView）
1. 新建 `NotFoundView.vue` 组件，包含友好提示和返回首页按钮
2. `router/index.ts` 在路由表末尾添加 catch-all 路由：
   ```typescript
   { path: '/:pathMatch(.*)*', name: 'NotFound', component: () => import('@/views/NotFoundView.vue') }
   ```

### 4. P1-4 ReportView 时间字段修复
- `generatedAt` 原引用 `result.createdAt`（API 响应外层）
- 修正为 `result.value.createdAt`（API 响应 data 字段内）

### 5. P2-3 XSS 防护（AgentFlowChart）
1. 新增 `escapeHtml` 函数，转义 `& < > " '` 五个字符
2. ECharts tooltip formatter 中对 `intermediateResult` 调用 `escapeHtml`

### 6. P2-4 状态色常量提取（constants/agent.ts + AgentFlowChart）
1. 新建 `constants/agent.ts`，定义 `AGENT_STATUS_COLORS` 常量
2. `AgentFlowChart` 的 `STATUS_COLORS` 改为引用 `AGENT_STATUS_COLORS`

## 解决了什么问题

### 核心问题描述
1. **架构违规**：View 层直接调用 API 和修改 State，绕过 Store，无法添加缓存、重试等横切逻辑
2. **404 空白页**：未匹配路由时显示空白页，用户体验差
3. **XSS 漏洞**：Agent 中间结果未转义直接注入 ECharts tooltip，可能执行恶意脚本
4. **魔法值散落**：状态颜色硬编码在组件内，无法统一管理

### 解决方案对比
- 架构修复：Store Action vs View 直接调用（Action 符合 Pinia 规范）
- XSS 防护：手动转义 vs DOMPurify（手动转义足够，无需引入依赖）
- 常量管理：独立模块 vs 组件内常量（独立模块便于复用和主题切换）

### 最终方案的优势
- 架构合规：所有 API 调用和状态变更经过 Store Action
- 安全性：XSS 转义防止恶意脚本注入
- 可维护性：状态色常量统一管理
- 用户体验：404 页面提供友好提示

## 变更内容

### 新增文件
| 文件 | 作用 |
|------|------|
| `views/NotFoundView.vue` | 404 页面组件 |
| `constants/agent.ts` | Agent 状态色常量 |

### 修改文件
| 文件 | 变更点 |
|------|--------|
| `stores/sessionStore.ts` | 新增 `comparePapers`、`generateReport`、`saveReportContent` Action |
| `stores/paperStore.ts` | 新增 `setSortBy` Action |
| `views/CompareView.vue` | 移除 `analysisApi`，改用 Store Action |
| `views/ReportView.vue` | 移除 `analysisApi`，改用 Store Action；修复 `generatedAt` |
| `views/SearchView.vue` | `handleSortChange` 改用 `setSortBy`；`v-model` 改为 `:model-value` |
| `router/index.ts` | 添加 404 catch-all 路由 |
| `components/agent/AgentFlowChart.vue` | 新增 `escapeHtml`；状态色改用常量 |

### 配置变更
无配置文件变更。

## 关键技术点

### 1. Pinia 单向数据流
```
View (用户操作) → Action (异步/同步逻辑) → State (状态变更) → View (UI 更新)
```
- **View 不直接调用 API**：API 调用封装在 Action 中
- **View 不直接修改 State**：State 修改封装在 Action 中
- **好处**：可测试、可追踪、可添加横切逻辑（缓存、重试、日志）

### 2. v-model vs :model-value
```vue
<!-- ❌ 直接修改 Store State（绕过 Action） -->
<el-select v-model="paperStore.sortBy">

<!-- ✅ 通过 Action 修改 -->
<el-select :model-value="paperStore.sortBy" @change="handleSortChange">
```
- `v-model` 会直接赋值 State，绕过 Action
- `:model-value` + `@change` 通过事件触发 Action

### 3. HTML 转义防护
```typescript
function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')   // 必须最先转义
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}
```
- **转义顺序**：`&` 必须最先转义，否则后续转义的 `&` 会被二次转义
- **五个字符**：`& < > " '` 覆盖 HTML 注入的主要向量

### 4. 404 catch-all 路由
```typescript
{ path: '/:pathMatch(.*)*', name: 'NotFound', component: () => import('@/views/NotFoundView.vue') }
```
- `:pathMatch(.*)*` 匹配任意路径（包括多级）
- 必须放在路由表末尾，否则会拦截其他路由
- 使用懒加载 `() => import(...)` 减少初始 bundle 大小

### 5. as const 与类型兼容
```typescript
// constants/agent.ts
export const AGENT_STATUS_COLORS = {
  waiting: '#C0C4CC',
  running: '#409EFF'
} as const  // 类型为 { readonly waiting: "#C0C4CC"; readonly running: "#409EFF" }

// AgentFlowChart.vue
const STATUS_COLORS: Record<string, string> = AGENT_STATUS_COLORS
// 需要显式类型注解，否则字面量类型与 Record<string, string> 不兼容
```

## 经验总结

### 开发过程中的收获
1. **Pinia 架构规范**：View 层不应直接调用 API 或修改 State，必须通过 Action
2. **v-model 的陷阱**：`v-model` 在 Store State 上会绕过 Action，需用 `:model-value` + `@change`
3. **XSS 防护**：任何用户内容注入 HTML 前必须转义，即使是 ECharts tooltip
4. **常量管理**：魔法值应提取为独立模块，便于统一管理和主题切换

### 踩过的坑及如何避免
1. **移除 import 后未更新调用点**：移除 `analysisApi` import 后，代码中仍有 `analysisApi.xxx()` 调用。**避免方式**：移除 import 后全局搜索该符号，确保所有调用点同步更新
2. **`as const` 类型不兼容**：`AGENT_STATUS_COLORS` 用 `as const` 后是字面量类型，与 `Record<string, string>` 不兼容。**避免方式**：添加显式类型注解 `Record<string, string>`
3. **escapeHtml 忘记定义**：tooltip 中调用了 `escapeHtml` 但函数未定义。**避免方式**：新增函数调用时同步定义函数，或用 TypeScript 类型检查捕获

### 最佳实践建议
1. **View 层不直接调用 API**：所有 API 调用封装在 Store Action 中
2. **View 层不直接修改 State**：用 `:model-value` + `@change` 替代 `v-model`
3. **用户内容注入 HTML 前必须转义**：即使是 ECharts tooltip
4. **魔法值提取为常量模块**：颜色、枚举等提取为独立 `constants/` 模块
5. **路由表末尾放 catch-all**：404 路由必须放在最后
6. **`as const` 配合显式类型注解**：避免字面量类型与通用类型不兼容
