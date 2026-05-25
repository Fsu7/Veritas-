# 技术教学文档

## 开发思路
- 需求分析过程：4个并行开发任务（task04-07）完成后，需要交叉审查是否存在冲突、依赖问题或代码风格不一致。通过逐文件阅读代码并与 prompt.json 规格对比，发现了5个问题（2个P1 + 3个P2）
- 技术选型考虑：修复方案优先选择 Spring 社区推荐的最佳实践（构造器注入、Fail-Fast 校验），而非最小改动
- 架构设计思路：4个任务的依赖关系为 task04 → task05/task07（单向依赖），task06 相对独立。核心冲突不在文件层面（无重叠），而在 API 契约和代码风格层面
- 遇到的问题及解决方案：
  1. **timestamp 重复** — HealthController 在 data 内外各放了一个 timestamp → 移除 data 内的，统一使用 ApiResponse 外层
  2. **secret 校验时机错误** — generateToken 中校验导致"生成成功但解析失败"的不一致 → 移到 @PostConstruct 启动时校验
  3. **注入风格不一致** — HealthController 用字段注入，JwtUtil 用构造器注入 → 统一为构造器注入
  4. **@JsonProperty 缺失** — task04 FR-004 明确要求但未实现 → 补充
  5. **RedisTemplate 泛型** — 担心 RedisTemplate<String, String> Bean 不存在 → 检查 RedisConfig 确认已注册

## 实现步骤
1. 读取4个 prompt.json 规格文件，提取验收标准
2. 读取所有已实现的 Java 源文件和测试文件
3. 逐项对比规格与实现，标记偏差
4. 分析跨任务依赖关系和潜在冲突
5. 按优先级（P1 > P2）制定修复计划
6. 执行修复：HealthController timestamp + 构造器注入、JwtUtil @PostConstruct、ApiResponse @JsonProperty
7. 同步更新测试代码
8. 编译验证 + 单元测试验证

## 解决了什么问题
- 核心问题描述：4个并行任务产出代码存在5处一致性问题，可能导致运行时错误或维护困难
- 解决方案对比：
  - timestamp 重复：方案A（移除 data 内 timestamp）vs 方案B（改名为 checked_at）→ 选择方案A，更简洁
  - secret 校验：方案A（@PostConstruct）vs 方案B（保留在 generateToken + parseToken 中也校验）→ 选择方案A，Fail-Fast 更优
- 最终方案的优势：修复量最小、符合 Spring 最佳实践、不影响已有 API 契约

## 变更内容

### 新增文件
无新增文件（本次为修复，不新增类）

### 修改文件
- `HealthController.java`
  - 移除 `healthData.put("timestamp", ...)` — 消除与 ApiResponse 外层 timestamp 重复
  - 移除 `@Autowired` 字段注入，改为 `final` + 构造器注入
  - 移除 `import org.springframework.beans.factory.annotation.Autowired`
- `HealthControllerTest.java`
  - 移除 `testHealthEndpointContainsRequiredFields` 中 `$.data.timestamp` 断言
- `JwtUtil.java`
  - 新增 `@PostConstruct validateSecret()` 方法，启动时校验 secret 长度 >= 32 字节
  - 从 `generateToken` 中移除 secret 长度校验逻辑
  - 新增 `import jakarta.annotation.PostConstruct`
  - `validateSecret()` 增加 `secret == null` 判断
- `JwtUtilTest.java`
  - `shouldThrowWhenSecretTooShort` 测试从调用 `generateToken` 改为调用 `validateSecret()`
- `ApiResponse.java`
  - `timestamp` 字段添加 `@JsonProperty("timestamp")`
  - 新增 `import com.fasterxml.jackson.annotation.JsonProperty`
- `GlobalExceptionHandler.java`
  - 移除误添加的 `log.warn("Business error: {}", e.getMessage())`（BusinessException 通用处理器不应添加日志，具体子类处理器已有日志）

### 配置变更
无配置变更（确认 application.yml 中 JWT secret 默认值 40 字节满足要求）

## 关键技术点
- **@PostConstruct Fail-Fast 模式**：Spring Bean 初始化完成后立即校验配置，避免运行时才发现配置错误。比在业务方法中校验更安全，因为不会出现"部分方法成功、部分方法失败"的不一致行为
- **构造器注入 vs 字段注入**：Spring 官方推荐构造器注入，优势包括：不可变性（final 字段）、显式依赖、易于单元测试（不需要反射设置字段）、避免循环依赖
- **ApiResponse 统一包装的 timestamp 语义**：ApiResponse 的 timestamp 代表"响应生成时刻"，是所有接口的通用字段。HealthController data 内的 timestamp 是多余的，因为健康检查的"检查时刻"与"响应时刻"几乎同时
- **@ExceptionHandler 匹配规则**：Spring 的 @ExceptionHandler 会匹配最具体的异常类型，因此子类异常处理器（AuthenticationException、ResourceNotFoundException、AIServiceException）必须在父类（BusinessException）之前声明，否则父类会拦截所有子类异常

## 经验总结
- **并行开发审查必不可少**：即使4个任务修改的文件完全不重叠，API 契约层面仍可能存在冲突（如 timestamp 重复）。并行开发完成后必须做交叉审查
- **RedisTemplate 泛型陷阱**：Spring Data Redis 默认注入 `RedisTemplate<Object, Object>`，如果代码中需要 `RedisTemplate<String, String>`，必须手动注册 Bean（在 RedisConfig 中）。本次确认已有 RedisConfig，但这是一个常见的启动失败原因
- **@PostConstruct 校验是 Spring 最佳实践**：任何通过 @Value 注入的配置，如果有关键约束（如最小长度、格式要求），都应在 @PostConstruct 中校验，而非在使用时才校验
- **构造器注入应作为团队规范**：统一使用构造器注入可以避免字段注入带来的测试困难和隐式依赖问题。新代码应一律使用构造器注入
- **健康检查端点设计原则**：/health 端点必须始终返回 200（组件 DOWN 时也返回 200），不抛异常，不依赖 JPA 层（使用 DataSource 直接连接验证）
