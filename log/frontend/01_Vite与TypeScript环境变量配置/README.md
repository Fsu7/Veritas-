# Vite与TypeScript环境变量配置

## 功能描述
- 解决了前端项目构建工具、TypeScript编译、环境变量三大基础设施的配置问题
- 实现了 Element Plus 自动按需导入、路径别名 `@/` 映射、manualChunks 分包策略、开发环境 API 代理（含 SSE 支持）、TypeScript strict 模式、多环境变量管理
- 业务价值：为后续所有前端功能开发提供标准化构建与类型安全基础，确保开发体验和构建产物质量

## 实现逻辑

### 修改的核心文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `Veritas/frontend/vite.config.ts` | 修改 | 添加 `server.proxy` 配置，`/api` → `http://localhost:8080`，含 SSE 响应头处理 |
| `Veritas/frontend/tsconfig.json` | 重构 | 从 solution-style（files:[] + references）重构为含完整 compilerOptions 的主配置 |
| `Veritas/frontend/tsconfig.node.json` | 更新 | target ES2022、composite、emitDeclarationOnly、allowSyntheticDefaultImports |
| `Veritas/frontend/tsconfig.app.json` | 删除 | 已合并到 tsconfig.json |
| `Veritas/frontend/.env` | 创建 | 公共环境变量 `VITE_APP_TITLE` |
| `Veritas/frontend/.env.development` | 创建 | 开发环境 `VITE_API_BASE_URL=http://localhost:8080/api` |
| `Veritas/frontend/.env.production` | 创建 | 生产环境 `VITE_API_BASE_URL=/api` |

### 使用的算法或设计模式

1. **manualChunks 分包策略**：将 element-plus、echarts、vendor（vue/vue-router/pinia/axios）拆分为独立 chunk，优化首屏加载
2. **SSE 代理配置**：通过 `configure` 钩子监听 `proxyRes` 事件，对 `text/event-stream` 响应设置 `cache-control: no-cache` 和 `x-accel-buffering: no`，防止 SSE 流被代理缓存
3. **TypeScript 项目引用（Project References）**：tsconfig.json 引用 tsconfig.node.json，实现应用代码与构建配置的独立类型检查

### 关键代码逻辑说明

**Vite 开发代理 + SSE 支持**：
```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8080',
      changeOrigin: true,
      configure: (proxy) => {
        proxy.on('proxyRes', (proxyRes) => {
          if (proxyRes.headers['content-type']?.includes('text/event-stream')) {
            proxyRes.headers['cache-control'] = 'no-cache'
            proxyRes.headers['x-accel-buffering'] = 'no'
          }
        })
      }
    }
  }
}
```

**tsconfig.json 核心配置**：
- `strict: true` — 开启 TypeScript 严格模式
- `moduleResolution: "bundler"` — 适配 Vite 的模块解析策略
- `paths: { "@/*": ["./src/*"] }` — 与 vite.config.ts 的 resolve.alias 保持一致
- `references: [{ "path": "./tsconfig.node.json" }]` — 项目引用分离

**tsconfig.node.json 关键配置**：
- `composite: true` + `emitDeclarationOnly: true` — 满足 TypeScript 项目引用要求（被引用项目不能设置 noEmit）
- `allowSyntheticDefaultImports: true` — 允许从没有默认导出的模块中默认导入

## 接口变更

### Request
本次为配置任务，不涉及 API 接口变更。

### Response
本次为配置任务，不涉及 API 接口变更。

## 测试结果

- **TypeScript 编译测试**：`npx vue-tsc --noEmit` — ✅ 通过，零错误
- **生产构建测试**：`npm run build` — ✅ 通过，构建产物包含独立 chunk
  - `element-plus-B2bLDiJm.js` (960.99 kB)
  - `element-plus-COR10v1i.css` (356.00 kB)
  - `vendor-BTzWDtiW.js` (30.65 kB)
  - `echarts` chunk 将在组件使用 ECharts 后自动生成
- **环境变量验证**：`.env` / `.env.development` / `.env.production` 内容正确
- **路径别名验证**：`@/` 映射正常，router 中 `import('@/views/xxx')` 可正确解析
- **是否通过**：是

## 相关文件

### 配置文件
- `Veritas/frontend/vite.config.ts` — Vite 构建配置
- `Veritas/frontend/tsconfig.json` — TypeScript 主配置
- `Veritas/frontend/tsconfig.node.json` — Node 环境 TypeScript 配置
- `Veritas/frontend/.env` — 公共环境变量
- `Veritas/frontend/.env.development` — 开发环境变量
- `Veritas/frontend/.env.production` — 生产环境变量
- `Veritas/frontend/src/env.d.ts` — 环境变量类型声明（task00 已创建，无需修改）

### 额外修复的 task00 遗留问题
- `Veritas/frontend/src/views/LoginView.vue` — 占位页面（router 引用缺失）
- `Veritas/frontend/src/views/RegisterView.vue` — 占位页面
- `Veritas/frontend/src/views/SearchView.vue` — 占位页面
- `Veritas/frontend/src/views/PaperDetailView.vue` — 占位页面
- `Veritas/frontend/src/views/CompareView.vue` — 占位页面
- `Veritas/frontend/src/views/ReportView.vue` — 占位页面
- `Veritas/frontend/src/views/AgentFlowView.vue` — 占位页面
- `Veritas/frontend/src/views/UserCenterView.vue` — 占位页面
- `Veritas/frontend/src/views/HomeView.vue` — 修复中文引号与 HTML 属性冲突
