# LoginView 登录页面

## 任务概述

实现登录页面 LoginView.vue，包含用户名/密码表单、Element Plus 表单校验、登录逻辑（调用 userStore.login）、Token 自动存储、登录成功跳转、登录失败提示、按钮 loading 状态、已登录用户自动跳转首页、导航到注册页链接。

## 里程碑

FM2: 用户+检索页面

## 涉及模块

- F1.1 用户界面模块

## 文件变更

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | Veritas/frontend/src/views/LoginView.vue | 替换占位骨架为完整登录页面实现 |

## 已有可复用实现

| 文件 | 说明 | 复用方式 |
|------|------|---------|
| stores/userStore.ts | login/logout/persistLoginData/isLoggedIn | 直接复用 |
| api/user.ts | userApi.login({ username, password }) | 通过 userStore 间接复用 |
| types/user.ts | LoginResponse 接口定义 | 直接复用 |
| api/index.ts | Axios 实例 + JWT 注入 + 401 自动跳转 | 直接复用 |
| router/index.ts | /login 路由 + 全局认证守卫 | 直接复用 |

## 功能要求

| ID | 描述 | 优先级 | 验收条件 |
|----|------|--------|---------|
| FR-001 | 登录表单：el-form + 用户名/密码输入 | P0 | 包含2个 el-form-item，ref 和数据绑定正确 |
| FR-002 | 表单校验：用户名3-50字符，密码8-100字符 | P0 | 不合规时显示红色校验提示 |
| FR-003 | 登录逻辑：validate → userStore.login → 跳转 | P0 | 成功跳转，失败提示错误 |
| FR-004 | 登录按钮 loading 状态 | P0 | 请求期间按钮 loading，不可重复点击 |
| FR-005 | 导航到注册页链接 | P1 | router-link to="/register" |
| FR-006 | 居中卡片布局，最大宽度400px | P1 | 页面居中，含系统标题和副标题 |
| FR-007 | 密码框回车提交 | P2 | @keyup.enter 触发登录 |

## 数据流

```
用户输入 → LoginView → userStore.login() → userApi.login() → POST /api/users/login
→ Java后端验证 → 返回JWT Token → persistLoginData() → localStorage → router.push
```

## API 契约

```
POST /api/users/login
Request:  { "username": "string", "password": "string" }
Response: { "code": 200, "data": { "token": "string", "userId": "string", "username": "string", "hasProfile": "boolean" } }
```

## 安全要求

- Token 存储在 localStorage（userStore 已实现）
- 密码输入框使用 show-password 属性
- 禁止 console.log Token/密码
- 401 由 Axios 拦截器自动处理

## 编码约束

- `<script setup lang="ts">` + Composition API
- API 调用通过 userStore.login()，不直接调用 userApi
- BEM 命名：login-view__title / login-view__form / login-view__footer
- 8px 间距系统：16px/24px/32px/48px
- CSS 变量取色：var(--el-color-primary) 等
- 组件不超过 300 行
- scoped 样式

## 禁止行为

- ❌ 直接调用 axios 或 userApi（必须通过 userStore）
- ❌ 手动操作 localStorage 存储 Token（userStore 已处理）
- ❌ 登录请求无 loading 状态
- ❌ 硬编码颜色值
- ❌ 非 8px 倍数间距
- ❌ 输出伪代码或 TODO
- ❌ 组件超过 300 行

## 验收标准

- [ ] 表单校验规则正确（用户名3-50字符，密码8-100字符）
- [ ] 登录成功后 Token 存入 localStorage 并跳转
- [ ] 登录失败显示错误提示，loading 状态正确恢复
- [ ] 已登录用户访问 /login 自动跳转首页
- [ ] 页面居中布局，最大宽度 400px
- [ ] 密码框有 show-password，回车可提交
- [ ] TypeScript 无类型错误
- [ ] 组件不超过 300 行，BEM + scoped + CSS 变量