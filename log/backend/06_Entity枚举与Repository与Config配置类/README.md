# Entity枚举与Repository与Config配置类

## 功能描述
- 解决了Java后端数据层（Entity/Enum）、数据访问层（Repository）和基础设施配置层（Config）的从0到1搭建问题
- 实现了6个JPA实体类严格对应DDL、6个枚举类（3个含code/label映射+fromCode方法）、6个Repository接口（含全文检索原生SQL）、3个核心配置类（Redis缓存TTL分层+WebClient超时连接池+Security JWT白名单CORS）
- 业务价值：为Service层提供完整的数据访问能力，为缓存/HTTP调用/安全认证提供基础设施支撑，是M1里程碑的核心交付

## 实现逻辑

### 修改的核心文件列表

**新增21个Java文件：**

| 分类 | 文件 | 说明 |
|------|------|------|
| 枚举 | `enums/EducationLevel.java` | 学历层次：UNDERGRADUATE/MASTER/PHD/FACULTY |
| 枚举 | `enums/KnowledgeLevel.java` | 知识水平：BEGINNER/INTERMEDIATE/ADVANCED/EXPERT |
| 枚举 | `enums/PreferredStyle.java` | 偏好风格：SIMPLE/BALANCED/TECHNICAL |
| 枚举 | `enums/SessionStatus.java` | 会话状态：ACTIVE/COMPLETED/EXPIRED |
| 枚举 | `enums/AnalysisType.java` | 分析类型：PAPER_ANALYSIS/COMPARE/REPORT |
| 枚举 | `enums/AnalysisStatus.java` | 分析状态：PENDING/PROCESSING/COMPLETED/FAILED |
| 实体 | `entity/User.java` | 用户实体，自定义toString()排除passwordHash |
| 实体 | `entity/UserProfile.java` | 用户画像，3个@Enumerated(STRING)+JSON字段 |
| 实体 | `entity/Paper.java` | 论文实体，abstractText→abstract列映射 |
| 实体 | `entity/Session.java` | 会话实体，SessionStatus枚举 |
| 实体 | `entity/AnalysisResult.java` | 分析结果，2个枚举+JSON result字段 |
| 实体 | `entity/PaperFavorite.java` | 论文收藏 |
| 仓库 | `repository/UserRepository.java` | findByUserId/findByUsername/existsByUsername/existsByEmail |
| 仓库 | `repository/UserProfileRepository.java` | findByUserId/existsByUserId |
| 仓库 | `repository/PaperRepository.java` | +JpaSpecificationExecutor，searchByKeyword全文检索 |
| 仓库 | `repository/SessionRepository.java` | findByUserIdOrderByCreatedAtDesc（数据隔离） |
| 仓库 | `repository/AnalysisResultRepository.java` | findBySessionIdAndStatus |
| 仓库 | `repository/PaperFavoriteRepository.java` | existsByUserIdAndPaperId/deleteByUserIdAndPaperId |
| 配置 | `config/RedisConfig.java` | CacheManager(6缓存空间TTL分层+±10%偏移)+RedisTemplate |
| 配置 | `config/WebClientConfig.java` | 连接池50+超时5s/30s+16MB缓冲+SSE支持 |
| 配置 | `config/SecurityConfig.java` | CSRF禁用+STATELESS+白名单5路径+CORS从yml读取 |

**修改2个配置文件：**
- `pom.xml`：添加 `spring-boot-starter-web` + `spring-boot-starter-security`
- `application.yml`：添加 `cors.allowed-origins` 配置项

### 使用的算法或设计模式
- **Cache-Aside模式**：RedisConfig配置的CacheManager配合@Cacheable/@CacheEvict注解实现写后删缓存
- **TTL分层+随机偏移**：6个缓存空间自定义TTL（10min~2h），±10%随机偏移防缓存雪崩
- **数据隔离模式**：SessionRepository和PaperFavoriteRepository强制userId过滤，防止越权访问
- **Servlet+WebFlux共存**：spring-boot-starter-web使应用以Tomcat启动，WebClient在Servlet模式下正常工作

### 关键代码逻辑说明

1. **Paper.abstractText映射**：Java中`abstract`是保留字，字段名用`abstractText`，通过`@Column(name="abstract")`映射到DDL的`abstract`列
2. **User.toString()安全**：自定义toString()排除passwordHash，防止日志泄露密码
3. **PaperRepository.searchByKeyword**：使用MySQL FULLTEXT索引的`MATCH...AGAINST`原生SQL，支持条件过滤+动态排序+分页
4. **RedisConfig.applyJitter**：TTL添加±10%随机偏移，使用ThreadLocalRandom保证线程安全
5. **SecurityConfig白名单**：`/api/users/register`、`/api/users/login`、`/health`、`/actuator/**`、`/error`无需Token
6. **SecurityConfig CORS**：从yml读取`cors.allowed-origins`，逗号分隔支持多Origin

## 接口变更

### Request
本次为数据层+配置层开发，不涉及API接口变更。Repository方法供Service层内部调用。

### Response
无API接口变更。

## 测试结果
- 测试场景1：`mvn clean compile` — BUILD SUCCESS，34个源文件编译通过
- 测试场景2：`mvn clean test` — BUILD SUCCESS，85个测试全部通过，0失败0错误
- 是否通过：是

## 相关文件

### 新增代码文件
- `Veritas/backend/src/main/java/com/literatureassistant/enums/EducationLevel.java`
- `Veritas/backend/src/main/java/com/literatureassistant/enums/KnowledgeLevel.java`
- `Veritas/backend/src/main/java/com/literatureassistant/enums/PreferredStyle.java`
- `Veritas/backend/src/main/java/com/literatureassistant/enums/SessionStatus.java`
- `Veritas/backend/src/main/java/com/literatureassistant/enums/AnalysisType.java`
- `Veritas/backend/src/main/java/com/literatureassistant/enums/AnalysisStatus.java`
- `Veritas/backend/src/main/java/com/literatureassistant/entity/User.java`
- `Veritas/backend/src/main/java/com/literatureassistant/entity/UserProfile.java`
- `Veritas/backend/src/main/java/com/literatureassistant/entity/Paper.java`
- `Veritas/backend/src/main/java/com/literatureassistant/entity/Session.java`
- `Veritas/backend/src/main/java/com/literatureassistant/entity/AnalysisResult.java`
- `Veritas/backend/src/main/java/com/literatureassistant/entity/PaperFavorite.java`
- `Veritas/backend/src/main/java/com/literatureassistant/repository/UserRepository.java`
- `Veritas/backend/src/main/java/com/literatureassistant/repository/UserProfileRepository.java`
- `Veritas/backend/src/main/java/com/literatureassistant/repository/PaperRepository.java`
- `Veritas/backend/src/main/java/com/literatureassistant/repository/SessionRepository.java`
- `Veritas/backend/src/main/java/com/literatureassistant/repository/AnalysisResultRepository.java`
- `Veritas/backend/src/main/java/com/literatureassistant/repository/PaperFavoriteRepository.java`
- `Veritas/backend/src/main/java/com/literatureassistant/config/RedisConfig.java`
- `Veritas/backend/src/main/java/com/literatureassistant/config/WebClientConfig.java`
- `Veritas/backend/src/main/java/com/literatureassistant/config/SecurityConfig.java`

### 配置文件变更
- `Veritas/backend/pom.xml` — 添加spring-boot-starter-web、spring-boot-starter-security依赖
- `Veritas/backend/src/main/resources/application.yml` — 添加cors.allowed-origins配置项
