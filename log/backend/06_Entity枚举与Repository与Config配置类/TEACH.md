# 技术教学文档

## 开发思路

### 需求分析过程
本次开发涵盖三个顺序依赖的任务：
1. **Task08 Entity/Enum**：数据层基础，所有上层代码依赖Entity和Enum
2. **Task09 Repository**：数据访问层，依赖Entity定义
3. **Task10 Config**：基础设施配置层，依赖pom.xml依赖和application.yml配置

三个任务存在严格的依赖关系：Enum → Entity → Repository → Config，必须按顺序实施。

### 技术选型考虑
1. **枚举设计**：EducationLevel/KnowledgeLevel/PreferredStyle需要与Python/JSON端互通，因此设计code字段存储lower_case值（如"undergraduate"），label字段存储中文描述。Java端枚举名用UPPER_SNAKE_CASE，通过code字段实现跨系统映射
2. **Entity序列化**：JSON字段（authors、keywords、profileData、result）使用`columnDefinition="JSON"`让MySQL做JSON校验，Java端用String存储，在Service层用Jackson序列化/反序列化
3. **Repository全文检索**：MySQL 8.0的ngram全文索引支持中文分词，使用`MATCH...AGAINST`原生SQL比JPA Criteria API更高效
4. **Spring Security栈选择**：使用Servlet栈（HttpSecurity）而非响应式栈（ServerHttpSecurity），因为JWT鉴权过滤器OncePerRequestFilter是Servlet API

### 架构设计思路
```
┌─────────────────────────────────────────────┐
│                  Config层                    │
│  RedisConfig    WebClientConfig   SecurityConfig │
│  (缓存基础设施)  (HTTP调用基础设施)  (安全基础设施)  │
├─────────────────────────────────────────────┤
│                Repository层                  │
│  6个Repository接口 + JpaSpecificationExecutor │
├─────────────────────────────────────────────┤
│                 Entity层                     │
│  6个Entity + 6个Enum                        │
├─────────────────────────────────────────────┤
│                  DDL层                       │
│  01_create_tables.sql (MySQL 8.0)           │
└─────────────────────────────────────────────┘
```

### 遇到的问题及解决方案

**问题1：`abstract`是Java保留字**
- DDL中papers表有`abstract`列，但Java中`abstract`是保留字不能作字段名
- 解决：Java字段名用`abstractText`，通过`@Column(name="abstract")`映射到DDL的`abstract`列

**问题2：Spring WebFlux与Spring Security Servlet栈冲突**
- 原pom.xml仅有webflux，应用以Netty启动，SecurityConfig的HttpSecurity不可用
- 解决：添加spring-boot-starter-web使应用以Tomcat启动，WebClient在Servlet模式下仍正常工作

**问题3：pom.xml重复依赖**
- 编辑过程中意外引入重复的spring-boot-starter-web和spring-boot-starter-security声明
- 解决：手动去重，确保每个依赖只声明一次

**问题4：SecurityConfig中JwtAuthFilter尚未实现**
- Task10要求在SecurityConfig中预留JwtAuthFilter位置，但JwtAuthFilter在task12才实现
- 解决：暂不添加addFilterBefore，等task12实现JwtAuthFilter后再补充

## 实现步骤

1. **修改pom.xml**：添加spring-boot-starter-web和spring-boot-starter-security依赖，使应用以Servlet模式运行
2. **修改application.yml**：添加`cors.allowed-origins`配置项，供SecurityConfig从yml读取
3. **创建6个枚举类**：3个含code/label映射的枚举（EducationLevel/KnowledgeLevel/PreferredStyle）+ 3个纯枚举（SessionStatus/AnalysisType/AnalysisStatus）
4. **创建6个Entity类**：严格对应DDL，使用@Data @NoArgsConstructor @AllArgsConstructor @Builder注解，@PrePersist/@PreUpdate自动填充时间戳
5. **创建6个Repository接口**：继承JpaRepository，类级别@Transactional(readOnly=true)，PaperRepository额外继承JpaSpecificationExecutor
6. **创建3个Config类**：RedisConfig（CacheManager+RedisTemplate+TTL分层+随机偏移）、WebClientConfig（连接池+超时+缓冲区）、SecurityConfig（过滤器链+白名单+CORS）
7. **编译验证**：mvn clean compile + mvn clean test

## 解决了什么问题

### 核心问题描述
1. Java后端缺乏与DDL对应的数据模型，无法进行数据库操作
2. 缺少缓存基础设施，Service层无法使用@Cacheable注解
3. 缺少HTTP客户端配置，无法调用Python AI服务
4. 缺少安全配置，所有API裸露无鉴权保护

### 解决方案对比
| 问题 | 方案A | 方案B | 最终选择 |
|------|-------|-------|---------|
| JSON字段存储 | 用@Convert自定义转换器 | String+Jackson手动转换 | 方案B：更灵活，Service层控制序列化 |
| 缓存序列化 | JDK默认序列化 | GenericJackson2JsonRedisSerializer | 方案B：可读性好，跨语言兼容 |
| 全文检索 | JPA Criteria API | MySQL MATCH...AGAINST原生SQL | 方案B：性能更好，支持中文ngram |
| 安全框架 | Spring Security Servlet栈 | Spring Security WebFlux栈 | 方案A：JWT过滤器OncePerRequestFilter是Servlet API |

### 最终方案的优势
- Entity严格对应DDL，Hibernate自动建表时不会产生schema差异
- Redis TTL分层+随机偏移，兼顾缓存命中率和雪崩防护
- SecurityConfig从yml读取CORS配置，环境切换无需改代码
- WebClient连接池+超时配置，避免请求阻塞导致线程耗尽

## 变更内容

### 新增文件
- `enums/EducationLevel.java` — 学历层次枚举，含code/label/fromCode
- `enums/KnowledgeLevel.java` — 知识水平枚举，含code/label/fromCode
- `enums/PreferredStyle.java` — 偏好风格枚举，含code/label/fromCode
- `enums/SessionStatus.java` — 会话状态纯枚举
- `enums/AnalysisType.java` — 分析类型纯枚举
- `enums/AnalysisStatus.java` — 分析状态纯枚举
- `entity/User.java` — 用户实体，自定义toString()排除passwordHash
- `entity/UserProfile.java` — 用户画像实体，3个枚举字段+JSON字段
- `entity/Paper.java` — 论文实体，abstractText→abstract列映射
- `entity/Session.java` — 会话实体
- `entity/AnalysisResult.java` — 分析结果实体
- `entity/PaperFavorite.java` — 论文收藏实体
- `repository/UserRepository.java` — 用户数据访问
- `repository/UserProfileRepository.java` — 画像数据访问
- `repository/PaperRepository.java` — 论文数据访问+全文检索
- `repository/SessionRepository.java` — 会话数据访问（数据隔离）
- `repository/AnalysisResultRepository.java` — 分析结果数据访问
- `repository/PaperFavoriteRepository.java` — 收藏数据访问（数据隔离）
- `config/RedisConfig.java` — Redis缓存配置（6缓存空间TTL分层+随机偏移）
- `config/WebClientConfig.java` — WebClient配置（连接池+超时+SSE）
- `config/SecurityConfig.java` — Spring Security配置（JWT白名单+CORS）

### 修改文件
- `pom.xml` — 添加spring-boot-starter-web、spring-boot-starter-security依赖
- `application.yml` — 添加cors.allowed-origins配置项

### 配置变更
- `cors.allowed-origins: ${CORS_ALLOWED_ORIGINS:http://localhost:5173}` — CORS允许的Origin列表，支持环境变量注入

## 关键技术点

### 1. JPA枚举映射策略
```java
@Enumerated(EnumType.STRING)
@Column(name = "education_level", length = 20)
private EducationLevel educationLevel;
```
使用`EnumType.STRING`而非`ORDINAL`，原因：
- STRING存储枚举名（如"UNDERGRADUATE"），可读性好
- ORDINAL存储序号（如0,1,2,3），枚举顺序变更会导致数据错乱
- 配合code字段实现Java UPPER_SNAKE_CASE ↔ JSON lower_case双向映射

### 2. Redis TTL分层+随机偏移防雪崩
```java
private Duration applyJitter(Duration baseTtl) {
    long baseSeconds = baseTtl.getSeconds();
    long jitterSeconds = (long) (baseSeconds * 0.1);
    long randomOffset = ThreadLocalRandom.current().nextLong(-jitterSeconds, jitterSeconds + 1);
    return Duration.ofSeconds(Math.max(1, baseSeconds + randomOffset));
}
```
- 缓存雪崩：大量缓存同时过期导致请求全部打到数据库
- 解决：TTL添加±10%随机偏移，使过期时间分散
- ThreadLocalRandom保证线程安全，Math.max(1,...)防止负数

### 3. WebClient连接池+超时配置
```java
ConnectionProvider provider = ConnectionProvider.builder("ai-service-pool")
    .maxConnections(50)
    .pendingAcquireTimeout(Duration.ofSeconds(30))
    .build();
HttpClient client = HttpClient.create(provider)
    .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, 5000)
    .responseTimeout(Duration.ofSeconds(30));
```
- 连接池maxConnections=50：限制最大连接数，防止资源耗尽
- CONNECT_TIMEOUT=5s：TCP连接超时
- responseTimeout=30s：HTTP响应超时
- maxInMemorySize=16MB：SSE流可能产生大响应，避免BufferOverflowException

### 4. Spring Security白名单+STATELESS
```java
http.csrf(csrf -> csrf.disable())
    .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
    .authorizeHttpRequests(auth -> auth
        .requestMatchers("/api/users/register", "/api/users/login", "/health", "/actuator/**", "/error").permitAll()
        .anyRequest().authenticated());
```
- CSRF禁用：JWT无状态认证不需要CSRF保护
- STATELESS：不创建HttpSession，每次请求通过JWT Token验证身份
- 白名单：注册/登录/健康检查/监控端点无需Token

### 5. MySQL全文检索原生SQL
```sql
SELECT * FROM papers WHERE MATCH(title, abstract) AGAINST(:keyword IN NATURAL LANGUAGE MODE)
AND (:yearFrom IS NULL OR year >= :yearFrom)
ORDER BY CASE WHEN :sort = 'relevance' THEN MATCH(title, abstract) AGAINST(:keyword IN NATURAL LANGUAGE MODE) END DESC
```
- MySQL 8.0 ngram全文索引支持中文分词
- 条件过滤使用IS NULL技巧实现动态条件
- CASE WHEN实现动态排序（相关性/年份/引用量）

## 经验总结

### 开发过程中的收获
1. **DDL优先原则**：先有DDL再有Entity，确保@Column注解与DDL完全一致，避免Hibernate自动建表产生schema差异
2. **依赖顺序思维**：Enum → Entity → Repository → Config，严格按依赖顺序创建文件，避免编译错误
3. **安全意识**：User.toString()排除passwordHash、CORS禁止通配符、JWT Secret环境变量注入

### 踩过的坑及如何避免
1. **pom.xml重复依赖**：编辑时意外引入重复声明，导致Maven警告。避免方式：每次编辑后用`mvn clean compile`验证
2. **abstract保留字**：Java中`abstract`是保留字不能作字段名。避免方式：遇到DDL保留字时用Java安全名+@Column(name=...)映射
3. **WebFlux与Security栈冲突**：SecurityConfig使用HttpSecurity需要Servlet栈，但原pom.xml仅有webflux。避免方式：添加spring-boot-starter-web，理解Spring Boot自动配置的优先级

### 最佳实践建议
1. **Entity注解模板**：`@Data @NoArgsConstructor @AllArgsConstructor @Builder` + `@PrePersist`/`@PreUpdate`是标准组合
2. **Repository类级别@Transactional(readOnly=true)**：所有查询方法自动只读，写方法单独标注@Transactional覆盖
3. **Config类职责单一**：RedisConfig只管Redis、WebClientConfig只管WebClient、SecurityConfig只管安全，不交叉依赖
4. **配置外部化**：CORS allowed-origins、AI服务URL等从yml/环境变量读取，不硬编码
5. **编译验证先行**：每完成一批文件立即`mvn compile`验证，不要等全部写完再编译
