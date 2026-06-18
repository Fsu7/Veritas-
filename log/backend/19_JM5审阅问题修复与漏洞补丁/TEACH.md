# 技术教学文档 — JM5 审阅问题修复与漏洞补丁

## 开发思路

### 需求分析过程

**输入**：资深 Java 后端架构审阅工程师产出的 [JM5 缓存优化与功能完善审阅报告](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/log/阶段审阅报告/backend/JM5-缓存优化与功能完善-审阅报告.md)，识别出 4 个 P0 数据隔离漏洞 + 3 个 P1/P2 重要问题 + 6 个 P2/P3 建议项。

**核心问题识别**：
- 4 个 P0 漏洞的本质相同：`@Cacheable` 命中时方法体不执行，导致 Service 内部 `validateDataIsolation` 被绕过
- B-002 是缓存 Key 设计不完整（漏掉分页参数）
- S-003 是 JSON 注入风险（CONCAT 拼接 JSON 字符串）
- U-002/U-003/U-005 是缓存策略细节优化

**修复优先级**：
1. P0 全部修复（数据隔离漏洞 + 缓存 Key 完整性）
2. P1 全部修复（JSON 注入 + allEntries 注释）
3. P2 全部修复（异常类型 + try-finally + sync=true）
4. P3 不修复（降级容错可接受 + 死代码自然清理）

### 技术选型考虑

**数据隔离校验位置选择**：

| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| A. Controller 层校验 | 每次请求必执行，不受缓存影响 | Controller 层冗余 | ✅ 推荐 |
| B. Service 层校验 + AOP 拦截 | 业务内聚 | AOP 实现复杂，性能开销 | ❌ |
| C. 缓存 Key 含 userId | 天然隔离 | 同一资源被缓存多份，浪费空间 | ❌ |
| D. 自定义 RedisCacheManager | 精细控制 | 复杂度高 | ❌ |

**最终方案 A**：在 Controller 层添加 `validateXxxAccess` 私有方法（path variable 是 userId）或调用 Service 的 `validateXxxAccess` 公开方法（path variable 是资源 ID）。Service 层的 `@Cacheable` 方法信任入参，不做二次校验。

**FavoriteService allEntries 决策**：

`listFavorites` 的 Key 改为 `RedisKeyUtil.favoriteListKey(#userId, #page, #size)` 后，`addFavorite`/`removeFavorite` 无法用 `@CacheEvict(key="#userId")` 精准失效（Key 包含分页参数，存在多种组合）。决策：
- 选项 1：保留 `allEntries=true`，清空整个 `favoriteList` 缓存空间
- 选项 2：改用 `RedisTemplate.scan` 按 `user:favorites:{userId}:*` 前缀精准失效
- 选项 3：取消缓存，每次查询都查 DB

**最终选择选项 1**，理由：`favoriteList` TTL=10min 较短，收藏操作频率低，清空整个空间影响可控。

### 架构设计思路

**Controller-Service 分层校验原则**：

```
┌─────────────────────────────────────────────┐
│ Controller（每次请求必执行）                 │
│   ├─ JWT 认证                                │
│   ├─ 数据隔离校验（path 资源归属）            │
│   └─ Service 调用（信任入参）                 │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│ Service @Cacheable（缓存命中不执行）         │
│   ├─ Repository 调用                          │
│   └─ 返回 DTO                                │
└─────────────────────────────────────────────┘
```

**规则**：
- `@Cacheable` 方法体内**严禁**做任何安全/权限校验
- 安全/权限校验**必须**在 Controller 层执行
- 校验方式分两类：
  - path variable 是 userId：Controller 直接比较
  - path variable 是资源 ID：Controller 调用 Service 的 `validateXxxAccess` 公开方法查 DB 校验

### 遇到的问题及解决方案

**问题 1：校验上移后测试 Mock 不匹配**

- 现象：移除 Service 内部 `validateDataIsolation` 后，原有测试中 `when(userService.getProfile("usr_test1234")).thenThrow(...)` 之类的 Mock 不会被调用（UnnecessaryStubbing）
- 解决：删除 Service 层测试中的越权/认证场景（已不再适用），改为在 Controller 测试中设置 SecurityContext + 让 Controller 直接抛 403

**问题 2：Mockito void 方法 mock 语法**

- 现象：`when(analysisService.validateAnalysisAccess(...)).thenThrow(...)` 编译错误（void 方法不能用 `when().thenThrow()`）
- 解决：改用 `doThrow(...).when(analysisService).validateAnalysisAccess(...)` 语法

**问题 3：JM5-9 测试中调用链未触发**

- 现象：`verify(analysisService).validateAnalysisAccess("uB", "anl_A")` 失败，因为 Controller 抛 403 后没继续调用
- 解决：先确认 `doThrow` 配置正确，然后验证调用次数 + 验证 `getAnalysisResult` 未被调用（短路返回）

**问题 4：ExportService 数据隔离漏洞（B-003 延伸）**

- 现象：`ExportService.getValidatedResult` 调用 `@Cacheable` 方法 `getAnalysisResult`，缓存命中时校验被绕过，用户 B 可导出用户 A 的报告
- 发现时机：本轮修复过程中审计所有调用 `@Cacheable` 方法的位置时发现
- 解决：在 `AnalysisController.exportAnalysis` 中添加 `validateAnalysisAccess` 调用

**问题 5：CachePenetrationAvalancheTest 不匹配新架构**

- 现象：测试期望 `@CacheEvict(key="#userId", allEntries=false)`，但 B-002 修复后实际是 `@CacheEvict(allEntries=true)`
- 解决：修改测试断言，验证 `allEntries=true` 并说明这是 B-002 修复的折衷方案

**问题 6：PaperServiceSearchTest 异常类型不匹配**

- 现象：测试期望 `IllegalArgumentException`，但 U-002 修复后实际是 `BusinessException`
- 解决：修改测试断言使用 `BusinessException`

## 实现步骤

### 第一步：明确架构决策（与用户确认）

通过 AskUserQuestion 询问用户：
- **数据隔离漏洞修复方案**：Controller 层校验（推荐） / Service 层 AOP 拦截 / 缓存 Key 含 userId
- **U-001 引用数筛选**：不实现（保持现状） / 实现
- **S-001 SessionService.createSession allEntries=true**：保留（推荐） / 改 RedisTemplate.scan

**用户选择**：Controller 层校验 + 不实现引用数筛选 + 保留 allEntries=true

### 第二步：源代码修复（10 项，已在上一轮完成）

| 顺序 | 编号 | 内容 | 文件 |
|------|------|------|------|
| 1 | B-001/B-005 | UserController.validateUserIdMatch | UserController.java + UserService.java |
| 2 | B-002 | RedisKeyUtil.favoriteListKey(userId, page, size) | RedisKeyUtil.java + FavoriteService.java |
| 3 | B-003 | AnalysisController 调用 validateAnalysisAccess | AnalysisController.java + AnalysisService.java |
| 4 | B-004 | SessionService.validateSessionAccess 公开方法 | SessionController.java + SessionService.java |
| 5 | S-001 | SessionService.createSession 添加注释 | SessionService.java |
| 6 | S-003 | PaperRepositoryCustomImpl CONCAT → JSON_QUOTE | PaperRepositoryCustomImpl.java |
| 7 | U-002 | PaperService.searchPapers 抛 BusinessException | PaperService.java |
| 8 | U-003 | AnalysisService 三处 try-finally evict | AnalysisService.java |
| 9 | U-005 | PaperService 热点 key 加 sync=true | PaperService.java |
| 10 | 测试 | Jm5IntegrationTest 新增 JM5-9/10/11 | Jm5IntegrationTest.java |

### 第三步：编译验证

```bash
cd Veritas/backend && mvn compile -q
```

**结果**：✅ 编译成功

### 第四步：运行测试（发现 5 + 4 = 9 个失败）

首次运行 `mvn test` 发现：
- **4 个文件 8 个测试** 因校验上移导致 Mock 不被调用或期望异常不再抛出
- **2 个文件 5 个测试** 因 B-002 和 U-002 修复导致断言不匹配

### 第五步：本轮修复（本轮重点）

**1. 新漏洞补丁 — ExportService**

```java
// AnalysisController.java - exportAnalysis 方法
analysisService.validateAnalysisAccess(currentUserId, analysisId);
byte[] bytes = exportService.export(currentUserId, analysisId, format);
```

**2. 删除失效测试（4 个）**

| 文件 | 删除的测试 |
|------|----------|
| UserServiceProfileTest | getProfile_notAuthenticated_throwsAuthenticationException |
| UserServiceProfileTest | getProfile_forbiddenAccess_throwsBusinessException |
| AnalysisServiceQueryTest | getAnalysisResult_other_user_returns403 |
| SessionServiceTest | getSessionDetail_dataIsolationViolation_throws403 |
| SessionServiceTest | getSessionDetail_unauthenticated_throws401 |

**3. 修改测试 Mock（4 个文件）**

| 文件 | 修改 |
|------|------|
| UserControllerTest | 设置 SecurityContext + 移除 Service Mock + 添加 @BeforeEach/@AfterEach |
| AnalysisServiceQueryTest | 移除 sessionRepository.findBySessionId 的 Mock |
| CachePenetrationAvalancheTest | 修改 3 个测试断言匹配 B-002 修复 |
| PaperServiceSearchTest | 修改 2 个测试断言使用 BusinessException |

### 第六步：重新运行测试验证

```bash
cd Veritas/backend && mvn test
```

**结果**：✅ **445 个测试全部通过，0 失败，0 错误**

### 第七步：归档

按 `log/规则.md` 协议归档到 `log/backend/19_JM5审阅问题修复与漏洞补丁/`。

## 解决了什么问题

### 核心问题描述

**JM5 缓存优化的核心 bug**：`@Cacheable` 注解的语义陷阱。

```java
// 看似安全的代码：
@Cacheable(value = "userProfile", key = "#userId")
public ProfileResponse getProfile(String userId) {
    validateDataIsolation(userId);  // ← 缓存命中时不执行！
    return userProfileRepository.findByUserId(userId)
            .map(userMapper::toProfileResponse)
            .orElseThrow(...);
}
```

实际攻击路径：
1. 用户 A 调用 `GET /api/users/uA/profile` → 缓存未命中 → 执行方法 → 校验通过 → 缓存 key=`uA` 写入
2. 用户 B 调用 `GET /api/users/uA/profile` → **缓存命中（key=`uA`）** → 直接返回用户 A 画像，**绕过 `validateDataIsolation`**

**4 个 P0 漏洞 + 1 个延伸漏洞**：用户 B 可读取用户 A 的画像 / 分析结果 / 会话详情 / 报告导出。

### 解决方案对比

| 方案 | 实现复杂度 | 安全保证 | 性能影响 | 选择 |
|------|----------|---------|---------|------|
| Controller 层校验 + Service 信任入参 | ⭐⭐ 简单 | ✅ 每次请求必执行 | 无影响 | ✅ |
| Service 层校验 + 自定义 AOP 拦截 | ⭐⭐⭐⭐ 复杂 | ✅ AOP 总是拦截 | AOP 调用开销 | ❌ |
| 缓存 Key 含 userId | ⭐⭐⭐ 中等 | ✅ 天然隔离 | 同一资源缓存多份 | ❌ |
| 自定义 RedisCacheManager 拦截 | ⭐⭐⭐⭐⭐ 极复杂 | ✅ 精细控制 | 维护成本高 | ❌ |

### 最终方案的优势

1. **简单直接**：Controller 层加 5-10 行校验代码，无需 AOP/自定义拦截器
2. **安全保证**：每次请求都执行校验，不受缓存影响
3. **零性能开销**：校验逻辑是简单字符串比较 + DB 查询（仅资源 ID 类）
4. **易于测试**：Controller 测试直接验证 403 响应，无需模拟 Spring Cache 行为
5. **架构清晰**：Controller 负责安全/权限，Service 负责业务逻辑，职责分明

### 配套架构原则

**「缓存安全审查清单」**：每次新增 `@Cacheable` 方法时，必须检查：

1. ✅ **Key 完整性**：所有影响结果的参数都必须在 Key 中（包括分页参数）
2. ✅ **无内部校验**：方法体内禁止做权限校验、所有权校验
3. ✅ **Controller 层校验**：在调用 `@Cacheable` Service 前，必须在 Controller 层校验归属
4. ✅ **unless 防穿透**：`unless = "#result == null"` 防止空值缓存
5. ✅ **sync 防击穿**：热点 key 加 `sync = true` 防止缓存击穿
6. ✅ **try-finally evict**：写操作使用 `try-finally` 确保缓存一致性
7. ✅ **合理 TTL + 抖动**：避免雪崩

## 变更内容

### 新增文件
无新增源代码文件。

### 修改文件

**源代码（1 个，本轮新增）**

| 文件 | 变更 |
|------|------|
| [AnalysisController.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/main/java/com/literatureassistant/controller/AnalysisController.java) | `exportAnalysis` 添加 `validateAnalysisAccess` 调用（B-003 延伸） |

**测试文件（7 个）**

| 文件 | 变更 |
|------|------|
| [UserServiceProfileTest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/test/java/com/literatureassistant/service/UserServiceProfileTest.java) | 删除 2 个失效测试 |
| [UserControllerTest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/test/java/com/literatureassistant/controller/UserControllerTest.java) | 修改 2 个数据隔离测试 + 新增 @BeforeEach/@AfterEach |
| [AnalysisServiceQueryTest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/test/java/com/literatureassistant/service/AnalysisServiceQueryTest.java) | 移除 2 个 Mock + 删除 1 个失效测试 |
| [SessionServiceTest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/test/java/com/literatureassistant/service/SessionServiceTest.java) | 删除 2 个失效测试 |
| [CachePenetrationAvalancheTest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/test/java/com/literatureassistant/cache/CachePenetrationAvalancheTest.java) | 修改 3 个测试匹配 B-002 修复 |
| [PaperServiceSearchTest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/test/java/com/literatureassistant/service/PaperServiceSearchTest.java) | 修改 2 个测试匹配 U-002 修复 |
| [Jm5IntegrationTest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/test/java/com/literatureassistant/integration/Jm5IntegrationTest.java) | 新增 JM5-9/10/11 数据隔离测试用例 |

### 配置变更
无配置变更。

## 关键技术点

### 1. Spring Cache 语义陷阱

**核心规则**：`@Cacheable` 命中时，方法体**完全不执行**，包括所有的安全校验、权限检查、业务逻辑。

**正确做法**：
- `@Cacheable` 方法体内只做数据查询 + DTO 转换
- 安全/权限校验**必须**在 Controller 层执行
- Controller 层校验失败时直接抛异常，不调用 Service

### 2. 数据隔离校验的两种模式

**模式 A：path variable 是 userId**

```java
@GetMapping("/{userId}/profile")
public ApiResponse<ProfileResponse> getProfile(@PathVariable String userId) {
    validateUserIdMatch(userId);  // 直接比较
    return ApiResponse.success(userService.getProfile(userId));
}
```

**模式 B：path variable 是资源 ID**

```java
@GetMapping("/{analysisId}")
public ApiResponse<AnalysisResponse> getAnalysisResult(@PathVariable String analysisId) {
    analysisService.validateAnalysisAccess(currentUserId, analysisId);  // 查 DB 校验
    return ApiResponse.success(analysisService.getAnalysisResult(currentUserId, analysisId));
}
```

### 3. 缓存 Key 完整性原则

**反例**：`@Cacheable(key = "#userId")` 但方法签名是 `listFavorites(userId, page, size)`

```java
// 用户 u1 查询 page=1&size=10 → 缓存 key=u1
// 用户 u1 查询 page=2&size=10 → 缓存命中 key=u1 → 返回 page=1 的数据（错误！）
```

**正例**：Key 包含所有影响结果的参数

```java
@Cacheable(key = "T(com.literatureassistant.util.RedisKeyUtil).favoriteListKey(#userId, #page, #size)")
```

### 4. JSON 注入防护

**反例**：`CONCAT('"', ?6, '"')` 不会转义特殊字符

```sql
-- keywords = 'deep"learning' → 生成 "deep"learning"（非法 JSON）
JSON_CONTAINS(keywords, CONCAT('"', ?6, '"'))
```

**正例**：使用 `JSON_QUOTE` 自动转义

```sql
JSON_CONTAINS(keywords, JSON_QUOTE(?6))
```

### 5. try-finally 缓存 evict 模式

```java
AnalysisTaskResponse response;
try {
    response = analysisTransactionService.completeAnalysis(pending.getId(), result);
} finally {
    evictAnalysisResultCache(analysisId);  // 无论是否抛异常都 evict
}
```

**避免场景**：`completeAnalysis` 抛异常 → 事务回滚 → evict 不执行 → 缓存可能仍是旧的 PENDING 状态数据。

### 6. Mockito void 方法 mock 语法

```java
// void 方法不能用 when().thenThrow()
doThrow(new BusinessException(403, "无权限", "FORBIDDEN"))
        .when(analysisService).validateAnalysisAccess("uB", "anl_A");

// void 方法的正常返回
doNothing().when(sessionService).validateSessionAccess(anyString(), anyString());
```

## 经验总结

### 开发过程中的收获

1. **架构原则重于实现细节**：数据隔离校验放在 Controller 层还是 Service 层，不是简单的代码位置问题，而是架构原则问题。Controller 负责安全、Service 负责业务、Repository 负责数据访问，分层清晰才能避免缓存/事务/AOP 等"横切关注点"带来的复杂性。

2. **缓存是双刃剑**：缓存能极大提升性能，但也会绕过业务逻辑。`@Cacheable` 命中时方法体不执行是一个**安全陷阱**，必须在 Controller 层做校验。

3. **测试与架构同步演进**：架构变更（校验上移）必须同步更新测试，否则测试会失败或给出错误的信号。本轮发现 8 个测试失败 + 4 个测试错误，本质都是测试没有跟上架构演进。

4. **审计必须系统化**：修复 B-001/B-003/B-004 时，应该**系统审计所有调用 `@Cacheable` 方法的位置**，而不是只修审阅报告列出的部分。本轮发现 `ExportService.getValidatedResult` 也是同类漏洞（B-003 延伸）。

### 踩过的坑及如何避免

**坑 1：`@Cacheable` 内部校验被绕过**
- **症状**：用户 B 命中用户 A 缓存，绕过权限校验
- **避免**：所有 `@Cacheable` 方法体内禁止做权限校验，校验必须上移到 Controller

**坑 2：缓存 Key 不完整**
- **症状**：不同分页查询互相干扰，用户永远只能看到第一次查询的页
- **避免**：建立"缓存安全审查清单"，每次新增 `@Cacheable` 必须检查 Key 完整性

**坑 3：JSON 注入**
- **症状**：keywords 含双引号会破坏 JSON 结构，导致 `JSON_CONTAINS` 报错
- **避免**：使用 `JSON_QUOTE` 自动转义，而不是手动 `CONCAT` 拼接

**坑 4：缓存与事务不一致**
- **症状**：`completeAnalysis` 抛异常时 evict 不执行，缓存仍是旧数据
- **避免**：写操作使用 `try-finally` 确保 evict 一定执行

**坑 5：测试 Mock 与新架构不匹配**
- **症状**：校验上移后，原有测试的 Mock 不被调用（UnnecessaryStubbing）或期望异常不再抛出
- **避免**：架构变更时，必须同步审查所有相关测试

### 最佳实践建议

1. **「Controller 校验 + Service 信任入参」原则**
   - Controller 层做所有安全/权限校验
   - Service 层 `@Cacheable` 方法信任入参，不做二次校验
   - 校验方式：path variable 是 userId 直接比较；是资源 ID 调用 Service 的 `validateXxxAccess` 公开方法

2. **「缓存安全审查清单」**
   - 每次新增 `@Cacheable` 方法时检查：
     - Key 是否含所有影响结果的参数（包括分页参数）
     - 方法体内是否有权限校验（应禁止）
     - 缓存命中是否会绕过校验（是 → 必须上移到 Controller）
     - 是否使用 `unless` 防穿透
     - 热点 key 是否使用 `sync=true` 防击穿

3. **「测试匹配架构」原则**
   - 架构变更（尤其是分层变更）必须同步更新测试
   - 删除失效测试 > 修改测试绕过架构
   - 数据隔离测试必须在 Controller 层验证 403 响应

4. **「系统审计同类问题」原则**
   - 修复一个漏洞时，必须审计所有同类位置
   - 例如：修复 B-003 时应该审计所有调用 `getAnalysisResult` 的位置（如 `ExportService`）
   - 否则会留下"延伸漏洞"（B-003 延伸）

5. **「try-finally 缓存 evict」模式**
   - 所有写操作的缓存 evict 必须放在 `finally` 块中
   - 保证异常路径下缓存也能失效，避免缓存不一致

6. **「JSON 操作使用 MySQL 内置函数」原则**
   - JSON 字符串拼接使用 `JSON_QUOTE`，不要用 `CONCAT` 手动拼接
   - JSON 对象构建使用 `JSON_OBJECT`，不要用字符串拼接
   - 避免 JSON 注入风险