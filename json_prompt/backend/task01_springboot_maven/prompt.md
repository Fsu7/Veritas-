# Task01: Spring Boot 项目骨架与 Maven 配置

| 项目 | 内容 |
|------|------|
| **项目** | XH-202630 科研文献智能助手 |
| **版本** | v0.1 |
| **里程碑** | M1：基础设施就绪 / JM1：项目骨架与数据层就绪 |
| **功能编号** | F2.1, F2.2, F2.3, F2.4, F2.5, F2.6 |

## 需求描述

使用Spring Initializr创建Spring Boot 3.2+项目骨架，groupId=com.literatureassistant，artifactId=backend-java，Java 17，Maven构建。pom.xml包含全部必需依赖（spring-boot-starter-webflux、spring-boot-starter-data-jpa、spring-boot-starter-data-redis、spring-boot-starter-validation、mysql-connector-j、jjwt 0.12.5、lombok、mapstruct 1.5.5.Final、spring-boot-starter-test），并创建标准包结构和启动类。

## 涉及层级

- **java_backend** — com.literatureassistant

## 需要修改/新增的文件

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `backend-java/pom.xml` | Maven项目配置，含Spring Boot Parent、全部依赖、编译插件 |
| 新增 | `backend-java/src/main/java/com/literatureassistant/LiteratureAssistantApplication.java` | Spring Boot启动类 |
| 新增 | `backend-java/src/main/java/com/literatureassistant/config/.gitkeep` | config包占位 |
| 新增 | `backend-java/src/main/java/com/literatureassistant/controller/.gitkeep` | controller包占位 |
| 新增 | `backend-java/src/main/java/com/literatureassistant/service/.gitkeep` | service包占位 |
| 新增 | `backend-java/src/main/java/com/literatureassistant/repository/.gitkeep` | repository包占位 |
| 新增 | `backend-java/src/main/java/com/literatureassistant/entity/.gitkeep` | entity包占位 |
| 新增 | `backend-java/src/main/java/com/literatureassistant/dto/request/.gitkeep` | dto/request包占位 |
| 新增 | `backend-java/src/main/java/com/literatureassistant/dto/response/.gitkeep` | dto/response包占位 |
| 新增 | `backend-java/src/main/java/com/literatureassistant/dto/common/.gitkeep` | dto/common包占位 |
| 新增 | `backend-java/src/main/java/com/literatureassistant/client/.gitkeep` | client包占位 |
| 新增 | `backend-java/src/main/java/com/literatureassistant/mapper/.gitkeep` | mapper包占位 |
| 新增 | `backend-java/src/main/java/com/literatureassistant/filter/.gitkeep` | filter包占位 |
| 新增 | `backend-java/src/main/java/com/literatureassistant/exception/.gitkeep` | exception包占位 |
| 新增 | `backend-java/src/main/java/com/literatureassistant/enums/.gitkeep` | enums包占位 |
| 新增 | `backend-java/src/main/java/com/literatureassistant/util/.gitkeep` | util包占位 |
| 新增 | `backend-java/src/main/resources/application.yml` | 主配置文件（仅spring.application.name和spring.profiles.active=dev） |
| 新增 | `backend-java/src/test/java/com/literatureassistant/LiteratureAssistantApplicationTests.java` | Spring Boot启动测试类 |
| 新增 | `backend-java/.gitignore` | Java项目gitignore |

## 功能要求

| ID | 优先级 | 描述 |
|----|--------|------|
| FR-001 | P0 | pom.xml使用spring-boot-starter-parent 3.2.x作为Parent POM，groupId=com.literatureassistant，artifactId=backend-java，java.version=17 |
| FR-002 | P0 | pom.xml包含以下依赖：spring-boot-starter-webflux（**非starter-web**，因为需要WebClient+SSE）、spring-boot-starter-data-jpa、spring-boot-starter-data-redis、spring-boot-starter-validation、mysql-connector-j(runtime)、jjwt-api/jjwt-impl/jjwt-jackson(0.12.5, impl和jackson为runtime)、lombok(optional)、mapstruct(1.5.5.Final)、spring-boot-starter-test(test scope) |
| FR-003 | P0 | maven-compiler-plugin配置Java 17，并添加Lombok和MapStruct的annotationProcessorPaths，确保Lombok和MapStruct注解处理器共存（Lombok需使用lombok-mapstruct-binding绑定） |
| FR-004 | P0 | 创建LiteratureAssistantApplication启动类，@SpringBootApplication注解，标准main方法 |
| FR-005 | P0 | 创建标准包结构：config/controller/service/repository/entity/dto(request/response/common)/client/mapper/filter/exception/enums/util，每个包放.gitkeep占位 |
| FR-006 | P0 | application.yml仅包含spring.application.name=literature-assistant和spring.profiles.active=dev（详细配置在任务2中完成） |
| FR-007 | P1 | 创建LiteratureAssistantApplicationTests测试类，@SpringBootTest注解，包含contextLoads()测试方法 |

## 关键约束

- **必须使用 webflux 而非 starter-web**（项目需要WebClient+SSE支持）
- Lombok和MapStruct注解处理器必须通过 lombok-mapstruct-binding 共存
- Maven依赖必须锁定版本号，禁止使用RELEASE/LATEST
- 禁止硬编码敏感配置，所有敏感信息通过 `${VAR}` 环境变量引用

## 验收标准

| ID | 标准 | 验证方式 |
|----|------|---------|
| AC-001 | pom.xml使用spring-boot-starter-parent 3.2.x，Java 17，groupId和artifactId正确 | 代码审查 |
| AC-002 | 所有必需依赖已声明且版本锁定：webflux/jpa/redis/validation/mysql-connector/jjwt/lombok/mapstruct/test | 代码审查 |
| AC-003 | maven-compiler-plugin配置了Lombok+MapStruct annotationProcessorPaths，含lombok-mapstruct-binding | 代码审查 |
| AC-004 | mvn compile 成功，无编译错误 | 自动测试 |
| AC-005 | LiteratureAssistantApplication启动类存在且注解正确 | 代码审查 |
| AC-006 | 包结构与架构文档§3.1完全一致（16个包目录） | 代码审查 |
| AC-007 | application.yml包含spring.application.name和spring.profiles.active=dev | 代码审查 |
| AC-008 | pom.xml中无硬编码敏感信息 | 代码审查 |
| AC-009 | .gitignore包含target/、*.class、.idea/、*.iml | 代码审查 |
| AC-010 | mvn dependency:tree 无依赖冲突 | 自动测试 |

## 验证命令

```bash
# 验证POM格式
cd backend-java && mvn validate

# 验证依赖下载
cd backend-java && mvn dependency:resolve

# 验证编译（含MapStruct生成）
cd backend-java && mvn compile

# 验证包结构
cd backend-java && find src/main/java/com/literatureassistant -type d | sort
```
