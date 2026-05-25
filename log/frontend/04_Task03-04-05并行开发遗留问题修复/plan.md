# 修复计划：Task03/04/05 并行开发遗留问题

## 问题清单与修复方案

### 问题 #1：`api/index.ts` 循环依赖（P0）

**现状**：顶层 `import { useUserStore }` 和 `import router`，形成三方循环链：

```
api/index.ts → stores/userStore.ts → api/user.ts → api/index.ts
api/index.ts → router/index.ts → stores/userStore.ts → api/user.ts → api/index.ts
```

**修复方案**：

* 移除顶层 `import { useUserStore }` 和 `import router`

* 在请求拦截器回调内使用 `import('@/stores/userStore')` 动态导入 `useUserStore`

* 在401错误处理中使用 `import('@/router')` 动态导入 `router`

**修改文件**：`Veritas/frontend/src/api/index.ts`

**修改前**：

```typescript
import { useUserStore } from '@/stores/userStore'
import router from '@/router'
```

**修改后**：

```typescript
// 移除顶层导入，在拦截器回调内动态获取
```

拦截器内改为：

```typescript
http.interceptors.request.use(async (config) => {
  const { useUserStore } = await import('@/stores/userStore')
  const userStore = useUserStore()
  if (userStore.token) {
    config.headers.Authorization = `Bearer ${userStore.token}`
  }
  return config
})
```

401错误处理改为：

```typescript
if (error.response?.status === 401) {
  const { useUserStore } = await import('@/stores/userStore')
  const { default: router } = await import('@/router')
  const userStore = useUserStore()
  userStore.logout()
  router.push('/login')
  ElMessage.error('登录已过期，请重新登录')
}
```

> 注意：`request.use` 的回调签名需改为 `async`，Axios 原生支持拦截器返回 Promise。

***

### 问题 #2：`router/index.ts` 循环依赖（P0）

**现状**：顶层 `import { useUserStore }`，违反 task04 FA-004

**修复方案**：

* 移除顶层 `import { useUserStore }`

* 在 `beforeEach` 回调内动态导入

**修改文件**：`Veritas/frontend/src/router/index.ts`

**修改前**：

```typescript
import { useUserStore } from '@/stores/userStore'
```

**修改后**：

```typescript
// 移除顶层导入
```

守卫改为：

```typescript
router.beforeEach(async (to, _from, next) => {
  const { useUserStore } = await import('@/stores/userStore')
  const userStore = useUserStore()

  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if ((to.name === 'Login' || to.name === 'Register') && userStore.isLoggedIn) {
    next({ name: 'Home' })
  } else {
    next()
  }
})
```

***

### 问题 #3：`ProfileResponse` 类型与 `UserProfile` 不一致（P1）

**现状**：`ProfileResponse` 字段为 `string`，`UserProfile` 为枚举字面量，Store 中用 `as` 断言桥接

**修复方案**：

* 让 `ProfileResponse` 复用 `UserProfile` 的枚举类型

* 简化 Store 中的 `fetchProfile`/`saveProfile`，移除 `as` 断言

**修改文件**：

1. `Veritas/frontend/src/types/user.ts` — `ProfileResponse` 使用枚举类型
2. `Veritas/frontend/src/stores/userStore.ts` — 移除 `as` 断言

**types/user.ts 修改后**：

```typescript
export interface ProfileResponse {
  educationLevel: UserProfile['educationLevel']
  researchField: string
  knowledgeLevel: UserProfile['knowledgeLevel']
  preferredStyle: UserProfile['preferredStyle']
}
```

**userStore.ts 修改后**：`fetchProfile` 和 `saveProfile` 中直接赋值，无需 `as`：

```typescript
profile.value = res  // ProfileResponse 已与 UserProfile 兼容
```

但需注意 `ProfileResponse` 有 `researchField: string` 而 `UserProfile` 也是 `string`，其余三个字段类型现在一致，可以直接赋值。

***

### 问题 #4：`filteredResults` 占位符（P1）

**现状**：`filteredResults` 直接返回 `searchResults`，未根据 `filters` 过滤

**修复方案**：实现基于 `filters` 的前端过滤逻辑（年份范围、会议、最低引用数）

**修改文件**：`Veritas/frontend/src/stores/paperStore.ts`

**修改后**：

```typescript
const filteredResults = computed(() => {
  let results = searchResults.value
  const f = filters.value
  if (f.yearFrom) {
    results = results.filter(p => p.year >= f.yearFrom!)
  }
  if (f.yearTo) {
    results = results.filter(p => p.year <= f.yearTo!)
  }
  if (f.venue) {
    results = results.filter(p => p.venue?.toLowerCase().includes(f.venue!.toLowerCase()))
  }
  if (f.minCitations) {
    results = results.filter(p => (p.citationCount ?? 0) >= f.minCitations!)
  }
  if (f.sort === 'year') {
    results = [...results].sort((a, b) => b.year - a.year)
  } else if (f.sort === 'citations') {
    results = [...results].sort((a, b) => (b.citationCount ?? 0) - (a.citationCount ?? 0))
  }
  return results
})
```

***

### 问题 #5：`login` 未利用 `hasProfile` 自动获取画像（P1）

**现状**：登录后 `profile` 始终为 `null`，需手动调用 `fetchProfile`

**修复方案**：登录后若 `hasProfile === true`，自动调用 `fetchProfile`

**修改文件**：`Veritas/frontend/src/stores/userStore.ts`

**修改后**：

```typescript
async function login(user: string, password: string) {
  const res = await userApi.login({ username: user, password })
  persistLoginData(res)
  if (res.hasProfile) {
    await fetchProfile()
  }
}
```

***

## 执行顺序

| 步骤 | 修改文件                     | 对应问题                 | 优先级 |
| -- | ------------------------ | -------------------- | --- |
| 1  | `api/index.ts`           | #1 循环依赖              | P0  |
| 2  | `router/index.ts`        | #2 循环依赖              | P0  |
| 3  | `types/user.ts`          | #3 类型不一致             | P1  |
| 4  | `stores/userStore.ts`    | #3+#5 移除断言+自动获取画像    | P1  |
| 5  | `stores/paperStore.ts`   | #4 filteredResults实现 | P1  |
| 6  | 运行 `vue-tsc --noEmit` 验证 | 全部                   | —   |
| 7  | 运行 `npm run dev` 验证      | 全部                   | —   |

## 风险评估

* **动态 import 风险**：`await import()` 在拦截器中使用是安全的，Axios 原生支持异步拦截器。但需确保 Vite 构建时不会将动态导入的模块拆分到不合理的 chunk 中。

* **ProfileResponse 类型收紧风险**：如果后端实际返回的枚举值不在定义范围内，会导致类型不匹配。但这是后端契约问题，前端应按契约定义严格类型。

* **filteredResults 前端过滤**：当前搜索API已支持服务端过滤（`paperApi.search` 传递 `filters`），前端过滤是补充。如果搜索结果量不大，前端过滤是合理的。

