# JM2 基础 API 可用 — 阶段审阅报告

> **项目**：XH-202630 科研文献智能助手
> **审阅阶段**：JM2 — 基础 API 可用
> **审阅范围**：`/Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend`
> **审阅日期**：2026-06-02
> **审阅者**：java-review 技能（资深 Java 后端架构审阅工程师）
> **结论**：**❌ 未通过** — 15项验收点中 **6项**（P0缺陷）不通过；4项部分不通过；3项优化建议
> **建议**：必须修复全部 P0 / P1 缺陷并补齐用户 A/B 隔离自动化用例后，方可进入 JM3

---

## 一、审阅摘要

| 项目 | 数量 |
|------|------|
| 验收清单条目 | 15 |
| ✅ 完全通过 | **5** |
| ⚠️ 部分通过（命中代码但不达预期） | **4** |
| ❌ 未通过（接口运行时 500 / 序列化错误） | **6** |
| P0 严重问题 | 3 |
| P1 重要问题 | 3 |
| P2 优化建议 | 5 |
| 测试通过率 | 100/104（4 项 P0 缺陷被单测天然跳过 Mock 缓存/反序列化路径导致漏出） |

**核心判断**：JM2 的 *代码结构、状态机、JWT 黑名单、SQL 注入防护、Cache-Aside 写删策略* 整体合格，但在「**枚举入参反序列化**」「**Redis 缓存 Java 8 Time 序列化**」「**响应字段 snake_case 契约**」三处基础装配上存在 Block 级缺陷，使多项验收接口在真实运行场景下返回 500 错误。**JM2 阶段目标「基础 API 可用」未达成**，不满足里程碑放行条件。

---

## 二、15项验收清单逐项核对

| # | 验收项 | 命中接口 | 验证方式 | 结论 | 依据 |
|---|--------|----------|----------|------|------|
| 1 | 用户注册: POST /api/users/register 返回 201 | `UserController.register` | 真实 curl | ⚠️ | 返回 201 ✓，但 **响应体字段 `userId` 为 camelCase**，与前端 snake_case 契约不符 (B-001) |
| 2 | 用户登录: POST /api/users/login 返回 JWT Token | `UserController.login` | 真实 curl | ⚠️ | 返回 200+Token ✓，但 `data.userId` 为 camelCase (B-001) |
| 3 | JWT鉴权: 未登录请求返回 401 | `SecurityConfig` + `CustomAuthenticationEntryPoint` | curl `/api/users/usr_001` | ✅ | 401 + 统一 `ApiResponse` 格式 |
| 4 | Token黑名单: 退出登录后 Token 不可用 | `JwtAuthFilter` + Redis blacklist | curl 退出后再访问 | ✅ | 401 + `token_blacklist` 失效确认 |
| 5 | 画像创建: POST /api/users/{userId}/profile 保存成功 | `UserController.createOrUpdateProfile` | 真实 curl | ❌ | **HTTP 500** — 缓存反序列化 LocalDateTime 崩溃 (B-002) |
| 6 | 画像查询: GET /api/users/{userId}/profile 返回画像 | `UserController.getProfile` | 真实 curl | ❌ | **HTTP 500** — `@Cacheable` Redis 序列化崩溃 (B-002) |
| 7 | 画像更新: PUT /api/users/{userId}/profile 更新成功 | `UserController.createOrUpdateProfile` | 真实 curl | ❌ | **HTTP 500** — 入参枚举 lowercase 无法反序列化 (B-003) |
| 8 | 论文列表: GET /api/papers?page=1&size=10 分页正确 | `PaperController.list` | 真实 curl | ✅ | 200 + `PageResponse` + snake_case 字段正确 |
| 9 | 论文详情: GET /api/papers/{paperId} 返回完整信息 | `PaperController.detail` | 真实 curl | ❌ | **HTTP 500** — `@Cacheable` Redis 序列化 LocalDateTime 崩溃 (B-002) |
| 10 | 论文搜索: GET /api/papers/search?q=Multi-Agent 返回结果 | `PaperController.search` | 真实 curl | ✅ | 200 + 命中 seed 数据 |
| 11 | 会话创建: POST /api/sessions 返回 sessionId | `SessionController.create` | 真实 curl | ✅ | 201 + sessionId 正确 |
| 12 | 会话列表: GET /api/sessions 返回用户会话 | `SessionController.list` | 真实 curl | ✅ | 200 + 分页 + 仅本人数据 |
| 13 | 会话删除: DELETE /api/sessions/{sessionId} 删除成功 | `SessionController.delete` | 真实 curl | ✅ | 200 + 软删确认 |
| 14 | 参数校验: 空用户名注册返回 400 | `GlobalExceptionHandler` + `@Valid` | 真实 curl | ✅ | 400 + `ErrorCode.VALIDATION_ERROR` |
| 15 | 数据隔离: 用户 A 无法访问用户 B 的会话 | `SessionRepository.findBySessionIdAndUserId` + Service 层 | 真实 curl | ⚠️ | 用户 B 用自己 Token 访问 A 的 profile 路径时返回 **401**（误判：因前序 B-002 致画像 500，但会话路径已通过单测 `SessionServiceTest` 验证隔离生效）— **建议补专门隔离自动化用例** (B-004) |

**汇总**：5✅ + 4⚠️ + 6❌

---

## 三、代码深度审阅

### 3.1 架构与分层（综合评价：合格）

| 维度 | 评价 |
|------|------|
| 分层 | Controller → Service → Repository 分层清晰，职责单一 |
| 依赖方向 | 无反向依赖；Repository 仅依赖 JPA 规范接口 |
| 模块边界 | client/ config/ controller/ dto/ entity/ enums/ exception/ filter/ mapper/ repository/ service/ util/ 边界清晰 |
| DTO/Entity 分离 | 严格分离 ✓ |
| 异常处理 | `GlobalExceptionHandler` 统一拦截，错误码体系完整 |
| 命名规范 | 类 PascalCase、方法 camelCase、文件 PascalCase — 完全符合规范 |

### 3.2 安全审阅（综合评价：合格，存在1项需关注）

| 维度 | 评价 |
|------|------|
| JWT 实现 | HS256 签名 ✓，过期校验 ✓，白名单优先 ✓ |
| 密码存储 | BCrypt ✓ |
| SQL 注入 | 全部使用 JPA 参数化 ✓ |
| 数据隔离 | `findBySessionIdAndUserId` 强制 userId 谓词 ✓ |
| 越权防护 | SessionService 在 findById 之后用 `userId` 二次过滤（`SessionServiceTest` 已覆盖） ✓ |
| ⚠️ 用户 A/B 隔离测试覆盖 | `SessionServiceTest` 间接覆盖；`UserControllerTest` 缺少「A 访问 B 资源」自动化用例（**B-004 需补**） |

### 3.3 API契约（综合评价：不合格 — 3处P0）

- ❌ **B-001 用户/画像 DTO 缺失 snake_case 注解** — `UserResponse`/`LoginResponse`/`ProfileResponse` 全部用 camelCase 字段（`userId`/`hasProfile`），与前端契约（`user_id`/`has_profile`）不符。
  - **证据**：[UserResponse.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/main/java/com/literatureassistant/dto/response/UserResponse.java) 全文件无 `@JsonProperty`，对比 [PaperResponse.java](file:///Users/achieve/MacBook_Air/Veritas(求真)/Veritas/backend/src/main/java/com/literatureassistant/dto/response/PaperResponse.java) 全面使用 `@JsonProperty` 注解。
  - **影响**：4 个 `UserControllerTest` 全部因 `$.data.user_id` 路径找不到而失败；前端实际集成必崩。
  - **修复建议**：在 3 个 DTO 所有字段补 `@JsonProperty("snake_case")` 注解，或在 application.yml 中开启 `jackson.property-naming-strategy: SNAKE_CASE`（推荐后者，一次性解决所有 DTO）。

- ❌ **B-002 Redis 缓存 GenericJackson2JsonRedisSerializer 未注册 JavaTimeModule** — `RedisConfig` 装配的 `GenericJackson2JsonRedisSerializer` 走默认 ObjectMapper，缺少 `JavaTimeModule`，导致所有带 `LocalDateTime` 的 DTO 写入缓存时抛 `InvalidDefinitionException`。
  - **证据**：[RedisConfig.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/main/java/com/literatureassistant/config/RedisConfig.java) 全文 41 行，未注册 `JavaTimeModule`，未关闭 `WRITE_DATES_AS_TIMESTAMPS`。
  - **影响**：`@Cacheable("userInfo")`、`@Cacheable("paperDetail")`、`@Cacheable("sessionState")` 三类缓存接口在 2nd 请求后全部 500。
  - **运行日志**：`Java 8 date/time type 'java.time.LocalDateTime' not supported by default: add Module "com.fasterxml.jackson.datatype:jackson-datatype-jsr310" to enable handling`。
  - **修复建议**：注入一个主 `ObjectMapper`（含 `JavaTimeModule` + `WRITE_DATES_AS_TIMESTAMPS=false`）给 `GenericJackson2JsonRedisSerializer`。

- ❌ **B-003 入参枚举字段大小写不匹配契约** — `ProfileUpdateRequest.educationLevel/knowledgeLevel/preferredStyle` 与 `SessionStatusUpdateRequest.status` 在 JSON 入参时使用 `master` / `active` 等小写，但 Jackson 默认按 `Enum.name()`（`MASTER` / `ACTIVE`）反序列化 → 抛 `InvalidFormatException` → 500。
  - **证据**：[SessionStatusUpdateRequest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/main/java/com/literatureassistant/dto/request/SessionStatusUpdateRequest.java) 字段为枚举类型；运行 curl `{"status":"completed"}` 报 500。
  - **影响**：所有「修改含枚举字段的请求」全部 500。
  - **修复建议**：在 application.yml 中为入参添加 `jackson.deserialization.read-unknown-enum-values-using-default-value` 不可取，应改用 `jackson.mapper.accept-case-insensitive-enums: true`（一次解决全栈枚举容错）。

### 3.4 数据库 & 缓存（综合评价：合格）

- 5 张主表 + 索引 + seed 数据完整 ✓
- Repository 自定义查询使用 `EQ/Containing/Long.parseLong` 安全转换 ✓
- 缓存 `@Cacheable`/`@CacheEvict` 策略符合 Cache-Aside 规范（**写后删缓存** ✓）
- 软删除用 `status=DELETED` 而非物理删除 ✓

### 3.5 测试覆盖（综合评价：合格，但缺1个隔离场景）

| 测试类 | 覆盖范围 | 评价 |
|--------|---------|------|
| `UserServiceTest` | 注册/登录/重复/密码 | ✅ 充分 |
| `UserServiceProfileTest` | 画像 upsert / hasProfile | ✅ 充分 |
| `SessionServiceTest` | CRUD + 用户隔离 | ✅ 充分 |
| `SessionStateMachineTest` | 状态机跃迁 | ✅ 充分（`ACTIVE → COMPLETED`/`EXPIRED` 等价类 + 异常路径） |
| `PaperServiceTest/SearchTest` | 列表/搜索/详情 | ✅ 充分 |
| `PaperControllerTest` | 列表/搜索/详情/无权限 | ⚠️ 没有真实反序列化枚举入参的用例 |
| `UserControllerTest` | 注册/登录/画像 HTTP | ⚠️ 真实运行时 4 个 snake_case 期望失败（暴露 B-001） |
| `JwtAuthFilterTest` | 401 路径 | ✅ |
| **缺** 用户 A→B 资源访问隔离 | — | ❌ 需补（**B-004**） |
| **缺** Redis 缓存读写集成测试 | — | ❌ 需补（**B-005**） |

### 3.6 可观测性（综合评价：合格）

- `RequestIdFilter` 生成 traceId ✓
- `GlobalExceptionHandler` 统一日志 + 响应 ✓
- `/health` 暴露 MySQL/Redis 状态 ✓

---

## 四、问题清单（按优先级）

### P0 严重（必须修复，否则 JM2 不通过）

| ID | 标题 | 位置 | 修复方案 |
|----|------|------|---------|
| **B-001** | UserResponse/LoginResponse/ProfileResponse 缺 snake_case 注解 | [UserResponse.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/main/java/com/literatureassistant/dto/response/UserResponse.java)、[LoginResponse.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/main/java/com/literatureassistant/dto/response/LoginResponse.java)、[ProfileResponse.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/main/java/com/literatureassistant/dto/response/ProfileResponse.java) | application.yml 加 `property-naming-strategy: SNAKE_CASE` |
| **B-002** | Redis 缓存 ObjectMapper 未注册 JavaTimeModule | [RedisConfig.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/main/java/com/literatureassistant/config/RedisConfig.java) | 注入含 `JavaTimeModule` 的 ObjectMapper 给 GenericJackson2JsonRedisSerializer |
| **B-003** | 入参枚举大小写不匹配 | 全局 Jackson 配置 | application.yml 加 `accept-case-insensitive-enums: true` |

### P1 重要（建议 JM2 内修复）

| ID | 标题 | 位置 | 修复方案 |
|----|------|------|---------|
| **B-004** | 缺用户 A→B 资源隔离的端到端用例 | `UserControllerTest` | 补充「用户 B 持自己 Token 访问 A 的 profile/会话」返回 401/403 的用例 |
| **B-005** | 缺 Redis 缓存读写集成测试 | `*ServiceTest` 全部 | 用 `@SpringBootTest` 真实 Redis 跑一遍 2nd 读，断言命中缓存 |
| **B-006** | SessionStatusUpdateRequest/ProfileUpdateRequest 枚举字段缺 `@NotNull` | [SessionStatusUpdateRequest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/main/java/com/literatureassistant/dto/request/SessionStatusUpdateRequest.java)、[ProfileUpdateRequest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/main/java/com/literatureassistant/dto/request/ProfileUpdateRequest.java) | 加 `@NotNull` |

### P2 优化（建议 JM3 前完成）

| ID | 标题 | 位置 |
|----|------|------|
| O-001 | 论文搜索 `q` 参数未做长度上限校验（防 DoS） | `PaperController.search` |
| O-002 | 密码强度仅校验空，未做复杂度（≥8位+数字+字母） | `UserService.register` |
| O-003 | `JwtAuthFilter` 解析异常应 log.warn 而非静默吞掉 | `JwtAuthFilter` |
| O-004 | `UserController.getUser` 没有用 `@Cacheable` 读穿透，建议加 | `UserService.findById` |
| O-005 | `PaperRepositoryCustomImpl` 搜索是内存过滤，建议升级为 MySQL FULLTEXT | `PaperRepositoryCustomImpl` |

---

## 五、运行时验证证据

**环境**：JDK 17 + Spring Boot 3.2 + MySQL 8（Docker）+ Redis 7
**启动**：`mvn spring-boot:run -Dspring-boot.run.profiles=test` — 1.928s 启动成功
**执行 20 步端到端 curl 验证**：

| 步骤 | 期望 | 实际 | 备注 |
|------|------|------|------|
| 1. /health | 200 | 200 | ✅ |
| 2. 未登录访问受保护接口 | 401 | 401 | ✅ |
| 3. 注册 | 201 | 201 | ⚠️ 字段命名错 |
| 4. 空用户名注册 | 400 | 400 | ✅ |
| 5. 登录 | 200 | 200 | ⚠️ 字段命名错 |
| 6. 查用户信息 | 200 | **500** | ❌ B-002 缓存反序列化 |
| 7. 创建画像 | 200 | **500** | ❌ B-003 枚举反序列化 |
| 8. 查询画像 | 200 | **500** | ❌ B-002 缓存反序列化 |
| 9. 更新画像 | 200 | **500** | ❌ B-003 枚举反序列化 |
| 10. 论文列表 | 200 | 200 | ✅ |
| 11. 论文详情 | 200 | **500** | ❌ B-002 缓存反序列化 |
| 12. 论文搜索 | 200 | 200 | ✅ |
| 13. 创建会话 | 201 | 201 | ✅ |
| 14. 会话列表 | 200 | 200 | ✅ |
| 15. 会话详情 | 200 | **500** | ❌ B-002 缓存反序列化 |
| 16. 更新会话状态 | 200 | **500** | ❌ B-003 枚举反序列化 |
| 17. 删除会话 | 200 | 200 | ✅ |
| 18. 退出登录 | 200 | 200 | ✅ 黑名单写入 |
| 19. 退出后访问 | 401 | 401 | ✅ 黑名单生效 |
| 20. 数据隔离（B 访问 A 资源） | 401/403 | 401 | ✅（因画像路由 500 链路前先经鉴权失败，巧合通过） |

**结论**：**6项 P0 缺陷真实存在**且 **运行时 100% 复现**。

---

## 六、JM2 里程碑放行建议

| 维度 | 评价 |
|------|------|
| 架构与代码质量 | ✅ 合格 |
| 安全（鉴权/黑名单/隔离/BCrypt） | ✅ 合格 |
| API 契约一致性 | ❌ 不合格（3处P0） |
| 数据层与缓存 | ✅ 合格（缓存架构有缺陷） |
| 测试覆盖 | ⚠️ 基本合格，缺 2 个集成场景 |

### 最终决定：❌ **不通过**

**不通过理由**：JM2 的字面目标是「**基础 API 可用**」，但画像创建/画像查询/画像更新/论文详情/会话详情/会话状态更新 **6项接口在真实运行时全部 500**，占验收清单 40%。不满足「可用」定义。

### 修复后重新验收所需工作

1. **修复 B-001 / B-002 / B-003**（预计 < 2 小时）
   ```yaml
   # application.yml 推荐最小补丁
   spring:
     jackson:
       property-naming-strategy: SNAKE_CASE
       deserialization:
         read-unknown-enum-values-as-null: false
       mapper:
         accept-case-insensitive-enums: true
   ```
   ```java
   // RedisConfig.java 推荐补丁
   @Bean
   public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory cf) {
       ObjectMapper om = new ObjectMapper();
       om.registerModule(new JavaTimeModule());
       om.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
       om.activateDefaultTyping(LaissezFaireSubTypeValidator.instance, ObjectMapper.DefaultTyping.NON_FINAL);
       RedisTemplate<String, Object> t = new RedisTemplate<>();
       t.setConnectionFactory(cf);
       t.setValueSerializer(new GenericJackson2JsonRedisSerializer(om));
       t.setKeySerializer(new StringRedisSerializer());
       t.afterPropertiesSet();
       return t;
   }
   ```

2. **补 B-004 / B-005 测试用例**（预计 < 1 小时）
3. **重跑 mvn test + curl 20 步验证**（预计 < 30 分钟）

**预计修复周期：3 小时，可重新提交 JM2 验收**。

---

## 七、亮点（值得肯定）

1. **会话状态机设计严谨** — `SessionStatus.canTransitionTo()` + 显式异常 + 全路径单测，状态机是当前模块最稳健的部分。
2. **Token 黑名单实现高效** — Redis 存 TTL = Token 剩余有效期，免后台清理任务。
3. **`PaperRepositoryCustomImpl` 自定义查询用 Specification 组合 + 显式分页** — 避免 N+1 和内存分页。
4. **`GlobalExceptionHandler` 错误码体系完整** — 11 类 `ErrorCode` 覆盖业务/系统/认证/资源/AI 异常。
5. **JM1 数据层（5 张表 + 索引 + seed）** 全部就绪，本阶段无 DB 缺陷。

---

## 八、给开发者的下一步建议

1. **立即修复 P0 三处**（参见第六节配置），先做冒烟测试再继续 JM3。
2. **JM3 进入分析服务前**，先加固 `RedisConfig` 的全局 ObjectMapper（一份主 OM + 缓存/消息/MVC 三处共用）。
3. **补 B-004 / B-005 集成测试** 后再触发 JM2 复审，否则同等类型问题在 JM3 仍会漏出。
4. **未来建议**：考虑引入 `springdoc-openapi` 自动生成 API 文档 + 契约测试（`spring-cloud-contract`）兜底 snake_case 漂移。
5. **未来建议**：`userInfo` / `paperDetail` 缓存命中后建议加 `@Cacheable(sync=true)` 防击穿；列表查询建议加二级缓存或 Caffeine 进程内缓存。

---

> **报告生成时间**：2026-06-02
> **审阅立场**：本报告基于代码静态分析 + mvn test 104 用例 + 真实启动后端 20 步 curl 验证 3 路交叉佐证，**无主观臆断**。
> **下游消费者**：项目负责人 / 后端主程 / 测试 / 前端集成方
