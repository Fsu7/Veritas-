# UserCenterView 用户中心页面 + userStore 扩展

## 任务概述

实现用户中心页面 UserCenterView.vue 和 userStore 完整实现，包含 3 大区块：用户信息展示区（el-descriptions 展示用户名/邮箱/注册时间）、用户画像编辑区（复用 UserProfileForm 组件）、历史记录区（el-timeline 展示最近会话记录 + el-empty 空状态）。同时完善 userStore 添加 register 方法和 getUserInfo 方法，扩展 types/user.ts 添加 UserInfo 接口。

## 里程碑

FM2: 用户+检索页面

## 涉及模块

- F1.1 用户界面模块（F1.1.3 画像编辑、F1.1.4 历史记录查看）

## 文件变更

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | Veritas/frontend/src/views/UserCenterView.vue | 替换占位骨架为完整用户中心页面 |
| 修改 | Veritas/frontend/src/stores/userStore.ts | 扩展：添加 userInfo/getUserInfo/register |
| 修改 | Veritas/frontend/src/types/user.ts | 添加 UserInfo 接口类型 |

## 已有可复用实现

| 文件 | 说明 | 复用方式 |
|------|------|---------|
| stores/userStore.ts | login/logout/fetchProfile/saveProfile | 扩展 |
| api/user.ts | getUserInfo/register | 直接复用 |
| api/session.ts | list/getDetail/delete | 直接复用 |
| types/user.ts | UserProfile/LoginResponse/ProfileResponse | 扩展 |
| components/common/UserProfileForm.vue | task12 产出的画像表单组件 | 直接复用 |

## 功能要求

### UserCenterView.vue

| ID | 描述 | 优先级 | 验收条件 |
|----|------|--------|---------|
| FR-001 | 用户信息展示区：el-descriptions 展示用户名/邮箱/注册时间 | P0 | 3 个字段正确展示 |
| FR-002 | 画像编辑区：复用 UserProfileForm，传入 initialData | P0 | 画像表单正确渲染和保存 |
| FR-003 | 历史记录区：el-timeline 展示最近会话 | P1 | 按时间倒序排列 |
| FR-004 | 历史记录空状态：el-empty | P1 | 无记录时显示空提示 |
| FR-005 | 页面加载 loading | P0 | 加载期间 v-loading |
| FR-010 | 3 大区块 el-card 垂直排列，居中 max-width 1200px | P1 | 布局正确 |

### userStore.ts 扩展

| ID | 描述 | 优先级 | 验收条件 |
|----|------|--------|---------|
| FR-006 | 添加 userInfo state (Ref\<UserInfo \| null\>) | P0 | state 正确定义 |
| FR-007 | 添加 getUserInfo() 方法 | P0 | 调用 API 更新 userInfo |
| FR-008 | 添加 register() 方法 | P1 | 调用 API 不建立登录态 |
| FR-011 | logout 时清除 userInfo | P1 | logout 后 userInfo 为 null |

### types/user.ts 扩展

| ID | 描述 | 优先级 | 验收条件 |
|----|------|--------|---------|
| FR-009 | 添加 UserInfo 接口 | P0 | 含 username/email/createdAt |

## 数据流

```
UserCenterView onMounted
  ├── userStore.getUserInfo() → userApi.getUserInfo(userId) → userInfo state
  ├── userStore.fetchProfile() → userApi.getProfile(userId) → profile state
  └── sessionApi.list({page:1, size:10}) → sessions local ref
→ 3路数据并行加载 → 渲染3大区块
```

## API 契约

```
GET /api/users/{userId}
Response: { "code": 200, "data": { "username": "string", "email": "string", "createdAt": "string" } }

GET /api/sessions?page=1&size=10
Response: { "code": 200, "data": { "items": [...], "total": number } }
```

## 页面布局

```
┌─────────────────────────────────────────────────┐
│  ┌─── 用户信息 ────────────────────────────┐   │
│  │  用户名：张三                             │   │
│  │  邮箱：zhangsan@example.com              │   │
│  │  注册时间：2026-05-23                     │   │
│  └──────────────────────────────────────────┘   │
│                                                 │
│  ┌─── 用户画像 ────────────────────────────┐   │
│  │  <UserProfileForm :initial-data="..." /> │   │
│  └──────────────────────────────────────────┘   │
│                                                 │
│  ┌─── 历史记录 ────────────────────────────┐   │
│  │  <el-timeline>                           │   │
│  │    <el-timeline-item ... />              │   │
│  │  </el-timeline>                          │   │
│  │  <el-empty v-if="!sessions.length" />    │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

## 编码约束

- `<script setup lang="ts">` + Composition API
- 用户信息/画像通过 userStore 获取
- 会话列表直接调用 sessionApi.list()（无 sessionStore 缓存需求）
- 必须复用 UserProfileForm 组件（禁止重复实现画像表单）
- BEM 命名：user-center-view__section / user-center-view__info
- 8px 间距系统
- CSS 变量取色
- 组件不超过 300 行
- scoped 样式

## 禁止行为

- ❌ 直接调用 userApi 获取用户信息（必须通过 userStore）
- ❌ 页面加载无 loading 状态
- ❌ 历史记录无空状态
- ❌ 重复实现 UserProfileForm 逻辑（必须复用组件）
- ❌ 硬编码颜色值
- ❌ 非 8px 倍数间距
- ❌ 输出伪代码或 TODO
- ❌ 组件超过 300 行

## 验收标准

- [ ] 用户信息区展示用户名/邮箱/注册时间
- [ ] 画像编辑区复用 UserProfileForm，保存后画像更新
- [ ] 历史记录区 el-timeline + el-empty 空状态
- [ ] 页面加载有 loading
- [ ] userStore 新增 userInfo/getUserInfo/register
- [ ] types/user.ts 新增 UserInfo 接口
- [ ] logout 时 userInfo 被清除
- [ ] TypeScript 无类型错误，组件不超过 300 行