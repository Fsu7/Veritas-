# 技术教学文档

## 开发思路

### 需求分析过程
本次任务源于对用户管理模块（F2.1）的架构审阅。审阅发现了 2 个 P0 严重问题、5 个 P1 重要问题、6 个 P2 建议和 3 个 P3 提示。需求不是新功能开发，而是对已有代码的质量提升和安全加固。

审阅使用 java-review Skill，按照 review-checklist.md 逐项检查，涵盖架构一致性、代码质量、API规范、数据库、安全性、性能、并发、可测试性、可观测性等9个维度。

### 技术选型考虑
- **Entity equals/hashCode**：选择 `@EqualsAndHashCode(onlyExplicitlyIncluded = true)` 仅基于主键 ID，而非基于业务 ID（userId），因为 JPA 在 `@PrePersist` 之前 id 为 null，基于 id 的 equals 在新建实体时行为正确
- **logout 逻辑下沉**：将 Token 解析和权限校验从 Controller 移到 Service，符合分层架构原则
- **HTTP 状态码对齐**：选择 `ResponseEntity<ApiResponse<Void>>` 而非在 ApiResponse 中加 httpCode 字段，因为 Spring MVC 原生支持 ResponseEntity，且前端 Axios 拦截器可直接根据 HTTP 状态码处理

### 架构设计思路
- **P0 优先**：先修复运行时可能崩溃的问题（NPE、Entity equals 隐患）
- **分层严格化**：Controller 不再直接依赖 JwtUtil，所有业务逻辑在 Service 层
- **安全加固**：validateDataIsolation 从"放行未认证"改为"拒绝未认证"
- **功能补全**：补充架构文档定义但未实现的 PUT /api/users/{userId}

### 遇到的问题及解决方案

| 问题 | 解决方案 |
|------|---------|
| Entity @Data 导致 JPA 行为异常 | 替换为 @Getter @Setter @EqualsAndHashCode(onlyExplicitlyIncluded=true) |
| logout 时 tokenUserId 为 null 导致 NPE | 在 equals 前增加 null 检查，null 时抛 BusinessException |
| Controller 直接依赖 JwtUtil | 将 logout 逻辑封装为 logoutWithAuth() 下沉到 Service |
| GlobalExceptionHandler 全部返回 200 | 改为 ResponseEntity，HTTP 状态码与业务码对齐 |
| 测试中 validateDataIsolation 抛 AuthenticationException | 在 @BeforeEach 中设置 SecurityContext |

## 实现步骤

1. **Step 1 (P0)**：修复 User.java 和 UserProfile.java 的 `@Data` 注解，替换为 `@Getter @Setter @EqualsAndHashCode(onlyExplicitlyIncluded=true)`，排除敏感字段的 toString
2. **Step 2 (P0)**：修复 UserController.logout() 中 tokenUserId 为 null 时的 NPE 风险
3. **Step 3 (P1)**：将 logout 业务逻辑从 Controller 下沉到 UserService.logoutWithAuth()
4. **Step 4 (P1)**：统一 getUserInfo() 异常类型为 ResourceNotFoundException
5. **Step 5 (P1)**：收紧 CORS allowedHeaders 从 `*` 到3个具体 Header
6. **Step 6 (P1)**：login() 添加 `@Transactional(readOnly = true)`
7. **Step 7 (P1)**：补充 PUT /api/users/{userId} 接口 + UserUpdateRequest DTO
8. **Step 8 (P2)**：UserResponse.userId 添加 `@JsonProperty("user_id")`
9. **Step 9 (P2)**：register() 移除不必要的 existsByUserId 查询
10. **Step 10 (P2)**：validateDataIsolation() 加固 — null 认证直接拒绝
11. **Step 12 (P2)**：GlobalExceptionHandler HTTP 状态码对齐
12. **Step 13 (P3)**：UserProfile 移除冗余 @Convert 注解
13. **Step 14 (P3)**：JwtAuthFilter/SecurityConfig 改用 @RequiredArgsConstructor
14. **Step 15**：更新所有受影响的测试代码
15. **Step 16**：编译验证 — mvn compile + mvn test 全部通过

## 解决了什么问题

### 核心问题描述

1. **JPA Entity @Data 隐患**：`@Data` 自动生成包含所有字段的 equals/hashCode，对 JPA Entity 有3大隐患：新建实体（id=null）与已持久化实体 equals 返回 false；延迟加载字段触发额外 SQL；循环引用导致 StackOverflow

2. **logout NPE 风险**：`jwtUtil.getUserIdFromToken(rawToken)` 在 Token 过期/无效时返回 null，后续 `tokenUserId.equals(currentUserId)` 抛出 NullPointerException

3. **Controller 违反分层原则**：UserController 直接注入 JwtUtil，在 logout 方法中执行 Token 解析和权限校验逻辑

4. **数据隔离漏洞**：validateDataIsolation 在 currentUserId == null 时放行，意味着未认证用户可能访问他人数据

5. **HTTP 状态码语义错误**：所有异常都返回 HTTP 200 + 业务码，前端需要同时检查两个维度的错误

### 解决方案对比

| 问题 | 方案A | 方案B | 最终选择 |
|------|-------|-------|---------|
| Entity equals | 基于 userId 的 equals | 基于 id 的 equals | **基于 id**（JPA 标准做法，@PrePersist 前后行为一致） |
| logout NPE | 在 Controller 加 null 检查 | 逻辑下沉到 Service | **下沉到 Service**（同时解决分层问题） |
| HTTP 状态码 | 在 ApiResponse 加 httpCode 字段 | 使用 ResponseEntity | **ResponseEntity**（Spring 原生支持，前端拦截器友好） |
| 数据隔离 | 依赖 SecurityConfig 的 .authenticated() | 双重保障：validateDataIsolation 也拒绝 null | **双重保障**（防御性编程） |

### 最终方案的优势
- **安全性提升**：双重数据隔离保障 + CORS 收紧 + HTTP 状态码正确
- **架构一致性**：Controller 不再跨层依赖 Util
- **可维护性**：Entity equals/hashCode 行为可预测
- **API 语义正确**：HTTP 状态码与业务含义一致

## 变更内容

### 新增文件
- `dto/request/UserUpdateRequest.java` — 用户信息更新请求 DTO，包含 username（@Size 3-50）和 email（@Email）字段

### 修改文件

| 文件 | 变更点 |
|------|--------|
| `entity/User.java` | `@Data` → `@Getter @Setter @EqualsAndHashCode(onlyExplicitlyIncluded=true) @ToString(exclude={"passwordHash","email"})`；删除手动 toString()；id 字段添加 `@EqualsAndHashCode.Include` |
| `entity/UserProfile.java` | `@Data` → `@Getter @Setter @EqualsAndHashCode(onlyExplicitlyIncluded=true)`；id 字段添加 `@EqualsAndHashCode.Include`；移除3个 `@Convert` 注解 |
| `controller/UserController.java` | 移除 `JwtUtil` 依赖和 `BusinessException`/`SecurityContextHolder` import；logout 方法简化为 `userService.logoutWithAuth(authHeader)`；新增 `PUT /{userId}` 端点 |
| `service/UserService.java` | 新增 `logoutWithAuth()` 和 `updateUser()` 方法；`login()` 加 `@Transactional(readOnly=true)`；`getUserInfo()` 改用 `ResourceNotFoundException`；`register()` 移除 `existsByUserId` 查询直接传 false；`validateDataIsolation()` 加固 null 认证拒绝 |
| `config/SecurityConfig.java` | CORS `allowedHeaders` 从 `List.of("*")` 改为 `Arrays.asList("Authorization","Content-Type","X-Request-Id")`；手动构造器改为 `@RequiredArgsConstructor` |
| `filter/JwtAuthFilter.java` | 手动构造器改为 `@RequiredArgsConstructor` |
| `exception/GlobalExceptionHandler.java` | 所有处理器返回类型从 `ApiResponse<Void>` 改为 `ResponseEntity<ApiResponse<Void>>`；新增 `mapCodeToStatus()` 方法 |
| `dto/response/UserResponse.java` | `userId` 字段添加 `@JsonProperty("user_id")` |

### 测试文件变更

| 文件 | 变更点 |
|------|--------|
| `UserControllerTest.java` | 移除 `@Mock JwtUtil`；logout 测试改为 Mock `userService.logoutWithAuth()`；新增 updateUser 和 invalidToken 测试 |
| `UserServiceTest.java` | 新增 logoutWithAuth/updateUser/getUserInfo 测试；register 测试验证不调用 existsByUserId；updateUser 测试添加 SecurityContext |
| `UserServiceProfileTest.java` | @BeforeEach 设置 SecurityContext；@AfterEach 清除 SecurityContext；新增未认证/越权访问测试 |
| `GlobalExceptionHandlerTest.java` | 所有断言从 `ApiResponse<Void>` 改为 `ResponseEntity<ApiResponse<Void>>`；验证 HTTP 状态码 |

### 配置变更
- 无 application.yml 变更

## 关键技术点

### 1. JPA Entity 的 equals/hashCode 最佳实践

JPA Entity 使用 `@Data` 是常见的反模式。正确做法：

```java
@Getter
@Setter
@EqualsAndHashCode(onlyExplicitlyIncluded = true)
@ToString(exclude = {"passwordHash", "email"})
public class User {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @EqualsAndHashCode.Include
    private Long id;
}
```

**为什么仅基于 id？**
- 新建实体 id=null，持久化后 id=1，基于所有字段的 equals 会返回 false
- 在 `Set<User>` 或 `Map<User, ?>` 中使用时行为不可预测
- 延迟加载字段触发额外 SQL 查询

### 2. Controller 不应包含业务逻辑

```java
// 错误：Controller 直接解析 Token
@PostMapping("/logout")
public ApiResponse<Void> logout(@RequestHeader("Authorization") String authHeader) {
    String rawToken = jwtUtil.extractBearerToken(authHeader);
    String tokenUserId = jwtUtil.getUserIdFromToken(rawToken);
    // ... 权限校验逻辑
}

// 正确：Controller 只做参数传递
@PostMapping("/logout")
public ApiResponse<Void> logout(@RequestHeader("Authorization") String authHeader) {
    userService.logoutWithAuth(authHeader);
    return ApiResponse.success(null);
}
```

### 3. GlobalExceptionHandler HTTP 状态码对齐

```java
@ExceptionHandler(BusinessException.class)
public ResponseEntity<ApiResponse<Void>> handleBusiness(BusinessException e) {
    HttpStatus status = mapCodeToStatus(e.getCode());
    return ResponseEntity.status(status).body(ApiResponse.error(e.getCode(), e.getMessage()));
}

private HttpStatus mapCodeToStatus(int code) {
    return switch (code) {
        case 400 -> HttpStatus.BAD_REQUEST;
        case 401 -> HttpStatus.UNAUTHORIZED;
        case 403 -> HttpStatus.FORBIDDEN;
        case 404 -> HttpStatus.NOT_FOUND;
        case 409 -> HttpStatus.CONFLICT;
        case 503 -> HttpStatus.SERVICE_UNAVAILABLE;
        default -> HttpStatus.INTERNAL_SERVER_ERROR;
    };
}
```

### 4. 防御性编程：数据隔离双重保障

```java
private void validateDataIsolation(String userId) {
    String currentUserId = getCurrentUserId();
    if (currentUserId == null) {
        throw new AuthenticationException("未认证，请先登录");
    }
    if (!currentUserId.equals(userId)) {
        throw new BusinessException(403, "无权限访问他人数据", "FORBIDDEN_ACCESS");
    }
}
```

虽然 SecurityConfig 配置了 `.anyRequest().authenticated()`，但 Service 层也应做防御性检查，避免绕过 Filter 的场景。

### 5. 部分更新模式

```java
public UserResponse updateUser(String userId, UserUpdateRequest request) {
    User user = userRepository.findByUserId(userId)
            .orElseThrow(() -> new ResourceNotFoundException("User", userId));

    if (request.getUsername() != null && !request.getUsername().equals(user.getUsername())) {
        if (userRepository.existsByUsername(request.getUsername())) {
            throw new BusinessException(409, "用户名已存在", "USERNAME_DUPLICATE");
        }
        user.setUsername(request.getUsername());
    }
    // email 同理
    userRepository.save(user);
}
```

**关键点**：先检查字段是否有变更，再检查唯一性，避免不必要的 DB 查询。

## 经验总结

### 开发过程中的收获
1. **审阅驱动开发**：先做全面审阅再按优先级修复，比边写边改效率高得多
2. **P0 优先原则**：先修复可能导致运行时崩溃的问题，再处理架构和规范问题
3. **测试先行验证**：修改 GlobalExceptionHandler 后，测试代码也需要同步更新返回类型

### 踩过的坑及如何避免
1. **Entity @Data 陷阱**：Lombok `@Data` 对 JPA Entity 不安全，项目编码规范应明确禁止，改用 `@Getter @Setter @EqualsAndHashCode(onlyExplicitlyIncluded=true)`
2. **SecurityContext 测试遗漏**：validateDataIsolation 依赖 SecurityContext，单元测试必须手动设置，否则会抛 AuthenticationException 导致测试失败
3. **JSON 字段不一致**：UserResponse.userId 缺少 `@JsonProperty("user_id")`，导致前端收到的字段名与 ProfileResponse 不一致。应在 DTO 创建时就统一 snake_case 输出

### 最佳实践建议
1. **JPA Entity 模板**：所有 Entity 统一使用 `@Getter @Setter @EqualsAndHashCode(onlyExplicitlyIncluded=true) @ToString(exclude=敏感字段)` 注解组合
2. **Controller 依赖原则**：Controller 只依赖 Service，不直接依赖 Util/Repository/Client
3. **异常类型精确化**：404 用 ResourceNotFoundException，401 用 AuthenticationException，409 用 BusinessException(409)
4. **HTTP 状态码对齐**：GlobalExceptionHandler 应返回 ResponseEntity，HTTP 状态码与业务码语义一致
5. **测试 SecurityContext**：涉及认证/授权的 Service 测试，必须在 @BeforeEach 设置 SecurityContext，@AfterEach 清除
