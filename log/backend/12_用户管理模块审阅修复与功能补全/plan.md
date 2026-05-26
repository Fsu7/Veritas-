# 用户管理模块（F2.1）审阅问题修复计划

> 基于 java-review 审阅报告，按优先级修复用户管理模块的所有问题

## 修复总览

| 优先级 | 数量 | 涉及文件数 |
|--------|------|-----------|
| P0 严重 | 2 | 2 |
| P1 重要 | 5 | 6 |
| P2 建议 | 6 | 5 |
| P3 提示 | 3 | 3 |

---

## Step 1: P0 — 修复 JPA Entity @Data 隐患

**问题**: B-001 — `@Data` 自动生成 `equals()/hashCode()` 包含所有字段，对 JPA Entity 有隐患

**修改文件**:
- `entity/User.java` — 替换 `@Data` 为 `@Getter @Setter @EqualsAndHashCode(onlyExplicitlyIncluded = true)`，排除 passwordHash 和 email 的 toString
- `entity/UserProfile.java` — 同样替换，排除敏感字段

**具体变更**:

### User.java
```java
// 修改前
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Entity
@Table(name = "users")
public class User {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    // ...
    @Override
    public String toString() { ... }
}

// 修改后
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Entity
@Table(name = "users")
@EqualsAndHashCode(onlyExplicitlyIncluded = true)
@ToString(exclude = {"passwordHash", "email"})
public class User {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @EqualsAndHashCode.Include
    private Long id;
    // ... 其余字段不变
    // 删除手动 toString()，使用 Lombok @ToString
}
```

### UserProfile.java
```java
// 修改前
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Entity
@Table(name = "user_profiles")
public class UserProfile { ... }

// 修改后
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Entity
@Table(name = "user_profiles")
@EqualsAndHashCode(onlyExplicitlyIncluded = true)
public class UserProfile {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @EqualsAndHashCode.Include
    private Long id;
    // ... 其余字段不变
}
```

---

## Step 2: P0 — 修复 UserController.logout() NPE 风险

**问题**: B-002 — `jwtUtil.getUserIdFromToken(rawToken)` 返回 null 时，`tokenUserId.equals()` 抛 NPE

**修改文件**: `controller/UserController.java`

**具体变更**: 在 `tokenUserId.equals(currentUserId)` 前增加 null 检查

```java
// 修改前
String tokenUserId = jwtUtil.getUserIdFromToken(rawToken);
String currentUserId = SecurityContextHolder.getContext().getAuthentication().getPrincipal().toString();
if (!tokenUserId.equals(currentUserId)) {

// 修改后
String tokenUserId = jwtUtil.getUserIdFromToken(rawToken);
if (tokenUserId == null) {
    throw new BusinessException(401, "无效或已过期的Token", "INVALID_TOKEN");
}
String currentUserId = SecurityContextHolder.getContext().getAuthentication().getPrincipal().toString();
if (!tokenUserId.equals(currentUserId)) {
```

---

## Step 3: P1 — 将 logout 业务逻辑下沉到 UserService

**问题**: S-002 — Controller 直接注入 JwtUtil 违反分层原则

**修改文件**:
- `controller/UserController.java` — 移除 JwtUtil 依赖，logout 方法简化
- `service/UserService.java` — 新增 `logoutWithAuth(String authHeader)` 方法

**具体变更**:

### UserController.java
```java
// 修改前
private final UserService userService;
private final JwtUtil jwtUtil;

@PostMapping("/logout")
public ApiResponse<Void> logout(@RequestHeader("Authorization") String authHeader) {
    String rawToken = jwtUtil.extractBearerToken(authHeader);
    // ... 大量业务逻辑
    userService.logout(rawToken);
    return ApiResponse.success(null);
}

// 修改后
private final UserService userService;

@PostMapping("/logout")
public ApiResponse<Void> logout(@RequestHeader("Authorization") String authHeader) {
    userService.logoutWithAuth(authHeader);
    return ApiResponse.success(null);
}
```

### UserService.java — 新增方法
```java
public void logoutWithAuth(String authHeader) {
    String rawToken = jwtUtil.extractBearerToken(authHeader);
    if (rawToken == null) {
        throw new BusinessException(401, "无效的Authorization头", "INVALID_AUTH_HEADER");
    }
    String tokenUserId = jwtUtil.getUserIdFromToken(rawToken);
    if (tokenUserId == null) {
        throw new BusinessException(401, "无效或已过期的Token", "INVALID_TOKEN");
    }
    validateDataIsolation(tokenUserId);
    logout(rawToken);
}
```

---

## Step 4: P1 — 统一 getUserInfo() 异常类型

**问题**: S-003 — `getUserInfo()` 使用 `BusinessException(404)` 而非 `ResourceNotFoundException`

**修改文件**: `service/UserService.java`

```java
// 修改前
User user = userRepository.findByUserId(userId)
    .orElseThrow(() -> new BusinessException(404, "用户不存在", "USER_NOT_FOUND"));

// 修改后
User user = userRepository.findByUserId(userId)
    .orElseThrow(() -> new ResourceNotFoundException("User", userId));
```

---

## Step 5: P1 — 收紧 CORS allowedHeaders

**问题**: S-004 — `allowedHeaders = List.of("*")` 过于宽松

**修改文件**: `config/SecurityConfig.java`

```java
// 修改前
configuration.setAllowedHeaders(List.of("*"));

// 修改后
configuration.setAllowedHeaders(Arrays.asList("Authorization", "Content-Type", "X-Request-Id"));
```

---

## Step 6: P1 — login() 添加 @Transactional(readOnly = true)

**问题**: S-005 — 纯读操作缺少只读事务优化

**修改文件**: `service/UserService.java`

```java
// 修改前
public LoginResponse login(LoginRequest request) {

// 修改后
@Transactional(readOnly = true)
public LoginResponse login(LoginRequest request) {
```

---

## Step 7: P1 — 补充 PUT /api/users/{userId} 接口

**问题**: S-001 — 架构文档 F2.1.4 定义了此接口但未实现

**新增/修改文件**:
- `dto/request/UserUpdateRequest.java` — 新增 DTO
- `mapper/UserMapper.java` — 新增映射方法
- `service/UserService.java` — 新增 `updateUser()` 方法
- `controller/UserController.java` — 新增端点

### UserUpdateRequest.java
```java
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class UserUpdateRequest {
    @Size(min = 3, max = 50, message = "用户名长度3-50")
    private String username;

    @Email(message = "邮箱格式不正确")
    private String email;
}
```

### UserMapper.java — 新增
```java
@Mapping(target = "id", ignore = true)
@Mapping(target = "userId", ignore = true)
@Mapping(target = "passwordHash", ignore = true)
@Mapping(target = "createdAt", ignore = true)
@Mapping(target = "hasProfile", ignore = true)
@BeanMapping(nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
void updateUserFromRequest(UserUpdateRequest request, @MappingTarget User user);
```

### UserService.java — 新增
```java
@Transactional
@CacheEvict(value = "userInfo", key = "#userId")
public UserResponse updateUser(String userId, UserUpdateRequest request) {
    User user = userRepository.findByUserId(userId)
            .orElseThrow(() -> new ResourceNotFoundException("User", userId));
    userMapper.updateUserFromRequest(request, user);
    userRepository.save(user);
    boolean hasProfile = userProfileRepository.existsByUserId(userId);
    log.info("User updated: userId={}", userId);
    return userMapper.toUserResponse(user, hasProfile);
}
```

### UserController.java — 新增
```java
@PutMapping("/{userId}")
public ApiResponse<UserResponse> updateUser(@PathVariable String userId,
                                             @Valid @RequestBody UserUpdateRequest request) {
    UserResponse response = userService.updateUser(userId, request);
    return ApiResponse.success(response);
}
```

---

## Step 8: P2 — 统一 UserResponse JSON 字段命名

**问题**: U-001 — `userId` 缺少 `@JsonProperty("user_id")`，与 ProfileResponse 不一致

**修改文件**: `dto/response/UserResponse.java`

```java
// 修改前
private String userId;

// 修改后
@JsonProperty("user_id")
private String userId;
```

---

## Step 9: P2 — 移除 register() 中不必要的 existsByUserId 查询

**问题**: U-003 — 新注册用户必然无画像，无需查询

**修改文件**: `service/UserService.java`

```java
// 修改前
userRepository.save(user);
boolean hasProfile = userProfileRepository.existsByUserId(userId);
return userMapper.toUserResponse(user, hasProfile);

// 修改后
userRepository.save(user);
return userMapper.toUserResponse(user, false);
```

---

## Step 10: P2 — 加固 validateDataIsolation()

**问题**: U-004 — `currentUserId == null` 时放行，应拒绝访问

**修改文件**: `service/UserService.java`

```java
// 修改前
private void validateDataIsolation(String userId) {
    String currentUserId = getCurrentUserId();
    if (currentUserId != null && !currentUserId.equals(userId)) {
        throw new BusinessException(403, "无权限访问他人画像", "FORBIDDEN_ACCESS");
    }
}

// 修改后
private void validateDataIsolation(String userId) {
    String currentUserId = getCurrentUserId();
    if (currentUserId == null) {
        throw new AuthenticationException("未认证，请先登录");
    }
    if (!currentUserId.equals(userId)) {
        throw new BusinessException(403, "无权限访问他人画像", "FORBIDDEN_ACCESS");
    }
}
```

---

## Step 11: P2 — 统一 Controller 返回风格

**问题**: U-005 — register 返回 ResponseEntity，其他返回 ApiResponse

**修改文件**: `controller/UserController.java`

统一所有方法返回 `ApiResponse<T>`（保持当前多数方法的风格），register 特殊处理 HTTP 201：

```java
// 保持 register 返回 ResponseEntity（HTTP 201 语义正确）
// 其他方法保持 ApiResponse（HTTP 200 + 业务码）
// 这是合理的混合模式，无需强制统一
```

**决策**: 保持现状。register 用 ResponseEntity 返回 201 是 RESTful 最佳实践，其他用 ApiResponse 返回 200 也是合理的。不强求统一。

---

## Step 12: P2 — GlobalExceptionHandler HTTP 状态码对齐

**问题**: U-006 — 所有异常返回 HTTP 200 + 业务码，RESTful 不规范

**修改文件**: `exception/GlobalExceptionHandler.java`

```java
// 修改前
@ExceptionHandler(AuthenticationException.class)
public ApiResponse<Void> handleAuth(AuthenticationException e) {
    return ApiResponse.error(e.getCode(), e.getMessage());
}

// 修改后
@ExceptionHandler(AuthenticationException.class)
public ResponseEntity<ApiResponse<Void>> handleAuth(AuthenticationException e) {
    return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
            .body(ApiResponse.error(e.getCode(), e.getMessage()));
}

// 同理修改其他异常处理器：
// ResourceNotFoundException → 404
// AIServiceException → 503
// BusinessException → 根据 code 动态设置
// MethodArgumentNotValidException → 400
// Exception (兜底) → 500
```

---

## Step 13: P3 — 移除 UserProfile 冗余 @Convert 注解

**问题**: U-002 — Converter autoApply=true，@Convert 注解冗余

**修改文件**: `entity/UserProfile.java`

```java
// 修改前
@Convert(converter = EducationLevelConverter.class)
@Column(name = "education_level", length = 20)
private EducationLevel educationLevel;

// 修改后
@Column(name = "education_level", length = 20)
private EducationLevel educationLevel;

// 同理移除 KnowledgeLevel 和 PreferredStyle 的 @Convert
```

---

## Step 14: P3 — JwtAuthFilter / SecurityConfig 使用 @RequiredArgsConstructor

**问题**: N-001/N-002 — 手动构造器可简化

**修改文件**:
- `filter/JwtAuthFilter.java` — 改用 `@RequiredArgsConstructor`
- `config/SecurityConfig.java` — 改用 `@RequiredArgsConstructor`

JwtAuthFilter 中 `AntPathMatcher` 为非 final 字段（不需要注入），需保留为字段初始化。

---

## Step 15: 更新测试代码

**修改文件**:
- `test/controller/UserControllerTest.java` — 移除 JwtUtil Mock，更新 logout 测试，新增 updateUser 测试
- `test/service/UserServiceTest.java` — 新增 logoutWithAuth 测试、updateUser 测试
- `test/service/UserServiceProfileTest.java` — 更新 validateDataIsolation 测试

### UserControllerTest.java 变更
1. 移除 `@Mock JwtUtil jwtUtil`
2. 更新 `logout_success` — 直接 Mock `userService.logoutWithAuth()`
3. 更新 `logout_forbiddenTokenOperation` — Mock `userService.logoutWithAuth()` 抛异常
4. 新增 `updateUser_success` 测试

### UserServiceTest.java 变更
1. 新增 `logoutWithAuth_nullToken_throwsBusinessException` 测试
2. 新增 `logoutWithAuth_invalidToken_throwsBusinessException` 测试
3. 新增 `logoutWithAuth_forbiddenAccess_throwsBusinessException` 测试
4. 新增 `updateUser_normal_returnsUserResponse` 测试
5. 新增 `updateUser_duplicateUsername_throwsBusinessException` 测试

---

## Step 16: 编译验证

运行 `mvn compile` 和 `mvn test` 确认所有修改无编译错误、测试通过。

---

## 执行顺序

```
Step 1  (P0) Entity @Data 修复
Step 2  (P0) logout NPE 修复
  ↓
Step 3  (P1) logout 逻辑下沉 Service
Step 4  (P1) getUserInfo 异常类型统一
Step 5  (P1) CORS allowedHeaders 收紧
Step 6  (P1) login @Transactional(readOnly=true)
Step 7  (P1) 补充 PUT /api/users/{userId} 接口
  ↓
Step 8  (P2) UserResponse @JsonProperty 统一
Step 9  (P2) register 移除不必要查询
Step 10 (P2) validateDataIsolation 加固
Step 11 (P2) Controller 返回风格 — 保持现状
Step 12 (P2) GlobalExceptionHandler HTTP 状态码
  ↓
Step 13 (P3) UserProfile 移除冗余 @Convert
Step 14 (P3) @RequiredArgsConstructor 简化
  ↓
Step 15 更新测试代码
Step 16 编译验证
```

## 变更文件清单

| 文件 | 操作 | Step |
|------|------|------|
| `entity/User.java` | 修改 | 1 |
| `entity/UserProfile.java` | 修改 | 1, 13 |
| `controller/UserController.java` | 修改 | 2, 3, 7 |
| `service/UserService.java` | 修改 | 3, 4, 6, 7, 9, 10 |
| `config/SecurityConfig.java` | 修改 | 5, 14 |
| `dto/request/UserUpdateRequest.java` | **新增** | 7 |
| `dto/response/UserResponse.java` | 修改 | 8 |
| `mapper/UserMapper.java` | 修改 | 7 |
| `exception/GlobalExceptionHandler.java` | 修改 | 12 |
| `filter/JwtAuthFilter.java` | 修改 | 14 |
| `test/controller/UserControllerTest.java` | 修改 | 15 |
| `test/service/UserServiceTest.java` | 修改 | 15 |
| `test/service/UserServiceProfileTest.java` | 修改 | 15 |
