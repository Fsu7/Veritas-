# Task 00: Vue3+Vite项目创建 + TypeScript + 依赖安装

## 项目
XH-202630 科研文献智能助手 — 领域知识个性化生成与多智能体协同决策系统研究

## 版本与里程碑
- 版本：v0.1
- 里程碑：M1 / FM1：项目骨架与基础设施就绪

## 需求描述
创建Vue3+Vite前端项目骨架，配置TypeScript，安装项目所有核心依赖（Vue3、TypeScript、Vite、Element Plus、ECharts、Pinia、Vue Router、Axios、markdown-it、Sass、unplugin-auto-import、unplugin-vue-components），生成基础目录结构，创建入口文件main.ts和根组件App.vue，确保npm run dev可正常启动。

## 涉及层级
前端（frontend）

## 修改范围

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | Veritas/frontend/package.json | 项目依赖配置 |
| 新增 | Veritas/frontend/index.html | HTML入口 |
| 新增 | Veritas/frontend/src/main.ts | 应用入口 |
| 新增 | Veritas/frontend/src/App.vue | 根组件 |
| 新增 | Veritas/frontend/src/views/HomeView.vue | 首页骨架 |
| 新增 | Veritas/frontend/src/router/index.ts | 路由配置（9条路由+守卫） |
| 新增 | Veritas/frontend/src/stores/*.ts | 4个Pinia Store骨架 |
| 新增 | Veritas/frontend/src/api/index.ts | Axios实例+拦截器 |
| 新增 | Veritas/frontend/src/types/*.ts | 5个TypeScript类型文件 |
| 新增 | Veritas/frontend/src/styles/*.scss | 全局样式+CSS变量 |
| 新增 | Veritas/frontend/src/components/layout/*.vue | AppHeader+AppFooter |

## 核心依赖
- vue@^3.4, typescript@^5.0, vite@^5.0
- element-plus@^2.5, echarts@^5.4, pinia@^2.1
- vue-router@^4.2, axios@^1.6, markdown-it@^14.0
- sass@^1.77, unplugin-auto-import, unplugin-vue-components

## 关键实现要求
1. 使用`<script setup lang="ts">` + Composition API
2. 9条路由全部懒加载，设置requiresAuth元数据
3. Axios请求拦截器注入JWT Token，响应拦截器统一错误处理
4. 4个Pinia Store使用setup store风格
5. TypeScript类型定义与API契约一致（JSON字段统一snake_case）
6. Agent状态色CSS变量：waiting/#C0C4CC, running/#409EFF, completed/#67C23A, failed/#F56C6C

## 禁止行为
- ❌ 使用Options API
- ❌ 组件中直接调用Axios
- ❌ 硬编码敏感配置
- ❌ 单个组件超过300行
- ❌ JSON字段使用camelCase

## 验收标准
- [ ] npm run dev启动成功，首页可访问
- [ ] TypeScript编译无错误
- [ ] 9条路由懒加载生效
- [ ] 路由守卫拦截未登录用户
- [ ] Axios拦截器正确处理401
- [ ] 4个Store可正常创建
- [ ] npm run build构建成功
