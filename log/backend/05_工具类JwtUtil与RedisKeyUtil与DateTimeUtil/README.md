# 工具类开发：JwtUtil + RedisKeyUtil + DateTimeUtil

## 功能描述
- 解决了JWT Token生成/验证/解析/黑名单检查的统一管理问题，为后续JwtAuthFilter和UserService提供安全鉴权基础设施
- 实现了Redis Key的统一命名规范，按`{域}:{操作}:{标识符}`格式生成9种Key，避免Key命名混乱
- 提供了日期时间的格式化/解析/过期判断工具方法，统一项目中时间处理逻辑
- 业务价值：为F2.1用户管理模块（JWT鉴权）、F2.6缓存管理模块（Redis Key管理）提供核心工具支撑

## 实现逻辑

### 修改的核心文件列表
| 文件 | 操作 | 说明 |
|------|------|------|
| `util/RedisKeyUtil.java` | 新增 | final类+private构造，9个静态方法生成Redis Key |
| `util/DateTimeUtil.java` | 新增 | final类+private构造，4个静态方法处理日期时间 |
| `util/JwtUtil.java` | 新增 | @Component，8个方法处理JWT Token全生命周期 |
| `util/RedisKeyUtilTest.java` | 新增 | 9个测试用例验证Key格式 |
| `util/DateTimeUtilTest.java` | 新增 | 6个测试用例验证时间处理 |
| `util/JwtUtilTest.java` | 新增 | 16个测试用例验证JWT功能 |
| `pom.xml` | 修改 | 添加maven-surefire-plugin的--add-opens JVM参数 |

### 使用的算法或设计模式
- **工具类模式**：final类+private构造方法，禁止实例化
- **HMAC-SHA256签名**：JWT Token使用对称密钥签名，密钥通过`Keys.hmacShaKeyFor()`生成
- **Cache-Aside模式**：Token黑名单通过Redis TTL自动过期，与Token剩余有效期一致
- **防御性编程**：parseToken捕获所有异常返回null而非抛出，Token无效是常见业务场景

### 关键代码逻辑说明

**JwtUtil.generateToken**：
```
校验secret长度≥32字节 → Jwts.builder()
  .subject(userId) → .claim("username", username) → .id(UUID)
  .issuedAt(now) → .expiration(now+24h) → .signWith(HS256)
```

**JwtUtil.parseToken**：
```
Jwts.parser().verifyWith(key).build().parseSignedClaims(token)
  → 捕获5种异常(ExpiredJwt/UnsupportedJwt/MalformedJwt/Security/IllegalArgument)
  → log.debug记录（非log.error）→ 返回null
```

**JwtUtil.isTokenBlacklisted**：
```
getTokenJti(token) → null则返回true(无效Token视为已黑名单)
  → RedisKeyUtil.authBlacklistKey(jti) → redisTemplate.hasKey(key)
```

**RedisKeyUtil**：9个静态方法，每个方法返回`"前缀:" + 标识符`格式字符串

**DateTimeUtil**：`DateTimeFormatter`作为`private static final`常量，线程安全

## 接口变更

### Request
本任务为工具类开发，不涉及HTTP接口变更。以下是JwtUtil的核心方法签名：

```java
String generateToken(String userId, String username)
Claims parseToken(String token)
boolean validateToken(String token)
boolean isTokenBlacklisted(String token)
String getUserIdFromToken(String token)
String getUsernameFromToken(String token)
String getTokenJti(String token)
long getTokenRemainingTime(String token)
```

### Response
JwtUtil.generateToken生成的JWT Token Payload结构：

```json
{
  "sub": "usr_001",
  "username": "张三",
  "jti": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "iat": 1748160000,
  "exp": 1748246400
}
```

## 测试结果
- **RedisKeyUtilTest**：9个测试用例，验证9个Key生成方法的格式正确性 → 全部通过
- **DateTimeUtilTest**：6个测试用例，验证格式化/解析/逆运算/时间戳/过期判断 → 全部通过
- **JwtUtilTest**：16个测试用例，覆盖Token生成/解析/验证/字段提取/黑名单/密钥校验 → 全部通过
- **是否通过**：是（Tests run: 31, Failures: 0, Errors: 0, Skipped: 0）

## 相关文件
- `Veritas/backend/src/main/java/com/literatureassistant/util/JwtUtil.java`
- `Veritas/backend/src/main/java/com/literatureassistant/util/RedisKeyUtil.java`
- `Veritas/backend/src/main/java/com/literatureassistant/util/DateTimeUtil.java`
- `Veritas/backend/src/test/java/com/literatureassistant/util/JwtUtilTest.java`
- `Veritas/backend/src/test/java/com/literatureassistant/util/RedisKeyUtilTest.java`
- `Veritas/backend/src/test/java/com/literatureassistant/util/DateTimeUtilTest.java`
- `Veritas/backend/pom.xml`（添加maven-surefire-plugin配置）
- `Veritas/backend/src/main/resources/application.yml`（已有jwt.secret和jwt.expiration配置，未修改）
