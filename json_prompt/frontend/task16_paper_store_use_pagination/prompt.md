# Task16: paperStore完整实现 + usePagination组合函数

## 任务概述

完善 `paperStore.ts` 为完整的论文数据 Pinia Store，新增 loading/error 状态管理、计算属性、缺失的 Actions；同时创建 `usePagination.ts` 通用分页组合函数。

| 项目 | 内容 |
|------|------|
| **任务编号** | task16_paper_store_use_pagination |
| **版本** | v0.2 |
| **里程碑** | FM2：用户界面与论文检索页面可用 |
| **功能编号** | F1.2.1, F1.2.2, F1.2.3 |

## 文件变更

| 操作 | 文件 | 说明 |
|------|------|------|
| **modify** | `Veritas/frontend/src/stores/paperStore.ts` | 完善Store：新增state/getters/actions，移除filteredResults |
| **create** | `Veritas/frontend/src/composables/usePagination.ts` | 新增通用分页组合函数 |

## paperStore State（10个）

| 字段 | 类型 | 默认值 | 状态 |
|------|------|--------|------|
| searchResults | Paper[] | [] | ✅已有 |
| selectedPapers | Paper[] | [] | ✅已有 |
| favorites | string[] | [] | ✅已有 |
| filters | FilterParams | {} | ✅已有 |
| currentQuery | string | '' | ✅已有 |
| totalResults | number | 0 | ✅已有 |
| currentPage | number | 1 | ✅已有 |
| pageSize | number | 10 | ✅已有 |
| **loading** | boolean | false | 🆕新增 |
| **error** | string\|null | null | 🆕新增 |

## paperStore Getters（3个）

| 名称 | 说明 | 状态 |
|------|------|------|
| selectedPaperIds | selectedPapers.map(p => p.paperId) | ✅已有 |
| **hasResults** | searchResults.length > 0 | 🆕新增 |
| **totalPages** | Math.ceil(totalResults / pageSize) \|\| 1 | 🆕新增 |
| ~~filteredResults~~ | ~~客户端过滤排序~~ | ❌**移除** |

## paperStore Actions（7个）

| 名称 | 说明 | 状态 |
|------|------|------|
| searchPapers | 搜索论文，**增加loading/error管理** | 🔧完善 |
| togglePaperSelection | 切换论文选择（≤5篇） | ✅已有 |
| **clearSelection** | 清空已选论文 | 🆕新增 |
| toggleFavorite | 切换收藏状态 | ✅已有 |
| **fetchFavorites** | 获取收藏列表（占位实现） | 🆕新增 |
| **updateFilters** | 更新筛选参数并重新搜索 | 🆕新增 |
| **resetSearch** | 重置搜索状态 | 🆕新增 |

## usePagination 签名

```typescript
function usePagination(
  total: Ref<number>,
  defaultPageSize?: number
): {
  currentPage: Ref<number>
  totalPages: ComputedRef<number>
  pageSize: Ref<number>
  handleCurrentChange: (callback: (page: number) => void) => (page: number) => void
  handleSizeChange: (callback: (size: number) => void) => (size: number) => void
  resetPage: () => void
}
```

## 关键约束

1. **Pinia setup store风格**
2. **usePagination不依赖任何Store**（仅 import { ref, computed } from 'vue'）
3. **异步操作在Store Actions中**
4. **API通过paperApi调用**
5. **fetchFavorites占位实现**，不调用不存在的API
6. **单文件≤300行**

## 验证命令

```bash
cd Veritas/frontend && npx vue-tsc --noEmit
cd Veritas/frontend && npx vitest run src/stores/paperStore.ts src/composables/usePagination.ts
```

## 验收标准

| 编号 | 标准 | 验证方式 |
|------|------|---------|
| AC-001 | paperStore包含10个state字段 | 代码审查 |
| AC-002 | paperStore包含3个getter（无filteredResults） | 代码审查 |
| AC-003 | paperStore包含7个action | 代码审查 |
| AC-004 | searchPapers loading/error状态正确 | 自动测试 |
| AC-005 | togglePaperSelection最多5篇 | 自动测试 |
| AC-006 | updateFilters合并参数并触发搜索 | 自动测试 |
| AC-007 | resetSearch重置搜索状态但不清空selectedPapers/favorites | 自动测试 |
| AC-008 | usePagination不依赖Store | 代码审查 |
| AC-009 | handleCurrentChange/handleSizeChange通过callback解耦 | 自动测试 |
| AC-010 | TypeScript编译通过，文件≤300行 | 自动测试 |
| AC-011 | fetchFavorites为占位实现 | 代码审查 |
