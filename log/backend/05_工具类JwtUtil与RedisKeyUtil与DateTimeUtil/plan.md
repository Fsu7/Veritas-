# Task06 实施计划：工具类（JwtUtil + RedisKeyUtil + DateTimeUtil）

## 任务概述

创建3个工具类：JwtUtil、RedisKeyUtil、DateTimeUtil，以及对应的单元测试。所有工具类遵循 `final类 + private构造方法` 模式，禁止实例化。

---

## 前置分析

### 项目现状
- **pom.xml** 已配置：jjwt 0.12.5、spring-boot-starter-data-redis、spring-boot-starter-data-jpa、lombok
- **application.yml** 已配置：`jwt.secret` 和 `jwt.expiration: 86400000`
- **util/ 包** 已存在（含 .gitkeep），需要创建3个Java文件
- **测试目录** 仅含 `LiteratureAssistantApplicationTests.java`，需创建3个测试类

### 关键规范约束
1. **安全**：JWT Secret 通过 `@Value('${jwt.secret}')` 注入，不硬编码
2. **日志**：parseToken 捕获异常时使用 `log.debug`（非 log.error），Token无效是常见业务场景
3. **敏感信息**：禁止在日志中输出完整Token，最多输出前8位+省略号
4. **密钥强度**：HMAC-SHA256 最小密钥长度 32字节，不足时抛 IllegalStateException
5. **工具类**：RedisKeyUtil 和 DateTimeUtil 为 final类 + private构造方法
6. **线程安全**：DateTimeFormatter 作为 `private static final` 常量

### Key格式差异说明
- prompt.json 定义黑名单Key为 `auth:blacklist:{tokenHash}`
- 开发规范文档定义黑名单Key为 `auth:token:blacklist:{tokenHash}`
- **决策**：遵循 prompt.json 的 `auth:blacklist:{tokenHash}` 格式（任务需求优先）

---

## 实施步骤

### Step 1：创建 RedisKeyUtil.java

**文件路径**：`Veritas/backend/src/main/java/com/literatureassistant/util/RedisKeyUtil.java`

**设计要点**：
- `public final class` + `private RedisKeyUtil() {}`
- 9个静态方法，按 `{域}:{操作}:{标识符}` 格式生成Key
- 方法列表：
  - `userProfileKey(String userId)` → `"user:profile:" + userId`
  - `userInfoKey(String userId)` → `"user:info:" + userId`
  - `paperDetailKey(String paperId)` → `"paper:detail:" + paperId`
  - `paperListKey(String queryHash)` → `"paper:list:" + queryHash`
  - `searchResultKey(String queryHash)` → `"search:result:" + queryHash`
  - `analysisResultKey(String analysisId)` → `"analysis:result:" + analysisId`
  - `sessionStateKey(String sessionId)` → `"session:state:" + sessionId`
  - `agentStateKey(String analysisId)` → `"agent:state:" + analysisId`
  - `authBlacklistKey(String tokenHash)` → `"auth:blacklist:" + tokenHash`

### Step 2：创建 DateTimeUtil.java

**文件路径**：`Veritas/backend/src/main/java/com/literatureassistant/util/DateTimeUtil.java`

**设计要点**：
- `public final class` + `private DateTimeUtil() {}`
- `private static final DateTimeFormatter FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")`
- 4个静态方法：
  - `formatDateTime(LocalDateTime dateTime)` → 使用 FORMATTER 格式化
  - `parseDateTime(String dateTimeStr)` → 使用 FORMATTER 解析
  - `getCurrentTimestamp()` → `System.currentTimeMillis()`
  - `isExpired(LocalDateTime dateTime)` → `dateTime.isBefore(LocalDateTime.now())`

### Step 3：创建 JwtUtil.java

**文件路径**：`Veritas/backend/src/main/java/com/literatureassistant/util/JwtUtil.java`

**设计要点**：
- `@Component` 注解（非final，因为需要Spring注入依赖）
- 通过 `@Value("${jwt.secret}")` 注入 secret
- 通过 `@Value("${jwt.expiration:86400000}")` 注入 expiration
- 注入 `RedisTemplate<String, String>` 用于黑名单检查
- SLF4J Logger：`private static final Logger log = LoggerFactory.getLogger(JwtUtil.class)`

**方法实现**：

1. **generateToken(String userId, String username)**
   - 校验 secret 长度 ≥ 32字节，否则抛 IllegalStateException
   - 使用 `Jwts.builder()`
   - `.subject(userId)` — sub字段存userId
   - `.claim("username", username)` — 自定义claim
   - `.id(UUID.randomUUID().toString())` — jti唯一ID
   - `.issuedAt(new Date())` — 签发时间
   - `.expiration(new Date(System.currentTimeMillis() + expiration))` — 过期时间
   - `.signWith(Keys.hmacShaKeyFor(secret.getBytes()), SignatureAlgorithm.HS256)` — HMAC-SHA256签名

2. **parseToken(String token)**
   - 使用 `Jwts.parserBuilder().setSigningKey(Keys.hmacShaKeyFor(secret.getBytes())).build().parseClaimsJws(token).getBody()`
   - 捕获异常：ExpiredJwtException、UnsupportedJwtException、MalformedJwtException、SecurityException（jjwt 0.12+用SecurityException替代SignatureException）、IllegalArgumentException
   - 所有异常用 `log.debug` 记录（非log.error）
   - 异常时返回 null

3. **validateToken(String token)**
   - `return parseToken(token) != null`

4. **isTokenBlacklisted(String token)**
   - 从token提取jti
   - 使用 `RedisKeyUtil.authBlacklistKey(jti)` 生成Key
   - 查询Redis：`redisTemplate.hasKey(key)`
   - jti为null时返回true（无效Token视为已黑名单）

5. **getUserIdFromToken(String token)**
   - `Claims claims = parseToken(token); return claims != null ? claims.getSubject() : null`

6. **getUsernameFromToken(String token)**
   - `Claims claims = parseToken(token); return claims != null ? claims.get("username", String.class) : null`

7. **getTokenJti(String token)**
   - `Claims claims = parseToken(token); return claims != null ? claims.getId() : null`

8. **getTokenRemainingTime(String token)**
   - `Claims claims = parseToken(token)`
   - 如果 claims 为 null，返回 0
   - `long expMs = claims.getExpiration().getTime()`
   - `return Math.max(0, expMs - System.currentTimeMillis())`

**安全注意事项**：
- 日志中Token最多输出前8位+省略号：`token.substring(0, Math.min(8, token.length())) + "..."`
- secret长度校验在 `generateToken` 中执行（@PostConstruct也可，但prompt要求在generateToken中）

### Step 4：创建 RedisKeyUtilTest.java

**文件路径**：`Veritas/backend/src/test/java/com/literatureassistant/util/RedisKeyUtilTest.java`

**测试用例**：
- `shouldReturnCorrectUserProfileKey` — `userProfileKey("usr_001")` 返回 `"user:profile:usr_001"`
- `shouldReturnCorrectUserInfoKey` — `userInfoKey("usr_001")` 返回 `"user:info:usr_001"`
- `shouldReturnCorrectPaperDetailKey` — `paperDetailKey("arxiv_001")` 返回 `"paper:detail:arxiv_001"`
- `shouldReturnCorrectPaperListKey` — `paperListKey("a1b2c3")` 返回 `"paper:list:a1b2c3"`
- `shouldReturnCorrectSearchResultKey` — `searchResultKey("a1b2c3")` 返回 `"search:result:a1b2c3"`
- `shouldReturnCorrectAnalysisResultKey` — `analysisResultKey("anl_001")` 返回 `"analysis:result:anl_001"`
- `shouldReturnCorrectSessionStateKey` — `sessionStateKey("ses_001")` 返回 `"session:state:ses_001"`
- `shouldReturnCorrectAgentStateKey` — `agentStateKey("anl_001")` 返回 `"agent:state:anl_001"`
- `shouldReturnCorrectAuthBlacklistKey` — `authBlacklistKey("abc123")` 返回 `"auth:blacklist:abc123"`

### Step 5：创建 DateTimeUtilTest.java

**文件路径**：`Veritas/backend/src/test/java/com/literatureassistant/util/DateTimeUtilTest.java`

**测试用例**：
- `shouldFormatDateTime` — 格式化 LocalDateTime 为 `"yyyy-MM-dd HH:mm:ss"`
- `shouldParseDateTime` — 解析字符串为 LocalDateTime
- `shouldFormatAndParseBeInverse` — formatDateTime/parseDateTime 互为逆运算
- `shouldReturnCurrentTimestamp` — getCurrentTimestamp 返回合理的时间戳
- `shouldReturnTrueForExpiredTime` — isExpired 对过去时间返回 true
- `shouldReturnFalseForFutureTime` — isExpired 对未来时间返回 false

### Step 6：创建 JwtUtilTest.java

**文件路径**：`Veritas/backend/src/test/java/com/literatureassistant/util/JwtUtilTest.java`

**测试策略**：使用 Spring Boot Test + MockRedisTemplate，因为 JwtUtil 是 @Component 需要Spring上下文

**测试用例**：
- `shouldGenerateValidToken` — 生成Token并验证非空
- `shouldParseTokenSuccessfully` — 生成Token后解析，验证Claims含正确userId/username/jti
- `shouldReturnNullForInvalidToken` — 无效Token解析返回null
- `shouldReturnNullForExpiredToken` — 过期Token解析返回null
- `shouldValidateToken` — 有效Token验证通过
- `shouldNotValidateInvalidToken` — 无效Token验证失败
- `shouldExtractUserIdFromToken` — 从Token提取userId
- `shouldExtractUsernameFromToken` — 从Token提取username
- `shouldExtractJtiFromToken` — 从Token提取jti
- `shouldReturnTokenRemainingTime` — Token剩余有效期大于0
- `shouldReturnZeroRemainingTimeForInvalidToken` — 无效Token剩余有效期为0
- `shouldThrowWhenSecretTooShort` — secret不足32字节时抛IllegalStateException
- `shouldDetectBlacklistedToken` — 黑名单中的Token返回true
- `shouldNotDetectNonBlacklistedToken` — 非黑名单Token返回false

### Step 7：编译验证

```bash
cd Veritas/backend && mvn compile
```

### Step 8：运行单元测试

```bash
cd Veritas/backend && mvn test -Dtest=JwtUtilTest,RedisKeyUtilTest,DateTimeUtilTest
```

---

## 文件清单

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 创建 | `Veritas/backend/src/main/java/com/literatureassistant/util/RedisKeyUtil.java` | Redis Key生成工具 |
| 创建 | `Veritas/backend/src/main/java/com/literatureassistant/util/DateTimeUtil.java` | 日期时间工具 |
| 创建 | `Veritas/backend/src/main/java/com/literatureassistant/util/JwtUtil.java` | JWT工具 |
| 创建 | `Veritas/backend/src/test/java/com/literatureassistant/util/RedisKeyUtilTest.java` | RedisKeyUtil测试 |
| 创建 | `Veritas/backend/src/test/java/com/literatureassistant/util/DateTimeUtilTest.java` | DateTimeUtil测试 |
| 创建 | `Veritas/backend/src/test/java/com/literatureassistant/util/JwtUtilTest.java` | JwtUtil测试 |

---

## 验收标准对照

| AC编号 | 验收标准 | 验证方式 |
|--------|---------|---------|
| AC-001 | JwtUtil.generateToken生成包含userId/username/jti的24h有效期Token | 自动化测试 |
| AC-002 | JwtUtil.parseToken正确解析Token获取Claims，无效Token返回null | 自动化测试 |
| AC-003 | JwtUtil.validateToken验证Token有效性 | 自动化测试 |
| AC-004 | JwtUtil.isTokenBlacklisted检查Redis黑名单 | 自动化测试 |
| AC-005 | JwtUtil.getTokenRemainingTime返回Token剩余有效期毫秒数 | 自动化测试 |
| AC-006 | RedisKeyUtil 9个方法生成符合{域}:{操作}:{标识符}格式的Key | 自动化测试 |
| AC-007 | DateTimeUtil formatDateTime/parseDateTime互为逆运算 | 自动化测试 |
| AC-008 | RedisKeyUtil和DateTimeUtil为final类+private构造方法 | 代码审查 |
| AC-009 | JWT Secret通过@Value注入，不硬编码 | 代码审查 |
| AC-010 | JwtUtil中parseToken捕获异常时日志级别为DEBUG | 代码审查 |
| AC-011 | 单元测试全部通过 | 自动化测试 |
