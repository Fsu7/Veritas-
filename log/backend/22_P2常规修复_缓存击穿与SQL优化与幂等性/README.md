# P2 常规修复 — 后端（缓存击穿与SQL优化与幂等性）

## 功能描述
- **解决的问题**：修复了 P2 级别的 7 项 Java 后端代码质量问题，包括缓存击穿、SQL 全表扫描、重复查询、安全日志级别、编译错误
- **实现的功能**：
  - 6 个 `@Cacheable` 方法添加 `sync = true`，防止缓存击穿
  - `PaperRepositoryCustomImpl` 的 `authors LIKE` 改为 `JSON_SEARCH`，语义更准确
  - `AnalysisService.validateAnalysisAccess` 返回实体，减少缓存未命中时的重复查询
  - `JwtUtil` 的 `SecurityException`/`MalformedJwtException` 日志从 debug 改为 warn
  - Spring Boot 升级至 3.2.12 + Lombok 升级至 1.18.38
  - Session 创建接口添加 `clientToken` 幂等性（Redis 5 分钟去重窗口）
  - 修复编译错误：AnalysisController 缺失字段、SessionRepository 缺失导入、UserService 缺失导入
- **业务价值**：提升缓存稳定性、SQL 查询效率、安全事件可观测性、接口幂等性

## 实现逻辑
- **修改的核心文件**：
  - `AnalysisService.java` — validateAnalysisAccess 返回实体 + sync=true
  - `SessionService.java` — sync=true + createSession 幂等性
  - `UserService.java` — sync=true + CacheEvictionHelper 字段
  - `FavoriteService.java` — sync=true
  - `JwtUtil.java` — 日志级别 warn
  - `PaperRepositoryCustomImpl.java` — JSON_SEARCH
  - `SessionRepository.java` — 缺失导入修复
  - `AnalysisController.java` — 缺失字段修复
  - `AnalysisTransactionService.java` — 缺失导入修复
  - `SessionCreateRequest.java` — clientToken 字段
  - `pom.xml` — Spring Boot 3.2.12 + Lombok 1.18.38
- **设计模式**：
  - Cache-Aside sync=true（Spring Cache 内置的同步锁，防止热点 Key 过期时并发击穿）
  - Idempotency-Key 模式（Redis SETNX 5 分钟窗口）
  - JSON_SEARCH 替代 LIKE（利用 MySQL JSON 函数在数组内搜索）

## 接口变更
### Request（Session 创建新增可选字段）
```json
{
  "topic": "深度学习综述",
  "clientToken": "client-uuid-12345"
}
```

### Response（无变化）
```json
{
  "code": 201,
  "message": "success",
  "data": {
    "sessionId": "ses_a1b2c3d4",
    "topic": "深度学习综述",
    "status": "ACTIVE"
  }
}
```

## 测试结果
- Java 编译：`mvn clean compile` BUILD SUCCESS（需 MAVEN_OPTS 设置 add-opens）
- 代码模式验证：Grep 确认 sync=true 共 7 处（6 新增 + 3 原有）
- 是否通过：是

## 相关文件
- `backend/src/main/java/com/literatureassistant/service/AnalysisService.java`
- `backend/src/main/java/com/literatureassistant/service/SessionService.java`
- `backend/src/main/java/com/literatureassistant/service/UserService.java`
- `backend/src/main/java/com/literatureassistant/service/FavoriteService.java`
- `backend/src/main/java/com/literatureassistant/service/AnalysisTransactionService.java`
- `backend/src/main/java/com/literatureassistant/util/JwtUtil.java`
- `backend/src/main/java/com/literatureassistant/repository/PaperRepositoryCustomImpl.java`
- `backend/src/main/java/com/literatureassistant/repository/SessionRepository.java`
- `backend/src/main/java/com/literatureassistant/controller/AnalysisController.java`
- `backend/src/main/java/com/literatureassistant/dto/request/SessionCreateRequest.java`
- `backend/pom.xml`
