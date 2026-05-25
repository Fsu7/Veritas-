# Vue Router 配置与路由守卫

## 功能描述
- 解决了前端路由统一管理与认证守卫的问题，为9个页面提供导航控制
- 实现了9条路由定义（全部懒加载）、路由元信息 `meta.requiresAuth` 区分公开/需认证路由、全局前置守卫（未登录跳转登录页携带 redirect 参数、已登录访问登录/注册页跳转首页）
- 业务价值：为整个前端应用提供页面导航骨架和认证拦截能力，确保未认证用户无法访问受保护页面，同时支持登录后跳回原页面

## 实现逻辑
- 修改的核心文件：`Veritas/frontend/src/router/index.ts`
- 使用的设计模式：
  - **懒加载模式**：所有页面组件使用 `component: () => import(...)` 动态导入，Vite 自动代码分割
  - **元信息守卫模式**：通过 `meta.requiresAuth` 标记路由认证需求，全局前置守卫统一拦截
  - **函数式 Store 获取**：在 `beforeEach` 回调内调用 `useUserStore()`，避免模块顶层导入导致的循环依赖
- 关键代码逻辑说明：
  1. `declare module 'vue-router'` 扩展 `RouteMeta` 接口，使 `requiresAuth` 获得 TypeScript 类型安全
  2. 9条路由：3条公开（Home/Login/Register）+ 6条需认证（Search/PaperDetail/Compare/Report/AgentFlow/UserCenter）
  3. 守卫逻辑：`requiresAuth && !isLoggedIn` → 跳转 `/login?redirect=原路径`；`已登录访问 Login/Register` → 跳转首页

## 接口变更
### Request
无 API 接口变更，本任务仅涉及前端路由配置。

### Response
无 API 接口变更。

## 测试结果
- 测试场景1：TypeScript 编译验证（`vue-tsc --noEmit`）— 零错误通过 ✅
- 测试场景2：开发服务器启动验证（`npm run dev`）— 正常启动在 localhost:5173 ✅
- 测试场景3：路由定义完整性 — 9条路由路径、名称、懒加载、meta 配置均正确 ✅
- 测试场景4：守卫逻辑验证（代码审查）— 未登录跳转携带 redirect、已登录重定向首页 ✅
- 是否通过：是

## 相关文件
- `Veritas/frontend/src/router/index.ts` — 路由配置文件（修改）
- `Veritas/frontend/src/main.ts` — 应用入口（确认无需修改，router 已注册）
- `Veritas/frontend/src/stores/userStore.ts` — 用户状态管理（守卫引用 isLoggedIn）
- `Veritas/frontend/src/api/index.ts` — Axios 实例（401 拦截器引用 router）
