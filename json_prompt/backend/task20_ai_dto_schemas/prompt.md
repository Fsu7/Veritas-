# task20: AI DTO 完善 — AgentRequest/AnalysisResultDTO/UserProfileDTO/AgentStateResponse/PaperSearchResultDTO/ModelStatusDTO (JM3 Day 6)

> **里程碑**：M3：前后端联调成功 / **JM3 Day 6**：AI 服务调用打通
> **版本**：v0.3
> **优先级**：P0
> **功能编号**：F2.5.1, F2.5.2, F2.5.3, F2.5.4

---

## 任务概述

完善 task19 占位的 2 个 DTO，并新增 4 个 DTO，建立 Java→Python 通信的**强类型契约层**。所有字段命名、必填、默认值必须严格对齐 Python Pydantic Schema（`app.models.schemas`）：

| DTO | 路径 | 字段数 | 对齐 Python Schema |
|-----|------|--------|---------------------|
| `AgentRequest`（完善） | `dto/common/AgentRequest.java` | 6 | `AnalyzeRequest` |
| `UserProfileDTO`（新增） | `dto/common/UserProfileDTO.java` | 4 | `UserProfile` |
| `AnalysisResultDTO`（完善） | `dto/response/AnalysisResultDTO.java` | 7 | `AnalyzeResponse` |
| `AgentStateResponse`（新增） | `dto/response/AgentStateResponse.java` | 5 | `AgentStateResponse` |
| `PaperSearchResultDTO`（新增） | `dto/response/PaperSearchResultDTO.java` | 6 | `SearchResultItem` |
| `ModelStatusDTO`（新增） | `dto/response/ModelStatusDTO.java` | 6 | `ModelStatusResponse` |

---

## 上下文定位

| 涉及层级 | 模块 |
|----------|------|
| java_backend | `com.literatureassistant.dto.common` / `com.literatureassistant.dto.response` |
| python_ai_service | `app.models.schemas`（契约真源） / `app.models.enums`（枚举真源） |

**已有可复用**：
- `AnalysisType` / `AnalysisStatus`（Java 枚举，dbValue 与 Python 枚举一致）
- `EducationLevel` / `KnowledgeLevel` / `PreferredStyle`（4 维度画像枚举）
- `ProfileResponse`（DTO 风格参考）
- 全局 Jackson SNAKE_CASE（依赖 `application.yml` 配置，**禁止 @JsonProperty 覆盖**）

---

## 字段映射契约（核心）

| Java camelCase | JSON snake_case | Python attr |
|----------------|------------------|-------------|
| `paperIds` | `paperIds` | `paper_ids` |
| `userId` | `userId` | `user_id` |
| `userProfile` | `userProfile` | `user_profile` |
| `analysisType` | `analysisType` | `analysis_type` |
| `analysisId` | `analysisId` | `analysis_id` |
| `educationLevel` | `educationLevel` | `education_level` |
| `researchField` | `researchField` | `research_field` |
| `knowledgeLevel` | `knowledgeLevel` | `knowledge_level` |
| `preferredStyle` | `preferredStyle` | `preferred_style` |
| `agentName` | `agentName` | `agent_name` |
| `intermediateResult` | `intermediateResult` | `intermediate_result` |
| `durationMs` | `durationMs` | `duration_ms` |
| `embeddingDimension` | `embeddingDimension` | `embedding_dimension` |
| `activeLlmProvider` | `activeLlmProvider` | `active_llm_provider` |

> ⚠️ Python 端 Pydantic v2 使用 `alias="camelCase" + populate_by_name=True`，因此 JSON 字段名是 camelCase（如 `paperIds`），但 Python 属性名是 snake_case（如 `paper_ids`）。Java 端依赖全局 Jackson SNAKE_CASE 配置自动完成转换。

---

## 涉及文件

| 操作 | 路径 | 说明 |
|------|------|------|
| 修改 | `Veritas/backend/src/main/java/com/literatureassistant/dto/common/AgentRequest.java` | 6 字段 + @NotBlank/@Size/@JsonProperty + @Valid |
| 修改 | `Veritas/backend/src/main/java/com/literatureassistant/dto/response/AnalysisResultDTO.java` | 7 字段 + 静态工厂 degraded() |
| 新增 | `Veritas/backend/src/main/java/com/literatureassistant/dto/common/UserProfileDTO.java` | 4 字段 + 4 枚举 |
| 新增 | `Veritas/backend/src/main/java/com/literatureassistant/dto/response/AgentStateResponse.java` | 5 字段 |
| 新增 | `Veritas/backend/src/main/java/com/literatureassistant/dto/response/PaperSearchResultDTO.java` | 6 字段 |
| 新增 | `Veritas/backend/src/main/java/com/literatureassistant/dto/response/ModelStatusDTO.java` | 6 字段 |
| 新增 | `Veritas/backend/src/test/java/com/literatureassistant/dto/AiDtoSerializationTest.java` | 6 个序列化/反序列化测试 |

---

## 关键实现要点

### AgentRequest 关键约束
```java
@NotBlank(message = "研究主题不能为空")
@Size(max = 500, message = "研究主题长度不能超过500")
private String topic;

@NotBlank(message = "用户ID不能为空")
private String userId;

@Builder.Default
private AnalysisType analysisType = AnalysisType.REPORT;

@Valid  // 触发嵌套校验
private UserProfileDTO userProfile;
```

### AnalysisResultDTO 静态工厂
```java
public static AnalysisResultDTO degraded(String analysisId, String reason) {
    return AnalysisResultDTO.builder()
        .analysisId(analysisId)
        .status(AnalysisStatus.FAILED)
        .degraded(true)
        .degradedReason(reason)
        .build();
}
```

---

## 禁止行为

- ❌ 在 DTO 字段加 `@JsonProperty`（破坏全局 SNAKE_CASE）
- ❌ 硬编码枚举字符串（必须用 Java 枚举引用）
- ❌ 省略 @NotBlank/@Size/@Valid
- ❌ DTO 中混入 Entity
- ❌ 自定义 toJson/fromJson 方法（依赖 Jackson 自动）

---

## 测试要求

| 测试名 | 覆盖 |
|--------|------|
| `agentRequest_serialization_to_python_format` | Java→JSON 字段名一致 |
| `agentRequest_deserialization_from_python` | JSON→Java 反序列化 |
| `analysisResultDTO_status_enum_mapping` | 4 个 status 字符串映射 |
| `agentStateResponse_field_alias` | 5 字段映射 |
| `userProfileDTO_enum_default_values` | 枚举默认值 |
| `agentRequest_validation_blank_topic` | 字段约束生效 |

**验证命令**：
```bash
cd Veritas/backend && mvn -Dtest=AiDtoSerializationTest test
```

---

## 验收标准

- [ ] 6 个 DTO 全部创建且编译通过
- [ ] 字段命名与 Python Schema 一致（已通过测试验证）
- [ ] @NotBlank/@Size/@Valid 字段约束生效
- [ ] `AiDtoSerializationTest` 6/6 通过
- [ ] 未添加 @JsonProperty 覆盖全局配置

---

## 下一步

- **task21**：构建 `AgentClientService`（基于本 task 的 DTO + task19 的 PythonAIClient，添加降级处理 + Redis 缓存）
- **task22**：构建 `AnalysisController` + `AnalysisService.analyzePaper`（使用本 task 的 AgentRequest / AnalysisResultDTO）
