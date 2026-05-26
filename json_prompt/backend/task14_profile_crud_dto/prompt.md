# 用户画像CRUD + ProfileUpdateRequest/ProfileResponse

## 项目上下文

- **项目**：XH-202630 科研文献智能助手
- **版本**：v0.2
- **里程碑**：M3：前后端联调 / JM2：Java后端M2
- **功能编号**：F2.1.5

## 涉及层级

- `java_backend` — DTO创建、Service扩展、Controller扩展
- `data_layer` — Redis缓存操作（画像JSON同步）

## 修改范围

| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | `dto/request/ProfileUpdateRequest.java` | 画像请求DTO：4字段 + @NotNull/@NotBlank校验 + @JsonProperty snake_case |
| 新增 | `dto/response/ProfileResponse.java` | 画像响应DTO：6字段 + @JsonProperty snake_case + 枚举输出dbValue字符串 |
| 修改 | `service/UserService.java` | 扩展3个画像方法：getProfile/createProfile/updateProfile（含缓存+事务+Redis同步） |
| 修改 | `controller/UserController.java` | 扩展3个画像端点：GET/POST/PUT /api/users/{userId}/profile |

## 已有实现

| 文件 | 说明 | 复用方式 |
|------|------|---------|
| `entity/UserProfile.java` | UserProfile实体（userId, educationLevel枚举, researchField, knowledgeLevel枚举, preferredStyle枚举, profileData JSON, updatedAt） | 直接复用 |
| `repository/UserProfileRepository.java` | findByUserId(), existsByUserId() | 直接复用 |
| `repository/UserRepository.java` | findByUserId()，用于校验用户存在 | 直接复用 |
| `enums/EducationLevel.java` | UNDERGRADUATE/MASTER/PHD/FACULTY + getDbValue() | 直接复用 |
| `enums/KnowledgeLevel.java` | BEGINNER/INTERMEDIATE/ADVANCED/EXPERT + getDbValue() | 直接复用 |
| `enums/PreferredStyle.java` | SIMPLE/BALANCED/TECHNICAL + getDbValue() | 直接复用 |
| `dto/common/ApiResponse.java` | 统一响应封装 | 直接复用 |
| `exception/BusinessException.java` | 业务异常（code, message, errorKey） | 直接复用 |
| `exception/ResourceNotFoundException.java` | 资源不存在异常（404） | 直接复用 |
| `util/RedisKeyUtil.java` | userProfileKey(userId) → "user:profile:" + userId | 直接复用 |
| `config/RedisConfig.java` | CacheManager + RedisTemplate<String, String> | 直接复用 |
| `service/UserService.java` | 已有register/login/getUserInfo/updateUser/logout | 扩展 |
| `controller/UserController.java` | 已有register/login/getUser端点 | 扩展 |

## 功能要求

| 编号 | 描述 | 优先级 | 验收条件 |
|------|------|--------|---------|
| FR-001 | ProfileUpdateRequest DTO：4字段（educationLevel/researchField/knowledgeLevel/preferredStyle），@NotNull/@NotBlank校验 + @JsonProperty snake_case映射 | P0 | 4个字段均有校验注解和@JsonProperty |
| FR-002 | ProfileResponse DTO：6字段（userId/educationLevel/researchField/knowledgeLevel/preferredStyle/updatedAt），@JsonProperty snake_case输出，枚举字段输出dbValue字符串 | P0 | 6个字段均有@JsonProperty，枚举输出dbValue |
| FR-003 | UserService.getProfile：findByUserId → 不存在抛404 → Entity转ProfileResponse → @Cacheable(userProfile) | P0 | 正常返回ProfileResponse，缓存命中直接返回 |
| FR-004 | UserService.createProfile：校验用户存在 → 校验画像不存在(409) → 转换保存 → 同步Redis画像JSON → @Transactional + @CacheEvict(userProfile) | P0 | 正常创建200，用户不存在404，画像已存在409 |
| FR-005 | UserService.updateProfile：查找已有画像(404) → 合并字段 → 保存 → 双重缓存失效(userProfile+userProfileJson) → 同步Redis画像JSON → @Transactional | P0 | 正常更新200，画像不存在404，双重缓存失效 |
| FR-006 | UserController新增3个画像端点：GET/POST/PUT /api/users/{userId}/profile，@Valid校验 | P0 | 3个端点正常工作 |
| FR-007 | Entity→DTO转换：私有方法convertToProfileResponse，枚举字段调用getDbValue()输出dbValue字符串 | P0 | 枚举输出"master"而非"MASTER" |
| FR-008 | Redis画像JSON同步：createProfile/updateProfile后使用RedisTemplate写入Redis（key=user:profile:{userId}, TTL=1h），供Python AI服务消费 | P1 | Redis中存在画像JSON |
| FR-009 | 数据隔离：Service层校验userId与当前认证用户一致，不一致抛403 | P0 | 非本人访问返回403 |

## 跨系统一致性

### 字段命名映射

| Java (camelCase) | Python/JSON (snake_case) | 映射方式 |
|------------------|--------------------------|---------|
| educationLevel | education_level | @JsonProperty |
| knowledgeLevel | knowledge_level | @JsonProperty |
| preferredStyle | preferred_style | @JsonProperty |
| researchField | research_field | @JsonProperty |
| userId | user_id | @JsonProperty |
| updatedAt | updated_at | @JsonProperty |

### API契约

**GET /api/users/{userId}/profile**

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
  }
}
```

**POST /api/users/{userId}/profile**

请求体：
```json
{
  "education_level": "master",
  "research_field": "NLP",
  "knowledge_level": "intermediate",
  "preferred_style": "balanced"
}
```

**PUT /api/users/{userId}/profile**

请求体：
```json
{
  "education_level": "phd",
  "research_field": "CV",
  "knowledge_level": "advanced",
  "preferred_style": "technical"
}
```

### 数据流转

```
前端 snake_case JSON → ProfileUpdateRequest(@JsonProperty接收) → UserService转换Entity(Java枚举)
→ JPA存储MySQL(dbValue字符串) → Entity转ProfileResponse(枚举getDbValue()→snake_case字符串)
→ @JsonProperty输出snake_case JSON → 前端

同时 createProfile/updateProfile → RedisTemplate同步画像JSON → Redis(user:profile:{userId}, TTL=1h) → Python AI服务消费
```

## 降级策略

- LLM降级：BuiltinLLMProvider → APILLMProvider → LocalLLMProvider
- Agent降级：单Agent超时30s跳过，多Agent失败降级为单Agent模式
- 本功能不涉及LLM调用，无降级要求

## 约束

### 命名规范

- 类名PascalCase：ProfileUpdateRequest、ProfileResponse
- 方法名camelCase：getProfile()、createProfile()、updateProfile()
- 常量UPPER_SNAKE_CASE：PROFILE_ALREADY_EXISTS
- 枚举值UPPER_SNAKE_CASE：EducationLevel.MASTER
- JSON字段snake_case：education_level、knowledge_level

### 分层规范

- Controller：仅接收请求 + @Valid校验 + 调用Service + 返回ApiResponse
- Service：业务逻辑 + Entity↔DTO转换 + 缓存注解 + 事务管理 + Redis操作
- Repository：仅数据访问，不含业务逻辑
- 禁止跨层调用（Controller不直接操作UserProfileRepository）

### 错误处理

- 画像不存在：ResourceNotFoundException("UserProfile", userId) → 404
- 画像已存在：BusinessException(409, "用户画像已存在", "PROFILE_ALREADY_EXISTS") → 409
- 用户不存在：ResourceNotFoundException("User", userId) → 404
- 数据隔离违规：BusinessException(403, "无权限访问他人画像", "FORBIDDEN_ACCESS") → 403
- 参数校验失败：@Valid → MethodArgumentNotValidException → GlobalExceptionHandler → 400

### 缓存策略

| 方法 | 缓存注解 | 说明 |
|------|---------|------|
| getProfile | @Cacheable(value="userProfile", key="#userId", unless="#result == null") | 缓存命中直接返回 |
| createProfile | @CacheEvict(value="userProfile", key="#userId") | 创建后失效缓存 |
| updateProfile | @CacheEvict(value={"userProfile", "userProfileJson"}, key="#userId") | 双重失效：userProfile + userProfileJson(Python服务消费) |

### 日志

- SLF4J + @Slf4j
- 关键操作记录info日志：画像创建成功、画像更新成功
- 异常记录warn/error日志
- 禁止日志中输出敏感信息

### 数据库

- JPA参数化查询，禁止SQL拼接
- UserProfile实体使用DbValueEnum + @Convert体系映射枚举
- user_profiles.user_id唯一约束保证画像唯一性

### 安全

- JWT认证：3个画像端点均需Token
- 数据隔离：Service层校验userId与当前认证用户一致
- ProfileResponse不包含敏感信息

## 禁止行为

- ❌ FA-001：输出伪代码或TODO注释
- ❌ FA-002：修改需求范围外的模块
- ❌ FA-003：破坏三层分离架构
- ❌ FA-004：Controller直接操作Repository
- ❌ FA-005：Entity直接返回给前端
- ❌ FA-006：硬编码敏感配置
- ❌ FA-007：枚举字段输出Java枚举名而非dbValue（必须输出"master"而非"MASTER"）
- ❌ FA-008：循环中打印INFO及以上级别日志
- ❌ FA-009：使用SQL拼接
- ❌ FA-010：Controller中编写业务逻辑

## 测试要求

### 单元测试（JUnit5）

| 测试类 | 覆盖场景 |
|--------|---------|
| ProfileUpdateRequestTest | @Valid校验：null educationLevel、blank researchField、null knowledgeLevel、null preferredStyle |
| UserServiceProfileTest | getProfile正常/404/缓存命中；createProfile正常/409已存在/404用户不存在；updateProfile正常/404/字段合并/双重缓存失效；403数据隔离 |

### 集成测试

| 测试类 | 覆盖场景 |
|--------|---------|
| ProfileControllerIntegrationTest | GET 200、POST 200、POST 409、PUT 200、PUT 404、@Valid 400 |

### 验证命令

```bash
cd Veritas/backend && mvn compile
cd Veritas/backend && mvn test -Dtest=ProfileUpdateRequestTest,UserServiceProfileTest
cd Veritas/backend && mvn test
```

## 验收标准

| 编号 | 标准 | 验证方式 |
|------|------|---------|
| AC-001 | GET /api/users/{userId}/profile 返回 ApiResponse<ProfileResponse>，字段snake_case | 自动测试 |
| AC-002 | POST /api/users/{userId}/profile 创建画像成功返回200 | 自动测试 |
| AC-003 | PUT /api/users/{userId}/profile 更新画像成功返回200 | 自动测试 |
| AC-004 | ProfileUpdateRequest @Valid校验生效（null/blank字段返回400） | 自动测试 |
| AC-005 | ProfileResponse枚举字段输出dbValue字符串（"master"而非"MASTER"） | 自动测试 |
| AC-006 | getProfile使用@Cacheable(userProfile) | 代码审查 |
| AC-007 | updateProfile使用@CacheEvict({userProfile, userProfileJson})双重失效 | 代码审查 |
| AC-008 | createProfile画像已存在返回409 | 自动测试 |
| AC-009 | getProfile/updateProfile画像不存在返回404 | 自动测试 |
| AC-010 | createProfile/updateProfile后Redis中存在画像JSON（TTL=1h） | 自动测试 |
| AC-011 | 非本人userId访问画像返回403 | 自动测试 |
| AC-012 | Controller不含业务逻辑 | 代码审查 |
| AC-013 | 所有单元测试通过 | 自动测试 |
