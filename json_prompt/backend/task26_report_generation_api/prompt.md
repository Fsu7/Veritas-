# task26: 综述生成API + ReportRequest DTO (JM4 Week 7-8 Day 4)

> **里程碑**：M4：多Agent协同 / **JM4 Week 7-8 Day 4**：综述生成API
> **版本**：v0.4
> **优先级**：P0
> **功能编号**：F2.4.3, F2.4.6

---

## 任务概述

实现综述生成API，支持基于多篇论文生成个性化综述报告。新建 `ReportRequest` DTO，扩展 `AnalysisService.generateReport()` 方法（替换现有 Mono 占位实现），新增 POST /api/analysis/report 端点。

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/analysis/report` | POST | 基于多篇论文生成综述报告 |

---

## 上下文定位

| 涉及层级 | 模块 |
|----------|------|
| java_backend | `dto/request.ReportRequest`（新增） |
| java_backend | `AnalysisService`（扩展 — 替换 Mono 占位为同步编排） |
| java_backend | `AnalysisController`（扩展 — 新增 /report 端点） |

**已有可复用**：
- `task22 AnalysisService.analyzePaper` 7 步编排模式（画像 → 校验 → Session → savePending → AI → completeAnalysis）
- `task22 AnalysisController` POST /paper 端点模式
- `AgentClientService.analyzePaper(AgentRequest)` 同步调用 + 三级降级
- `AgentRequest`（含 paperIds List + analysisType + userId + userProfile + analysisId）
- `AnalysisType.REPORT` 枚举值（已存在）
- `AnalysisResultDTO.citations` 字段（List<Map<String, Object>>）
- `PaperAnalysisRequest` DTO 结构（参照模式）

---

## 涉及文件

| 操作 | 路径 | 说明 |
|------|------|------|
| 新增 | `dto/request/ReportRequest.java` | 综述生成请求 DTO（topic/paperIds/sessionId） |
| 修改 | `service/AnalysisService.java` | 新增 generateReport(userId, ReportRequest)，替换 Mono 占位 |
| 修改 | `controller/AnalysisController.java` | 新增 @PostMapping("/report") 端点 |
| 新增 | `test/service/AnalysisServiceReportTest.java` | generateReport 测试（正常/404/403/验证） |
| 修改 | `test/controller/AnalysisControllerTest.java` | 扩展 /report 端点测试 |

---

## 关键实现

### 1. ReportRequest DTO

```java
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ReportRequest {

    @NotBlank(message = "研究主题不能为空")
    @Size(max = 500, message = "研究主题长度不能超过500")
    private String topic;

    @NotEmpty(message = "论文列表不能为空，至少选择1篇论文")
    private List<@NotBlank String> paperIds;

    /** 可选；为空时新建 Session */
    private String sessionId;
}
```

### 2. AnalysisService.generateReport（替换 Mono 占位）

```java
/**
 * 综述生成入口（POST /api/analysis/report）。
 * <p>7 步编排（与 analyzePaper 类似，但 AnalysisType.REPORT + paperIds 列表验证）：
 * 1) 画像 → 2) 验证所有 paperIds 存在 → 3) resolveOrCreateSession →
 * 4) 生成 analysisId → 5) savePending(REPORT) → 6) agentClientService.analyzePaper →
 * 7) completeAnalysis + citations 校验
 */
public AnalysisTaskResponse generateReport(String userId, ReportRequest request) {
    log.info("generateReport start: userId={}, paperIds={}, topic={}",
            userId, request.getPaperIds().size(), truncate(request.getTopic(), 50));

    // 1) 用户画像
    UserProfileDTO userProfile = buildUserProfile(userId);

    // 2) 验证所有 paperIds 存在（任一不存在抛 404）
    for (String paperId : request.getPaperIds()) {
        paperService.getPaperDetail(paperId);  // 不存在抛 ResourceNotFoundException
    }

    // 3) Session 复用/创建
    String sessionId = resolveOrCreateSessionForReport(userId, request);

    // 4) 生成 analysisId
    String analysisId = "anl_" + UUID.randomUUID().toString().replace("-", "").substring(0, 12);

    // 5) 保存 AnalysisResult(PENDING, REPORT) — 短事务
    AnalysisResult pending = self.savePending(analysisId, sessionId, AnalysisType.REPORT);

    // 6) 调 AgentClientService.analyzePaper（事务外，长耗时）
    AgentRequest agentRequest = AgentRequest.builder()
            .topic(request.getTopic())
            .paperIds(request.getPaperIds())
            .userId(userId)
            .userProfile(userProfile)
            .analysisType(AnalysisType.REPORT)
            .analysisId(analysisId)
            .build();
    AnalysisResultDTO result = agentClientService.analyzePaper(agentRequest);

    // 7) 更新 AnalysisResult + citations 校验
    if (result != null && result.getCitations() == null) {
        log.warn("综述报告引用列表为空: analysisId={}", analysisId);
    }
    return self.completeAnalysis(pending.getId(), result);
}
```

### 3. AnalysisController 新增端点

```java
@PostMapping("/report")
public ApiResponse<AnalysisTaskResponse> generateReport(
        @Valid @RequestBody ReportRequest request,
        @AuthenticationPrincipal String userId) {
    String currentUserId = userId != null ? userId : extractCurrentUserId();
    if (currentUserId == null || currentUserId.isBlank()) {
        throw new AuthenticationException("未认证，请先登录");
    }
    log.info("REST generateReport: userId={}, topic={}, paperCount={}",
            currentUserId, request.getTopic(), request.getPaperIds().size());
    AnalysisTaskResponse response = analysisService.generateReport(currentUserId, request);
    return ApiResponse.success(response);
}
```

---

## API 契约

### POST /api/analysis/report

**Request:**
```json
{
  "topic": "大语言模型综述",
  "paperIds": ["arxiv_2024_001", "arxiv_2024_002", "arxiv_2024_003"],
  "sessionId": "ses_xxx"  // 可选
}
```

**Response:**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "analysisId": "anl_a1b2c3d4e5f6",
    "status": "COMPLETED",
    "message": "综述生成完成",
    "createdAt": "2026-06-08T10:30:00"
  },
  "timestamp": "2026-06-08T10:30:00"
}
```

**Error:**
- 400: topic 为空 / paperIds 为空
- 401: 未认证
- 403: sessionId 属于他人
- 404: paperId 不存在

---

## 禁止行为

- ❌ generateReport 方法加 @Transactional 覆盖 AI 调用（长事务约束）
- ❌ Controller 直接调 AgentClientService 或 Repository（分层约束）
- ❌ 返回 Entity 给前端（必须 DTO 转换）
- ❌ 忽略 paperIds 中不存在的论文（必须 404）
- ❌ ReportRequest 不做 paperIds 数量上限校验（防止滥用）
- ❌ 保留 AgentClientService.generateReport(AgentRequest) Mono 占位方法

---

## 测试要求

| 测试名 | 覆盖 |
|--------|------|
| `generateReport_normal_flow_returns_task_response` | 3 篇论文正常流程 |
| `generateReport_paperId_not_found_throws404` | paperId 不存在 |
| `generateReport_analysisType_is_REPORT` | AgentRequest 字段验证 |
| `generateReport_reuse_session` | 复用已有 Session |
| `generateReport_other_user_session_returns403` | 数据隔离 |
| `reportRequest_validation_blank_topic` | topic 为空 → 400 |
| `reportRequest_validation_empty_paperIds` | paperIds 为空 → 400 |
| `generateReport_citations_empty_warns` | citations 为空时 warn |

**验证命令**：
```bash
# 单元测试
cd Veritas/backend && mvn -Dtest='AnalysisServiceReportTest' test

# 端点测试
cd Veritas/backend && mvn -Dtest='AnalysisControllerTest#generateReport*' test

# 手动验证
curl -s -X POST http://localhost:8080/api/analysis/report \
  -H 'Authorization: Bearer {jwt}' \
  -H 'Content-Type: application/json' \
  -d '{"topic":"LLM综述","paperIds":["pid1"]}' | jq .
```

---

## 验收标准

- [ ] ReportRequest DTO 含 topic(@NotBlank, max500) + paperIds(@NotEmpty) + sessionId(可选)
- [ ] generateReport 7 步编排完整执行，AnalysisType.REPORT 正确传入
- [ ] POST /api/analysis/report JWT 认证 + 数据隔离
- [ ] paperIds 中任一论文不存在 → 404
- [ ] 综述结果 citations 非空时 log.info，为空时 log.warn
- [ ] AgentClientService.generateReport(AgentRequest) Mono 占位方法已移除
- [ ] 8+ 个 generateReport 测试全部通过

---

## 下一步（JM4 Day 5-6）

### task27: PythonAIClient SSE 接收扩展
- 新增 compareStream / reportStream 方法
- 408 超时事件处理
- AgentClientService compareStream / reportStream 包装

### JM4 后续
- **JM4 Day 7-8**: AgentController（独立控制器，对比/综述 SSE 端点）
- **JM4 Day 9-10**: SSE 前端集成 + JM4 验收

---

## 未来建议 / 补充

1. **建议 ReportRequest.paperIds 增加 @Size(max=20)**：防止一次传入过多论文导致 AI 调用超时/Token 爆炸；JM6 性能优化时可根据实测调整
2. **建议 generateReport 支持异步模式**：当前为同步阻塞（agentClientService.analyzePaper），综述生成可能 30s+；JM5 可改为 SSE 流式推送
3. **建议 citations 校验增强**：当前仅 log.warn，未来可增加 citations 数量下限校验（如至少 3 条引用）作为质量门控
4. **建议 AgentRequest 增加 paperCount 字段**：Python 端可根据 paperCount 选择不同的 Prompt 策略（单篇 vs 多篇 vs 综述）
5. **跨系统字段命名**：ReportRequest 作为前端→Java DTO 使用 camelCase；AgentRequest 作为 Java→Python DTO 使用 @JsonProperty 覆盖全局 SNAKE_CASE