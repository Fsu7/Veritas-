# 科研文献智能助手 — 前端模块

> **课题编号** XH-202630 · **项目名称** 领域知识个性化生成与多智能体协同决策系统
>
> 基于 Vue 3 + TypeScript + Vite 构建的科研文献智能助手前端，提供智能检索、论文分析、多论文对比、个性化综述生成及 Agent 协同可视化等功能。

---

## 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | ^3.5.34 | 渐进式框架，Composition API + `<script setup>` |
| TypeScript | ~6.0.2 | 类型安全 |
| Vite | ^8.0.12 | 构建工具 + 开发服务器 |
| Pinia | ^2.3.1 | 状态管理（Setup Store 风格） |
| Vue Router | ^4.6.4 | 路由管理（懒加载 + 导航守卫） |
| Element Plus | ^2.14.0 | UI 组件库 |
| ECharts | ^5.6.0 | 图表可视化（Agent 流程图等） |
| Axios | ^1.16.1 | HTTP 客户端（统一拦截器） |
| markdown-it | ^14.2.0 | Markdown 渲染（综述报告展示） |
| Sass | ^1.100.0 | CSS 预处理器 |
| Vitest | ^3.2.4 | 单元测试框架 |

---

## 目录结构总览

```
frontend/
├── public/                    # 静态资源（不经 Vite 处理）
├── src/                       # 源代码
│   ├── api/                   # HTTP 请求封装（5 个文件）
│   ├── assets/                # 静态资源（经 Vite 处理）
│   ├── components/            # 可复用组件
│   │   ├── agent/             # Agent 可视化相关组件
│   │   ├── analysis/          # 分析结果展示组件
│   │   ├── common/            # 通用基础组件
│   │   ├── layout/            # 布局组件（页头/页脚）
│   │   ├── paper/             # 论文相关组件
│   │   └── report/            # 报告展示组件
│   ├── composables/           # 组合式函数（Hooks）
│   ├── router/                # 路由配置
│   ├── stores/                # Pinia 状态管理
│   ├── styles/                # 全局样式
│   ├── types/                 # TypeScript 类型定义（6 个文件）
│   ├── utils/                 # 工具函数
│   └── views/                 # 页面级组件
├── .vscode/                   # VS Code 推荐扩展
├── dist/                      # 构建产物（已 .gitignore）
└── 配置文件                    # 根目录下的各类配置
```

---

## 详细说明

### 📁 `public/` — 静态资源目录

不经 Vite 处理，直接复制到构建产物中。

| 文件 | 说明 |
|------|------|
| `favicon.svg` | 网站图标，显示在浏览器标签页上 |
| `icons.svg` | SVG 图标集合（Sprite 方式），供组件内 `<use>` 引用 |

---

### 📁 `src/` — 源代码根目录

| 文件 | 说明 |
|------|------|
| `main.ts` | **应用入口**。创建 Vue 实例，注册 Pinia、Vue Router 插件，挂载到 `#app`，引入全局样式 |
| `App.vue` | **根组件**。三段式布局：`AppHeader`（顶部导航）→ `<RouterView>`（主内容区）→ `AppFooter`（底部页脚），整体采用 Flex 纵向布局撑满视口 |
| `env.d.ts` | Vite 环境类型声明，让 TypeScript 识别 `import.meta.env` 等 Vite 特有变量，声明 `VITE_APP_TITLE`/`VITE_API_BASE_URL` 环境变量类型 |

---

### 📁 `src/api/` — HTTP 请求封装

按业务域划分为 5 个文件，全部基于 `index.ts` 的 Axios 实例封装：

| 文件 | 说明 |
|------|------|
| `index.ts` | **Axios 实例封装**。基础配置：`baseURL` 从 `VITE_API_BASE_URL` 读取（默认 `/api`），超时 30s，JSON 格式。**请求拦截器**：动态导入 `userStore` 读取 JWT Token 注入 `Authorization` 头。**响应拦截器**：成功时解包 `ApiResponse.data`（code=200 返回 data）；失败时按状态码统一处理（401→清空登录态跳转登录页、403→无权限提示、404→资源不存在、ECONNABORTED→超时提示、其他→网络错误提示），所有错误通过 `ElMessage` 弹出 |
| `user.ts` | **用户 API**。`register`（POST /users/register）、`login`（POST /users/login，返回 `LoginResponse`）、`getUserInfo`（GET /users/{userId}）、`getProfile`（GET /users/{userId}/profile，返回 `ProfileResponse`）、`createProfile`（POST /users/{userId}/profile）、`updateProfile`（PUT /users/{userId}/profile） |
| `paper.ts` | **论文 API**。`list`（GET /papers，分页）、`getDetail`（GET /papers/{paperId}，返回 `Paper`）、`search`（GET /papers/search，支持 q + FilterParams，返回 `PageResponse<Paper>`）、`addFavorite`（POST /papers/{paperId}/favorite）、`removeFavorite`（DELETE /papers/{paperId}/favorite） |
| `session.ts` | **会话 API**。`create`（POST /sessions，返回 `SessionResponse`）、`list`（GET /sessions，分页，返回 `PageResponse<SessionDetail>`）、`getDetail`（GET /sessions/{sessionId}，返回 `SessionDetail`）、`delete`（DELETE /sessions/{sessionId}） |
| `analysis.ts` | **分析 API**。`analyzePaper`（POST /analysis/paper）、`comparePapers`（POST /analysis/compare）、`generateReport`（POST /analysis/report）、`getResult`（GET /analysis/{analysisId}，返回 `AnalysisResult`）、`getStatus`（GET /analysis/{analysisId}/status）、`getAgentStreamUrl`（返回 SSE 流 URL `/api/analysis/{analysisId}/agent-stream`） |

---

### 📁 `src/assets/` — 静态资源（经 Vite 处理）

| 文件 | 说明 |
|------|------|
| `hero.png` | 首页英雄区装饰图片 |
| `vite.svg` | Vite Logo，开发阶段占位图 |

> 与 `public/` 的区别：`src/assets/` 下的资源会被 Vite 处理（hash 命名、压缩、内联小文件），通过 `import` 引用。

---

### 📁 `src/components/` — 可复用组件

按业务领域划分为 6 个子目录：

#### `components/layout/` — 布局组件

| 文件 | 说明 |
|------|------|
| `AppHeader.vue` | **顶部导航栏**。左侧 Logo（点击回首页）+ 中间水平菜单（首页、用户中心，仅登录后显示）+ 右侧用户区（已登录显示用户名+退出按钮，未登录显示登录/注册按钮）。高度由 CSS 变量 `--header-height` 控制 |
| `AppFooter.vue` | **底部页脚**。居中显示版权信息 "© 2026 科研文献智能助手"，固定高度 48px |

#### `components/agent/` — Agent 可视化组件（待开发）

用于 Agent 协同流程可视化，如 Agent 状态卡片、流程图节点、进度条等。当前通过 `.gitkeep` 占位。

#### `components/analysis/` — 分析结果展示组件（待开发）

用于论文分析结果的结构化展示，如研究问题/核心方法/主要实验/核心结论/局限性五维度卡片。当前通过 `.gitkeep` 占位。

#### `components/common/` — 通用基础组件（待开发）

用于跨业务复用的基础组件，如加载骨架屏、空状态占位、确认弹窗等。当前通过 `.gitkeep` 占位。

#### `components/paper/` — 论文相关组件（待开发）

用于论文列表、论文卡片、论文详情等场景。当前通过 `.gitkeep` 占位。

#### `components/report/` — 报告展示组件（待开发）

用于综述报告渲染，如 Markdown 渲染器、引用标注、对比矩阵等。当前通过 `.gitkeep` 占位。

---

### 📁 `src/composables/` — 组合式函数

Vue 3 Composition API 的可复用逻辑单元（习惯上以 `use` 前缀命名），如 `useSSE`（SSE 事件流封装，自动重连 3s 间隔最多 5 次）、`usePagination`（分页逻辑）等。当前通过 `.gitkeep` 占位，待开发。

---

### 📁 `src/router/` — 路由配置

| 文件 | 说明 |
|------|------|
| `index.ts` | **路由定义 + 导航守卫**。9 条路由，全部使用懒加载（`() => import(...)`）：<br>• `/` → HomeView（首页，无需认证）<br>• `/login` → LoginView（登录，无需认证）<br>• `/register` → RegisterView（注册，无需认证）<br>• `/search` → SearchView（论文检索，需认证）<br>• `/paper/:paperId` → PaperDetailView（论文详情，需认证）<br>• `/compare` → CompareView（多论文对比，需认证）<br>• `/report/:analysisId` → ReportView（综述报告，需认证）<br>• `/agent-flow/:analysisId` → AgentFlowView（Agent 协同可视化，需认证）<br>• `/user-center` → UserCenterView（用户中心，需认证）<br><br>**全局前置守卫**：未登录访问需认证页面 → 重定向至登录页并携带 `redirect` 参数；已登录访问登录/注册页 → 重定向至首页 |

---

### 📁 `src/stores/` — Pinia 状态管理

采用 Setup Store 风格（`defineStore('name', () => {...})`），按业务域划分 4 个 Store：

| 文件 | Store 名 | 说明 |
|------|---------|------|
| `userStore.ts` | `user` | **用户认证与画像管理**。状态：`token`/`userId`/`username`（同步至 localStorage）、`profile`（UserProfile）。计算属性：`isLoggedIn`/`hasProfile`。方法：`login`（调用 userApi.login + 持久化 + 自动拉取画像）、`logout`（清空登录态 + localStorage）、`fetchProfile`（调用 userApi.getProfile）、`saveProfile`（根据 hasProfile 判断调用 createProfile 或 updateProfile） |
| `paperStore.ts` | `paper` | **论文搜索与选择管理**。状态：`searchResults`（搜索结果列表）、`selectedPapers`（已选论文，上限5篇）、`favorites`（收藏ID列表）、`filters`/`currentQuery`/`totalResults`/`currentPage`/`pageSize`。计算属性：`selectedPaperIds`/`filteredResults`（前端内存筛选：年份/会议/引用数 + 排序）。方法：`searchPapers`（调用 paperApi.search）、`togglePaperSelection`（选择/取消，上限5篇）、`toggleFavorite`（调用 paperApi 收藏/取消） |
| `agentStore.ts` | `agent` | **Agent 执行状态管理**。状态：`agentStates`（Record<string, AgentState>）、`flowData`（流程图数据）、`isConnected`（SSE 连接状态）、`currentAnalysisId`。计算属性：`agentStatesList`/`activeAgents`（运行中的 Agent）/`progress`（完成进度 0~1）。方法：`getAgentState`/`updateAgentState`/`resetStates` |
| `sessionStore.ts` | `session` | **分析会话管理**。状态：`currentSessionId`/`currentAnalysisId`/`analysisResults`（Map 结构缓存）。方法：`createSession`（调用 sessionApi.create）、`fetchAnalysisResult`（调用 analysisApi.getResult 并缓存至 Map） |

---

### 📁 `src/styles/` — 全局样式

| 文件 | 说明 |
|------|------|
| `variables.scss` | **CSS 变量 / 设计令牌**。定义全局 CSS 自定义属性：<br>• Element Plus 主题色覆盖（`--el-color-primary` 等）<br>• Agent 状态色：`--agent-waiting`/`--agent-running`/`--agent-completed`/`--agent-failed`<br>• 布局尺寸：`--header-height`(60px)/`--sidebar-width`(240px)/`--content-max-width`(1200px)<br><br>在 `vite.config.ts` 中通过 `additionalData` 全局注入，所有 SCSS 文件均可直接使用 |
| `global.scss` | **全局样式重置 + 布局**。CSS Reset（box-sizing/margin/padding）、html 基础字号与行高、body 字体栈与背景色、链接样式、`.app-container` 纵向 Flex 布局撑满视口、`.app-main` 主内容区限宽居中 |

---

### 📁 `src/types/` — TypeScript 类型定义

6 个类型文件覆盖全部业务域：

| 文件 | 说明 |
|------|------|
| `common.ts` | **通用 API 响应类型**。`ApiResponse<T>`：统一响应格式（code/message/data/timestamp）；`PageResponse<T>`：分页响应格式（items/total/page/size/totalPages） |
| `user.ts` | **用户相关类型**。`UserProfile`：用户画像四维度（educationLevel/researchField/knowledgeLevel/preferredStyle，严格枚举）；`LoginResponse`：登录响应（token/userId/username/hasProfile）；`ProfileResponse`：画像响应 |
| `paper.ts` | **论文数据类型**。`Paper`：论文完整信息（paperId/title/authors/abstract/year/venue/keywords/citationCount/pdfUrl/score/recommendReason）；`FilterParams`：搜索筛选参数（年份范围/会议/最低引用数/排序方式） |
| `session.ts` | **会话相关类型**。`SessionResponse`：会话创建响应（sessionId/topic/status/createdAt）；`SessionDetail`：会话详情（sessionId/userId/topic/status 枚举/createdAt/updatedAt） |
| `agent.ts` | **Agent 相关类型**。`AgentState`：Agent 状态（name/status 四种枚举/progress/intermediateResult/durationMs/error）；`FlowData`/`FlowNode`/`FlowLink`：流程图数据结构，供 ECharts 渲染 Agent 协同图 |
| `analysis.ts` | **分析结果类型**。`AnalysisResult`：分析结果（analysisId/status 四种枚举/type 三种枚举/result 可选嵌套/agentStates/degraded 降级标记）；`StructuredAnalysis`：五维度结构化分析；`CompareResult`/`CompareRow`/`Conflict`：对比矩阵与矛盾发现；`Citation`：引用标注；`AgentStateInfo`：Agent 状态摘要 |

---

### 📁 `src/utils/` — 工具函数

通用工具函数，如日期格式化、防抖节流、本地存储封装等。当前通过 `.gitkeep` 占位，待开发。

---

### 📁 `src/views/` — 页面级组件

每个文件对应一个路由页面，命名约定 `{Name}View.vue`：

| 文件 | 路由 | 说明 |
|------|------|------|
| `HomeView.vue` | `/` | **首页**（已实现）。居中英雄区布局，展示项目标题 + 副标题 + 搜索输入框（回车或点击检索按钮触发搜索 → 跳转 `/search?q=...`）+ 最近搜索标签（最多10条，点击可快速搜索） |
| `LoginView.vue` | `/login` | **登录页**（占位，显示"页面开发中..."） |
| `RegisterView.vue` | `/register` | **注册页**（占位） |
| `SearchView.vue` | `/search` | **论文检索结果页**（占位）。将展示混合检索结果列表，支持筛选排序 |
| `PaperDetailView.vue` | `/paper/:paperId` | **论文详情页**（占位）。将展示论文元数据 + 五维度结构化分析结果 |
| `CompareView.vue` | `/compare` | **多论文对比页**（占位）。将展示方法对比矩阵 + 矛盾自动发现 |
| `ReportView.vue` | `/report/:analysisId` | **综述报告页**（占位）。将展示个性化综述全文，支持 Markdown 渲染 + 引用溯源 |
| `AgentFlowView.vue` | `/agent-flow/:analysisId` | **Agent 协同可视化页**（占位）。将展示 ECharts 流程图 + SSE 实时 Agent 状态推送 |
| `UserCenterView.vue` | `/user-center` | **用户中心页**（占位）。将展示用户画像编辑（四维度）+ 收藏论文列表 + 历史会话 |

---

### 📁 `dist/` — 构建产物

Vite 构建输出目录，已 `.gitignore`。包含经过代码分割和压缩的生产环境文件：

| 文件 | 说明 |
|------|------|
| `index.html` | 入口 HTML |
| `favicon.svg` / `icons.svg` | 静态资源 |
| `assets/index-*.js` | 入口 + 路由逻辑 |
| `assets/vendor-*.js` | Vue/VueRouter/Pinia/Axios |
| `assets/element-plus-*.js` | Element Plus 按需导入 |
| `assets/element-plus-*.css` | Element Plus 样式 |
| `assets/*View-*.js` | 各页面懒加载 chunk |

---

## 根目录配置文件

| 文件 | 说明 |
|------|------|
| `package.json` | 项目元数据（`literature-assistant-frontend` v0.1.0，ESM 模式，`private: true`）。脚本：`dev`(开发服务器)/`build`(类型检查+构建)/`preview`(预览构建产物)/`typecheck`(类型检查)/`test`(Vitest 单元测试)/`test:run`(单次运行测试) |
| `package-lock.json` | npm 依赖锁定文件，确保团队依赖版本一致 |
| `vite.config.ts` | **Vite 构建配置**。插件：Vue SFC + AutoImport（Vue/VueRouter/Pinia 自动导入 + Element Plus 按需导入）+ Components（Element Plus 组件自动注册）。路径别名 `@` → `src/`。SCSS 全局注入 `variables.scss`。构建优化：Element Plus / ECharts / Vue 生态三分包。开发代理：`/api` → `http://localhost:8080`（Java 后端），SSE 响应特殊处理（禁用缓存和缓冲） |
| `vite.config.js` | `vite.config.ts` 编译产物 |
| `vite.config.d.ts` | `vite.config.ts` 类型声明 |
| `vite.config.d.ts.map` | Source Map |
| `tsconfig.json` | TypeScript 项目配置，strict 模式，引用 `tsconfig.node.json` |
| `tsconfig.node.json` | Node 环境 TypeScript 配置（Vite 配置文件用） |
| `tsconfig.tsbuildinfo` | TypeScript 增量编译信息 |
| `index.html` | **HTML 入口**。中文语言设定，引入 `favicon.svg`，挂载点 `<div id="app">`，加载 `src/main.ts` |
| `.env.development` | 开发环境变量：`VITE_API_BASE_URL=http://localhost:8080/api`（直连 Java 后端） |
| `.env.production` | 生产环境变量：`VITE_API_BASE_URL=/api`（通过 Nginx 反向代理） |
| `Dockerfile` | **多阶段构建**。第一阶段：Node 18 Alpine 安装依赖并构建；第二阶段：Nginx 1.25 Alpine 部署产物，非 root 用户运行，内置健康检查 |
| `.dockerignore` | Docker 构建排除文件（node_modules/dist 等） |
| `.gitignore` | Git 忽略规则（node_modules/dist/.env.local 等） |
| `.vscode/extensions.json` | VS Code 推荐扩展：Vue.volar |
| `README.md` | 本文件 |

---

## 开发指南

### 安装与启动

```bash
# 安装依赖
npm install

# 启动开发服务器（默认 http://localhost:5173）
npm run dev

# 类型检查
npm run typecheck

# 构建生产版本
npm run build

# 预览构建产物
npm run preview

# 运行单元测试
npm run test
```

### 开发约定

| 约定 | 规范 |
|------|------|
| 组件写法 | `<script setup lang="ts">` + Composition API + scoped 样式 |
| 命名规范 | 页面 `{Name}View.vue`，组件 `{Name}.vue`，Store `{domain}Store.ts`，组合函数 `use{Name}.ts` |
| 状态管理 | Pinia Setup Store 风格，按业务域划分 |
| API 调用 | 统一通过 `src/api/` 下的模块化 API 封装调用，底层共享 `index.ts` 的 Axios 实例，不直接使用原生 axios |
| 路由 | 懒加载 + `meta.requiresAuth` + 全局前置守卫 |
| 样式 | SCSS，全局变量使用 `variables.scss` 中定义的 CSS 自定义属性 |
| 自动导入 | Vue/VueRouter/Pinia API 和 Element Plus 组件无需手动 import |

### API 代理说明

开发环境下，Vite 将 `/api` 开头的请求代理到 `http://localhost:8080`（Java 后端），并对 SSE 响应做特殊处理（禁用缓存和 Nginx 缓冲），确保 Agent 状态实时推送正常工作。

---

## 项目进度

| 模块 | 状态 | 说明 |
|------|------|------|
| 项目脚手架 | ✅ 已完成 | Vue3 + Vite + TS + Element Plus + Pinia + Router |
| 全局布局 | ✅ 已完成 | AppHeader + AppFooter + Flex 三段式布局 |
| 首页搜索 | ✅ 已完成 | 搜索输入 + 最近搜索标签 |
| API 封装 | ✅ 已完成 | Axios 拦截器 + JWT 注入 + 统一错误处理 + 5 个业务 API 模块 |
| 类型体系 | ✅ 已完成 | 6 个类型文件覆盖全部业务域 |
| Store 层 | ✅ 已完成 | 4 个 Store 已实现状态/计算属性/API 调用方法 |
| 路由守卫 | ✅ 已完成 | 认证检查 + 登录重定向 |
| 构建优化 | ✅ 已完成 | 三分包（Element Plus / ECharts / Vendor） |
| Docker 部署 | ✅ 已完成 | 多阶段构建 + Nginx + 健康检查 |
| 业务页面 | ⏳ 待开发 | 9 个页面中仅首页已实现，其余为占位符 |
| 业务组件 | ⏳ 待开发 | 5 个业务组件目录均为空（layout 已完成） |
| 组合函数 | ⏳ 待开发 | composables/ 为空（useSSE 等待开发） |
| 工具函数 | ⏳ 待开发 | utils/ 为空 |
| 单元测试 | ⏳ 待开发 | Vitest 已配置，尚无测试用例 |
