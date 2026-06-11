# task29: SSE端点完善 + 前端联调支持 (JM4 Day 9-10)

> **里程碑**：M4 多Agent协同 / **JM4 Day 9-10**：SSE 事件格式标准化 + 心跳 + 超时 + CORS
> **版本**：v0.4
> **优先级**：P0
> **功能编号**：F2.4.8, F2.4.9, F2.5.7

---

## 任务概述

完善 SSE 端点的事件格式标准化（7 种事件类型统一 JSON data 格式），添加心跳机制（30s ping）、超时处理（120s 无事件自动关闭）、Last-Event-ID 断线重连、CORS 配置支持 SSE 跨域请求，确保前端可正确解析所有 SSE 事件并完成联调。

| 改动项 | 说明 |
|--------|------|
| SSE 事件格式标准化 | 7 种事件 data 字段统一为结构化 JSON |
| 心跳机制 | 每 30s 发送 ping 事件保持连接 |
| 超时处理 | 120s 无数据事件自动关闭（先发 error 后关闭） |
| Last-Event-ID | 支持断线重连 |
| CORS | SecurityConfig 增加 Last-Event-ID Header |
| WebClientConfig | sseWebClient 超时 150s → 120s |

---

## 上下文定位

| 涉及层级 | 模块 |
|----------|------|
| java_backend | `AgentController`（扩展 SSE 事件格式标准化） |
| java_backend | `AgentClientService`（扩展心跳 + 超时） |
| java_backend | `WebClientConfig`（sseWebClient 超时调整） |
| java_backend | `SecurityConfig`（CORS 增加 Last-Event-ID） |

**已有可复用**：
- `task28 AgentController.agentStream` — SSE 流转发端点
- `task28 AgentClientService.generateReportStream` — Flux<AgentSseEvent>
- `task28 writeAgentStateToRedis` — 7 种事件类型映射
- `AgentSseEvent` — 7 种事件类型定义
- `WebClientConfig.sseWebClient` — 150s 超时（待调整）
- `SecurityConfig.corsConfigurationSource` — CORS 配置（待扩展）

---

## 涉及文件

| 操作 | 路径 | 说明 |
|------|------|------|
| 修改 | `controller/AgentController.java` | SSE 事件格式标准化（toStandardizedSseEvent） |
| 修改 | `service/AgentClientService.java` | 新增 generateReportStreamWithHeartbeat（30s ping + 120s 超时） |
| 修改 | `config/WebClientConfig.java` | sseWebClient 150s → 120s |
| 修改 | `config/SecurityConfig.java` | CORS allowedHeaders + Last-Event-ID |
| 新增 | `test/sse/SseEventFormatTest.java` | 7 种事件格式验证测试 |
| 新增 | `test/sse/SseHeartbeatTimeoutTest.java` | 心跳 + 超时 + 重连测试 |

---

## 关键实现

### 1. SSE 事件格式标准化

```java
/**
 * 将内部 AgentSseEvent 转换为标准化 SSE 事件（统一 data JSON 格式）。
 *
 * 事件格式规范：
 * - agent_started:       {agentName, analysisId, timestamp}
 * - agent_state_update:  {agentName, status, progress, intermediateResult, durationMs}
 * - agent_completed:     {agentName, analysisId, result, timestamp}
 * - agent_failed:        {agentName, error, timestamp}
 * - analysis_completed:  {analysisId, status, report, citations}
 * - error:               {type, message}
 * - ping:                {timestamp}
 */
private ServerSentEvent<Object> toStandardizedSseEvent(AgentSseEvent event) {
    ServerSentEvent.Builder<Object> builder = ServerSentEvent.builder();

    // event id（单调递增，用于 Last-Event-ID 断线重连）
    if (event.getId() != null) {
        builder.id(String.valueOf(event.getId()));
    }

    // event type
    if (event.getEvent() != null) {
        builder.event(event.getEvent());
    }

    // 标准化 data 字段
    Map<String, Object> standardizedData = standardizeEventData(event);
    builder.data(standardizedData);

    // retry: 告知前端断线后 5s 重连
    builder.retry(Duration.ofSeconds(5).toMillis());

    return builder.build();
}

/**
 * 根据事件类型标准化 data 字段。
 */
private Map<String, Object> standardizeEventData(AgentSseEvent event) {
    String eventType = event.getEvent();
    Map<String, Object> rawData = event.getData() != null ? event.getData() : Map.of();
    String now = Instant.now().toString(); // ISO8601

    return switch (eventType) {
        case "agent_started" -> Map.of(
                "agentName", rawData.getOrDefault("agentName", ""),
                "analysisId", rawData.getOrDefault("analysisId", ""),
                "timestamp", now
        );
        case "agent_state_update" -> Map.of(
                "agentName", rawData.getOrDefault("agentName", ""),
                "status", rawData.getOrDefault("status", ""),
                "progress", rawData.getOrDefault("progress", 0.0),
                "intermediateResult", rawData.getOrDefault("intermediateResult", null),
                "durationMs", rawData.getOrDefault("durationMs", null)
        );
        case "agent_completed" -> Map.of(
                "agentName", rawData.getOrDefault("agentName", ""),
                "analysisId", rawData.getOrDefault("analysisId", ""),
                "result", rawData.getOrDefault("result", Map.of()),
                "timestamp", now
        );
        case "agent_failed" -> Map.of(
                "agentName", rawData.getOrDefault("agentName", ""),
                "error", rawData.getOrDefault("error", "Unknown error"),
                "timestamp", now
        );
        case "analysis_completed" -> Map.of(
                "analysisId", rawData.getOrDefault("analysisId", ""),
                "status", rawData.getOrDefault("status", "completed"),
                "report", rawData.getOrDefault("report", ""),
                "citations", rawData.getOrDefault("citations", List.of())
        );
        case "error" -> Map.of(
                "type", rawData.getOrDefault("type", "internal"),
                "message", rawData.getOrDefault("message", "Internal server error")
        );
        case "ping" -> Map.of(
                "timestamp", now
        );
        default -> rawData; // 未知事件类型透传原始 data
    };
}
```

### 2. 心跳机制 + 超时检测（Service 层）

```java
/** 心跳间隔 */
private static final Duration HEARTBEAT_INTERVAL = Duration.ofSeconds(30);
/** 超时阈值（无数据事件） */
private static final Duration SSE_TIMEOUT = Duration.ofSeconds(120);

/**
 * SSE 流 + 心跳 + 超时检测（包装 generateReportStream）。
 * <p>1) 每 30s 注入 ping 事件保持连接活跃
 * <p>2) 120s 无数据事件发送 error:{type:timeout} 后关闭流
 * <p>3) ping 事件不写 Redis（控制事件）
 */
public Flux<AgentSseEvent> generateReportStreamWithHeartbeat(AgentRequest request, String lastEventId) {
    String analysisId = request.getAnalysisId();

    // 数据事件流（从 Python SSE）
    Flux<AgentSseEvent> dataStream = generateReportStream(request, lastEventId);

    // 心跳流（每 30s 发 ping）
    Flux<AgentSseEvent> heartbeatStream = Flux.interval(HEARTBEAT_INTERVAL)
            .map(seq -> AgentSseEvent.builder()
                    .id(System.currentTimeMillis())
                    .event("ping")
                    .data(Map.of("timestamp", Instant.now().toString()))
                    .build());

    // 合并数据流 + 心跳流
    Flux<AgentSseEvent> mergedStream = Flux.merge(dataStream, heartbeatStream);

    // 超时检测：120s 无数据事件（不含 ping）触发超时
    return dataStream
            .timeout(SSE_TIMEOUT, Mono.fromSupplier(() -> {
                // 超时时发送 error 事件
                AgentSseEvent timeoutEvent = AgentSseEvent.builder()
                        .id(System.currentTimeMillis())
                        .event("error")
                        .data(Map.of(
                                "type", "timeout",
                                "message", "SSE connection timeout: no data event received in 120s"
                        ))
                        .build();
                return timeoutEvent;
            }))
            .mergeWith(heartbeatStream.takeUntilOther(dataStream.ignoreElements()))
            .doOnNext(event -> {
                // ping 事件不写 Redis
                if (!"ping".equals(event.getEvent()) && !"error".equals(event.getEvent())) {
                    writeAgentStateToRedis(analysisId, event);
                }
            });
}
```

### 3. WebClientConfig 超时调整

```java
/**
 * SSE 流式调用 WebClient (120s 响应超时)，用于 /api/agent/analyze/stream。
 * <p>从 150s 调整为 120s，对齐 JM4 检查点。
 */
@Bean("sseWebClient")
public WebClient sseWebClient() {
    ConnectionProvider connectionProvider = ConnectionProvider.builder("ai-service-sse-pool")
            .maxConnections(20)
            .pendingAcquireTimeout(Duration.ofSeconds(60))
            .build();

    HttpClient httpClient = HttpClient.create(connectionProvider)
            .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, 5000)
            .responseTimeout(Duration.ofSeconds(120))  // 150s → 120s
            .doOnConnected(conn -> conn
                    .addHandlerLast(new ReadTimeoutHandler(120, TimeUnit.SECONDS))  // 150s → 120s
                    .addHandlerLast(new WriteTimeoutHandler(30, TimeUnit.SECONDS)));

    // ... 其余不变
}
```

### 4. SecurityConfig CORS 扩展

```java
@Bean
public CorsConfigurationSource corsConfigurationSource() {
    CorsConfiguration configuration = new CorsConfiguration();
    List<String> origins = Arrays.asList(allowedOrigins.split(","));
    configuration.setAllowedOrigins(origins);
    configuration.setAllowedMethods(Arrays.asList("GET", "POST", "PUT", "DELETE", "OPTIONS"));
    // 增加 Last-Event-ID Header 支持 SSE 断线重连
    configuration.setAllowedHeaders(Arrays.asList(
            "Authorization", "Content-Type", "X-Request-Id", "Last-Event-ID"
    ));
    configuration.setAllowCredentials(true);
    configuration.setMaxAge(3600L);

    UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
    source.registerCorsConfiguration("/**", configuration);
    return source;
}
```

---

## SSE 事件格式规范

| 事件类型 | event 字段 | data 字段（JSON） |
|---------|-----------|------------------|
| Agent 启动 | `agent_started` | `{agentName, analysisId, timestamp}` |
| Agent 状态更新 | `agent_state_update` | `{agentName, status, progress, intermediateResult, durationMs}` |
| Agent 完成 | `agent_completed` | `{agentName, analysisId, result, timestamp}` |
| Agent 失败 | `agent_failed` | `{agentName, error, timestamp}` |
| 分析完成 | `analysis_completed` | `{analysisId, status, report, citations}` |
| 错误 | `error` | `{type, message}` |
| 心跳 | `ping` | `{timestamp}` |

**SSE 原始格式示例**：
```
event: agent_started
data: {"agentName":"retriever","analysisId":"anl_abc123","timestamp":"2026-06-08T14:30:00Z"}
id: 1
retry: 5000

event: ping
data: {"timestamp":"2026-06-08T14:30:30Z"}
id: 2

event: agent_completed
data: {"agentName":"retriever","analysisId":"anl_abc123","result":{...},"timestamp":"2026-06-08T14:31:00Z"}
id: 3
```

---

## 禁止行为

- ❌ 心跳 ping 事件写 Redis Hash
- ❌ 超时关闭 SSE 流时不发送 error 事件直接断开
- ❌ error 事件 data 包含 Python 服务堆栈/URL
- ❌ 在 Controller 层实现心跳/超时逻辑
- ❌ SSE 事件 data 使用非 JSON 格式
- ❌ sseWebClient 超时设为 0 或负数

---

## 测试要求

| 测试名 | 覆盖 |
|--------|------|
| `sseEventFormat_agent_started_has_required_fields` | agent_started 格式 |
| `sseEventFormat_agent_state_update_has_required_fields` | agent_state_update 格式 |
| `sseEventFormat_agent_completed_has_required_fields` | agent_completed 格式 |
| `sseEventFormat_agent_failed_has_required_fields` | agent_failed 格式 |
| `sseEventFormat_analysis_completed_has_required_fields` | analysis_completed 格式 |
| `sseEventFormat_error_has_type_and_message` | error 格式 + 安全（无堆栈） |
| `sseEventFormat_ping_has_timestamp` | ping 格式 |
| `heartbeat_emits_ping_every_30s` | 30s 心跳间隔 |
| `timeout_emits_error_after_120s_no_data` | 120s 超时 + error 事件 |
| `timeout_resets_on_data_event` | 数据事件重置超时 |
| `lastEventId_forwarded_to_python` | Last-Event-ID 透传 |
| `cors_allows_last_event_id_header` | CORS Last-Event-ID |
| `webClient_sse_timeout_is_120s` | WebClient 超时配置 |

**验证命令**：
```bash
# 单元测试
cd Veritas/backend && mvn -Dtest='SseEventFormatTest,SseHeartbeatTimeoutTest' test

# 手动验证 - SSE 流
curl -s -N -H 'Authorization: Bearer {token}' -H 'Accept: text/event-stream' \
  http://localhost:8080/api/agents/{analysisId}/stream
# 期望: 收到 SSE 事件流（event: agent_started, event: ping, ...）

# 手动验证 - Last-Event-ID 重连
curl -s -N -H 'Authorization: Bearer {token}' -H 'Last-Event-ID: 5' -H 'Accept: text/event-stream' \
  http://localhost:8080/api/agents/{analysisId}/stream
# 期望: 从 event id=6 开始续传
```

---

## 验收标准

- [ ] 7 种 SSE 事件类型 data 格式标准化，所有字段符合规范
- [ ] 每 30s 发送 ping 心跳事件保持连接
- [ ] 120s 无数据事件自动关闭 SSE 流（先发 error:{type:timeout} 再关闭）
- [ ] Last-Event-ID 支持断线重连
- [ ] CORS 允许前端跨域 SSE 请求（含 Last-Event-ID Header）
- [ ] sseWebClient 超时从 150s 调整为 120s
- [ ] error 事件不暴露 Python 内部堆栈/URL
- [ ] 13+ 个单元测试全部通过

---

## 下一步（JM4 验收 → JM5 启动）

### JM4 验收清单（task28 + task29 完成后）
- ☑ AgentController SSE 转发（task28）
- ☑ Agent 状态 Redis 缓存 7 种事件映射（task28）
- ☑ Agent 状态查询 API（task28）
- ☑ SSE 事件格式标准化（task29）
- ☑ 心跳机制 30s ping（task29）
- ☑ 超时处理 120s（task29）
- ☑ Last-Event-ID 断线重连（task29）
- ☑ CORS 支持 SSE（task29）

### JM5 启动准备
- **JM5 Day 1-2**: 前端 SSE EventSource 集成 + Agent 状态可视化
- **JM5 Day 3-4**: ECharts Agent 执行进度可视化
- **JM5 Day 5-7**: 对比分析/综述生成前端页面

---

## 未来建议 / 补充

1. **建议 SSE 流增加 retry 字段**：当前 toStandardizedSseEvent 已设置 retry:5000ms，前端 EventSource 自动 5s 重连；建议 Python 端也设置 `retry: 5000\n` 确保一致性
2. **建议引入 SSE 连接数限制**：每用户最多 3 个并发 SSE 流，超过返回 429 Too Many Requests；可用 Redis 计数器实现
3. **建议心跳间隔可配置化**：当前硬编码 30s，建议提取到 `application.yml` 的 `ai-service.sse.heartbeat-interval` 配置项
4. **建议超时时间可配置化**：当前硬编码 120s，建议提取到 `ai-service.sse.timeout` 配置项
5. **建议前端 EventSource 封装统一 SSE Client**：处理自动重连 + 事件分发 + 心跳超时检测，减少各组件重复逻辑
6. **建议增加 SSE 流量监控**：通过 Micrometer 暴露 `sse_connections_active` + `sse_events_sent_total` 指标，便于 JM6 性能监控
