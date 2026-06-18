# 三层全栈评估 P0-P2 修复 — Java 后端

## 功能描述

### 解决了什么问题
基于《三层全栈综合技术评估报告-2026-06-18》指出的 Java 后端问题，系统性修复了以下阻断性与建议性缺陷：
- **P0-1 Redis RCE 漏洞**：`LaissezFaireSubTypeValidator` 允许反序列化任意类型，存在远程代码执行风险
- **P0-2 密码硬编码**：`application.yml` 中 MySQL 密码明文硬编码
- **P0-3 测试密码硬编码**：`application-test.yml` 中测试密码明文硬编码
- **P0-4 ddl-auto 危险配置**：`ddl-auto: update` 在生产环境可能意外修改表结构
- **P0-5 SSE 跨块解析缺陷**：`bodyToFlux(byte[].class)` + 手动 `splitSseEvents` 无法正确处理跨 TCP 块的 SSE 事件
- **P1-1 参数校验异常未处理**：`ConstraintViolationException` 未被全局异常处理器捕获
- **P1-2 JPA Entity 使用 @Data**：`@Data` 生成全字段 `equals/hashCode`，可能导致延迟加载触发和性能问题
- **P2-1 缓存全空间清空**：`@CacheEvict(allEntries=true)` 清空整个缓存空间，影响其他用户
- **P2-2 SQL DEBUG 日志**：生产环境打印 SQL 语句，性能与安全风险

### 实现了什么功能
1. Redis 反序列化白名单验证器，仅允许 `com.literatureassistant.`、`java.util.`、`java.time.`、`java.lang.` 包类型
2. 密码改为环境变量 `${MYSQL_PASSWORD:CHANGE_ME}` 占位
3. `ddl-auto` 改为 `validate`，仅校验不修改表结构
4. SSE 解析改用 Spring 内置 `ServerSentEventHttpMessageReader`，自动处理跨块分片
5. 新增 `ConstraintViolationException` 异常处理器，返回 400 + 字段级错误信息
6. 4 个 Entity 的 `@Data` 替换为 `@Getter/@Setter/@EqualsAndHashCode(onlyExplicitlyIncluded = true)`
7. 新建 `CacheEvictionHelper`，使用 SCAN 按用户前缀精准失效缓存
8. SQL 日志级别从 DEBUG 降为 WARN

### 业务价值
- 修复 Redis RCE 漏洞，消除远程代码执行风险
- 密码环境变量化，支持容器化部署的安全凭证管理
- `ddl-auto: validate` 防止生产环境意外表结构变更
- SSE 解析可靠性提升，消除跨块事件丢失
- 缓存精准失效避免用户间缓存互相影响
- SQL 日志降级避免敏感信息泄露和性能损耗

## 实现逻辑

### 修改的核心文件列表
| 文件 | 修复项 | 变更说明 |
|------|--------|----------|
| `config/RedisConfig.java` | P0-1 | `LaissezFaireSubTypeValidator` → `BasicPolymorphicTypeValidator` 白名单 |
| `resources/application.yml` | P0-2, P0-4, P2-2 | 密码环境变量化；`ddl-auto: validate`；SQL 日志 WARN |
| `test/resources/application-test.yml` | P0-3 | 测试密码环境变量化 |
| `client/PythonAIClient.java` | P0-5 | `bodyToFlux(String.class)` + `bufferUntil` → `bodyToFlux(ServerSentEvent.class)` |
| `exception/GlobalExceptionHandler.java` | P1-1 | 新增 `ConstraintViolationException` 处理器 |
| `entity/Paper.java` | P1-2 | `@Data` → `@Getter/@Setter/@EqualsAndHashCode(onlyExplicitlyIncluded)` |
| `entity/Session.java` | P1-2 | 同上 |
| `entity/AnalysisResult.java` | P1-2 | 同上 |
| `entity/PaperFavorite.java` | P1-2 | 同上 |
| `cache/CacheEvictionHelper.java` | P2-1 | 新建，SCAN + 按前缀精准失效 |
| `service/SessionService.java` | P2-1 | 移除 `@CacheEvict(allEntries=true)`，改用 `CacheEvictionHelper` |
| `service/FavoriteService.java` | P2-1 | 同上 |

### 使用的算法或设计模式
- **白名单验证器模式**：`BasicPolymorphicTypeValidator` 限制可反序列化的类型范围
- **环境变量占位模式**：`${VAR:default}` 支持环境变量注入与默认值兜底
- **委托模式**：SSE 解析委托给 Spring 内置 `ServerSentEventHttpMessageReader`
- **写后删模式（Cache-Aside）**：`evictByPatternAfterCommit` 在事务提交后清除缓存，避免脏读回填
- **SCAN 迭代模式**：使用 Redis SCAN 命令分批扫描 key，避免 KEYS 阻塞

### 关键代码逻辑说明

#### P0-1 Redis 反序列化白名单
```java
om.activateDefaultTyping(
    BasicPolymorphicTypeValidator.builder()
        .allowIfSubType("com.literatureassistant.")
        .allowIfSubType("java.util.")
        .allowIfSubType("java.time.")
        .allowIfSubType("java.lang.")
        .build(),
    ObjectMapper.DefaultTyping.NON_FINAL,
    JsonTypeInfo.As.PROPERTY);
```

#### P0-5 SSE 解析（ServerSentEvent）
```java
return bodySpec
    .bodyValue(request)
    .retrieve()
    .bodyToFlux(ServerSentEvent.class)  // Spring 内置 SSE 解析器
    .map(this::convertServerSentEvent)
    .filter(e -> e.getEvent() != null || e.getData() != null)
    .flatMap(this::transformTimeoutEvents)
    .timeout(Duration.ofSeconds(SSE_RESPONSE_TIMEOUT_SECONDS));
```

#### P2-1 缓存精准失效
```java
// CacheEvictionHelper
public void evictByPatternAfterCommit(String pattern) {
    if (TransactionSynchronizationManager.isSynchronizationActive()) {
        TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
            @Override
            public void afterCommit() {
                evictByPattern(pattern);  // 事务提交后清除
            }
        });
    } else {
        evictByPattern(pattern);  // 无事务直接清除
    }
}
```

## 接口变更

### Request
本次修复未改变 API 请求契约。

### Response
`ConstraintViolationException` 异常响应格式变更（P1-1）：
```json
{
  "code": 400,
  "message": "userId: must not be blank; paperId: must not be blank",
  "data": null,
  "timestamp": "2026-06-18T10:30:00"
}
```

## 测试结果
- **全量测试**：445 个测试全部通过（需设置 `MYSQL_TEST_PASSWORD` 环境变量）
- **缓存相关测试**：53 个测试通过（SessionCacheTest/SessionServiceTest/FavoriteServiceTest/CacheConsistencyTest/CachePenetrationAvalancheTest）
- **SSE 测试**：PythonAIClientTest 13 个测试全部通过
- **状态机测试**：SessionStateMachineTest 13 个测试全部通过
- 是否通过：是

## 相关文件
- `Veritas/backend/src/main/java/com/literatureassistant/config/RedisConfig.java`
- `Veritas/backend/src/main/resources/application.yml`
- `Veritas/backend/src/test/resources/application-test.yml`
- `Veritas/backend/src/main/java/com/literatureassistant/client/PythonAIClient.java`
- `Veritas/backend/src/main/java/com/literatureassistant/exception/GlobalExceptionHandler.java`
- `Veritas/backend/src/main/java/com/literatureassistant/entity/{Paper,Session,AnalysisResult,PaperFavorite}.java`
- `Veritas/backend/src/main/java/com/literatureassistant/cache/CacheEvictionHelper.java`（新建）
- `Veritas/backend/src/main/java/com/literatureassistant/service/{SessionService,FavoriteService}.java`
- 评估报告：`log/阶段审阅报告/三层全栈综合技术评估报告-2026-06-18.md`
- 修复计划：`.trae/documents/全栈P0-P2问题修复计划-2026-06-18.md`
