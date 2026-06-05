# task23: 分析结果查询 + 状态查询 + /health AI 集成 (JM3 Week 6 Day 2)

> **里程碑**：M3：前后端联调成功 / **JM3 Week 6 Day 2**：分析结果/状态查询 + 健康检查
> **版本**：v0.3
> **优先级**：P0
> **功能编号**：F2.4.4, F2.4.5, F2.5.5

---

## 任务概述

扩展 task22 的 `AnalysisService` 与 `AnalysisController`，新增 **3 个端点** + **2 个 DTO** + **HealthController 升级**：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/analysis/{analysisId}` | GET | 查询完整分析结果（含嵌套 report/citations/agentStates） |
| `/api/analysis/{analysisId}/status` | GET | 实时状态（聚合 AnalysisResult.status + Agent Redis 状态） |
| `/health`（扩展） | GET | 新增 `aiService` 字段（UP/DOWN） |

---

## 上下文定位

| 涉及层级 | 模块 |
|----------|------|
| java_backend | `AnalysisService`（扩展） / `AnalysisController`（扩展） / `HealthController`（扩展） |
| java_backend | `dto/response.AnalysisResponse` / `AnalysisStatusResponse`（新增） |

**已有可复用**：
- `task22 AnalysisService.analyzePaper` + 数据隔离模式
- `task21 AgentClientService.getAgentStates(analysisId)` + `isHealthy()`
- `AnalysisResultRepository.findByAnalysisId(String)`
- `AnalysisResult Entity`（result JSON 字段）
- `RedisKeyUtil.analysisResultKey(analysisId)`（缓存 key）

---

## 涉及文件

| 操作 | 路径 | 说明 |
|------|------|------|
| 修改 | `service/AnalysisService.java` | +2 方法（getAnalysisResult / getAnalysisStatus） |
| 修改 | `controller/AnalysisController.java` | +2 GET 端点 |
| 修改 | `controller/HealthController.java` | 注入 AgentClientService + 增 aiService 字段 |
| 新增 | `dto/response/AnalysisResponse.java` | 6 字段（含 result 嵌套 DTO） |
| 新增 | `dto/response/AnalysisStatusResponse.java` | 5 字段（聚合状态） |
| 修改 | `test/controller/HealthControllerTest.java` | 扩展 aiService 字段测试 |
| 新增 | `test/service/AnalysisServiceQueryTest.java` | 5 个查询测试 |

---

## 关键实现

### 1. getAnalysisResult（缓存路径）

```java
@Cacheable(value = "analysisResult", key = "#analysisId", unless = "#result == null")
@Transactional(readOnly = true)
public AnalysisResponse getAnalysisResult(String userId, String analysisId) {
    AnalysisResult entity = analysisResultRepository.findByAnalysisId(analysisId)
        .orElseThrow(() -> new ResourceNotFoundException("AnalysisResult", analysisId));
    
    // 数据隔离：通过 sessionId → Session → userId 校验
    Session session = sessionRepository.findBySessionId(entity.getSessionId())
        .orElseThrow(() -> new ResourceNotFoundException("Session", entity.getSessionId()));
    validateDataIsolation(session.getUserId(), userId);
    
    // 反序列化 result JSON
    AnalysisResultDTO resultDto = parseResultJson(entity.getResult());
    
    return AnalysisResponse.builder()
        .analysisId(entity.getAnalysisId())
        .sessionId(entity.getSessionId())
        .status(entity.getStatus())
        .type(entity.getType())
        .result(resultDto)
        .createdAt(entity.getCreatedAt())
        .build();
}

@CacheEvict(value = "analysisResult", key = "#analysisId")
@Transactional
protected void updateAnalysisResult(String analysisId, AnalysisResultDTO result) {
    // task22 updateAnalysisResult 增加 @CacheEvict
}
```

### 2. getAnalysisStatus（实时聚合，不缓存）

```java
public AnalysisStatusResponse getAnalysisStatus(String userId, String analysisId) {
    // 1) DB 状态
    AnalysisResult entity = analysisResultRepository.findByAnalysisId(analysisId)
        .orElseThrow(() -> new ResourceNotFoundException("AnalysisResult", analysisId));
    Session session = sessionRepository.findBySessionId(entity.getSessionId())
        .orElseThrow(() -> new ResourceNotFoundException("Session", entity.getSessionId()));
    validateDataIsolation(session.getUserId(), userId);
    
    // 2) 实时 Agent 状态（Redis Hash）
    List<AgentStateResponse> agentStates = agentClientService.getAgentStates(analysisId);
    
    // 3) 计算 progress + currentAgent
    Double progress = computeAverageProgress(agentStates);
    String currentAgent = agentStates.stream()
        .filter(a -> "running".equals(a.getStatus()))
        .map(AgentStateResponse::getAgentName)
        .findFirst()
        .orElse(null);
    
    return AnalysisStatusResponse.builder()
        .analysisId(analysisId)
        .status(entity.getStatus())
        .progress(progress)
        .currentAgent(currentAgent)
        .agentStates(agentStates)
        .build();
}

private Double computeAverageProgress(List<AgentStateResponse> agents) {
    if (agents == null || agents.isEmpty()) return null;
    return agents.stream()
        .filter(a -> a.getProgress() != null)
        .mapToDouble(AgentStateResponse::getProgress)
        .average()
        .orElse(0.0);
}
```

### 3. HealthController 扩展

```java
@RestController
@Slf4j
public class HealthController {

    private final DataSource dataSource;
    private final RedisTemplate<String, String> redisTemplate;
    private final AgentClientService agentClientService;  // 新增

    public HealthController(DataSource dataSource, 
                            RedisTemplate<String, String> redisTemplate,
                            AgentClientService agentClientService) {
        this.dataSource = dataSource;
        this.redisTemplate = redisTemplate;
        this.agentClientService = agentClientService;
    }

    @GetMapping("/health")
    public ApiResponse<Map<String, Object>> health() {
        Map<String, Object> healthData = new HashMap<>();
        String mysqlStatus = checkMySQL();
        String redisStatus = checkRedis();
        String aiStatus = checkAIService();  // 新增
        
        String overallStatus = "UP".equals(mysqlStatus) && "UP".equals(redisStatus) && "UP".equals(aiStatus) 
            ? "UP" : "DOWN";
        
        healthData.put("status", overallStatus);
        healthData.put("mysql", mysqlStatus);
        healthData.put("redis", redisStatus);
        healthData.put("aiService", aiStatus);
        return ApiResponse.success(healthData);
    }
    
    private String checkAIService() {
        try {
            return agentClientService.isHealthy() ? "UP" : "DOWN";
        } catch (Exception e) {
            log.warn("AI service health check failed: {}", e.getMessage());
            return "DOWN";
        }
    }
}
```

---

## 缓存策略

| 缓存空间 | Key | TTL | 失效时机 |
|----------|-----|-----|----------|
| `analysisResult` | `analysis:result:{analysisId}` | 30min | `updateAnalysisResult` 后 `@CacheEvict` |
| `agent:state`（不缓存查询） | — | — | 实时从 Redis Hash 读 |

---

## 禁止行为

- ❌ getAnalysisStatus 使用 @Cacheable（必须实时性）
- ❌ 暴露他人 analysisId 数据
- ❌ HealthController 直接构造 WebClient
- ❌ /health 在 AI 5s 超时时阻塞响应线程（isHealthy 内部已 5s 超时）
- ❌ getAnalysisResult 返回 Entity

---

## 测试要求

| 测试名 | 覆盖 |
|--------|------|
| `getAnalysisResult_returns_dto_with_deserialized_result` | 正常 + JSON 反序列化 |
| `getAnalysisResult_uses_cache_second_call` | 缓存命中 |
| `getAnalysisResult_other_user_returns403` | 数据隔离 |
| `getAnalysisStatus_aggregates_agent_states` | 状态聚合 + progress 计算 |
| `getAnalysisStatus_empty_agents_progress_null` | 边界（无 Agent 状态） |
| `healthController_includes_aiService_field` | UP 场景 |
| `healthController_python_down_returns_DOWN` | DOWN 场景 |

**验证命令**：
```bash
# 单元测试
cd Veritas/backend && mvn -Dtest='AnalysisServiceQueryTest,HealthControllerTest' test

# 手动验证
curl -s http://localhost:8080/health | jq .
# 期望: {code:200, data:{status:UP, mysql:UP, redis:UP, aiService:UP}}
```

---

## 验收标准

- [ ] GET /api/analysis/{id} 返回 AnalysisResponse，result 字段正确反序列化
- [ ] getAnalysisResult 走 @Cacheable 缓存（30min TTL）
- [ ] GET /api/analysis/{id}/status 返回聚合状态（不缓存）
- [ ] 数据隔离：他人 analysisId → 403
- [ ] /health 响应增加 aiService 字段
- [ ] Python 停止时 /health 整体 DOWN
- [ ] 7+ 个测试全部通过

---

## 下一步（JM3 验收 → JM4 启动）

### JM3 验收清单（本任务完成后）
- ☑ PythonAIClient 同步调用成功（task19）
- ☑ 请求转换正确（task20）
- ☑ 响应解析正确（task20）
- ☑ 超时处理 + 重试（task19）
- ☑ 降级处理（task21）
- ☑ 论文分析 API（task22）
- ☑ 分析结果查询 API（task23）
- ☑ 分析状态查询 API（task23）
- ☑ AgentRequest/AnalysisResultDTO/AgentStateResponse DTO（task20）
- ☑ /health 包含 AI 服务状态（task23）

### JM4 启动准备
- **JM4 Day 1-2**: AnalysisService 完整编排（扩展 analyzePaper → 对比/综述）
- **JM4 Day 3-4**: 对比分析 API + 综述生成 API
- **JM4 Day 5-10**: SSE 推送 + AgentController + PythonAIClient SSE 扩展

---

## 未来建议 / 补充

1. **建议引入 Hystrix/Resilience4j 熔断器**：当前三级降级无熔断，连续 AI 故障会持续触发重试；JM6 性能优化时引入
2. **建议增加 /metrics 端点**：通过 Micrometer 暴露 ai_service_call_duration_seconds 指标，便于 JM6 性能监控
3. **建议 AnalysisResult 增加 user_id 列**：当前通过 sessionId 间接隔离有性能损耗；JM5 缓存优化时可考虑冗余字段
4. **建议 AnalysisResult.result 列增加版本号**：未来 Python 端 AnalyzeResponse Schema 演进时（JM4 综述报告增加 structure 字段），Java 端反序列化可向后兼容
5. **跨系统字段命名**：务必依赖全局 Jackson SNAKE_CASE，**禁止** DTO 字段加 @JsonProperty
