# RegisterView 注册页面

## 任务概述

实现注册页面 RegisterView.vue，包含用户名/邮箱/密码/确认密码表单、Element Plus 表单校验（含确认密码一致性校验）、注册逻辑（调用 userApi.register）、注册成功跳转登录页、注册失败提示、按钮 loading 状态、导航到登录页链接。

## 里程碑

FM2: 用户+检索页面

## 涉及模块

- F1.1 用户界面模块

## 文件变更

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | Veritas/frontend/src/views/RegisterView.vue | 替换占位骨架为完整注册页面实现 |

## 已有可复用实现

| 文件 | 说明 | 复用方式 |
|------|------|---------|
| api/user.ts | userApi.register({ username, email, password }) | 直接复用 |
| api/index.ts | Axios 实例 + 响应拦截器 | 直接复用 |
| router/index.ts | /register 路由 + 全局认证守卫 | 直接复用 |
| LoginView.vue | 登录页布局风格参考 | 参考 |

## 功能要求

| ID | 描述 | 优先级 | 验收条件 |
|----|------|--------|---------|
| FR-001 | 注册表单：4字段（用户名/邮箱/密码/确认密码） | P0 | el-form 4 个 el-form-item，ref 和数据绑定正确 |
| FR-002 | 表单校验：用户名3-50字符、邮箱格式、密码8-100字符 | P0 | 所有校验规则生效 |
| FR-003 | 确认密码自定义校验器：与密码一致性校验 | P0 | 不一致时校验失败 |
| FR-004 | 注册逻辑：validate → userApi.register → 跳转/login | P0 | 成功跳转+提示，失败提示错误 |
| FR-005 | 注册按钮 loading 状态 | P0 | 请求期间 loading，不可重复点击 |
| FR-006 | 导航到登录页链接 | P1 | router-link to="/login" |
| FR-007 | 居中卡片布局，与 LoginView 风格一致 | P1 | 最大宽度 400px |
| FR-008 | 密码变更时重新校验确认密码 | P2 | watch password → 重新校验 confirmPassword |

## 数据流

```
用户输入 → RegisterView → userApi.register() → POST /api/users/register
→ Java后端创建用户 → 成功 → ElMessage.success + router.push('/login')
```

## API 契约

```
POST /api/users/register
Request:  { "username": "string", "email": "string", "password": "string" }
Response: { "code": 200, "data": null, "message": "success" }
```

## 编码约束

- `<script setup lang="ts">` + Composition API
- 注册场景直接调用 userApi.register()（无需通过 Store，注册后不建立登录态）
- BEM 命名：register-view__title / register-view__form / register-view__footer
- 8px 间距系统
- CSS 变量取色
- 组件不超过 300 行
- scoped 样式
- 与 LoginView 保持视觉风格一致

## 禁止行为

- ❌ 注册成功后自动登录（应引导用户手动登录）
- ❌ 注册请求无 loading 状态
- ❌ 确认密码校验缺失
- ❌ 硬编码颜色值
- ❌ 非 8px 倍数间距
- ❌ 输出伪代码或 TODO
- ❌ 组件超过 300 行
- ❌ 与 LoginView 风格不一致

## 验收标准

- [ ] 注册表单 4 个字段校验规则全部正确
- [ ] 确认密码与密码不一致时校验失败
- [ ] 注册成功后跳转 /login 并显示成功提示
- [ ] 注册失败显示错误提示，loading 状态正确恢复
- [ ] 页面布局与 LoginView 风格一致
- [ ] 密码框有 show-password 属性
- [ ] TypeScript 无类型错误
- [ ] 组件不超过 300 行，BEM + scoped + CSS 变量