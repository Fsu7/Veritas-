# 技术教学文档

## 开发思路

### 需求分析过程

本次开发涉及4个顺序依赖的任务（Task11→12→13→14），核心目标是实现用户管理模块的完整功能链：

1. **Task11**: 创建Controller+DTO骨架 — 定义API接口契约
2. **Task12**: 实现Service业务逻辑 — 注册/登录/查询/退出
3. **Task13**: 增强JWT安全组件 — 过滤器白名单/MDC/黑名单
4. **Task14**: 扩展画像CRUD — 3个画像端点+数据隔离

关键发现：Task11的Controller依赖Task12的UserService，无法独立编译。因此采用**合并编译策略**：先创建完整UserService（而非空壳），再创建Controller，一步到位。

### 技术选型考虑

| 决策点 | 选项 | 选择 | 理由 |
|--------|------|------|------|
| 密码加密 | MD5/SHA256/BCrypt | BCrypt(strength=10) | 自带盐值，抗彩虹表 |
| Token存储 | 数据库/Redis | Redis黑名单 | 高性能，自动过期 |
| 画像缓存 | @Cacheable/手动Redis | @Cacheable+手动Redis双写 | @Cacheable供Java层使用，Redis JSON供Python AI服务直接消费 |
| 数据隔离 | Filter/Service层 | Service层 | 更灵活，可获取业务上下文 |
| 枚举序列化 | 枚举直接序列化/String dbValue | String dbValue | 跨系统一致性（Python/JSON使用小写值如"master"而非"MASTER"） |

### 架构设计思路

```
请求流程:
前端 → JwtAuthFilter(白名单跳过/Token验证/MDC注入) → SecurityFilterChain → UserController → UserService → Repository
                                                                                                    ↓
                                                                                              Redis缓存/黑名单
```

### 遇到的问题及解决方案

1. **Controller依赖Service编译问题** → 合并Task11+12，一次性创建完整Service
2. **SecurityContext在finally中清理导致测试断言失败** → 使用`doAnswer`在filterChain.doFilter()回调期间捕获SecurityContext状态
3. **ObjectMapper序列化LocalDateTime失败** → 测试中注册JavaTimeModule + disable WRITE_DATES_AS_TIMESTAMPS
4. **RedisTemplate匿名子类在Java 23+无法mock ValueOperations** → 使用Mockito mock ValueOperations接口

## 实现步骤

1. 创建4个请求/响应DTO（RegisterRequest, LoginRequest, UserResponse, LoginResponse），含@Valid校验和@JsonProperty
2. 创建UserService完整实现（register/login/getUserInfo/logout），构造器注入5个依赖
3. 创建UserController（7个端点），构造器注入UserService
4. 修改SecurityConfig，新增PasswordEncoder @Bean
5. 重构JwtAuthFilter：shouldNotFilter白名单、MDC注入、finally清理、边界处理
6. 增强JwtUtil：blacklistToken、isTokenExpired、token_type声明、parseToken中文日志
7. 创建ProfileUpdateRequest/ProfileResponse DTO
8. 扩展UserService：3个画像方法（含数据隔离、Redis同步、缓存注解）
9. 扩展UserController：3个画像端点
10. 编写6个测试类（共48个新测试用例）
11. mvn compile + mvn test验证（167 tests, 0 failures）

## 解决了什么问题

### 核心问题
用户认证全链路从零到可用：注册→登录→Token认证→退出黑名单→画像管理

### 解决方案对比

| 方案 | 优点 | 缺点 | 最终选择 |
|------|------|------|---------|
| Session认证 | 简单 | 不支持分布式 | ❌ |
| JWT无状态 | 无服务端存储 | 无法主动失效 | ❌ |
| JWT+Redis黑名单 | 可主动失效+高性能 | 需Redis依赖 | ✅ |

### 最终方案的优势
- JWT无状态特性保留（大部分请求无需查Redis）
- Redis黑名单仅用于logout场景，TTL=Token剩余有效期自动清理
- 画像JSON同步到Redis供Python AI服务直接消费，避免HTTP回查

## 变更内容

### 新增文件
- `dto/request/RegisterRequest.java` — 注册请求DTO，@NotBlank+@Size+@Email校验
- `dto/request/LoginRequest.java` — 登录请求DTO，@NotBlank校验
- `dto/request/ProfileUpdateRequest.java` — 画像更新请求DTO，枚举字段+@JsonProperty
- `dto/response/UserResponse.java` — 用户响应DTO，不含passwordHash，@JsonProperty("has_profile")
- `dto/response/LoginResponse.java` — 登录响应DTO，含token+@JsonProperty("user_id")
- `dto/response/ProfileResponse.java` — 画像响应DTO，枚举字段使用String dbValue
- `controller/UserController.java` — 7个API端点（4用户+3画像）
- `service/UserService.java` — 7个业务方法（4用户+3画像）+3个私有辅助方法
- 测试文件6个

### 修改文件
- `config/SecurityConfig.java` — 新增PasswordEncoder @Bean (BCryptPasswordEncoder, strength=10)
- `filter/JwtAuthFilter.java` — 重构为白名单跳过+MDC注入+finally清理+边界处理
- `util/JwtUtil.java` — 新增blacklistToken/isTokenExpired，generateToken增加token_type声明，parseToken增加中文错误日志
- 测试文件2个扩展

### 配置变更
- SecurityConfig: 新增`@Bean PasswordEncoder passwordEncoder()` → `BCryptPasswordEncoder(10)`

## 关键技术点

### 1. @JsonProperty跨系统一致性
Java使用camelCase，Python/JSON使用snake_case。通过`@JsonProperty`注解确保DTO输出snake_case：
```java
@JsonProperty("has_profile")
private boolean hasProfile;

@JsonProperty("user_id")
private String userId;
```

### 2. 枚举字段序列化为dbValue
ProfileResponse中枚举字段使用String类型，通过`entity.getEducationLevel().getDbValue()`输出小写值（如"master"而非"MASTER"），确保与Python/JSON端一致。

### 3. JwtAuthFilter白名单+MDC+finally清理
```java
@Override
protected boolean shouldNotFilter(HttpServletRequest request) {
    return WHITELIST_PATHS.stream()
            .anyMatch(pattern -> pathMatcher.match(pattern, uri));
}

@Override
protected void doFilterInternal(...) {
    // Token验证 + MDC注入
    MDC.put("userId", userId);
    try {
        chain.doFilter(request, response);
    } finally {
        SecurityContextHolder.clearContext();
        MDC.remove("userId");
    }
}
```

### 4. 防枚举攻击
登录失败统一返回`AuthenticationException("用户名或密码错误")`，不区分"用户不存在"和"密码错误"。

### 5. Redis黑名单TTL=Token剩余有效期
```java
long remainingTime = jwtUtil.getTokenRemainingTime(token);
redisTemplate.opsForValue().set(key, "1", Duration.ofMillis(remainingTime));
```
Token过期后黑名单key自动清除，无需手动清理。

### 6. 画像Redis双写
@CacheEvict清除Spring Cache + 手动RedisTemplate同步画像JSON，供Python AI服务直接消费。

## 经验总结

### 开发过程中的收获

1. **合并编译策略**：当多个任务存在编译依赖时，先创建完整实现再创建依赖方，比创建空壳+后续填充更高效
2. **finally块清理的测试技巧**：SecurityContext在finally中清理，测试需用`doAnswer`在filterChain回调期间捕获状态
3. **ObjectMapper与LocalDateTime**：Spring Boot自动配置的ObjectMapper已注册JavaTimeModule，但手动`new ObjectMapper()`需要显式注册

### 踩过的坑及如何避免

1. **JwtUtilTest的RedisTemplate匿名子类**：在Java 23+环境下，匿名子类无法mock抽象方法（如ValueOperations的bitField），改用Mockito mock接口
2. **ProfileResponse枚举序列化**：直接序列化枚举会输出枚举名（如"MASTER"），需使用getDbValue()输出dbValue（如"master"）
3. **UserService中ObjectMapper注入**：@InjectMocks不会自动注入非@Mock对象，需用ReflectionTestUtils手动设置

### 最佳实践建议

1. **DTO设计原则**：响应DTO绝不包含敏感字段（passwordHash），请求DTO使用@Valid校验+中文message
2. **Service层数据隔离**：从SecurityContext获取当前用户ID，与路径参数比对，防止越权访问
3. **缓存策略**：写操作@CacheEvict+手动Redis同步，读操作@Cacheable，确保多消费方数据一致
4. **日志安全**：不在日志中输出密码明文，Token使用maskToken()只输出前8位
