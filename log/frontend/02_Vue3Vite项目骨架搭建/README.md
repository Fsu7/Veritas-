# Vue3 + Vite + TypeScript 前端项目骨架搭建

## 功能描述

- **解决了什么问题**：为科研文献智能助手项目建立完整的前端工程化基础，包括项目初始化、依赖管理、路由系统、状态管理、API封装、UI组件库集成等。
- **实现了什么功能**：搭建了一个可直接用于后续业务开发的前端项目骨架，覆盖 Vue3 Composition API、TypeScript 严格模式、Pinia 状态管理、Vue Router 懒加载路由、Axios 统一请求封装、Element Plus 按需自动导入、SCSS 全局样式系统、Vite 构建优化等全部基础设施。
- **业务价值**：为 M1（基础设施就绪）和 M3（前后端联调）里程碑提供前端基础，使后续页面开发可以直接基于本骨架进行，无需重复配置工程环境。

## 实现逻辑

### 修改的核心文件列表

| 文件 | 作用 |
|------|------|
| `package.json` | 项目依赖配置：Vue3、Vite8、TypeScript、Element Plus、Pinia、Vue Router、Axios、ECharts、SCSS 等 |
| `vite.config.ts` | Vite 构建配置：Element Plus 自动导入、路径别名 `@/`、SCSS 变量注入、`manualChunks` 分包策略、开发代理 `/api` → `localhost:8080`、SSE 代理支持 |
| `tsconfig.json` | TypeScript 严格模式配置，`paths` 别名映射，`noUnusedLocals` 等严格检查 |
| `tsconfig.node.json` | Node 环境配置，`composite: true` 支持项目引用 |
| `src/main.ts` | 应用入口：创建 Vue 应用实例，挂载 Pinia 和 Router |
| `src/App.vue` | 根组件：AppHeader + RouterView + AppFooter 布局 |
| `src/router/index.ts` | 9 条路由定义 + 全局前置守卫（JWT 认证拦截、登录态重定向） |
| `src/api/index.ts` | Axios 实例封装：JWT Token 注入、统一响应错误处理（401/403/404/超时）、ElMessage 提示 |
| `src/stores/userStore.ts` | 用户状态管理：token/userId/username/profile，localStorage 持久化 |
| `src/stores/paperStore.ts` | 论文状态管理：搜索结果、选中论文、收藏、筛选条件 |
| `src/stores/sessionStore.ts` | 会话状态管理：当前会话 ID、分析结果缓存 |
| `src/stores/agentStore.ts` | Agent 状态管理：Agent 执行状态、流程图数据、连接状态、进度计算 |
| `src/types/*.ts` | 5 个类型定义文件：common、user、paper、analysis、agent |
| `src/styles/global.scss` | 全局 CSS Reset、字体、颜色、布局容器样式 |
| `src/styles/variables.scss` | CSS 变量：Element Plus 主题色、Agent 状态色、布局尺寸变量 |
| `src/components/layout/AppHeader.vue` | 顶部导航栏：Logo、菜单、登录/注册/用户信息、退出登录 |
| `src/components/layout/AppFooter.vue` | 底部信息栏 |
| `src/views/HomeView.vue` | 首页：主题搜索输入框、最近搜索标签、路由跳转 |
| `src/views/LoginView.vue` 等 8 个视图 | 占位视图文件，供后续业务开发填充 |

### 使用的算法或设计模式

- **Composition API + `<script setup>`**：所有组件和 Store 均采用 Vue3 Composition API 风格，代码更简洁、类型推导更友好。
- **Pinia Setup Store**：使用函数式定义 Store（非 Options API），与 Composition API 风格统一，支持 TypeScript 自动类型推断。
- **懒加载路由**：所有业务路由使用 `() => import('@/views/xxx.vue')`，减少首屏加载体积。
- **Cache-Aside 前端版**：用户登录态通过 localStorage 持久化，页面刷新后状态不丢失。
- **Axios 拦截器模式**：请求拦截器注入 JWT，响应拦截器统一处理业务错误码和 HTTP 状态码。
- **manualChunks 函数式分包**：Vite8 要求函数式配置，按库拆分 chunk（element-plus / echarts / vendor），优化缓存命中率。

### 关键代码逻辑说明

**路由守卫（JWT 认证）**：
```typescript
router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token')
  const isLoggedIn = !!token
  if (to.meta.requiresAuth && !isLoggedIn) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if ((to.name === 'Login' || to.name === 'Register') && isLoggedIn) {
    next({ name: 'Home' })
  } else {
    next()
  }
})
```

**Axios 响应拦截器**：
```typescript
http.interceptors.response.use(
  (response) => {
    const data = response.data as ApiResponse<unknown>
    if (data.code === 200) return data.data
    ElMessage.error(data.message || '请求失败')
    return Promise.reject(new Error(data.message))
  },
  (error) => {
    if (error.response?.status === 401) {
      const userStore = useUserStore()
      userStore.logout()
      router.push('/login')
      ElMessage.error('登录已过期，请重新登录')
    }
    // ... 其他状态码处理
  }
)
```

**Vite 构建分包**：
```typescript
manualChunks(id: string) {
  if (id.includes('element-plus')) return 'element-plus'
  if (id.includes('echarts')) return 'echarts'
  if (id.includes('node_modules/vue') || id.includes('node_modules/vue-router') || id.includes('node_modules/pinia') || id.includes('node_modules/axios')) return 'vendor'
}
```

## 接口变更

本项目为前端基础设施搭建，不涉及后端 API 接口变更。前端内部接口（类型定义）如下：

### 统一响应类型

```typescript
// src/types/common.ts
export interface ApiResponse<T> {
  code: number
  message: string
  data: T
  timestamp: number
}

export interface PageResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
  totalPages: number
}
```

### 用户相关类型

```typescript
// src/types/user.ts
export interface UserProfile {
  educationLevel: 'undergraduate' | 'master' | 'phd' | 'faculty'
  researchField: string
  knowledgeLevel: 'beginner' | 'intermediate' | 'advanced' | 'expert'
  preferredStyle: 'simple' | 'balanced' | 'technical'
}

export interface LoginResponse {
  token: string
  userId: string
  username: string
  hasProfile: boolean
}
```

## 测试结果

| 测试场景 | 结果 |
|---------|------|
| `npm run dev` 开发服务器启动 | 通过，无报错 |
| `npm run typecheck` TypeScript 类型检查 | 通过，0 错误 |
| `npm run build` 生产构建 | 通过，产物正常生成 |
| Element Plus 组件按需加载 | 通过，CSS 从 356KB 降至 55.9KB |
| 路由懒加载 | 通过，首屏仅加载必要 chunk |
| 路由守卫 JWT 拦截 | 通过，未登录访问 `/search` 自动跳转登录页 |
| Axios 拦截器 Token 注入 | 通过，请求头携带 `Authorization: Bearer xxx` |
| SCSS 变量全局注入 | 通过，所有组件可直接使用变量 |
| Pinia Store 状态持久化 | 通过，刷新页面后登录态保留 |
| 开发代理 `/api` → `localhost:8080` | 通过，API 请求正确转发 |

**是否通过：是**

## 相关文件

### 配置文件
- `Veritas/frontend/package.json`
- `Veritas/frontend/vite.config.ts`
- `Veritas/frontend/tsconfig.json`
- `Veritas/frontend/tsconfig.node.json`
- `Veritas/frontend/src/env.d.ts`

### 核心源码
- `Veritas/frontend/src/main.ts`
- `Veritas/frontend/src/App.vue`
- `Veritas/frontend/src/router/index.ts`
- `Veritas/frontend/src/api/index.ts`

### Store
- `Veritas/frontend/src/stores/userStore.ts`
- `Veritas/frontend/src/stores/paperStore.ts`
- `Veritas/frontend/src/stores/sessionStore.ts`
- `Veritas/frontend/src/stores/agentStore.ts`

### 类型定义
- `Veritas/frontend/src/types/common.ts`
- `Veritas/frontend/src/types/user.ts`
- `Veritas/frontend/src/types/paper.ts`
- `Veritas/frontend/src/types/analysis.ts`
- `Veritas/frontend/src/types/agent.ts`

### 样式
- `Veritas/frontend/src/styles/global.scss`
- `Veritas/frontend/src/styles/variables.scss`

### 组件
- `Veritas/frontend/src/components/layout/AppHeader.vue`
- `Veritas/frontend/src/components/layout/AppFooter.vue`

### 视图
- `Veritas/frontend/src/views/HomeView.vue`
- `Veritas/frontend/src/views/LoginView.vue`
- `Veritas/frontend/src/views/RegisterView.vue`
- `Veritas/frontend/src/views/SearchView.vue`
- `Veritas/frontend/src/views/PaperDetailView.vue`
- `Veritas/frontend/src/views/CompareView.vue`
- `Veritas/frontend/src/views/ReportView.vue`
- `Veritas/frontend/src/views/AgentFlowView.vue`
- `Veritas/frontend/src/views/UserCenterView.vue`
