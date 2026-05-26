# 用户管理模块审阅修复与功能补全

## 功能描述
- 解决了 java-review 审阅发现的 2 个严重问题（P0）、5 个重要问题（P1）、6 个建议优化（P2）、3 个提示（P3）
- 补全了架构文档定义但未实现的 `PUT /api/users/{userId}` 接口
- 加固了安全防线：validateDataIsolation 空认证拒绝、CORS Header 收紧、GlobalExceptionHandler HTTP 状态码对齐
- 业务价值：消除运行时 NPE 风险、修复 JPA Entity equals/hashCode 隐患、提升 API 语义正确性、完善数据隔离安全

## 实现逻辑

### 修改的核心文件列表

| 文件 | 修改内容 |
|------|---------|
| `entity/User.java` | `@Data` → `@Getter @Setter @EqualsAndHashCode(onlyExplicitlyIncluded=true) @ToString(exclude={"passwordHash","email"})` |
| `entity/UserProfile.java` | 同上 + 移除3个冗余 `@Convert` 注解 |
| `controller/UserController.java` | 移除 JwtUtil 依赖；logout 简化为调用 `userService.logoutWithAuth()`；新增 `PUT /{userId}` |
| `service/UserService.java` | 新增 `logoutWithAuth()`/`updateUser()`；`login()` 加 `@Transactional(readOnly=true)`；`getUserInfo()` 改用 `ResourceNotFoundException`；`register()` 移除不必要查询；`validateDataIsolation()` 加固 |
| `config/SecurityConfig.java` | CORS `allowedHeaders` 收紧为3个；改用 `@RequiredArgsConstructor` |
| `filter/JwtAuthFilter.java` | 改用 `@RequiredArgsConstructor` |
| `exception/GlobalExceptionHandler.java` | 所有处理器返回 `ResponseEntity`，HTTP 状态码与业务码对齐 |
| `dto/response/UserResponse.java` | `userId` 添加 `@JsonProperty("user_id")` |
| `dto/request/UserUpdateRequest.java` | **新增** — 用户信息更新 DTO |

### 使用的设计模式
- **分层架构严格化**：Controller 不再直接依赖 JwtUtil，logout 业务逻辑下沉到 Service
- **防御性编程**：validateDataIsolation 中 null 认证直接拒绝而非放行
- **JPA Entity 安全模式**：`@EqualsAndHashCode(onlyExplicitlyIncluded = true)` 仅基于主键

### 关键代码逻辑说明
1. `logoutWithAuth()` 方法封装了 Token 提取 → null 检查 → 权限校验 → 登出的完整流程
2. `updateUser()` 方法实现了部分更新（null 字段不更新）+ 唯一性校验
3. `mapCodeToStatus()` 方法将业务码映射为正确的 HTTP 状态码

## 接口变更

### 新增接口：PUT /api/users/{userId}

#### Request
```json
{
  "username": "newusername",
  "email": "new@example.com"
}
```

#### Response
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "user_id": "usr_test1234",
    "username": "newusername",
    "email": "new@example.com",
    "has_profile": false
  },
  "timestamp": "2026-05-26 13:30:00"
}
```

### 变更接口：POST /api/users/logout

#### Request
```
Authorization: Bearer <token>
```

#### Response（无变化）
```json
{
  "code": 200,
  "message": "success",
  "data": null,
  "timestamp": "2026-05-26 13:30:00"
}
```

### 全局变更：HTTP 状态码对齐

| 异常类型 | 修改前 | 修改后 |
|---------|--------|--------|
| AuthenticationException | 200 + code=401 | **401** + code=401 |
| ResourceNotFoundException | 200 + code=404 | **404** + code=404 |
| AIServiceException | 200 + code=503 | **503** + code=503 |
| BusinessException(409) | 200 + code=409 | **409** + code=409 |
| MethodArgumentNotValidException | 200 + code=400 | **400** + code=400 |
| Exception(兜底) | 200 + code=500 | **500** + code=500 |

### 全局变更：UserResponse JSON 字段

| 字段 | 修改前 | 修改后 |
|------|--------|--------|
| userId | `"userId"` | `"user_id"` |

## 测试结果
- 编译验证：`mvn compile` 通过 ✅
- 全量测试：`mvn test` — 153 个测试全部通过 ✅
- 新增测试场景：
  - `logoutWithAuth_nullToken_throwsBusinessException` ✅
  - `logoutWithAuth_invalidToken_throwsBusinessException` ✅
  - `updateUser_normal_returnsUserResponse` ✅
  - `updateUser_duplicateUsername_throwsBusinessException` ✅
  - `getUserInfo_notFound_throwsResourceNotFoundException` ✅
  - `getProfile_notAuthenticated_throwsAuthenticationException` ✅
  - `getProfile_forbiddenAccess_throwsBusinessException` ✅
  - `logout_invalidToken_returns401` ✅
  - `updateUser_success` ✅
- 是否通过：是

## 相关文件

### 代码文件
- `src/main/java/com/literatureassistant/entity/User.java`
- `src/main/java/com/literatureassistant/entity/UserProfile.java`
- `src/main/java/com/literatureassistant/controller/UserController.java`
- `src/main/java/com/literatureassistant/service/UserService.java`
- `src/main/java/com/literatureassistant/config/SecurityConfig.java`
- `src/main/java/com/literatureassistant/filter/JwtAuthFilter.java`
- `src/main/java/com/literatureassistant/exception/GlobalExceptionHandler.java`
- `src/main/java/com/literatureassistant/dto/response/UserResponse.java`
- `src/main/java/com/literatureassistant/dto/request/UserUpdateRequest.java`（新增）

### 测试文件
- `src/test/java/com/literatureassistant/controller/UserControllerTest.java`
- `src/test/java/com/literatureassistant/service/UserServiceTest.java`
- `src/test/java/com/literatureassistant/service/UserServiceProfileTest.java`
- `src/test/java/com/literatureassistant/exception/GlobalExceptionHandlerTest.java`

### 配置文件变更
- 无 application.yml 变更
