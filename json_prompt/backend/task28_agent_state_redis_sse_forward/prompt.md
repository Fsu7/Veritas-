# task28: Agent状态Redis缓存 + AgentController SSE转发 (JM4 Day 7-8)

> **里程碑**：M4 多Agent协同 / **JM4 Day 7-8**：AgentController SSE 转发 + Agent 状态 Redis 缓存完善
> **版本**：v0.4
> **优先级**：P0
> **功能编号**：F2.4.6, F2.4.7, F2.5.6

---

## 任务概述

新建 `AgentController` 处理 Agent 相关的 SSE 转发和状态查询，完善 `AgentClientService.writeAgentStateToRedis()` 支持全部 7 种 SSE 事件类型映射，将 `AnalysisController.agentStream` 逻辑迁移至 `AgentController`，旧端点标记 `@Deprecated` 并 301 重定向。

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/agents/{analysisId}/stream` | GET | SSE 流转发（从 AnalysisController 迁移） |
| `/api/agents/{analysisId}/states` | GET | 查询所有 Agent 状态（Redis Hash） |
| `/api/agents/{analysisId}/status?agentName=xxx` | GET | 查询单个 Agent 状态 |
| `/api/analysis/{analysisId}/agent-stream`（旧） | GET | @Deprecated + 301 重定向 |

---

## 上下文定位

| 涉及层级 | 模块 |
|----------|------|
| java_backend | `AgentController`（新增） |
| java_backend | `AgentClientService`（扩展 writeAgentStateToRedis） |
| java_backend | `AnalysisController`（修改 agentStream → @Deprecated） |

**已有可复用**：
- `AnalysisController.agentStream` — SSE 转发逻辑（待迁移）
- `AgentClientService.generateReportStream` — Flux<AgentSseEvent> SSE 流
- `AgentClientService.writeAgentStateToRedis` — 仅处理 agent_state_update（需扩展）
- `AgentClientService.getAgentStates` — Redis Hash 读取
- `AnalysisService.validateAnalysisAccess` — 数据隔离校验
- `AgentSseEvent` — 7 种事件类型定义
- `AgentStateResponse` — Agent 状态 DTO（5 字段）
- `RedisKeyUtil.agentStateKey` — "agent:state:{analysisId}"

---

## 涉及文件

| 操作 | 路径 | 说明 |
|------|------|------|
| 新增 | `controller/AgentController.java` | Agent 专用控制器（3 端点） |
| 修改 | `service/AgentClientService.java` | writeAgentStateToRedis 扩展 + getAgentState 新增 |
| 修改 | `controller/AnalysisController.java` | agentStream @Deprecated + 301 重定向 |
| 新增 | `test/controller/AgentControllerTest.java` | AgentController 测试 |
| 新增 | `test/service/AgentClientServiceRedisTest.java` | Redis 写入映射测试 |

---

## 关键实现

### 1. AgentController（新增）

```java
@Slf4j
@RestController
@RequestMapping("/api/agents")
@RequiredArgsConstructor
public class AgentController {

    private final AgentClientService agentClientService;
    private final AnalysisService analysisService;

    /**
     * SSE 流转发（GET /api/agents/{analysisId}/stream）。
     * <p>从 AnalysisController.agentStream 迁移，支持 compare/report 分析类型。
     */
    @GetMapping(value = "/{analysisId}/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<Object>> agentStream(
            @PathVariable String analysisId,
            @RequestHeader(value = "Last-Event-ID", required = false) String lastEventId,
            @AuthenticationPrincipal String userId) {
        String currentUserId = resolveUserId(userId);
        log.info("AgentController.agentStream: userId={}, analysisId={}, lastEventId={}",
                currentUserId, analysisId, lastEventId);

        // 数据隔离校验
        analysisService.validateAnalysisAccess(currentUserId, analysisId);

        AgentRequest agentRequest = AgentRequest.builder()
                .analysisId(analysisId)
                .userId(currentUserId)
                .build();

        return agentClientService.generateReportStream(agentRequest, lastEventId)
                .map(this::toServerSentEvent);
    }

    /**
     * 查询所有 Agent 状态（GET /api/agents/{analysisId}/states）。
     */
    @GetMapping("/{analysisId}/states")
    public ResponseEntity<ApiResponse<List<AgentStateResponse>>> getAgentStates(
            @PathVariable String analysisId,
            @AuthenticationPrincipal String userId) {
        String currentUserId = resolveUserId(userId);
        analysisService.validateAnalysisAccess(currentUserId, analysisId);
        List<AgentStateResponse> states = agentClientService.getAgentStates(analysisId);
        return ResponseEntity.ok(ApiResponse.success(states));
    }

    /**
     * 查询单个 Agent 状态（GET /api/agents/{analysisId}/status?agentName=xxx）。
     */
    @GetMapping("/{analysisId}/status")
    public ResponseEntity<ApiResponse<AgentStateResponse>> getAgentStatus(
            @PathVariable String analysisId,
            @RequestParam String agentName,
            @AuthenticationPrincipal String userId) {
        String currentUserId = resolveUserId(userId);
        analysisService.validateAnalysisAccess(currentUserId, analysisId);
        AgentStateResponse state = agentClientService.getAgentState(analysisId, agentName);
        return ResponseEntity.ok(ApiResponse.success(state));
    }
}
```

### 2. writeAgentStateToRedis 扩展（7 种事件映射）

```java
/**
 * 从 SSE 事件中提取 Agent 状态并写入 Redis（支持全部 7 种事件类型）。
 *
 * 事件映射规则：
 * - agent_started       → status=running, progress=0.0
 * - agent_state_update  → 完整状态更新（status/progress/intermediateResult/durationMs）
 * - agent_completed     → status=completed, progress=1.0
 * - agent_failed        → status=failed
 * - analysis_completed  → 所有 Agent status=completed
 * - error / ping        → 不写 Redis（控制事件）
 */
private void writeAgentStateToRedis(String analysisId, AgentSseEvent event) {
    if (analysisId == null || event == null || event.getEvent() == null) {
        return;
    }
    String eventType = event.getEvent();

    switch (eventType) {
        case "agent_started" -> {
            // 从 data 提取 agentName，写入 status=running, progress=0.0
            String agentName = extractAgentName(event);
            if (agentName != null) {
                AgentStateResponse state = AgentStateResponse.builder()
                        .agentName(agentName)
                        .status("running")
                        .progress(0.0)
                        .build();
                updateAgentState(analysisId, List.of(state));
            }
        }
        case "agent_state_update" -> {
            // 完整状态更新（现有逻辑）
            if (event.getData() != null && !event.getData().isEmpty()) {
                try {
                    AgentStateResponse state = objectMapper.convertValue(event.getData(), AgentStateResponse.class);
                    updateAgentState(analysisId, List.of(state));
                } catch (Exception e) {
                    log.warn("SSE 事件转 AgentState 失败: analysisId={}, error={}", analysisId, e.getMessage());
                }
            }
        }
        case "agent_completed" -> {
            String agentName = extractAgentName(event);
            if (agentName != null) {
                AgentStateResponse state = AgentStateResponse.builder()
                        .agentName(agentName)
                        .status("completed")
                        .progress(1.0)
                        .build();
                updateAgentState(analysisId, List.of(state));
            }
        }
        case "agent_failed" -> {
            String agentName = extractAgentName(event);
            if (agentName != null) {
                AgentStateResponse state = AgentStateResponse.builder()
                        .agentName(agentName)
                        .status("failed")
                        .build();
                updateAgentState(analysisId, List.of(state));
            }
        }
        case "analysis_completed" -> {
            // 所有 Agent 标记 completed
            markAllAgentsCompleted(analysisId);
        }
        case "error", "ping" -> {
            // 控制事件，不写 Redis
        }
        default -> log.debug("未知 SSE 事件类型: {}", eventType);
    }
}

/**
 * 从 SSE event data 中提取 agentName。
 */
private String extractAgentName(AgentSseEvent event) {
    if (event.getData() == null) return null;
    Object agentName = event.getData().get("agentName");
    return agentName != null ? agentName.toString() : null;
}

/**
 * 标记所有 Agent 为 completed（analysis_completed 事件触发）。
 */
private void markAllAgentsCompleted(String analysisId) {
    List<AgentStateResponse> currentStates = getAgentStates(analysisId);
    if (currentStates.isEmpty()) return;
    List<AgentStateResponse> completedStates = currentStates.stream()
            .map(s -> AgentStateResponse.builder()
                    .agentName(s.getAgentName())
                    .status("completed")
                    .progress(1.0)
                    .intermediateResult(s.getIntermediateResult())
                    .durationMs(s.getDurationMs())
                    .build())
            .toList();
    updateAgentState(analysisId, completedStates);
}
```

### 3. AnalysisController.agentStream @Deprecated + 301 重定向

```java
/**
 * @deprecated 使用 {@link AgentController#agentStream} 替代。将在 v0.5 移除。
 */
@Deprecated(forRemoval = true, since = "0.4")
@GetMapping(value = "/{analysisId}/agent-stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
public ResponseEntity<Void> agentStream(
        @PathVariable String analysisId,
        @RequestHeader(value = "Last-Event-ID", required = false) String lastEventId,
        @AuthenticationPrincipal String userId) {
    log.warn("agentStream 端点已弃用，请使用 GET /api/agents/{analysisId}/stream");
    return ResponseEntity.status(HttpStatus.MOVED_PERMANENTLY)
            .location(URI.create("/api/agents/" + analysisId + "/stream"))
            .build();
}
```

---

## SSE 事件 → Redis 映射表

| SSE 事件类型 | Redis 操作 | AgentStateResponse 字段 |
|-------------|-----------|------------------------|
| `agent_started` | 写入 Hash field=agentName | status=running, progress=0.0 |
| `agent_state_update` | 写入 Hash field=agentName | 完整状态（status/progress/intermediateResult/durationMs） |
| `agent_completed` | 写入 Hash field=agentName | status=completed, progress=1.0 |
| `agent_failed` | 写入 Hash field=agentName | status=failed |
| `analysis_completed` | 更新所有 Hash fields | status=completed, progress=1.0 |
| `error` | 不写 Redis | — |
| `ping` | 不写 Redis | — |

---

## 禁止行为

- ❌ AgentController 直接注入 PythonAIClient（必须通过 AgentClientService）
- ❌ writeAgentStateToRedis 忽略 agent_started/agent_completed/agent_failed 事件
- ❌ 删除 AnalysisController.agentStream 端点（必须保留 @Deprecated + 301）
- ❌ AgentController 直接调 Repository 查 AnalysisResult
- ❌ SSE 流中暴露 Python 服务异常堆栈或内部 URL
- ❌ 对 error/ping 事件写 Redis

---

## 测试要求

| 测试名 | 覆盖 |
|--------|------|
| `agentController_stream_returns_sse_events` | SSE 流转发正常 |
| `agentController_stream_validates_data_isolation` | 数据隔离 403 |
| `agentController_getAgentStates_returns_list` | 状态列表查询 |
| `agentController_getAgentStates_empty_returns_empty_list` | 空状态边界 |
| `agentController_getAgentStatus_returns_single` | 单 Agent 查询 |
| `agentController_getAgentStatus_not_found_returns404` | Agent 不存在 404 |
| `agentClientService_writeAgentState_agent_started_maps_running` | agent_started → running |
| `agentClientService_writeAgentState_agent_completed_maps_completed` | agent_completed → completed |
| `agentClientService_writeAgentState_agent_failed_maps_failed` | agent_failed → failed |
| `agentClientService_writeAgentState_analysis_completed_maps_all_completed` | analysis_completed → 全部 completed |
| `agentClientService_writeAgentState_error_ping_skip_redis` | error/ping → 不写 Redis |
| `analysisController_agentStream_deprecated_redirects_301` | 旧端点 301 重定向 |

**验证命令**：
```bash
# 单元测试
cd Veritas/backend && mvn -Dtest='AgentControllerTest,AgentClientServiceRedisTest' test

# 手动验证 - Agent 状态查询
curl -s -H 'Authorization: Bearer {token}' http://localhost:8080/api/agents/{analysisId}/states | jq .
# 期望: {code:200, data:[{agentName, status, progress, ...}]}

# 手动验证 - 旧端点重定向
curl -s -o /dev/null -w '%{http_code}' -H 'Authorization: Bearer {token}' http://localhost:8080/api/analysis/{analysisId}/agent-stream
# 期望: 301
```

---

## 验收标准

- [ ] AgentController 3 个端点均可正常访问，JWT 认证 + 数据隔离
- [ ] GET /api/agents/{analysisId}/stream SSE 流转发成功
- [ ] GET /api/agents/{analysisId}/states 返回 List<AgentStateResponse>
- [ ] GET /api/agents/{analysisId}/status?agentName=xxx 返回单个 AgentStateResponse
- [ ] writeAgentStateToRedis 支持 7 种事件类型正确映射
- [ ] AnalysisController.agentStream 标记 @Deprecated + 301 重定向
- [ ] 12+ 个单元测试全部通过

---

## 下一步（task29 衔接）

### task29 将在本任务基础上：
- **SSE 事件格式标准化**：统一 7 种事件的 data JSON 格式
- **心跳机制**：每 30s 发送 ping 事件保持连接
- **超时处理**：120s 无数据事件自动关闭 SSE 流
- **CORS 配置**：SecurityConfig 允许前端跨域 SSE 请求（Last-Event-ID Header）

---

## 未来建议 / 补充

1. **建议 AgentController 增加 /api/agents/{analysisId}/cancel 端点**：前端可取消正在执行的 Agent 流程，Python 端需配合实现取消接口
2. **建议 Redis Hash 增加 startedAt 字段**：当前 AgentStateResponse 仅有 durationMs，缺少绝对开始时间；前端展示"已运行 Xs"需要计算
3. **建议 writeAgentStateToRedis 增加事件幂等校验**：agent_completed 后再收到 agent_started（同一 agentName）应忽略或覆盖
4. **建议 SSE 流增加 retry 字段**：ServerSentEvent.builder().retry(5000) 告知前端断线后 5s 重连
5. **建议 AgentController 增加 Rate Limiting**：SSE 连接数限制（每用户最多 3 个并发 SSE 流），防止资源耗尽
