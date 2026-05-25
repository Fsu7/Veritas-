# Task04-07 并行开发问题修复计划

## 修复清单

### P1-1: HealthController data.timestamp 与 ApiResponse.timestamp 重复

**问题**: HealthController 在 data Map 中放了 `timestamp`，同时 ApiResponse 外层也有 `timestamp`，导致响应 JSON 中出现两个 timestamp，语义重复且值可能不同。

**修复方案**: 从 HealthController 的 data Map 中移除 `timestamp` 字段，统一使用 ApiResponse 外层的 timestamp。

**修改文件**:
- `Veritas/backend/src/main/java/com/literatureassistant/controller/HealthController.java`
  - 删除 `healthData.put("timestamp", System.currentTimeMillis());` 这一行
- `Veritas/backend/src/test/java/com/literatureassistant/controller/HealthControllerTest.java`
  - 移除 `testHealthEndpointContainsRequiredFields` 中对 `$.data.timestamp` 的断言
  - 外层 `$.timestamp` 的断言已在 `testHealthEndpointReturns200` 中覆盖

**同时更新 task07 prompt.json**:
- `json_prompt/backend/task07_health_controller/prompt.json` 的 response_format 中移除 data 内的 timestamp

---

### P1-2: JwtUtil secret 校验应在 @PostConstruct 中统一做

**问题**: 当前 secret 长度校验仅在 `generateToken` 方法中执行，如果 secret 太短，`parseToken` 不会报错但会静默失败，导致生成和解析行为不一致。

**修复方案**: 将校验移到 `@PostConstruct` 方法中，应用启动时即校验，失败快速报错。

**修改文件**:
- `Veritas/backend/src/main/java/com/literatureassistant/util/JwtUtil.java`
  - 添加 `@PostConstruct` 方法 `validateSecret()`，校验 secret 长度 >= 32
  - 从 `generateToken` 方法中移除校验逻辑
  - 添加 `import jakarta.annotation.PostConstruct;`

---

### P2-1: HealthController 使用字段注入改为构造器注入

**问题**: HealthController 使用 `@Autowired` 字段注入，与 JwtUtil 的构造器注入风格不一致。Spring 推荐构造器注入。

**修复方案**: 改为构造器注入。

**修改文件**:
- `Veritas/backend/src/main/java/com/literatureassistant/controller/HealthController.java`
  - 移除 `@Autowired` 字段注入
  - 添加构造器注入 DataSource 和 RedisTemplate（使用 `final` + 构造器）

---

### P2-2: ApiResponse.timestamp 添加 @JsonProperty 注解

**问题**: task04 FR-004 要求 timestamp 字段使用 `@JsonProperty("timestamp")` 注解，当前缺失。

**修复方案**: 添加 `@JsonProperty("timestamp")` 注解。

**修改文件**:
- `Veritas/backend/src/main/java/com/literatureassistant/dto/common/ApiResponse.java`
  - 在 `timestamp` 字段上添加 `@JsonProperty("timestamp")`
  - 添加 `import com.fasterxml.jackson.annotation.JsonProperty;`

---

### P2-3: GlobalExceptionHandler 添加异常处理顺序注释

**问题**: `handleBusiness(BusinessException)` 在子类处理器之后，虽然 Spring 会优先匹配最具体类型，但缺乏注释说明，未来维护可能误调顺序。

**修复方案**: 添加注释说明顺序重要性。

**修改文件**:
- `Veritas/backend/src/main/java/com/literatureassistant/exception/GlobalExceptionHandler.java`
  - 在 `handleBusiness` 方法上添加注释，说明子类异常处理器必须在父类之前

---

## 执行顺序

1. P1-1: 修复 HealthController timestamp 重复
2. P1-2: JwtUtil @PostConstruct 校验
3. P2-1: HealthController 构造器注入
4. P2-2: ApiResponse @JsonProperty
5. P2-3: GlobalExceptionHandler 注释
6. 编译验证: `mvn compile`
7. 单元测试验证: `mvn test`

## 验证标准

- `mvn compile` 编译成功
- `mvn test` 所有测试通过
- HealthController 响应中只有一个 timestamp（ApiResponse 外层）
- JwtUtil 启动时校验 secret 长度
- 所有注入使用构造器注入风格
