# 技术教学文档 — HealthController 健康检查与 SecurityConfig

## 开发思路

### 需求分析过程
1. 原始需求来自 `task07_health_controller/prompt.json`，要求创建 `GET /health` 端点
2. 端点需检查 MySQL（DataSource SELECT 1）和 Redis（RedisTemplate ping）连接状态
3. 始终返回 HTTP 200 + ApiResponse 包装，组件异常标记 DOWN 而非抛出异常
4. /health 无需 JWT 鉴权，用于 Docker healthcheck

### 技术选型考虑
1. **WebFlux vs WebMVC**：项目原 pom.xml 仅有 `spring-boot-starter-webflux`，但 JPA（DataSource）是阻塞式 API，与纯 WebFlux（Netty 容器）不兼容。且测试要求 `@AutoConfigureMockMvc`（MVC 专属）。最终决定添加 `spring-boot-starter-web`，两者共存时 Spring Boot 默认使用 MVC 模式（Tomcat），WebClient 仍可用于响应式 HTTP 调用。
2. **健康检查方式**：MySQL 使用最底层的 `DataSource.getConnection()` 执行 `SELECT 1`，而非 JPA Repository，因为健康检查应验证最基础的连接能力。Redis 使用 `RedisTemplate.execute(RedisCallback)` 访问底层连接执行 `ping()`。
3. **SecurityConfig 必要性**：添加 `spring-boot-starter-web` 后，Spring Security 自动配置会拦截所有请求返回 401。必须创建 SecurityConfig 放行 `/health`，否则健康检查端点无法访问。

### 架构设计思路
```
请求流程：
Docker healthcheck → curl http://localhost:8080/health
    → SecurityFilterChain（/health permitAll）
    → HealthController.health()
    → checkMySQL() + checkRedis()
    → ApiResponse.success(healthData)
    → HTTP 200 + JSON
```

### 遇到的问题及解决方案

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 测试全部返回 401 | Spring Security 自动配置拦截所有请求 | 创建 SecurityConfig 放行 /health |
| Maven 重复依赖警告 | 编辑时误添加重复的 starter 声明 | 删除重复的 dependency 块 |
| RedisCallback import 错误 | 错误使用 `connection` 包下的 RedisCallback | 改为 `org.springframework.data.redis.core.RedisCallback` |

## 实现步骤

1. **添加 Maven 依赖**：在 pom.xml 中添加 `spring-boot-starter-web` 和 `spring-boot-starter-security`
2. **创建 HealthController**：实现 `GET /health` 端点，注入 DataSource 和 RedisTemplate，检查 MySQL/Redis 状态
3. **创建 SecurityConfig**：配置安全过滤链，放行公开端点，CSRF 禁用，Session STATELESS
4. **创建 HealthControllerTest**：3 个集成测试用例验证端点
5. **编译验证**：`mvn compile` 通过
6. **运行测试**：`mvn test` 全部 85 个测试通过

## 解决了什么问题

### 核心问题描述
项目需要为 Docker 容器编排提供健康检查端点，同时需要安全配置框架来控制 API 访问权限。

### 解决方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| Spring Boot Actuator | 功能丰富，自动检测 | 引入过多不需要的端点，配置复杂 |
| 自定义 HealthController | 精确控制，轻量，符合需求 | 需手动实现组件检查 |

### 最终方案的优势
1. 精确满足 Docker healthcheck 需求（`curl -f http://localhost:8080/health`）
2. 返回结构化 JSON（ApiResponse 包装），便于监控系统解析
3. 组件异常时仍返回 200，避免 Docker 误判容器不健康
4. SecurityConfig 为后续所有 API 端点提供安全框架基础

## 变更内容

### 新增文件
- `Veritas/backend/src/main/java/com/literatureassistant/controller/HealthController.java` — 健康检查控制器，GET /health 返回 MySQL/Redis 连接状态
- `Veritas/backend/src/main/java/com/literatureassistant/config/SecurityConfig.java` — Spring Security 安全配置，放行公开端点
- `Veritas/backend/src/test/java/com/literatureassistant/controller/HealthControllerTest.java` — 集成测试，3 个测试用例

### 修改文件
- `Veritas/backend/pom.xml` — 新增 `spring-boot-starter-web`（MVC 容器）和 `spring-boot-starter-security`（安全框架）依赖

### 配置变更
- 无 application.yml 变更，所有配置复用已有项

## 关键技术点

### 1. WebFlux + Web MVC 共存
Spring Boot 在 classpath 同时存在 `spring-boot-starter-web` 和 `spring-boot-starter-webflux` 时，默认使用 MVC 模式（Servlet 容器/Tomcat）。WebClient Bean 仍可正常使用，不影响后续 AI 服务的响应式 HTTP 调用。

### 2. RedisTemplate 泛型与 RedisCallback
项目使用 `RedisTemplate<String, String>`，通过 `RedisCallback` 接口可以访问底层 Redis 连接执行原生命令（如 ping）。注意 `RedisCallback` 在 `org.springframework.data.redis.core` 包中，不是 `connection` 包。

### 3. 健康检查的防御性编程
健康检查端点必须始终返回 200，即使组件不可用。所有检查方法使用 try-catch 捕获 Exception，标记 DOWN 并记录 WARN 日志，绝不向上抛出异常。

### 4. Spring Security 6.x 配置风格
Spring Security 6.x 推荐使用 Lambda DSL 配置（而非已废弃的链式 API）：
```java
http
    .csrf(AbstractHttpConfigurer::disable)
    .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
    .authorizeHttpRequests(auth -> auth
        .requestMatchers("/health").permitAll()
        .anyRequest().authenticated());
```

### 5. DataSource 连接验证 vs JPA Repository
健康检查使用 `DataSource.getConnection()` + `SELECT 1` 而非 JPA Repository，原因：
- 验证最基础的 JDBC 连接能力，不依赖 JPA/Hibernate 层
- 避免因 JPA 配置问题导致健康检查误判
- 符合 prompt.json 中 FA-HC3 禁止项的要求

## 经验总结

### 开发过程中的收获
1. **依赖传递影响**：`spring-boot-starter-webflux` 传递引入了 Spring Security，添加 `spring-boot-starter-web` 后 Security 自动配置生效，必须显式配置 SecurityFilterChain
2. **MVC 与 WebFlux 选择**：对于以 JPA 为主的项目，MVC 模式更合适（JPA 是阻塞式），WebFlux 仅用于 WebClient 调用外部服务
3. **测试驱动发现问题**：先写测试再运行，401 错误暴露了 Security 自动配置的问题

### 踩过的坑及如何避免
1. **RedisCallback import 错误**：IDE 自动补全可能选择错误的包路径。记住 `RedisCallback` 在 `core` 包而非 `connection` 包
2. **pom.xml 重复依赖**：编辑时注意不要重复添加已存在的依赖，Maven 会发出 WARNING
3. **SecurityConfig 缺失导致全部 401**：添加 `spring-boot-starter-security` 后必须创建 SecurityConfig，否则默认所有请求需认证

### 最佳实践建议
1. 健康检查端点应始终返回 200，组件异常标记 DOWN 而非抛出异常
2. 安全配置应在项目骨架阶段就创建，避免后续所有端点被拦截
3. 使用 `@SpringBootTest` + `@AutoConfigureMockMvc` 进行 Controller 集成测试，能发现安全配置问题
4. Docker healthcheck 配置 `curl -f` 参数，HTTP 200 才视为健康
