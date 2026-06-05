# task19: PythonAIClient 同步调用封装 (JM3 Day 5)

> **里程碑**：M3：前后端联调成功 / **JM3 Day 5**：AI 服务调用打通
> **版本**：v0.3
> **优先级**：P0
> **功能编号**：F2.5.1, F2.5.2, F2.5.3, F2.5.5

---

## 任务概述

实现 `PythonAIClient`（位于 `com.literatureassistant.client` 包），基于 Spring `WebClient` 封装 Java→Python AI 服务的 HTTP 同步调用能力。提供 4 个核心方法：

| 方法 | 端点 | 用途 |
|------|------|------|
| `analyze(AgentRequest)` | `POST /api/agent/analyze` | 论文分析 / 对比分析 / 综述生成 |
| `search(query, topK, filters)` | `POST /api/search/` | 语义检索 |
| `isHealthy()` | `GET /health` | 健康检查（5s 超时） |
| `getModelStatus()` | `GET /api/model/status` | LLM/Embedding/Chroma 状态查询 |

**关键能力**：超时 30s + 重试 1 次（间隔 3s） + 异常统一转换为 `AIServiceException(503)`。

---

## 上下文定位

| 涉及层级 | 模块 |
|----------|------|
| java_backend | `com.literatureassistant.client`（新增）、`com.literatureassistant.config.WebClientConfig`（已存在）、`com.literatureassistant.exception.AIServiceException`（已存在） |
| python_ai_service | `app.api.endpoints.{agent,search,model}` + `app.main`（已实现） |

**已有可复用**：
- `WebClientConfig.webClient()` — Bean 已注入（连接池 50 / 30s 超时 / 16MB buffer / baseUrl 来自 `${ai-service.url}`）
- `AIServiceException` — 503 + message + cause + errorKey=`AI_SERVICE_ERROR`
- `GlobalExceptionHandler.handleAIService` — 统一返回 `ApiResponse.error(503, "AI服务暂时不可用，请稍后重试")`

---

## 涉及文件

| 操作 | 路径 | 说明 |
|------|------|------|
| 新增 | `Veritas/backend/src/main/java/com/literatureassistant/client/PythonAIClient.java` | 主类 |
| 新增 | `Veritas/backend/src/main/java/com/literatureassistant/dto/common/AgentRequest.java` | 占位 DTO（task20 完善注解） |
| 新增 | `Veritas/backend/src/main/java/com/literatureassistant/dto/response/AnalysisResultDTO.java` | 占位 DTO（task20 完善注解） |
| 新增 | `Veritas/backend/src/test/java/com/literatureassistant/client/PythonAIClientTest.java` | 7 个单元测试 |

---

## API 契约（Java ↔ Python）

| 字段 | Java (camelCase) | Python/JSON (snake_case via Jackson) |
|------|------------------|--------------------------------------|
| 论文ID列表 | `paperIds: List<String>` | `paperIds` (JSON) → `paper_ids` (Python attr) |
| 用户ID | `userId: String` | `userId` → `user_id` |
| 用户画像 | `userProfile: UserProfile` | `userProfile` → `user_profile` |
| 分析类型 | `analysisType: String` | `analysisType` → `analysis_type` |
| 分析ID | `analysisId: String` | `analysisId` → `analysis_id` |
| 检索TopK | `topK: Integer` | `topK` → `top_k` |
| Embedding维度 | `embeddingDimension: Integer` | `embeddingDimension` → `embedding_dimension` |
| 活跃LLM | `activeLlmProvider: String` | `activeLlmProvider` → `active_llm_provider` |

> 依赖 `application.yml` 全局 `spring.jackson.property-naming-strategy: SNAKE_CASE`，**禁止**在 DTO 字段上加 `@JsonProperty` 覆盖。

---

## 实现要点

1. **依赖注入**：`@Component` + 构造器注入 `WebClient webClient`（来自 `WebClientConfig`）。
2. **重试机制**：使用 `Mono.retryWhen(Retry.backoff(1, Duration.ofSeconds(3)).filter(this::isRetryable))`；仅在 `WebClientResponseException` 5xx / `TimeoutException` / `ConnectException` 时重试，4xx 不重试。
3. **异常转换**：所有异常统一包装为 `AIServiceException(503, "AI service call failed: <method>", cause, "AI_SERVICE_ERROR")`。
4. **超时**：`analyze` / `search` / `getModelStatus` 复用 WebClient 30s；`isHealthy` 用 `.block(Duration.ofSeconds(5))`。
5. **日志**：`log.info("AI service analyze: analysisId={}, durationMs={}", id, ms)`，禁止打印 AgentRequest 完整 body。
6. **方法签名**：
   ```java
   public AnalysisResultDTO analyze(AgentRequest request);
   public List<PaperSearchResultDTO> search(String query, int topK, Map<String,Object> filters);
   public boolean isHealthy();
   public ModelStatusDTO getModelStatus();
   ```

---

## 禁止行为

- ❌ 硬编码 `ai-service.url`（必须 `@Value("${ai-service.url}")`）
- ❌ 在 PythonAIClient 内吞掉异常（必须上抛）
- ❌ 把 Python 端原始错误信息原样返回给前端
- ❌ 使用 RestTemplate/HttpClient（必须 WebClient，为 task29 SSE 扩展铺路）
- ❌ 在 4xx 错误时重试
- ❌ 在 DTO 字段加 `@JsonProperty` 覆盖全局配置

---

## 测试要求

| 测试名 | 覆盖场景 |
|--------|---------|
| `analyze_normal_returnsDTO` | 正常 200 返回 |
| `analyze_timeout_triggers_retry` | 第一次超时、第二次成功 |
| `analyze_5xx_raises_AIServiceException` | 两次 5xx 后抛 AIServiceException(503) |
| `analyze_4xx_no_retry` | 400 不重试 |
| `isHealthy_returns_true_on_200` | 健康检查成功 |
| `isHealthy_returns_false_on_timeout` | 5s 超时不抛异常 |
| `search_passes_topK_and_filters` | 检索参数正确传递 |

**验证命令**：
```bash
cd Veritas/backend && mvn -Dtest=PythonAIClientTest test
```

---

## 验收标准

- [ ] `PythonAIClient.java` 编译通过，含 4 个 public 方法
- [ ] `analyze` 失败时抛 `AIServiceException(503)`
- [ ] `analyze` 仅在 5xx/超时/连接错误时重试 1 次
- [ ] `isHealthy()` 5s 超时，不抛异常
- [ ] 字段命名遵循 Java camelCase
- [ ] `PythonAIClientTest` 7/7 通过
- [ ] 未修改 WebClientConfig / 已有 Service / Controller

---

## 下一步

- **task20**：完善 `AgentRequest` / `AnalysisResultDTO` / `AgentStateResponse` 三个 DTO 的 `@JsonProperty` 注解与字段约束
- **task21**：基于本 task 的 `PythonAIClient` 构建 `AgentClientService` 编排层（降级处理 + 缓存回退）
- **task23**：在 `HealthController` 集成 `pythonAIClient.isHealthy()`
