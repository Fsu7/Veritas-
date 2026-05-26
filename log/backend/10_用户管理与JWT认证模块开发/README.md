# 用户管理与JWT认证模块开发

## 功能描述
- 实现了用户注册/登录/查询/退出4个API端点及对应业务逻辑
- 实现了用户画像CRUD 3个API端点（GET/POST/PUT）
- 增强了JWT认证过滤器（白名单跳过、MDC链路追踪、SecurityContext清理、边界处理）
- 增强了JWT工具类（黑名单写入、过期检查、token_type声明、错误日志区分）
- 业务价值：完成M3里程碑中用户认证核心功能，为前后端联调奠定基础

## 实现逻辑

### 修改的核心文件列表

| 操作 | 文件 | Task |
|------|------|------|
| 创建 | dto/request/RegisterRequest.java | 11 |
| 创建 | dto/request/LoginRequest.java | 11 |
| 创建 | dto/request/ProfileUpdateRequest.java | 14 |
| 创建 | dto/response/UserResponse.java | 11 |
| 创建 | dto/response/LoginResponse.java | 11 |
| 创建 | dto/response/ProfileResponse.java | 14 |
| 创建 | controller/UserController.java | 11+14 |
| 创建 | service/UserService.java | 12+14 |
| 修改 | config/SecurityConfig.java | 12 |
| 修改 | filter/JwtAuthFilter.java | 13 |
| 修改 | util/JwtUtil.java | 13 |

### 使用的算法或设计模式

- **分层架构**: Controller → Service → Repository，Controller仅做请求转发
- **构造器注入**: 所有依赖通过构造器注入，无@Autowired
- **Cache-Aside缓存**: getUserInfo使用@Cacheable，画像CRUD使用@CacheEvict
- **Redis黑名单**: logout时将Token jti写入Redis，TTL=Token剩余有效期
- **数据隔离**: Service层从SecurityContext获取当前用户ID，与路径参数比对
- **防枚举攻击**: 登录失败统一返回"用户名或密码错误"，不区分用户不存在和密码错误

### 关键代码逻辑说明

1. **注册流程**: 唯一性校验(username/email) → BCrypt加密 → UUID生成userId(usr_xxxxxxxx) → 保存User → 检查画像 → 返回UserResponse
2. **登录流程**: findByUsername → BCrypt校验 → 生成JWT → 检查画像 → 返回LoginResponse(含token)
3. **退出流程**: 提取jti → 获取剩余有效期 → 写入Redis黑名单(auth:blacklist:{jti})
4. **画像创建**: 数据隔离校验 → 用户存在校验 → 画像不存在校验 → 保存 → 同步Redis画像JSON
5. **画像更新**: 数据隔离校验 → 查找已有画像 → 合并字段 → 保存 → 双重缓存失效 + Redis同步

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
Response:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "userId": "usr_a1b2c3d4",
    "username": "testuser",
    "email": "test@example.com",
    "createdAt": "2026-05-26T10:00:00",
    "has_profile": false
  },
  "timestamp": 1748236800000
}
```

### POST /api/users/login
Request:
```json
{
  "username": "testuser",
  "password": "password123"
}
```
Response:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiJ9...",
    "user_id": "usr_a1b2c3d4",
    "username": "testuser",
    "has_profile": false
  },
  "timestamp": 1748236800000
}
```

### GET /api/users/{userId}
Response:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "userId": "usr_a1b2c3d4",
    "username": "testuser",
    "email": "test@example.com",
    "createdAt": "2026-05-26T10:00:00",
    "has_profile": false
  },
  "timestamp": 1748236800000
}
```

### POST /api/users/logout
Request Header: `Authorization: Bearer {token}`
Response:
```json
{
  "code": 200,
  "message": "success",
  "data": null,
  "timestamp": 1748236800000
}
```

### GET /api/users/{userId}/profile
Response:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "user_id": "usr_a1b2c3d4",
    "education_level": "master",
    "research_field": "NLP",
    "knowledge_level": "intermediate",
    "preferred_style": "balanced",
    "updated_at": "2026-05-26T10:00:00"
  },
  "timestamp": 1748236800000
}
```

### POST /api/users/{userId}/profile
Request:
```json
{
  "education_level": "master",
  "research_field": "NLP",
  "knowledge_level": "intermediate",
  "preferred_style": "balanced"
}
```
Response: 同GET画像响应

### PUT /api/users/{userId}/profile
Request/Response: 同POST画像

## 测试结果

- UserControllerTest: 6个测试通过（注册正常/校验失败、登录正常/校验失败、查询正常、退出正常）
- UserServiceTest: 11个测试通过（注册3场景、登录3场景、查询2场景、退出3场景）
- JwtAuthFilterTest: 13个测试通过（原有5个+新增白名单2+MDC2+SecurityContext清理1+边界处理2+过期1）
- JwtUtilTest: 24个测试通过（原有16个+新增blacklistToken3+isTokenExpired4+token_type1）
- ProfileUpdateRequestTest: 5个测试通过（@Valid校验各字段）
- UserServiceProfileTest: 9个测试通过（getProfile3+createProfile3+updateProfile3）
- 全量测试: **167 tests, 0 failures** ✅

## 相关文件

### 新增文件
- `Veritas/backend/src/main/java/com/literatureassistant/dto/request/RegisterRequest.java`
- `Veritas/backend/src/main/java/com/literatureassistant/dto/request/LoginRequest.java`
- `Veritas/backend/src/main/java/com/literatureassistant/dto/request/ProfileUpdateRequest.java`
- `Veritas/backend/src/main/java/com/literatureassistant/dto/response/UserResponse.java`
- `Veritas/backend/src/main/java/com/literatureassistant/dto/response/LoginResponse.java`
- `Veritas/backend/src/main/java/com/literatureassistant/dto/response/ProfileResponse.java`
- `Veritas/backend/src/main/java/com/literatureassistant/controller/UserController.java`
- `Veritas/backend/src/main/java/com/literatureassistant/service/UserService.java`
- `Veritas/backend/src/test/java/com/literatureassistant/controller/UserControllerTest.java`
- `Veritas/backend/src/test/java/com/literatureassistant/service/UserServiceTest.java`
- `Veritas/backend/src/test/java/com/literatureassistant/service/UserServiceProfileTest.java`
- `Veritas/backend/src/test/java/com/literatureassistant/dto/request/ProfileUpdateRequestTest.java`

### 修改文件
- `Veritas/backend/src/main/java/com/literatureassistant/config/SecurityConfig.java` — 新增PasswordEncoder @Bean
- `Veritas/backend/src/main/java/com/literatureassistant/filter/JwtAuthFilter.java` — 白名单/MDC/清理/边界处理
- `Veritas/backend/src/main/java/com/literatureassistant/util/JwtUtil.java` — blacklistToken/isTokenExpired/token_type/日志增强
- `Veritas/backend/src/test/java/com/literatureassistant/filter/JwtAuthFilterTest.java` — 扩展8个新测试
- `Veritas/backend/src/test/java/com/literatureassistant/util/JwtUtilTest.java` — 扩展8个新测试

### 配置变更
- SecurityConfig新增PasswordEncoder Bean (BCryptPasswordEncoder, strength=10)
