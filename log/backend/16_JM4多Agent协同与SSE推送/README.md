# JM4 多Agent协同与SSE推送

## 功能描述

- **解决了什么问题**：后端此前仅实现了论文分析（task22/23），缺乏对比分析、综述生成、Agent状态SSE推送、三级降级机制、心跳/超时保护等能力。JM4里程碑的目标是补齐多Agent协同场景的全链路支撑。

- **实现了什么功能**：
  1. **重构消除自注入反模式** — 提取 `AnalysisTransactionService`，删除 `@Autowired @Lazy self`
  2. **对比分析API** — POST /api/analysis/compare，编排2-5篇论文对比分析
  3. **综述生成API** — POST /api/analysis/report，编排1-20篇论文综述生成
  4. **SSE事件格式标准化** — 7种事件类型data字段统一为结构化JSON
  5. **SSE心跳机制** — 每30s注入ping事件保活
  6. **SSE超时处理** — 120s无数据事件自动关闭
  7. **Last-Event-ID断线重连** — 透传到Python端续传
  8. **降级机制完善** — COMPARE/REPORT类型降级+SSE流降级
  9. **CORS扩展** — allowedHeaders增加Last-Event-ID
  10. **WebClient超时调整** — sseWebClient 150s→120s对齐JM4检查点

- **业务价值**：前端可实时观察6个Agent执行状态、AI服务不可用时优雅降级、支持对比/综述两种分析类型。

## 实现逻辑

- **设计模式**：Service编排层 → TransactionService事务层 → Repository数据层，消除自注入反模式
- **7步编排**（analyzePaper/comparePapers/generateReport共用）：
  1. buildUserProfile → 2. 验证paperIds → 3. resolveOrCreateSession → 4. generateAnalysisId → 5. savePending(事务) → 6. callAI(事务外) → 7. completeAnalysis(事务)
- **SSE流链路**：AgentController → AgentClientService.generateReportStreamWithHeartbeat → PythonAIClient.analyzeStream → Python SSE → byte[]流手动解析 → AgentSseEvent → writeAgentStateToRedis → 前端EventSource
- **三级降级**：Python正常 → Redis缓存回退 → 降级DTO（COMPARE/REPORT/PAPER_ANALYSIS各自不同的降级内容）
- **408超时转换**：Python端event=error+data.type=timeout → 转为AgentSseEvent(event=error, data={type:timeout, message:Agent执行超时})

## 接口变更

### POST /api/analysis/compare（新增）

Request:
```json
{
  "topic": "对比多Agent框架",
  "paper_ids": ["arxiv_2024_001", "arxiv_2024_002"],
  "session_id": "ses_xxx"
}
```

Response (202 Accepted):
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "analysis_id": "anl_abc123",
    "status": "completed",
    "message": "分析完成",
    "created_at": "2026-06-08T12:00:00"
  },
  "timestamp": 1716451200000
}
```

### POST /api/analysis/report（新增）

Request:
```json
{
  "topic": "LLM综述",
  "paper_ids": ["arxiv_2024_001", "arxiv_2024_002", "arxiv_2024_003"],
  "session_id": "ses_xxx"
}
```

Response: 同compare，202 Accepted + AnalysisTaskResponse

### GET /api/analysis/{id}/agent-stream（变更）

- 原路径不变，实现从AnalysisController迁至AgentController
- 新增30s ping心跳 + 120s超时保护
- 7种事件data格式标准化（timestamp=ISO8601）
- CORS支持Last-Event-ID Header

## 测试结果

- **测试总数**：200+（175+现有 + 44新增）
- **测试场景**：
  - AnalysisTransactionService savePending/completeAnalysis 事务行为：通过
  - comparePapers 正常流程/paperId不存在/session隔离/AgentRequest校验：通过
  - generateReport 正常流程/citations空/paperId不存在/session复用：通过
  - CompareRequest/ReportRequest Bean Validation边界值：通过
  - PythonAIClient SSE扩展（analyzeStream/compareStream/reportStream/408转换/Last-Event-ID透传）：13/13通过
  - AgentClientService 降级（COMPARE/REPORT/PAPER_ANALYSIS）/SSE流降级/cache回退：7/7通过
  - SSE事件格式标准化 7种事件data字段：11/11通过
  - SSE心跳/超时/CORS/WebClient超时：5/5通过
- **是否通过**：是（`mvn test` BUILD SUCCESS，0失败）

## 相关文件

### 新增文件（10个）
- `service/AnalysisTransactionService.java` — 事务服务
- `dto/request/CompareRequest.java` — 对比分析请求DTO
- `dto/request/ReportRequest.java` — 综述生成请求DTO
- `controller/AgentController.java` — Agent SSE控制器
- `service/AnalysisTransactionServiceTest.java` — 事务服务测试（6）
- `dto/request/CompareRequestValidationTest.java` — 校验测试（8）
- `service/AnalysisServiceReportTest.java` — 综述生成测试（6）
- `sse/SseEventFormatTest.java` — 事件格式测试（11）
- `sse/SseHeartbeatTimeoutTest.java` — 心跳超时测试（5）

### 修改文件（10个）
- `service/AnalysisService.java` — 消除self注入，新增comparePapers/generateReport
- `service/AgentClientService.java` — 删除Mono占位，新增心跳/降级/compareStream/reportStream
- `client/PythonAIClient.java` — 提取streamSse公共方法，新增compareStream/reportStream，408转换，byte[] SSE解析
- `dto/response/AnalysisResultDTO.java` — 新增compareDegraded/reportDegraded静态工厂
- `controller/AnalysisController.java` — 新增POST /compare、POST /report，移除agentStream
- `config/WebClientConfig.java` — sseWebClient超时150s→120s
- `config/SecurityConfig.java` — CORS allowedHeaders增加Last-Event-ID
- `service/AnalysisServiceTest.java` — Mock替代self反射，新增comparePapers测试
- `service/AnalysisServiceQueryTest.java` — 移除self反射调用
- `client/PythonAIClientTest.java` — SSE扩展测试（7→13）
- `service/AgentClientServiceTest.java` — 适配Mono删除
