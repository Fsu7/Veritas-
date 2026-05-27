# Task14: HomeView完整实现（主题输入+历史搜索+检索触发）

## 任务概述

完善HomeView首页，从FM1骨架升级为完整功能实现：
- 主题输入框（el-input clearable + 回车/按钮触发检索）
- 历史搜索记录展示（最近10条，localStorage el-tag标签形式）
- 检索触发逻辑（paperStore.searchPapers() → router.push('/search')）
- 未登录用户可使用首页，检索时引导登录
- 搜索中loading状态 + 空状态处理

## 里程碑

FM2：用户界面与论文检索页面可用

## UI分析

| 维度 | 说明 |
|------|------|
| 页面类型 | 居中搜索入口型 |
| 用户目标 | 输入研究主题，快速开始检索 |
| 信息层级 | L1搜索框 → L2历史搜索标签 → L3系统名称/副标题 |
| 视觉重点 | 搜索输入框居中突出 |
| 数据密度 | 低（大量留白） |
| 核心CTA | [检索] |
| 布局 | 居中单列，搜索区max-width 600px |

## 涉及模块

| 模块 | 路径 | 复用方式 |
|------|------|---------|
| paperStore | `Veritas/frontend/src/stores/paperStore.ts` | 直接复用 — searchPapers(query, page?) |
| userStore | `Veritas/frontend/src/stores/userStore.ts` | 直接复用 — isLoggedIn |
| storage | `Veritas/frontend/src/utils/storage.ts` | 直接复用 — getRecentSearches/saveRecentSearch/clearRecentSearches |
| router | `Veritas/frontend/src/router/index.ts` | 直接复用 — /search路由(meta.requiresAuth:true) |
| paperApi | `Veritas/frontend/src/api/paper.ts` | 直接复用 — search方法 |

## 文件变更

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `Veritas/frontend/src/views/HomeView.vue` | 骨架→完整实现 |

## 功能要求

### FR-001: 搜索输入框 [P0]

- el-input, size="large", clearable, placeholder引导输入
- v-model绑定searchQuery
- 回车(@keyup.enter)和检索按钮均可触发搜索
- **el-input append插槽**整合检索按钮，视觉一体

**验收**: el-input clearable可清空，回车和按钮均可触发，输入框按钮视觉一体

### FR-002: 检索触发逻辑 [P0]

搜索流程（严格顺序）：

```
1. 校验 searchQuery.trim() 非空 → 空则return
2. 调用 saveRecentSearch(query) 保存历史
3. 刷新 recentSearches.value = getRecentSearches()
4. 检查 userStore.isLoggedIn
   ├── 未登录 → ElMessage.warning('请先登录') + router.push('/login') + return
   └── 已登录 → 继续
5. isSearching = true
6. await paperStore.searchPapers(query)
7. router.push({ name: 'Search', query: { q: query } })
8. catch → ElMessage.error('检索失败，请稍后重试')
9. finally → isSearching = false
```

**验收**: 空查询不触发，未登录跳转登录，已登录搜索成功跳转/search，失败有错误提示

### FR-003: 历史搜索展示 [P0]

- onMounted初始化: `recentSearches = ref<string[]>(getRecentSearches())`
- `v-if="recentSearches.length"` 条件渲染（为空不显示）
- el-tag展示，effect="plain"，size="small"，点击触发handleRecentClick
- 末尾"清除"按钮(el-button text size="small")，调用clearRecentSearches()
- 每次成功触发搜索后刷新recentSearches

**验收**: 空历史不显示区域，标签可点击快捷检索，清除按钮清空

### FR-004: Loading状态 [P0]

- isSearching ref(false)，搜索开始true，finally中false
- 检索按钮 `:loading="isSearching"` 显示旋转动画
- isSearching时 `el-input :disabled="isSearching"` 禁用输入

**验收**: 搜索中按钮loading旋转，输入框禁用，结束恢复

### FR-005: 页面布局与样式 [P0]

- 垂直水平居中，min-height:100vh flex布局
- 搜索区max-width:600px居中
- 标题h1 font-size:32px，color:var(--el-text-color-primary)
- 副标题font-size:14px，color:var(--el-color-info)
- 8px间距网格(8/12/16/24/32/48)
- BEM命名: home-view__content / home-view__search-box / home-view__title / home-view__subtitle / home-view__recent

**验收**: 居中布局，8px网格，CSS变量取色无硬编码

### FR-006: 未登录引导 [P0]

- 首页不需登录(meta.requiresAuth:false)可正常访问
- 检索时检查isLoggedIn，未登录ElMessage.warning + router.push('/login')
- 不阻止浏览和输入

**验收**: 未登录可访问首页，点击检索提示并跳转登录

## 数据流

```
HomeView → paperStore.searchPapers(query)
         → paperApi.search({q, page, size})
         → Java GET /api/papers/search
         → 返回 PageResponse<Paper>
         → paperStore.searchResults/totalResults 更新
         → router.push('/search')
         → SearchView 读取 paperStore.searchResults 展示
```

## 关键约束

| 约束 | 规则 |
|------|------|
| 组件语法 | `<script setup lang="ts">` + Composition API |
| 组件结构顺序 | imports → ref/reactive → computed → methods → onMounted |
| 样式 | `<style scoped lang="scss">` + BEM |
| 体积 | ≤300行 |
| API调用 | 通过paperStore.searchPapers()，禁止直接调axios/paperApi |
| 颜色 | CSS变量(var(--el-color-primary)等)，禁止硬编码 |
| 间距 | 8px倍数(4/8/12/16/24/32/48) |
| 三层架构 | 前端只调Java后端API，禁止直接调Python |

## 验收标准

| 编号 | 验收项 | 验证方式 |
|------|--------|---------|
| AC-001 | 搜索输入框clearable+回车+按钮触发，视觉整合 | 手动测试 |
| AC-002 | 完整检索流程（空查询/未登录/已登录/失败） | 手动测试 |
| AC-003 | 历史搜索展示、点击检索、清除、空状态 | 手动测试 |
| AC-004 | Loading状态正确切换 | 手动测试 |
| AC-005 | 未登录用户引导登录 | 手动测试 |
| AC-006 | 居中布局+8px间距+CSS变量 | 代码审查 |
| AC-007 | BEM CSS命名规范 | 代码审查 |
| AC-008 | 组件≤300行+script setup+scoped | 代码审查 |
| AC-009 | vue-tsc无错误+build成功 | 自动化测试 |
| AC-010 | 异步操作通过Store调用 | 代码审查 |
