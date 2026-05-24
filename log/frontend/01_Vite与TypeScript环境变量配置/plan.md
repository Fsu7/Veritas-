# Task01 实施计划：Vite/TypeScript/环境变量配置

## 任务概述

配置前端项目基础设施：Vite构建工具、TypeScript编译选项、环境变量文件，实现Element Plus自动按需导入、ECharts按需导入、路径别名、manualChunks分包、TypeScript strict模式、开发代理、环境变量。

---

## 现状分析

### 已有文件（task00创建）

| 文件 | 状态 | 差距 |
|------|------|------|
| `vite.config.ts` | ✅ 已存在 | 缺少 server proxy 配置（/api → localhost:8080 + SSE支持） |
| `tsconfig.json` | ✅ 已存在 | 当前为 solution-style（files:[] + references），需重构为含 compilerOptions 的主配置 |
| `tsconfig.app.json` | ✅ 已存在 | 选项基本齐全，将合并到 tsconfig.json |
| `tsconfig.node.json` | ✅ 已存在 | target 需从 ES2023 改为 ES2022，需添加 allowSyntheticDefaultImports |
| `env.d.ts` | ✅ 已存在 | 已声明 VITE_APP_TITLE 和 VITE_API_BASE_URL，无需修改 |
| `.env` | ❌ 不存在 | 需创建 |
| `.env.development` | ❌ 不存在 | 需创建 |
| `.env.production` | ❌ 不存在 | 需创建 |

### 关键决策

1. **tsconfig 结构**：将 tsconfig.app.json 合并到 tsconfig.json，删除 tsconfig.app.json。理由：prompt.json 明确要求 tsconfig.json 包含 compilerOptions + include + references，且验收命令为 `vue-tsc --noEmit`，两文件结构更简洁
2. **.env 文件不加入 .gitignore**：仅含 VITE_ 前缀非敏感变量，符合 Vite 惯例（.env.local 才 gitignore）
3. **ECharts 按需导入**：不在 vite.config.ts 中配置全局导入，而是在组件中按需 import（FR-010）

---

## 实施步骤

### Step 1：修改 vite.config.ts — 添加 server proxy

**文件**：`Veritas/frontend/vite.config.ts`

**变更**：在 `defineConfig` 中添加 `server` 配置块

```ts
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

**对应需求**：FR-004（开发代理 + SSE 支持）

---

### Step 2：重构 tsconfig.json — 合并 app 配置

**文件**：`Veritas/frontend/tsconfig.json`

**变更**：从 solution-style 重构为包含完整 compilerOptions 的主配置

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "jsx": "preserve",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "esModuleInterop": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "noEmit": true,
    "types": ["vite/client"],
    "paths": {
      "@/*": ["./src/*"]
    },
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src/**/*.ts", "src/**/*.tsx", "src/**/*.vue"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

**对应需求**：FR-005（strict 模式 + 路径别名 + 编译选项）

---

### Step 3：更新 tsconfig.node.json

**文件**：`Veritas/frontend/tsconfig.node.json`

**变更**：target 从 ES2023 改为 ES2022，添加 allowSyntheticDefaultImports

```json
{
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.node.tsbuildinfo",
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "types": ["node"],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "verbatimModuleSyntax": true,
    "moduleDetection": "force",
    "noEmit": true,
    "allowSyntheticDefaultImports": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["vite.config.ts"]
}
```

**对应需求**：FR-006（Node 环境 TS 配置）

---

### Step 4：删除 tsconfig.app.json

**文件**：`Veritas/frontend/tsconfig.app.json`

**操作**：删除（已合并到 tsconfig.json）

---

### Step 5：创建 .env 公共环境变量

**文件**：`Veritas/frontend/.env`

```
VITE_APP_TITLE=科研文献智能助手
```

**对应需求**：FR-007

---

### Step 6：创建 .env.development 开发环境变量

**文件**：`Veritas/frontend/.env.development`

```
VITE_API_BASE_URL=http://localhost:8080/api
```

**对应需求**：FR-008

---

### Step 7：创建 .env.production 生产环境变量

**文件**：`Veritas/frontend/.env.production`

```
VITE_API_BASE_URL=/api
```

**对应需求**：FR-009

---

### Step 8：验证

1. `cd Veritas/frontend && npx vue-tsc --noEmit` — TypeScript 编译无错误
2. `cd Veritas/frontend && npm run build` — 生产构建成功，dist/ 包含独立 chunk
3. 检查构建产物是否包含 element-plus、echarts、vendor 独立 chunk

---

## 需求覆盖矩阵

| 需求ID | 描述 | 实施步骤 | 验证方式 |
|--------|------|---------|---------|
| FR-001 | Element Plus 自动按需导入 | 已有（task00） | build 产物检查 |
| FR-002 | 路径别名 @/ 映射 | 已有（task00） | vue-tsc 编译 |
| FR-003 | manualChunks 分包 | 已有（task00） | build 产物检查 |
| FR-004 | 开发代理 + SSE | Step 1 | 代码审查 |
| FR-005 | tsconfig.json strict 模式 | Step 2 | vue-tsc --noEmit |
| FR-006 | tsconfig.node.json | Step 3 | vue-tsc --noEmit |
| FR-007 | .env 公共变量 | Step 5 | 代码审查 |
| FR-008 | .env.development | Step 6 | 代码审查 |
| FR-009 | .env.production | Step 7 | 代码审查 |
| FR-010 | ECharts 按需导入 | 不在 vite.config 配置 | 组件中按需 import |

## 禁止操作检查

| ID | 禁止操作 | 状态 |
|----|---------|------|
| FA-001 | 输出伪代码或TODO注释 | ✅ 全部为完整可执行代码 |
| FA-002 | 环境变量硬编码API Key | ✅ 仅含 VITE_ 前缀非敏感配置 |
| FA-003 | 全局导入 Element Plus | ✅ 使用 AutoImport + Components 按需导入 |
| FA-004 | 全局导入 ECharts | ✅ 不在 vite.config 中配置全局导入 |
| FA-005 | 关闭 TypeScript strict | ✅ strict: true |
| FA-006 | 修改 task00 已创建文件 | ⚠️ 仅修改 vite.config.ts 和 tsconfig 文件（属于本任务范围） |
