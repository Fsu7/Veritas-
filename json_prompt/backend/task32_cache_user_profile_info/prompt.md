# Task 32: 用户画像缓存 + 用户信息缓存完善

> **课题编号**：XH-202630
> **版本**：v0.5
> **里程碑**：JM5 缓存优化与功能完善（Week 9 Day 1）
> **功能编号**：F2.6.1, F2.1.5, F2.1.6, F2.1.7
> **创建日期**：2026-06-17

---

## 1. Context

### 1.1 项目
XH-202630 科研文献智能助手 — 领域知识个性化生成与多智能体协同决策系统研究

### 1.2 当前版本
v0.5 / JM5：缓存优化与功能完善（Week 9 Day 1）

### 1.3 需求描述
完善用户画像缓存与用户信息缓存：
- 修复 `userProfileJson` 缓存名在 RedisConfig 未配置 TTL 的 Bug
- 完善 UserService 的 @Cacheable/@CacheEvict 注解
- 统一 Spring Cache 注解体系与 syncProfileToRedis 手动 Redis 操作
- 实现缓存穿透防护（空值缓存 TTL=60s）
- 验证缓存雪崩防护（TTL ±10% 随机偏移）
- 保障双重失效（userProfile + userProfileJson + userInfo 同步失效）

### 1.4 参考文档
- `docs/backend/Java后端模块系统架构文档.md` — 第9章 缓存管理模块（F2.6）
- `docs/backend/Java后端模块项目里程碑文档.md` — 第7章 JM5 Day 1 任务分解
- `AGENTS.md` — 关键规则第6条 Cache-Aside 写后删
- `docs/架构决策记录(ADR).md` — ADR-007 缓存策略决策

---

## 2. Current Architecture

### 2.1 涉及层级
- java_backend
- data_layer（Redis）

### 2.2 相关模块
| 模块路径 | 职责 |
|---------|------|
| `com.literatureassistant.config.RedisConfig` | Redis缓存配置，管理6个缓存空间TTL |
| `com.literatureassistant.service.UserService` | 用户管理业务，已实现缓存注解但有Bug |
| `com.literatureassistant.util.RedisKeyUtil` | Redis Key生成工具 |

### 2.3 已有实现
| 文件 | 描述 | 复用方式 |
|------|------|---------|
| `config/RedisConfig.java` | 已配置6个缓存空间TTL，默认30min，±10%随机偏移；**缺失userProfileJson配置** | 扩展 |
| `service/UserService.java` | 已实现@Cacheable/@CacheEvict，但userProfileJson引用未配置缓存名 | 扩展 |
| `util/RedisKeyUtil.java` | 已实现userProfileKey等方法 | 直接复用 |
| `exception/BusinessException.java` | 异常体系（code+message+errorKey） | 直接复用 |

---

## 3. Relevant Modules

### 3.1 RedisConfig
- **路径**：`Veritas/backend/src/main/java/com/literatureassistant/config/RedisConfig.java`
- **职责**：Redis缓存配置，管理缓存空间TTL、序列化、连接池
- **关键接口**：
  - `@Bean RedisCacheManager cacheManager(RedisConnectionFactory factory)` — 缓存管理器
  - `@Bean RedisTemplate<String, String> redisTemplate(RedisConnectionFactory factory)` — RedisTemplate Bean

### 3.2 UserService
- **路径**：`Veritas/backend/src/main/java/com/literatureassistant/service/UserService.java`
- **职责**：用户管理业务，注册/登录/画像CRUD，缓存管理
- **关键接口**：
  - `@Cacheable(value="userInfo", key="#userId") UserResponse getUserInfo(String userId)`
  - `@Cacheable(value="userProfile", key="#userId", unless="#result == null") ProfileResponse getProfile(String userId)`
  - `@CacheEvict(value={"userProfile","userProfileJson","userInfo"}, key="#userId") ProfileResponse createProfile(...)`
  - `private void syncProfileToRedis(String userId, UserProfile profile)` — 手动写Redis供Python使用

### 3.3 RedisKeyUtil
- **路径**：`Veritas/backend/src/main/java/com/literatureassistant/util/RedisKeyUtil.java`
- **职责**：Redis Key统一生成工具
- **关键接口**：
  - `public static String userProfileKey(String userId)` — 生成 `user:profile:{userId}`

---

## 4. Files To Modify

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 修改 | `config/RedisConfig.java` | 补齐 userProfileJson 缓存空间TTL配置（1h） |
| 修改 | `service/UserService.java` | 完善缓存注解：空值防护、unless条件、注释说明 |
| 修改 | `util/RedisKeyUtil.java` | 新增 userProfileJsonKey(userId) 方法 |
| 新增 | `test/.../UserServiceCacheTest.java` | 缓存命中率、失效、穿透、雪崩测试 |

---

## 5. Implementation Requirements

### 5.1 功能要求

| ID | 描述 | 优先级 | 验收条件 |
|----|------|--------|---------|
| FR-001 | 修复 RedisConfig 中 userProfileJson 缓存名未配置TTL的Bug，新增TTL=1h | P0 | cacheConfigurations 包含 userProfileJson，TTL=Duration.ofHours(1) |
| FR-002 | 完善 UserService.getProfile 缓存穿透防护，画像不存在时缓存空值（TTL=60s） | P1 | 60秒内重复查询不命中数据库 |
| FR-003 | 完善 UserService.getUserInfo 缓存穿透防护 | P1 | 用户不存在时缓存策略正确 |
| FR-004 | 统一 syncProfileToRedis 与 Spring Cache 注解体系的Key命名（注释说明或统一） | P2 | 两套Key命名策略清晰说明 |
| FR-005 | 验证缓存雪崩防护（TTL ±10%随机偏移） | P1 | userProfile TTL在54min~66min范围 |
| FR-006 | 保障双重失效：createProfile/updateProfile 三重失效 | P0 | 三个缓存Key均被删除 |
| FR-007 | RedisKeyUtil 新增 userProfileJsonKey(userId) 方法 | P2 | 返回 user:profile:json:{userId} |

### 5.2 跨系统一致性
- **字段命名**：Java camelCase ↔ Python/JSON snake_case
- **关键字段映射**：userId↔user_id, educationLevel↔education_level, knowledgeLevel↔knowledge_level, preferredStyle↔preferred_style, researchField↔research_field
- **数据流转**：前端 → Java UserService（@Cacheable）→ MySQL；同时 syncProfileToRedis 写入 Redis 供 Python AI 服务读取

### 5.3 安全要求
- **数据隔离**：缓存Key必须包含userId，@Cacheable key="#userId" 已实现
- **敏感信息**：缓存中不得存储 passwordHash；UserResponse DTO 不包含该字段

---

## 6. Constraints

### 6.1 命名规范
- Java: 类名PascalCase, 方法/变量camelCase, 常量UPPER_SNAKE_CASE, 文件PascalCase.java
- 数据库: 表名snake_case复数, 列名snake_case
- JSON: 字段名snake_case

### 6.2 分层规范
- Controller → Service → Repository → Client，禁止跨层
- Entity与DTO分离，禁止直接返回Entity

### 6.3 错误处理
- BusinessException + GlobalExceptionHandler(@RestControllerAdvice)
- BusinessException包含 code、message、errorKey 三个字段

### 6.4 缓存策略
- **模式**：Cache-Aside，写MySQL后删Redis缓存
- **TTL分层**：
  - userProfile: 1h (54min~66min with ±10% jitter)
  - userProfileJson: 1h (54min~66min with ±10% jitter)
  - userInfo: 1h (54min~66min with ±10% jitter)
- **穿透防护**：查询结果为空时缓存空值（TTL=60s）
- **雪崩防护**：TTL添加±10%随机偏移
- **大小限制**：单个缓存值不超过1MB

### 6.5 日志规范
- SLF4J + Logback
- 禁止在循环中打印INFO及以上级别日志
- 禁止在日志中输出敏感信息

### 6.6 数据库规范
- utf8mb4 + utf8mb4_unicode_ci, InnoDB
- 主键 id BIGINT AUTO_INCREMENT
- 业务ID xxx_id VARCHAR(100) UNIQUE NOT NULL
- 禁止SELECT *，明确列出查询字段

### 6.7 安全规范
- BCrypt哈希（强度10）+ JWT Token (24h) + Redis黑名单
- JPA参数化查询，禁止SQL拼接
- 数据隔离：WHERE user_id = currentUserId

---

## 7. Forbidden Actions

| ID | 禁止行为 | 原因 | 严重程度 |
|----|---------|------|---------|
| FA-001 | 输出伪代码或TODO注释 | 必须输出完整可执行代码 | critical |
| FA-002 | 修改需求范围外的模块（PaperService/SessionService/AnalysisService） | 本任务仅涉及UserService/RedisConfig/RedisKeyUtil | high |
| FA-003 | 破坏三层分离架构 | 架构约束ADR-001 | critical |
| FA-004 | 破坏分层调用规范 | 分层架构约束 | critical |
| FA-005 | Entity直接返回给前端 | 数据隔离与接口稳定性 | high |
| FA-006 | 硬编码敏感配置 | 安全约束 | critical |
| FA-007 | 违反跨系统字段命名约定 | 跨系统一致性约束 | high |
| FA-008 | 在循环中打印INFO及以上级别日志 | 性能约束 | medium |
| FA-009 | 使用SQL拼接 | SQL注入防护 | critical |
| FA-010 | 忽略降级场景（缓存失效时需回源数据库） | 可用性约束 | high |

---

## 8. Test Requirements

### 8.1 单元测试

| 测试名称 | 描述 | 覆盖场景 |
|---------|------|---------|
| `UserServiceCacheTest.getProfile_cacheHit_returnsCached` | 验证缓存命中 | normal_flow |
| `UserServiceCacheTest.createProfile_tripleInvalidation` | 验证createProfile三重失效 | normal_flow |
| `UserServiceCacheTest.updateProfile_tripleInvalidation` | 验证updateProfile三重失效 | normal_flow |
| `UserServiceCacheTest.getProfile_notFound_cachesNullForPenetration` | 验证缓存穿透防护 | boundary_condition |
| `RedisConfigTest.userProfileJson_ttlConfigured` | 验证userProfileJson TTL=1h | normal_flow |
| `RedisConfigTest.userProfile_ttlJitterApplied` | 验证TTL ±10%随机偏移 | boundary_condition |
| `RedisKeyUtilTest.userProfileJsonKey_format` | 验证Key格式 | normal_flow |

### 8.2 验证命令
```bash
cd Veritas/backend && mvn test -Dtest=UserServiceCacheTest
cd Veritas/backend && mvn test -Dtest=RedisConfigTest
cd Veritas/backend && mvn compile
```

---

## 9. Acceptance Criteria

- [ ] AC-001: RedisConfig中userProfileJson缓存空间TTL已配置为1小时
- [ ] AC-002: UserService.getProfile缓存命中时直接返回缓存数据
- [ ] AC-003: createProfile/updateProfile触发三重失效
- [ ] AC-004: 画像不存在时缓存穿透防护生效（空值缓存TTL=60s）
- [ ] AC-005: userProfile/userInfo缓存TTL在54min~66min范围内
- [ ] AC-006: RedisKeyUtil.userProfileJsonKey(userId)返回正确格式
- [ ] AC-007: 缓存Key包含userId，确保数据隔离
- [ ] AC-008: 缓存值不含passwordHash等敏感信息
- [ ] AC-009: syncProfileToRedis与Spring Cache关系在注释中说明
- [ ] AC-010: mvn test 全部通过，0失败0错误
- [ ] AC-011: 未修改UserService以外的Service类
