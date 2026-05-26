# 技术教学文档 — 用户界面模块开发

## 开发思路

### 需求分析过程

本次开发属于 FM2 里程碑的 F1.1 用户界面模块，涵盖4个任务（Task10-13）：

1. **Task10 LoginView** — 登录页面，核心是JWT认证流程的前端闭环
2. **Task11 RegisterView** — 注册页面，与登录页风格一致但独立流程
3. **Task12 UserProfileForm** — 画像表单通用组件，被UserCenterView复用
4. **Task13 UserCenterView + Store扩展** — 用户中心页面+状态管理扩展

关键需求决策：
- 注册成功**不自动登录**（安全最佳实践，需用户手动登录）
- 注册页直接调userApi（不经过Store），因为注册不建立登录态
- 会话列表直接调sessionApi（无Store），符合"无全局缓存需求则无需Store"原则

### 技术选型考虑

| 选型 | 决策 | 原因 |
|------|------|------|
| 表单校验 | Element Plus FormRules | 项目已用Element Plus，内置校验足够 |
| 确认密码校验 | 自定义validator | Element Plus无内置一致性校验 |
| 密码联动 | watch + validateField | 修改密码后需重新校验确认密码 |
| 画像编辑 | watch props.initialData | 支持新增/编辑两种模式 |
| 用户中心数据加载 | Promise.all并行 | 3路独立请求，并行提升速度 |
| 日期格式化 | 原生Intl.DateTimeFormat | 项目规范禁止moment.js |

### 架构设计思路

```
数据流分层：

LoginView → userStore.login() → userApi.login() → POST /api/users/login
RegisterView → userApi.register() → POST /api/users/register（不经过Store）
UserProfileForm → userStore.saveProfile() → userApi.createProfile/updateProfile
UserCenterView → userStore.getUserInfo() + userStore.fetchProfile() + sessionApi.list()
```

依赖关系决定了实现顺序：Task12（UserProfileForm）必须在Task13之前完成，因为UserCenterView需要复用该组件。

### 遇到的问题及解决方案

**问题1：userApi.getUserInfo缺少返回类型**
- 现象：`vue-tsc --noEmit` 报错 TS2352，AxiosResponse无法转换为UserInfo
- 原因：`getUserInfo`方法未声明返回类型`Promise<UserInfo>`
- 解决：在`api/user.ts`中为getUserInfo添加`: Promise<UserInfo>`返回类型声明

**问题2：注册页是否应该通过Store调用API**
- 分析：注册成功后不建立登录态，不需要更新Store状态
- 决策：RegisterView直接调用userApi.register()，符合"注册无需Store"的分层规则
- 依据：prompt.json中明确指出"View → API（注册场景无需Store）"

## 实现步骤

1. **Task10 LoginView**：创建登录表单，定义校验规则（用户名3-50字符、密码8-100字符），实现login逻辑通过userStore.login()，添加loading状态、回车提交、注册页链接
2. **Task11 RegisterView**：参照LoginView布局风格，新增邮箱和确认密码字段，实现自定义确认密码校验器，添加密码联动watch，直接调用userApi.register()
3. **Task12 UserProfileForm**：创建4维度枚举表单（学历/研究方向/知识水平/偏好风格），定义Props/Emits接口，实现watch initialData编辑模式，通过userStore.saveProfile()保存
4. **Task13 types扩展**：在user.ts中新增UserInfo接口{username, email, createdAt}
5. **Task13 Store扩展**：userStore新增userInfo state、getUserInfo方法、register方法，logout中清理userInfo
6. **Task13 UserCenterView**：3区块布局（el-descriptions+UserProfileForm+el-timeline），Promise.all并行加载，空状态el-empty
7. **类型修复**：为userApi.getUserInfo添加返回类型，消除TS2352错误
8. **验证**：vue-tsc --noEmit零错误，vite build成功

## 解决了什么问题

### 核心问题描述

项目FM1阶段完成后，LoginView/RegisterView/UserCenterView均为占位骨架（`<h2>xxx页</h2><p>页面开发中...</p>`），用户无法进行任何交互操作。userStore缺少getUserInfo和register方法，types/user.ts缺少UserInfo类型定义。

### 解决方案对比

| 方案 | 描述 | 优劣 |
|------|------|------|
| A: 注册也走Store | RegisterView调userStore.register() | ❌ 注册不建立登录态，走Store无意义 |
| B: 注册直接调API | RegisterView直接调userApi.register() | ✅ 符合分层规则，注册与登录解耦 |
| A: 会话列表走sessionStore | 新建sessionStore管理会话 | ❌ 会话数据无全局缓存需求 |
| B: 会话列表直接调sessionApi | UserCenterView直接调sessionApi.list() | ✅ 轻量，符合"无需Store则不建"原则 |

### 最终方案的优势

1. **最小Store原则** — 只在需要全局状态共享时创建Store，避免过度设计
2. **组件复用** — UserProfileForm作为通用组件，LoginView和UserCenterView都可使用
3. **并行加载** — Promise.all让3路请求同时发出，页面加载更快
4. **类型安全** — 所有API方法都有明确的返回类型声明

## 变更内容

### 新增文件
- `src/components/common/UserProfileForm.vue` — 用户画像4维度表单通用组件（168行）

### 修改文件
- `src/views/LoginView.vue` — 占位骨架→完整登录页面（163行）
- `src/views/RegisterView.vue` — 占位骨架→完整注册页面（207行）
- `src/views/UserCenterView.vue` — 占位骨架→3区块用户中心（155行）
- `src/types/user.ts` — 新增UserInfo接口
- `src/stores/userStore.ts` — 新增userInfo state + getUserInfo + register方法，logout清理userInfo
- `src/api/user.ts` — getUserInfo添加返回类型Promise\<UserInfo\>

### 配置变更
- 无配置文件变更

## 关键技术点

### 1. Element Plus表单校验模式

```typescript
const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度为3-50个字符', trigger: 'blur' }
  ]
}

// 使用：el-form :rules="rules" + el-form-item prop="username"
```

### 2. 自定义表单校验器（确认密码一致性）

```typescript
const validateConfirmPassword = (
  _rule: unknown,
  value: string,
  callback: (error?: Error) => void
) => {
  if (value !== registerForm.password) {
    callback(new Error('两次输入密码不一致'))
  } else {
    callback()
  }
}
```

注意：Element Plus自定义校验器使用callback模式，不是return模式。

### 3. 密码联动重新校验

```typescript
watch(
  () => registerForm.password,
  () => {
    if (registerForm.confirmPassword) {
      registerFormRef.value?.validateField('confirmPassword')
    }
  }
)
```

关键：只在confirmPassword非空时触发重新校验，避免空字段弹出校验提示。

### 4. Props/Emits TypeScript泛型声明

```typescript
const props = defineProps<{
  initialData?: UserProfile
}>()

const emit = defineEmits<{
  (e: 'saved'): void
}>()
```

### 5. watch + immediate实现编辑模式初始化

```typescript
watch(
  () => props.initialData,
  (data) => {
    if (data) {
      form.educationLevel = data.educationLevel
      form.researchField = data.researchField
      form.knowledgeLevel = data.knowledgeLevel
      form.preferredStyle = data.preferredStyle
    }
  },
  { immediate: true }
)
```

`immediate: true`确保组件挂载时如果有initialData就立即填充。

### 6. Promise.all并行加载

```typescript
onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([
      userStore.getUserInfo(),
      userStore.fetchProfile(),
      loadSessions()
    ])
  } catch {
    ElMessage.error('页面加载失败，请刷新重试')
  } finally {
    loading.value = false
  }
})
```

3路独立请求并行发出，任一失败统一提示。

## 经验总结

### 开发过程中的收获

1. **自底向上实现** — 先实现Type→API→Store→Component→View的顺序，确保每层依赖都已就绪
2. **Task12必须在Task13之前** — UserProfileForm是UserCenterView的依赖，顺序不能颠倒
3. **API返回类型声明的重要性** — userApi.getUserInfo最初缺少返回类型，导致Store中需要`as UserInfo`强制转换，修复后类型自然推导

### 踩过的坑及如何避免

1. **Axios拦截器自动解包** — api/index.ts的响应拦截器已经解包了`ApiResponse.data`，所以API方法的返回类型应该是`Promise<XXX>`而不是`Promise<ApiResponse<XXX>>`
2. **CSS变量必须已定义** — 使用`var(--spacing-lg)`等变量时，确保variables.scss中已定义，否则样式不生效
3. **el-select宽度** — el-select默认不会撑满容器，需要手动设置`width: 100%`

### 最佳实践建议

1. **表单页面模板** — LoginView/RegisterView可作为后续表单页面的参考模板（校验+loading+错误处理）
2. **通用组件设计** — UserProfileForm的Props/Emits模式可作为其他通用组件的参考
3. **Store扩展原则** — 扩展Store时不要修改已有方法签名，只新增state/methods，确保向后兼容
4. **logout清理** — 每次新增Store state时，必须同步在logout方法中清理，避免脏数据
