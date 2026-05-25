# Task08/09/10 实施计划：Entity/Enum + Repository + Config Classes

> **项目**：XH-202630 科研文献智能助手  
> **里程碑**：M1 基础设施就绪 / JM1 项目骨架与数据层就绪  
> **日期**：2026-05-25

---

## 1 总览

按顺序实施三个任务，共创建 **21个Java文件** + 修改 **2个配置文件**：

| 任务 | 文件数 | 核心内容 |
|------|--------|---------|
| Task08 Entity/Enum | 12个 | 6个Entity + 6个枚举 |
| Task09 Repository | 6个 | 6个Repository接口 |
| Task10 Config | 3个 | RedisConfig + WebClientConfig + SecurityConfig |

---

## 2 前置条件检查

### 2.1 需要添加的Maven依赖（pom.xml）

当前pom.xml缺少 `spring-boot-starter-web` 和 `spring-boot-starter-security`：

- **`spring-boot-starter-web`**：SecurityConfig使用`HttpSecurity`（Servlet模式），需要Web栈切换为Servlet模式（Tomcat）。当前仅有webflux会以Netty启动，导致`HttpSecurity`不可用
- **`spring-boot-starter-security`**：SecurityConfig核心依赖

### 2.2 需要修改的配置文件（application.yml）

添加CORS配置项（SecurityConfig从yml读取）：

```yaml
cors:
  allowed-origins: ${CORS_ALLOWED_ORIGINS:http://localhost:5173}
```

---

## 3 Task08：Entity + Enum（12个文件）

### 3.1 枚举类（6个）

按依赖顺序先创建枚举（Entity引用枚举）：

#### 3.1.1 EducationLevel.java
- 路径：`com.literatureassistant.enums.EducationLevel`
- 枚举值：`UNDERGRADUATE("undergraduate","本科")`, `MASTER("master","硕士")`, `PHD("phd","博士")`, `FACULTY("faculty","教师")`
- 字段：`code(String)`, `label(String)`
- 方法：`fromCode(String code)` → 返回匹配枚举或null
- 构造器：`@Getter` + 私有构造

#### 3.1.2 KnowledgeLevel.java
- 枚举值：`BEGINNER("beginner","初级")`, `INTERMEDIATE("intermediate","中级")`, `ADVANCED("advanced","高级")`, `EXPERT("expert","专家")`
- 同EducationLevel结构

#### 3.1.3 PreferredStyle.java
- 枚举值：`SIMPLE("simple","通俗")`, `BALANCED("balanced","均衡")`, `TECHNICAL("technical","专业")`
- 同EducationLevel结构

#### 3.1.4 SessionStatus.java
- 枚举值：`ACTIVE`, `COMPLETED`, `EXPIRED`
- **无**code/label字段，纯枚举

#### 3.1.5 AnalysisType.java
- 枚举值：`PAPER_ANALYSIS`, `COMPARE`, `REPORT`
- **无**code/label字段，纯枚举

#### 3.1.6 AnalysisStatus.java
- 枚举值：`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`
- **无**code/label字段，纯枚举

### 3.2 Entity类（6个）

严格对应DDL `01_create_tables.sql`：

#### 3.2.1 User.java
- `@Entity @Table(name="users") @Data @NoArgsConstructor @AllArgsConstructor @Builder`
- 字段：
  - `id` (Long, `@Id @GeneratedValue(IDENTITY)`)
  - `userId` (String, `@Column(name="user_id", unique=true, nullable=false, length=100)`)
  - `username` (String, `@Column(nullable=false, length=100)`)
  - `email` (String, `@Column(length=200)`)
  - `passwordHash` (String, `@Column(name="password_hash", nullable=false, length=200)`)
  - `createdAt` (LocalDateTime, `@Column(name="created_at", updatable=false)`)
- `@PrePersist onCreate()` → `createdAt = LocalDateTime.now()`
- **安全**：自定义`toString()`排除passwordHash

#### 3.2.2 UserProfile.java
- `@Entity @Table(name="user_profiles")`
- 字段：
  - `id` (Long)
  - `userId` (String, `@Column(name="user_id", nullable=false, length=100)`)
  - `educationLevel` (EducationLevel, `@Enumerated(STRING) @Column(name="education_level", length=20)`)
  - `researchField` (String, `@Column(name="research_field", length=200)`)
  - `knowledgeLevel` (KnowledgeLevel, `@Enumerated(STRING) @Column(name="knowledge_level", length=20)`)
  - `preferredStyle` (PreferredStyle, `@Enumerated(STRING) @Column(name="preferred_style", length=20)`)
  - `profileData` (String, `@Column(name="profile_data", columnDefinition="JSON")`)
  - `updatedAt` (LocalDateTime, `@Column(name="updated_at")`)
- `@PrePersist @PreUpdate onUpdate()` → `updatedAt = LocalDateTime.now()`

#### 3.2.3 Paper.java
- `@Entity @Table(name="papers")`
- 字段：
  - `id` (Long)
  - `paperId` (String, `@Column(name="paper_id", unique=true, nullable=false, length=100)`)
  - `title` (String, `@Column(nullable=false, length=500)`)
  - `authors` (String, `@Column(columnDefinition="JSON")`)
  - `abstractText` (String, `@Column(name="abstract", columnDefinition="TEXT")`) — **注意**：Java字段名`abstractText`，`@Column(name="abstract")`映射到DDL的`abstract`列
  - `year` (Integer)
  - `venue` (String, `@Column(length=200)`)
  - `keywords` (String, `@Column(columnDefinition="JSON")`)
  - `citationCount` (Integer, `@Column(name="citation_count")`)
  - `pdfUrl` (String, `@Column(name="pdf_url", length=500)`)
  - `createdAt` (LocalDateTime, `@Column(name="created_at", updatable=false)`)
  - `updatedAt` (LocalDateTime, `@Column(name="updated_at")`)
- `@PrePersist onCreate()` → 填充createdAt + updatedAt
- `@PreUpdate onUpdate()` → 填充updatedAt

#### 3.2.4 Session.java
- `@Entity @Table(name="sessions")`
- 字段：
  - `id` (Long)
  - `sessionId` (String, `@Column(name="session_id", unique=true, nullable=false, length=100)`)
  - `userId` (String, `@Column(name="user_id", nullable=false, length=100)`)
  - `topic` (String, `@Column(length=500)`)
  - `status` (SessionStatus, `@Enumerated(STRING) @Column(nullable=false, length=20)`)
  - `createdAt` (LocalDateTime, `@Column(name="created_at", updatable=false)`)
- `@PrePersist onCreate()` → `createdAt = LocalDateTime.now()`

#### 3.2.5 AnalysisResult.java
- `@Entity @Table(name="analysis_results")`
- 字段：
  - `id` (Long)
  - `analysisId` (String, `@Column(name="analysis_id", unique=true, nullable=false, length=100)`)
  - `sessionId` (String, `@Column(name="session_id", nullable=false, length=100)`)
  - `type` (AnalysisType, `@Enumerated(STRING) @Column(nullable=false, length=20)`)
  - `result` (String, `@Column(nullable=false, columnDefinition="JSON")`)
  - `status` (AnalysisStatus, `@Enumerated(STRING) @Column(nullable=false, length=20)`)
  - `createdAt` (LocalDateTime, `@Column(name="created_at", updatable=false)`)
- `@PrePersist onCreate()` → `createdAt = LocalDateTime.now()`

#### 3.2.6 PaperFavorite.java
- `@Entity @Table(name="paper_favorites")`
- 字段：
  - `id` (Long)
  - `userId` (String, `@Column(name="user_id", nullable=false, length=100)`)
  - `paperId` (String, `@Column(name="paper_id", nullable=false, length=100)`)
  - `createdAt` (LocalDateTime, `@Column(name="created_at", updatable=false)`)
- `@PrePersist onCreate()` → `createdAt = LocalDateTime.now()`

---

## 4 Task09：Repository（6个文件）

### 4.1 UserRepository.java
- 继承 `JpaRepository<User, Long>`
- 方法：
  - `Optional<User> findByUserId(String userId)`
  - `Optional<User> findByUsername(String username)`
  - `boolean existsByUsername(String username)`
  - `boolean existsByEmail(String email)`
- 类级别 `@Transactional(readOnly = true)`

### 4.2 UserProfileRepository.java
- 继承 `JpaRepository<UserProfile, Long>`
- 方法：
  - `Optional<UserProfile> findByUserId(String userId)`
  - `boolean existsByUserId(String userId)`
- 类级别 `@Transactional(readOnly = true)`

### 4.3 PaperRepository.java
- 继承 `JpaRepository<Paper, Long>` + `JpaSpecificationExecutor<Paper>`
- 方法：
  - `Optional<Paper> findByPaperId(String paperId)`
  - `List<Paper> findByPaperIdIn(List<String> paperIds)`
  - `Page<Paper> searchByKeyword(...)` — `@Query`原生SQL，MATCH...AGAINST全文检索 + 条件过滤 + 排序 + 分页
- 类级别 `@Transactional(readOnly = true)`

**searchByKeyword原生SQL**：
```sql
SELECT * FROM papers 
WHERE MATCH(title, abstract) AGAINST(:keyword IN NATURAL LANGUAGE MODE) 
AND (:yearFrom IS NULL OR year >= :yearFrom) 
AND (:yearTo IS NULL OR year <= :yearTo) 
AND (:venue IS NULL OR venue = :venue) 
ORDER BY CASE 
  WHEN :sort = 'relevance' THEN MATCH(title, abstract) AGAINST(:keyword IN NATURAL LANGUAGE MODE) 
  WHEN :sort = 'year' THEN year 
  WHEN :sort = 'citations' THEN citation_count 
END DESC
```

### 4.4 SessionRepository.java
- 继承 `JpaRepository<Session, Long>`
- 方法：
  - `Optional<Session> findBySessionId(String sessionId)`
  - `Page<Session> findByUserIdOrderByCreatedAtDesc(String userId, Pageable pageable)` — 数据隔离
- 类级别 `@Transactional(readOnly = true)`

### 4.5 AnalysisResultRepository.java
- 继承 `JpaRepository<AnalysisResult, Long>`
- 方法：
  - `Optional<AnalysisResult> findByAnalysisId(String analysisId)`
  - `List<AnalysisResult> findBySessionId(String sessionId)`
  - `List<AnalysisResult> findBySessionIdAndStatus(String sessionId, AnalysisStatus status)`
- 类级别 `@Transactional(readOnly = true)`

### 4.6 PaperFavoriteRepository.java
- 继承 `JpaRepository<PaperFavorite, Long>`
- 方法：
  - `Page<PaperFavorite> findByUserIdOrderByCreatedAtDesc(String userId, Pageable pageable)` — 数据隔离
  - `boolean existsByUserIdAndPaperId(String userId, String paperId)`
  - `@Transactional void deleteByUserIdAndPaperId(String userId, String paperId)` — 写操作覆盖readOnly
- 类级别 `@Transactional(readOnly = true)`

---

## 5 Task10：Config Classes（3个文件）

### 5.1 RedisConfig.java
- `@Configuration @EnableCaching`
- **cacheManager Bean**：
  - 默认配置：`StringRedisSerializer`序列化Key + `GenericJackson2JsonRedisSerializer`序列化Value + 默认TTL 30分钟
  - 6个缓存空间自定义TTL：
    - `userProfile` → 1小时
    - `userInfo` → 1小时
    - `paperDetail` → 30分钟
    - `paperSearch` → 10分钟
    - `analysisResult` → 30分钟
    - `sessionState` → 2小时
  - 构建：`RedisCacheManager.builder(factory).cacheDefaults(defaultConfig).withInitialCacheConfigurations(cacheConfigurations).build()`
- **redisTemplate Bean**：
  - Key + Value均使用`StringRedisSerializer`
  - 用于手动操作Redis（JWT黑名单、Agent状态Hash等）
- **P1 缓存穿透防护**：空值缓存TTL=60s
- **P1 缓存雪崩防护**：TTL添加±10%随机偏移

### 5.2 WebClientConfig.java
- `@Configuration`
- **webClient Bean**：
  - `@Value("${ai-service.url}") private String aiServiceUrl`
  - 连接池：`ConnectionProvider` maxConnections=50
  - HttpClient配置：
    - `CONNECT_TIMEOUT_MILLIS` = 5000
    - `responseTimeout` = 30s
    - `ReadTimeoutHandler` = 30s
    - `WriteTimeoutHandler` = 30s
  - ExchangeStrategies：`maxInMemorySize` = 16MB（SSE大响应缓冲）
  - 基础URL从`aiServiceUrl`读取
- **注意**：重试逻辑在PythonAIClient中实现，WebClientConfig仅配置连接和超时

### 5.3 SecurityConfig.java
- `@Configuration @EnableWebSecurity`
- **corsConfigurationSource Bean**：
  - `allowedOrigins`从`@Value("${cors.allowed-origins}")`读取，逗号分隔
  - `allowedMethods`：GET, POST, PUT, DELETE, OPTIONS
  - `allowCredentials` = true
  - `allowedHeaders` = *
  - `maxAge` = 3600s
- **securityFilterChain Bean**：
  1. `csrf().disable()` — JWT无状态认证不需要CSRF
  2. `cors(Customizer.withDefaults())` — 使用corsConfigurationSource Bean
  3. `sessionManagement().sessionCreationPolicy(STATELESS)`
  4. 白名单路径放行：`/api/users/register`, `/api/users/login`, `/health`, `/actuator/**`, `/error`
  5. `anyRequest().authenticated()`
  6. 在`UsernamePasswordAuthenticationFilter`之前添加`JwtAuthFilter`（使用`@ConditionalOnBean`确保JwtAuthFilter不存在时不报错）
  7. `formLogin().disable()`
  8. `logout().disable()`

---

## 6 配置文件变更

### 6.1 pom.xml 新增依赖

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-security</artifactId>
</dependency>
```

### 6.2 application.yml 新增CORS配置

```yaml
cors:
  allowed-origins: ${CORS_ALLOWED_ORIGINS:http://localhost:5173}
```

---

## 7 实施步骤（严格顺序）

### Step 1：修改pom.xml
- 添加 `spring-boot-starter-web`
- 添加 `spring-boot-starter-security`

### Step 2：修改application.yml
- 添加 `cors.allowed-origins` 配置项

### Step 3：创建6个枚举类（Task08）
1. `EducationLevel.java`
2. `KnowledgeLevel.java`
3. `PreferredStyle.java`
4. `SessionStatus.java`
5. `AnalysisType.java`
6. `AnalysisStatus.java`

### Step 4：创建6个Entity类（Task08）
1. `User.java`
2. `UserProfile.java`
3. `Paper.java`
4. `Session.java`
5. `AnalysisResult.java`
6. `PaperFavorite.java`

### Step 5：创建6个Repository接口（Task09）
1. `UserRepository.java`
2. `UserProfileRepository.java`
3. `PaperRepository.java`
4. `SessionRepository.java`
5. `AnalysisResultRepository.java`
6. `PaperFavoriteRepository.java`

### Step 6：创建3个Config类（Task10）
1. `RedisConfig.java`
2. `WebClientConfig.java`
3. `SecurityConfig.java`

### Step 7：编译验证
- `cd Veritas/backend && mvn compile`
- 确保所有21个新文件编译通过

### Step 8：单元测试（如需要）
- 枚举fromCode方法测试
- Entity @PrePersist/@PreUpdate测试
- Repository方法签名验证

---

## 8 关键注意事项

### 8.1 安全红线
- ❌ 禁止硬编码JWT Secret或AI服务URL
- ❌ 禁止CORS使用`allowedOrigins("*")`
- ❌ 禁止User.toString()输出passwordHash
- ❌ 禁止使用JDK默认序列化（必须用GenericJackson2JsonRedisSerializer）
- ❌ 禁止启用CSRF（JWT无状态认证）
- ❌ 禁止省略@Column的name属性

### 8.2 跨系统一致性
- Java camelCase ↔ Python/JSON snake_case
- 枚举值Java端UPPER_SNAKE_CASE，Python/JSON端lower_case
- Paper.abstractText → DDL abstract列

### 8.3 数据隔离
- SessionRepository.findByUserIdOrderByCreatedAtDesc — 强制userId过滤
- PaperFavoriteRepository.findByUserIdOrderByCreatedAtDesc — 强制userId过滤

### 8.4 Spring Security与WebFlux共存
- 添加`spring-boot-starter-web`使应用以Servlet模式运行（Tomcat）
- WebClient仍可正常使用（WebFlux的HTTP客户端在Servlet模式下工作正常）
- SecurityConfig使用Servlet栈的`HttpSecurity`（非响应式的`ServerHttpSecurity`）
- JwtAuthFilter继承`OncePerRequestFilter`（Servlet过滤器）

---

## 9 验收标准

| ID | 验收项 | 验证方式 |
|----|--------|---------|
| AC-001 | 6个Entity类编译通过，@Column与DDL完全一致 | mvn compile |
| AC-002 | 6个枚举类编译通过，枚举值完整正确 | mvn compile |
| AC-003 | Entity使用@Data @NoArgsConstructor @AllArgsConstructor @Builder | 代码审查 |
| AC-004 | 枚举字段@Enumerated(STRING)，JSON字段columnDefinition="JSON" | 代码审查 |
| AC-005 | Paper.abstractText映射到abstract列 | 代码审查 |
| AC-006 | EducationLevel/KnowledgeLevel/PreferredStyle的fromCode方法正确 | 单元测试 |
| AC-007 | 6个Repository编译通过，自定义查询方法签名正确 | mvn compile |
| AC-008 | PaperRepository.searchByKeyword支持全文检索+条件过滤+排序+分页 | 代码审查 |
| AC-009 | Session/PaperFavorite Repository强制userId过滤 | 代码审查 |
| AC-010 | RedisConfig 6个缓存空间TTL分层正确 | 代码审查 |
| AC-011 | WebClientConfig连接超时5s、响应超时30s | 代码审查 |
| AC-012 | SecurityConfig白名单路径无需Token | 代码审查 |
| AC-013 | CSRF禁用、Session STATELESS、formLogin禁用 | 代码审查 |
| AC-014 | CORS从yml读取，禁止硬编码Origin | 代码审查 |
| AC-015 | mvn compile 全部通过 | 自动验证 |
