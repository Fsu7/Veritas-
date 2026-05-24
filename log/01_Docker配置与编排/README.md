# Docker 配置与编排

## 功能描述
- 解决了项目多服务容器化部署的问题，实现了 MySQL、Redis、AI 服务、Java 后端、前端 5 个服务的 Docker 编排
- 实现了基于 healthcheck 的服务启动顺序控制，确保依赖服务就绪后才启动下游服务
- 实现了 Java 后端的多阶段 Docker 构建，优化镜像体积和构建缓存
- 实现了 MySQL 数据库的自动初始化（建表 + 索引 + 种子数据）
- 业务价值：一键 `docker-compose up` 即可启动全部服务，降低环境配置门槛，保证开发/测试/演示环境一致性

## 实现逻辑

### 修改的核心文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `Veritas/backend/Dockerfile` | 新增 | Java 后端多阶段构建镜像 |
| `Veritas/backend/.dockerignore` | 新增 | Docker 构建忽略文件 |
| `Veritas/docker-compose.yml` | 新增 | 5 服务编排配置 |
| `Veritas/.env.example` | 新增 | 环境变量模板 |
| `Veritas/backend/src/main/resources/db/` | 迁移 | SQL 脚本从 backend-java/ 迁移 |

### 使用的算法或设计模式
- **多阶段构建模式**：build 阶段（JDK + Maven 编译）→ run 阶段（仅 JRE 运行），减小最终镜像体积
- **Docker 缓存优化**：先 COPY pom.xml 下载依赖（依赖层独立缓存），再 COPY src 编译，pom.xml 不变时跳过依赖下载
- **Healthcheck 链式依赖**：`depends_on + condition: service_healthy` 保证启动顺序
- **环境变量外部化**：敏感配置通过 `${VAR}` 引用 .env 文件，不硬编码

### 关键代码逻辑说明

**Dockerfile 多阶段构建**：
1. build 阶段：`eclipse-temurin:17-jdk-alpine` → `mvn dependency:go-offline`（缓存依赖层）→ `mvn package`
2. run 阶段：`eclipse-temurin:17-jre-alpine` → 安装 curl（healthcheck）→ 创建非 root 用户 → COPY jar → HEALTHCHECK → ENTRYPOINT

**docker-compose.yml 启动顺序**：
```
mysql (healthy) ──┐
redis (healthy) ──┼──→ ai-service (healthy) ──→ java-backend (healthy) ──→ frontend
                  └────────────────────────────→ java-backend
```

**MySQL 自动初始化**：
- 通过 volume 挂载 `./backend/src/main/resources/db/` → `/docker-entrypoint-initdb.d/`
- MySQL 8.0 首次启动时自动按文件名顺序执行 SQL 脚本（01→02→03）

## 接口变更

### Request
本次为基础设施配置，无 API 接口变更。

### Response
本次为基础设施配置，无 API 接口变更。

## 测试结果

| 测试场景 | 结果 |
|----------|------|
| `docker-compose config` YAML 语法验证 | ✅ 通过，无语法错误 |
| MySQL 容器启动 + healthcheck | ✅ healthy 状态 |
| Redis 容器启动 + healthcheck | ✅ healthy 状态 |
| Redis `redis-cli ping` → PONG | ✅ 返回 PONG |
| MySQL `mysqladmin ping` → alive | ✅ 返回 alive |
| `literature_assistant` 数据库自动创建 | ✅ 数据库存在 |
| 6 张表自动创建（users/user_profiles/papers/sessions/analysis_results/paper_favorites） | ✅ 全部存在 |
| 种子数据自动导入（1 user, 2 papers） | ✅ 数据正确 |
| 是否通过 | **是** |

> **注意**：`docker build` 和全量 `docker-compose up` 验证需等 Task 01（Spring Boot Maven 骨架）完成后执行，因为当前 `Veritas/backend/` 中尚无 pom.xml。

## 相关文件

### 代码文件
- `Veritas/backend/Dockerfile`
- `Veritas/backend/.dockerignore`
- `Veritas/docker-compose.yml`
- `Veritas/.env.example`
- `Veritas/.env`（从 .env.example 复制，不提交 Git）

### 配置文件变更
- `Veritas/backend/src/main/resources/db/01_create_tables.sql`（迁移自 backend-java/）
- `Veritas/backend/src/main/resources/db/02_create_indexes.sql`（迁移自 backend-java/）
- `Veritas/backend/src/main/resources/db/03_insert_seed_data.sql`（迁移自 backend-java/）

### Docker 资源
- Network: `veritas_app-network`（bridge）
- Volume: `veritas_mysql_data`（MySQL 持久化）
- Container: `literature-mysql`, `literature-redis`
