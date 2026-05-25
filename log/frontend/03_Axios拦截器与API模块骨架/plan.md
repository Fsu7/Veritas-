# Task03: Axios拦截器 + API模块骨架 实施计划

## 任务概述

创建Axios HTTP客户端实例（含请求/响应拦截器），4个API模块骨架（user.ts、paper.ts、analysis.ts、session.ts），以及TypeScript通用类型定义。

## 现有状态分析

| 文件 | 状态 | 说明 |
|------|------|------|
| `types/common.ts` | ✅ 已存在 | `ApiResponse<T>` 和 `PageResponse<T>` 已定义完整，无需修改 |
| `types/user.ts` | ✅ 已存在 | `UserProfile`、`LoginResponse`、`ProfileResponse` 已定义完整 |
| `types/paper.ts` | ✅ 已存在 | `Paper`、`FilterParams` 已定义完整 |
| `types/analysis.ts` | ✅ 已存在 | `AnalysisResult`、`CompareResult`、`Citation`、`Conflict` 等已定义完整 |
| `types/agent.ts` | ✅ 已存在 | `AgentState`、`FlowData` 等已定义完整 |
| `api/index.ts` | ⚠️ 需审查 | 已有基础Axios实例+拦截器，需对照prompt.json验收标准逐项检查 |
| `api/user.ts` | ❌ 不存在 | 需创建 |
| `api/paper.ts` | ❌ 不存在 | 需创建 |
| `api/analysis.ts` | ❌ 不存在 | 需创建 |
| `api/session.ts` | ❌ 不存在 | 需创建 |

## 关键约束（来自prompt.json forbidden_actions）

- **FA-001**: 禁止输出伪代码或TODO注释，必须输出完整可执行代码
- **FA-002**: 禁止在模块顶层导入useUserStore（导致循环依赖），必须在拦截器回调内函数式获取
- **FA-003**: 禁止在API模块中编写业务逻辑，API层仅封装HTTP调用
- **FA-004**: 禁止硬编码API baseURL，必须从`import.meta.env.VITE_API_BASE_URL`读取
- **FA-005**: 禁止在拦截器中console.log完整Token
- **FA-006**: 禁止忽略401错误不跳转登录页
- **FA-007**: 禁止修改task00-01已创建的文件（但api/index.ts属于本task范围，可修改）
- **FA-008**: 禁止前端直接调用Python AI服务API

## 实施步骤

### Step 1: 审查并完善 `api/index.ts`

现有代码已基本符合要求，逐项对照验收标准：

| 验收项 | 现状 | 是否需要修改 |
|--------|------|-------------|
| AC-001: baseURL从VITE_API_BASE_URL读取，timeout 30000ms | ✅ 已实现 | 否 |
| AC-002: 请求拦截器自动携带Authorization: Bearer {token} | ✅ 已实现，且在回调内函数式获取userStore | 否 |
| AC-003: 响应拦截器成功分支：code===200返回data，业务错误ElMessage提示 | ✅ 已实现 | 否 |
| AC-004: 响应拦截器错误分支：401跳转登录+清除Token，403/404/超时有友好提示 | ✅ 已实现 | 否 |
| AC-010: 请求拦截器在回调内函数式获取userStore，无循环依赖 | ✅ 已实现 | 否 |

**结论**：`api/index.ts` 已完整符合所有验收标准，无需修改。

### Step 2: 创建 `api/user.ts`

导出 `userApi` 对象，包含6个方法：

```typescript
export const userApi = {
  register(data: { username: string; email: string; password: string })
  login(data: { username: string; password: string }): Promise<LoginResponse>
  getUserInfo(userId: string)
  getProfile(userId: string): Promise<ProfileResponse>
  createProfile(userId: string, data: UserProfile): Promise<ProfileResponse>
  updateProfile(userId: string, data: UserProfile): Promise<ProfileResponse>
}
```

- 依赖类型：`LoginResponse`、`ProfileResponse`、`UserProfile` 来自 `@/types/user`
- API路径与AGENTS.md API契约一致

### Step 3: 创建 `api/paper.ts`

导出 `paperApi` 对象，包含5个方法：

```typescript
export const paperApi = {
  list(params: { page: number; size: number })
  getDetail(paperId: string)
  search(params: SearchParams)  // 含 q/page/size/yearFrom/yearTo/venue/sort
  addFavorite(paperId: string)
  removeFavorite(paperId: string)
}
```

- 依赖类型：`Paper`、`FilterParams` 来自 `@/types/paper`，`PageResponse` 来自 `@/types/common`
- search参数需定义 `SearchParams` 接口（扩展FilterParams，增加q/page/size）

### Step 4: 创建 `api/analysis.ts`

导出 `analysisApi` 对象，包含6个方法：

```typescript
export const analysisApi = {
  analyzePaper(data: { paperId: string })
  comparePapers(data: { paperIds: string[] })
  generateReport(data: { topic: string; paperIds: string[] })
  getResult(analysisId: string)
  getStatus(analysisId: string)
  getAgentStreamUrl(analysisId: string): string  // 返回SSE URL，非HTTP调用
}
```

- 依赖类型：`AnalysisResult` 来自 `@/types/analysis`
- `getAgentStreamUrl` 返回字符串URL，不发起HTTP请求

### Step 5: 创建 `api/session.ts`

导出 `sessionApi` 对象，包含4个方法：

```typescript
export const sessionApi = {
  create(data: { topic: string })
  list(params: { page: number; size: number })
  getDetail(sessionId: string)
  delete(sessionId: string)
}
```

- 依赖类型：`PageResponse` 来自 `@/types/common`

### Step 6: 验证TypeScript编译

运行 `npx vue-tsc --noEmit` 确认无类型错误。

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 审查（无需修改） | `Veritas/frontend/src/api/index.ts` | 已符合验收标准 |
| 审查（无需修改） | `Veritas/frontend/src/types/common.ts` | 已符合验收标准 |
| **创建** | `Veritas/frontend/src/api/user.ts` | 用户管理API（6个方法） |
| **创建** | `Veritas/frontend/src/api/paper.ts` | 论文管理API（5个方法） |
| **创建** | `Veritas/frontend/src/api/analysis.ts` | 分析服务API（6个方法） |
| **创建** | `Veritas/frontend/src/api/session.ts` | 会话管理API（4个方法） |

## 验收标准对照

| ID | 验收标准 | 实现方式 |
|----|---------|---------|
| AC-001 | Axios实例baseURL从VITE_API_BASE_URL读取，timeout 30000ms | api/index.ts 已实现 |
| AC-002 | 请求拦截器：登录后请求自动携带Authorization: Bearer {token} | api/index.ts 已实现 |
| AC-003 | 响应拦截器成功分支：code===200返回data，业务错误ElMessage提示 | api/index.ts 已实现 |
| AC-004 | 响应拦截器错误分支：401跳转登录+清除Token，403/404/超时有友好提示 | api/index.ts 已实现 |
| AC-005 | userApi包含6个方法 | api/user.ts 创建 |
| AC-006 | paperApi包含5个方法 | api/paper.ts 创建 |
| AC-007 | analysisApi包含6个方法 | api/analysis.ts 创建 |
| AC-008 | sessionApi包含4个方法 | api/session.ts 创建 |
| AC-009 | types/common.ts定义ApiResponse和PageResponse | 已存在 |
| AC-010 | 请求拦截器在回调内函数式获取userStore，无循环依赖 | api/index.ts 已实现 |
