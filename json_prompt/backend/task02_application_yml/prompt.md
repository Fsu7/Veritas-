# Task02: Spring Boot 三层配置文件

| 项目 | 内容 |
|------|------|
| **项目** | XH-202630 科研文献智能助手 |
| **版本** | v0.1 |
| **里程碑** | M1：基础设施就绪 / JM1：项目骨架与数据层就绪 |
| **功能编号** | F2.1, F2.2, F2.3, F2.4, F2.5, F2.6 |

## 需求描述

创建Spring Boot三层配置文件：application.yml（公共配置）、application-dev.yml（开发环境，连接本机MySQL 9和Redis）、application-prod.yml（生产环境，通过 `${环境变量}` 引用Docker内服务地址）。所有敏感配置必须通过 `${VAR}` 环境变量注入，提供默认值仅用于开发环境。

## 涉及层级

- **java_backend** — com.literatureassistant.config

## 需要修改/新增的文件

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 修改 | `backend-java/src/main/resources/application.yml` | 覆盖任务1的简化版，写入完整公共配置 |
| 新增 | `backend-java/src/main/resources/application-dev.yml` | 开发环境配置（本机MySQL9/Redis/AI服务、DEBUG日志、ddl-auto=update） |
| 新增 | `backend-java/src/main/resources/application-prod.yml` | 生产环境配置（Docker内服务发现、INFO日志、ddl-auto=validate、连接池优化） |

## 功能要求

| ID | 优先级 | 描述 |
|----|--------|------|
| FR-001 | P0 | application.yml公共配置包含：server.port=8080、spring.application.name、spring.datasource（url/username/password/driver-class-name/hikari最大20最小5超时30s）、spring.jpa（ddl-auto/show-sql/dialect/format_sql）、spring.data.redis（host/port/password/timeout/lettuce连接池max-active=20/max-idle=10/min-idle=5）、spring.jackson（date-format/time-zone/default-property-inclusion）、ai-service（url/timeout=30000/retry-count=1/retry-interval=3000）、jwt（secret/expiration=86400000）、logging |
| FR-002 | P0 | application.yml中所有环境相关值使用 `${VAR:defaultValue}` 格式，默认值仅适用于开发环境：MYSQL_URL→localhost:3306、MYSQL_USERNAME→root、MYSQL_PASSWORD→Aa2105268075.、REDIS_HOST→localhost、REDIS_PORT→6379、REDIS_PASSWORD→空、AI_SERVICE_URL→http://localhost:8000、JWT_SECRET→literature-assistant-jwt-secret-key-2026 |
| FR-003 | P0 | application-dev.yml：覆盖spring.datasource为本机MySQL9（localhost:3306, root/Aa2105268075.）、spring.data.redis为localhost:6379无密码、ai-service.url=http://localhost:8000、ddl-auto=update、show-sql=true、DEBUG日志 |
| FR-004 | P0 | application-prod.yml：所有敏感配置通过 `${VAR}` 引用无默认值、ddl-auto=validate、show-sql=false、INFO日志、hikari连接池优化（maximum-pool-size=20、minimum-idle=10、connection-timeout=30000、idle-timeout=600000、max-lifetime=1800000） |
| FR-005 | P0 | MySQL连接URL必须包含 `useUnicode=true&characterEncoding=utf8mb4&serverTimezone=Asia/Shanghai` |
| FR-006 | P1 | JPA配置使用MySQL8Dialect（org.hibernate.dialect.MySQL8Dialect），即使本机是MySQL 9也使用MySQL8Dialect |
| FR-007 | P1 | logging.pattern.console格式包含requestId：`%d{yyyy-MM-dd HH:mm:ss} [%thread] %-5level %logger{36} - [%X{requestId}] %msg%n` |

## 跨系统一致性

- Java camelCase ↔ Python/JSON snake_case 字段映射：educationLevel↔education_level、knowledgeLevel↔knowledge_level、preferredStyle↔preferred_style
- Java后端通过WebClient调用Python AI服务（ai-service.url配置），请求中用户画像字段使用snake_case（@JsonProperty注解）

## 降级要求

- **LLM三级降级**：BuiltinLLMProvider → APILLMProvider → LocalLLMProvider，触发条件：连续3次失败/超时30s/HTTP 5xx，每5分钟尝试恢复
- **Agent降级**：单Agent失败跳过→多Agent失败降级为单Agent模式（Retriever+Generator）

## 关键约束

- **禁止**在application.yml中写死环境特定值（如localhost地址），应使用 `${VAR:defaultValue}` 格式
- **禁止**在application-prod.yml中硬编码敏感配置
- **禁止**生产环境ddl-auto设为update或create，必须validate
- **禁止**省略MySQL连接URL中的useUnicode/characterEncoding/serverTimezone参数

## 验收标准

| ID | 标准 | 验证方式 |
|----|------|---------|
| AC-001 | application.yml包含完整公共配置：server/spring.datasource/JPA/Redis/Jackson/ai-service/jwt/logging | 代码审查 |
| AC-002 | application.yml中所有环境相关值使用 `${VAR:defaultValue}` 格式 | 代码审查 |
| AC-003 | application-dev.yml正确配置本机MySQL9（localhost:3306, root/Aa2105268075.）和Redis（localhost:6379无密码） | 代码审查 |
| AC-004 | application-dev.yml中ddl-auto=update, show-sql=true, DEBUG日志 | 代码审查 |
| AC-005 | application-prod.yml中所有敏感配置通过 `${VAR}` 引用，无默认值 | 代码审查 |
| AC-006 | application-prod.yml中ddl-auto=validate, show-sql=false, INFO日志 | 代码审查 |
| AC-007 | MySQL连接URL包含useUnicode=true&characterEncoding=utf8mb4&serverTimezone=Asia/Shanghai | 代码审查 |
| AC-008 | HikariCP连接池配置：max=20, min-idle=5, connection-timeout=30000 | 代码审查 |
| AC-009 | Redis Lettuce连接池配置：max-active=20, max-idle=10, min-idle=5 | 代码审查 |
| AC-010 | JPA dialect使用MySQL8Dialect | 代码审查 |
| AC-011 | logging.pattern.console包含requestId（%X{requestId}） | 代码审查 |
| AC-012 | dev profile启动时HikariCP连接池初始化成功 | 手动测试 |

## 验证命令

```bash
# 验证dev profile启动
cd backend-java && mvn spring-boot:run -Dspring-boot.run.profiles=dev

# 验证健康检查（需HealthController已实现）
curl -s http://localhost:8080/actuator/health 2>/dev/null || echo '需要HealthController'

# 验证本机MySQL9连接
mysql -u root -p'Aa2105268075.' -e "SELECT 1"
```
