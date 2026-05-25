# XH-202630 科研文献智能助手 — 前端 FM1 里程碑审阅报告

> **审阅阶段**：FM1 项目骨架与基础设施就绪
> **审阅日期**：2026-05-25
> **审阅范围**：`Veritas/frontend/` 全部代码
> **对照文档**：前端模块系统架构文档 + 前端模块项目里程碑文档
> **审阅结论**：✅ 通过（含2项待改进）

---

## 1 FM1 验收检查清单逐项验证

| # | 检查项 | 状态 | 验证详情 |
|---|--------|------|---------|
| 1 | Vue3启动: npm run dev 无报错 | ✅ 通过 | Vite v8.0.14 启动成功，385ms就绪，`http://localhost:5173/` 可访问 |
| 2 | 首页访问: 浏览器访问 http://localhost:5173 显示首页 | ✅ 通过 | HomeView.vue 完整实现，含主题输入框、最近搜索标签 |
| 3 | TypeScript: strict模式编译无错误 | ✅ 通过 | `vue-tsc --noEmit` 退出码0，tsconfig.json strict:true + noUnusedLocals + noUnusedParameters + noFallthroughCasesInSwitch |
| 4 | 路由: 9条路由定义正确，懒加载生效 | ✅ 通过 | 9条路由全部使用 `() => import(...)` 懒加载 |
| 5 | 路由守卫: 未登录访问/requiresAuth页面跳转/login | ✅ 通过 | beforeEach 正确实现：requiresAuth→跳转Login+redirect参数；已登录访问Login/Register→跳转Home |
| 6 | Axios: 请求拦截器注入Token，响应拦截器处理401 | ✅ 通过 | 请求拦截器注入 `Bearer ${token}`；响应拦截器处理 401/403/404/ECONNABORTED |
| 7 | Pinia: 4个Store可正常创建和访问 | ✅ 通过 | userStore / paperStore / sessionStore / agentStore 全部使用 setup store 风格 |
| 8 | 类型定义: 5个类型文件编译无错误 | ✅ 通过 | paper.ts / user.ts / analysis.ts / agent.ts / common.ts + session.ts = 6个文件，全部编译通过 |
| 9 | Element Plus: 自动按需导入生效 | ✅ 通过 | unplugin-auto-import + unplugin-vue-components + ElementPlusResolver |
| 10 | ECharts: 按需导入配置正确 | ⚠️ 部分 | manualChunks 分包已配置，但**ECharts 按需导入未实现**（当前全量导入） |
| 11 | 环境变量: VITE_API_BASE_URL正确读取 | ✅ 通过 | .env.development 配置完整；env.d.ts 声明了 ImportMetaEnv 类型 |
| 12 | Docker: docker build 构建镜像成功 | ✅ 通过 | 多阶段构建（node:18-alpine → nginx:1.25-alpine），含 HEALTHCHECK，非root用户 |
| 13 | Nginx: try_files SPA路由 + /api/代理配置 | ✅ 通过 | try_files + proxy_pass java-backend:8080 + 安全头 |
| 14 | SSE: Nginx proxy_buffering off 配置 | ✅ 通过 | proxy_buffering off + proxy_cache off + proxy_read_timeout 300s + proxy_http_version 1.1 |

**通过率：12/14 完全通过，2/14 部分通过**

---

## 2 FM1 交付物完成度

| 序号 | 交付物 | 状态 | 备注 |
|------|--------|------|------|
| 1 | Vue3+Vite项目骨架 | ✅ | npm run dev 启动成功 |
| 2 | package.json依赖配置 | ✅ | Vue3/TS/Vite/Element Plus/Pinia/Router/Axios/ECharts/markdown-it 全部安装 |
| 3 | TypeScript配置 | ✅ | strict模式 + @/路径别名 + noUnused系列 |
| 4 | Vite配置 | ⚠️ | Element Plus自动按需导入✅，ECharts按需导入❌，manualChunks✅ |
| 5 | 环境变量配置 | ⚠️ | 缺少 .env 和 .env.production |
| 6 | Axios实例+拦截器 | ✅ | JWT Token注入 + 401/403/404/超时处理 |
| 7 | Vue Router配置 | ✅ | 9条路由懒加载 + requiresAuth + 全局前置守卫 |
| 8 | Pinia Store骨架 | ✅ | 4个Store完整实现（超出骨架要求） |
| 9 | TypeScript类型定义 | ✅ | 6个类型文件（比文档多session.ts） |
| 10 | 全局样式 | ✅ | variables.scss + global.scss 完整 |
| 11 | AppHeader布局组件 | ✅ | 导航栏+Logo+菜单+用户信息+退出+未登录登录/注册按钮 |
| 12 | HomeView首页骨架 | ✅ | 超出骨架要求，已实现完整首页功能 |
| 13 | Docker+Nginx配置 | ✅ | Dockerfile + nginx.conf（SPA+API代理+SSE+安全头+gzip） |

**完成率：11/13 完全通过，2/13 部分通过**

---

## 3 问题清单

### 3.1 [High] ECharts 按需导入未实现

**Issue**: 架构文档明确要求"ECharts按需导入（仅导入Graph/Bar类型）"，但当前 vite.config.ts 仅配置了 manualChunks 分包，未配置 ECharts 按需导入。使用 `import * as echarts from 'echarts'` 会全量导入，打包体积约800KB+。

**Impact**: 打包体积显著增大，首屏加载性能下降，可能影响FM6性能验收标准（首屏gzip后<2秒）。

**Root Cause**: M1阶段ECharts组件尚未实际使用，按需导入配置被推迟。

**Suggested Fix**: 在使用ECharts时改为按需导入：

```typescript
import * as echarts from 'echarts/core'
import { GraphChart, BarChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([GraphChart, BarChart, TooltipComponent, LegendComponent, GridComponent, CanvasRenderer])
```

**建议处理时机**: FM4 开发 Agent 可视化时一并处理。

---

### 3.2 [Medium] 缺少 .env 和 .env.production 环境变量文件

**Issue**: 里程碑文档要求 `.env + .env.development + .env.production` 三个环境变量文件，当前仅有 `.env.development`。

**Impact**: 生产构建时 VITE_API_BASE_URL 回退到代码默认值 `/api`，功能不受影响但不符合配置管理规范。

**Suggested Fix**:

```bash
# .env
VITE_APP_TITLE=科研文献智能助手

# .env.production
VITE_API_BASE_URL=/api
```

---

### 3.3 [Medium] paperStore 中前端过滤/排序逻辑泄漏

**Issue**: `paperStore.ts` 的 `filteredResults` computed 中实现了年份、会议、引用数筛选和排序逻辑。架构文档要求避免前端排序/筛选逻辑泄漏。

**Impact**: 当数据量大时前端过滤性能差，与后端API筛选参数重复，可能导致前后端筛选逻辑不一致。

**Root Cause**: M1阶段后端API可能未实现筛选参数，前端先行实现本地过滤作为兜底。

**Suggested Fix**: 筛选排序应通过API参数传递给后端，`filteredResults` 应直接返回 `searchResults`。`searchPapers` 已传递 `...filters.value` 给API，前端过滤属于冗余。

**建议处理时机**: FM2 联调时移除。

---

### 3.4 ~~[Medium] AppHeader 在 App.vue 和 HomeView.vue 中重复引入~~ ✅ 已修复

**Issue**: App.vue 中已引入 AppHeader + AppFooter 作为全局布局，HomeView.vue 又重复引入，导致首页显示两层 Header/Footer。

**状态**: 已修复

---

## 4 亮点

1. **TypeScript 严格模式增强**：不仅 `strict: true`，还额外启用 `noUnusedLocals`、`noUnusedParameters`、`noFallthroughCasesInSwitch`
2. **循环依赖规避**：Router 和 Axios 拦截器中使用动态 `import()` 获取 Store 实例，正确避免 Pinia-Router-Axios 循环依赖
3. **Docker 安全**：Dockerfile 使用非 root 用户运行 nginx，包含 HEALTHCHECK，多阶段构建减小镜像体积
4. **Nginx 安全头**：X-Content-Type-Options / X-Frame-Options / X-XSS-Protection + gzip 压缩
5. **CSS 变量体系完整**：variables.scss 定义了完整的 Design Token（间距/圆角/阴影/字号/过渡/Agent状态色），通过 Vite additionalData 全局注入
6. **Store 设计规范**：4个 Store 全部使用 setup store 风格，userStore Token 持久化使用常量 key，paperStore MAX_SELECTED_PAPERS=5
7. **API 层类型标注**：API 函数有 TypeScript 返回类型标注
8. **测试覆盖**：storage 工具函数测试（7个）+ HomeView 组件测试（6个），共13个测试全部通过
9. **Vite SSE 代理**：proxy 配置中检测 `text/event-stream` 并设置 `cache-control: no-cache` 和 `x-accel-buffering: no`

---

## 5 统计

| Severity | 数量 | 状态 |
|----------|------|------|
| Critical | 0 | — |
| High | 1 | 待FM4处理 |
| Medium | 2 | 待FM2处理 |
| Low | 0 | — |
| 已修复 | 1 | AppHeader重复引入 ✅ |

---

## 6 测试验证记录

| 验证项 | 命令 | 结果 |
|--------|------|------|
| TypeScript 编译 | `npm run typecheck` | ✅ 退出码0，零错误 |
| 单元测试 | `npm run test:run` | ✅ 2个测试文件，13个测试用例，全部通过 |
| 开发服务器 | `npm run dev` | ✅ Vite v8.0.14，385ms启动，localhost:5173 可访问 |

---

## 7 结论与建议

### 审阅结论

**FM1 里程碑通过** ✅

核心基础设施全部就绪，14项验收检查中12项完全通过，2项部分通过（ECharts按需导入和缺少环境变量文件），均不影响FM2开发进度。多项交付物已超出M1的"骨架"要求。

### 下一步行动

| 优先级 | 行动项 | 时间窗口 |
|--------|--------|---------|
| P0 | 开始 FM2 开发：LoginView / RegisterView / UserProfileForm | Week 5-6 |
| P1 | 补充 .env 和 .env.production 环境变量文件 | 本周内 |
| P2 | ECharts 按需导入配置 | FM4 开发时 |
| P2 | paperStore 前端过滤逻辑移除 | FM2 联调时 |

---

> **报告生成时间**：2026-05-25
> **下次审阅**：FM2 里程碑完成时
