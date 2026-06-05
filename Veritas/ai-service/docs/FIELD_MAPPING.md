# FIELD_MAPPING.md — 字段映射与契约文档

> XH-202630 科研文献智能助手 · AI Service 层
> 版本: 1.0 · 最后更新: 2026-06-04

---

## 目录

1. [端点完整契约](#1-端点完整契约)
2. [字段命名映射表](#2-字段命名映射表)
3. [枚举映射表](#3-枚举映射表)
4. [SSE 事件清单](#4-sse-事件清单)
5. [ChromaDB 字段映射](#5-chromadb-字段映射)
6. [错误码体系](#6-错误码体系)
7. [curl 示例](#7-curl-示例)

---

## 1. 端点完整契约

### 1.1 POST /api/agent/analyze

| 项目 | 内容 |
|------|------|
| **URL** | `/api/agent/analyze` |
| **方法** | POST |
| **Content-Type** | application/json |
| **描述** | 同步分析接口，Java 后端调用后阻塞等待完整结果 |

**请求示例：**

```json
{
  "topic": "Multi-Agent协同决策",
  "paperIds": ["arxiv_2024_001", "arxiv_2024_002"],
  "userId": "usr_001",
  "userProfile": {
    "educationLevel": "master",
    "researchField": "NLP",
    "knowledgeLevel": "intermediate",
    "preferredStyle": "balanced"
  },
  "analysisType": "report",
  "analysisId": "anl_20240523_001"
}
```

**成功响应 (200)：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "analysisId": "anl_20240523_001",
    "status": "completed",
    "report": "## 文献综述\n...",
    "citations": [{"index": 1, "paper_id": "arxiv_2024_001", "citation": "[Author, 2024]"}],
    "agentStates": [
      {"agentName": "retriever", "status": "completed", "progress": 1.0, "intermediateResult": "Found 10 papers", "durationMs": 1200},
      {"agentName": "analyzer", "status": "completed", "progress": 1.0, "intermediateResult": "", "durationMs": 8000},
      {"agentName": "generator", "status": "completed", "progress": 1.0, "intermediateResult": "", "durationMs": 15000}
    ],
    "degraded": false,
    "degradedReason": null
  },
  "timestamp": 1716441600000
}
```

**状态码：**

| HTTP 状态码 | 业务 code | 含义 |
|-------------|-----------|------|
| 200 | 200 | 分析成功 |
| 422 | 422 | 请求参数校验失败（缺字段/枚举非法/extra字段） |
| 500 | 500 | 工作流执行失败 |
| 503 | 503 | LLM/Prompt/Search 服务未就绪 |

**错误码：**

| code | 含义 |
|------|------|
| 422 | 参数校验失败（Pydantic ValidationError 或 ValidationException） |
| 500 | 分析任务执行失败 |
| 503 | 模型未加载（ModelNotLoadedException） |

**请求 Headers：**

| Header | 必填 | 说明 |
|--------|------|------|
| Content-Type | 是 | application/json |

---

### 1.2 POST /api/agent/analyze/stream

| 项目 | 内容 |
|------|------|
| **URL** | `/api/agent/analyze/stream` |
| **方法** | POST |
| **Content-Type** | application/json |
| **描述** | SSE 流式分析接口，实时推送 Agent 执行状态 |

**请求示例：**

```json
{
  "topic": "Multi-Agent协同决策",
  "paperIds": ["arxiv_2024_001"],
  "userId": "usr_001",
  "analysisType": "report",
  "analysisId": "anl_20240523_002"
}
```

**SSE 响应流示例：**

```
id: 1
event: agent_started
data: {"agentName":"retriever","status":"running","analysisId":"anl_20240523_002","timestamp":1716441600000}

id: 2
event: agent_state_update
data: {"agentName":"retriever","status":"running","progress":0.1,"analysisId":"anl_20240523_002","intermediateResult":"","durationMs":0}

id: 3
event: agent_completed
data: {"agentName":"retriever","status":"completed","progress":1.0,"analysisId":"anl_20240523_002","intermediateResult":"Found 10 papers","durationMs":1200}

id: 4
event: agent_started
data: {"agentName":"analyzer","status":"running","analysisId":"anl_20240523_002","timestamp":1716441602000}

id: 5
event: agent_completed
data: {"agentName":"analyzer","status":"completed","progress":1.0,"analysisId":"anl_20240523_002","intermediateResult":"","durationMs":8000}

id: 6
event: agent_started
data: {"agentName":"generator","status":"running","analysisId":"anl_20240523_002","timestamp":1716441610000}

id: 7
event: agent_completed
data: {"agentName":"generator","status":"completed","progress":1.0,"analysisId":"anl_20240523_002","intermediateResult":"","durationMs":15000}

id: 8
event: analysis_completed
data: {"analysisId":"anl_20240523_002","status":"completed","finalReport":"## 文献综述\n...","degraded":false,"degradedReason":null,"totalDurationMs":24200}
```

**状态码：**

| HTTP 状态码 | 业务 code | 含义 |
|-------------|-----------|------|
| 200 | — | SSE 流开始（Content-Type: text/event-stream） |
| 503 | 503 | LLM/Prompt/Search 服务未就绪（无法启动流） |

**请求 Headers：**

| Header | 必填 | 说明 |
|--------|------|------|
| Content-Type | 是 | application/json |
| Last-Event-ID | 否 | 断线重连时传入上次最后事件的 ID |

**响应 Headers：**

| Header | 说明 |
|--------|------|
| Content-Type | text/event-stream |
| Cache-Control | no-cache |
| Connection | keep-alive |

---

### 1.3 POST /api/search/

| 项目 | 内容 |
|------|------|
| **URL** | `/api/search/` |
| **方法** | POST |
| **Content-Type** | application/json |
| **描述** | 基础语义检索，基于 Embedding 向量相似度 |

**请求示例：**

```json
{
  "query": "Transformer注意力机制",
  "topK": 10,
  "filters": {
    "yearFrom": 2020,
    "yearTo": 2024,
    "venue": "ACL"
  }
}
```

**成功响应 (200)：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "results": [
      {
        "paperId": "arxiv_2024_001",
        "title": "Attention Is All You Need",
        "abstract": "We propose a new network architecture...",
        "score": 0.95,
        "year": 2017,
        "venue": "NeurIPS"
      }
    ],
    "total": 1
  },
  "timestamp": 1716441600000
}
```

**状态码：**

| HTTP 状态码 | 业务 code | 含义 |
|-------------|-----------|------|
| 200 | 200 | 检索成功 |
| 422 | 422 | 参数校验失败 |
| 503 | 503 | SearchService 未就绪 |

---

### 1.4 POST /api/search/hybrid

| 项目 | 内容 |
|------|------|
| **URL** | `/api/search/hybrid` |
| **方法** | POST |
| **Content-Type** | application/json |
| **描述** | 混合检索（语义 + 关键词），支持个性化重排序 |

**请求示例：**

```json
{
  "query": "Multi-Agent协同决策",
  "topK": 10,
  "filters": {
    "yearFrom": 2020,
    "yearTo": 2024
  },
  "userProfile": {
    "educationLevel": "master",
    "researchField": "NLP",
    "knowledgeLevel": "intermediate",
    "preferredStyle": "balanced"
  }
}
```

**成功响应 (200)：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "results": [
      {
        "paperId": "arxiv_2024_001",
        "title": "Multi-Agent Collaborative Decision Making",
        "abstract": "We study multi-agent collaboration...",
        "score": 0.92,
        "year": 2024,
        "venue": "ACL"
      }
    ],
    "total": 1
  },
  "timestamp": 1716441600000
}
```

**状态码：**

| HTTP 状态码 | 业务 code | 含义 |
|-------------|-----------|------|
| 200 | 200 | 检索成功 |
| 422 | 422 | 参数校验失败 |
| 503 | 503 | SearchService 未就绪 |

---

### 1.5 GET /api/search/suggest

| 项目 | 内容 |
|------|------|
| **URL** | `/api/search/suggest` |
| **方法** | GET |
| **描述** | 搜索建议（基于 ChromaDB 论文标题） |

**请求参数 (Query)：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | 是 | 搜索查询文本（1-100字符） |

**请求示例：**

```
GET /api/search/suggest?query=Multi-Agent
```

**成功响应 (200)：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "suggestions": [
      "Multi-Agent Collaborative Decision Making",
      "AgentBench: A Comprehensive Benchmark"
    ],
    "total": 2
  },
  "timestamp": 1716441600000
}
```

**状态码：**

| HTTP 状态码 | 业务 code | 含义 |
|-------------|-----------|------|
| 200 | 200 | 建议成功 |
| 422 | 422 | query 参数缺失或非法 |
| 503 | 503 | SearchService 未就绪 |

---

### 1.6 GET /health

| 项目 | 内容 |
|------|------|
| **URL** | `/health` |
| **方法** | GET |
| **描述** | 健康检查（critical_ok 规则 + 统一响应格式） |

**请求示例：**

```
GET /health
```

**成功响应 (200)：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "llm": "loaded",
    "embedding": "loaded_api",
    "chroma": "connected",
    "prompts": "loaded",
    "searchService": "ready",
    "reranker": "ready",
    "status": "UP"
  },
  "timestamp": 1716441600000
}
```

**降级响应 (503)：**

```json
{
  "code": 503,
  "message": "DEGRADED",
  "data": {
    "llm": "not_loaded",
    "embedding": "not_loaded",
    "chroma": "not_connected",
    "prompts": "not_loaded",
    "searchService": "not_initialized",
    "reranker": "not_initialized",
    "status": "DEGRADED"
  },
  "timestamp": 1716441600000
}
```

**状态码：**

| HTTP 状态码 | 业务 code | 含义 |
|-------------|-----------|------|
| 200 | 200 | 关键组件全部就绪（UP） |
| 503 | 503 | 关键组件未就绪（DEGRADED） |

**critical_ok 规则：**

- `llm == "loaded"`
- `embedding in ("loaded", "loaded_api", "loaded_local")`
- `chroma == "connected"`

三个条件同时满足时返回 200，否则返回 503。

---

### 1.7 GET /api/model/status

| 项目 | 内容 |
|------|------|
| **URL** | `/api/model/status` |
| **方法** | GET |
| **描述** | 模型与服务状态详情（含 GPU/ChromaDB/Provider 信息） |

**请求示例：**

```
GET /api/model/status
```

**成功响应 (200)：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "llm": "loaded",
    "embedding": "loaded_api",
    "chroma": "connected",
    "prompts": "loaded",
    "embeddingDimension": 1024,
    "activeLlmProvider": "api",
    "providerCandidates": ["api"],
    "chromaPaperCount": 200,
    "gpuMemoryUsed": null,
    "llmProviderCount": 1,
    "searchService": "ready",
    "reranker": "ready"
  },
  "timestamp": 1716441600000
}
```

**状态码：**

| HTTP 状态码 | 业务 code | 含义 |
|-------------|-----------|------|
| 200 | 200 | 状态查询成功 |
| 503 | 503 | LLM 服务未就绪 |

---

## 2. 字段命名映射表

> **核心规则**：Python 内部使用 snake_case，JSON 传输使用 camelCase（通过 Pydantic alias），
> Java 后端使用 camelCase。三端通过 Pydantic `alias` + `populate_by_name=True` 实现自动转换。

| Java camelCase | Python snake_case | JSON camelCase | 所属模型 |
|----------------|-------------------|----------------|----------|
| analysisId | analysis_id | analysisId | AnalyzeRequest / AnalyzeResponse |
| analysisType | analysis_type | analysisType | AnalyzeRequest |
| paperIds | paper_ids | paperIds | AnalyzeRequest |
| userId | user_id | userId | AnalyzeRequest |
| userProfile | user_profile | userProfile | AnalyzeRequest / HybridSearchRequest |
| educationLevel | education_level | educationLevel | UserProfile |
| researchField | research_field | researchField | UserProfile |
| knowledgeLevel | knowledge_level | knowledgeLevel | UserProfile |
| preferredStyle | preferred_style | preferredStyle | UserProfile |
| agentName | agent_name | agentName | AgentStateResponse / SSE |
| agentStates | agent_states | agentStates | AnalyzeResponse |
| intermediateResult | intermediate_result | intermediateResult | AgentStateResponse / SSE |
| durationMs | duration_ms | durationMs | AgentStateResponse / SSE |
| degradedReason | degraded_reason | degradedReason | AnalyzeResponse / SSE |
| activeLlmProvider | active_llm_provider | activeLlmProvider | ModelStatusResponse |
| embeddingDimension | embedding_dimension | embeddingDimension | ModelStatusResponse |
| providerCandidates | provider_candidates | providerCandidates | ModelStatusResponse |
| chromaPaperCount | chroma_paper_count | chromaPaperCount | ModelStatusResponse |
| gpuMemoryUsed | gpu_memory_used | gpuMemoryUsed | ModelStatusResponse |
| llmProviderCount | llm_provider_count | llmProviderCount | ModelStatusResponse |
| searchService | search_service | searchService | ModelStatusResponse / Health |
| reranker | reranker | reranker | ModelStatusResponse / Health |
| topK | top_k | topK | SearchRequest / HybridSearchRequest |
| paperId | paper_id | paperId | SearchResultItem |
| finalReport | — | finalReport | SSE (analysis_completed) |
| totalDurationMs | — | totalDurationMs | SSE (analysis_completed) |
| errorCode | — | errorCode | SSE (error) |
| errorMessage | — | errorMessage | SSE (error) |
| lastEventId | — | lastEventId | SSE Header (Last-Event-ID) |
| eventId | — | id | SSE event id 字段 |

> **说明**：
> - `finalReport`、`totalDurationMs`、`errorCode`、`errorMessage` 仅在 SSE 事件的 data JSON 中出现，
>   不属于 Pydantic 模型字段，直接在 `orchestrator.py` 中以 camelCase 硬编码构造。
> - `lastEventId` 是 HTTP 请求 Header `Last-Event-ID` 的语义名，非 JSON 字段。
> - `eventId` 对应 SSE 协议的 `id:` 字段，在 data JSON 外层。

---

## 3. 枚举映射表

> **核心规则**：4 个 StrEnum 的字符串值在三端完全一致（小写英文），
> Python 使用 StrEnum 保证 `str(enum_member) == enum_member.value`。

### 3.1 EducationLevel

| Java 枚举 | Python StrEnum | JSON/字符串值 |
|-----------|---------------|--------------|
| UNDERGRADUATE | EducationLevel.UNDERGRADUATE | `"undergraduate"` |
| MASTER | EducationLevel.MASTER | `"master"` |
| PHD | EducationLevel.PHD | `"phd"` |
| FACULTY | EducationLevel.FACULTY | `"faculty"` |

### 3.2 KnowledgeLevel

| Java 枚举 | Python StrEnum | JSON/字符串值 |
|-----------|---------------|--------------|
| BEGINNER | KnowledgeLevel.BEGINNER | `"beginner"` |
| INTERMEDIATE | KnowledgeLevel.INTERMEDIATE | `"intermediate"` |
| ADVANCED | KnowledgeLevel.ADVANCED | `"advanced"` |
| EXPERT | KnowledgeLevel.EXPERT | `"expert"` |

### 3.3 PreferredStyle

| Java 枚举 | Python StrEnum | JSON/字符串值 |
|-----------|---------------|--------------|
| SIMPLE | PreferredStyle.SIMPLE | `"simple"` |
| BALANCED | PreferredStyle.BALANCED | `"balanced"` |
| TECHNICAL | PreferredStyle.TECHNICAL | `"technical"` |

### 3.4 AnalysisType

| Java 枚举 | Python StrEnum | JSON/字符串值 |
|-----------|---------------|--------------|
| PAPER_ANALYSIS | AnalysisType.PAPER_ANALYSIS | `"paper_analysis"` |
| COMPARE | AnalysisType.COMPARE | `"compare"` |
| REPORT | AnalysisType.REPORT | `"report"` |

---

## 4. SSE 事件清单

> **协议格式**：`event: <type>\nid: <seq>\ndata: <json_string>\n\n`
> **data 字段统一使用 camelCase**（与 JSON API 响应一致）。

### 4.1 agent_started

**触发时机**：Agent 开始执行

```json
{
  "agentName": "retriever",
  "status": "running",
  "analysisId": "anl_20240523_001",
  "timestamp": 1716441600000
}
```

### 4.2 agent_state_update

**触发时机**：Agent 状态变更（进度更新）

```json
{
  "agentName": "retriever",
  "status": "running",
  "progress": 0.1,
  "analysisId": "anl_20240523_001",
  "intermediateResult": "",
  "durationMs": 0
}
```

### 4.3 agent_completed

**触发时机**：Agent 正常完成

```json
{
  "agentName": "retriever",
  "status": "completed",
  "progress": 1.0,
  "analysisId": "anl_20240523_001",
  "intermediateResult": "Found 10 papers",
  "durationMs": 1200
}
```

### 4.4 agent_failed

**触发时机**：Agent 执行失败（不中断流，后续 Agent 继续执行）

```json
{
  "agentName": "analyzer",
  "status": "failed",
  "analysisId": "anl_20240523_001",
  "errorMessage": "LLM 调用超时",
  "durationMs": 30000
}
```

### 4.5 analysis_completed

**触发时机**：全流程结束（所有 Agent 执行完毕）

```json
{
  "analysisId": "anl_20240523_001",
  "status": "completed",
  "finalReport": "## 文献综述\n...",
  "degraded": false,
  "degradedReason": null,
  "totalDurationMs": 24200
}
```

**status 取值**：
- `"completed"` — 全部 Agent 正常完成
- `"degraded"` — 有 Agent 失败或超时，结果可能不完整

### 4.6 error

**触发时机**：错误事件（Agent 失败、超时等）

```json
{
  "analysisId": "anl_20240523_001",
  "errorCode": 408,
  "errorMessage": "全流程超时(120s)"
}
```

**errorCode 取值**：
- 408 — 全流程超时（AgentTimeoutException）
- 500 — Agent 执行异常

---

## 5. ChromaDB 字段映射

> **核心规则**：ChromaDB metadata 使用 snake_case 存储（Python 惯例），
> 向上层返回时由 VectorStoreService 转换为 camelCase。

### 5.1 metadata 字段

| ChromaDB metadata (snake_case) | API 响应 (camelCase) | 类型 | 说明 |
|-------------------------------|---------------------|------|------|
| paper_id | paperId | string | 论文唯一标识，如 `"arxiv_2401_12345"` |
| title | title | string | 论文标题 |
| abstract | — (作为 document 存储) | string | 论文摘要（存储在 ChromaDB documents 中） |
| year | year | int | 发表年份 |
| venue | venue | string | 发表会议/期刊 |
| authors | — | list[str] | 作者列表（仅 JSON 导入时使用，未存入 metadata） |
| keywords | — | list[str] | 关键词列表（仅 JSON 导入时使用，未存入 metadata） |

### 5.2 扩展 metadata 字段

| ChromaDB metadata | 说明 |
|-------------------|------|
| citation_count | 引用次数（默认 0） |
| chunk_index | 分块索引 |
| chunk_type | 分块类型（如 `"title_abstract"`） |

### 5.3 存储架构

```
ChromaDB Collection: papers
├── ids: ["arxiv_2401_12345_chunk_0", ...]     # 分块级 ID
├── embeddings: [[0.1, 0.2, ...], ...]          # 1024 维向量
├── metadatas: [{paper_id, title, year, ...}, ...]
└── documents: ["Title. Abstract text...", ...]    # 分块文本
```

---

## 6. 错误码体系

> **核心规则**：所有异常继承 `AIServiceException(code, message)`，
> 由全局异常处理器统一返回 `{code, message, data, timestamp}` 格式。

### 6.1 异常类层次

```
AIServiceException (code=500)
├── LLMException (code=503)
├── VectorStoreException (code=503)
├── AgentTimeoutException (code=408)
├── ModelNotLoadedException (code=503)
├── ValidationException (code=422)
└── RateLimitException (code=429)
```

### 6.2 异常详情

| 异常类 | 默认 code | 含义 | 触发场景 |
|--------|----------|------|---------|
| AIServiceException | 500 | AI 服务基础异常 | 未知内部错误 |
| LLMException | 503 | LLM 调用异常 | LLM API 超时/返回错误/模型加载失败 |
| VectorStoreException | 503 | 向量数据库异常 | ChromaDB 连接失败/维度不匹配/查询异常 |
| AgentTimeoutException | 408 | Agent 执行超时 | 单 Agent 超过 AGENT_TIMEOUT(30s) 或全流程超过 AGENT_FULL_TIMEOUT(120s) |
| ModelNotLoadedException | 503 | 模型未加载 | LLM/Embedding/Prompt/Search 服务未初始化 |
| ValidationException | 422 | 业务校验异常 | 跨字段组合校验失败（语义层面，与 Pydantic 422 区分） |
| RateLimitException | 429 | 限流异常 | 请求过于频繁 |

### 6.3 错误响应格式

所有异常由 FastAPI 全局异常处理器统一包装：

```json
{
  "code": 503,
  "message": "LLM服务未就绪",
  "data": null,
  "timestamp": 1716441600000
}
```

### 6.4 Pydantic ValidationError (422)

由 FastAPI `RequestValidationError` 处理器捕获，返回中文友好 message：

```json
{
  "code": 422,
  "message": "参数校验失败: userId 字段必填; analysisType 取值非法",
  "data": null,
  "timestamp": 1716441600000
}
```

---

## 7. curl 示例

> **注意**：以下示例使用 `localhost:8000` 作为 AI Service 地址。
> 实际部署中 Java 后端通过内部 HTTP 调用，不暴露 AI Service 端口。

### 7.1 POST /api/agent/analyze

```bash
curl -X POST http://localhost:8000/api/agent/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Multi-Agent协同决策",
    "paperIds": ["arxiv_2024_001"],
    "userId": "usr_001",
    "userProfile": {
      "educationLevel": "master",
      "researchField": "NLP",
      "knowledgeLevel": "intermediate",
      "preferredStyle": "balanced"
    },
    "analysisType": "report",
    "analysisId": "anl_test_001"
  }'
```

### 7.2 POST /api/agent/analyze/stream

```bash
curl -X POST http://localhost:8000/api/agent/analyze/stream \
  -H "Content-Type: application/json" \
  -H "Last-Event-ID: 3" \
  -d '{
    "topic": "Transformer注意力机制",
    "paperIds": ["arxiv_2024_002"],
    "userId": "usr_001",
    "analysisType": "paper_analysis",
    "analysisId": "anl_test_002"
  }'
```

### 7.3 POST /api/search/

```bash
curl -X POST http://localhost:8000/api/search/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Transformer注意力机制",
    "topK": 5,
    "filters": {
      "yearFrom": 2020,
      "yearTo": 2024,
      "venue": "ACL"
    }
  }'
```

### 7.4 GET /health

```bash
curl http://localhost:8000/health
```

### 7.5 GET /api/model/status

```bash
curl http://localhost:8000/api/model/status
```

---

## 附录 A：字段转换规则

### A.1 Python → JSON（序列化）

```python
# Pydantic model_dump(by_alias=True) 自动将 snake_case 转为 camelCase alias
response_data.model_dump(by_alias=True)
# analysis_id → analysisId
# user_profile → userProfile
# education_level → educationLevel
```

### A.2 JSON → Python（反序列化）

```python
# Pydantic populate_by_name=True 允许同时接受 camelCase alias 和 snake_case
AnalyzeRequest.model_validate(json_data)
# "analysisId" → analysis_id
# "paperIds" → paper_ids
# "userId" → user_id
```

### A.3 Java → Python 调用链

```
Java (camelCase)
  ↓ WebClient POST JSON (camelCase)
Python FastAPI (Pydantic alias 自动转为 snake_case)
  ↓ 内部处理 (snake_case)
Python FastAPI (model_dump by_alias=True 转回 camelCase)
  ↓ JSON Response (camelCase)
Java (camelCase 反序列化)
```

---

## 附录 B：统一响应格式契约

所有 API 端点（除 SSE 流）必须返回以下 4 字段根级结构：

```json
{
  "code": 200,
  "message": "success",
  "data": { ... },
  "timestamp": 1716441600000
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务状态码（非 HTTP 状态码，但通常一致） |
| message | string | 人类可读消息（成功/错误描述） |
| data | any | 业务数据（成功时为对象/数组，失败时为 null） |
| timestamp | int | UTC 毫秒时间戳（与 Java `System.currentTimeMillis()` 一致） |

---

## 附录 C：SSE 协议约定

### C.1 事件顺序

```
agent_started → agent_state_update → agent_completed → ... → analysis_completed
                                                              (或 error)
```

### C.2 降级场景

当某个 Agent 失败时，流不会中断：

```
agent_started(retriever) → agent_completed(retriever)
→ agent_started(analyzer) → agent_failed(analyzer) → error
→ agent_started(generator) → agent_completed(generator)
→ analysis_completed(status="degraded")
```

### C.3 超时场景

全流程超时时，直接推送 error + analysis_completed：

```
agent_started(retriever) → agent_completed(retriever)
→ agent_started(analyzer) → ... (超时)
→ error(errorCode=408) → analysis_completed(status="degraded")
```

---

## 附录 D：安全注意事项

1. **extra="forbid"** — AnalyzeRequest 和 UserProfile 设置 `extra="forbid"`，拒绝未定义字段，防止字段污染攻击
2. **userId 必填** — AnalyzeRequest 的 userId 字段 `min_length=1`，禁止空字符串
3. **枚举严格校验** — analysisType / educationLevel / knowledgeLevel / preferredStyle 使用 StrEnum，非法值触发 422
4. **无真实密钥** — 本文档所有示例使用 `localhost:8000`，不暴露真实 API Key 或内部 IP
5. **SSE data 为 JSON 字符串** — SSE 事件的 data 字段是 JSON 字符串（`json.dumps`），不是原始对象
