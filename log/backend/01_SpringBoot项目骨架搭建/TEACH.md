# 技术教学文档

## 开发思路
- 需求分析过程：
  - 根据 task01_springboot_maven.json 规范，明确需要创建 Spring Boot 3.2+ 项目骨架
  - 核心需求：Maven 依赖配置 + 标准包结构 + 启动类 + 基础配置
  - 关键约束：必须使用 webflux（非 web）、Lombok + MapStruct 必须共存、版本必须锁定
- 技术选型考虑：
  - Spring Boot 3.2.5：最新稳定版，支持 Java 17+、Virtual Threads 预览
  - webflux 而非 web：项目需要 WebClient 调用 Python AI 服务 + SSE 推送 Agent 状态
  - MapStruct 1.5.5.Final：编译期代码生成，性能优于运行时反射（如 ModelMapper）
  - jjwt 0.12.5：JWT 认证，api/impl/jackson 三件套分离
- 架构设计思路：
  - Parent POM 统一管理 Spring 依赖版本，避免版本冲突
  - 分层包结构：Controller → Service → Repository → Client，禁止跨层
  - dto 拆分为 request/response/common 三个子包，Entity 与 DTO 严格分离
- 遇到的问题及解决方案：
  - 问题1：MySQL connector groupId 在 Spring Boot 3.2.x 中从 `mysql` 变更为 `com.mysql`，导致 `mvn validate` 报错 version missing
    - 解决：将 groupId 改为 `com.mysql`，版本由 Parent POM 管理
  - 问题2：Lombok 和 MapStruct 注解处理器冲突
    - 解决：在 maven-compiler-plugin 的 annotationProcessorPaths 中添加 `lombok-mapstruct-binding`，确保两者共存

## 实现步骤
1. 第一步：迁移 SQL 文件从旧 `backend-java/` 到新 `Veritas/backend/src/main/resources/db/`
2. 第二步：创建 pom.xml，配置 Spring Boot 3.2.5 Parent + 全部依赖 + maven-compiler-plugin（Lombok + MapStruct + binding）
3. 第三步：创建 LiteratureAssistantApplication.java 启动类
4. 第四步：创建14个标准包目录 + .gitkeep 占位文件
5. 第五步：创建 application.yml 最小配置
6. 第六步：创建 LiteratureAssistantApplicationTests.java 测试类
7. 第七步：创建 .gitignore
8. 第八步：验证 mvn validate → dependency:resolve → compile → 目录结构检查
9. 第九步：更新 AGENTS.md 项目目录结构

## 解决了什么问题
- 核心问题描述：项目需要从零搭建 Java 后端，且必须满足 webflux（SSE）、Lombok+MapStruct 共存、JWT 认证等特定需求
- 解决方案对比：
  - 方案A：使用 Spring Initializr 生成 → 需要手动补充依赖和包结构
  - 方案B：手动创建所有文件 → 完全可控，符合项目规范
  - 最终选择方案B，因为项目有特定的包结构和依赖配置要求
- 最终方案的优势：
  - 完全符合架构文档规范
  - Lombok + MapStruct 注解处理器正确配置，编译期无冲突
  - webflux 支持 WebClient + SSE，为后续 AI 服务调用和 Agent 状态推送提供基础

## 变更内容
### 新增文件
- `Veritas/backend/pom.xml` — Maven 项目配置
- `Veritas/backend/src/main/java/com/literatureassistant/LiteratureAssistantApplication.java` — 启动类
- `Veritas/backend/src/main/java/com/literatureassistant/{config,controller,service,repository,entity,client,mapper,filter,exception,enums,util}/.gitkeep` — 11个包占位
- `Veritas/backend/src/main/java/com/literatureassistant/dto/{request,response,common}/.gitkeep` — 3个DTO子包占位
- `Veritas/backend/src/main/resources/application.yml` — 最小配置
- `Veritas/backend/src/test/java/com/literatureassistant/LiteratureAssistantApplicationTests.java` — 测试类
- `Veritas/backend/.gitignore` — 忽略规则

### 修改文件
- `AGENTS.md` — 项目目录结构中 `backend-java/` 更新为 `Veritas/backend/`，补充 dto 子包和 mapper/filter/exception/enums 包

### 配置变更
- `pom.xml` properties: java.version=17, jjwt.version=0.12.5, mapstruct.version=1.5.5.Final
- `application.yml`: spring.application.name=literature-assistant, spring.profiles.active=dev

## 关键技术点
- 使用的核心技术：
  - Spring Boot 3.2.5 + Spring WebFlux（响应式 Web 框架）
  - Spring Data JPA + Spring Data Redis
  - MapStruct 1.5.5.Final（编译期对象映射）
  - Lombok 1.18.32（编译期代码简化）
  - JJWT 0.12.5（JWT Token 生成/验证）
- 代码实现亮点：
  - maven-compiler-plugin 的 annotationProcessorPaths 三层配置：lombok → lombok-mapstruct-binding → mapstruct-processor
  - 使用 `${lombok.version}` 和 `${mapstruct.version}` 属性引用，避免版本号硬编码
  - spring-boot-maven-plugin 排除 Lombok 依赖，避免打包进最终 JAR
- 需要注意的细节：
  - Spring Boot 3.2.x 中 MySQL connector 的 groupId 是 `com.mysql` 而非 `mysql`
  - webflux 和 web 不能同时引入，否则会冲突
  - jjwt-impl 和 jjwt-jackson 必须设为 runtime scope

## 经验总结
- 开发过程中的收获：
  - Spring Boot 3.x 的依赖管理比 2.x 更严格，groupId 变更需要特别注意
  - Lombok + MapStruct 共存是一个常见但容易出错的配置点，lombok-mapstruct-binding 是关键
  - 项目目录结构的规范化对后续开发效率影响很大
- 踩过的坑及如何避免：
  - 坑1：MySQL connector groupId 变更导致 mvn validate 失败
    - 避免：使用 Spring Boot Parent POM 管理的依赖时，先确认 Parent 中定义的 groupId
  - 坑2：pom.xml 被意外覆盖为错误内容（缺少 webflux/jjwt/lombok/mapstruct 等依赖）
    - 避免：写入文件后应立即验证内容是否正确
- 最佳实践建议：
  - 创建 pom.xml 后立即执行 `mvn validate` 验证格式
  - 使用 `mvn dependency:tree | grep` 检查关键依赖是否正确引入
  - 包结构创建使用脚本批量执行，避免遗漏
  - .gitkeep 是 Git 追踪空目录的标准做法，不可省略
