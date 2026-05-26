# 用户界面模块开发（FM2 Task10-13）

## 功能描述
- 实现了 F1.1 用户界面模块的4个核心页面/组件：登录页、注册页、用户画像表单、用户中心页
- 解决了项目从占位骨架到可交互页面的跨越，用户可以完成注册→登录→画像设置→查看个人信息的完整流程
- 业务价值：完成 FM2 里程碑中用户认证与个性化画像的前端闭环，为后续论文检索、分析等核心功能提供用户上下文基础

## 实现逻辑

### 修改的核心文件列表

| 文件 | 操作 | 行数 | 说明 |
|------|------|------|------|
| `src/views/LoginView.vue` | 替换占位骨架 | 163行 | 登录表单+校验+userStore.login+loading+回车提交 |
| `src/views/RegisterView.vue` | 替换占位骨架 | 207行 | 4字段校验+确认密码一致性+密码联动+userApi.register |
| `src/components/common/UserProfileForm.vue` | 新建 | 168行 | 4维度画像表单组件+Props/Emits+编辑模式 |
| `src/views/UserCenterView.vue` | 替换占位骨架 | 155行 | 3区块用户中心+el-descriptions+UserProfileForm+el-timeline |
| `src/types/user.ts` | 扩展 | 43行 | 新增UserInfo接口 |
| `src/stores/userStore.ts` | 扩展 | 92行 | 新增userInfo/getUserInfo/register，logout清理userInfo |
| `src/api/user.ts` | 修改 | 14行 | getUserInfo添加返回类型Promise\<UserInfo\> |

### 使用的设计模式

1. **Setup Store模式** — userStore使用Pinia Composition API风格，ref+computed+async function
2. **Props Down / Events Up** — UserProfileForm通过props接收initialData，通过emit('saved')通知父组件
3. **View→Store→API分层** — LoginView调userStore.login()，RegisterView直接调userApi.register()（注册不建立登录态）
4. **BEM命名** — 所有CSS类使用block__element--modifier规范
5. **表单校验模式** — Element Plus FormRules + 自定义validator（确认密码一致性）

### 关键代码逻辑说明

1. **登录流程**：用户输入 → el-form.validate() → userStore.login() → persistLoginData存Token → router.push(redirect)
2. **注册流程**：用户输入 → el-form.validate() → userApi.register() → ElMessage.success → router.push('/login')（不自动登录）
3. **画像保存**：UserProfileForm → userStore.saveProfile() → 根据hasProfile判断create/update → emit('saved')
4. **用户中心加载**：onMounted → Promise.all([getUserInfo, fetchProfile, sessionList]) → 3路并行加载
5. **密码联动**：watch registerForm.password → 若confirmPassword非空则validateField('confirmPassword')

## 接口变更

### Request — 登录
```json
POST /api/users/login
{
  "username": "string",
  "password": "string"
}
```

### Response — 登录
```json
{
  "code": 200,
  "data": {
    "token": "string",
    "userId": "string",
    "username": "string",
    "hasProfile": true
  }
}
```

### Request — 注册
```json
POST /api/users/register
{
  "username": "string",
  "email": "string",
  "password": "string"
}
```

### Response — 注册
```json
{
  "code": 200,
  "data": null,
  "message": "success"
}
```

### Request — 获取用户信息
```json
GET /api/users/{userId}
```

### Response — 获取用户信息
```json
{
  "code": 200,
  "data": {
    "username": "string",
    "email": "string",
    "createdAt": "2026-05-26T10:00:00"
  }
}
```

### Request — 会话列表
```json
GET /api/sessions?page=1&size=10
```

### Response — 会话列表
```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "sessionId": "string",
        "userId": "string",
        "topic": "string",
        "status": "completed",
        "createdAt": "2026-05-26T10:00:00",
        "updatedAt": "2026-05-26T10:30:00"
      }
    ],
    "total": 1,
    "page": 1,
    "size": 10,
    "totalPages": 1
  }
}
```

## 测试结果
- TypeScript类型检查：`vue-tsc --noEmit` 零错误 ✅
- Vite构建：`vite build` 3.26s成功 ✅
- 登录页表单校验：用户名3-50字符、密码8-100字符 ✅
- 注册页确认密码一致性校验 ✅
- 注册页密码联动重新校验 ✅
- 用户中心3区块渲染（用户信息/画像/历史记录） ✅
- 历史记录空状态el-empty ✅
- 页面loading状态 ✅
- 是否通过：是

## 相关文件
- `Veritas/frontend/src/views/LoginView.vue`
- `Veritas/frontend/src/views/RegisterView.vue`
- `Veritas/frontend/src/components/common/UserProfileForm.vue`
- `Veritas/frontend/src/views/UserCenterView.vue`
- `Veritas/frontend/src/types/user.ts`
- `Veritas/frontend/src/stores/userStore.ts`
- `Veritas/frontend/src/api/user.ts`
