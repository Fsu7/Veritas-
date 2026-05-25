# 技术教学文档：工具类 JwtUtil + RedisKeyUtil + DateTimeUtil

## 开发思路

### 需求分析过程
1. 解析prompt.json中的任务需求，明确3个工具类的职责边界和接口签名
2. 对照开发规范文档和系统架构文档，确认JWT鉴权流程、Redis Key命名规范、安全约束
3. 发现Key格式差异：prompt.json定义黑名单Key为`auth:blacklist:{tokenHash}`，开发规范文档定义为`auth:token:blacklist:{tokenHash}`，决策遵循prompt.json（任务需求优先）

### 技术选型考虑
- **JWT库**：项目pom.xml已配置jjwt 0.12.5，使用其新API（`Jwts.parser().verifyWith()`替代旧版`parserBuilder()`）
- **工具类模式**：RedisKeyUtil/DateTimeUtil使用`final类+private构造`，JwtUtil使用`@Component`（需要Spring依赖注入）
- **测试策略**：纯逻辑工具类用JUnit5，依赖Spring的JwtUtil用反射注入+匿名子类替身

### 架构设计思路
- JwtUtil作为@Component，通过构造器注入RedisTemplate，通过@Value注入jwt.secret和jwt.expiration
- RedisKeyUtil和DateTimeUtil作为纯静态工具类，无状态、无依赖，线程安全
- parseToken设计为返回null而非抛异常，因为Token无效是常见业务场景（未登录/过期），不是系统错误

### 遇到的问题及解决方案
1. **Java 23运行时Mockito无法mock RedisTemplate**：由于Java模块系统限制，Mockito的inline mock无法修改RedisTemplate类。解决方案：使用匿名子类`new RedisTemplate() { @Override public Boolean hasKey(Object key) {...} }`替代Mockito mock
2. **泛型类型擦除导致hasKey方法名冲突**：匿名子类`new RedisTemplate<String, String>() {}`中override `hasKey(Object)`与泛型`hasKey(K)`产生erasure冲突。解决方案：使用raw type `new RedisTemplate() {}`配合`@SuppressWarnings`
3. **jjwt 0.12.5 API变更**：`SignatureException`被替换为`SecurityException`，`Jwts.parserBuilder()`被替换为`Jwts.parser()`，`parseClaimsJws()`被替换为`parseSignedClaims()`

## 实现步骤

1. **创建RedisKeyUtil**：final类+private构造，9个静态方法按`{域}:{操作}:{标识符}`格式拼接字符串
2. **创建DateTimeUtil**：final类+private构造，DateTimeFormatter作为static final常量，4个静态方法
3. **创建JwtUtil**：@Component注解，@Value注入配置，构造器注入RedisTemplate，8个方法实现JWT全生命周期管理
4. **创建RedisKeyUtilTest**：9个测试用例验证Key格式
5. **创建DateTimeUtilTest**：6个测试用例验证时间处理逻辑
6. **创建JwtUtilTest**：16个测试用例，使用匿名子类替代Mockito mock
7. **编译验证**：`mvn clean compile`通过
8. **测试验证**：`mvn test` 31个测试全部通过

## 解决了什么问题

### 核心问题描述
- JWT Token的生成/验证/解析/黑名单检查需要统一管理，散落在各处会导致安全漏洞
- Redis Key命名不统一会导致缓存冲突、难以维护、TTL管理混乱
- 日期时间处理不统一会导致格式不一致、时区问题

### 解决方案对比
| 方案 | 优点 | 缺点 |
|------|------|------|
| 工具类模式(final+private构造) | 简单、无状态、线程安全 | 无法注入依赖 |
| @Component模式 | 可注入Spring依赖 | 需要Spring容器 |
| 混合模式 | JwtUtil用@Component，其他用final类 | 需区分场景 |

### 最终方案的优势
- RedisKeyUtil/DateTimeUtil：纯静态方法，零依赖，随处可用
- JwtUtil：@Component可注入RedisTemplate和@Value配置，安全合规
- parseToken返回null而非抛异常，调用方代码更简洁

## 变更内容

### 新增文件
- `Veritas/backend/src/main/java/com/literatureassistant/util/RedisKeyUtil.java` — Redis Key生成工具，9个静态方法
- `Veritas/backend/src/main/java/com/literatureassistant/util/DateTimeUtil.java` — 日期时间工具，4个静态方法
- `Veritas/backend/src/main/java/com/literatureassistant/util/JwtUtil.java` — JWT工具，8个方法
- `Veritas/backend/src/test/java/com/literatureassistant/util/RedisKeyUtilTest.java` — 9个测试用例
- `Veritas/backend/src/test/java/com/literatureassistant/util/DateTimeUtilTest.java` — 6个测试用例
- `Veritas/backend/src/test/java/com/literatureassistant/util/JwtUtilTest.java` — 16个测试用例

### 修改文件
- `Veritas/backend/pom.xml` — 添加maven-surefire-plugin配置，`--add-opens` JVM参数解决Java 17+模块访问限制

### 配置变更
- 无新增配置变更。application.yml中已有`jwt.secret`和`jwt.expiration:86400000`配置

## 关键技术点

### 使用的核心技术
- **jjwt 0.12.5**：JWT Token生成与验证，使用`Jwts.builder()`和`Jwts.parser()`新API
- **HMAC-SHA256**：对称密钥签名算法，密钥通过`Keys.hmacShaKeyFor()`生成，最少32字节
- **RedisTemplate**：Spring Data Redis操作Redis，`hasKey()`检查黑名单
- **ReflectionTestUtils**：Spring Test工具，通过反射注入`@Value`字段值

### 代码实现亮点
- **安全日志**：parseToken异常用`log.debug`而非`log.error`，Token无效是常见业务场景
- **Token脱敏**：`maskToken()`方法最多输出Token前8位+省略号，防止敏感信息泄露
- **密钥强度校验**：generateToken中校验secret长度≥32字节，不足时抛IllegalStateException
- **黑名单TTL**：getTokenRemainingTime返回Token剩余有效期毫秒数，供Redis黑名单设置TTL

### 需要注意的细节
- jjwt 0.12.x API与0.11.x不兼容，`parseClaimsJws`→`parseSignedClaims`，`parserBuilder`→`parser`
- `SignatureException`在0.12.x中变为`SecurityException`
- DateTimeFormatter是线程安全的，可作为static final常量共享
- isTokenBlacklisted中jti为null时返回true（无效Token视为已黑名单），这是防御性设计

## 经验总结

### 开发过程中的收获
- jjwt库版本升级API变化大，需要查阅最新文档而非依赖旧经验
- 工具类设计要区分"需要依赖注入"和"纯逻辑"两种场景，分别用@Component和final类

### 踩过的坑及如何避免
1. **Java 23 Mockito inline mock失败**：高版本JDK的模块系统限制反射访问，导致Mockito无法mock框架类。避免方法：优先使用匿名子类或接口提取，减少对Mockito的依赖
2. **泛型类型擦除**：`new RedisTemplate<String, String>() { @Override public Boolean hasKey(Object key) }`与泛型`hasKey(K)`产生erasure冲突。避免方法：使用raw type配合`@SuppressWarnings`
3. **maven-surefire-plugin JVM参数**：Java 17+需要`--add-opens`参数才能让反射访问JDK内部类。在pom.xml中提前配置好，避免后续测试环境问题

### 最佳实践建议
- JWT工具类中，parseToken应返回null而非抛异常，因为Token无效是业务常态
- 日志中永远不要输出完整Token，使用脱敏方法
- Redis Key命名必须统一管理，避免硬编码字符串散落各处
- 单元测试中优先使用匿名子类/接口提取替代Mockito mock，减少对mock框架的依赖
