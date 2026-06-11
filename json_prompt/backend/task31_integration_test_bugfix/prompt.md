# task31: 集成测试 + Bug修复 (JM4 Week 7-8 Day 6-7)

> **里程碑**：M4 多Agent协同 / **JM4 Day 6-7**：集成测试 + Bug修复
> **版本**：v0.4
> **优先级**：P0
> **功能编号**：F2.4.6, F2.4.7, F2.5.6, F2.5.7

---

## 任务概述

编写 JM4 完整集成测试，覆盖 **对比分析**、**综述生成**、**SSE 推送**、**降级机制** 的端到端场景，修复测试中发现的 Bug。

| 测试类 | 覆盖场景 | 测试数量 |
|--------|----------|----------|
| `AnalysisServiceIntegrationTest` | 对比分析/综述生成/降级/数据隔离 | 5+ |
| `SseIntegrationTest` | 事件顺序/断线重连/心跳/超时/降级 | 5+ |
| `AgentControllerIntegrationTest` | 状态查询/健康检查/数据隔离 | 3+ |

---

## 上下文定位

| 涉及层级 | 模块 |
|----------|------|
| java_backend | `AnalysisService`（被测：analyzePaper/comparePapers/generateReport） |
| java_backend | `AgentClientService`（被测：降级/SSE流） |
| java_backend | `AnalysisController`（被测：REST + SSE 端点） |
| test | 3 个新建集成测试类 |

**已有可复用**：
- `PythonAIClientTest` — MockWebServer 使用模式参考
- `AgentClientServiceTest` — 单元测试 Mock 模式参考
- `AnalysisServiceTest` — 316 行单元测试参考

---

## 涉及文件

| 操作 | 路径 | 说明 |
|------|------|------|
| 新建 | `test/integration/AnalysisServiceIntegrationTest.java` | 对比分析/综述生成/降级/数据隔离端到端 |
| 新建 | `test/integration/SseIntegrationTest.java` | SSE 事件顺序/断线重连/心跳/超时/降级 |
| 新建 | `test/integration/AgentControllerIntegrationTest.java` | Agent 状态查询/健康检查/数据隔离 |
| 修改 | 根据测试发现动态确定 | Bug 修复 |

---

## 测试基础设施

### MockWebServer 配置

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
@TestInstance(Lifecycle.PER_CLASS)
class AnalysisServiceIntegrationTest {

    @LocalServerPort
    private int port;

    @Autowired
    private TestRestTemplate restTemplate;

    private MockWebServer mockWebServer;

    @BeforeAll
    void setUp() throws IOException {
        mockWebServer = new MockWebServer();
        mockWebServer.start(PYTHON_PORT);  // 与 application-test.yml 中配置一致
    }

    @AfterAll
    void tearDown() throws IOException {
        mockWebServer.shutdown();
    }

    @AfterEach
    void resetServer() {
        mockWebServer.removeAll();
    }
}
```

### SSE 测试配置

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class SseIntegrationTest {

    @Autowired
    private WebTestClient webTestClient;

    private MockWebServer mockWebServer;

    // SSE 事件模拟
    private String buildSseEvent(String event, Map<String, Object> data, long id) {
        return "id: " + id + "\nevent: " + event + "\ndata: " + 
               objectMapper.writeValueAsString(data) + "\n\n";
    }
}
```

---

## 关键测试场景

### 1. 对比分析端到端 (FR-031-01)

```java
@Test
@DisplayName("对比分析端到端：POST /compare → GET /status → GET /{id}")
void compareAnalysis_e2e() {
    // 1) MockWebServer 模拟 Python 正常响应
    AnalysisResultDTO pythonResponse = AnalysisResultDTO.builder()
            .analysisId("anl_compare_001")
            .status(AnalysisStatus.COMPLETED)
            .report("## 对比分析报告\n\n### 方法对比\n...")
            .citations(List.of(Map.of("index", 1, "paperId", "p1", "citation", "Wang et al.")))
            .build();
    mockWebServer.enqueue(new MockResponse()
            .setHeader("Content-Type", "application/json")
            .setBody(objectMapper.writeValueAsString(pythonResponse)));

    // 2) POST /api/analysis/compare
    ResponseEntity<ApiResponse> createResp = restTemplate
            .withBasicAuth("userA", "password")
            .postForEntity("/api/analysis/compare", compareRequest, ApiResponse.class);
    assertThat(createResp.getStatusCode()).isEqualTo(HttpStatus.ACCEPTED);
    String analysisId = extractAnalysisId(createResp);

    // 3) GET /api/analysis/{id}/status
    ResponseEntity<ApiResponse> statusResp = restTemplate
            .withBasicAuth("userA", "password")
            .getForEntity("/api/analysis/" + analysisId + "/status", ApiResponse.class);
    assertThat(statusResp.getStatusCode()).isEqualTo(HttpStatus.OK);

    // 4) GET /api/analysis/{id}
    ResponseEntity<ApiResponse> resultResp = restTemplate
            .withBasicAuth("userA", "password")
            .getForEntity("/api/analysis/" + analysisId, ApiResponse.class);
    assertThat(resultResp.getStatusCode()).isEqualTo(HttpStatus.OK);
    // 验证对比结果含 citations
    assertThat(extractResult(resultResp).getCitations()).isNotEmpty();
}
```

### 2. SSE 事件顺序 (FR-031-03)

```java
@Test
@DisplayName("SSE 事件顺序：agent_started → agent_state_update → agent_completed → analysis_completed")
void sseEventOrder() {
    // MockWebServer 模拟 SSE 流
    mockWebServer.enqueue(new MockResponse()
            .setHeader("Content-Type", "text/event-stream")
            .setBody(buildSseEvent("agent_started", Map.of("agentName", "retriever"), 1) +
                     buildSseEvent("agent_state_update", Map.of("agentName", "retriever", "progress", 0.5), 2) +
                     buildSseEvent("agent_completed", Map.of("agentName", "retriever"), 3) +
                     buildSseEvent("analysis_completed", Map.of("status", "completed"), 4)));

    // WebTestClient 订阅 SSE 流
    List<ServerSentEvent<Object>> events = webTestClient.get()
            .uri("/api/analysis/{id}/agent-stream", analysisId)
            .header("Authorization", "Bearer " + token)
            .accept(MediaType.TEXT_EVENT_STREAM)
            .exchange()
            .expectStatus().isOk()
            .returnResult(new ParameterizedTypeReference<ServerSentEvent<Object>>() {})
            .getResponseBody()
            .collectList()
            .block(Duration.ofSeconds(10));

    // 验证事件顺序
    assertThat(events).hasSizeGreaterThanOrEqualTo(4);
    assertThat(events.get(0).event()).isEqualTo("agent_started");
    assertThat(events.get(1).event()).isEqualTo("agent_state_update");
    assertThat(events.get(2).event()).isEqualTo("agent_completed");
    assertThat(events.get(3).event()).isEqualTo("analysis_completed");
}
```

### 3. 降级端到端 (FR-031-04)

```java
@Test
@DisplayName("降级端到端：Python 502 → 降级响应 → degraded=true")
void degradation_compare_e2e() {
    // MockWebServer 模拟 Python 502
    mockWebServer.enqueue(new MockResponse().setResponseCode(502));

    // POST /api/analysis/compare
    ResponseEntity<ApiResponse> resp = restTemplate
            .withBasicAuth("userA", "password")
            .postForEntity("/api/analysis/compare", compareRequest, ApiResponse.class);
    assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.ACCEPTED);

    // GET /api/analysis/{id} 验证降级
    String analysisId = extractAnalysisId(resp);
    ResponseEntity<ApiResponse> resultResp = restTemplate
            .withBasicAuth("userA", "password")
            .getForEntity("/api/analysis/" + analysisId, ApiResponse.class);
    // 验证 degraded=true
    assertThat(extractResult(resultResp).getDegraded()).isTrue();
    assertThat(extractResult(resultResp).getDegradedReason()).isNotBlank();
}
```

### 4. 数据隔离 (FR-031-05)

```java
@Test
@DisplayName("数据隔离：用户 B 不能访问用户 A 的分析结果 → 403")
void dataIsolation_differentUsers() {
    // 用户 A 创建分析
    ResponseEntity<ApiResponse> createResp = restTemplate
            .withBasicAuth("userA", "password")
            .postForEntity("/api/analysis/paper", request, ApiResponse.class);
    String analysisId = extractAnalysisId(createResp);

    // 用户 B 尝试访问
    ResponseEntity<ApiResponse> accessResp = restTemplate
            .withBasicAuth("userB", "password")
            .getForEntity("/api/analysis/" + analysisId, ApiResponse.class);
    assertThat(accessResp.getStatusCode()).isEqualTo(HttpStatus.FORBIDDEN);
}
```

### 5. SSE 降级 (FR-031-09)

```java
@Test
@DisplayName("SSE 降级：Python 不可用 → 降级事件序列")
void sseDegradation() {
    // MockWebServer shutdown 模拟 Python 不可用
    mockWebServer.shutdown();

    List<ServerSentEvent<Object>> events = webTestClient.get()
            .uri("/api/analysis/{id}/agent-stream", analysisId)
            .header("Authorization", "Bearer " + token)
            .accept(MediaType.TEXT_EVENT_STREAM)
            .exchange()
            .expectStatus().isOk()
            .returnResult(new ParameterizedTypeReference<ServerSentEvent<Object>>() {})
            .getResponseBody()
            .collectList()
            .block(Duration.ofSeconds(10));

    // 验证降级事件序列
    assertThat(events).hasSizeGreaterThanOrEqualTo(2);
    assertThat(events.get(0).event()).isEqualTo("error");
    assertThat(events.get(1).event()).isEqualTo("analysis_completed");
}
```

---

## JM4 验收检查点

- [ ] 对比分析: POST /api/analysis/compare 返回对比结果
- [ ] 综述生成: POST /api/analysis/report 返回 analysisId
- [ ] SSE推送: Agent 执行过程中前端实时收到状态更新
- [ ] SSE事件格式: event:agent_state_update + data:JSON
- [ ] Agent状态缓存: Redis 中 agent:state:{id} 正确更新
- [ ] 分析编排: 画像→论文→会话→AI调用→结果保存 完整流程
- [ ] 降级: Python 不可用时返回缓存或降级提示，不崩溃
- [ ] 个性化: 请求中包含用户画像信息
- [ ] 引用标注: 综述结果中包含 citations 数组
- [ ] 超时处理: SSE 流 120s 超时后正常关闭

---

## 禁止行为

- ❌ 集成测试中 Mock AgentClientService（必须通过 MockWebServer 模拟 Python）
- ❌ 集成测试依赖外部 Python 服务运行
- ❌ 修改生产代码以通过测试（Bug 修复除外）
- ❌ 测试间共享可变状态
- ❌ SSE 超时测试实际等待 120s（必须使用短超时配置）
- ❌ 跳过失败的集成测试（@Disabled）而不修复 Bug

---

## 测试要求

| 测试名 | 覆盖 |
|--------|------|
| `compareAnalysis_e2e` | 对比分析端到端 |
| `reportGeneration_e2e` | 综述生成端到端 |
| `degradation_compare_e2e` | 对比分析降级 |
| `degradation_report_e2e` | 综述生成降级 |
| `sseEventOrder` | SSE 事件顺序 |
| `sseLastEventId_reconnect` | SSE 断线重连 |
| `sseDegradation` | SSE 流降级 |
| `sseTimeout_handling` | SSE 超时处理 |
| `dataIsolation_differentUsers` | 数据隔离 |
| `agentStream_dataIsolation` | SSE 数据隔离 |
| `healthCheck_withAIService` | 健康检查 |
| `personalization_in_request` | 个性化验证 |

**验证命令**：
```bash
# 集成测试
cd Veritas/backend && mvn -Dtest='*IntegrationTest' test

# 全量测试
cd Veritas/backend && mvn test
# 期望: 272+ 现有测试 + 12+ 集成测试全部通过
```

---

## 验收标准

- [ ] 对比分析: POST /api/analysis/compare 返回对比结果
- [ ] 综述生成: POST /api/analysis/report 返回 analysisId
- [ ] SSE推送: Agent 执行过程中前端实时收到状态更新
- [ ] SSE事件格式: event:agent_state_update + data:JSON
- [ ] Agent状态缓存: Redis 中 agent:state:{id} 正确更新
- [ ] 分析编排: 画像→论文→会话→AI调用→结果保存 完整流程
- [ ] 降级: Python 不可用时返回缓存或降级提示，不崩溃
- [ ] 个性化: 请求中包含用户画像信息
- [ ] 引用标注: 综述结果中包含 citations 数组
- [ ] 超时处理: SSE 流 120s 超时后正常关闭
- [ ] 数据隔离: 用户 A 不能访问用户 B 的分析结果
- [ ] 272+ 现有测试 + 12+ 集成测试全部通过

---

## 下一步（JM4 验收 → JM5 启动）

### JM4 验收清单（本任务完成后）
- ☑ 对比分析 API 端到端通过
- ☑ 综述生成 API 端到端通过
- ☑ SSE 推送端到端通过
- ☑ 降级机制端到端通过
- ☑ 数据隔离验证通过
- ☑ 全量测试通过

### JM5 启动准备
- **JM5 Day 1-2**: 前端 SSE 对接（EventSource + 状态展示）
- **JM5 Day 3-4**: 缓存优化（Redis key 前缀区分 + TTL 策略调优）
- **JM5 Day 5-7**: 性能优化（Resilience4j 熔断器 + 连接池调优）

---

## 未来建议 / 补充

1. **建议引入 Testcontainers**：当前集成测试依赖本机 MySQL/Redis；JM5 可引入 Testcontainers 实现完全自包含的集成测试环境
2. **建议增加契约测试**：Python AI 服务接口变更时 Java 端无感知；JM5 可引入 Pact 契约测试确保跨系统接口一致性
3. **建议 SSE 测试增加并发场景**：多用户同时订阅不同 analysisId 的 SSE 流，验证资源隔离和性能
4. **建议集成测试增加性能基线**：记录关键路径（对比分析/综述生成）的响应时间基线，JM6 性能优化时对比
5. **建议 Bug 修复记录 ADR**：集成测试发现的 Bug 可能涉及架构决策，建议记录 ADR 避免同类问题复发
