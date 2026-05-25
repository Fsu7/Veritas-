# Task05: Pinia Stores 骨架实现计划

## 当前状态分析

### 已完成的基础设施
- `main.ts` — 已注册 `createPinia()`，无需修改 ✅
- `types/` — 5个类型文件已完整定义（user.ts, paper.ts, common.ts, analysis.ts, agent.ts）✅
- `api/index.ts` — Axios实例+拦截器已创建 ✅
- `stores/` — 4个Store文件已存在，但Actions中有TODO占位，未接入API ✅（需完善）

### 缺失的依赖
- `api/user.ts` — 不存在，userStore需要调用
- `api/paper.ts` — 不存在，paperStore需要调用
- `api/analysis.ts` — 不存在，sessionStore需要调用
- `api/session.ts` — 不存在，sessionStore需要调用

### 关键发现
1. **main.ts已注册Pinia** — `app.use(createPinia())` 已存在，无需修改
2. **4个Store骨架已存在** — 但Actions中都是TODO，需要补全API调用逻辑
3. **userStore有额外方法** — 当前有`setLoginData`方法，但prompt要求`login`方法直接调用API
4. **API模块文件缺失** — task03的API封装文件尚未创建，Store无法调用API

## 实施计划

### 步骤1: 创建API模块文件（4个文件）

按照前端架构文档第10.2节的API模块封装规范，创建4个API文件：

#### 1.1 `api/user.ts`
- `register` — POST `/users/register`
- `login` — POST `/users/login` → `Promise<LoginResponse>`
- `getUserInfo` — GET `/users/{userId}`
- `getProfile` — GET `/users/{userId}/profile` → `Promise<ProfileResponse>`
- `createProfile` — POST `/users/{userId}/profile` → `Promise<ProfileResponse>`
- `updateProfile` — PUT `/users/{userId}/profile` → `Promise<ProfileResponse>`

#### 1.2 `api/paper.ts`
- `list` — GET `/papers`
- `getDetail` — GET `/papers/{paperId}`
- `search` — GET `/papers/search` → `Promise<PageResponse<Paper>>`
- `addFavorite` — POST `/papers/{paperId}/favorite`
- `removeFavorite` — DELETE `/papers/{paperId}/favorite`

#### 1.3 `api/analysis.ts`
- `analyzePaper` — POST `/analysis/paper`
- `comparePapers` — POST `/analysis/compare`
- `generateReport` — POST `/analysis/report`
- `getResult` — GET `/analysis/{analysisId}` → `Promise<AnalysisResult>`
- `getStatus` — GET `/analysis/{analysisId}/status`
- `getAgentStreamUrl` — 返回SSE流URL字符串

#### 1.4 `api/session.ts`
- `create` — POST `/sessions` → `Promise<SessionResponse>`
- `list` — GET `/sessions`
- `getDetail` — GET `/sessions/{sessionId}`
- `delete` — DELETE `/sessions/{sessionId}`

> **注意**: 需要在`types/`中补充`SessionResponse`类型定义

### 步骤2: 完善 userStore.ts

**当前问题**:
- 有`setLoginData`方法但prompt要求`login`方法直接调用API
- `fetchProfile`和`saveProfile`是TODO

**修改方案**:
- 将`setLoginData`重命名为`login`，内部调用`userApi.login`
- 实现`fetchProfile`：调用`userApi.getProfile`
- 实现`saveProfile`：根据`hasProfile`调用`createProfile`或`updateProfile`
- 保留`logout`（已完整实现）
- 禁止console.log Token内容

### 步骤3: 完善 paperStore.ts

**当前问题**:
- `searchPapers`和`toggleFavorite`是TODO
- `togglePaperSelection`已实现（含5篇限制）

**修改方案**:
- 实现`searchPapers`：调用`paperApi.search`，更新searchResults/totalResults/currentQuery/currentPage
- 实现`toggleFavorite`：调用`paperApi.addFavorite`/`removeFavorite`，更新favorites列表
- `togglePaperSelection`保持不变（已正确实现）

### 步骤4: 完善 sessionStore.ts

**当前问题**:
- `createSession`和`fetchAnalysisResult`是TODO

**修改方案**:
- 实现`createSession`：调用`sessionApi.create`，更新currentSessionId，返回响应
- 实现`fetchAnalysisResult`：调用`analysisApi.getResult`，存入analysisResults Map

### 步骤5: 完善 agentStore.ts

**当前状态**: agentStore已完整实现，无TODO

**验证方案**: 确认所有接口与prompt要求一致
- ✅ agentStates / flowData / isConnected / currentAnalysisId
- ✅ agentStatesList / activeAgents / progress
- ✅ getAgentState / updateAgentState / resetStates

### 步骤6: 补充类型定义

在`types/session.ts`（新建）或现有类型文件中补充：
- `SessionResponse` — `{ sessionId: string; topic: string; status: string; createdAt: string }`
- `SessionDetail` — 会话详情类型

### 步骤7: TypeScript编译验证

运行 `npx vue-tsc --noEmit` 确保无类型错误

### 步骤8: 开发服务器验证

运行 `npm run dev` 确保4个Store可正常创建

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| **创建** | `src/api/user.ts` | 用户API封装 |
| **创建** | `src/api/paper.ts` | 论文API封装 |
| **创建** | `src/api/analysis.ts` | 分析API封装 |
| **创建** | `src/api/session.ts` | 会话API封装 |
| **创建** | `src/types/session.ts` | 会话相关类型定义 |
| **修改** | `src/stores/userStore.ts` | 补全login/fetchProfile/saveProfile |
| **修改** | `src/stores/paperStore.ts` | 补全searchPapers/toggleFavorite |
| **修改** | `src/stores/sessionStore.ts` | 补全createSession/fetchAnalysisResult |
| **修改** | `src/stores/agentStore.ts` | 验证完整性，可能无需修改 |
| ~~修改~~ | ~~`src/main.ts`~~ | ~~已注册Pinia，无需修改~~ |

## 规范遵循要点

1. **Composition API setup store风格** — 所有Store使用`defineStore('name', () => {...})`
2. **禁止Options API** — 不使用`{ state, getters, actions }`对象风格
3. **按业务域划分** — 4个独立Store，不创建全局大Store
4. **Store只调用api/层** — 不直接操作Repository或调用Python API
5. **Token安全** — 禁止console.log Token内容
6. **camelCase命名** — Store内部使用camelCase
7. **try-catch错误处理** — Store Actions中处理API错误
8. **无TODO注释** — 所有代码完整可执行

## 验收标准对照

| AC编号 | 验收标准 | 验证方式 |
|--------|---------|---------|
| AC-001 | userStore：Token管理+login/logout/fetchProfile/saveProfile功能完整 | 代码审查 |
| AC-002 | paperStore：searchPapers/togglePaperSelection(最多5篇)/toggleFavorite功能完整 | 代码审查 |
| AC-003 | sessionStore：createSession/fetchAnalysisResult功能完整 | 代码审查 |
| AC-004 | agentStore：updateAgentState/getAgentState/resetStates/progress计算完整 | 代码审查 |
| AC-005 | 4个Store全部使用Composition API setup store风格 | 代码审查 |
| AC-006 | userStore Token持久化到localStorage，logout时清除 | 代码审查 |
| AC-007 | main.ts注册pinia插件 | 已完成，代码审查确认 |
| AC-008 | Store按业务域划分，无全局大Store | 代码审查 |
