# UserController + RegisterRequest/LoginRequest DTO

## 项目上下文

- **项目**：XH-202630 科研文献智能助手
- **版本**：v0.2
- **里程碑**：M3 前后端联调 / JM2 基础API可用
- **功能编号**：F2.1.1, F2.1.2, F2.1.3

## 涉及层级

java_backend

## 修改范围

| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | UserController.java | 用户API控制器：4个端点 |
| 新增 | RegisterRequest.java | 注册请求DTO |
| 新增 | LoginRequest.java | 登录请求DTO |
| 新增 | UserResponse.java | 用户响应DTO |
| 新增 | LoginResponse.java | 登录响应DTO |

## 功能要求

| 编号 | 描述 | 优先级 | 验收条件 |
|------|------|--------|---------|
| FR-001 | UserController 4个API端点 | P0 | 编译通过，不含业务逻辑 |
| FR-002 | RegisterRequest @Valid校验 | P0 | 空用户名/非法邮箱/短密码返回400 |
| FR-003 | LoginRequest @Valid校验 | P0 | 空用户名/空密码返回400 |
| FR-004 | UserResponse不含passwordHash | P0 | 密码哈希不泄露 |
| FR-005 | LoginResponse含JWT Token | P0 | @JsonProperty确保snake_case |
| FR-006 | logout提取Bearer Token | P0 | 正确提取并传递 |

## 跨系统一致性

- 字段命名：Java camelCase ↔ Python/JSON snake_case
- API契约：POST /api/users/register, POST /api/users/login
- 数据流转：前端→Controller→Service→Repository

## 降级策略

- LLM降级：BuiltinLLMProvider → APILLMProvider → LocalLLMProvider
- Agent降级：单Agent超时30s跳过，多Agent失败降级为单Agent模式

## 约束

- 分层：Controller → Service → Repository → Client
- 异常：BusinessException + GlobalExceptionHandler
- 缓存：Cache-Aside，TTL分层
- 日志：SLF4J + Logback，requestId MDC
- 安全：BCrypt，JWT+Redis黑名单，数据隔离

## 禁止行为

- ❌ 输出伪代码或TODO注释
- ❌ Controller中编写业务逻辑
- ❌ UserResponse包含passwordHash
- ❌ Entity直接返回前端
- ❌ 硬编码敏感配置
- ❌ 违反跨系统字段命名约定
- ❌ 日志中输出password明文

## 测试要求

- 单元测试：JUnit5
- 验证命令：`cd Veritas/backend && mvn test`

## 验收标准

| 编号 | 标准 | 验证方式 |
|------|------|---------|
| AC-001 | UserController 4个API端点编译通过 | automated_test |
| AC-002 | RegisterRequest @Valid校验生效 | automated_test |
| AC-003 | LoginRequest @Valid校验生效 | automated_test |
| AC-004 | UserResponse不含passwordHash | code_review |
| AC-005 | LoginResponse @JsonProperty正确 | code_review |
| AC-006 | Controller不含业务逻辑 | code_review |
| AC-007 | logout正确提取Bearer Token | automated_test |
| AC-008 | DTO使用Lombok注解 | code_review |
| AC-009 | 单元测试全部通过 | automated_test |
