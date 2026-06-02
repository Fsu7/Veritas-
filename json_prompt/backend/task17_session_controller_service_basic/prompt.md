# SessionController + SessionService (基础) Coding Task

> 任务编号：`task17_session_controller_service_basic`
> 对应需求编号：`F2.3.1` ~ `F2.3.5`
> 里程碑：M3 前后端联调 / JM2 Java后端M2（Week 5 Day 4 上午）

---

## 1. Context（项目上下文）

| 字段 | 值 |
|------|-----|
| 项目 | XH-202630 科研文献智能助手 — 领域知识个性化生成与多智能体协同决策系统研究 |
| 版本 | v0.2 |
| 里程碑 | M3：前后端联调 / JM2：Java后端M2 基础API可用（Week 5 Day 4 上午） |
| 涉及模块 | F2.3 会话管理模块（Controller + Service 基础） |
| 涉及层级 | `java_backend` + `data_layer` |

### 需求描述

实现会话管理模块的 5 个 REST API 端点（F2.3.1 ~ F2.3.5）：

- 新增 `SessionCreateRequest` DTO（含 topic `@NotBlank`/`@Size` 校验）
- 新增 `SessionResponse` DTO（`@JsonProperty` 输出 `session_id`/`user_id`/`created_at` 等 `snake_case` 字段，`SessionStatus` 枚举在 JSON 中序列化为小写 dbValue）
- `SessionService` 实现 5 个核心方法：`createSession`（生成 sessionId + `status=ACTIVE`）/ `listSessions`（按 `userId` 分页 + `createdAt DESC`）/ `getSessionDetail`（含数据隔离 + `@Cacheable` 2h）/ `updateStatus`（接受 `SessionStatus` 枚举 + `@CacheEvict`）/ `deleteSession`（硬删除 + `@CacheEvict`）
- `SessionController` 暴露 5 个 REST 端点（`@RequestMapping("/api/sessions")`，`@Valid` 参数校验，调用 Service 后包装 `ApiResponse`）

> **本任务边界（关键）**：
> - **不**实现完整状态机规则（ACTIVE→COMPLETED/EXPIRED 转换、终态不可转换等）— 属于 task18
> - **不**创建 `SessionMapper`（MapStruct）— 属于 task18
> - **不**创建 `SessionDetailResponse` — 属于 task18
> - **不**实现 `SessionStatusUpdateRequest` 完整校验 — 仅创建占位类，task18 完善

### 参考文档

| 路径 | 用途 |
|------|------|
| `docs/backend/Java后端模块系统架构文档.md` | §6 会话管理模块 F2.3、§11 数据模型规范、§12 统一响应、§13 安全架构 |
| `docs/database/数据库设计文档.md` | §3.4 sessions 表结构 |
| `AGENTS.md` | §7.2 Redis 缓存 Key、§8.1 API 契约、§9.2 Java 后端规范 |
| `docs/backend/Java后端模块项目里程碑文档.md` | §4 JM2 任务分解、§4.4 JM2 验收检查点 |

---

## 2. Current Architecture（当前架构）

**涉及层级**：`Controller → Service → Repository → Database (MySQL + Redis)`

**已有实现（可直接复用）**：

| 文件 | 说明 | 复用方式 |
|------|------|---------|
| `entity/Session.java` | Session 实体：6 字段（id/sessionId/userId/topic/status/createdAt），`@PrePersist` 自动设置 createdAt | direct_reuse |
| `enums/SessionStatus.java` | `ACTIVE('active')` / `COMPLETED('completed')` / `EXPIRED('expired')` + `getDbValue()` + `fromDbValue()` | direct_reuse |
| `repository/SessionRepository.java` | `findBySessionId(String)` + `findByUserIdOrderByCreatedAtDesc(String, Pageable)` | direct_reuse |
| `dto/common/ApiResponse.java` | `ApiResponse<T>` 统一响应包装（success/error 工厂方法） | direct_reuse |
| `dto/common/PageResponse.java` | `PageResponse<T>` 分页响应 + `fromPage()` 静态工厂 | direct_reuse |
| `exception/ResourceNotFoundException.java` | 资源不存在异常（404, `RESOURCE_NOT_FOUND`） | direct_reuse |
| `exception/BusinessException.java` | 业务异常基类（code/message/errorKey 三字段） | direct_reuse |
| `exception/AuthenticationException.java` | 认证异常（401, `AUTHENTICATION_FAILED`） | direct_reuse |
| `util/RedisKeyUtil.java` | `sessionStateKey(sessionId)` → `"session:state:"+sessionId` | direct_reuse |
| `config/RedisConfig.java` | `sessionState` 缓存空间 TTL=2h（含 ±10% 随机偏移）已配置 | direct_reuse |
| `config/SecurityConfig.java` | JWT 鉴权链 + 白名单（`/api/users/register`、`/api/users/login`、`/health`、`/actuator/**`、`/error`） | direct_reuse |
| `service/UserService.java` | `validateDataIsolation(userId)` + `getCurrentUserId()` 私有方法模式 | reference |
| `controller/UserController.java` | `@RestController` + `@RequestMapping` + `@Valid` + `ApiResponse.success()` 模式 | reference |
| `service/PaperService.java` | `DEFAULT_PAGE`/`DEFAULT_SIZE`/`MAX_SIZE` 分页边界处理 + `@Cacheable` 注解模式 | reference |

---

## 3. Relevant Modules（相关模块）

### SessionCreateRequest（新）

- 路径：`com.literatureassistant.dto.request.SessionCreateRequest`
- 职责：创建会话请求 DTO
- 关键字段：`topic`（`@NotBlank` + `@Size(max=500)`）

### SessionStatusUpdateRequest（新，占位）

- 路径：`com.literatureassistant.dto.request.SessionStatusUpdateRequest`
- 职责：状态更新请求 DTO（task17 仅占位，task18 完善）
- 关键字段：`status`（`SessionStatus` 枚举类型，task17 暂不加 `@NotNull`）

### SessionResponse（新）

- 路径：`com.literatureassistant.dto.response.SessionResponse`
- 职责：会话基础响应 DTO（用于列表/创建/更新）
- 关键字段（5 个）：
  - `sessionId` (`@JsonProperty("session_id")`)
  - `userId` (`@JsonProperty("user_id")`)
  - `topic`
  - `status`（`String` 类型，存储 `SessionStatus.getDbValue()` 小写值）
  - `createdAt` (`@JsonProperty("created_at")`)

### SessionService（新）

- 路径：`com.literatureassistant.service.SessionService`
- 职责：会话业务逻辑（5 个方法 + 数据隔离 + 缓存管理 + 临时状态转换）
- 关键方法：
  - `createSession(String userId, SessionCreateRequest request)` → `SessionResponse`
  - `listSessions(String userId, int page, int size)` → `PageResponse<SessionResponse>`（page 从 1 开始，size 默认 10、上限 100）
  - `getSessionDetail(String sessionId)` → `SessionResponse`（`@Cacheable("sessionState", key="#sessionId", unless="#result == null")`）
  - `updateStatus(String sessionId, SessionStatus newStatus)` → `void`（`@CacheEvict("sessionState", key="#sessionId")`）
  - `deleteSession(String sessionId)` → `void`（`@Transactional` + `@CacheEvict`）
- 私有方法：`validateDataIsolation(String resourceUserId)` + `getCurrentUserId()`

### SessionController（新）

- 路径：`com.literatureassistant.controller.SessionController`
- 职责：会话 REST API 入口（5 个端点）
- 关键端点：
  - `POST /api/sessions` → 创建会话（返回 201）
  - `GET /api/sessions?page=1&size=10` → 会话列表
  - `GET /api/sessions/{sessionId}` → 会话详情
  - `PUT /api/sessions/{sessionId}/status` → 状态更新
  - `DELETE /api/sessions/{sessionId}` → 删除会话

### SessionRepository（已有）

- 路径：`com.literatureassistant.repository.SessionRepository`
- 关键方法：`findBySessionId(String)` → `Optional<Session>`、`findByUserIdOrderByCreatedAtDesc(String, Pageable)` → `Page<Session>`

---

## 4. Files To Modify（待修改文件）

| 操作 | 路径 | 说明 |
|------|------|------|
| 新增 | `com/literatureassistant/dto/request/SessionCreateRequest.java` | 1 字段 DTO（topic），`@NotBlank` + `@Size(max=500)` |
| 新增 | `com/literatureassistant/dto/request/SessionStatusUpdateRequest.java` | 1 字段 DTO（status: SessionStatus），task17 占位 |
| 新增 | `com/literatureassistant/dto/response/SessionResponse.java` | 5 字段 DTO，`@JsonProperty` 输出 snake_case，status 字段为 String |
| 新增 | `com/literatureassistant/service/SessionService.java` | 5 个业务方法 + 私有数据隔离 + 缓存管理 |
| 新增 | `com/literatureassistant/controller/SessionController.java` | 5 个 REST 端点 |
| 新增（测试） | `src/test/java/com/literatureassistant/service/SessionServiceTest.java` | SessionService 单元测试（Mockito） |

---

## 5. Implementation Requirements（实现要求）

### 5.1 功能要求

| 编号 | 描述 | 优先级 | 验收条件 |
|------|------|--------|---------|
| FR-001 | `SessionCreateRequest` DTO：1 字段 topic，`@NotBlank` + `@Size(max=500)` | P0 | 空 topic 返回 400 |
| FR-002 | `SessionResponse` DTO：5 字段，`@JsonProperty` 输出 snake_case，status 字段为 String | P0 | JSON 字段名为 snake_case，status 值为小写 |
| FR-003 | `SessionService.createSession`：生成 `'ses_'+UUID前8位` sessionId，手动构建 SessionResponse | P0 | sessionId 以 'ses_' 开头，status='active' |
| FR-004 | `SessionService.listSessions`：分页 + `createdAt DESC`（复用 Repository 内置排序） | P0 | 按时间倒序，仅返回当前 userId |
| FR-005 | `SessionService.getSessionDetail`：`@Cacheable("sessionState", key="#sessionId")` + 数据隔离 | P0 | 缓存 2h，越权 403 |
| FR-006 | `SessionService.updateStatus`：基本更新 + `@CacheEvict`（完整状态机在 task18） | P0 | 更新后清空缓存 |
| FR-007 | `SessionService.deleteSession`：`@Transactional` + 硬删除 + `@CacheEvict` | P0 | 级联删除 analysis_results |
| FR-008 | 数据隔离私有方法 `validateDataIsolation` + `getCurrentUserId` | P0 | 越权 403 |
| FR-009 | `SessionController` 5 个端点：仅做参数接收 + Service 调用 + 响应包装 | P0 | 不含业务逻辑 |
| FR-010 | JWT 鉴权：5 个端点均需 JWT 认证 | P0 | 未携带 Token 返回 401 |

### 5.2 跨系统一致性

- 字段命名：Java camelCase ↔ Python/JSON snake_case
- 关键映射：`sessionId`↔`session_id`、`userId`↔`user_id`、`createdAt`↔`created_at`、`SessionStatus` 枚举 ↔ `active`/`completed`/`expired`（小写 dbValue）
- API 契约：5 个端点（POST/GET/GET-by-id/PUT-status/DELETE）的请求/响应格式
- 数据流转：Controller → Service → Repository → Entity → 手动构建 SessionResponse → ApiResponse 包装 → JSON

### 5.3 降级要求

- 本任务不涉及 LLM/Agent 调用，无降级要求

### 5.4 安全要求

- 5 个端点均需 JWT 认证
- 用户只能访问/修改/删除自己的会话（`validateDataIsolation` 私有方法，越权 403 + `errorKey=FORBIDDEN_ACCESS`）
- API 响应不包含敏感信息

---

## 6. Constraints（约束）

### 6.1 命名规范

- Java：类名 PascalCase、方法/变量 camelCase、常量 UPPER_SNAKE_CASE、文件 PascalCase.java
- JSON：字段名 `snake_case`
- 数据库：表名/列名 `snake_case`

### 6.2 分层规范

- `Controller → Service → Repository → Client`，禁止跨层
- Entity 与 DTO 分离，禁止直接返回 Entity
- DTO 命名：`XxxRequest` / `XxxResponse`

### 6.3 错误处理

- `BusinessException` + `GlobalExceptionHandler`（`@RestControllerAdvice`）
- 业务异常字段：`code`、`message`、`errorKey`

### 6.4 缓存策略

- Cache-Aside 模式：写 MySQL 后删 Redis 缓存（`@CacheEvict`）
- `sessionState` TTL = 2h（已配置，含 ±10% 随机偏移）
- 缓存 Key 使用 `RedisKeyUtil.sessionStateKey(sessionId)`

### 6.5 日志规范

- SLF4J + Logback
- 禁止在循环中打印 INFO 及以上级别日志
- 禁止在日志中输出敏感信息

### 6.6 数据库规范

- utf8mb4 + utf8mb4_unicode_ci、InnoDB
- JPA 参数化查询，禁止 SQL 拼接
- 所有列表接口强制分页

### 6.7 安全规范

- BCrypt 密码哈希（强度 10）
- JWT Token (24h) + Redis 黑名单
- 公开端点：`/api/users/register`、`/api/users/login`
- 数据隔离：`validateDataIsolation` 私有方法比对 currentUserId

---

## 7. Forbidden Actions（禁止行为）

- ❌ 输出伪代码或 TODO 注释
- ❌ 修改需求范围外的模块（`UserService` / `PaperService` / `AnalysisService` 等）
- ❌ 破坏三层分离架构（前端直接调 Python 等）
- ❌ 破坏分层调用规范（`SessionController` 直接操作 `SessionRepository`）
- ❌ Session Entity 直接返回给前端
- ❌ 硬编码敏感配置
- ❌ 违反跨系统字段命名约定（输出 Java 驼峰而非 snake_case）
- ❌ 在循环中打印 INFO 及以上级别日志
- ❌ 使用 SQL 拼接
- ❌ Controller 中编写业务逻辑（Entity→DTO 转换、UUID 生成、Repository 调用、缓存操作）
- ❌ **在 task17 中创建 `SessionMapper` 或 `SessionDetailResponse`**（属于 task18 范围）
- ❌ **在 `updateStatus` 中实现完整状态机规则**（属于 task18 范围）

---

## 8. Test Requirements（测试要求）

### 8.1 单元测试

| 测试类 | 验证点 |
|--------|--------|
| `SessionServiceTest` | 5 个核心方法（Mockito Mock SessionRepository + 模拟 SecurityContextHolder）：正常/异常/边界/越权/缓存命中 |

### 8.2 集成测试

- `SessionControllerTest`：完整 HTTP 链路（5 个端点 + 404/403/401 + snake_case 字段名 + status 小写值）

### 8.3 验证命令

```bash
cd Veritas/backend && mvn compile                                          # 编译
cd Veritas/backend && mvn test -Dtest=SessionServiceTest                  # 单元测试
cd Veritas/backend && mvn test                                             # 全部测试
```

---

## 9. Acceptance Criteria（验收标准）

- [ ] AC-001：`POST /api/sessions` 返回 201 + `ApiResponse<SessionResponse>`，sessionId 以 `ses_` 开头，status=`active`
- [ ] AC-002：`POST /api/sessions` 请求 body 缺 topic 字段返回 400（`@NotBlank` 校验）
- [ ] AC-003：`POST /api/sessions` 请求 body topic 超过 500 字符返回 400（`@Size` 校验）
- [ ] AC-004：`GET /api/sessions?page=1&size=10` 返回 `PageResponse<SessionResponse>`，按 `createdAt DESC` 排序，仅当前用户
- [ ] AC-005：`GET /api/sessions/{sessionId}` 返回 `SessionResponse`，sessionId 不存在返回 404
- [ ] AC-006：`GET /api/sessions/{sessionId}` 越权访问（用户A访问用户B的会话）返回 403（`errorKey=FORBIDDEN_ACCESS`）
- [ ] AC-007：`getSessionDetail` 第二次调用命中 Redis 缓存（`@Cacheable("sessionState", key="#sessionId")` TTL=2h）
- [ ] AC-008：`PUT /api/sessions/{sessionId}/status` 状态更新成功，Redis 缓存被清空（`@CacheEvict`）
- [ ] AC-009：`DELETE /api/sessions/{sessionId}` 硬删除 MySQL + 级联删除 `analysis_results` + 清空缓存
- [ ] AC-010：`SessionResponse` JSON 字段名使用 `snake_case`（`session_id`/`user_id`/`created_at`），status 字段值为小写 dbValue
- [ ] AC-011：5 个端点未携带 Token 均返回 401
- [ ] AC-012：Controller 不含业务逻辑（无 Entity→DTO 转换、无 Repository 调用、无 UUID 生成、无缓存操作）
- [ ] AC-013：`SessionServiceTest` 单元测试通过，`mvn compile` + `mvn test` 均成功
- [ ] AC-014：未创建 `SessionMapper`/`SessionDetailResponse`（属于 task18），未实现完整状态机规则（属于 task18）

---

## 10. 数据契约示例

### POST /api/sessions

**请求**：
```json
{ "topic": "Multi-Agent协同决策" }
```

**响应（201）**：
```json
{
  "code": 201,
  "message": "success",
  "data": {
    "session_id": "ses_a1b2c3d4",
    "user_id": "usr_xxxx",
    "topic": "Multi-Agent协同决策",
    "status": "active",
    "created_at": "2026-05-23T10:00:00"
  },
  "timestamp": 1716451200000
}
```

### GET /api/sessions?page=1&size=10

**响应（200）**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "session_id": "ses_a1b2c3d4",
        "user_id": "usr_xxxx",
        "topic": "Multi-Agent",
        "status": "active",
        "created_at": "2026-05-23T10:00:00"
      }
    ],
    "total": 5,
    "page": 1,
    "size": 10,
    "total_pages": 1
  },
  "timestamp": 1716451200000
}
```

### PUT /api/sessions/{sessionId}/status

**请求**：
```json
{ "status": "completed" }
```

**响应（200）**：
```json
{ "code": 200, "message": "success", "data": null, "timestamp": 1716451200000 }
```

---

## 11. 后续建议

- **下一步（task18）**：将实现完整会话状态机（`validateStatusTransition` / `markAsCompleted` / `markAsExpired` / `isTerminal`） + `SessionMapper` (MapStruct) + `SessionDetailResponse` + 完善 `SessionStatusUpdateRequest` 校验
- **后续 P1**：`GET /api/sessions/{sessionId}/analyses` 列出该会话下所有分析结果（JM5 缓存优化阶段）
- **JM6 优化**：会话超时清理（24h 未操作自动 EXPIRED），可考虑 `@Scheduled` 定时任务
- 字段命名小技巧：状态机转换时建议引入 `ALLOWED_TRANSITIONS` 常量 `Map<SessionStatus, Set<SessionStatus>>`，便于 task18 扩展

---

> **任务完成后必须**：
> 1. 运行 `mvn compile && mvn test` 验证编译和测试
> 2. 手动验证 5 个端点的 HTTP 响应（使用 curl 或 Postman）
> 3. 在 `json_prompt/Coding.md` 的 backend 序号映射表中追加新行（task17_session_controller_service_basic / v0.2 / M3:JM2 / F2.3.1-F2.3.5）
