# Task03/04/05 并行开发遗留问题修复

## 功能描述
- 解决了 Task03（Axios拦截器+API骨架）、Task04（Vue Router+守卫）、Task05（Pinia Store骨架）三个任务并行开发后产生的循环依赖、类型不一致、占位符和功能遗漏问题
- 消除了 `api/index.ts` → `stores/userStore.ts` → `api/user.ts` → `api/index.ts` 和 `api/index.ts` → `router/index.ts` → `stores/userStore.ts` 的三方循环依赖链
- 统一了 `ProfileResponse` 与 `UserProfile` 的类型定义，移除了不安全的 `as` 类型断言
- 实现了 `paperStore.filteredResults` 的真实过滤逻辑
- 完善了 `userStore.login` 登录后自动获取用户画像的功能
- 业务价值：确保前端基础设施层在并行开发后保持一致性和健壮性，为后续页面开发提供可靠的状态管理和API通信基础

## 实现逻辑
- 修改的核心文件列表：
  1. `Veritas/frontend/src/api/index.ts` — 移除顶层循环导入，改为拦截器回调内动态 `await import()`
  2. `Veritas/frontend/src/router/index.ts` — 移除顶层循环导入，改为守卫回调内动态 `await import()`
  3. `Veritas/frontend/src/types/user.ts` — `ProfileResponse` 字段类型从 `string` 改为枚举引用
  4. `Veritas/frontend/src/stores/userStore.ts` — 移除6处 `as` 断言，login后自动fetchProfile
  5. `Veritas/frontend/src/stores/paperStore.ts` — `filteredResults` 实现年份/会议/引用数过滤+排序
- 使用的设计模式：
  - 动态导入（Dynamic Import）模式解决循环依赖
  - 计算属性（Computed）链式过滤模式实现前端筛选
- 关键代码逻辑说明：
  - Axios拦截器回调改为 `async`，在回调内使用 `await import('@/stores/userStore')` 延迟加载Store
  - Vue Router `beforeEach` 守卫改为 `async`，在守卫内动态导入 `useUserStore`
  - `ProfileResponse` 的枚举字段使用 `UserProfile['educationLevel']` 索引类型引用，保证与 `UserProfile` 类型一致
  - `filteredResults` 按年份范围、会议名、最低引用数过滤，支持按年份/引用数排序

## 接口变更
### Request
无新增API请求，本次修复仅涉及前端内部模块间依赖关系和类型定义。

### Response
无API响应变更。`ProfileResponse` 的TypeScript类型定义收紧（`string` → 枚举字面量类型），但运行时JSON格式不变。

## 测试结果
- 测试场景1：`vue-tsc --noEmit` TypeScript编译检查 — 结果：零错误通过 ✅
- 测试场景2：`npm run dev` 开发服务器启动 — 结果：正常启动（localhost:5173）✅
- 测试场景3：循环依赖验证 — 模块加载顺序无报错，Pinia Store在Router守卫和Axios拦截器中均可正常获取 ✅
- 测试场景4：`filteredResults` 过滤逻辑 — TypeScript类型检查通过，computed链式过滤逻辑完整 ✅
- 是否通过：是

## 相关文件
- `Veritas/frontend/src/api/index.ts` — Axios实例+拦截器（修复循环依赖）
- `Veritas/frontend/src/router/index.ts` — Vue Router配置+守卫（修复循环依赖）
- `Veritas/frontend/src/types/user.ts` — 用户类型定义（修复类型不一致）
- `Veritas/frontend/src/stores/userStore.ts` — 用户Store（移除断言+自动获取画像）
- `Veritas/frontend/src/stores/paperStore.ts` — 论文Store（实现过滤逻辑）
- `Veritas/frontend/src/main.ts` — 应用入口（Pinia先于Router注册，无冲突）
