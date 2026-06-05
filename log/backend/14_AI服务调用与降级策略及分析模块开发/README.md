# AI服务调用与降级策略及分析模块开发

> **任务编号**：task19 ~ task23  
> **里程碑**：JM3（AI服务调用打通）  
> **日期**：2026-06-04  
> **测试结果**：269/269 全通过，BUILD SUCCESS

---

## 功能描述

- **解决了什么问题**：打通 Java 后端到 Python AI 服务的全链路调用，实现三级降级策略保证系统可用性，建立完整的分析任务编排（创建→执行→查询→状态跟踪）。
- **实现了什么功能**：
  - `PythonAIClient`：基于 Spring WebClient 封装 Java→Python 全部 HTTP 调用（analyze/search/isHealthy/getModelStatus），含30s超时+1次重试
  - AI DTO 体系：`AgentRequest`/`AnalysisResultDTO`/`AgentStateResponse`/`UserProfileDTO`/`ModelStatusDTO`/`PaperSearchResultDTO`
  - `AgentClientService`：编排层，三级降级（Python正常→Redis缓存回退→降级提示DTO），维护 Agent 状态 Redis Hash
  - `AnalysisService`：完整7步编排（画像→论文→Session→生成analysisId→PENDING→调AI→更新结果），含事务边界控制
  - `AnalysisController`：POST `/api/analysis/paper` + GET `/{id}` + GET `/{id}/status`
  - `HealthController` 扩展：新增 `aiService` 字段
- **业务价值**：后端具备完整的三层架构AI调用能力，前端可通过REST API提交分析任务、轮询状态、获取结果。

---

## 实现逻辑

### 核心文件列表

| 操作 | 文件 | 说明 |
|------|------|------|
| 新建 | `client/PythonAIClient.java` | WebClient封装，analyze/search/isHealthy/getModelStatus |
| 新建 | `dto/common/AgentRequest.java` | Java→Python请求体（6字段） |
| 新建 | `dto/common/UserProfileDTO.java` | 用户画像DTO（4维度） |
| 新建 | `dto/response/AnalysisResultDTO.java` | Python→Java响应体（7字段+degraded工厂） |
| 新建 | `dto/response/AgentStateResponse.java` | 单Agent状态DTO |
| 新建 | `dto/response/ModelStatusDTO.java` | LLM模型状态DTO |
| 新建 | `dto/response/PaperSearchResultDTO.java` | 搜索结果项DTO |
| 新建 | `service/AgentClientService.java` | 编排层：降级+缓存+Agent状态维护 |
| 新建 | `service/AnalysisService.java` | 分析编排层：7步工作流+事务控制 |
| 新建 | `controller/AnalysisController.java` | 3个端点（POST+2×GET） |
| 新建 | `dto/request/PaperAnalysisRequest.java` | 论文分析请求（3字段） |
| 新建 | `dto/response/AnalysisTaskResponse.java` | 任务创建响应（4字段） |
| 新建 | `dto/response/AnalysisResponse.java` | 结果查询响应（6字段+嵌套result） |
| 新建 | `dto/response/AnalysisStatusResponse.java` | 状态查询响应（5字段） |
| 修改 | `controller/HealthController.java` | 新增 AgentClientService 注入 + aiService 字段 |
| 修改 | `enums/AnalysisStatus.java` | 添加 @JsonValue 保证小写序列化 |
| 修改 | `enums/AnalysisType.java` | 添加 @JsonValue 保证 snake_case 序列化 |

### 关键设计模式

1. **分层架构**：Controller → Service → Client，禁止跨层调用
2. **三级降级策略**：Python正常→Redis缓存回退→degraded DTO，无缝切换
3. **事务边界控制**：@Transactional 仅覆盖DB写入，AI调用在事务外执行（避免30s长事务）
4. **Cache-Aside缓存**：@Cacheable 30min TTL + 主动失效
5. **自注入模式**：`@Lazy @Autowired self` 使Spring事务代理对内部调用生效

---

## 接口变更

### POST /api/analysis/paper
```json
// Request
{
  "topic": "Multi-Agent协同决策",
  "paper_id": "arxiv_2024_001",
  "session_id": "ses_a1b2c3d4"
}

// Response (202 Accepted)
{
  "code": 200,
  "message": "success",
  "data": {
    "analysis_id": "anl_abcdef012345",
    "status": "completed",
    "message": "分析完成"
  }
}
```

### GET /api/analysis/{analysisId}
```json
// Response
{
  "code": 200,
  "data": {
    "analysis_id": "anl_abcdef012345",
    "session_id": "ses_a1b2c3d4",
    "status": "completed",
    "type": "paper_analysis",
    "result": {
      "analysis_id": "anl_abcdef012345",
      "status": "completed",
      "report": "## 分析报告\n...",
      "citations": [{"index": 1, "paper_id": "...", "citation": "..."}],
      "agent_states": [{"agent_name": "retriever", "status": "completed", "progress": 1.0}],
      "degraded": false
    },
    "created_at": "2026-06-01T10:00:00"
  }
}
```

### GET /api/analysis/{analysisId}/status
```json
// Response
{
  "code": 200,
  "data": {
    "analysis_id": "anl_abcdef012345",
    "status": "processing",
    "progress": 0.5,
    "current_agent": "analyzer",
    "agent_states": [
      {"agent_name": "retriever", "status": "completed", "progress": 1.0, "duration_ms": 2300},
      {"agent_name": "analyzer", "status": "running", "progress": 0.5, "duration_ms": null},
      {"agent_name": "generator", "status": "waiting", "progress": 0.0, "duration_ms": null}
    ]
  }
}
```

### GET /health（扩展）
```json
// Response
{
  "code": 200,
  "data": {
    "status": "UP",
    "mysql": "UP",
    "redis": "UP",
    "aiService": "UP"
  }
}
```

---

## 测试结果

| 测试类 | 用例数 | 结果 |
|--------|--------|------|
| PythonAIClientTest | 7 | 通过 |
| AiDtoSerializationTest | 6 | 通过 |
| AgentClientServiceTest | 7 | 通过 |
| AnalysisServiceTest | 6 | 通过 |
| AnalysisServiceQueryTest | 5 | 通过 |
| AnalysisControllerTest | 5 | 通过 |
| HealthControllerTest | 5 | 通过 |
| **全量回归（mvn test）** | **269** | **全通过** |

---

## 相关文件

### 新增文件（17个）
- `client/PythonAIClient.java`
- `dto/common/AgentRequest.java`
- `dto/common/UserProfileDTO.java`
- `dto/response/AnalysisResultDTO.java`
- `dto/response/AgentStateResponse.java`
- `dto/response/ModelStatusDTO.java`
- `dto/response/PaperSearchResultDTO.java`
- `dto/response/AnalysisResponse.java`
- `dto/response/AnalysisStatusResponse.java`
- `dto/response/AnalysisTaskResponse.java`
- `dto/request/PaperAnalysisRequest.java`
- `service/AgentClientService.java`
- `service/AnalysisService.java`
- `controller/AnalysisController.java`
- `test/client/PythonAIClientTest.java`
- `test/service/AgentClientServiceTest.java`
- `test/service/AnalysisServiceTest.java`
- `test/service/AnalysisServiceQueryTest.java`
- `test/controller/AnalysisControllerTest.java`

### 修改文件（4个）
- `controller/HealthController.java` — 注入 AgentClientService + aiService字段
- `test/controller/HealthControllerTest.java` — 改为单元测试 + 新增2个AI状态测试
- `enums/AnalysisStatus.java` — 添加 @JsonValue
- `enums/AnalysisType.java` — 添加 @JsonValue
- `dto/common/AgentRequest.java` — 移除错误的跨包import
