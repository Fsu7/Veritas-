# AM3 API完善与Java对接

## 功能描述

- **实现了 AI 服务层接口规范化**: 统一响应格式 `{code, message, data, timestamp}`、StrEnum 严格校验、Pydantic `extra='forbid'` 安全防护、中文友好 422 错误消息
- **实现了 SSE 流式推送**: 7 种事件类型 (agent_started/agent_state_update/agent_completed/agent_failed/analysis_completed/error/ping)，异常不中断流，EventSourceResponse
- **完善了健康检查与模型状态**: /health 采用 critical_ok 规则 (llm+embedding+chroma 全 OK→200，否则 503)，/api/model/status 扩展 4 字段 (providerCandidates/chromaPaperCount/gpuMemoryUsed/llmProviderCount)
- **打通了 Java↔Python 通信链路**: camelCase alias + populate_by_name=True 确保 Java 端 WebClient 请求可被 Python 解析，响应以 camelCase 序列化
- **建立了字段映射文档与一致性验证**: 51 项自动测试覆盖 20+ 字段 camelCase alias，确保 Java snake_case → Python camelCase → JSON camelCase 全链路正确
- **实现了三级降级机制**: LLM 三路降级 (builtin→api→local)、Agent 超时跳过 (30s)、多 Agent 失败降级提示
- **增强了 SSE 稳定性**: Keep-alive ping 每 15s、Last-Event-ID 断线重连、客户端断开优雅关闭 (asyncio.CancelledError)、并发 SSE 隔离
- **修复了 6 个 Bug**: response_model 冲突、BaseAgent 异常吞噬、/health 格式不一致、422 英文消息、Last-Event-ID 零值问题、fail() HTTP 状态码错误
- **业务价值**: AM3 里程碑 12 项检查点全部通过，Java 后端可稳定调用 AI 服务，为 AM4 端到端集成奠定基础

## 实现逻辑

### 修改/新增的核心文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/utils/response.py` | 修改 | 新增 `fail_response()` 返回 JSONResponse 并设置正确 HTTP 状态码 |
| `app/models/enums.py` | 新增 | 7 个 StrEnum 类 (EducationLevel/KnowledgeLevel/PreferredStyle/AnalysisType 等) |
| `app/models/schemas.py` | 修改 | 9 个 Pydantic 模型，camelCase alias + populate_by_name=True + extra='forbid' |
| `app/exception.py` | 修改 | 7 个异常类 (503/408/422/429)，含 LLMException/ModelNotLoadedException |
| `app/main.py` | 修改 | /health critical_ok 规则、中文 422 处理器、AIServiceException 全局处理器 |
| `app/api/endpoints/agent.py` | 修改 | /analyze + /analyze/stream (SSE)，移除 response_model，统一 ok()/fail_response() |
| `app/api/endpoints/search.py` | 修改 | 3 个端点移除 response_model，错误路径使用 fail_response() |
| `app/api/endpoints/model.py` | 修改 | /status 扩展字段，移除 response_model |
| `app/agents/orchestrator.py` | 新增 | AgentOrchestrator 流式编排，7 种 SSE 事件，ping/Last-Event-ID/CancelledError |
| `docs/FIELD_MAPPING.md` | 新增 | 20+ 字段 camelCase ↔ snake_case 映射表 (~420 行) |
| `docs/DEGRADATION_TEST_REPORT.md` | 新增 | LLM 3 路降级 + Agent 超时 + 错误码验证报告 |
| `docs/AM3_TEST_REPORT.md` | 新增 | 187 项测试报告 |
| `docs/AM3_BUGFIX_LOG.md` | 新增 | 6 个 Bug 详细记录 |

### 架构设计

```mermaid
graph TB
    subgraph 请求校验
        REQ[AnalyzeRequest Pydantic] -->|StrEnum 严格校验| VAL[extra='forbid']
        VAL -->|422 中文友好| ERR[validation_exception_handler]
    end

    subgraph SSE流式推送
        SSER[POST /analyze/stream] --> ORCH[AgentOrchestrator]
        ORCH -->|yield SSE事件| RET[RetrieverAgent]
        ORCH -->|yield SSE事件| ANA[AnalyzerAgent]
        ORCH -->|yield SSE事件| GEN[GeneratorAgent]
        ORCH -->|15s间隔| PING[ping事件]
        ORCH -->|Last-Event-ID| RECON[断线重连]
    end

    subgraph 健康监控
        HEALTH[GET /health] --> CRIT{critical_ok?}
        CRIT -->|llm+emb+chroma全OK| 200[HTTP 200]
        CRIT -->|任一不可用| 503[HTTP 503]
    end

    subgraph 降级机制
        LLM[LLMService] -->|builtin失败| API[API provider]
        API -->|API失败| LOCAL[本地模型]
        AGENT[Agent.execute] -->|30s超时| SKIP[跳过该Agent]
        SKIP -->|降级提示| CONT[继续后续Agent]
    end

    subgraph 统一响应
        OK[ok(data)] -->|HTTP 200| CLIENT[Java WebClient]
        FAIL[fail_response(msg, code)] -->|HTTP 503/500| CLIENT
    end
```

### 统一响应格式

```json
// 成功
{"code": 200, "message": "success", "data": {...}, "timestamp": 1717500000000}

// 失败
{"code": 503, "message": "LLM服务未就绪", "data": null, "timestamp": 1717500000000}
```

### SSE 事件类型

| 事件类型 | 触发时机 | data 字段 |
|----------|---------|-----------|
| agent_started | Agent 开始执行 | {agentName, agentType, stepIndex} |
| agent_state_update | Agent 中间状态 | {agentName, progress, intermediateResult} |
| agent_completed | Agent 执行成功 | {agentName, durationMs, stepIndex} |
| agent_failed | Agent 执行失败 (不中断流) | {agentName, errorMessage, stepIndex} |
| analysis_completed | 全流程结束 | {analysisId, status, report, degraded, degradedReason} |
| error | 工作流异常 | {errorCode, errorMessage} |
| ping | 15s 无事件时保活 | {} |

## 接口变更

### POST /api/agent/analyze (统一响应包装)

**Request**:
```json
{
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
}
```

**Response (200)**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "analysisId": "anl_test_001",
    "status": "completed",
    "report": "## 文献综述\n...",
    "citations": [...],
    "agentStates": [
      {"agentName": "retriever", "status": "completed", "progress": 1.0, "durationMs": 1200}
    ],
    "degraded": false,
    "degradedReason": null
  },
  "timestamp": 1717500000000
}
```

**Response (503 - 服务未就绪)**:
```json
{
  "code": 503,
  "message": "LLM服务未就绪",
  "data": null,
  "timestamp": 1717500000000
}
```

### POST /api/agent/analyze/stream (SSE)

**SSE Event Stream**:
```
id: 1
event: agent_started
data: {"agentName":"retriever","agentType":"retriever","stepIndex":0}

id: 2
event: agent_completed
data: {"agentName":"retriever","durationMs":1200,"stepIndex":0}

...

id: 10
event: analysis_completed
data: {"analysisId":"anl_test_001","status":"completed","report":"...","degraded":false}
```

### GET /health (critical_ok 规则)

**Response (200 - 全健康)**:
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
  "timestamp": 1717500000000
}
```

**Response (503 - 降级)**:
```json
{
  "code": 503,
  "message": "DEGRADED",
  "data": {
    "llm": "not_loaded",
    "embedding": "loaded_api",
    "chroma": "connected",
    "prompts": "loaded",
    "searchService": "ready",
    "reranker": "ready",
    "status": "DEGRADED"
  },
  "timestamp": 1717500000000
}
```

### GET /api/model/status (扩展字段)

**Response (200)**:
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
    "activeLlmProvider": "builtin",
    "providerCandidates": ["builtin", "api", "local"],
    "chromaPaperCount": 12,
    "gpuMemoryUsed": null,
    "llmProviderCount": 3,
    "searchService": "ready",
    "reranker": "not_initialized"
  },
  "timestamp": 1717500000000
}
```

## 测试结果

| 测试套件 | 用例数 | 通过 | 失败 |
|----------|--------|------|------|
| test_request_validation_response.py (task24) | 25 | 25 | 0 |
| test_agent_endpoint.py (回归) | 10 | 10 | 0 |
| test_sse_basic_push.py (task25) | 15 | 15 | 0 |
| test_health_model_status.py (task26) | 12 | 12 | 0 |
| test_field_mapping_consistency.py (task28) | 51 | 51 | 0 |
| test_degradation.py (task29) | 8 | 8 | 0 |
| test_sse_stability.py + test_sse_reconnect_frontend.py (task30) | 16 | 16 | 0 |
| test_integration_am3.py (task31) | 39 | 39 | 0 |
| test_perf_baseline.py (性能基线) | 5 | 5 | 0 |
| **AM3 合计** | **181** | **181** | **0** |
| 全项目回归 (排除 test_import_papers.py) | 536 | 519 | 17* |

> \* 17 个失败均为已有环境问题（缺少 DASHSCOPE_API_KEY / 模型文件未下载 / test_integration.py 旧格式）

### AM3 12 项检查点验证

| # | 检查点 | 结果 |
|---|--------|------|
| 1 | 统一响应格式 {code,message,data,timestamp} | PASS |
| 2 | 4 枚举 StrEnum 严格校验 | PASS |
| 3 | 422 中文友好消息 | PASS |
| 4 | SSE 7 种事件类型完整 | PASS |
| 5 | Agent 异常不中断 SSE 流 | PASS |
| 6 | /health critical_ok 规则 | PASS |
| 7 | /api/model/status 扩展字段 | PASS |
| 8 | Java camelCase 请求解析 | PASS |
| 9 | 20+ 字段 camelCase alias 一致 | PASS |
| 10 | LLM 3 路降级 | PASS |
| 11 | 错误码 422/503/408/500 | PASS |
| 12 | SSE 稳定性 (ping/重连/并发/优雅关闭) | PASS |

## 相关文件

### 代码变更
- [app/utils/response.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/app/utils/response.py)
- [app/models/enums.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/app/models/enums.py)
- [app/models/schemas.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/app/models/schemas.py)
- [app/exception.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/app/exception.py)
- [app/main.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/app/main.py)
- [app/api/endpoints/agent.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/app/api/endpoints/agent.py)
- [app/api/endpoints/search.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/app/api/endpoints/search.py)
- [app/api/endpoints/model.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/app/api/endpoints/model.py)
- [app/agents/orchestrator.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/app/agents/orchestrator.py)

### 测试文件 (新增)
- [tests/test_request_validation_response.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/tests/test_request_validation_response.py)
- [tests/test_sse_basic_push.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/tests/test_sse_basic_push.py)
- [tests/test_health_model_status.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/tests/test_health_model_status.py)
- [tests/test_field_mapping_consistency.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/tests/test_field_mapping_consistency.py)
- [tests/test_degradation.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/tests/test_degradation.py)
- [tests/test_sse_stability.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/tests/test_sse_stability.py)
- [tests/test_sse_reconnect_frontend.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/tests/test_sse_reconnect_frontend.py)
- [tests/integration/test_java_calls_python.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/tests/integration/test_java_calls_python.py)
- [tests/test_integration_am3.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/tests/test_integration_am3.py)
- [tests/performance/test_perf_baseline.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/tests/performance/test_perf_baseline.py)

### 文档
- [docs/FIELD_MAPPING.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/docs/FIELD_MAPPING.md) — 字段映射文档
- [docs/DEGRADATION_TEST_REPORT.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/docs/DEGRADATION_TEST_REPORT.md) — 降级测试报告
- [docs/AM3_TEST_REPORT.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/docs/AM3_TEST_REPORT.md) — 测试报告
- [docs/AM3_BUGFIX_LOG.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/docs/AM3_BUGFIX_LOG.md) — Bug 修复日志
