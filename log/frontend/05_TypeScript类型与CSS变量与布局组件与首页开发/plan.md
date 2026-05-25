# Task 06-09 前端实施计划

## 当前状态分析

所有4个任务涉及的文件均已存在（由task00-05创建的骨架），但内容**不完整**，需要按照prompt.json规范补全。

### 文件现状对照表

| 文件 | 当前状态 | 需要的操作 |
|------|---------|-----------|
| `types/common.ts` | ✅ 完整 | 补充JSDoc注释 |
| `types/paper.ts` | ✅ 完整 | 补充JSDoc注释 |
| `types/user.ts` | ✅ 完整 | 补充JSDoc注释 |
| `types/analysis.ts` | ⚠️ 部分问题 | 修复AgentStateInfo→导入AgentState，补充JSDoc |
| `types/agent.ts` | ✅ 完整 | 补充JSDoc注释 |
| `styles/variables.scss` | ⚠️ 缺5类变量 | 补充间距/圆角/阴影/字体/过渡变量 |
| `styles/global.scss` | ⚠️ 缺大量内容 | 补充导入、工具类、EP定制、AI标注 |
| `components/layout/AppHeader.vue` | ⚠️ 基本完整 | 微调优化 |
| `components/layout/AppFooter.vue` | ⚠️ 不完整 | 补充版本号、AI标注、BEM结构 |
| `views/HomeView.vue` | ⚠️ 不完整 | 补充登录检查、LocalStorage、AppHeader/Footer集成 |
| `utils/storage.ts` | ❌ 不存在 | 新建 |

---

## Task 06: TypeScript类型定义

### 步骤6.1: 修复 `types/analysis.ts`

**问题**: `AgentStateInfo` 使用 `status: string` 而非正确的联合类型，且未从 `agent.ts` 导入 `AgentState`

**操作**:
- 删除 `AgentStateInfo` 接口
- 将 `AnalysisResult.agentStates` 类型改为 `AgentState[]`（从 `agent.ts` 导入）
- 为所有6个interface添加JSDoc注释（标注JSON snake_case映射）

### 步骤6.2: 为所有类型文件添加JSDoc注释

**操作**: 为以下文件中每个interface和关键字段添加JSDoc，标注 `@field camelCase ↔ snake_case` 映射关系：
- `types/common.ts`
- `types/paper.ts`
- `types/user.ts`
- `types/analysis.ts`
- `types/agent.ts`

---

## Task 07: 全局样式与CSS变量

### 步骤7.1: 补全 `styles/variables.scss`

**当前**: 仅3类变量（主色/Agent状态/布局）

**需补充5类**:
```scss
// 间距变量
--spacing-xs: 4px; --spacing-sm: 8px; --spacing-md: 16px;
--spacing-lg: 24px; --spacing-xl: 32px;

// 圆角变量
--radius-sm: 4px; --radius-md: 8px; --radius-lg: 12px;

// 阴影变量
--shadow-sm: 0 2px 4px rgba(0,0,0,0.08);
--shadow-md: 0 4px 12px rgba(0,0,0,0.1);
--shadow-lg: 0 8px 24px rgba(0,0,0,0.12);

// 字体变量
--font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', ...;
--font-size-sm: 12px; --font-size-base: 14px;
--font-size-lg: 16px; --font-size-xl: 20px; --font-size-xxl: 24px;

// 过渡变量
--transition-fast: 0.15s ease; --transition-normal: 0.3s ease;
```

### 步骤7.2: 重写 `styles/global.scss`

**当前**: 仅基础重置 + `.app-container` / `.app-main`

**需补充**:
1. 导入 `variables.scss`（`@use './variables' as *`）
2. body样式使用CSS变量（`font-family: var(--font-family)` 等）
3. 通用工具类：`.text-ellipsis` / `.flex-center` / `.page-container` / `.section-title`
4. Element Plus组件定制：`.el-card` / `.el-button` / `.el-tag`
5. AI内容标注：`.ai-generated-label`
6. 保留现有的 `.app-container` / `.app-main`

### 步骤7.3: 验证 `main.ts` 和 `vite.config.ts`

**当前**: 已正确配置 ✅
- `main.ts` 已有 `import './styles/global.scss'`
- `vite.config.ts` 已有 `additionalData: '@use "@/styles/variables.scss" as *;'`

---

## Task 08: 布局组件

### 步骤8.1: 微调 `AppHeader.vue`

**当前**: 基本完整，已包含所有功能

**需调整**:
- 退出按钮class改为 `app-header__logout`（BEM规范）
- 优化细节确认

### 步骤8.2: 重写 `AppFooter.vue`

**当前**: 仅1行版权信息，缺少版本号和AI标注

**需实现**:
```html
<el-footer class="app-footer" height="auto">
  <div class="app-footer__content">
    <p class="app-footer__info">XH-202630 科研文献智能助手</p>
    <p class="app-footer__info">v0.1</p>
    <p class="app-footer__ai-label ai-generated-label">AI生成内容仅供参考</p>
  </div>
</el-footer>
```
- 背景色 `#f5f7fa`，上边框 `1px solid #e4e7ed`
- 居中对齐，BEM命名

---

## Task 09: 首页与集成测试

### 步骤9.1: 创建 `utils/storage.ts`

**需实现**:
```typescript
RECENT_SEARCHES_KEY = 'recent_searches'
getRecentSearches(): string[]
saveRecentSearch(query: string): void  // 去重+头部插入+最多10条
clearRecentSearches(): void
```

### 步骤9.2: 重写 `views/HomeView.vue`

**当前**: 缺少登录检查、LocalStorage持久化、AppHeader/Footer集成

**需实现**:
1. 导入 `useUserStore`、`storage.ts`
2. `recentSearches` 使用 `getRecentSearches()` 初始化
3. `handleSearch`: 校验非空 → `saveRecentSearch()` → 判断登录 → 跳转/提示
4. 未登录：`ElMessage.warning('请先登录')` + `router.push('/login')`
5. 集成 `AppHeader` 和 `AppFooter`
6. `clearRecentSearches` 方法
7. 样式使用CSS变量

### 步骤9.3: 确认路由配置

**当前**: `router/index.ts` 已有 `{ path: '/', name: 'Home', component: HomeView }` ✅

### 步骤9.4: 编写集成测试

**测试文件**: `tests/views/HomeView.spec.ts`

**测试用例**:
1. 首页正确渲染AppHeader和AppFooter
2. 搜索输入框存在且可输入
3. 回车触发检索跳转（已登录→/search?q=xxx）
4. 未登录点击检索提示登录
5. 最近搜索标签正确显示和点击
6. 清除历史功能正确

### 步骤9.5: 编写storage工具测试

**测试文件**: `tests/utils/storage.spec.ts`

**测试用例**:
1. `getRecentSearches` 正确读取
2. `saveRecentSearch` 去重、头部插入、10条限制
3. `clearRecentSearches` 正确清除

---

## 执行顺序

```
Task 06 (types) → Task 07 (styles) → Task 08 (layout) → Task 09 (home + tests)
```

自底向上：类型定义 → 样式基础 → 布局组件 → 页面 + 测试

## 验证步骤

每完成一个Task后运行：
```bash
cd Veritas/frontend && npx vue-tsc --noEmit   # TypeScript编译检查
cd Veritas/frontend && npm run build           # 构建检查
```

全部完成后运行：
```bash
cd Veritas/frontend && npm run test            # 测试检查
cd Veritas/frontend && npm run dev             # 开发服务器启动
```

## 变更文件清单

| 操作 | 文件路径 | Task |
|------|---------|------|
| 修改 | `src/types/analysis.ts` | 06 |
| 修改 | `src/types/common.ts` | 06 |
| 修改 | `src/types/paper.ts` | 06 |
| 修改 | `src/types/user.ts` | 06 |
| 修改 | `src/types/agent.ts` | 06 |
| 修改 | `src/styles/variables.scss` | 07 |
| 重写 | `src/styles/global.scss` | 07 |
| 微调 | `src/components/layout/AppHeader.vue` | 08 |
| 重写 | `src/components/layout/AppFooter.vue` | 08 |
| 新建 | `src/utils/storage.ts` | 09 |
| 重写 | `src/views/HomeView.vue` | 09 |
| 新建 | `tests/utils/storage.spec.ts` | 09 |
| 新建 | `tests/views/HomeView.spec.ts` | 09 |
