# 任务1：Spring Boot Maven 项目骨架创建计划

## 任务概述

基于 `task01_springboot_maven.json` 规范，创建 Spring Boot 3.2+ 项目骨架，包含完整 Maven 依赖配置、标准包结构、启动类和基础配置文件，最终验证 `mvn compile` 通过。

## 路径修正

* **后端根目录**：`/Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/`（用户指定）

* JSON 任务文件中的 `backend-java/` 路径统一替换为 `Veritas/backend/`

* 现有 `backend-java/src/main/resources/db/` 下的 SQL 文件（任务0创建）需迁移到新路径

## 现有状态

* `Veritas/backend/` 目录不存在，需新建

* 旧路径 `backend-java/` 下有 SQL 文件（任务0创建的），需迁移

* 无 pom.xml、无 Java 源码、无 application.yml

## 实施步骤

### Step 1：迁移现有 SQL 文件

将 `backend-java/src/main/resources/db/` 下的3个SQL文件迁移到 `Veritas/backend/src/main/resources/db/`：

* 01\_create\_tables.sql

* 02\_create\_indexes.sql

* 03\_insert\_seed\_data.sql

### Step 2：创建 `Veritas/backend/pom.xml`

**关键配置：**

* `spring-boot-starter-parent` 3.2.5

* `groupId`: com.literatureassistant

* `artifactId`: backend-java

* `java.version`: 17

**依赖清单（全部版本锁定）：**

| 依赖                             | 版本          | Scope    |
| ------------------------------ | ----------- | -------- |
| spring-boot-starter-webflux    | Parent管理    | compile  |
| spring-boot-starter-data-jpa   | Parent管理    | compile  |
| spring-boot-starter-data-redis | Parent管理    | compile  |
| spring-boot-starter-validation | Parent管理    | compile  |
| mysql-connector-j              | Parent管理    | runtime  |
| jjwt-api                       | 0.12.5      | compile  |
| jjwt-impl                      | 0.12.5      | runtime  |
| jjwt-jackson                   | 0.12.5      | runtime  |
| lombok                         | Parent管理    | optional |
| mapstruct                      | 1.5.5.Final | compile  |
| spring-boot-starter-test       | Parent管理    | test     |

**maven-compiler-plugin 配置（关键！）：**

* source/target: 17

* annotationProcessorPaths 必须包含：

  1. `lombok`（版本由Parent管理）
  2. `lombok-mapstruct-binding`（确保Lombok与MapStruct共存）
  3. `mapstruct-processor` 1.5.5.Final

### Step 3：创建启动类 `LiteratureAssistantApplication.java`

* 路径：`Veritas/backend/src/main/java/com/literatureassistant/LiteratureAssistantApplication.java`

* `@SpringBootApplication` 注解

* 标准 `main` 方法

### Step 4：创建标准包结构（14个包目录 + .gitkeep）

| 包路径           | 说明           |
| ------------- | ------------ |
| config/       | 配置类          |
| controller/   | API控制器       |
| service/      | 业务逻辑         |
| repository/   | 数据访问         |
| entity/       | JPA实体        |
| dto/request/  | 请求DTO        |
| dto/response/ | 响应DTO        |
| dto/common/   | 通用DTO        |
| client/       | 外部服务客户端      |
| mapper/       | MapStruct映射器 |
| filter/       | 过滤器/拦截器      |
| exception/    | 异常定义         |
| enums/        | 枚举定义         |
| util/         | 工具类          |

每个包下创建 `.gitkeep` 占位文件（共14个 .gitkeep）。

### Step 5：创建 `application.yml`

路径：`Veritas/backend/src/main/resources/application.yml`

仅包含最小配置：

```yaml
spring:
  application:
    name: literature-assistant
  profiles:
    active: dev
```

### Step 6：创建测试类 `LiteratureAssistantApplicationTests.java`

* 路径：`Veritas/backend/src/test/java/com/literatureassistant/LiteratureAssistantApplicationTests.java`

* `@SpringBootTest` 注解

* `contextLoads()` 测试方法

### Step 7：创建 `.gitignore`

路径：`Veritas/backend/.gitignore`

包含：target/、*.class、.idea/、*.iml、.DS\_Store、.env 等

### Step 8：验证

1. `cd Veritas/backend && mvn validate` — POM格式正确
2. `cd Veritas/backend && mvn dependency:resolve` — 依赖下载成功
3. `cd Veritas/backend && mvn compile` — 编译成功
4. `find src/main/java/com/literatureassistant -type d | sort` — 包结构完整

## 关键注意事项

1. **必须使用 webflux 而非 web**（项目需要 WebClient + SSE）
2. **Lombok + MapStruct 共存**：必须配置 `lombok-mapstruct-binding`，否则编译会失败
3. **jjwt 三件套**：api(compile) + impl(runtime) + jackson(runtime)
4. **不硬编码敏感信息**：pom.xml 中无密码、密钥等
5. **SQL 文件迁移**：从旧 `backend-java/` 迁移到新 `Veritas/backend/`
6. **Spring Boot 3.2.x 需要 Java 17+**，使用 `java.version` 属性
7. **artifactId 保持 backend-java**（与JSON任务文件一致），虽然目录名是 backend

## 验收标准对照

| AC编号   | 标准                                                           | 验证方式  |
| ------ | ------------------------------------------------------------ | ----- |
| AC-001 | pom.xml使用spring-boot-starter-parent 3.2.x, Java 17           | 代码审查  |
| AC-002 | 所有必需依赖已声明且版本锁定                                               | 代码审查  |
| AC-003 | maven-compiler-plugin配置了Lombok+MapStruct+binding             | 代码审查  |
| AC-004 | mvn compile 成功                                               | 自动化测试 |
| AC-005 | 启动类存在且注解正确                                                   | 代码审查  |
| AC-006 | 包结构与架构文档§3.1一致（14个包目录）                                       | 代码审查  |
| AC-007 | application.yml包含spring.application.name和profiles.active=dev | 代码审查  |
| AC-008 | pom.xml无硬编码敏感信息                                              | 代码审查  |
| AC-009 | .gitignore包含target/、*.class、.idea/、*.iml                     | 代码审查  |
| AC-010 | mvn dependency:tree 无依赖冲突                                    | 自动化测试 |

