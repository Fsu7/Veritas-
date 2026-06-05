# JM3 task22 修复 & task23 实施计划

> **版本**: v1.0  
> **日期**: 2026-06-04  
> **状态**: 待审批

---

## 1. 摘要

task19/task20/task21/task22 核心实现已完成，但 task22 的 AnalysisControllerTest 有 2 个测试失败（枚举序列化为大写而非小写）。本计划覆盖：
1. 修复 `AnalysisStatus` 枚举序列化 → 完成 task22 验收
2. 实施 task23 全部功能（查询端点 + DTO + Health扩展 + 7+ 测试）

---

## 2. 当前状态分析

### 2.1 已完成

| 任务 | 文件 | 测试数 | 状态 |
|------|------|--------|------|
| task19 | `PythonAIClient.java` / `PythonAIClientTest.java` | 7/7 | 通过 |
| task20 | `AgentRequest.java` / `AnalysisResultDTO.java` / `AgentStateResponse.java` / `UserProfileDTO.java` / `ModelStatusDTO.java` / `PaperSearchResultDTO.java` 等 | 6/6 | 通过 |
| task21 | `AgentClientService.java` / `AgentClientServiceTest.java` | 7/7 | 通过 |
| task22 | `AnalysisController.java` / `AnalysisService.java` / `PaperAnalysisRequest.java` / `AnalysisTaskResponse.java` | AnalysisServiceTest 6/6 通过, AnalysisControllerTest **2/5 失败** | 部分通过 |

### 2.2 失败根因

```
JSON path "$.data.status" expected:<completed> but was:<COMPLETED>
```

`AnalysisStatus` 枚举实现了 `toString()` 返回 `dbValue`（如 `"completed"`），但 Jackson 默认使用 `Enum.name()` 序列化（输出 `"COMPLETED"`）。

**API 契约要求**：状态值应为小写 `pending|processing|completed|failed|degraded`（与 Python snake_case 对齐）。

### 2.3 待实施（task23）

| 功能 | 描述 |
|------|------|
| `AnalysisService.getAnalysisResult` | `@Cacheable` 查 DB + 反序列化 result JSON |
| `AnalysisService.getAnalysisStatus` | 聚合 AnalysisResult.status + Redis Agent 状态 |
| `AnalysisController` 新增 GET 端点 | `GET /api/analysis/{id}` + `GET /api/analysis/{id}/status` |
| `HealthController` 扩展 | 集成 `agentClientService.isHealthy()`，增加 `aiService` 字段 |
| 新 DTO | `AnalysisResponse` + `AnalysisStatusResponse` |
| 新测试 | `AnalysisServiceQueryTest`(5) + `HealthControllerTest` 扩展(2) |

---

## 3. 修改计划

### 3.1 第1步：修复枚举序列化 → 完成 task22

**文件**: `Veritas/backend/src/main/java/com/literatureassistant/enums/AnalysisStatus.java`

**变更**：在 `dbValue` 字段添加 `@com.fasterxml.jackson.annotation.JsonValue`

```java
@JsonValue
private final String dbValue;
```

**文件**: `Veritas/backend/src/main/java/com/literatureassistant/enums/AnalysisType.java`

**变更**：同样在 `dbValue` 字段添加 `@JsonValue`（一致性）

**影响**：
- `AnalysisStatus.COMPLETED` → JSON: `"completed"`
- `AnalysisType.PAPER_ANALYSIS` → JSON: `"paper_analysis"`
- 这符合跨系统 snake_case 命名约定
- 需验证 `AnalysisResultDTO`（含 `AnalysisStatus` 字段）的序列化仍正常
- 需验证 `AiDtoSerializationTest` 仍通过

**验证**：
```bash
cd Veritas/backend && mvn -Dtest='AnalysisControllerTest' test  # 期望 5/5
```

### 3.2 第2步：实施 task23

#### 3.2.1 创建 AnalysisResponse DTO

**文件**: `Veritas/backend/src/main/java/com/literatureassistant/dto/response/AnalysisResponse.java`

**字段**：
| 字段 | 类型 | JSON名 | 说明 |
|------|------|--------|------|
| analysisId | String | analysis_id | 分析任务ID |
| sessionId | String | session_id | 所属会话ID |
| status | AnalysisStatus | status | 状态枚举 |
| type | AnalysisType | type | 分析类型 |
| result | AnalysisResultDTO | result | 嵌套反序列化结果 |
| createdAt | LocalDateTime | created_at | 创建时间 |

**注解**：`@Data @Builder @NoArgsConstructor @AllArgsConstructor @JsonInclude(NON_NULL)`

#### 3.2.2 创建 AnalysisStatusResponse DTO

**文件**: `Veritas/backend/src/main/java/com/literatureassistant/dto/response/AnalysisStatusResponse.java`

**字段**：
| 字段 | 类型 | JSON名 | 说明 |
|------|------|--------|------|
| analysisId | String | analysis_id | 分析任务ID |
| status | AnalysisStatus | status | 结果状态 |
| progress | Double | progress | 总体进度(0.0-1.0)，由agentStates平均计算 |
| currentAgent | String | current_agent | 当前执行中的Agent（status=running时第一个） |
| agentStates | List\<AgentStateResponse\> | agent_states | Agent实时状态列表 |

#### 3.2.3 扩展 AnalysisService（新增2个查询方法）

**文件**: `Veritas/backend/src/main/java/com/literatureassistant/service/AnalysisService.java`

**新增方法1**: `getAnalysisResult(String userId, String analysisId) -> AnalysisResponse`

- `@Cacheable(value = "analysisResult", key = "#analysisId", unless = "#result == null")`
- 通过 `analysisResultRepository.findByAnalysisId(analysisId)` 查 DB
- 校验数据隔离：查 `SessionRepository.findBySessionId` 比对 `userId`
- 不匹配 → `BusinessException(403)`
- 反序列化 `entity.getResult()` JSON 字符串 → `AnalysisResultDTO`
- 组装 `AnalysisResponse`

**新增方法2**: `getAnalysisStatus(String userId, String analysisId) -> AnalysisStatusResponse`

- **不缓存**（实时性要求，见 FA-023-01）
- 查 DB 获取 `AnalysisResult.status`
- 调用 `agentClientService.getAgentStates(analysisId)` 获取实时 Agent 状态
- 计算 `progress`：agentStates 非空时取各 `progress` 平均值
- 计算 `currentAgent`：agentStates 中首个 `status != "completed"` 的 agent
- 数据隔离：同 getAnalysisResult

#### 3.2.4 扩展 AnalysisController（新增2个GET端点）

**文件**: `Veritas/backend/src/main/java/com/literatureassistant/controller/AnalysisController.java`

**新增端点1**: `GET /api/analysis/{analysisId}`
```java
@GetMapping("/{analysisId}")
public ResponseEntity<ApiResponse<AnalysisResponse>> getAnalysisResult(
    @PathVariable String analysisId,
    @AuthenticationPrincipal String userId)
```

**新增端点2**: `GET /api/analysis/{analysisId}/status`
```java
@GetMapping("/{analysisId}/status")
public ResponseEntity<ApiResponse<AnalysisStatusResponse>> getAnalysisStatus(
    @PathVariable String analysisId,
    @AuthenticationPrincipal String userId)
```

两者都需要 JWT 鉴权 + userId 提取逻辑（复用现有 `extractCurrentUserId()` 模式）。

#### 3.2.5 扩展 HealthController

**文件**: `Veritas/backend/src/main/java/com/literatureassistant/controller/HealthController.java`

**变更**：
- 注入 `AgentClientService agentClientService`（构造函数注入）
- `health()` 方法中调用 `agentClientService.isHealthy()` → `aiService` 字段
- 整体 `status` 逻辑扩展为：`mysql/redis/aiService` 全 UP → UP；任一 DOWN → DOWN

#### 3.2.6 创建 AnalysisServiceQueryTest（5个测试）

**文件**: `Veritas/backend/src/test/java/com/literatureassistant/service/AnalysisServiceQueryTest.java`

| 测试 | 覆盖 |
|------|------|
| `getAnalysisResult_returns_dto_with_deserialized_result` | normal_flow |
| `getAnalysisResult_uses_cache_second_call` | normal_flow, boundary |
| `getAnalysisResult_other_user_returns403` | error_flow |
| `getAnalysisStatus_aggregates_agent_states` | normal_flow |
| `getAnalysisStatus_empty_agents_progress_null` | boundary_condition |

#### 3.2.7 扩展 HealthControllerTest（2个新测试）

**文件**: `Veritas/backend/src/test/java/com/literatureassistant/controller/HealthControllerTest.java`

现有 3 个测试已覆盖 MySQL/Redis 检查。需新增 2 个测试覆盖 aiService：
| 测试 | 覆盖 |
|------|------|
| `healthController_includes_aiService_field` | normal_flow（Mock isHealthy=true → UP） |
| `healthController_python_down_returns_DOWN` | degradation（Mock isHealthy=false → DOWN） |

**注意**：现有 HealthControllerTest 使用 `@SpringBootTest` + `@AutoConfigureMockMvc`（集成测试方式），需要 Mock AgentClientService。最简单的方式是改用单元测试（`@ExtendWith(MockitoExtension.class)` + `MockMvcBuilders.standaloneSetup`），或使用 `@MockBean`。

---

## 4. 关键决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 枚举序列化修复方式 | `@JsonValue` 注解 | 最小改动，不影响现有 Converter（DB读写） |
| getAnalysisStatus 缓存 | 不缓存 | FA-023-01 禁止缓存 Agent 状态，实时性要求 |
| HealthControllerTest 方式 | 改用单元测试（Mockito + standaloneSetup） | 避免 Spring 容器启动开销，更容易 Mock AgentClientService |
| result JSON 反序列化 | `objectMapper.readValue(resultStr, AnalysisResultDTO.class)` | 复用已有 ObjectMapper 配置 |
| progress 计算 | agentStates 中 progress 字段算术平均 | prompt 明确要求（FR-023-03） |

---

## 5. 文件清单

| 操作 | 文件路径 |
|------|----------|
| **修改** | `Veritas/backend/src/main/java/com/literatureassistant/enums/AnalysisStatus.java` |
| **修改** | `Veritas/backend/src/main/java/com/literatureassistant/enums/AnalysisType.java` |
| **修改** | `Veritas/backend/src/main/java/com/literatureassistant/service/AnalysisService.java` |
| **修改** | `Veritas/backend/src/main/java/com/literatureassistant/controller/AnalysisController.java` |
| **修改** | `Veritas/backend/src/main/java/com/literatureassistant/controller/HealthController.java` |
| **新建** | `Veritas/backend/src/main/java/com/literatureassistant/dto/response/AnalysisResponse.java` |
| **新建** | `Veritas/backend/src/main/java/com/literatureassistant/dto/response/AnalysisStatusResponse.java` |
| **新建** | `Veritas/backend/src/test/java/com/literatureassistant/service/AnalysisServiceQueryTest.java` |
| **修改** | `Veritas/backend/src/test/java/com/literatureassistant/controller/HealthControllerTest.java` |

---

## 6. 验证命令

```bash
# 1. 编译检查
cd Veritas/backend && mvn clean compile

# 2. task22 修复验证
mvn -Dtest='AnalysisControllerTest,AnalysisServiceTest' test

# 3. task23 查询测试
mvn -Dtest='AnalysisServiceQueryTest' test

# 4. Health 测试
mvn -Dtest='HealthControllerTest' test

# 5. 全量回归
mvn test
```

**期望结果**：38+ 测试全部通过，BUILD SUCCESS。
