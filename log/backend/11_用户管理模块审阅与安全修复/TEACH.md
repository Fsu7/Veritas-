# 技术教学文档

## 开发思路

### 需求分析过程
本次任务源于对F2.1用户管理模块的架构审阅。审阅按照安全、架构一致性、性能、缓存、代码风格5个维度，发现了14个问题。核心问题包括：
1. JWT黑名单Key使用jti明文存储，存在Redis被入侵后Token伪造风险
2. register()缺少@Transactional，违反写操作事务规范
3. 画像操作后userInfo缓存不失效，导致hasProfile字段返回过期值
4. JwtAuthFilter中parseToken被调用4次（validateToken + isTokenBlacklisted + getUserIdFromToken + getUsernameFromToken），每次都做HMAC-SHA256签名验证
5. 缺少MapStruct UserMapper，手动Builder映射已达5字段阈值
6. logout接口无Token归属验证，恶意用户可将他人Token加入黑名单

### 技术选型考虑
- **SHA256哈希**: 使用JDK内置`MessageDigest`，不引入Apache Commons Codec等新依赖，符合stack.md依赖白名单
- **MapStruct**: 项目pom.xml已配置mapstruct 1.5.5.Final + lombok-mapstruct-binding 0.2.0，直接使用
- **Claims一次解析**: JwtAuthFilter中调用`parseToken(token)`返回`Claims`对象，从中直接读取字段，避免重复签名验证

### 架构设计思路
采用"最小变更"原则，不改变API契约和业务逻辑，仅修复安全和架构问题：
- 黑名单Key从明文改为哈希：对调用方透明，Redis Key格式不变
- parseToken优化：在Filter层一次解析，Service层方法保持不变
- UserMapper替换手动Builder：对Controller和Service接口无影响

### 遇到的问题及解决方案
1. **UserMapperTest使用@SpringBootTest失败**: @SpringBootTest需要完整Spring上下文（MySQL/Redis），改为使用MapStruct生成的`UserMapperImpl`直接实例化测试
2. **ProfileUpdateRequest字段类型**: 测试中误用String构造枚举字段，实际DTO使用`EducationLevel`等枚举类型
3. **JwtUtil @PostConstruct方法名**: 测试中误用`init()`，实际方法名为`validateSecret()`

## 实现步骤

1. **B-001 JWT黑名单SHA256**: 在JwtUtil中新增`sha256()`私有方法，修改`isTokenBlacklisted()`和`blacklistToken()`使用哈希后的jti作为Redis Key；新增`isJtiBlacklisted(jti)`方法接收已解析的jti
2. **B-002 @Transactional**: 在UserService.register()上添加@Transactional注解
3. **S-001 缓存失效**: createProfile和updateProfile的@CacheEvict增加`userInfo`缓存区
4. **S-002 parseToken优化**: JwtAuthFilter重构为一次parseToken返回Claims，从中直接读取subject/username/jti
5. **S-003 UserMapper**: 创建MapStruct接口，使用expression处理枚举getDbValue()转换；UserService注入UserMapper替换手动Builder
6. **S-004 logout归属验证**: UserController.logout()中比较Token userId与当前认证用户userId，不一致抛BusinessException(403)
7. **U-002 @RequiredArgsConstructor**: UserService移除手动构造器，改用Lombok注解
8. **U-004 HTTP 201**: register接口返回`ResponseEntity.status(HttpStatus.CREATED)`
9. **U-005 unique约束**: UserProfile.java和01_create_tables.sql中user_id添加UNIQUE
10. **N-001 extractBearerToken**: JwtUtil新增统一Token提取方法，UserController使用该方法
11. **N-002 @Slf4j**: JwtUtil移除手动Logger声明，改用@Slf4j注解
12. **U-001 @JsonProperty**: ProfileResponse字段添加@JsonProperty snake_case
13. **更新测试**: 6个测试文件适配新代码，新增UserMapperTest

## 解决了什么问题

### 核心问题描述
用户管理模块功能完整但存在安全和架构隐患：JWT黑名单Key明文存储、缓存不一致、性能浪费、缺少MapStruct、logout越权

### 解决方案对比
| 问题 | 方案A | 方案B | 最终选择 |
|------|-------|-------|---------|
| 黑名单Key | SHA256哈希 | UUID二次加密 | SHA256（标准做法，无额外依赖） |
| parseToken重复 | 一次解析Claims | 缓存Claims到ThreadLocal | 一次解析（更简洁，无线程安全风险） |
| Entity→DTO | MapStruct | 手动Builder | MapStruct（项目规范要求） |
| logout越权 | Token归属验证 | 禁止logout他人Token | Token归属验证（更友好） |

### 最终方案的优势
- 安全性：黑名单Key不可逆，logout不可越权
- 性能：JWT签名验证从4次降为1次
- 一致性：MapStruct编译时检查，缓存联动失效
- 规范性：@Transactional、@RequiredArgsConstructor、HTTP 201

## 变更内容

### 新增文件
- `src/main/java/com/literatureassistant/mapper/UserMapper.java` — MapStruct Entity↔DTO映射接口
- `src/test/java/com/literatureassistant/mapper/UserMapperTest.java` — MapStruct映射测试

### 修改文件
- `src/main/java/com/literatureassistant/util/JwtUtil.java` — SHA256哈希、isJtiBlacklisted、extractBearerToken、@Slf4j
- `src/main/java/com/literatureassistant/service/UserService.java` — @Transactional、@RequiredArgsConstructor、UserMapper、userInfo缓存失效
- `src/main/java/com/literatureassistant/controller/UserController.java` — logout归属验证、HTTP 201、JwtUtil注入
- `src/main/java/com/literatureassistant/filter/JwtAuthFilter.java` — Claims一次解析
- `src/main/java/com/literatureassistant/entity/UserProfile.java` — userId unique约束
- `src/main/java/com/literatureassistant/dto/response/ProfileResponse.java` — @JsonProperty
- `src/main/resources/db/01_create_tables.sql` — user_id UNIQUE
- `src/test/java/com/literatureassistant/util/JwtUtilTest.java` — 适配SHA256+extractBearerToken
- `src/test/java/com/literatureassistant/service/UserServiceTest.java` — 适配UserMapper+logout
- `src/test/java/com/literatureassistant/service/UserServiceProfileTest.java` — 适配UserMapper
- `src/test/java/com/literatureassistant/filter/JwtAuthFilterTest.java` — 适配Claims解析
- `src/test/java/com/literatureassistant/controller/UserControllerTest.java` — HTTP 201+logout越权

### 配置变更
- 无application.yml变更
- 数据库DDL变更：`user_profiles.user_id` 添加 UNIQUE 约束

## 关键技术点

### SHA-256哈希保护JWT黑名单Key
```java
private String sha256(String input) {
    MessageDigest digest = MessageDigest.getInstance("SHA-256");
    byte[] hash = digest.digest(input.getBytes(StandardCharsets.UTF_8));
    // 转hex string
    return hexString.toString();
}
```
使用JDK内置MessageDigest，不引入新依赖。哈希后Redis Key格式：`auth:blacklist:{sha256hex}`

### MapStruct枚举getDbValue()映射
```java
@Mapping(target = "educationLevel",
    expression = "java(profile.getEducationLevel().getDbValue())")
```
MapStruct无法自动调用枚举的getDbValue()方法，需使用expression显式调用。

### @CacheEvict多缓存区联动
```java
@CacheEvict(value = {"userProfile", "userProfileJson", "userInfo"}, key = "#userId")
```
画像操作影响3个缓存区，必须全部失效，否则userInfo中的hasProfile字段会返回过期值。

### JwtAuthFilter Claims一次解析
```java
Claims claims = jwtUtil.parseToken(token);
if (claims != null && !jwtUtil.isJtiBlacklisted(claims.getId())) {
    String userId = claims.getSubject();
    String username = claims.get("username", String.class);
}
```
从4次parseToken降为1次，HMAC-SHA256签名验证开销减少75%。

## 经验总结

### 开发过程中的收获
1. **审阅先行**: 先做全面审阅再修复，比边写边改效率高很多
2. **优先级驱动**: Block > Strong > Suggestion > Nit，确保关键问题优先修复
3. **测试同步更新**: 代码修改后立即更新测试，避免测试与代码脱节

### 踩过的坑及如何避免
1. **MapStruct测试不要用@SpringBootTest**: @SpringBootTest需要完整Spring上下文（数据库/Redis），对于纯映射测试应直接使用生成的Impl类
2. **ProfileUpdateRequest字段类型是枚举不是String**: 测试中构造请求对象时要注意DTO的实际字段类型
3. **@PostConstruct方法名**: 测试中调用@PostConstruct方法时，要确认实际方法名而非臆测

### 最佳实践建议
1. **黑名单Key永远不要明文存储**: 任何敏感标识符作为Redis Key时都应哈希处理
2. **写操作必须@Transactional**: 即使当前只有一次save，也要标注事务注解
3. **缓存联动失效**: 修改数据时，所有关联缓存区都要@CacheEvict
4. **JWT一次解析**: 在Filter层一次parseToken，后续从Claims读取字段
5. **MapStruct替代手动Builder**: 超过5个字段的映射必须使用MapStruct
