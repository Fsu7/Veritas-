# 技术教学文档：Vue3 + Vite + TypeScript 前端项目骨架搭建

## 开发思路

### 需求分析过程

本次任务来自 M1 里程碑（基础设施就绪）的前端部分，需求可拆解为：

1. **工程化基础**：项目初始化、构建工具、TypeScript 严格模式
2. **UI 框架集成**：Element Plus 按需导入、主题定制
3. **路由系统**：页面路由 + 懒加载 + 认证守卫
4. **状态管理**：用户/论文/会话/Agent 四大业务域的状态隔离
5. **API 封装**：Axios 统一实例 + JWT 注入 + 错误处理
6. **样式系统**：SCSS 全局变量 + CSS 变量 + Reset
7. **构建优化**：代码分包 + 代理配置 + SSE 支持

### 技术选型考虑

| 技术点 | 选择 | 理由 |
|--------|------|------|
| 构建工具 | Vite 8 | 启动快、HMR 快、原生 ESM、与 Vue3 生态深度整合 |
| UI 库 | Element Plus 2.14 | Vue3 官方推荐、组件丰富、主题可定制、社区活跃 |
| 状态管理 | Pinia 2.3 | Vue 官方推荐、TypeScript 支持好、Setup Store 风格与 Composition API 统一 |
| 路由 | Vue Router 4 | Vue3 官方路由、支持组合式 API、懒加载成熟 |
| HTTP 库 | Axios 1.16 | 拦截器机制成熟、浏览器/Node 通用、社区生态丰富 |
| 样式预处理器 | SCSS | 变量/嵌套/混入功能完善，Element Plus 主题定制依赖 SCSS |
| 图表 | ECharts 5.6 | 后续 Agent 流程可视化需要，提前引入 |
| 测试 | Vitest | Vite 原生集成、与 Vue Test Utils 配合好 |

### 架构设计思路

采用 **"分层 + 领域"** 双维度组织代码：

```
src/
├── api/          # 网络层：统一 Axios 实例
├── types/        # 类型层：按业务域拆分类型定义
├── stores/       # 状态层：按业务域拆分 Pinia Store
├── router/       # 路由层：集中式路由配置
├── components/   # 组件层：按功能分类（layout/xxx/）
├── views/        # 页面层：与路由一一对应
├── styles/       # 样式层：全局 + 变量
└── utils/        # 工具层：通用函数（预留）
```

核心设计原则：
- **类型先行**：所有业务数据结构先定义 TypeScript 接口，再写实现
- **Store 按域拆分**：user / paper / session / agent 四个独立 Store，避免单文件臃肿
- **跨系统命名规范**：JSON 字段使用 snake_case（后端 Python/Java 约定），前端 TypeScript 接口使用 camelCase，通过字段名映射保持一致

## 实现步骤

### 第一步：项目初始化与依赖安装

```bash
# 使用 npm create vite 初始化 Vue3 + TypeScript 模板
npm create vite@latest frontend -- --template vue-ts

# 安装核心依赖
cd frontend
npm install vue@^3.5 vue-router@^4 pinia@^2 axios@^1 element-plus@^2 echarts@^5 markdown-it@^14

# 安装开发依赖
npm install -D @vitejs/plugin-vue@^6 typescript@~6.0 sass@^1 unplugin-auto-import@^21 unplugin-vue-components@^32 vitest@^3 @vue/test-utils@^2
```

### 第二步：Vite 配置（核心）

配置 `vite.config.ts`，重点解决三个问题：

1. **Element Plus 按需自动导入**：使用 `unplugin-auto-import` + `unplugin-vue-components` + `ElementPlusResolver`
2. **路径别名**：`@/` → `src/`，配合 `tsconfig.json` 的 `paths`
3. **SCSS 变量全局注入**：`additionalData` 让每个组件自动引入变量文件
4. **manualChunks 函数式分包**：Vite 8 不再支持对象字面量形式，必须写函数

### 第三步：TypeScript 严格配置

`tsconfig.json` 关键项：
- `"strict": true`：启用所有严格类型检查
- `"noUnusedLocals": true` / `"noUnusedParameters": true`：强制清理未使用变量
- `"paths": { "@/*": ["./src/*"] }`：与 Vite 别名保持一致
- `"noEmit": true`：仅做类型检查，不输出 JS

`tsconfig.node.json` 关键项：
- `"composite": true`：支持项目引用（Project References）
- `"emitDeclarationOnly": true`：仅输出声明文件
- 必须包含 `"declaration": true`，否则 Vite 配置文件的类型推导会出错

### 第四步：路由系统搭建

1. 定义 9 条路由，覆盖首页、认证、搜索、详情、对比、报告、Agent 流程、用户中心
2. 所有业务路由使用 `component: () => import('@/views/xxx.vue')` 懒加载
3. 全局前置守卫 `router.beforeEach` 实现 JWT 认证拦截：
   - 未登录访问需认证页面 → 跳转登录页（携带 redirect 参数）
   - 已登录访问登录/注册页 → 跳转首页

### 第五步：状态管理（Pinia Setup Store）

四个 Store 分别负责：

| Store | 职责 | 持久化 |
|-------|------|--------|
| `userStore` | token、userId、username、profile | localStorage |
| `paperStore` | 搜索结果、选中论文、收藏、筛选 | 内存 |
| `sessionStore` | 当前会话 ID、分析结果缓存 | 内存 |
| `agentStore` | Agent 执行状态、流程图、进度 | 内存 |

Setup Store 写法示例：
```typescript
export const useUserStore = defineStore('user', () => {
  const token = ref<string>(localStorage.getItem('token') || '')
  const isLoggedIn = computed(() => !!token.value)
  function setLoginData(data: LoginResponse) { /* ... */ }
  return { token, isLoggedIn, setLoginData }
})
```

### 第六步：API 封装（Axios）

1. 创建 Axios 实例，配置 `baseURL`、`timeout`、`headers`
2. **请求拦截器**：从 `userStore` 读取 token，注入 `Authorization: Bearer {token}`
3. **响应拦截器**：
   - 业务成功（code === 200）：直接返回 `data.data`
   - 业务失败：ElMessage 提示错误信息
   - HTTP 401：自动登出 + 跳转登录页
   - HTTP 403/404/超时：分别给出友好提示

### 第七步：样式系统

1. `global.scss`：CSS Reset、全局字体、链接样式、布局容器（`.app-container` / `.app-main`）
2. `variables.scss`：CSS 自定义属性（Custom Properties）
   - Element Plus 主题色覆盖
   - Agent 状态专用颜色（waiting/running/completed/failed）
   - 布局尺寸变量（header-height、sidebar-width、content-max-width）
3. Vite 配置 `additionalData` 实现全局注入，所有 `.vue` 文件 `<style lang="scss">` 自动可用变量

### 第八步：组件与视图骨架

1. **布局组件**：AppHeader（导航栏）、AppFooter（底部信息）
2. **首页**：主题搜索输入框 + 最近搜索标签 + 路由跳转
3. **8 个占位视图**：Login、Register、Search、PaperDetail、Compare、Report、AgentFlow、UserCenter

## 解决了什么问题

### 核心问题 1：Vite 8 + Element Plus 按需导入兼容性

**问题描述**：
Vite 8 的 `rollupOptions.output.manualChunks` 不再接受对象字面量 `{ 'element-plus': ['element-plus'] }`，TypeScript 会报错：
```
Type '{ manualChunks: { 'element-plus': string[]; ... } }' is not assignable to type 'OutputOptions'
```

**解决方案对比**：

| 方案 | 做法 | 缺点 |
|------|------|------|
| A. 降级 Vite 到 7.x | 修改 package.json | 错过 Vite 8 性能优化，后续升级更麻烦 |
| B. 使用函数式配置 | `manualChunks(id: string) { ... }` | 需要理解 Vite 8 新 API，但一劳永逸 |

**最终方案**：采用方案 B，函数式配置：
```typescript
manualChunks(id: string) {
  if (id.includes('element-plus')) return 'element-plus'
  if (id.includes('echarts')) return 'echarts'
  if (id.includes('node_modules/vue') || id.includes('node_modules/vue-router') || id.includes('node_modules/pinia') || id.includes('node_modules/axios')) return 'vendor'
}
```

**优势**：兼容 Vite 8 新类型系统，按库拆分 chunk 优化缓存，无需降级。

### 核心问题 2：Element Plus CSS 加载失败（开发环境）

**问题描述**：
开发服务器启动后，浏览器控制台报错 `net::ERR_ABORTED`，多个 element-plus CSS 文件 404。

**根因**：
`main.ts` 中同时存在 `import 'element-plus/dist/index.css'`（全量 CSS）和 `unplugin-vue-components` 的按需样式导入，两者冲突。

**解决方案**：
移除 `main.ts` 中的 `import 'element-plus/dist/index.css'`，完全依赖 `unplugin-vue-components` 的按需样式自动导入。

**效果**：
- Element Plus CSS 从 **356KB** 降至 **55.9KB**
- JS 从 **960KB** 降至 **200KB**

### 核心问题 3：tsconfig.node.json 项目引用配置

**问题描述**：
TypeScript 报错 `"Referenced project must have setting "composite": true"` 和 `"may not disable emit"`。

**解决方案**：
1. `tsconfig.node.json` 添加 `"composite": true`
2. 移除 `"noEmit": true`（composite 项目必须输出声明文件）
3. 添加 `"emitDeclarationOnly": true` 和 `"declaration": true`

## 变更内容

### 新增文件

| 文件路径 | 作用 |
|---------|------|
| `Veritas/frontend/package.json` | 项目依赖与脚本配置 |
| `Veritas/frontend/vite.config.ts` | Vite 构建、插件、代理、分包配置 |
| `Veritas/frontend/tsconfig.json` | TypeScript 严格模式、路径别名 |
| `Veritas/frontend/tsconfig.node.json` | Node 环境、composite 项目引用 |
| `Veritas/frontend/src/env.d.ts` | Vite 环境变量类型声明、`.vue` 文件模块声明 |
| `Veritas/frontend/src/main.ts` | 应用入口，挂载 Pinia + Router |
| `Veritas/frontend/src/App.vue` | 根组件，Header + RouterView + Footer 布局 |
| `Veritas/frontend/src/router/index.ts` | 9 条路由 + 全局前置守卫 |
| `Veritas/frontend/src/api/index.ts` | Axios 实例 + 拦截器 |
| `Veritas/frontend/src/stores/userStore.ts` | 用户状态管理 |
| `Veritas/frontend/src/stores/paperStore.ts` | 论文状态管理 |
| `Veritas/frontend/src/stores/sessionStore.ts` | 会话状态管理 |
| `Veritas/frontend/src/stores/agentStore.ts` | Agent 状态管理 |
| `Veritas/frontend/src/types/common.ts` | 通用响应类型 |
| `Veritas/frontend/src/types/user.ts` | 用户/画像类型 |
| `Veritas/frontend/src/types/paper.ts` | 论文/筛选类型 |
| `Veritas/frontend/src/types/analysis.ts` | 分析结果/对比/引用类型 |
| `Veritas/frontend/src/types/agent.ts` | Agent 状态/流程图类型 |
| `Veritas/frontend/src/styles/global.scss` | 全局 CSS Reset + 布局 |
| `Veritas/frontend/src/styles/variables.scss` | CSS 变量（主题色、Agent 色、布局尺寸） |
| `Veritas/frontend/src/components/layout/AppHeader.vue` | 顶部导航栏 |
| `Veritas/frontend/src/components/layout/AppFooter.vue` | 底部信息栏 |
| `Veritas/frontend/src/views/HomeView.vue` | 首页（搜索入口） |
| `Veritas/frontend/src/views/LoginView.vue` | 登录页（占位） |
| `Veritas/frontend/src/views/RegisterView.vue` | 注册页（占位） |
| `Veritas/frontend/src/views/SearchView.vue` | 搜索结果页（占位） |
| `Veritas/frontend/src/views/PaperDetailView.vue` | 论文详情页（占位） |
| `Veritas/frontend/src/views/CompareView.vue` | 对比分析页（占位） |
| `Veritas/frontend/src/views/ReportView.vue` | 综述报告页（占位） |
| `Veritas/frontend/src/views/AgentFlowView.vue` | Agent 流程可视化页（占位） |
| `Veritas/frontend/src/views/UserCenterView.vue` | 用户中心页（占位） |

### 修改文件

本项目为全新创建，无修改文件。

### 配置变更

| 配置项 | 说明 |
|--------|------|
| `vite.config.ts` → `plugins` | 注册 `unplugin-auto-import` + `unplugin-vue-components`，使用 `ElementPlusResolver` |
| `vite.config.ts` → `resolve.alias` | `@/` → `./src` |
| `vite.config.ts` → `css.preprocessorOptions.scss.additionalData` | 全局注入 `@/styles/variables.scss` |
| `vite.config.ts` → `build.rollupOptions.output.manualChunks` | 函数式分包：element-plus / echarts / vendor |
| `vite.config.ts` → `server.proxy` | `/api` → `http://localhost:8080`，SSE 支持（关闭缓存和缓冲） |
| `tsconfig.json` → `compilerOptions` | `strict: true`, `noUnusedLocals: true`, `paths: {"@/*": ["./src/*"]}` |
| `tsconfig.node.json` → `compilerOptions` | `composite: true`, `emitDeclarationOnly: true`, `declaration: true` |

## 关键技术点

### 1. Element Plus 按需自动导入

使用 `unplugin-auto-import` + `unplugin-vue-components` 实现真正的按需加载：
- **组件按需**：只在用到的页面导入对应组件的 JS 和 CSS
- **API 按需**：`ElMessage`、`ElLoading` 等 API 自动导入，无需手动 `import`
- **类型声明自动生成**：`src/auto-imports.d.ts` 和 `src/components.d.ts`

### 2. Pinia Setup Store 模式

与传统 Options Store 对比：

```typescript
// Options Store（不推荐）
export const useUserStore = defineStore('user', {
  state: () => ({ token: '' }),
  getters: { isLoggedIn: (state) => !!state.token },
  actions: { setToken(t: string) { this.token = t } }
})

// Setup Store（推荐，与 Composition API 风格统一）
export const useUserStore = defineStore('user', () => {
  const token = ref('')
  const isLoggedIn = computed(() => !!token.value)
  function setToken(t: string) { token.value = t }
  return { token, isLoggedIn, setToken }
})
```

优势：
- 更好的 TypeScript 类型推断
- 与 `<script setup>` 风格完全一致
- 支持组合式函数复用（composables）

### 3. Axios 拦截器与 Pinia 的循环依赖处理

**问题**：`api/index.ts` 需要 `useUserStore` 获取 token，但 Store 文件可能依赖 API 文件，形成循环依赖。

**解决方案**：
在请求拦截器中**延迟获取** Store 实例：
```typescript
http.interceptors.request.use((config) => {
  const userStore = useUserStore()  // 延迟到拦截器执行时才实例化
  if (userStore.token) {
    config.headers.Authorization = `Bearer ${userStore.token}`
  }
  return config
})
```

避免在模块顶层 `import` 时立即实例化 Store，从而打破循环依赖。

### 4. Vite 8 manualChunks 函数式分包

Vite 8 的 Rollup 输出配置类型更严格，对象字面量形式已废弃。函数式配置的优势：
- 更灵活：可以基于 `id` 做任意条件判断
- 类型安全：TypeScript 能正确推断参数和返回值类型
- 未来兼容：符合 Rollup 官方推荐写法

### 5. SCSS 变量全局注入的注意事项

`additionalData` 会在**每个** SCSS 文件开头注入内容，因此：
- 必须使用 `@use` 而非 `@import`（避免重复导入问题）
- 变量文件不应包含实际 CSS 规则（只放变量和 mixin），否则会被重复输出
- 使用 `as *` 可以让变量无需命名空间前缀直接使用

## 经验总结

### 开发过程中的收获

1. **Vite 8 升级经验**：Vite 大版本升级时，`manualChunks` 等配置项的类型约束会变严格，需要仔细阅读 changelog 或类型报错信息。
2. **按需导入的彻底性**：Element Plus 的按需导入不仅指组件，还包括样式。移除全量 CSS 导入后，构建产物大幅缩小。
3. **TypeScript 项目引用**：`tsconfig.json` + `tsconfig.node.json` 的拆分是 Vite 模板的默认做法，理解 `composite` 和 `references` 的机制对排查类型错误很重要。
4. **Pinia 与 Axios 的协作**：拦截器中延迟获取 Store 是处理循环依赖的优雅方案，比将 token 存储在独立模块中更符合 Vue 生态习惯。

### 踩过的坑及如何避免

| 坑 | 原因 | 如何避免 |
|----|------|---------|
| Element Plus CSS 404 | 全量 CSS 导入与按需导入冲突 | 只保留 `unplugin-vue-components` 的自动导入，移除 `import 'element-plus/dist/index.css'` |
| manualChunks 类型报错 | Vite 8 不再支持对象字面量 | 改用函数式配置 `manualChunks(id: string) { ... }` |
| tsconfig.node.json 报错 | 缺少 `composite: true` 或 `noEmit` 与 `composite` 冲突 | 添加 `composite: true`，移除 `noEmit`，添加 `emitDeclarationOnly: true` |
| SCSS 变量未生效 | `additionalData` 路径错误或语法错误 | 使用 `@use "@/styles/variables.scss" as *;`，确保路径与 `resolve.alias` 一致 |
| 路由守卫无限重定向 | 守卫逻辑中 `next()` 调用条件有漏洞 | 确保所有分支都有明确的 `next()` 调用，已登录访问登录页应跳首页 |

### 最佳实践建议

1. **类型先行**：每个业务模块先写 `types/xxx.ts`，再写 Store 和 API，最后写视图。类型是前后端协作的契约。
2. **Store 最小化**：每个 Store 只管理一个业务域的状态，跨域通信通过组件层协调，避免 Store 之间直接引用。
3. **拦截器职责单一**：请求拦截器只做「注入 Token」，响应拦截器只做「统一错误处理」，业务逻辑在组件/Store 中处理。
4. **CSS 变量优先**：颜色、尺寸等设计 token 使用 CSS 自定义属性（`:root`），便于运行时主题切换和响应式适配。
5. **懒加载全覆盖**：所有非首屏路由必须懒加载，首屏只加载 `HomeView` 和公共 chunk（vendor / element-plus）。
6. **环境变量管理**：敏感配置（API 地址）使用 `import.meta.env.VITE_xxx`，配合 `.env` 文件，不硬编码。
7. **构建产物监控**：定期运行 `npm run build` 检查 chunk 大小，发现异常膨胀及时排查（如全量导入未按需）。
