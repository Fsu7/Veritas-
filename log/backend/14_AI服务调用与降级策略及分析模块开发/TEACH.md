# 技术教学文档 — AI服务调用与降级策略及分析模块

---

## 开发思路

### 需求分析过程

本次开发覆盖 JM3 里程碑全部5个任务（task19-23），目标是从零打通 Java 后端到 Python AI 服务的全链路调用：

1. **task19 PythonAIClient**：底层HTTP客户端，封装 WebClient 调用
2. **task20 AI DTO Schemas**：定义跨系统数据传输对象，对齐 Python Pydantic Schema
3. **task21 AgentClientService**：编排层，添加降级策略和缓存
4. **task22 AnalysisController/Service**：业务层，暴露分析端点+任务编排
5. **task23 查询端点+健康扩展**：提供分析结果查询能力和AI服务状态监控

### 技术选型考虑

- **WebClient 而非 RestTemplate**：Spring Boot 3.2+ 异步首选，为 JM4 SSE 扩展预留
- **Redis Hash 存储 Agent 状态**：支持单Agent独立更新，避免重复序列化开销
- **@Cacheable 而非手动缓存**：利用 Spring Cache 抽象，统一 TTL 和失效策略
- **@JsonValue 而非 @JsonProperty**：枚举序列化用 dbValue，全局生效无需逐个字段标注

### 架构设计思路

```
Controller → AnalysisService → AgentClientService → PythonAIClient → Python AI
                ↓                    ↓
          AnalysisResult(DB)    Redis(agent:state + analysis:result)
```

- Controller 层：参数校验 + JWT鉴权 + userId提取
- Service 层：业务编排 + 事务控制 + 数据隔离
- Client 层：HTTP调用 + 超时重试 + 异常转换

---

## 实现步骤

### 第1步：PythonAIClient（task19）
- 创建 `client/PythonAIClient.java`，注入 `WebClient`（WebClientConfig已配置）
- 实现 `analyze(AgentRequest)`：POST `/api/agent/analyze`，30s超时，重试1次（间隔3s）
- 实现 `search(query, topK, filters)`：POST `/api/search/`
- 实现 `isHealthy()`：GET `/health`，5s独立超时，不抛异常只返回 boolean
- 实现 `getModelStatus()`：GET `/api/model/status`
- 异常转换：WebClientResponseException/IOException → AIServiceException(503)

### 第2步：AI DTO Schemas（task20）
- `AgentRequest`：对齐 Python `AnalyzeRequest`，6字段 + @Valid校验
- `AnalysisResultDTO`：对齐 Python `AnalyzeResponse`，7字段 + `degraded()` 静态工厂
- `AgentStateResponse`：单Agent状态，5字段（agentName/status/progress/intermediateResult/durationMs）
- `UserProfileDTO`：用户画像，4维度（educationLevel/researchField/knowledgeLevel/preferredStyle）
- `ModelStatusDTO`：LLM状态，6字段
- `PaperSearchResultDTO`：搜索结果项，6字段

### 第3步：AgentClientService（task21）
- 实现 `analyzePaper(AgentRequest)`：调用 PythonAIClient → 成功写Redis → 失败走降级
- 降级逻辑：查 `agent:fallback:{id}` Redis缓存 → 命中返回cached+degraded=true → 未命中返回degraded DTO
- 实现 `updateAgentState/getAgentStates`：Redis Hash 结构，TTL=5min
- 实现 `cacheAnalysisResult`：Redis String，TTL=30min
- 预留 `generateReport(Mono)`：JM4 SSE 扩展入口

### 第4步：AnalysisController + AnalysisService（task22）
- `AnalysisService.analyzePaper` 7步编排：
  1. 调用 userService.getProfile 获取画像
  2. 调用 paperService.getPaperDetail 校验论文
  3. 解析/创建 Session
  4. 生成 analysisId（`anl_` + UUID前12位）
  5. `@Transactional savePending()` 保存 PENDING 记录
  6. 调用 agentClientService.analyzePaper（事务外）
  7. `@Transactional completeAnalysis()` 更新状态+result JSON
- 数据隔离：复用 Session 时校验 userId 一致性，否则 403
- 事务边界：AI调用30s不在 @Transactional 内，避免长事务锁行

### 第5步：查询端点+健康扩展（task23）
- `AnalysisService.getAnalysisResult`：@Cacheable 30min，反序列化result JSON → AnalysisResponse
- `AnalysisService.getAnalysisStatus`：不缓存，实时读Redis Agent状态 + 计算progress/currentAgent
- `AnalysisController` 新增 GET `/{analysisId}` 和 `/{analysisId}/status`
- `HealthController` 注入 AgentClientService，新增 aiService 字段
- 整体 status 逻辑：mysql/redis/aiService 全UP→UP，任一DOWN→DOWN

---

## 解决了什么问题

### 核心问题

| 问题 | 解决方案 |
|------|----------|
| Java→Python跨系统JSON字段命名不一致 | 全局 Jackson SNAKE_CASE + 枚举 @JsonValue |
| AI服务不可用时系统仍要可用 | 三级降级：正常→缓存回退→degraded DTO |
| 30s AI调用阻塞DB连接池 | @Transactional 仅覆盖DB写入，AI调用在事务外 |
| 枚举序列化为大写不符合API契约 | @JsonValue 注解使序列化使用dbValue（小写） |
| 数据隔离（他人分析结果不可见） | validateDataIsolation() 校验 sessionId→userId |
| Agent状态实时性要求 | getAnalysisStatus 不缓存，每次实时查Redis Hash |

### 最终方案的优势

- **高可用**：Python服务宕机不影响用户获取历史缓存结果
- **可观测**：/health 端点可监控三层（MySQL/Redis/AI）状态
- **可扩展**：generateReport(Mono) 为 SSE 实时推送预留入口
- **规范统一**：所有API返回 `{code, message, data, timestamp}` 格式

---

## 变更内容

### 新增文件（19个源文件 + 对应测试）

| 层 | 文件 | 作用 |
|----|------|------|
| client | `PythonAIClient.java` | HTTP调用封装 |
| dto/common | `AgentRequest.java`, `UserProfileDTO.java` | 请求DTO |
| dto/response | `AnalysisResultDTO.java`, `AgentStateResponse.java`, `ModelStatusDTO.java`, `PaperSearchResultDTO.java`, `AnalysisResponse.java`, `AnalysisStatusResponse.java`, `AnalysisTaskResponse.java` | 响应DTO |
| dto/request | `PaperAnalysisRequest.java` | 请求DTO |
| service | `AgentClientService.java`, `AnalysisService.java` | 业务服务 |
| controller | `AnalysisController.java` | REST控制器 |
| test | `PythonAIClientTest.java`, `AgentClientServiceTest.java`, `AnalysisServiceTest.java`, `AnalysisServiceQueryTest.java`, `AnalysisControllerTest.java` | 单元测试 |

### 修改文件（5个）

| 文件 | 变更 |
|------|------|
| `controller/HealthController.java` | 注入 AgentClientService，新增 aiService 字段 + checkAIService() |
| `test/controller/HealthControllerTest.java` | 从 @SpringBootTest 改为 @ExtendWith(MockitoExtension) 单元测试 |
| `enums/AnalysisStatus.java` | 添加 @JsonValue 注解保证小写序列化 |
| `enums/AnalysisType.java` | 添加 @JsonValue 注解保证 snake_case 序列化 |
| `dto/common/AgentRequest.java` | 移除错误的跨包 import |

### 配置变更

无新增配置。依赖已存在于：
- `RedisConfig.java`：`analysisResult` cache 30min TTL（已预配置）
- `application.yml`：`ai-service.url/timeout/retry-count/retry-interval`

---

## 关键技术点

### 1. 枚举序列化 @JsonValue
```java
@Getter
public enum AnalysisStatus implements DbValueEnum {
    COMPLETED("completed"),
    // ...
    @JsonValue  // Jackson 序列化使用 dbValue 而非 Enum.name()
    private final String dbValue;
}
// AnalysisStatus.COMPLETED → JSON: "completed"（非 "COMPLETED"）
```

### 2. 事务边界控制（自注入模式）
```java
@Service
public class AnalysisService {
    @Autowired @Lazy
    private AnalysisService self;  // 自注入使 @Transactional 生效

    public AnalysisTaskResponse analyzePaper(...) {
        // 6) AI调用 — 事务外
        AnalysisResultDTO result = agentClientService.analyzePaper(request);
        // 7) DB更新 — 通过 self 调用使 @Transactional 生效
        return self.completeAnalysis(pending.getId(), result);
    }
}
```

### 3. 三级降级策略
```java
public AnalysisResultDTO analyzePaper(AgentRequest request) {
    try {
        AnalysisResultDTO result = pythonAIClient.analyze(request);
        updateAgentState(...);     // Level 1: 正常
        cacheAnalysisResult(...);
        return result;
    } catch (AIServiceException e) {
        // Level 2: Redis缓存回退 或 Level 3: degraded DTO
        return handleFallback(request, e);
    }
}
```

### 4. progress 计算
```java
private Double calcProgress(List<AgentStateResponse> agentStates) {
    // agentStates 非空时取各 Agent progress 算术平均
    double sum = 0; int count = 0;
    for (AgentStateResponse s : agentStates) {
        if (s != null && s.getProgress() != null) {
            sum += s.getProgress(); count++;
        }
    }
    return count > 0 ? sum / count : null;
}
```

---

## 经验总结

### 开发过程中的收获

1. **@JsonValue vs toString()**：之前以为重写 `toString()` 就能控制 Jackson 序列化，实际上 Jackson 默认用 `Enum.name()`。必须在字段或 getter 上加 `@JsonValue` 才能生效。
2. **Spring事务代理限制**：同一个类内方法调用不走代理，`@Transactional` 不生效。通过 `@Lazy @Autowired self` 自注入解决。
3. **WebClient 的 blocking 调用**：虽然 WebClient 是响应式的，但 `.block()` 可以同步获取结果，适合当前不需要 SSE 的阶段。

### 踩过的坑

1. **HealthControllerTest 从集成测试改为单元测试**：原 `@SpringBootTest` 启动开销大且无法 Mock AgentClientService，改为 `MockMvcBuilders.standaloneSetup` 后简洁高效。
2. **跨包 import 残留**：AgentRequest 中 `import com.literatureassistant.dto.response.UserProfileDTO` 应删除（同包无需import），编译期才会发现。
3. **Enum name() vs dbValue**：DB 使用 Converter 存 dbValue，API 也需使用 dbValue 序列化，但 Jackson 默认用 name()。统一加 @JsonValue 解决。

### 最佳实践建议

1. 枚举统一实现 `DbValueEnum` 接口 + `@JsonValue` 注解，保证 DB 和 JSON 序列化一致
2. 长耗时操作（如AI调用）务必放在 @Transactional 外
3. 降级策略要逐级尝试，先缓存再兜底，避免直接返回错误
4. 查询类端点区分缓存（getAnalysisResult）和实时（getAnalysisStatus）
5. Health 端点应覆盖所有依赖服务，用于 K8s/Docker 健康探测
