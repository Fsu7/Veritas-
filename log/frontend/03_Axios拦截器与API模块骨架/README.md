# Axios拦截器与API模块骨架

## 功能描述
- 解决了前端与Java后端之间的HTTP通信基础设施问题，统一了请求/响应处理逻辑
- 实现了Axios实例创建、JWT Token自动注入、统一错误处理（401/403/404/超时/网络错误），以及4个API模块骨架（user/paper/analysis/session）共21个API方法
- 业务价值：为后续所有前端页面提供标准化的API调用能力，确保认证流程自动化、错误处理一致化，避免每个页面重复编写HTTP请求逻辑

## 实现逻辑
- 修改的核心文件列表：
  - `Veritas/frontend/src/api/index.ts` — 审查确认已符合标准（Axios实例+拦截器，由前序task创建）
  - `Veritas/frontend/src/api/user.ts` — **新建**，6个用户管理API方法
  - `Veritas/frontend/src/api/paper.ts` — **新建**，5个论文管理API方法
  - `Veritas/frontend/src/api/analysis.ts` — **新建**，6个分析服务API方法
  - `Veritas/frontend/src/api/session.ts` — **新建**，4个会话管理API方法
  - `Veritas/frontend/src/types/common.ts` — 审查确认已符合标准（ApiResponse/PageResponse，由前序task创建）

- 使用的设计模式：
  - **拦截器模式**：请求拦截器自动注入JWT Token，响应拦截器统一解包ApiResponse和错误处理
  - **模块化封装**：按业务域划分API模块（user/paper/analysis/session），每个模块导出单一对象
  - **函数式Store获取**：在拦截器回调内调用`useUserStore()`而非模块顶层导入，避免循环依赖

- 关键代码逻辑说明：
  - 响应拦截器成功分支：`data.code === 200` 时直接返回 `data.data`（解包ApiResponse），调用方无需再`.data.data`
  - 响应拦截器错误分支：401→清除Token+跳转登录页；403→无权限提示；404→资源不存在提示；ECONNABORTED→超时提示；其他→网络错误提示
  - `analysisApi.getAgentStreamUrl` 返回SSE URL字符串而非发起HTTP请求，供`EventSource`使用
  - `paperApi.search` 参数使用 `SearchParams` 接口扩展 `FilterParams`，增加 `q`/`page`/`size`

## 接口变更

### Request — 用户注册
```json
POST /api/users/register
{
  "username": "zhangsan",
  "email": "zhangsan@example.com",
  "password": "password123"
}
```

### Response — 用户登录
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiJ9...",
    "userId": "usr_001",
    "username": "zhangsan",
    "hasProfile": false
  },
  "timestamp": 1716441600000
}
```

### Request — 论文搜索
```json
GET /api/papers/search?q=Multi-Agent&page=1&size=10&yearFrom=2020&yearTo=2024&venue=ACL&sort=relevance
```

### Response — 论文搜索
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "paperId": "arxiv_2024_001",
        "title": "A Survey on Multi-Agent Systems",
        "authors": ["Zhang", "Li"],
        "abstract": "...",
        "year": 2024,
        "venue": "ACL",
        "keywords": ["Multi-Agent", "LLM"],
        "citationCount": 156,
        "score": 0.95,
        "recommendReason": "与您的研究方向匹配"
      }
    ],
    "total": 156,
    "page": 1,
    "size": 10,
    "totalPages": 16
  },
  "timestamp": 1716441600000
}
```

### Request — 综述生成
```json
POST /api/analysis/report
{
  "topic": "Multi-Agent协同决策",
  "paperIds": ["arxiv_2024_001", "arxiv_2024_002"]
}
```

### Response — 综述生成
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "analysisId": "anl_001",
    "status": "processing"
  },
  "timestamp": 1716441600000
}
```

## 测试结果
- 测试场景1：TypeScript编译检查 `npx vue-tsc --noEmit` — 通过，0错误
- 测试场景2：Axios实例配置验证 — baseURL从`VITE_API_BASE_URL`读取，timeout=30000ms，Content-Type='application/json'
- 测试场景3：请求拦截器验证 — 在回调内函数式获取userStore，有Token时注入Authorization头，无Token时不注入
- 测试场景4：响应拦截器验证 — code===200返回data，非200 ElMessage提示；401跳转登录+清除Token
- 是否通过：是

## 相关文件
- `Veritas/frontend/src/api/index.ts` — Axios实例+拦截器（已存在，审查确认）
- `Veritas/frontend/src/api/user.ts` — 用户管理API（新建）
- `Veritas/frontend/src/api/paper.ts` — 论文管理API（新建）
- `Veritas/frontend/src/api/analysis.ts` — 分析服务API（新建）
- `Veritas/frontend/src/api/session.ts` — 会话管理API（新建）
- `Veritas/frontend/src/types/common.ts` — 通用类型定义（已存在，审查确认）
- `Veritas/frontend/src/types/user.ts` — 用户类型定义（已存在，被user.ts引用）
- `Veritas/frontend/src/types/paper.ts` — 论文类型定义（已存在，被paper.ts引用）
- `Veritas/frontend/src/types/analysis.ts` — 分析类型定义（已存在，被analysis.ts引用）
