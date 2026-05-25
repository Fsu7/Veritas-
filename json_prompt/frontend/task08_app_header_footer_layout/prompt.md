# Task 08: AppHeader + AppFooter布局组件

## 任务概述

| 项目 | 内容 |
|------|------|
| **版本** | v0.1 |
| **里程碑** | M1 / FM1：项目骨架与基础设施就绪 |
| **涉及层级** | 前端 (frontend) |
| **功能编号** | F1.1 |

## 需求描述

创建2个布局组件：AppHeader顶部导航栏（Logo+菜单+用户信息+退出）和AppFooter底部信息栏（项目名称+版本号+AI标注），根据登录状态动态显示，使用Element Plus组件和CSS变量。

## 影响范围

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `src/components/layout/AppHeader.vue` | 顶部导航栏组件 |
| 新增 | `src/components/layout/AppFooter.vue` | 底部信息栏组件 |

## 组件设计

### AppHeader.vue

| 区域 | 内容 | 说明 |
|------|------|------|
| 左侧 | Logo文字"科研文献智能助手" | .app-header__logo |
| 中间 | el-menu水平菜单 | 已登录：首页+用户中心；未登录：空 |
| 右侧 | 用户信息+退出按钮 | 已登录显示；未登录显示登录/注册链接 |

**关键逻辑**：
- menuItems根据userStore.isLoggedIn动态生成
- 退出：userStore.logout() + router.push('/login')
- el-menu使用router模式，index为路由路径

### AppFooter.vue

| 内容 | 说明 |
|------|------|
| 项目名称 | XH-202630 科研文献智能助手 |
| 版本号 | v0.1 |
| AI标注 | AI生成内容仅供参考（.ai-generated-label样式） |

## 依赖关系

| 依赖 | 来源 | 用途 |
|------|------|------|
| userStore | task05 | isLoggedIn/username/logout |
| router | task04 | 导航跳转 |
| variables.scss | task07 | --header-height等CSS变量 |

## 实现要求

- 使用`<script setup lang="ts">` + Composition API
- 样式使用scoped + BEM命名
- 使用CSS变量（var(--header-height)等）
- 组件成员排列：导入 → Props/Emits → 响应式状态 → 计算属性 → 方法
- 退出按钮清除token并跳转登录页
- AI内容标注使用.ai-generated-label样式类

## 验收标准

- [ ] AppHeader：Logo+菜单+用户信息+退出按钮功能完整
- [ ] AppHeader：根据登录状态动态显示
- [ ] AppHeader：退出按钮清除token并跳转登录页
- [ ] AppFooter：项目名称+版本号+AI标注显示正确
- [ ] 两个组件使用script setup + scoped + BEM
- [ ] 使用CSS变量而非硬编码
- [ ] npx vue-tsc --noEmit编译无错误

## 验证命令

```bash
cd Veritas/frontend && npx vue-tsc --noEmit
cd Veritas/frontend && npm run dev
```
