# Task07: HealthController 健康检查控制器 — 实施计划

## 任务概述

创建 `HealthController` 健康检查控制器 + 集成测试验证，提供 `GET /health` 端点，返回系统健康状态（MySQL/Redis连接检查）。

---

## 前置分析

### 现有代码基础

| 模块 | 状态 | 说明 |
|------|------|------|
| `ApiResponse<T>` | ✅ 已完成 | 统一响应封装，`success(T data)` / `error(int, String)` |
| `ErrorCode` | ✅ 已完成 | 错误码枚举 |
| `GlobalExceptionHandler` | ✅ 已完成 | 全局异常处理 |
| `JwtUtil` / `RedisKeyUtil` | ✅ 已完成 | JWT和Redis Key工具类 |
| `application.yml` | ✅ 已完成 | MySQL/Redis/JWT配置已就绪 |
| `controller/` 包 | 🈳 空 | HealthController为第一个Controller |
| `config/` 包 | 🈳 空 | SecurityConfig尚未创建（后续task） |

### 关键架构决策

1. **WebFlux → WebMVC 切换**：当前 `pom.xml` 仅有 `spring-boot-starter-webflux`，但 HealthController 使用 `DataSource`（阻塞JDBC）和 `RedisTemplate`（阻塞），且测试要求 `@AutoConfigureMockMvc`（MVC专属）。需添加 `spring-boot-starter-web`，Spring Boot 在两者共存时默认使用 MVC 模式，WebClient 仍可用于响应式HTTP调用。
2. **SecurityConfig 暂不创建**：prompt 明确说明"当前task仅创建Controller，SecurityConfig在后续task中配置"，/health 的白名单配置延后。
3. **不检查 aiService**：架构文档中 HealthController 示例包含 aiService 检查，但 prompt.json 仅要求 mysql 和 redis，严格按需求范围实现。

---

## 实施步骤

### Step 1: 添加 `spring-boot-starter-web` 依赖

**文件**: `Veritas/backend/pom.xml`

**变更**: 在 `<dependencies>` 中添加：

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>
```

**原因**:
- `@AutoConfigureMockMvc` 需要 MVC Servlet 栈
- JPA (`DataSource`) 是阻塞式，与纯 WebFlux (Netty) 不兼容
- 两者共存时 Spring Boot 默认 MVC 模式，WebClient 仍可用于 AI 服务调用
- SSE 推送改用 `SseEmitter`（MVC方式）

### Step 2: 创建 HealthController

**文件**: `Veritas/backend/src/main/java/com/literatureassistant/controller/HealthController.java`

**设计要点**:

```
@RestController
@Slf4j
public class HealthController {

    @Autowired DataSource dataSource
    @Autowired RedisTemplate<String, String> redisTemplate

    @GetMapping("/health")
    public ApiResponse<Map<String, Object>> health()
        → 构建 healthMap: {status, timestamp, mysql, redis}
        → checkMySQL(): try-with-resources, dataSource.getConnection() → SELECT 1
        → checkRedis(): redisTemplate.execute(RedisCallback → connection.ping())
        → 任一组件DOWN则整体status=DOWN
        → 所有异常捕获，标记DOWN，记录WARN日志
        → 始终返回200 + ApiResponse.success(healthMap)
}
```

**关键约束**:
- ❌ 禁止健康检查抛出异常导致 /health 返回500（FA-HC1）
- ❌ 禁止使用JPA Repository查询（FA-HC3），必须用 DataSource 连接验证
- ✅ 始终返回 HTTP 200 + ApiResponse 包装
- ✅ 异常时标记 DOWN + WARN 日志

**API契约**:
```json
GET /health → 200
{
  "code": 200,
  "message": "success",
  "data": {
    "status": "UP",
    "timestamp": 1716451200000,
    "mysql": "UP",
    "redis": "UP"
  },
  "timestamp": 1716451200000
}
```

### Step 3: 创建 HealthControllerTest 集成测试

**文件**: `Veritas/backend/src/test/java/com/literatureassistant/controller/HealthControllerTest.java`

**测试用例**:

| 测试方法 | 验证内容 |
|---------|---------|
| `testHealthEndpointReturns200` | GET /health 返回200状态码，ApiResponse格式正确（code=200） |
| `testHealthEndpointContainsRequiredFields` | 响应data包含 status/mysql/redis/timestamp 四个字段 |
| `testHealthEndpointStatusUpWhenServicesAvailable` | MySQL和Redis可用时 status=UP, mysql=UP, redis=UP |

**技术选型**:
- `@SpringBootTest` + `@AutoConfigureMockMvc`
- `@ActiveProfiles("test")` 如有test profile
- 使用 MockMvc.perform(get("/health")) 发起请求
- 使用 JsonPath 解析响应

### Step 4: 验证编译与测试

**命令**:
```bash
cd Veritas/backend && mvn compile
cd Veritas/backend && mvn test -Dtest=HealthControllerTest
```

**前提**: MySQL 和 Redis 服务需运行中

---

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 修改 | `Veritas/backend/pom.xml` | 添加 spring-boot-starter-web 依赖 |
| 新建 | `Veritas/backend/src/main/java/com/literatureassistant/controller/HealthController.java` | 健康检查控制器 |
| 新建 | `Veritas/backend/src/test/java/com/literatureassistant/controller/HealthControllerTest.java` | 集成测试 |

---

## 验收标准对照

| ID | 验收条件 | 验证方式 |
|----|---------|---------|
| AC-001 | GET /health返回200和ApiResponse格式 | 自动化测试 |
| AC-002 | /health响应包含status/mysql/redis/timestamp字段 | 自动化测试 |
| AC-003 | MySQL和Redis可用时status=UP | 自动化测试 |
| AC-004 | MySQL不可用时mysql=DOWN，整体status=DOWN，/health仍返回200 | 代码审查 |
| AC-005 | Redis不可用时redis=DOWN，整体status=DOWN，/health仍返回200 | 代码审查 |
| AC-006 | /health端点无需JWT鉴权即可访问 | 延后SecurityConfig配置时验证 |
| AC-007 | MySQL健康检查使用DataSource连接验证（SELECT 1） | 代码审查 |
| AC-008 | Redis健康检查使用RedisTemplate ping命令 | 代码审查 |
| AC-009 | 集成测试通过 | 自动化测试 |

---

## 风险与注意事项

1. **WebFlux + Web 共存**: 添加 `spring-boot-starter-web` 后，Spring Boot 默认使用 MVC 模式（Servlet容器）。WebClient Bean 仍可正常使用，不影响后续 AI 服务调用。
2. **RedisTemplate 泛型**: 项目中 `JwtUtil` 使用 `RedisTemplate<String, String>`，HealthController 应注入相同泛型，通过 `RedisCallback` 访问底层连接执行 ping。
3. **SecurityConfig 尚未创建**: /health 的白名单配置在后续 SecurityConfig task 中实现，当前 /health 默认可访问（无安全过滤器）。
4. **测试依赖 MySQL/Redis**: 集成测试需要 MySQL 和 Redis 服务运行，本地开发环境需确保服务可用。
