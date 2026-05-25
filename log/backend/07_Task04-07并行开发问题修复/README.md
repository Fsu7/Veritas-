# Task04-07 并行开发问题修复

## 功能描述
- 解决了 task04（ApiResponse/PageResponse/ErrorCode）、task05（BusinessException体系）、task06（JwtUtil/RedisKeyUtil/DateTimeUtil）、task07（HealthController）四个并行开发任务完成后的交叉审查问题
- 修复了5个跨任务一致性和代码质量问题，确保4个任务产出代码无冲突、风格统一、行为一致
- 业务价值：消除并行开发引入的潜在运行时风险，统一代码风格，为后续 JwtAuthFilter 等任务奠定坚实基础

## 实现逻辑
- 修改的核心文件列表：
  - `HealthController.java` — 移除重复 timestamp、改为构造器注入
  - `HealthControllerTest.java` — 移除 `$.data.timestamp` 断言
  - `JwtUtil.java` — secret 校验从 generateToken 移到 @PostConstruct
  - `JwtUtilTest.java` — 测试改为调用 validateSecret()
  - `ApiResponse.java` — timestamp 字段添加 @JsonProperty 注解
  - `GlobalExceptionHandler.java` — 移除误添加的 log.warn
- 使用的算法或设计模式：Fail-Fast 模式（@PostConstruct 启动校验）、构造器注入模式
- 关键代码逻辑说明：
  1. HealthController 的 data Map 中移除 timestamp，统一使用 ApiResponse 外层 timestamp，避免 JSON 响应中出现两个 timestamp
  2. JwtUtil 的 secret 长度校验移到 @PostConstruct，确保应用启动时即校验，而非等到第一次调用 generateToken 时才报错
  3. HealthController 从 @Autowired 字段注入改为 final + 构造器注入，与 JwtUtil 风格一致
  4. ApiResponse.timestamp 添加 @JsonProperty("timestamp")，符合 task04 FR-004 规格

## 接口变更

### Request
无变更（本次修复不涉及请求格式变更）

### Response

**GET /health 修复前**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "status": "UP",
    "timestamp": 1716451200000,
    "mysql": "UP",
    "redis": "UP"
  },
  "timestamp": 1716451200001
}
```

**GET /health 修复后**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "status": "UP",
    "mysql": "UP",
    "redis": "UP"
  },
  "timestamp": 1716451200000
}
```

## 测试结果
- 编译验证：`mvn compile` ✅ 成功
- 单元测试：`mvn test` 81 tests, 0 failures, 0 errors ✅
- 具体测试场景：
  - ApiResponseTest: success/error 工厂方法、JSON 序列化、@JsonProperty ✅
  - PageResponseTest: fromPage 转换、0-based→1-based ✅
  - ErrorCodeTest: 7个枚举值 ✅
  - BusinessExceptionTest: 3个构造方法 ✅
  - AuthenticationExceptionTest: code=401 ✅
  - ResourceNotFoundExceptionTest: message 格式 ✅
  - AIServiceExceptionTest: code=503、cause 保留 ✅
  - GlobalExceptionHandlerTest: 6种异常处理 ✅
  - JwtUtilTest: Token 生成/解析/验证/黑名单/validateSecret ✅
  - RedisKeyUtilTest: 9个 Key 生成方法 ✅
  - DateTimeUtilTest: 格式化/解析/过期判断 ✅
  - HealthControllerTest: /health 端点（需 MySQL+Redis 运行中）✅
- 是否通过：是

## 相关文件
- `Veritas/backend/src/main/java/com/literatureassistant/controller/HealthController.java`
- `Veritas/backend/src/test/java/com/literatureassistant/controller/HealthControllerTest.java`
- `Veritas/backend/src/main/java/com/literatureassistant/util/JwtUtil.java`
- `Veritas/backend/src/test/java/com/literatureassistant/util/JwtUtilTest.java`
- `Veritas/backend/src/main/java/com/literatureassistant/dto/common/ApiResponse.java`
- `Veritas/backend/src/main/java/com/literatureassistant/exception/GlobalExceptionHandler.java`
- `Veritas/backend/src/main/resources/application.yml`（确认 JWT secret 默认值满足 32 字节）
- `Veritas/backend/src/main/java/com/literatureassistant/config/RedisConfig.java`（确认 RedisTemplate<String, String> Bean 已注册）
