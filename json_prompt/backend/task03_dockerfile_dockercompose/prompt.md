# Task03: Dockerfile 与 Docker Compose 配置

| 项目 | 内容 |
|------|------|
| **项目** | XH-202630 科研文献智能助手 |
| **版本** | v0.1 |
| **里程碑** | M1：基础设施就绪 / JM1：项目骨架与数据层就绪 |
| **功能编号** | F2.1, F2.2, F2.3, F2.4, F2.5, F2.6 |

## 需求描述

创建Java后端的Dockerfile（多阶段构建）和docker-compose.yml（5服务编排：mysql/redis/ai-service/java-backend/frontend），以及.env.example环境变量模板。启动顺序：mysql → redis → ai-service → java-backend → frontend。

## 涉及层级

- **java_backend** — backend-java/Dockerfile
- **infra** — docker-compose.yml

## 需要修改/新增的文件

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `backend-java/Dockerfile` | Java后端Docker镜像构建文件（多阶段构建） |
| 新增 | `backend-java/.dockerignore` | Docker构建忽略文件 |
| 新增 | `docker-compose.yml` | Docker Compose编排文件（5服务） |
| 新增 | `.env.example` | 环境变量模板文件（仅含占位符，提交Git） |

## 功能要求

| ID | 优先级 | 描述 |
|----|--------|------|
| FR-001 | P0 | Dockerfile多阶段构建：阶段1(build)使用eclipse-temurin:17-jdk-alpine，安装Maven，COPY pom.xml先下载依赖（Docker缓存优化），COPY src编译打包；阶段2(run)使用eclipse-temurin:17-jre-alpine，COPY jar文件，EXPOSE 8080 |
| FR-002 | P0 | Dockerfile运行阶段：WORKDIR /app，COPY jar为app.jar，ENTRYPOINT激活prod profile，HEALTHCHECK（curl -f http://localhost:8080/health，interval=30s，timeout=10s，retries=3） |
| FR-003 | P0 | docker-compose.yml定义5个服务：mysql、redis、ai-service、java-backend、frontend |
| FR-004 | P0 | mysql服务：image=mysql:8.0，端口3306，environment含MYSQL_ROOT_PASSWORD/MYSQL_DATABASE，volume持久化+SQL初始化脚本挂载（/docker-entrypoint-initdb.d/），healthcheck（mysqladmin ping） |
| FR-005 | P0 | redis服务：image=redis:7-alpine，端口6379，command=redis-server --appendonly yes（AOF持久化），healthcheck（redis-cli ping） |
| FR-006 | P0 | java-backend服务：build=./backend-java，端口8080，environment注入SPRING_PROFILES_ACTIVE=prod及所有数据库/Redis/AI服务连接变量，depends_on={mysql/redis/ai-service condition=service_healthy}，healthcheck |
| FR-007 | P1 | ai-service和frontend服务使用占位定义（标注#TODO待后续完善） |
| FR-008 | P0 | 创建.env.example模板文件，包含所有环境变量及注释说明 |
| FR-009 | P0 | docker-compose.yml定义顶级networks(app-network, driver=bridge)和volumes(mysql_data) |
| FR-010 | P0 | 启动顺序通过depends_on + healthcheck保证：mysql → redis → ai-service → java-backend → frontend |

## 跨系统数据流

Docker内服务间通过服务名通信：
- java-backend → mysql:3306
- java-backend → redis:6379
- java-backend → ai-service:8000
- frontend → java-backend:8080

## 关键约束

- **必须多阶段构建**，运行阶段仅JRE，减小镜像体积（目标<200MB）
- **禁止**在docker-compose.yml中硬编码敏感配置，必须通过 `${VAR}` 引用.env文件
- **禁止**省略healthcheck配置
- **禁止**省略depends_on的condition: service_healthy
- **禁止**省略MySQL volume持久化
- **禁止**.env.example中包含真实密码
- Redis必须配置AOF持久化（JWT黑名单等关键数据需要）
- Dockerfile应以非root用户运行

## 验收标准

| ID | 标准 | 验证方式 |
|----|------|---------|
| AC-001 | Dockerfile使用多阶段构建（build阶段jdk-alpine + run阶段jre-alpine） | 代码审查 |
| AC-002 | docker build构建成功，镜像大小<200MB | 自动测试 |
| AC-003 | Dockerfile中ENTRYPOINT激活prod profile | 代码审查 |
| AC-004 | Dockerfile包含HEALTHCHECK配置 | 代码审查 |
| AC-005 | docker-compose.yml定义5个服务 | 代码审查 |
| AC-006 | mysql服务配置volume持久化+初始化脚本挂载+healthcheck | 代码审查 |
| AC-007 | redis服务配置AOF持久化+healthcheck | 代码审查 |
| AC-008 | java-backend服务环境变量正确注入 | 代码审查 |
| AC-009 | 服务依赖顺序正确，使用condition: service_healthy | 代码审查 |
| AC-010 | docker-compose.yml中无硬编码敏感信息 | 代码审查 |
| AC-011 | .env.example模板文件包含所有环境变量及注释说明 | 代码审查 |
| AC-012 | docker-compose config验证通过，无YAML语法错误 | 自动测试 |
| AC-013 | 顶级networks(app-network)和volumes(mysql_data)定义正确 | 代码审查 |

## 验证命令

```bash
# 验证Docker镜像构建
cd backend-java && docker build -t literature-assistant-backend .

# 验证docker-compose配置
docker-compose config

# 启动基础服务
docker-compose up -d mysql redis

# 验证MySQL初始化
docker exec -it $(docker ps -qf name=mysql) mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "SHOW DATABASES LIKE 'literature_assistant'"

# 验证Redis
docker exec -it $(docker ps -qf name=redis) redis-cli ping
```
