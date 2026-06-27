# 技术教学文档 — P2 常规修复（后端）

## 开发思路
- **需求分析**：根据 P2 修复清单，7 项 Java 后端问题分布在 11 个文件中，涉及缓存、SQL、安全日志、幂等性、编译错误修复
- **技术选型**：
  - 缓存击穿用 `sync = true`（Spring Cache 内置同步锁，比自定义分布式锁更简洁）
  - SQL 优化用 `JSON_SEARCH` 替代 `LIKE`（利用 MySQL JSON 函数，语义更准确）
  - 幂等性用 Redis SETNX 5 分钟窗口（标准 Idempotency-Key 模式）
  - Lombok 升级到 1.18.38 解决 JDK 25 兼容性
- **架构设计**：
  - `validateAnalysisAccess` 返回实体而非 void，供调用方复用减少重复查询
  - Session 幂等性提取 `doCreateSession` 私有方法，保持 createSession 入口逻辑清晰
- **遇到的问题**：
  - `--add-opens` 与 `--release` 冲突：fork 模式下 compilerArgs 中的 `--add-opens` 会被 javac 拒绝（"不允许在使用 --release 时从系统模块 java.base 导出程序包"），改为通过 MAVEN_OPTS 传递
  - Lombok 1.18.30（Spring Boot 3.2.12 自带）不支持 JDK 25，需显式指定 1.18.38
  - AnalysisController 使用了 idempotencyUtil 和 objectMapper 但未声明字段（@RequiredArgsConstructor 不会自动注入未声明的字段）
  - SessionRepository 使用了 @Lock/@Query/@Param 但未导入

## 实现步骤
1. 为 6 个 `@Cacheable` 方法添加 `sync = true`（AnalysisService、SessionService×2、UserService×2、FavoriteService）
2. `validateAnalysisAccess` 返回 `AnalysisResult` 实体，减少缓存未命中时重复查询
3. `PaperRepositoryCustomImpl` 的 `authors LIKE` 改为 `JSON_SEARCH(authors, 'one', CONCAT('%', ?5, '%')) IS NOT NULL`
4. `JwtUtil` 的 `SecurityException` 和 `MalformedJwtException` 日志从 debug 改为 warn
5. `SessionCreateRequest` 添加 `clientToken` 字段，`SessionService.createSession` 添加 Redis 幂等检查
6. pom.xml 升级 Spring Boot 3.2.5→3.2.12 + Lombok 显式指定 1.18.38
7. 修复编译错误：AnalysisController 添加 idempotencyUtil/objectMapper 字段、SessionRepository 添加导入、UserService 添加 CacheEvictionHelper 导入

## 解决了什么问题
- **缓存击穿**：热点 Key 过期瞬间 N 个并发请求同时查 DB → sync=true 同步锁只放行 1 个
- **SQL 全表扫描**：JSON 列 `LIKE '%xxx%'` 无法用索引 → `JSON_SEARCH` 在 JSON 数组内搜索
- **重复查询**：validateAnalysisAccess + getAnalysisResult 各查一次 → validateAnalysisAccess 返回实体复用
- **安全日志静默**：JWT 签名无效仅 debug 级别 → warn 级别，生产环境可见
- **Session 无幂等性**：快速点击创建多个重复会话 → clientToken + Redis 5 分钟去重
- **JDK 25 编译失败**：Lombok 1.18.30 不支持 JDK 25 → 升级 1.18.38

## 变更内容
### 修改文件
- `AnalysisService.java` — validateAnalysisAccess 返回 AnalysisResult + sync=true
- `SessionService.java` — sync=true×2 + createSession 幂等性 + doCreateSession 提取
- `UserService.java` — sync=true×2 + CacheEvictionHelper 字段+导入
- `FavoriteService.java` — sync=true
- `JwtUtil.java` — SecurityException/MalformedJwtException → warn
- `PaperRepositoryCustomImpl.java` — LIKE → JSON_SEARCH
- `SessionRepository.java` — 添加 @Lock/@Query/@Param/LockModeType 导入
- `AnalysisController.java` — 添加 idempotencyUtil/objectMapper 字段
- `AnalysisTransactionService.java` — 添加 BusinessException 导入
- `SessionCreateRequest.java` — 添加 clientToken 字段
- `pom.xml` — Spring Boot 3.2.12 + Lombok 1.18.38

## 关键技术点
- **sync=true 原理**：Spring Cache 的 sync 属性在缓存 miss 时通过 `Cache.get(key, valueLoader)` 同步加载，底层 Redis Cache 使用 Redis SETNX 实现分布式锁，确保同一 Key 只有一个线程查 DB
- **JSON_SEARCH vs LIKE**：`JSON_SEARCH(authors, 'one', CONCAT('%', ?5, '%'))` 在 JSON 数组中搜索匹配字符串，比 `LIKE '%xxx%'` 语义更准确（只搜索数组元素而非整列文本）
- **Lombok + JDK 25**：Lombok 通过反射访问 javac 内部 API，JDK 25 收紧了模块访问限制，需要 1.18.38+ 才能正常工作
- **MAVEN_OPTS vs compilerArgs**：`--add-opens` 在 `--release` 模式下被 javac 拒绝，必须通过 MAVEN_OPTS 传递给 Maven JVM 而非编译器 fork 进程

## 经验总结
- **sync=true 不是银弹**：它使用同步锁，在高并发场景下可能导致线程阻塞。但对于热点 Key 击穿防护是最简单的方案
- **JSON 列搜索**：MySQL JSON 类型列的搜索应优先使用 JSON 函数（JSON_SEARCH/JSON_CONTAINS/JSON_EXTRACT），而非 LIKE
- **Lombok 版本管理**：Spring Boot parent POM 管理的 Lombok 版本可能滞后于 JDK 版本，需要在 properties 中显式覆盖
- **@RequiredArgsConstructor 的陷阱**：它只会为 `final` 字段生成构造器注入，如果使用了未声明的字段会导致编译错误，IDE 诊断可能比 Maven 更早发现问题
