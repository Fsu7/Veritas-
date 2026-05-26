# 用户管理模块审阅与安全修复

## 功能描述
- 解决了用户管理模块（F2.1）在代码审阅中发现的14个问题，包括2个严重安全漏洞、4个重要架构问题、5个建议优化和3个代码风格问题
- 修复了JWT黑名单Key明文存储的安全漏洞，改用SHA256哈希
- 修复了logout接口越权漏洞，增加了Token归属验证
- 修复了缓存一致性问题，画像操作后userInfo缓存正确失效
- 优化了JwtAuthFilter中parseToken重复调用4次的性能问题
- 补齐了MapStruct UserMapper，替代手动Builder映射
- 业务价值：用户管理模块安全性和架构一致性大幅提升，达到JM2验收标准

## 实现逻辑
- 修改的核心文件列表：
  - `util/JwtUtil.java` — SHA256哈希黑名单Key + isJtiBlacklisted + extractBearerToken + @Slf4j
  - `service/UserService.java` — @Transactional + @RequiredArgsConstructor + UserMapper + userInfo缓存失效
  - `controller/UserController.java` — logout归属验证 + HTTP 201 + extractBearerToken
  - `filter/JwtAuthFilter.java` — parseToken优化为一次解析Claims
  - `entity/UserProfile.java` — userId unique约束
  - `dto/response/ProfileResponse.java` — @JsonProperty snake_case
  - `mapper/UserMapper.java` — 新增MapStruct映射器
  - `resources/db/01_create_tables.sql` — user_id UNIQUE约束
- 使用的算法或设计模式：
  - SHA-256哈希算法（JDK MessageDigest）保护黑名单Key
  - MapStruct编译时代码生成，替代运行时反射映射
  - Cache-Aside写后删策略，@CacheEvict多缓存区联动失效
  - Claims一次解析复用，避免重复JWT签名验证
- 关键代码逻辑说明：
  - JWT黑名单：jti → SHA256(jti) → `auth:blacklist:{sha256hex}` 作为Redis Key
  - JwtAuthFilter：`parseToken(token)` 返回 `Claims`，从中直接读取 subject/username/jti，一次解析
  - logout归属验证：比较Token中的userId与SecurityContext中的当前认证用户userId

## 接口变更

### POST /api/users/register
Request:
```json
{
  "username": "testuser",
  "email": "test@example.com",
  "password": "password123"
}
```
Response (HTTP 201):
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "user_id": "usr_test1234",
    "username": "testuser",
    "email": "test@example.com",
    "has_profile": false
  },
  "timestamp": "2026-05-26 10:00:00"
}
```
**变更**: HTTP状态码从200改为201

### POST /api/users/logout
Request:
```
Authorization: Bearer <jwt-token>
```
Response:
```json
{
  "code": 200,
  "message": "success",
  "data": null,
  "timestamp": "2026-05-26 10:00:00"
}
```
**变更**: 新增Token归属验证，禁止操作他人Token

## 测试结果
- 测试场景1：JWT黑名单Key使用SHA256哈希而非明文jti — 通过
- 测试场景2：register()在@Transactional事务中执行 — 通过
- 测试场景3：画像创建/更新后userInfo缓存正确失效 — 通过
- 测试场景4：JwtAuthFilter一次parseToken解析Claims — 通过
- 测试场景5：UserMapper (MapStruct) 正确映射Entity到DTO — 通过
- 测试场景6：logout越权操作他人Token返回403 — 通过
- 测试场景7：register接口返回HTTP 201 — 通过
- 测试场景8：extractBearerToken统一Token提取 — 通过
- 是否通过：是（145个测试全部通过，0失败，0错误）

## 相关文件
- `src/main/java/com/literatureassistant/util/JwtUtil.java`
- `src/main/java/com/literatureassistant/service/UserService.java`
- `src/main/java/com/literatureassistant/controller/UserController.java`
- `src/main/java/com/literatureassistant/filter/JwtAuthFilter.java`
- `src/main/java/com/literatureassistant/entity/UserProfile.java`
- `src/main/java/com/literatureassistant/dto/response/ProfileResponse.java`
- `src/main/java/com/literatureassistant/mapper/UserMapper.java` (新增)
- `src/main/resources/db/01_create_tables.sql`
- `src/test/java/com/literatureassistant/util/JwtUtilTest.java`
- `src/test/java/com/literatureassistant/service/UserServiceTest.java`
- `src/test/java/com/literatureassistant/service/UserServiceProfileTest.java`
- `src/test/java/com/literatureassistant/filter/JwtAuthFilterTest.java`
- `src/test/java/com/literatureassistant/controller/UserControllerTest.java`
- `src/test/java/com/literatureassistant/mapper/UserMapperTest.java` (新增)
