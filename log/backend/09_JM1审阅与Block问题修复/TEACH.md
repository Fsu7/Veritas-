# 技术教学文档 — JM1审阅与Block问题修复

## 开发思路
- 需求分析过程：JM1里程碑是Java后端开发的第一个里程碑，需要对照验收检查点逐项评审，确保骨架质量达标
- 技术选型考虑：审阅维度覆盖架构一致性、代码质量、安全性、可观测性等9个维度
- 架构设计思路：先识别Block问题（阻碍验收通过的严重问题），按优先级修复，再更新相关文档保持一致性
- 遇到的问题及解决方案：
  1. JWT密钥硬编码 → 移除默认值，强制环境变量注入
  2. 日志requestId为空 → 创建RequestIdFilter注入MDC
  3. Docker构建失败 → 修复Dockerfile为多阶段构建
  4. SQL排序不安全 → 白名单校验替代CASE WHEN参数化

## 实现步骤

### 第一步：全面审阅JM1代码
对照10项验收检查点，逐文件审阅config/entity/repository/filter/exception/util等包，识别出4个Block、6个Strong Suggestion、5个Suggestion、3个Nit问题。

### 第二步：修复B-001 JWT密钥硬编码
- `application.yml` 中 `${JWT_SECRET:literature-assistant-jwt-secret-key-2026}` 移除默认值
- `.env` 写入强密钥 `XH202630-LiteratureAssistant-JwtSecretKey-2026-Veritas`
- 创建 `application-test.yml` 提供测试用密钥
- 集成测试类添加 `@ActiveProfiles("test")`

### 第三步：修复B-002 缺少RequestIdFilter
- 创建 `RequestIdFilter.java`，实现 `jakarta.servlet.Filter`
- 最高优先级 `@Order(Ordered.HIGHEST_PRECEDENCE)`
- 从请求头 `X-Request-Id` 读取或生成32位UUID
- 写入 MDC `requestId` 键，与日志pattern `%X{requestId}` 对应
- 响应头回传 `X-Request-Id`
- `finally` 块清理MDC防止线程泄漏

### 第四步：修复B-004 缺少application-prod.yml
- 创建 `application-prod.yml`，关闭show-sql/format_sql
- 日志级别调整为生产标准（root=WARN, 业务=INFO）
- 修复 `Dockerfile` 为多阶段构建（maven:3.9-eclipse-temurin-17 → eclipse-temurin:17-jre-alpine）
- 添加HEALTHCHECK和非root用户

### 第五步：修复B-003 SQL排序白名单
- `PaperRepositoryCustomImpl` 使用 `SORT_MAPPING` Map白名单
- 仅允许 `relevance`/`year`/`citations` 三种排序
- 非法值降级为 `year DESC`
- `abstract` 保留字用反引号包裹

### 第六步：更新项目文档
- 里程碑文档：JM1状态⬜→✅，11项交付物和10项验收检查点全部标记完成
- AGENTS.md：目录结构新增3个文件，M1状态更新
- 架构文档：Dockerfile/JWT配置/PaperRepository/filter包结构更新
- 项目总里程碑：M1状态⬜→🔄进行中

## 解决了什么问题

### 核心问题1：JWT密钥安全
- 问题描述：`application.yml` 中JWT密钥有弱默认值，生产环境可能使用弱密钥
- 解决方案对比：
  - 方案A：保留默认值但加长复杂度 → 仍有泄露风险
  - 方案B：移除默认值，强制环境变量注入 → 启动时必须提供 ✅
- 最终方案优势：零容忍安全策略，忘记配置时启动失败比使用弱密钥更安全

### 核心问题2：请求链路追踪
- 问题描述：日志pattern配置了 `%X{requestId}` 但无Filter写入MDC
- 解决方案对比：
  - 方案A：在Controller层手动设置MDC → 容易遗漏
  - 方案B：Servlet Filter自动注入 → 全局覆盖 ✅
- 最终方案优势：最高优先级Filter确保所有请求都经过，finally块防止MDC泄漏

### 核心问题3：Docker构建
- 问题描述：Dockerfile使用JDK镜像但不含Maven，无法执行构建
- 解决方案对比：
  - 方案A：本地构建后COPY jar → 需要本地JDK环境
  - 方案B：多阶段构建（Maven镜像构建 + JRE镜像运行）→ 完全自包含 ✅
- 最终方案优势：任何环境只需Docker即可构建，不依赖本地JDK

### 核心问题4：SQL排序安全
- 问题描述：CASE WHEN ?5='relevance' 参数化排序不走索引且行为不可预测
- 解决方案对比：
  - 方案A：保留CASE WHEN但加白名单校验 → 仍不友好索引
  - 方案B：白名单Map + String.format动态拼接 → 简洁高效 ✅
- 最终方案优势：白名单保证安全，动态拼接对索引友好，非法值优雅降级

## 变更内容

### 新增文件
- `src/main/java/com/literatureassistant/filter/RequestIdFilter.java` — 请求ID过滤器，MDC注入requestId
- `src/main/resources/application-prod.yml` — 生产环境配置（关闭调试信息、调整日志级别）
- `src/test/resources/application-test.yml` — 测试环境配置（提供测试用JWT_SECRET和数据库连接）

### 修改文件
- `src/main/resources/application.yml` — JWT密钥移除默认值，expiration支持环境变量
- `src/main/java/com/literatureassistant/repository/PaperRepositoryCustomImpl.java` — 排序白名单校验，移除CASE WHEN
- `src/test/java/com/literatureassistant/LiteratureAssistantApplicationTests.java` — 添加@ActiveProfiles("test")
- `src/test/java/com/literatureassistant/controller/HealthControllerTest.java` — 添加@ActiveProfiles("test")
- `Dockerfile` — 多阶段构建、非root用户、HEALTHCHECK
- `.env` — JWT_SECRET写入强密钥

### 配置变更
- `jwt.secret`: `${JWT_SECRET:弱默认值}` → `${JWT_SECRET}`（无默认值）
- `jwt.expiration`: `86400000` → `${JWT_EXPIRATION:86400000}`（支持环境变量）
- Docker构建阶段镜像: `eclipse-temurin:17-jdk-alpine` → `maven:3.9-eclipse-temurin-17`
- Docker运行阶段: 新增 `curl` 安装、非root用户、HEALTHCHECK

## 关键技术点

### 1. MDC（Mapped Diagnostic Context）链路追踪
SLF4J提供的线程级上下文机制，每个请求线程独立维护一个Map，日志框架自动从MDC读取变量填充pattern。关键注意点：
- Filter必须在 `finally` 块中 `MDC.remove()`，否则线程池复用时requestId会泄漏到下一个请求
- Filter优先级设为 `Ordered.HIGHEST_PRECEDENCE`，确保所有请求最先经过

### 2. Spring Profile多环境配置
`application-{profile}.yml` 覆盖主配置，通过 `spring.profiles.active` 激活：
- `default`：开发环境（本地MySQL/Redis）
- `test`：测试环境（H2或本地MySQL_test库，测试用JWT_SECRET）
- `prod`：生产环境（关闭调试，调整日志级别）

### 3. Docker多阶段构建
```dockerfile
FROM maven:3.9-eclipse-temurin-17 AS build  # 阶段1：构建
# ... mvn package ...

FROM eclipse-temurin:17-jre-alpine          # 阶段2：运行
COPY --from=build /build/target/*.jar app.jar
```
优势：最终镜像不含Maven和JDK，体积从~500MB降至~200MB

### 4. SQL排序白名单模式
```java
private static final Map<String, String> SORT_MAPPING = Map.of(
    "relevance", "MATCH(title, `abstract`) AGAINST(?1 IN NATURAL LANGUAGE MODE) DESC",
    "year", "year DESC",
    "citations", "citation_count DESC"
);
```
比CASE WHEN参数化更安全：白名单之外的值不可能进入SQL，而CASE WHEN虽然参数化但排序逻辑仍依赖输入值

## 经验总结

### 开发过程中的收获
1. **审阅先行**：在进入下一阶段开发前做全面审阅，能及早发现架构问题，避免技术债累积
2. **验收驱动**：对照验收检查点逐项评审，比随意审阅更有针对性
3. **文档同步**：代码修改后立即更新相关文档，避免文档与代码脱节

### 踩过的坑及如何避免
1. **JWT密钥默认值陷阱**：Spring Boot的 `${VAR:default}` 语法很方便，但敏感配置不应有默认值。原则：**安全配置无默认值，业务配置可有合理默认值**
2. **MDC泄漏**：忘记在finally中清理MDC，导致线程池复用时requestId串请求。原则：**MDC.put() 必须配对 MDC.remove()**
3. **Dockerfile镜像选择**：`eclipse-temurin:17-jdk-alpine` 不含Maven，无法执行构建。原则：**构建阶段用Maven镜像，运行阶段用JRE镜像**
4. **MySQL保留字**：`abstract` 是MySQL保留字，原生SQL中必须用反引号包裹。原则：**原生SQL中所有列名用反引号包裹**

### 最佳实践建议
1. 每个里程碑完成后做架构审阅，形成审阅报告归档
2. Block问题必须修复后才能进入下一里程碑
3. 安全配置（JWT_SECRET、MYSQL_PASSWORD等）永远不要有默认值
4. Filter/Interceptor的MDC操作必须在finally中清理
5. Docker多阶段构建是Java项目的标准实践
6. SQL排序字段必须白名单校验，禁止直接拼接用户输入
