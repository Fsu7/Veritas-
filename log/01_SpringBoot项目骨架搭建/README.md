# Spring Boot 项目骨架搭建

## 功能描述
- 解决了 Java 后端项目从零搭建的问题，建立了标准化的 Spring Boot 3.2+ 项目骨架
- 实现了完整的 Maven 依赖管理（webflux/jpa/redis/validation/mysql/jjwt/lombok/mapstruct）、标准包结构、启动类和基础配置
- 业务价值：为后续 F2.1~F2.6 六大业务模块开发提供统一的项目基础和编码规范约束

## 实现逻辑
- 修改的核心文件列表：
  - `Veritas/backend/pom.xml` — Maven 项目配置，Spring Boot 3.2.5 Parent + 全部依赖 + Lombok/MapStruct 注解处理器
  - `Veritas/backend/src/main/java/com/literatureassistant/LiteratureAssistantApplication.java` — Spring Boot 启动类
  - `Veritas/backend/src/main/resources/application.yml` — 最小化配置（应用名 + profiles.active=dev）
  - `Veritas/backend/src/test/java/com/literatureassistant/LiteratureAssistantApplicationTests.java` — Spring 上下文加载测试
  - `Veritas/backend/.gitignore` — Java 项目忽略规则
  - 14个包目录 + .gitkeep 占位文件
  - `AGENTS.md` — 更新项目目录结构路径
- 使用的算法或设计模式：
  - Spring Boot Parent POM 统一版本管理
  - Lombok + MapStruct 注解处理器共存配置（lombok-mapstruct-binding）
  - Cache-Aside 缓存模式预留
- 关键代码逻辑说明：
  - maven-compiler-plugin 的 annotationProcessorPaths 必须按 lombok → lombok-mapstruct-binding → mapstruct-processor 顺序配置
  - 使用 webflux 而非 web，因为项目需要 WebClient + SSE 支持
  - jjwt 三件套：api(compile) + impl(runtime) + jackson(runtime)

## 接口变更
本次为项目骨架搭建，无 API 接口变更。

### Request
```json
{}
```

### Response
```json
{}
```

## 测试结果
- 测试场景1：`mvn validate` — BUILD SUCCESS，POM 格式正确
- 测试场景2：`mvn dependency:resolve` — BUILD SUCCESS，所有依赖下载完毕
- 测试场景3：`mvn compile` — BUILD SUCCESS，编译通过
- 测试场景4：依赖树关键检查 — webflux(非web)/jpa/redis/validation/mysql-connector-j/jjwt 0.12.5/lombok 1.18.32/mapstruct 1.5.5.Final 全部正确
- 测试场景5：包结构检查 — 16个目录（根包 + 14个子包 + dto子包）与架构文档§3.1一致
- 是否通过：是

## 相关文件
- `Veritas/backend/pom.xml`
- `Veritas/backend/src/main/java/com/literatureassistant/LiteratureAssistantApplication.java`
- `Veritas/backend/src/main/java/com/literatureassistant/config/.gitkeep`
- `Veritas/backend/src/main/java/com/literatureassistant/controller/.gitkeep`
- `Veritas/backend/src/main/java/com/literatureassistant/service/.gitkeep`
- `Veritas/backend/src/main/java/com/literatureassistant/repository/.gitkeep`
- `Veritas/backend/src/main/java/com/literatureassistant/entity/.gitkeep`
- `Veritas/backend/src/main/java/com/literatureassistant/dto/request/.gitkeep`
- `Veritas/backend/src/main/java/com/literatureassistant/dto/response/.gitkeep`
- `Veritas/backend/src/main/java/com/literatureassistant/dto/common/.gitkeep`
- `Veritas/backend/src/main/java/com/literatureassistant/client/.gitkeep`
- `Veritas/backend/src/main/java/com/literatureassistant/mapper/.gitkeep`
- `Veritas/backend/src/main/java/com/literatureassistant/filter/.gitkeep`
- `Veritas/backend/src/main/java/com/literatureassistant/exception/.gitkeep`
- `Veritas/backend/src/main/java/com/literatureassistant/enums/.gitkeep`
- `Veritas/backend/src/main/java/com/literatureassistant/util/.gitkeep`
- `Veritas/backend/src/main/resources/application.yml`
- `Veritas/backend/src/main/resources/db/01_create_tables.sql`（从 backend-java/ 迁移）
- `Veritas/backend/src/main/resources/db/02_create_indexes.sql`（从 backend-java/ 迁移）
- `Veritas/backend/src/main/resources/db/03_insert_seed_data.sql`（从 backend-java/ 迁移）
- `Veritas/backend/src/test/java/com/literatureassistant/LiteratureAssistantApplicationTests.java`
- `Veritas/backend/.gitignore`
- `AGENTS.md`（路径更新）
