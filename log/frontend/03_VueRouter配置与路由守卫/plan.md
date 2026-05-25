# Task04: Vue Router 配置、路由守卫与路由定义 — 实施计划

## 当前状态分析

### 已有文件
| 文件 | 状态 | 说明 |
|------|------|------|
| `Veritas/frontend/src/router/index.ts` | ✅ 已存在 | 9条路由已定义，守卫使用 `localStorage` 直接读取 |
| `Veritas/frontend/src/main.ts` | ✅ 已注册 | `app.use(router)` 已在 `app.mount('#app')` 之前 |
| `Veritas/frontend/src/stores/userStore.ts` | ✅ 已存在 | `isLoggedIn` computed 已定义 |
| `Veritas/frontend/src/api/index.ts` | ✅ 已存在 | 401拦截器已引用 `router` |
| 9个 View 组件 | ✅ 已存在 | 懒加载目标文件齐全 |

### 需要修复的问题

1. **守卫认证方式不规范** — 当前守卫直接读 `localStorage.getItem('token')`，应改为函数式获取 `useUserStore()`，保持单一数据源（userStore.isLoggedIn）
2. **缺少 RouteMeta 类型扩展** — `meta.requiresAuth` 无 TypeScript 类型安全，需扩展 `vue-router` 的 `RouteMeta` 接口
3. **潜在循环依赖风险** — `api/index.ts` 导入了 `router`，如果 `router/index.ts` 又在模块顶层导入 `useUserStore`，可能形成循环。**必须在守卫回调内函数式获取 Store**

### 与架构文档的差异

前端架构文档第11.1节的参考代码在模块顶层 `import { useUserStore }`，但 **prompt.json FA-004 明确禁止在守卫外导入 userStore 导致循环依赖**。正确做法：在 `beforeEach` 回调内部调用 `useUserStore()`。

---

## 实施步骤

### Step 1: 扩展 RouteMeta 类型定义

**文件**: `Veritas/frontend/src/router/index.ts`（在路由定义之前）

添加 TypeScript 类型扩展，使 `meta.requiresAuth` 获得类型提示：

```typescript
declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
  }
}
```

### Step 2: 重写 router/index.ts

**文件**: `Veritas/frontend/src/router/index.ts`

完整重写，包含：
1. `RouteMeta` 类型扩展
2. 9条路由定义（全部懒加载，与现有完全一致）
3. `createWebHistory` 模式
4. 全局前置守卫 — **在回调内函数式获取 `useUserStore()`**

关键守卫逻辑：
```
beforeEach((to, _from, next) => {
  const userStore = useUserStore()  // 函数式获取，避免循环依赖
  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if ((to.name === 'Login' || to.name === 'Register') && userStore.isLoggedIn) {
    next({ name: 'Home' })
  } else {
    next()
  }
})
```

### Step 3: 确认 main.ts 无需修改

**文件**: `Veritas/frontend/src/main.ts`

当前内容已正确：
```typescript
import router from './router'
app.use(createPinia())
app.use(router)
app.mount('#app')
```

- `createPinia()` 在 `router` 之前注册 ✅（守卫中 `useUserStore()` 依赖 Pinia 已安装）
- `app.use(router)` 在 `app.mount('#app')` 之前 ✅

**无需修改**，但需验证。

### Step 4: TypeScript 编译验证

运行 `npx vue-tsc --noEmit` 确认无类型错误。

### Step 5: 开发服务器验证

运行 `npm run dev` 确认开发服务器正常启动。

---

## 验收标准对照

| AC ID | 验收标准 | 实现方式 | 验证方法 |
|-------|---------|---------|---------|
| AC-001 | 9条路由定义完整，路径kebab-case，名称PascalCase | 9条路由与架构文档完全一致 | code_review |
| AC-002 | 所有页面组件懒加载 | `component: () => import(...)` | code_review |
| AC-003 | 需认证路由 requiresAuth:true，公开路由 false | Home/Login/Register=false, 其余=true | code_review |
| AC-004 | 未登录访问需认证页面跳转/login?redirect=原路径 | beforeEach守卫逻辑 | automated_test |
| AC-005 | 已登录访问/login或/register跳转首页 | beforeEach守卫逻辑 | automated_test |
| AC-006 | createWebHistory模式 | `createWebHistory()` | code_review |
| AC-007 | main.ts正确注册router插件 | 已确认无需修改 | code_review |
| AC-008 | 动态路由参数paperId/analysisId使用camelCase | `:paperId` `:analysisId` | code_review |

---

## 风险与注意事项

1. **循环依赖**: `api/index.ts` 导入了 `router`，`router/index.ts` 不能在模块顶层导入 `useUserStore`（因为 userStore 可能间接依赖 api）。解决方案：在 `beforeEach` 回调内调用 `useUserStore()`
2. **Pinia 初始化顺序**: `main.ts` 中 `createPinia()` 必须在 `router` 之前 `app.use()`，否则守卫中 `useUserStore()` 会报错。当前顺序正确
3. **FA-004 禁止事项**: 绝不在模块顶层 `import { useUserStore }` 并在守卫外使用
