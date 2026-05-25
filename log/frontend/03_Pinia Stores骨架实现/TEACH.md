# 技术教学文档 — Pinia Stores 骨架实现

## 开发思路

### 需求分析过程
本次任务（task05）要求创建4个Pinia Store基础结构骨架。在分析时发现：
1. 4个Store骨架文件已由前置任务创建，但Actions中全是TODO占位
2. API模块文件（user.ts/paper.ts/analysis.ts/session.ts）尚未创建，Store无法调用API
3. `main.ts`已注册Pinia，无需修改
4. `agentStore`已完整实现，无需改动

因此实际工作重心从"创建Store骨架"转变为"补全API模块 + 完善Store Actions"。

### 技术选型考虑
- **Pinia setup store vs options store**：项目规范强制要求Composition API setup store风格（`defineStore('name', () => {...})`），不使用Options API的`{ state, getters, actions }`对象风格
- **API返回类型**：Axios响应拦截器已解包`ApiResponse<T>`，直接返回`data.data`，因此API函数的返回类型是业务数据类型而非AxiosResponse
- **localStorage key管理**：使用常量（`TOKEN_KEY`等）避免字符串硬编码散落各处

### 架构设计思路
遵循前端分层架构：`View → Store → API → 后端`

```
┌─────────────┐     ┌──────────────┐     ┌──────────┐     ┌────────┐
│  View组件    │ ──→ │ Pinia Store  │ ──→ │ API模块  │ ──→ │ 后端   │
│ (页面/组件)  │ ←── │ (状态管理)   │ ←── │ (HTTP)   │ ←── │ (Java) │
└─────────────┘     └──────────────┘     └──────────┘     └────────┘
     响应式更新          数据缓存           请求封装         业务逻辑
```

### 遇到的问题及解决方案

**问题1：Store与API的循环依赖**
- `api/index.ts` 导入了 `useUserStore`（请求拦截器注入Token）
- Store又导入 `api/user.ts`
- 解决：Pinia的`useUserStore()`在拦截器中是延迟调用（运行时才执行），不会造成模块加载时的循环依赖

**问题2：ProfileResponse类型与UserProfile类型不匹配**
- API返回`ProfileResponse`（字段为string类型）
- Store内部使用`UserProfile`（字段为枚举字面量类型）
- 解决：在`fetchProfile`/`saveProfile`中使用`as UserProfile['educationLevel']`等类型断言

**问题3：sessionStore需要调用analysisApi**
- `sessionStore`的`fetchAnalysisResult`需要调用`analysisApi.getResult`
- 这意味着sessionStore依赖analysis API模块
- 解决：直接导入`analysisApi`，因为这是合理的跨域API调用（会话与分析结果天然关联）

## 实现步骤

1. **分析现状**：读取现有Store文件，确认哪些是TODO、哪些已实现
2. **创建types/session.ts**：补充SessionResponse和SessionDetail类型定义
3. **创建4个API模块**：按照架构文档10.2节规范封装HTTP请求
4. **完善userStore**：将`setLoginData`重构为`login`（调用API），实现`fetchProfile`/`saveProfile`
5. **完善paperStore**：实现`searchPapers`（调用paperApi.search）和`toggleFavorite`（调用addFavorite/removeFavorite）
6. **完善sessionStore**：实现`createSession`和`fetchAnalysisResult`
7. **验证agentStore**：逐项对照prompt要求确认完整性
8. **TypeScript编译验证**：`npx vue-tsc --noEmit` 零错误
9. **开发服务器验证**：`npm run dev` 启动成功

## 解决了什么问题

### 核心问题描述
前端4个核心业务域（用户/论文/会话/Agent）缺少完整的状态管理层，Store Actions为空壳（TODO），无法与后端通信。

### 解决方案对比
| 方案 | 优点 | 缺点 |
|------|------|------|
| A: 组件内直接调API | 简单直接 | 状态分散、难复用、难测试 |
| B: 全局大Store | 一次导入 | 职责不清、难维护 |
| **C: 按业务域划分Store** ✅ | 职责清晰、可复用、可测试 | 需要跨Store通信 |

### 最终方案的优势
- 每个Store职责单一，代码量可控
- 组件只需导入相关Store，不污染全局
- 便于单元测试（可独立mock API）
- 符合Pinia官方推荐和项目规范

## 变更内容

### 新增文件
- `src/types/session.ts` — SessionResponse/SessionDetail类型定义
- `src/api/user.ts` — 用户API封装（6个方法）
- `src/api/paper.ts` — 论文API封装（5个方法）
- `src/api/analysis.ts` — 分析API封装（6个方法）
- `src/api/session.ts` — 会话API封装（4个方法）

### 修改文件
- `src/stores/userStore.ts`
  - 移除`setLoginData`方法，新增`login`方法（调用userApi.login）
  - 新增`persistLoginData`内部辅助函数
  - 实现fetchProfile（调用userApi.getProfile + 类型转换）
  - 实现saveProfile（根据hasProfile调用create或update）
  - localStorage key提取为常量
- `src/stores/paperStore.ts`
  - 实现searchPapers（调用paperApi.search，更新searchResults/totalResults）
  - 实现toggleFavorite（调用paperApi.addFavorite/removeFavorite）
  - 提取MAX_SELECTED_PAPERS常量
- `src/stores/sessionStore.ts`
  - 实现createSession（调用sessionApi.create，更新currentSessionId）
  - 实现fetchAnalysisResult（调用analysisApi.getResult，存入Map）

### 配置变更
- 无配置变更（main.ts已注册Pinia，无需修改）

## 关键技术点

### 1. Pinia Setup Store 风格
```typescript
export const useXxxStore = defineStore('xxx', () => {
  // State — 用 ref
  const data = ref<Type>(initialValue)

  // Getters — 用 computed
  const derived = computed(() => data.value.xxx)

  // Actions — 用普通函数或async函数
  async function fetchData() {
    const res = await api.getData()
    data.value = res
  }

  // 必须return所有需要暴露的成员
  return { data, derived, fetchData }
})
```

### 2. Token持久化模式
```typescript
// 初始化：从localStorage读取
const token = ref<string>(localStorage.getItem('token') || '')

// 写入：同步更新state和localStorage
function persistLoginData(data: LoginResponse) {
  token.value = data.token
  localStorage.setItem('token', data.token)
}

// 清除：同步清除state和localStorage
function logout() {
  token.value = ''
  localStorage.removeItem('token')
}
```

### 3. API返回类型与Axios拦截器配合
Axios响应拦截器已解包`ApiResponse<T>`，返回`data.data`：
```typescript
// 拦截器中
if (data.code === 200) {
  return data.data  // 直接返回业务数据
}
```
因此API函数的返回类型声明为业务类型：
```typescript
login: (data: {...}): Promise<LoginResponse> => http.post('/users/login', data)
```

### 4. 论文选择5篇限制
```typescript
const MAX_SELECTED_PAPERS = 5

function togglePaperSelection(paper: Paper) {
  const idx = selectedPapers.value.findIndex(p => p.paperId === paper.paperId)
  if (idx >= 0) {
    selectedPapers.value.splice(idx, 1)  // 已选则取消
  } else if (selectedPapers.value.length < MAX_SELECTED_PAPERS) {
    selectedPapers.value.push(paper)     // 未达上限则添加
  }
  // 超限则静默忽略（不添加）
}
```

### 5. Map类型响应式使用
```typescript
const analysisResults = ref<Map<string, AnalysisResult>>(new Map())

// 存入
analysisResults.value.set(analysisId, res)

// 读取
const result = analysisResults.value.get(analysisId)
```

## 经验总结

### 开发过程中的收获
1. **先读代码再动手**：本次任务发现4个Store骨架已存在、main.ts已注册Pinia，避免了重复创建
2. **API模块是Store的前置依赖**：Store Actions要调用API，必须先创建API模块文件
3. **类型系统是安全网**：TypeScript编译验证能捕获类型不匹配、导入路径错误等问题

### 踩过的坑及如何避免
1. **ProfileResponse vs UserProfile类型差异**：API返回string类型，Store使用枚举字面量类型，需要类型断言。更好的做法是让后端返回枚举值，前端直接使用
2. **Map类型的Vue响应式**：`ref<Map>`在Vue3中是响应式的，但直接操作Map方法（set/get/delete）需要注意触发响应式更新

### 最佳实践建议
1. **Store按业务域划分**，每个Store不超过100行，超过需拆分
2. **异步操作放在Store Actions中**，不在组件内直接调API
3. **localStorage key使用常量**，避免硬编码字符串散落各处
4. **API函数声明返回类型**，配合拦截器解包获得类型安全
5. **禁止console.log敏感信息**（Token、密码等）
