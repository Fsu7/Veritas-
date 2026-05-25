# 技术教学文档

## 开发思路
- 需求分析过程：task04 要求创建 Vue Router 配置，定义9条路由并实现全局前置守卫。经分析发现 `router/index.ts` 已存在基本实现，但守卫直接读取 `localStorage` 而非使用 `userStore`，且缺少 `RouteMeta` 类型扩展
- 技术选型考虑：Vue Router 4 + createWebHistory（HTML5 History API，URL 无 # 号，更美观且利于 SEO）
- 架构设计思路：路由配置仅负责页面导航和认证守卫，不包含业务逻辑（遵循分层架构约束）
- 遇到的问题及解决方案：
  - **循环依赖风险**：`api/index.ts` 导入了 `router`，若 `router/index.ts` 在模块顶层调用 `useUserStore()` 可能形成循环。解决方案：在 `beforeEach` 回调内函数式获取 Store
  - **Pinia 初始化顺序**：守卫中 `useUserStore()` 依赖 Pinia 已安装。确认 `main.ts` 中 `createPinia()` 在 `router` 之前 `app.use()`，顺序正确

## 实现步骤
1. 第一步：分析现有 `router/index.ts`，发现守卫使用 `localStorage.getItem('token')` 直接读取，不符合单一数据源原则
2. 第二步：添加 `declare module 'vue-router'` 扩展 `RouteMeta` 接口，为 `requiresAuth` 提供类型安全
3. 第三步：重写全局前置守卫，改用 `useUserStore()` 函数式获取，实现 `requiresAuth` 检查 + 已登录用户访问登录页重定向
4. 第四步：确认 `main.ts` 无需修改（Pinia 在 router 之前注册，顺序正确）
5. 第五步：运行 `vue-tsc --noEmit` 和 `npm run dev` 验证

## 解决了什么问题
- 核心问题描述：路由守卫直接读取 `localStorage` 而非使用 Pinia Store，导致认证状态管理分散，且 `meta.requiresAuth` 无 TypeScript 类型提示
- 解决方案对比：
  - 方案A（架构文档参考）：模块顶层 `import { useUserStore }` — 存在循环依赖风险
  - 方案B（最终方案）：顶层导入 `useUserStore`，但在 `beforeEach` 回调内调用 — 避免循环依赖，保持单一数据源
- 最终方案的优势：类型安全 + 单一数据源 + 无循环依赖

## 变更内容
### 新增文件
无新增文件

### 修改文件
- `Veritas/frontend/src/router/index.ts`
  - 新增 `declare module 'vue-router'` RouteMeta 类型扩展
  - 新增 `import { useUserStore } from '@/stores/userStore'`
  - 守卫认证方式从 `localStorage.getItem('token')` 改为 `useUserStore().isLoggedIn`
  - 9条路由定义保持不变（懒加载 + meta.requiresAuth）

### 配置变更
无配置变更

## 关键技术点
- **RouteMeta 类型扩展**：通过 `declare module 'vue-router'` 模块增强，为 `route.meta.requiresAuth` 提供类型提示，避免运行时错误
- **函数式 Store 获取**：`useUserStore()` 在 `beforeEach` 回调内调用而非模块顶层执行，确保：1) Pinia 已安装 2) 避免循环依赖
- **懒加载代码分割**：`component: () => import('@/views/XxxView.vue')` 由 Vite 自动处理为独立 chunk，减小首屏体积
- **redirect 参数传递**：`next({ name: 'Login', query: { redirect: to.fullPath } })` 将原始路径编码到 URL 参数中，登录成功后可跳回

## 经验总结
- 开发过程中的收获：Vue Router 的 `declare module` 模块增强是官方推荐的方式扩展路由元信息类型，比自定义接口更优雅
- 踩过的坑及如何避免：
  - 循环依赖是前端路由配置中的常见陷阱，特别是当 API 层和路由层互相引用时。最佳实践是守卫内函数式获取 Store
  - Pinia 必须在 Router 之前 `app.use()`，否则守卫中 `useUserStore()` 会抛出 "getActivePinia was called with no active Pinia" 错误
- 最佳实践建议：
  - 路由守卫仅做认证检查，不包含业务逻辑（数据隔离由后端保证）
  - 路由路径使用 kebab-case，路由名称使用 PascalCase，动态参数使用 camelCase
  - 已登录用户访问登录/注册页应重定向首页，避免无意义操作
