# Task 09: HomeView首页骨架 + 集成测试验证

## 任务概述

| 项目 | 内容 |
|------|------|
| **版本** | v0.1 |
| **里程碑** | M1 / FM1：项目骨架与基础设施就绪 |
| **涉及层级** | 前端 (frontend) |
| **功能编号** | F1.2.1, F1.2.6 |

## 需求描述

创建HomeView.vue首页骨架组件，实现主题搜索输入框、最近搜索标签、检索跳转，集成AppHeader和AppFooter布局组件，使用paperStore管理搜索状态，未登录用户引导登录，并编写集成测试验证。

## 影响范围

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `src/views/HomeView.vue` | 首页页面：搜索+历史+跳转+布局 |
| 新增 | `src/utils/storage.ts` | LocalStorage工具：搜索历史存取 |
| 修改 | `src/router/index.ts` | 确认'/'路由已配置HomeView |

## 首页设计

```
┌─────────────────────────────────────────────┐
│  AppHeader：Logo | 菜单 | 用户信息           │
├─────────────────────────────────────────────┤
│                                             │
│           🔍 科研文献智能助手                 │
│                                             │
│     ┌─────────────────────────────────┐     │
│     │  输入研究主题，如"Multi-Agent..." │     │
│     └─────────────────────────────────┘     │
│                         [ 检 索 ]           │
│                                             │
│     最近搜索：                               │
│     [Multi-Agent] [RAG检索] [大模型微调]     │
│                                   [清除]    │
│                                             │
├─────────────────────────────────────────────┤
│  AppFooter：项目名称 | 版本 | AI标注         │
└─────────────────────────────────────────────┘
```

## 核心逻辑

| 功能 | 实现 | 说明 |
|------|------|------|
| 搜索输入 | el-input + v-model + @keyup.enter | 支持中英文、回车触发 |
| 检索跳转 | router.push({name:'Search', query:{q:query}}) | 已登录跳转/search |
| 未登录引导 | ElMessage.warning + router.push('/login') | 未登录提示登录 |
| 历史记录 | LocalStorage存储最近10条 | 去重、最新在前 |
| 历史点击 | 填入搜索框并触发检索 | 快捷选择 |
| 清除历史 | clearRecentSearches | 清空LocalStorage和UI |

## 依赖关系

| 依赖 | 来源 | 用途 |
|------|------|------|
| paperStore | task05 | searchPapers |
| userStore | task05 | isLoggedIn判断 |
| router | task04 | 导航跳转 |
| AppHeader | task08 | 顶部导航 |
| AppFooter | task08 | 底部信息 |
| variables.scss | task07 | CSS变量 |

## 集成测试

| 测试项 | 验证内容 |
|--------|---------|
| 布局集成 | AppHeader和AppFooter正确渲染 |
| 搜索输入 | 输入框存在且可输入 |
| 检索跳转 | 已登录→/search?q=xxx |
| 未登录引导 | 提示登录+跳转/login |
| 历史标签 | 正确显示和点击 |
| 清除历史 | 功能正确 |

## 验收标准

- [ ] HomeView：搜索输入框+检索按钮+历史标签功能完整
- [ ] HomeView：回车和按钮触发检索，已登录跳转/search
- [ ] HomeView：未登录点击检索提示登录
- [ ] HomeView：集成AppHeader和AppFooter
- [ ] utils/storage.ts：搜索历史存取、去重、10条限制
- [ ] 集成测试全部通过
- [ ] npx vue-tsc --noEmit编译无错误

## 验证命令

```bash
cd Veritas/frontend && npx vue-tsc --noEmit
cd Veritas/frontend && npm run dev
cd Veritas/frontend && npm run test
```
