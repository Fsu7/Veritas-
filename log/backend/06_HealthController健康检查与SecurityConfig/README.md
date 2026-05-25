# HealthController 健康检查与 SecurityConfig 安全配置

## 功能描述
- 解决了系统健康检查端点的需求，提供 `GET /health` 供 Docker healthcheck 和监控系统调用
- 实现了 MySQL（DataSource SELECT 1）和 Redis（RedisTemplate ping）两个组件的连接状态检查
- 创建了 SecurityConfig 安全配置，放行 `/health`、`/api/users/register`、`/api/users/login` 三个公开端点
- 添加了 `spring-boot-starter-web` 和 `spring-boot-starter-security` 依赖，补全了项目运行所需的基础设施
- 业务价值：为 Docker 容器编排提供健康检查能力，为后续所有 API 端点提供安全框架基础

## 实现逻辑

### 修改的核心文件列表
| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `pom.xml` | 添加 `spring-boot-starter-web` + `spring-boot-starter-security` |
| 新建 | `controller/HealthController.java` | 健康检查控制器 |
| 新建 | `config/SecurityConfig.java` | Spring Security 安全配置 |
| 新建 | `controller/HealthControllerTest.java` | 集成测试 |

### 使用的算法或设计模式
- **防御性编程**：健康检查方法捕获所有异常，标记 DOWN 而非抛出，确保 `/health` 始终返回 200
- **组件状态聚合**：任一组件 DOWN 则整体 status=DOWN，采用"与"逻辑
- **白名单模式**：SecurityConfig 使用 `permitAll()` 放行公开端点，其余 `authenticated()`

### 关键代码逻辑说明

**HealthController.health()**：
1. 分别调用 `checkMySQL()` 和 `checkRedis()` 获取组件状态
2. 两者均为 UP 则整体 status=UP，否则 DOWN
3. 构建 `Map<String, Object>` 包含 status/timestamp/mysql/redis
4. 通过 `ApiResponse.success(healthData)` 包装返回

**checkMySQL()**：
- `try-with-resources` 获取 Connection → Statement → 执行 `SELECT 1`
- 成功返回 "UP"，异常捕获后记录 WARN 日志返回 "DOWN"

**checkRedis()**：
- `redisTemplate.execute(RedisCallback)` 获取底层连接执行 `ping()`
- 返回 "PONG" 则 "UP"，否则 "DOWN"
- 异常捕获后记录 WARN 日志返回 "DOWN"

**SecurityConfig**：
- CSRF 禁用（JWT 无状态认证不需要）
- Session 策略 STATELESS
- `/health`、`/api/users/register`、`/api/users/login` 放行
- 其余所有请求需认证

## 接口变更

### Request
```
GET /health
```
无需请求体，无需 JWT Token。

### Response
```json
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

组件异常时响应（仍返回 200）：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "status": "DOWN",
    "timestamp": 1716451200000,
    "mysql": "DOWN",
    "redis": "UP"
  },
  "timestamp": 1716451200000
}
```

## 测试结果
- 测试场景1：GET /health 返回 200 状态码和 ApiResponse 格式（code=200, message=success）→ 通过
- 测试场景2：响应 data 包含 status/mysql/redis/timestamp 四个必需字段 → 通过
- 测试场景3：MySQL 和 Redis 可用时 status=UP, mysql=UP, redis=UP → 通过
- 全量测试：85 tests, 0 failures, 0 errors → 通过
- 是否通过：是

## 相关文件
- `Veritas/backend/pom.xml` — 新增 web + security 依赖
- `Veritas/backend/src/main/java/com/literatureassistant/controller/HealthController.java` — 健康检查控制器
- `Veritas/backend/src/main/java/com/literatureassistant/config/SecurityConfig.java` — 安全配置
- `Veritas/backend/src/test/java/com/literatureassistant/controller/HealthControllerTest.java` — 集成测试
