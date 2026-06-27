# 06 — API契约

> 加载时机：编写 API 接口、跨服务调用、前后端联调时加载。
> 关联文件：[07-standards.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/agents/07-standards.md) | [05-database.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/agents/05-database.md)

---

## 1 Java后端API

```
/api/users/register              POST         注册
/api/users/login                 POST         登录
/api/users/logout                POST         退出登录
/api/users/{userId}              GET          查询用户
/api/users/{userId}              PUT          更新用户
/api/users/{userId}/profile      GET/POST/PUT 画像CRUD
/api/papers                      GET          论文列表(分页)
/api/papers/{paperId}            GET          论文详情
/api/papers/search               GET          论文搜索
/api/papers/{paperId}/favorite   POST/DELETE  收藏/取消收藏
/api/papers/favorites            GET          收藏列表
/api/sessions                    POST/GET     创建/列表会话
/api/sessions/{sessionId}        GET/DELETE   详情/删除
/api/sessions/{sessionId}/status PUT          更新会话状态
/api/analysis/paper              POST         论文分析
/api/analysis/compare            POST         对比分析
/api/analysis/report             POST         综述生成
/api/analysis/{analysisId}       GET          分析结果
/api/analysis/{analysisId}/status GET         分析状态
/api/analysis/{analysisId}/agent-stream  GET(SSE)   Agent状态流（Java→前端，支持 Last-Event-ID 重连）
/api/analysis/{analysisId}/export       GET          报告导出（PDF/Word）
```

---

## 2 Python AI服务API

```
/api/agent/analyze               POST    启动6-Agent工作流（同步）
/api/agent/analyze/stream        POST(SSE)  Agent状态流（sse-starlette EventSourceResponse，支持 Last-Event-ID 重连）
/api/search                      POST    语义检索
/api/search/hybrid               POST    混合检索（关键词+语义 RRF 融合）
/api/search/suggest              GET     检索建议
/api/model/status                GET     模型状态（12字段：llm/embedding/chroma/prompts/embeddingDimension/activeLlmProvider/providerCandidates/chromaPaperCount/gpuMemoryUsed/llmProviderCount/searchService/reranker）
/health                          GET     健康检查（6组件）
```

---

## 3 统一响应格式

```json
{"code": 200, "message": "success", "data": {...}, "timestamp": "..."}
```

---

## 4 Java→Python请求契约

```json
{
  "topic": "Multi-Agent协同决策",
  "paper_ids": ["arxiv_2024_001"],
  "user_id": "usr_001",
  "user_profile": {
    "education_level": "master",
    "research_field": "NLP",
    "knowledge_level": "intermediate",
    "preferred_style": "balanced"
  },
  "analysis_type": "report",
  "analysis_id": "anl_001"
}
```

---

## 5 SSE事件格式（8 种）

```
// 1. Agent 状态更新
event: agent_state_update
id: evt_1
data: {"agentName": "retriever", "status": "running", "progress": 0.6, "intermediateResult": "找到15篇相关论文", "durationMs": 1200, "analysisId": "anl_001"}

// 2. Agent 完成
event: agent_completed
data: {"agentName": "analyzer", "status": "completed", "durationMs": 8000}

// 3. 检索中间结果
event: retrieval_intermediate
data: {"agentName": "retriever", "intermediateResult": "Top10候选论文"}

// 4. 分析中间结果
event: analysis_intermediate
data: {"agentName": "analyzer", "intermediateResult": "已分析5/10篇"}

// 5. 生成 token 流
event: generation_token
data: {"token": "...", "analysisId": "anl_001"}

// 6. 审核拒绝（触发重试）
event: review_rejected
data: {"issues": [...], "suggestions": [...], "regenerateCount": 0}

// 7. 分析完成
event: analysis_completed
data: {"analysisId": "anl_001", "status": "completed"}

// 8. 心跳
event: ping
data: {"timestamp": "..."}
```

**双层转发链路**：Python (`/api/agent/analyze/stream`) → Java (`/api/analysis/{id}/agent-stream`) → 前端 (`useSSE` composable + EventSource)。每层独立处理 `Last-Event-ID` 断点续传。
