# Pinia Stores 骨架实现

## 功能描述
- 解决了前端状态管理的基础架构问题，为4个核心业务域（用户、论文、会话、Agent）建立了独立的状态管理Store
- 实现了4个Pinia Store的完整Actions逻辑，将原有TODO占位替换为真实API调用
- 同步创建了4个API模块文件（user/paper/analysis/session），打通了 Store → API → 后端 的数据流通道
- 补充了Session相关的TypeScript类型定义
- 业务价值：为后续所有前端页面组件提供统一的状态管理和数据访问入口，确保数据流单向可控

## 实现逻辑

### 修改的核心文件列表
| 操作 | 文件 | 说明 |
|------|------|------|
| 新建 | `src/types/session.ts` | SessionResponse/SessionDetail 类型定义 |
| 新建 | `src/api/user.ts` | 用户API：register/login/getProfile/createProfile/updateProfile |
| 新建 | `src/api/paper.ts` | 论文API：list/getDetail/search/addFavorite/removeFavorite |
| 新建 | `src/api/analysis.ts` | 分析API：analyzePaper/comparePapers/generateReport/getResult/getStatus/getAgentStreamUrl |
| 新建 | `src/api/session.ts` | 会话API：create/list/getDetail/delete |
| 修改 | `src/stores/userStore.ts` | login接入API + fetchProfile/saveProfile实现 |
| 修改 | `src/stores/paperStore.ts` | searchPapers/toggleFavorite接入API |
| 修改 | `src/stores/sessionStore.ts` | createSession/fetchAnalysisResult接入API |
| 验证 | `src/stores/agentStore.ts` | 已完整实现，无需修改 |

### 使用的设计模式
- **Composition API Setup Store** — 使用 `defineStore('name', () => {...})` 风格，用 `ref`/`computed`/函数定义 State/Getters/Actions
- **业务域划分** — 按用户/论文/会话/Agent 4个业务域独立划分Store，避免全局大Store
- **分层调用** — View → Store Action → API调用 → 后端，异步操作在Store Actions中
- **Token持久化** — userStore通过localStorage实现Token跨刷新持久化，常量key避免硬编码

### 关键代码逻辑说明

**userStore Token管理**：
- State从localStorage初始化：`ref<string>(localStorage.getItem(TOKEN_KEY) || '')`
- login成功后同步写入state和localStorage
- logout清除state和localStorage
- 禁止console.log Token内容（安全约束）

**paperStore 5篇限制**：
- `togglePaperSelection` 使用 `MAX_SELECTED_PAPERS = 5` 常量
- 已选论文再点击取消选择，未选论文且未达上限则添加

**sessionStore Map缓存**：
- `analysisResults` 使用 `Map<string, AnalysisResult>` 存储分析结果
- `fetchAnalysisResult` 获取后自动存入Map，避免重复请求

**agentStore 进度计算**：
- `progress = completed / total`，total为0时返回0
- `updateAgentState` 使用展开运算符合并partial state

## 接口变更

### Request — userStore.login
```json
{
  "username": "zhangsan",
  "password": "password123"
}
```

### Response — LoginResponse
```json
{
  "token": "eyJhbGciOiJIUzI1NiJ9...",
  "userId": "usr_001",
  "username": "zhangsan",
  "hasProfile": false
}
```

### Request — paperStore.searchPapers
```json
{
  "q": "Multi-Agent协同决策",
  "page": 1,
  "size": 10,
  "yearFrom": 2020,
  "yearTo": 2024,
  "sort": "relevance"
}
```

### Response — PageResponse<Paper>
```json
{
  "items": [
    {
      "paperId": "arxiv_2024_001",
      "title": "A Survey on Multi-Agent Systems",
      "authors": ["Zhang", "Li", "Wang"],
      "abstract": "本文综述了多智能体...",
      "year": 2024,
      "venue": "ACL",
      "keywords": ["Multi-Agent", "LLM"],
      "citationCount": 156,
      "score": 0.95,
      "recommendReason": "与您的研究方向匹配"
    }
  ],
  "total": 85,
  "page": 1,
  "size": 10,
  "totalPages": 9
}
```

### Request — sessionStore.createSession
```json
{
  "topic": "Multi-Agent协同决策"
}
```

### Response — SessionResponse
```json
{
  "sessionId": "ses_001",
  "topic": "Multi-Agent协同决策",
  "status": "active",
  "createdAt": "2026-05-25T10:00:00Z"
}
```

## 测试结果
- 测试场景1：TypeScript编译 `npx vue-tsc --noEmit` — 零错误通过 ✅
- 测试场景2：开发服务器 `npm run dev` — 369ms启动成功 ✅
- 测试场景3：4个Store可正常创建和导入（通过编译验证） ✅
- 是否通过：是

## 相关文件
- `Veritas/frontend/src/stores/userStore.ts`
- `Veritas/frontend/src/stores/paperStore.ts`
- `Veritas/frontend/src/stores/sessionStore.ts`
- `Veritas/frontend/src/stores/agentStore.ts`
- `Veritas/frontend/src/api/user.ts`
- `Veritas/frontend/src/api/paper.ts`
- `Veritas/frontend/src/api/analysis.ts`
- `Veritas/frontend/src/api/session.ts`
- `Veritas/frontend/src/types/session.ts`
- `Veritas/frontend/src/main.ts`（已注册Pinia，无需修改）
