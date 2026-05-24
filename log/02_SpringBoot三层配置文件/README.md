# Spring Boot 三层配置文件

## 功能描述
- 解决了 Spring Boot 项目多环境配置分离的问题，实现了公共/开发/生产三层配置文件体系
- 实现了所有环境相关值通过 `${VAR:defaultValue}` 格式引用，默认值仅适用于开发环境
- 实现了生产环境敏感配置零硬编码，所有密码和密钥通过 `${VAR}` 无默认值注入
- 实现了 dev profile 启动时成功连接本机 MySQL 9 和 Redis，HikariCP 连接池正常初始化
- 业务价值：开发环境一键启动无需配置环境变量，生产环境安全合规无敏感信息泄露风险

## 实现逻辑

### 修改的核心文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `Veritas/backend/src/main/resources/application.yml` | 新增 | 公共配置（server/datasource/JPA/Redis/Jackson/ai-service/jwt/logging） |
| `Veritas/backend/src/main/resources/application-dev.yml` | 新增 | 开发环境配置（本机MySQL9/Redis/AI服务、ddl-auto=update、DEBUG日志） |
| `Veritas/backend/src/main/resources/application-prod.yml` | 新增 | 生产环境配置（${VAR}无默认值、ddl-auto=validate、连接池优化） |
| `Veritas/backend/pom.xml` | 新增 | 最小化Spring Boot项目骨架（webflux/JPA/Redis/MySQL/JJWT/Lombok/MapStruct） |
| `Veritas/backend/src/main/java/com/literatureassistant/LiteratureAssistantApplication.java` | 新增 | Spring Boot主启动类 |

### 使用的算法或设计模式
- **Profile分层模式**：application.yml（公共）+ application-{profile}.yml（环境特定），Spring Boot自动合并
- **环境变量外部化**：`${VAR:defaultValue}` 格式，开发环境使用默认值，生产环境通过环境变量覆盖
- **安全分层策略**：dev允许硬编码本机密码，prod强制 `${VAR}` 无默认值
- **连接池分层优化**：公共配置 max=20/min-idle=5，prod覆盖 min-idle=10 + idle-timeout/max-lifetime

### 关键代码逻辑说明

**application.yml 公共配置**：
- 所有环境相关值使用 `${VAR:defaultValue}` 格式
- 默认值指向本机开发环境（localhost:3306/6379/8000）
- HikariCP: maximum-pool-size=20, minimum-idle=5, connection-timeout=30000
- Redis Lettuce: max-active=20, max-idle=10, min-idle=5
- JPA dialect: `org.hibernate.dialect.MySQLDialect`（Hibernate 6.4+推荐）
- logging pattern 包含 `%X{requestId}` MDC占位符

**application-dev.yml 开发环境**：
- 直接硬编码本机 MySQL9 连接信息（localhost:3306, root/Aa2105268075.）
- Redis 无密码连接（localhost:6379）
- `ddl-auto: update` — 自动更新表结构
- `show-sql: true` — 显示SQL语句
- DEBUG级别日志

**application-prod.yml 生产环境**：
- 所有敏感值 `${VAR}` 无默认值（MYSQL_URL/USERNAME/PASSWORD, REDIS_HOST/PORT/PASSWORD, JWT_SECRET）
- `ddl-auto: validate` — 仅验证表结构，禁止自动修改
- `show-sql: false` — 不显示SQL
- HikariCP连接池优化：minimum-idle=10, idle-timeout=600000, max-lifetime=1800000
- INFO级别日志

## 接口变更

### Request
本次为配置文件创建，无 API 接口变更。

### Response
本次为配置文件创建，无 API 接口变更。

## 测试结果

| 测试场景 | 结果 |
|----------|------|
| 本机MySQL9连接测试：`mysql -u root -p'Aa2105268075.' -e "SELECT 1"` | ✅ 返回 1 |
| 本机Redis连接测试：`redis-cli ping` | ✅ 返回 PONG |
| `literature_assistant` 数据库创建 | ✅ utf8mb4/utf8mb4_unicode_ci |
| `mvn spring-boot:run -Dspring-boot.run.profiles=dev` 启动 | ✅ 启动成功（1.3秒） |
| HikariCP连接池初始化 | ✅ `HikariPool-1 - Start completed.` |
| MySQL9连接建立 | ✅ `HikariPool-1 - Added connection com.mysql.cj.jdbc.ConnectionImpl@3a16984c` |
| JPA EntityManagerFactory初始化 | ✅ `Initialized JPA EntityManagerFactory for persistence unit 'default'` |
| dev profile激活确认 | ✅ `The following 1 profile is active: "dev"` |
| Netty启动在8080端口 | ✅ `Netty started on port 8080` |
| 是否通过 | **是** |

### 实施中修复的问题

| 问题 | 原因 | 修复 |
|------|------|------|
| `Unsupported character encoding 'utf8mb4'` | `utf8mb4`是MySQL字符集名，不是Java字符集名 | `characterEncoding=utf8mb4` → `characterEncoding=UTF-8` |
| `MySQL8Dialect has been deprecated` | Hibernate 6.4+弃用MySQL8Dialect | `MySQL8Dialect` → `MySQLDialect` |
| 测试编译失败（缺少JUnit依赖） | pom.xml缺少spring-boot-starter-test | 添加test scope依赖 |

## 相关文件

### 代码文件
- `Veritas/backend/src/main/resources/application.yml`
- `Veritas/backend/src/main/resources/application-dev.yml`
- `Veritas/backend/src/main/resources/application-prod.yml`
- `Veritas/backend/pom.xml`
- `Veritas/backend/src/main/java/com/literatureassistant/LiteratureAssistantApplication.java`
- `Veritas/backend/src/test/java/com/literatureassistant/LiteratureAssistantApplicationTests.java`

### 配置文件变更
- 新增 `application.yml`：server/spring.datasource/JPA/Redis/Jackson/ai-service/jwt/logging
- 新增 `application-dev.yml`：本机MySQL9/Redis/AI服务覆盖
- 新增 `application-prod.yml`：Docker内服务发现 + 连接池优化

### 环境变量清单

| 环境变量 | 说明 | 默认值（dev） |
|---------|------|-------------|
| `MYSQL_URL` | MySQL连接URL | `jdbc:mysql://localhost:3306/literature_assistant?useUnicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai` |
| `MYSQL_USERNAME` | MySQL用户名 | `root` |
| `MYSQL_PASSWORD` | MySQL密码 | `Aa2105268075.` |
| `REDIS_HOST` | Redis主机 | `localhost` |
| `REDIS_PORT` | Redis端口 | `6379` |
| `REDIS_PASSWORD` | Redis密码 | 空 |
| `AI_SERVICE_URL` | Python AI服务URL | `http://localhost:8000` |
| `JWT_SECRET` | JWT签名密钥 | `literature-assistant-jwt-secret-key-2026` |
