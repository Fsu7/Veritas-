# task30: 降级机制完善（缓存回退+降级标记） (JM4 Week 7-8 Day 4-5)

> **里程碑**：M4 多Agent协同 / **JM4 Day 4-5**：降级机制完善
> **版本**：v0.4
> **优先级**：P0
> **功能编号**：F2.4.6, F2.4.7, F2.5.6

---

## 任务概述

完善降级机制，支持 **COMPARE（对比分析）** 和 **REPORT（综述生成）** 的降级场景，新增 **SSE 流降级处理**，确保 AI 服务不可用时系统优雅降级：

| 降级类型 | 场景 | 降级内容 |
|----------|------|----------|
| COMPARE | Python 不可用 + 无缓存 | 返回对比框架提示（研究背景/方法/结果/结论对比） |
| REPORT | Python 不可用 + 无缓存 | 返回综述大纲提示（引言/相关工作/方法综述/讨论/结论） |
| SSE 流 | Python 不可用 | 发送降级事件（error + analysis_completed）后关闭流 |
| 缓存回退 | COMPARE/REPORT + 有缓存 | 返回缓存结果 + degraded=true |

---

## 上下文定位

| 涉及层级 | 模块 |
|----------|------|
| java_backend | `AgentClientService`（扩展 handleFallback + 新增 handleStreamFallback） |
| java_backend | `AnalysisResultDTO`（新增 compareDegraded/reportDegraded 工厂） |
| java_backend | `AnalysisService`（comparePapers/generateReport 降级处理） |

**已有可复用**：
- `AgentClientService.handleFallback()` — 三级降级（PAPER_ANALYSIS only）
- `AnalysisResultDTO.degraded()` — 通用降级静态工厂
- `AgentSseEvent` — SSE 事件 DTO（7 种事件类型）
- `RedisKeyUtil.analysisResultKey()` — 缓存 key 模式
- `AnalysisType` 枚举 — PAPER_ANALYSIS / COMPARE / REPORT

---

## 涉及文件

| 操作 | 路径 | 说明 |
|------|------|------|
| 修改 | `service/AgentClientService.java` | 扩展 handleFallback(COMPARE/REPORT) + 新增 handleStreamFallback() + comparePapers() |
| 修改 | `dto/response/AnalysisResultDTO.java` | +2 降级工厂方法（compareDegraded/reportDegraded） |
| 修改 | `service/AnalysisService.java` | +2 方法（comparePapers/generateReport 降级处理） |
| 修改 | `test/service/AgentClientServiceTest.java` | +6 降级测试（COMPARE/REPORT/SSE流） |
| 修改 | `test/service/AnalysisServiceTest.java` | +2 降级传递测试 |
| 修改 | `test/dto/AiDtoSerializationTest.java` | +2 工厂方法序列化测试 |

---

## 关键实现

### 1. handleFallback 扩展（按 analysisType 区分）

```java
private AnalysisResultDTO handleFallback(AgentRequest request, Exception e) {
    String analysisId = request.getAnalysisId();
    if (analysisId == null || analysisId.isBlank()) {
        analysisId = "unknown";
    }
    
    // 1) Redis 缓存回退（所有类型共用）
    String fallbackKey = RedisKeyUtil.analysisResultKey(analysisId);
    try {
        String cached = redisTemplate.opsForValue().get(fallbackKey);
        if (cached != null) {
            AnalysisResultDTO cachedDto = objectMapper.readValue(cached, AnalysisResultDTO.class);
            return AnalysisResultDTO.builder()
                    .analysisId(cachedDto.getAnalysisId())
                    .status(cachedDto.getStatus())
                    .report(cachedDto.getReport())
                    .citations(cachedDto.getCitations())
                    .agentStates(cachedDto.getAgentStates())
                    .degraded(true)
                    .degradedReason("AI服务暂时不可用，返回缓存结果")
                    .build();
        }
    } catch (Exception ex) {
        log.error("降级缓存反序列化失败: analysisId={}, error={}", analysisId, ex.getMessage());
    }
    
    // 2) 无缓存时按 analysisType 返回不同降级 DTO
    return switch (request.getAnalysisType()) {
        case COMPARE -> AnalysisResultDTO.compareDegraded(analysisId, "AI服务暂时不可用，对比分析功能暂不可用");
        case REPORT -> AnalysisResultDTO.reportDegraded(analysisId, "AI服务暂时不可用，综述生成功能暂不可用");
        default -> AnalysisResultDTO.degraded(analysisId, "AI服务暂时不可用，请稍后重试");
    };
}
```

### 2. handleStreamFallback（SSE 流降级）

```java
/**
 * SSE 流降级：Python 不可用时发送降级事件后关闭流。
 * <p>事件序列：1) error(degradation) → 2) analysis_completed(degraded=true)
 */
public Flux<AgentSseEvent> handleStreamFallback(String analysisId, Exception e) {
    log.warn("SSE流降级: analysisId={}, error={}", analysisId, e.getMessage());
    
    AgentSseEvent degradationEvent = AgentSseEvent.builder()
            .id(System.currentTimeMillis())
            .event("error")
            .data(Map.of(
                    "type", "degradation",
                    "message", "AI服务暂时不可用，已返回缓存结果",
                    "analysisId", analysisId
            ))
            .build();
    
    AgentSseEvent completedEvent = AgentSseEvent.builder()
            .id(System.currentTimeMillis() + 1)
            .event("analysis_completed")
            .data(Map.of(
                    "status", "completed",
                    "degraded", true,
                    "degradedReason", "AI服务暂时不可用，返回缓存结果",
                    "analysisId", analysisId
            ))
            .build();
    
    return Flux.just(degradationEvent, completedEvent);
}
```

### 3. AnalysisResultDTO 降级工厂方法

```java
/**
 * 对比分析降级响应静态工厂。
 * 返回包含对比框架提示的降级 DTO。
 */
public static AnalysisResultDTO compareDegraded(String analysisId, String reason) {
    return AnalysisResultDTO.builder()
            .analysisId(analysisId)
            .status(AnalysisStatus.FAILED)
            .degraded(true)
            .degradedReason(reason)
            .report("## 对比分析框架（降级提示）\n\n1. 研究背景对比\n2. 研究方法对比\n3. 实验结果对比\n4. 结论与展望对比\n\n> AI服务暂时不可用，以上为对比分析框架参考。")
            .build();
}

/**
 * 综述生成降级响应静态工厂。
 * 返回包含综述大纲提示的降级 DTO。
 */
public static AnalysisResultDTO reportDegraded(String analysisId, String reason) {
    return AnalysisResultDTO.builder()
            .analysisId(analysisId)
            .status(AnalysisStatus.FAILED)
            .degraded(true)
            .degradedReason(reason)
            .report("## 综述大纲（降级提示）\n\n1. 引言\n2. 相关工作\n3. 方法综述\n4. 讨论与比较\n5. 结论与未来方向\n\n> AI服务暂时不可用，以上为综述大纲参考。")
            .build();
}
```

### 4. generateReportStream 降级集成

```java
public Flux<AgentSseEvent> generateReportStream(AgentRequest request, String lastEventId) {
    return pythonAIClient.analyzeStream(request, lastEventId)
            .doOnNext(event -> writeAgentStateToRedis(request.getAnalysisId(), event))
            .onErrorResume(AIServiceException.class, e -> {
                log.warn("SSE流AI服务异常，切换降级: analysisId={}", request.getAnalysisId());
                // 先尝试缓存回退
                AnalysisResultDTO cached = tryGetCachedResult(request.getAnalysisId());
                if (cached != null) {
                    cacheAnalysisResult(request.getAnalysisId(), cached);
                }
                return handleStreamFallback(request.getAnalysisId(), e);
            })
            .onErrorContinue((err, item) ->
                    log.warn("SSE event 解析失败: {}", err.getMessage()));
}
```

---

## 降级策略矩阵

| 分析类型 | Python 正常 | Python 异常 + Redis 有缓存 | Python 异常 + Redis 无缓存 |
|----------|------------|--------------------------|--------------------------|
| PAPER_ANALYSIS | 正常 DTO | cached + degraded=true | degraded() 通用降级 DTO |
| COMPARE | 正常 DTO | cached + degraded=true | compareDegraded() 含对比框架 |
| REPORT | 正常 DTO | cached + degraded=true | reportDegraded() 含综述大纲 |
| SSE 流 | 正常事件流 | — | error(degradation) + completed(degraded) |

---

## 禁止行为

- ❌ 降级时抛异常到 Controller（必须返回 degraded DTO）
- ❌ handleStreamFallback() 返回 Flux.error()（必须返回包含降级事件的正常 Flux）
- ❌ COMPARE/REPORT 降级 DTO 不含 report 字段（降级提示必须包含对比框架/综述大纲）
- ❌ degradedReason 暴露 Python 内部异常信息
- ❌ 缓存回退时修改反序列化的 cachedDto 原对象（U-002 不可变副本）
- ❌ handleFallback() 不区分 analysisType

---

## 测试要求

| 测试名 | 覆盖 |
|--------|------|
| `comparePapers_aiServiceException_returns_compareDegraded` | COMPARE 降级 + 无缓存 |
| `comparePapers_cache_hit_returns_cached_with_degraded_flag` | COMPARE 缓存回退 |
| `report_aiServiceException_returns_reportDegraded` | REPORT 降级 + 无缓存 |
| `report_cache_hit_returns_cached_with_degraded_flag` | REPORT 缓存回退 |
| `handleStreamFallback_sends_degradation_event_then_completed` | SSE 流降级事件序列 |
| `handleStreamFallback_events_contain_correct_data` | SSE 降级事件数据格式 |
| `analysisService_comparePapers_degraded_marks_degraded_true` | 降级标记传递 |
| `analysisService_generateReport_degraded_marks_degraded_true` | 降级标记传递 |
| `compareDegraded_factory_method_creates_correct_dto` | 工厂方法 |
| `reportDegraded_factory_method_creates_correct_dto` | 工厂方法 |

**验证命令**：
```bash
# 单元测试
cd Veritas/backend && mvn -Dtest='AgentClientServiceTest,AnalysisServiceTest,AiDtoSerializationTest' test

# 全量测试
cd Veritas/backend && mvn test
# 期望: 272+ 现有测试 + 新增测试全部通过
```

---

## 验收标准

- [ ] handleFallback() 支持 COMPARE 类型降级，返回含对比框架提示的降级 DTO
- [ ] handleFallback() 支持 REPORT 类型降级，返回含综述大纲提示的降级 DTO
- [ ] handleStreamFallback() SSE 流降级发送正确事件序列（error + analysis_completed）
- [ ] AnalysisResultDTO.degraded=true 在所有降级路径中正确设置
- [ ] Redis 缓存回退对 COMPARE/REPORT 类型正常工作
- [ ] degradedReason 明确说明降级原因
- [ ] Python 不可用时 SSE 流不崩溃，发送降级事件后正常关闭
- [ ] 272+ 现有测试 + 新增测试全部通过

---

## 下一步（JM4 Day 6-7）

### task31: 集成测试 + Bug修复
- **AnalysisServiceIntegrationTest** — 对比分析/综述生成/降级端到端测试
- **SseIntegrationTest** — SSE 事件顺序/断线重连/心跳/超时/降级测试
- **AgentControllerIntegrationTest** — Agent 控制器集成测试
- 修复测试中发现的 Bug

---

## 未来建议 / 补充

1. **建议引入 Resilience4j 熔断器**：当前三级降级无熔断，连续 AI 故障会持续触发重试；JM6 性能优化时引入 CircuitBreaker
2. **建议降级原因枚举化**：当前 degradedReason 为字符串，建议 JM5 引入 DegradedReason 枚举（TIMEOUT / SERVICE_UNAVAILABLE / CACHE_FALLBACK），前端可根据枚举值展示不同 UI
3. **建议 SSE 降级事件增加 retryAfter 字段**：告知客户端建议重试间隔，避免频繁重连
4. **建议降级 DTO 的 report 字段增加 i18n 支持**：当前降级提示硬编码中文，JM5 国际化时需提取
5. **建议 COMPARE/REPORT 缓存使用独立 key 前缀**：当前 analysis:result:{id} 不区分类型，若同一 analysisId 先做 PAPER_ANALYSIS 再做 COMPARE 会冲突；JM5 可考虑 analysis:compare:result:{id}
