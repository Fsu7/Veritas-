# 技术教学文档

## 开发思路

### 需求分析过程
本次开发涉及4个前端任务（Task14-17），均属于FM2里程碑「用户界面与论文检索页面可用」。核心目标是打通从首页搜索到论文结果展示的完整用户流程。

任务之间存在依赖关系：
- Task16（paperStore+usePagination）是基础设施层，Task14/15均依赖它
- Task14（HomeView完善）和Task15（SearchView+PaperCard）无相互依赖
- Task17（集成测试）必须等所有功能完成后执行

因此将执行顺序调整为：**Task16 → Task14 → Task15 → Task17**，而非按编号顺序执行。

### 技术选型考虑
1. **usePagination采用callback模式**：composable不硬编码数据加载逻辑（不直接调Store），而是通过callback参数让调用方决定如何加载数据。这样同一个composable可复用于不同场景
2. **toggleFavorite采用乐观更新模式**：先更新UI状态，API失败时回滚。用户体验优于等待API响应后再更新
3. **el-input append插槽整合检索按钮**：Element Plus的append插槽实现输入框与按钮视觉一体，比el-input-group更简洁

### 架构设计思路
遵循 View → Store → API 三层分离：
- HomeView调用paperStore.searchPapers()，不直接调paperApi
- SearchView通过paperStore读取searchResults，不直接调paperApi
- PaperCard是纯展示组件，通过emit上报事件，父组件处理业务逻辑

### 遇到的问题及解决方案
1. **问题**：原HomeView直接router.push跳转，SearchView无数据可展示
   **解决**：HomeView在跳转前先调用paperStore.searchPapers()，Store作为数据中转站
2. **问题**：vue-tsc报unused variable错误（totalPages解构后未使用）
   **解决**：从解构中移除未使用的变量
3. **问题**：测试中mock函数返回类型不匹配（addFavorite返回void但mockResolvedValue(undefined)类型报错）
   **解决**：使用`mockResolvedValue({} as never)`绕过类型检查

## 实现步骤

1. **Task16 - paperStore完善**：新增loading/error状态、hasResults/totalPages计算属性、clearSelection/fetchFavorites/updateFilters/resetSearch四个action，searchPapers增加try-catch-finally，toggleFavorite增加乐观更新+回滚，移除filteredResults
2. **Task16 - usePagination创建**：纯逻辑composable，currentPage/pageSize/totalPages/handleCurrentChange/handleSizeChange/resetPage，callback参数解耦
3. **Task14 - HomeView完善**：el-input append插槽整合检索按钮、isSearching loading状态、paperStore.searchPapers()调用、CSS变量替代硬编码颜色、副标题、max-width:600px
4. **Task15 - PaperCard创建**：Props/Emits类型化、truncateText/formatMeta/formatScore工具函数、BEM命名、CSS变量
5. **Task15 - SearchView重写**：搜索栏+结果统计+PaperCard列表+分页+Loading/Empty/Error三态、route.query.q初始化+watch
6. **Task17 - 集成测试**：创建5个测试文件共60个测试用例，修复tsconfig.json添加vitest/globals类型

## 解决了什么问题

### 核心问题描述
FM1里程碑交付的HomeView是基础骨架（缺少loading/paperStore调用/el-input整合），SearchView是空占位符，paperStore缺少loading/error状态管理。用户无法完成完整的搜索→查看结果流程。

### 解决方案对比
| 方案 | 描述 | 优缺点 |
|------|------|--------|
| A: SearchView自行搜索 | 跳转后由SearchView触发searchPapers | ❌ HomeView无法预加载，跳转后白屏等待 |
| B: HomeView预搜索后跳转 | 跳转前调searchPapers，Store缓存结果 | ✅ 跳转后数据已就绪，体验流畅 |
| C: URL传参+SearchView监听 | 仅传query参数，SearchView自行加载 | ❌ 与B类似但更复杂，需额外watch |

最终选择方案B：HomeView预搜索后跳转，Store作为数据中转站。

### 最终方案的优势
- 跳转后数据已就绪，无白屏等待
- Store缓存searchResults/totalResults/currentQuery，SearchView直接读取
- 路由query参数保留搜索词，支持刷新页面重新搜索

## 变更内容

### 新增文件
- `Veritas/frontend/src/composables/usePagination.ts` — 通用分页composable
- `Veritas/frontend/src/components/paper/PaperCard.vue` — 论文卡片展示组件
- `Veritas/frontend/src/__tests__/stores/paperStore.spec.ts` — paperStore测试（16个用例）
- `Veritas/frontend/src/__tests__/composables/usePagination.spec.ts` — usePagination测试（9个用例）
- `Veritas/frontend/src/__tests__/components/paper/PaperCard.spec.ts` — PaperCard测试（16个用例）
- `Veritas/frontend/src/__tests__/views/SearchView.spec.ts` — SearchView测试（4个用例）

### 修改文件
- `Veritas/frontend/src/stores/paperStore.ts` — 新增loading/error/新actions/移除filteredResults/toggleFavorite回滚
- `Veritas/frontend/src/views/HomeView.vue` — el-input append整合/loading/paperStore.searchPapers/CSS变量/副标题
- `Veritas/frontend/src/views/SearchView.vue` — 从占位符重写为完整搜索结果页
- `Veritas/frontend/src/__tests__/views/HomeView.spec.ts` — 更新测试适配新实现
- `Veritas/frontend/tsconfig.json` — 添加"vitest/globals"到types数组

### 配置变更
- tsconfig.json: `"types": ["vite/client"]` → `"types": ["vite/client", "vitest/globals"]`

## 关键技术点

### 1. Pinia Setup Store的loading/error管理模式
```typescript
async function searchPapers(query: string, page: number = 1) {
  loading.value = true
  error.value = null
  try {
    const res = await paperApi.search({...})
    searchResults.value = res.items
    totalResults.value = res.total
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '搜索失败'
  } finally {
    loading.value = false
  }
}
```
关键：finally确保loading始终重置，catch中error赋值供UI展示。

### 2. 乐观更新+回滚模式
```typescript
async function toggleFavorite(paperId: string) {
  const wasFavorited = favorites.value.includes(paperId)
  // 先更新状态（乐观）
  if (wasFavorited) favorites.value = favorites.value.filter(...)
  else favorites.value.push(paperId)
  try {
    await paperApi.addFavorite(paperId) // 或 removeFavorite
  } catch {
    // API失败，回滚状态
    if (wasFavorited) favorites.value.push(paperId)
    else favorites.value = favorites.value.filter(...)
    throw new Error('收藏操作失败')
  }
}
```

### 3. Composable callback解耦模式
```typescript
function handleCurrentChange(page: number, callback: (page: number) => Promise<void>) {
  currentPage.value = page
  callback(page) // 由调用方决定如何加载数据
}
```
usePagination不依赖任何Store，可在任何需要分页的场景复用。

### 4. el-input append插槽实现搜索框一体式设计
```html
<el-input v-model="searchQuery" size="large" clearable :disabled="isSearching">
  <template #append>
    <el-button type="primary" :loading="isSearching" @click="handleSearch">检索</el-button>
  </template>
</el-input>
```

### 5. SearchView三态互斥渲染
```html
<div v-if="hasError">Error结果</div>
<div v-else-if="hasSearched && !loading && !results.length">Empty空状态</div>
<template v-else>Results列表 + Pagination</template>
```
优先级：Error > Empty > Results，确保用户始终看到正确的状态。

## 经验总结

### 开发过程中的收获
1. **依赖分析的重要性**：按依赖顺序执行（Task16→14→15→17）比按编号顺序效率高很多，避免了返工
2. **Store作为数据中转站**：HomeView预搜索→Store缓存→SearchView读取，比纯URL传参更灵活
3. **composable设计原则**：纯逻辑+callback参数，不硬编码业务依赖，才能实现真正的复用

### 踩过的坑及如何避免
1. **vue-tsc对unused变量的严格检查**：解构赋值时只取需要的字段，避免`noUnusedLocals`报错
2. **Vitest全局类型（vi.fn/describe/it）**：tsconfig.json需要添加`"vitest/globals"`到types数组，否则测试文件中的全局API类型检查失败
3. **mock函数返回类型**：`mockResolvedValue(undefined)`对void返回类型的API可能类型不匹配，用`{} as never`更安全
4. **el-input append插槽中el-button type=primary**：Element Plus默认append区域有灰色背景，primary按钮在其中可能视觉不够突出，可能需要额外CSS覆盖

### 最佳实践建议
1. **所有异步操作必须有loading/error/empty三态处理** — 这是交互完整性的底线
2. **乐观更新适合收藏/点赞等高频操作** — 但必须配套回滚逻辑
3. **组件测试优先测试渲染和事件触发** — 深度逻辑测试放在Store测试中
4. **8px间距网格** — 使用CSS变量（如var(--spacing-md)）而非硬编码像素值，保持全局一致性
5. **BEM命名** — block__element--modifier模式，避免样式冲突和命名混乱
