# Task 04: Vue Router配置 + 路由守卫 + 9条路由定义

## 任务概述

| 项目 | 内容 |
|------|------|
| **版本** | v0.1 |
| **里程碑** | M1 / FM1：项目骨架与基础设施就绪 |
| **涉及层级** | 前端 (frontend) |
| **功能编号** | F1.1, F1.2, F1.3, F1.4, F1.5 |

## 需求描述

创建Vue Router配置，定义9条路由（全部懒加载），配置路由元信息meta.requiresAuth区分公开/需认证路由，实现全局前置守卫（未登录访问需认证页面跳转/login并携带redirect参数，已登录访问/login和/register跳转首页），使用createWebHistory模式。

## 影响范围

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `src/router/index.ts` | Vue Router配置：9条路由+守卫 |
| 修改 | `src/main.ts` | 注册router插件 |

## 9条路由定义

| 路径 | 名称 | 组件 | 需认证 |
|------|------|------|--------|
| `/` | Home | HomeView | 否 |
| `/login` | Login | LoginView | 否 |
| `/register` | Register | RegisterView | 否 |
| `/search` | Search | SearchView | 是 |
| `/paper/:paperId` | PaperDetail | PaperDetailView | 是 |
| `/compare` | Compare | CompareView | 是 |
| `/report/:analysisId` | Report | ReportView | 是 |
| `/agent-flow/:analysisId` | AgentFlow | AgentFlowView | 是 |
| `/user-center` | UserCenter | UserCenterView | 是 |

## 实现要求

### 路由守卫逻辑

```
beforeEach(to, from, next):
  1. to.requiresAuth && !isLoggedIn → next({ name:'Login', query:{ redirect:to.fullPath } })
  2. (to.name==='Login' || to.name==='Register') && isLoggedIn → next({ name:'Home' })
  3. 其他 → next()
```

### 关键约束

- 所有页面组件必须懒加载
- 路由路径使用kebab-case，名称使用PascalCase
- 使用createWebHistory模式
- userStore必须在守卫回调内函数式获取

## 验收标准

- [ ] 9条路由定义完整，路径kebab-case，名称PascalCase
- [ ] 所有页面组件懒加载
- [ ] requiresAuth元数据正确区分公开/需认证路由
- [ ] 未登录访问需认证页面跳转/login?redirect=原路径
- [ ] 已登录访问/login跳转首页
- [ ] 使用createWebHistory模式
- [ ] main.ts注册router插件

## 验证命令

```bash
cd Veritas/frontend && npx vue-tsc --noEmit
cd Veritas/frontend && npm run dev
```
