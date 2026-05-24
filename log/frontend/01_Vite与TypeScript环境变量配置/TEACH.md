# 技术教学文档 — Vite与TypeScript环境变量配置

## 开发思路

### 需求分析过程

本次任务（task01）属于 FM1 里程碑"项目骨架与基础设施就绪"的前端配置部分。需求来源为 `prompt.json` 中定义的 10 个功能需求（FR-001 ~ FR-010），核心目标：

1. **构建工具配置**：Vite 插件注册、路径别名、分包策略、开发代理
2. **TypeScript 配置**：strict 模式、模块解析、路径别名一致性
3. **环境变量**：多环境（公共/开发/生产）变量管理

分析现有代码发现，task00 已完成部分工作（Element Plus 按需导入、路径别名、manualChunks），但缺少开发代理和完整的环境变量体系。

### 技术选型考虑

| 决策点 | 选项 | 最终选择 | 理由 |
|--------|------|---------|------|
| tsconfig 结构 | 三文件（json + app + node）vs 两文件（json + node） | 两文件 | prompt.json 明确要求 tsconfig.json 包含 compilerOptions + include + references，两文件更简洁 |
| SSE 代理支持 | 简单 proxy vs configure 钩子 | configure 钩子 | 需要为 SSE 响应设置 `cache-control: no-cache` 和 `x-accel-buffering: no`，简单 proxy 无法实现 |
| ECharts 导入方式 | 全局注册 vs 按需导入 | 按需导入 | FR-010 明确要求按需导入减小打包体积，不在 vite.config.ts 中配置 |
| .env 是否 gitignore | 忽略 vs 提交 | 提交 | 仅含 VITE_ 前缀非敏感变量，Vite 惯例是 .env.local 才忽略 |

### 架构设计思路

```
前端配置架构
├── vite.config.ts          ← 构建配置中心
│   ├── plugins             ← Vue3 + AutoImport + Components（Element Plus 按需导入）
│   ├── resolve.alias       ← @/ → src/（与 tsconfig paths 一致）
│   ├── css preprocessor    ← SCSS 全局变量注入
│   ├── build.manualChunks  ← 分包策略（element-plus / echarts / vendor）
│   └── server.proxy        ← /api → localhost:8080（含 SSE 支持）
├── tsconfig.json           ← 应用代码 TS 配置
│   ├── strict: true        ← 严格模式
│   ├── paths: @/*          ← 路径别名（与 vite alias 一致）
│   └── references          ← 引用 tsconfig.node.json
├── tsconfig.node.json      ← 构建配置 TS 配置
│   ├── composite: true     ← 项目引用要求
│   └── emitDeclarationOnly ← 配合 allowImportingTsExtensions
├── .env                    ← 公共变量（VITE_APP_TITLE）
├── .env.development        ← 开发变量（VITE_API_BASE_URL=http://localhost:8080/api）
└── .env.production         ← 生产变量（VITE_API_BASE_URL=/api）
```

### 遇到的问题及解决方案

**问题1：tsconfig.node.json 的 `noEmit` 与项目引用冲突**
- 现象：`vue-tsc --noEmit` 通过，但 `vue-tsc -b`（build 模式）报错 `TS6310: Referenced project may not disable emit`
- 原因：TypeScript 项目引用要求被引用的项目必须启用声明文件生成，不能设置 `noEmit: true`
- 解决：将 `noEmit` 替换为 `composite: true` + `emitDeclarationOnly: true` + `declaration: true` + `declarationMap: true`

**问题2：`allowImportingTsExtensions` 与 `emitDeclarationOnly` 的兼容**
- 现象：`vue-tsc -b` 报错 `TS5096: Option 'allowImportingTsExtensions' can only be used when one of 'noEmit', 'emitDeclarationOnly', or 'rewriteRelativeImportExtensions' is set`
- 原因：`allowImportingTsExtensions` 要求不生成 JS 输出，而 `composite: true` 默认会生成
- 解决：添加 `emitDeclarationOnly: true`，只生成 `.d.ts` 声明文件，不生成 JS

**问题3：HomeView.vue 中文引号与 HTML 属性冲突**
- 现象：Vite 构建报错 `Attribute name cannot contain U+0022 (")`
- 原因：`placeholder="输入研究主题，如"Multi-Agent协同决策""` 中中文引号 `""` 被 HTML 解析器误认为属性分隔符
- 解决：将外层双引号改为单引号：`placeholder='输入研究主题，如"Multi-Agent协同决策"'`

**问题4：router 引用的 View 文件不存在导致构建失败**
- 现象：`npm run build` 报 9 个 `UNLOADABLE_DEPENDENCY` 错误
- 原因：task00 创建了 router 但未创建对应的 View 文件
- 解决：创建 8 个占位 View 文件（LoginView、RegisterView 等），遵循 `<script setup lang="ts">` 规范

## 实现步骤

1. **分析现有代码**：读取 task00 已创建的 vite.config.ts、tsconfig.json、tsconfig.app.json、tsconfig.node.json、env.d.ts，评估差距
2. **修改 vite.config.ts**：在 `build` 配置后添加 `server.proxy` 配置块，实现 `/api` 代理 + SSE 响应头处理
3. **重构 tsconfig.json**：将 tsconfig.app.json 的 compilerOptions 合并到 tsconfig.json，从 solution-style 改为完整配置
4. **更新 tsconfig.node.json**：target 改为 ES2022，添加 composite/emitDeclarationOnly/allowSyntheticDefaultImports
5. **删除 tsconfig.app.json**：已合并到 tsconfig.json，避免冗余
6. **创建环境变量文件**：`.env`（公共）、`.env.development`（开发）、`.env.production`（生产）
7. **验证**：`vue-tsc --noEmit` + `npm run build`，修复过程中发现的编译和构建错误
8. **创建占位 View 文件**：解决 router 引用缺失问题

## 解决了什么问题

### 核心问题描述

前端项目缺少完整的构建配置体系：
- 开发环境无法代理 API 请求到 Java 后端
- TypeScript 配置分散在三个文件中，维护成本高
- 没有多环境变量管理，API 地址硬编码风险高
- SSE（Server-Sent Events）在代理环境下可能被缓存导致实时推送失效

### 解决方案对比

| 方案 | 优点 | 缺点 | 最终选择 |
|------|------|------|---------|
| 三文件 tsconfig | 职责分离更清晰 | 不符合 prompt.json 要求，维护复杂 | ❌ |
| 两文件 tsconfig | 简洁，符合需求规格 | 被引用项目需 composite 配置 | ✅ |
| 简单 proxy 配置 | 配置简单 | 不支持 SSE 缓存控制 | ❌ |
| configure 钩子 proxy | SSE 支持完善 | 代码稍复杂 | ✅ |

### 最终方案的优势

1. **两文件 tsconfig 结构**：减少维护成本，符合项目规范要求
2. **SSE 感知代理**：确保 Agent 状态实时推送在开发环境下正常工作
3. **多环境变量**：开发/生产环境 API 地址自动切换，无需手动修改代码

## 变更内容

### 新增文件

| 文件路径 | 作用 |
|---------|------|
| `Veritas/frontend/.env` | 公共环境变量：`VITE_APP_TITLE=科研文献智能助手` |
| `Veritas/frontend/.env.development` | 开发环境变量：`VITE_API_BASE_URL=http://localhost:8080/api` |
| `Veritas/frontend/.env.production` | 生产环境变量：`VITE_API_BASE_URL=/api` |
| `Veritas/frontend/src/views/LoginView.vue` | 登录页占位组件 |
| `Veritas/frontend/src/views/RegisterView.vue` | 注册页占位组件 |
| `Veritas/frontend/src/views/SearchView.vue` | 论文检索页占位组件 |
| `Veritas/frontend/src/views/PaperDetailView.vue` | 论文详情页占位组件 |
| `Veritas/frontend/src/views/CompareView.vue` | 论文对比页占位组件 |
| `Veritas/frontend/src/views/ReportView.vue` | 综述报告页占位组件 |
| `Veritas/frontend/src/views/AgentFlowView.vue` | Agent 可视化页占位组件 |
| `Veritas/frontend/src/views/UserCenterView.vue` | 用户中心页占位组件 |

### 修改文件

| 文件路径 | 变更点 |
|---------|--------|
| `Veritas/frontend/vite.config.ts` | 添加 `server.proxy` 配置块：`/api` → `http://localhost:8080`，含 SSE 响应头处理 |
| `Veritas/frontend/tsconfig.json` | 从 solution-style 重构为含完整 compilerOptions 的主配置，合并 tsconfig.app.json |
| `Veritas/frontend/tsconfig.node.json` | target ES2023→ES2022，添加 composite/emitDeclarationOnly/allowSyntheticDefaultImports |
| `Veritas/frontend/src/views/HomeView.vue` | 修复中文引号与 HTML 属性冲突（第38行） |

### 删除文件

| 文件路径 | 原因 |
|---------|------|
| `Veritas/frontend/tsconfig.app.json` | 已合并到 tsconfig.json，避免冗余 |

### 配置变更

| 配置项 | 变更前 | 变更后 | 说明 |
|--------|-------|--------|------|
| `vite.config.ts > server.proxy` | 无 | `/api` → `localhost:8080` + SSE | 开发环境 API 代理 |
| `tsconfig.json > compilerOptions` | `files: []`（solution-style） | 完整 compilerOptions | 合并 app 配置 |
| `tsconfig.node.json > target` | `ES2023` | `ES2022` | 符合需求规格 |
| `tsconfig.node.json > composite` | 无 | `true` | 项目引用要求 |
| `tsconfig.node.json > emitDeclarationOnly` | 无 | `true` | 配合 allowImportingTsExtensions |
| `tsconfig.node.json > allowSyntheticDefaultImports` | 无 | `true` | 允许默认导入 |

## 关键技术点

### 1. TypeScript 项目引用（Project References）

TypeScript 的项目引用机制允许将大型项目拆分为多个子项目，各自独立进行类型检查。关键规则：
- 被引用的项目必须设置 `composite: true`
- `composite` 要求至少设置 `declaration: true` 或 `emitDeclarationOnly: true`
- 不能同时设置 `noEmit: true`（因为需要生成声明文件）
- `vue-tsc -b` 使用 build 模式，会检查项目引用的完整性

### 2. Vite 代理中的 SSE 支持

SSE（Server-Sent Events）是本项目 Agent 状态实时推送的核心通信方式。在开发环境中，Vite 代理需要特殊处理：
- `cache-control: no-cache` — 防止浏览器缓存 SSE 事件流
- `x-accel-buffering: no` — 防止 Nginx 等反向代理缓冲 SSE 响应
- 通过 `http-proxy` 的 `configure` 钩子，在 `proxyRes` 事件中检测 `content-type` 是否包含 `text/event-stream`，动态设置响应头

### 3. manualChunks 分包策略

Vite/Rolldown 的 `manualChunks` 配置允许将指定模块拆分为独立 chunk：
- `element-plus` — UI 组件库，体积大（~960KB），独立 chunk 可利用浏览器缓存
- `echarts` — 图表库，按需导入后独立 chunk 只包含使用的图表类型
- `vendor` — 框架核心（vue/vue-router/pinia/axios），变更频率低，长期缓存

### 4. Vite 环境变量机制

- 只有 `VITE_` 前缀的变量才会暴露给客户端代码（通过 `import.meta.env`）
- `.env` — 所有环境加载
- `.env.development` — `npm run dev` 时加载（覆盖 .env）
- `.env.production` — `npm run build` 时加载（覆盖 .env）
- `.env.local` / `.env.*.local` — 本地覆盖，应加入 .gitignore

### 5. unplugin-auto-import 与 unplugin-vue-components

这两个插件配合 Element Plus Resolver 实现自动按需导入：
- `AutoImport` — 自动导入 Element Plus 的 API（如 `ElMessage`、`ElNotification`）
- `Components` — 自动注册 Element Plus 组件（如 `<el-button>`、`<el-input>`）
- 生成 `auto-imports.d.ts` 和 `components.d.ts` 类型声明文件

## 经验总结

### 开发过程中的收获

1. **TypeScript 项目引用不是简单的文件拆分**：它涉及 composite、declaration、emitDeclarationOnly 等配置的联动，需要理解每个选项的含义和约束
2. **Vite 8.x 使用 Rolldown 替代 Rollup**：构建产物命名和分包行为与 Vite 5.x 有差异，需要注意兼容性
3. **SSE 在代理环境下的特殊性**：普通 HTTP 请求通过代理没问题，但 SSE 长连接需要禁用缓存和缓冲，否则客户端收不到实时事件

### 踩过的坑及如何避免

1. **tsconfig.node.json 不能用 noEmit**：被引用的项目必须能生成声明文件。记住：`composite + emitDeclarationOnly` 替代 `noEmit`
2. **HTML 属性中的中文引号**：中文引号 `""` 的 Unicode 码点与英文双引号 `"` 不同，但某些 HTML 解析器会混淆。建议在 HTML 属性值中使用单引号包裹含中文引号的内容
3. **router 引用的 View 文件必须存在**：即使使用懒加载 `() => import()`，Vite 构建时仍会解析模块依赖，文件不存在会报错。开发阶段应创建占位文件

### 最佳实践建议

1. **tsconfig 配置先跑通 `vue-tsc -b` 再做其他事**：`vue-tsc -b` 是最严格的检查模式，通过它意味着 `vue-tsc --noEmit` 和 IDE 类型检查都能正常工作
2. **环境变量类型声明要及时更新**：每次新增 `VITE_` 变量，都要在 `env.d.ts` 中添加对应类型声明，否则 TypeScript 会报类型错误
3. **分包策略要结合实际使用情况**：`echarts` 在 manualChunks 中声明但未实际 import 时不会生成 chunk，这是正常行为，不要误以为配置错误
4. **开发代理配置要与 Nginx 生产配置对齐**：确保开发环境和生产环境的 API 路径一致（都是 `/api`），只是代理目标不同
