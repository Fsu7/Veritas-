# Task07: HealthController + 集成测试验证

| 项目 | 内容 |
|------|------|
| **项目** | XH-202630 科研文献智能助手 |
| **版本** | v0.1 |
| **里程碑** | M1：基础设施就绪 / JM1：项目骨架与数据层就绪 |
| **功能编号** | F2.1, F2.2, F2.3, F2.4, F2.5, F2.6 |

## 需求描述

创建HealthController健康检查控制器，提供 `GET /health` 端点，返回系统各组件健康状态（MySQL/Redis连接检查）。同时创建集成测试验证Spring Boot启动、/health返回200、MySQL/Redis连接正常。该端点无需JWT鉴权，用于Docker healthcheck。

## 涉及层级

- **java_backend** — com.literatureassistant.controller
- **java_backend** — com.literatureassistant.dto.common（依赖ApiResponse）
- **data_layer** — MySQL/Redis连接验证

## 需要修改/新增的文件

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `Veritas/backend/src/main/java/com/literatureassistant/controller/HealthController.java` | 健康检查控制器 |
| 新增 | `Veritas/backend/src/test/java/com/literatureassistant/controller/HealthControllerTest.java` | 集成测试 |

## 功能要求

| ID | 优先级 | 描述 |
|----|--------|------|
| FR-001 | P0 | GET /health返回ApiResponse<Map>，data包含status(UP/DOWN)/timestamp/mysql(UP/DOWN)/redis(UP/DOWN) |
| FR-002 | P0 | MySQL检查：DataSource.getConnection() → SELECT 1 → UP；Redis检查：RedisTemplate.ping() → PONG → UP。异常时标记DOWN，不抛出 |
| FR-003 | P0 | /health端点无需JWT鉴权（后续SecurityConfig白名单） |
| FR-004 | P0 | 集成测试：验证/health返回200、ApiResponse格式、包含必需字段、服务可用时status=UP |

## 跨系统一致性

- 响应格式：`{code: 200, message: 'success', data: {status: 'UP', mysql: 'UP', redis: 'UP', timestamp: ...}}`
- Docker healthcheck使用：`curl -f http://localhost:8080/health`

## 关键约束

- **禁止**健康检查抛出异常导致/health返回500（组件异常标记DOWN）
- **禁止**/health端点要求JWT鉴权
- **禁止**MySQL健康检查使用JPA Repository（应使用DataSource底层连接）

## 验收标准

| ID | 标准 | 验证方式 |
|----|------|---------|
| AC-001 | GET /health返回200和ApiResponse格式 | 集成测试 |
| AC-002 | /health响应包含status/mysql/redis/timestamp字段 | 集成测试 |
| AC-003 | MySQL和Redis可用时status=UP | 集成测试 |
| AC-004 | MySQL不可用时mysql=DOWN，/health仍返回200 | 代码审查 |
| AC-005 | Redis不可用时redis=DOWN，/health仍返回200 | 代码审查 |
| AC-006 | /health端点无需JWT鉴权 | 手动测试 |
| AC-007 | MySQL检查使用DataSource SELECT 1 | 代码审查 |
| AC-008 | Redis检查使用RedisTemplate ping | 代码审查 |
| AC-009 | 集成测试通过 | 自动化测试 |

## 验证命令

```bash
# 集成测试
cd Veritas/backend && mvn test -Dtest=HealthControllerTest

# 手动验证
cd Veritas/backend && mvn spring-boot:run -Dspring-boot.run.profiles=dev & sleep 15 && curl -s http://localhost:8080/health
```
