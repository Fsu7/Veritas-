# Task 01: vite.config.ts + tsconfig.json + .env配置

## 项目
XH-202630 科研文献智能助手 — 领域知识个性化生成与多智能体协同决策系统研究

## 版本与里程碑
- 版本：v0.1
- 里程碑：M1 / FM1：项目骨架与基础设施就绪

## 需求描述
配置Vite构建工具（vite.config.ts）、TypeScript编译选项（tsconfig.json + tsconfig.node.json）和环境变量（.env + .env.development + .env.production），实现Element Plus自动按需导入、ECharts按需导入、路径别名@/映射、manualChunks分包策略、TypeScript strict模式、环境变量VITE_API_BASE_URL配置。

## 涉及层级
前端（frontend）

## 前置任务
- task00_vue3_vite_project（项目骨架和依赖已安装）

## 修改范围

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | Veritas/frontend/vite.config.ts | Vite构建配置 |
| 新增 | Veritas/frontend/tsconfig.json | TypeScript主配置 |
| 新增 | Veritas/frontend/tsconfig.node.json | Node环境TS配置 |
| 新增 | Veritas/frontend/.env | 公共环境变量 |
| 新增 | Veritas/frontend/.env.development | 开发环境变量 |
| 新增 | Veritas/frontend/.env.production | 生产环境变量 |

## 关键实现要求

### vite.config.ts
1. 插件：@vitejs/plugin-vue + unplugin-auto-import（ElementPlusResolver）+ unplugin-vue-components（ElementPlusResolver）
2. 路径别名：`@` → `/src`
3. 分包策略：element-plus / echarts / vendor 独立chunk
4. 开发代理：`/api` → `http://localhost:8080`，changeOrigin: true
5. SSE支持：代理配置不缓存

### tsconfig.json
1. strict: true
2. target: ES2020, module: ESNext, moduleResolution: bundler
3. paths: `@/*` → `./src/*`
4. lib: ['ES2020', 'DOM', 'DOM.Iterable']
5. references: [{ path: './tsconfig.node.json' }]

### 环境变量
1. .env: VITE_APP_TITLE=科研文献智能助手
2. .env.development: VITE_API_BASE_URL=http://localhost:8080/api
3. .env.production: VITE_API_BASE_URL=/api

## 禁止行为
- ❌ 全局导入Element Plus
- ❌ 全局导入ECharts
- ❌ 关闭TypeScript strict模式
- ❌ 环境变量中硬编码API Key或JWT Secret

## 验收标准
- [ ] Element Plus自动按需导入生效
- [ ] 路径别名@/正确解析
- [ ] manualChunks分包：3个独立chunk
- [ ] 开发代理/api到8080
- [ ] TypeScript strict编译无错误
- [ ] 环境变量VITE_API_BASE_URL正确读取
- [ ] npm run build构建成功
