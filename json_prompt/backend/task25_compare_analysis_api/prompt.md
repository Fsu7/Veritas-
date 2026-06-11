# task25: 对比分析 API + CompareRequest (JM4 Week 7 Day 3)

> **里程碑**：M4：多Agent协同完成 / **JM4 Week 7 Day 3**：对比分析 API
> **版本**：v0.4
> **优先级**：P0
> **功能编号**：F4.1.2, F4.1.3

---

## 任务概述

实现对比分析 API，支持 2-5 篇论文的对比分析。新建 `CompareRequest` DTO，扩展 `AnalysisService.comparePapers()` 方法，新增 `POST /api/analysis/compare` 端点。

| 变更 | 说明 |
|------|------|
| 新建 `CompareRequest` | DTO：topic(必填,max500) + paperIds(必填,2-5个) + sessionId(可选) |
| 修改 `AnalysisService` | comparePapers() 从骨架替换为完整编排 |
| 修改 `AnalysisController` | 新增 POST /api/analysis/compare 端点 |

---

## 上下文定位

| 涉及层级 | 模块 |
|----------|------|
| java_backend | `dto/request.CompareRequest`（新增） |
| java_backend | `AnalysisService`（扩展 comparePapers） |
| java_backend | `AnalysisController`（新增 /compare 端点） |

**已有可复用**：
- `task24 AnalysisService`：含 transactionService 注入 + comparePapers 骨架
- `AnalysisTransactionService`：savePending() + completeAnalysis() 事务方法
- `PaperAnalysisRequest` DTO 风格参考（@NotBlank/@Size + @Builder + @Data）
- `AnalysisController.analyzePaper` 端点模式（JWT + @Valid + @AuthenticationPrincipal）
- `PaperService.getPaperDetail(paperId)` 论文存在性校验
- `AgentClientService.analyzePaper(AgentRequest)` Agent 调用

---

## 涉及文件

| 操作 | 路径 | 说明 |
|------|------|------|
| 新增 | `dto/request/CompareRequest.java` | 对比分析请求 DTO |
| 修改 | `service/AnalysisService.java` | comparePapers() 完整实现 |
| 修改 | `controller/AnalysisController.java` | 新增 /compare 端点 |
| 新增 | `test/dto/request/CompareRequestValidationTest.java` | DTO 校验测试 |
| 修改 | `test/service/AnalysisServiceTest.java` | comparePapers 测试 |
| 修改 | `test/controller/AnalysisControllerTest.java` | /compare 端点测试 |

---

## 关键实现

### 1. CompareRequest DTO

```java
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CompareRequest {

    @NotBlank(message = "研究主题不能为空")
    @Size(max = 500, message = "研究主题长度不能超过500")
    private String topic;

    @NotNull(message = "论文ID列表不能为空")
    @Size(min = 2, max = 5, message = "对比论文数量必须在2-5篇之间")
    private List<String> paperIds;

    /** 可选；为空时新建 Session */
    private String sessionId;
}
```

### 2. AnalysisService.comparePapers() 完整编排

```java
/**
 * 对比分析入口（POST /api/analysis/compare）。
 * <p>8 步编排：1) 画像 → 2) 验证所有 paperIds 存在 → 3) Session 复用/创建 →
 * 4) 生成 analysisId → 5) savePending(COMPARE) → 6) 构建 AgentRequest →
 * 7) 调 AgentClientService → 8) completeAnalysis。
 */
public AnalysisTaskResponse comparePapers(String userId, CompareRequest request) {
    log.info("comparePapers start: userId={}, paperIds={}, topic={}",
            userId, request.getPaperIds(), truncate(request.getTopic(), 50));

    // 1) 用户画像（不抛错，缺失时用默认）
    UserProfileDTO userProfile = buildUserProfile(userId);

    // 2) 验证所有 paperIds 对应论文存在（任一不存在抛 404）
    List<PaperDetailResponse> papers = new ArrayList<>();
    for (String paperId : request.getPaperIds()) {
        papers.add(paperService.getPaperDetail(paperId));  // 不存在抛 ResourceNotFoundException
    }
    log.debug("papers validated: count={}", papers.size());

    // 3) Session 复用/创建
    String sessionId = resolveOrCreateSession(userId, request);

    // 4) 生成 analysisId
    String analysisId = "anl_" + UUID.randomUUID().toString().replace("-", "").substring(0, 12);

    // 5) 保存 AnalysisResult(PENDING) — 短事务
    AnalysisResult pending = transactionService.savePending(analysisId, sessionId, AnalysisType.COMPARE);

    // 6) 构建 AgentRequest（paperIds=完整列表, analysisType=COMPARE）
    AgentRequest agentRequest = AgentRequest.builder()
            .topic(request.getTopic())
            .paperIds(request.getPaperIds())     // 完整论文ID列表
            .userId(userId)
            .userProfile(userProfile)
            .analysisType(AnalysisType.COMPARE)
            .analysisId(analysisId)
            .build();

    // 7) 调 AgentClientService.analyzePaper（事务外，长耗时）
    AnalysisResultDTO result = agentClientService.analyzePaper(agentRequest);

    // 8) 更新 AnalysisResult 状态 + result JSON — 短事务
    return transactionService.completeAnalysis(pending.getId(), result);
}
```

### 3. AnalysisController 新增端点

```java
/**
 * 对比分析入口（POST /api/analysis/compare）。
 * <p>JWT 鉴权 → 参数校验 → AnalysisService.comparePapers。
 */
@PostMapping("/compare")
public ResponseEntity<ApiResponse<AnalysisTaskResponse>> comparePapers(
        @Valid @RequestBody CompareRequest request,
        @AuthenticationPrincipal String userId) {
    String currentUserId = userId != null ? userId : extractCurrentUserId();
    if (currentUserId == null || currentUserId.isBlank()) {
        throw new AuthenticationException("未认证，请先登录");
    }
    log.info("REST comparePapers: userId={}, paperIds={}", currentUserId, request.getPaperIds());
    AnalysisTaskResponse response = analysisService.comparePapers(currentUserId, request);
    return ResponseEntity.status(HttpStatus.ACCEPTED).body(ApiResponse.success(response));
}
```

---

## API 契约

### POST /api/analysis/compare

**Request**:
```json
{
  "topic": "对比Transformer与RNN在NLP中的表现",
  "paper_ids": ["arxiv_2024_001", "arxiv_2024_002"],
  "session_id": "ses_a1b2c3d4"
}
```

**Response** (202 ACCEPTED):
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "analysis_id": "anl_abcdef012345",
    "status": "PENDING",
    "message": "分析完成",
    "created_at": "2026-06-08T10:00:00"
  }
}
```

**错误响应**:
| 场景 | HTTP 状态 | code | 说明 |
|------|-----------|------|------|
| 未登录 | 401 | 401 | JWT 缺失 |
| topic 为空 | 400 | 400 | @Valid 校验失败 |
| paperIds < 2 或 > 5 | 400 | 400 | @Size 校验失败 |
| paperId 不存在 | 404 | 404 | ResourceNotFoundException |
| 他人 sessionId | 403 | 403 | BusinessException |

---

## 编排流程对比

```mermaid
graph LR
    subgraph analyzePaper
        A1[画像] --> A2[单论文校验] --> A3[Session] --> A4[savePending<br/>PAPER_ANALYSIS] --> A5[AgentRequest<br/>paperIds=[1个]] --> A6[callAI] --> A7[completeAnalysis]
    end
    subgraph comparePapers
        C1[画像] --> C2[多论文校验<br/>2-5个] --> C3[Session] --> C4[savePending<br/>COMPARE] --> C5[AgentRequest<br/>paperIds=[2-5个]] --> C6[callAI] --> C7[completeAnalysis]
    end
```

---

## 禁止行为

- ❌ 修改 analyzePaper 编排逻辑
- ❌ CompareRequest 中 paperIds 使用 @NotBlank（应使用 @NotNull + @Size）
- ❌ Controller 直接调用 PaperService 或 AnalysisTransactionService
- ❌ 在 comparePapers 中跳过论文存在性校验
- ❌ 返回 Entity 给前端
- ❌ 修改 AnalysisTransactionService 代码

---

## 测试要求

| 测试名 | 覆盖 |
|--------|------|
| `compareRequest_paperIds_too_few_validation_fails` | 边界（1个 paperId） |
| `compareRequest_paperIds_too_many_validation_fails` | 边界（6个 paperId） |
| `compareRequest_topic_blank_validation_fails` | 错误（空 topic） |
| `comparePapers_normal_flow_completes` | 正常流程 |
| `comparePapers_paperId_not_found_throws404` | 错误（论文不存在） |
| `comparePapers_session_isolation_throws403` | 错误（数据隔离） |
| `comparePapers_agentRequest_contains_all_paperIds` | 正常（AgentRequest 验证） |
| `compareController_success_returns202` | 端点测试 |

**验证命令**：
```bash
# 单元测试
cd Veritas/backend && mvn -Dtest='CompareRequestValidationTest,AnalysisServiceTest,AnalysisControllerTest' test

# 全量回归
cd Veritas/backend && mvn test
# 期望: 全部测试通过，0 失败
```

---

## 验收标准

- [ ] CompareRequest DTO 含 topic(@NotBlank,max500) + paperIds(@Size(min=2,max=5)) + sessionId(可选)
- [ ] comparePapers 编排 8 步完整执行，AgentRequest.paperIds 包含所有论文ID
- [ ] POST /api/analysis/compare 返回 202 + ApiResponse<AnalysisTaskResponse>
- [ ] paperIds 中任一论文不存在 → 404
- [ ] paperIds 数量不在 2-5 → 400
- [ ] JWT 认证 + 数据隔离（他人 sessionId → 403）
- [ ] 全部测试通过（含回归测试）

---

## 下一步（JM4 Day 4-5）

- **Day 4**: 实现 generateReport() 完整编排 + ReportRequest DTO + POST /api/analysis/report 端点
- **Day 5-10**: SSE 推送 + AgentController + PythonAIClient SSE 扩展

---

## 未来建议 / 补充

1. **建议 CompareRequest.paperIds 去重**：当前允许 paperIds 中包含重复 ID，建议在 Service 层或 DTO 层增加去重逻辑，避免同一论文重复对比
2. **建议增加对比分析超时策略**：对比分析涉及多篇论文，AI 处理时间可能超过单论文分析，建议 AgentClientService 为 COMPARE 类型设置更长的超时时间（如 60s vs 30s）
3. **建议 Python 端 AgentRequest 增加 paper_count 字段**：便于 Python 端根据论文数量动态调整 Agent 编排策略
4. **建议 CompareRequest 增加 language 可选字段**：未来支持多语言对比分析报告生成
