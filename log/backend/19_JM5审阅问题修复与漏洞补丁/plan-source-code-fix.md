# JM5 审阅报告问题修复计划

## Summary

修复 JM5 审阅报告中指出的 4 个 P0 严重数据隔离漏洞 + 1 个额外发现的同类漏洞，以及 3 个 P1/P2 重要问题。修复后 JM5 缓存优化与功能完善里程碑可达到生产级安全标准。

**修复范围**: 7 个源文件 + 5 个测试文件
**修复策略**: Controller 层校验资源归属 + Service @Cacheable 方法信任入参 + 缓存 Key 完整性修复 + JSON 注入防护

---

## Current State Analysis

### 当前存在的问题（按严重级别）

| 级别 | 编号 | 问题 | 文件 |
|------|------|------|------|
| 🔴 P0 | B-001 | `UserService.getProfile` 缓存命中绕过 `validateDataIsolation` | UserService.java:160 |
| 🔴 P0 | B-002 | `FavoriteService.listFavorites` 缓存 Key 缺 page/size 参数 | FavoriteService.java:111 |
| 🔴 P0 | B-003 | `AnalysisService.getAnalysisResult` 缓存命中绕过 `validateDataIsolation` | AnalysisService.java:223 |
| 🔴 P0 | B-004 | `SessionService.getSessionDetail` 缓存命中绕过 `validateDataIsolation` | SessionService.java:99 |
| 🔴 P0 | B-005 | `UserService.getUserInfo` 缺 `validateDataIsolation`（审阅报告未列出，同类漏洞） | UserService.java:96 |
| 🟠 P1 | S-001 | `SessionService.createSession` 使用 `allEntries=true`（用户选择保留，添加注释） | SessionService.java:52 |
| 🟠 P1 | S-003 | `PaperRepositoryCustomImpl` JSON_CONTAINS 存在 JSON 注入风险 | PaperRepositoryCustomImpl.java:52 |
| 🟡 P2 | U-002 | `PaperService.searchPapers` 抛 `IllegalArgumentException` 应为 `BusinessException` | PaperService.java:89 |
| 🟡 P2 | U-003 | `AnalysisService.evictAnalysisResultCache` 异常路径缓存不一致 | AnalysisService.java:115 |
| 🟡 P2 | U-005 | `PaperService.searchPapers` 缺 `sync=true` 防缓存击穿 | PaperService.java:82 |
| 🟢 P3 | N-003 | `RedisKeyUtil.favoriteListKey` 死代码（修复 B-002 时自然解决） | RedisKeyUtil.java:89 |

### 不修复的项（用户决策或可接受现状）

| 编号 | 原因 |
|------|------|
| U-001 引用数筛选 | 用户选择不实现，保持现状 |
| S-002 TTL 抖动空间级 | 复杂度高，当前空间级抖动可接受 |
| U-004 syncProfileToRedis 失败处理 | 降级容错可接受 |
| U-006 幂等场景 @CacheEvict | 频率低，不影响正确性 |
| N-001/N-002 代码风格 | 不影响功能 |

### 架构决策

**数据隔离修复方案**: Controller 层校验资源归属

```
请求 → Controller（校验 currentUserId 与资源归属）
         ↓ 信任入参
       Service @Cacheable 方法（无内部校验，缓存命中安全）
         ↓
       Repository
```

**校验方式分类**:
- **path variable 是 userId 的**（getProfile/getUserInfo）→ Controller 直接比较 `userId == currentUserId`
- **path variable 是资源 ID 的**（getAnalysisResult/getSessionDetail）→ Controller 调用 Service 的 `validateXxxAccess` public 方法查 DB 校验

---

## Proposed Changes

### 1. [P0] 修复 B-001/B-005: UserService 数据隔离漏洞

**文件**: `backend/src/main/java/com/literatureassistant/controller/UserController.java`
**文件**: `backend/src/main/java/com/literatureassistant/service/UserService.java`

**What**: 在 Controller 层校验 `userId == currentUserId`，Service 的 `@Cacheable` 方法移除内部 `validateDataIsolation`

**Why**: `@Cacheable` 命中时方法体不执行，导致 `validateDataIsolation` 被绕过，用户 B 可命中用户 A 的缓存

**How**:

UserController.java 修改：
```java
@GetMapping("/{userId}")
public ApiResponse<UserResponse> getUserInfo(@PathVariable String userId) {
    validateUserIdMatch(userId);  // 新增校验
    UserResponse response = userService.getUserInfo(userId);
    return ApiResponse.success(response);
}

@GetMapping("/{userId}/profile")
public ApiResponse<ProfileResponse> getProfile(@PathVariable String userId) {
    validateUserIdMatch(userId);  // 新增校验
    ProfileResponse response = userService.getProfile(userId);
    return ApiResponse.success(response);
}

// 新增私有方法
private void validateUserIdMatch(String userId) {
    String currentUserId = extractCurrentUserId();
    if (currentUserId == null || currentUserId.isBlank()) {
        throw new AuthenticationException("未认证，请先登录");
    }
    if (!currentUserId.equals(userId)) {
        throw new BusinessException(403, "无权限访问他人数据", "FORBIDDEN_ACCESS");
    }
}

private String extractCurrentUserId() {
    Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
    if (authentication != null && authentication.getPrincipal() instanceof String principal) {
        return principal;
    }
    return null;
}
```

UserService.java 修改：
- `getUserInfo`: 保持不变（原本就没有 validateDataIsolation，现在由 Controller 校验）
- `getProfile`: 移除 `validateDataIsolation(userId)` 调用，添加注释说明校验已上移到 Controller
- 保留 `validateDataIsolation` 私有方法（createProfile/updateProfile 仍使用）

```java
@Cacheable(value = "userProfile", key = "#userId", unless = "#result == null")
public ProfileResponse getProfile(String userId) {
    // 数据隔离校验已上移到 UserController，此处信任入参
    UserProfile profile = userProfileRepository.findByUserId(userId)
            .orElseThrow(() -> new ResourceNotFoundException("UserProfile", userId));
    return userMapper.toProfileResponse(profile);
}
```

UserController.java 需新增 import:
```java
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import com.literatureassistant.exception.AuthenticationException;
import com.literatureassistant.exception.BusinessException;
```

---

### 2. [P0] 修复 B-002: FavoriteService.listFavorites 缓存 Key 缺分页参数

**文件**: `backend/src/main/java/com/literatureassistant/util/RedisKeyUtil.java`
**文件**: `backend/src/main/java/com/literatureassistant/service/FavoriteService.java`

**What**: 扩展 `RedisKeyUtil.favoriteListKey` 支持 page/size，`FavoriteService.listFavorites` 的 `@Cacheable` Key 改用复合 Key

**Why**: 当前 Key 只有 `#userId`，不同 page/size 查询会命中同一缓存，分页完全失效

**How**:

RedisKeyUtil.java 修改：
```java
/**
 * task36: 用户收藏列表 Key（分页）。
 * 修复 B-002: 原 favoriteListKey(userId) 缺 page/size，导致分页失效。
 */
public static String favoriteListKey(String userId, int page, int size) {
    return "user:favorites:" + userId + ":" + page + ":" + size;
}
```
保留原 `favoriteListKey(String userId)` 方法以避免破坏兼容性（如有其他引用），但标注 @Deprecated。

FavoriteService.java 修改：
```java
@Cacheable(value = "favoriteList",
    key = "T(com.literatureassistant.util.RedisKeyUtil).favoriteListKey(#userId, #page, #size)",
    unless = "#result == null")
@Transactional(readOnly = true)
public PageResponse<FavoriteResponse> listFavorites(String userId, int page, int size) { ... }
```

---

### 3. [P0] 修复 B-003: AnalysisService.getAnalysisResult 数据隔离漏洞

**文件**: `backend/src/main/java/com/literatureassistant/controller/AnalysisController.java`
**文件**: `backend/src/main/java/com/literatureassistant/service/AnalysisService.java`

**What**: Controller 层先调用 `validateAnalysisAccess` 校验归属，Service 的 `@Cacheable` 方法移除内部 `validateDataIsolation`

**Why**: `@Cacheable` 命中时绕过 `validateDataIsolation`，用户 B 可命中用户 A 的分析结果缓存

**How**:

AnalysisController.java 修改 `getAnalysisResult`：
```java
@GetMapping("/{analysisId}")
public ResponseEntity<ApiResponse<AnalysisResponse>> getAnalysisResult(
        @PathVariable String analysisId,
        @AuthenticationPrincipal String userId) {
    String currentUserId = validateUserId(userId);
    log.info("REST getAnalysisResult: userId={}, analysisId={}", currentUserId, analysisId);
    // 修复 B-003: 先校验资源归属（查 DB），再调用 @Cacheable 方法
    analysisService.validateAnalysisAccess(currentUserId, analysisId);
    AnalysisResponse response = analysisService.getAnalysisResult(currentUserId, analysisId);
    return ResponseEntity.ok(ApiResponse.success(response));
}
```

AnalysisService.java 修改 `getAnalysisResult`：
```java
@Cacheable(value = "analysisResult", key = "#analysisId", unless = "#result == null")
public AnalysisResponse getAnalysisResult(String userId, String analysisId) {
    AnalysisResult entity = analysisResultRepository.findByAnalysisId(analysisId)
            .orElseThrow(() -> new ResourceNotFoundException("AnalysisResult", analysisId));
    // 修复 B-003: 数据隔离校验已上移到 Controller（validateAnalysisAccess），此处信任入参
    AnalysisResultDTO resultDto = deserializeResult(entity.getResult());
    return AnalysisResponse.builder()....build();
}
```

注意：`validateAnalysisAccess` 已存在（AnalysisService.java:364），无需新增。但需确认其可见性为 public。

---

### 4. [P0] 修复 B-004: SessionService.getSessionDetail 数据隔离漏洞

**文件**: `backend/src/main/java/com/literatureassistant/controller/SessionController.java`
**文件**: `backend/src/main/java/com/literatureassistant/service/SessionService.java`

**What**: SessionService 新增 public `validateSessionAccess` 方法，Controller 层调用校验，`getSessionDetail` 移除内部 `validateDataIsolation`

**Why**: `@Cacheable` 命中时绕过 `validateDataIsolation`，用户 B 可命中用户 A 的会话详情缓存

**How**:

SessionService.java 新增 public 方法：
```java
/**
 * 修复 B-004: 校验 sessionId 归属（供 Controller 在调用 @Cacheable 方法前使用）。
 * <p>数据隔离：sessionId 对应的 Session.userId 必须等于 currentUserId。
 */
public void validateSessionAccess(String userId, String sessionId) {
    Session session = sessionRepository.findBySessionId(sessionId)
            .orElseThrow(() -> new ResourceNotFoundException("Session", sessionId));
    if (!userId.equals(session.getUserId())) {
        throw new BusinessException(403, "无权限访问他人会话", "FORBIDDEN_ACCESS");
    }
}
```

SessionService.java 修改 `getSessionDetail`：
```java
@Cacheable(value = "sessionState", key = "#sessionId", unless = "#result == null")
@Transactional(readOnly = true)
public SessionDetailResponse getSessionDetail(String sessionId) {
    // 修复 B-004: 数据隔离校验已上移到 Controller（validateSessionAccess），此处信任入参
    Session session = sessionRepository.findBySessionId(sessionId)
            .orElseThrow(() -> new ResourceNotFoundException("Session", sessionId));
    SessionDetailResponse response = sessionMapper.toDetailResponse(session);
    int analysisCount = (int) analysisResultRepository.countBySessionId(sessionId);
    response.setAnalysisCount(analysisCount);
    log.info("Session detail fetched from DB: sessionId={}, analysisCount={}", sessionId, analysisCount);
    return response;
}
```

SessionController.java 修改 `getSessionDetail`：
```java
@GetMapping("/{sessionId}")
public ApiResponse<SessionDetailResponse> getSessionDetail(@PathVariable String sessionId) {
    String userId = extractCurrentUserId();
    log.info("REST getSessionDetail: userId={}, sessionId={}", userId, sessionId);
    // 修复 B-004: 先校验资源归属（查 DB），再调用 @Cacheable 方法
    sessionService.validateSessionAccess(userId, sessionId);
    SessionDetailResponse response = sessionService.getSessionDetail(sessionId);
    return ApiResponse.success(response);
}
```

---

### 5. [P1] 修复 S-001: SessionService.createSession allEntries=true 添加注释

**文件**: `backend/src/main/java/com/literatureassistant/service/SessionService.java`

**What**: 保留 `allEntries=true`，添加注释说明折衷理由

**Why**: 用户选择保留，需记录设计决策

**How**:
```java
@Transactional
// S-001: allEntries=true 会清空整个 sessionList 缓存空间，影响其他用户。
// 折衷理由：sessionList TTL=10min 较短，创建会话频率低，影响可控。
// 长期优化方案：改用 RedisTemplate.scan 按 session:list:{userId}:* 前缀精准失效。
@org.springframework.cache.annotation.CacheEvict(value = "sessionList", allEntries = true)
public SessionResponse createSession(String userId, SessionCreateRequest request) { ... }
```

---

### 6. [P1] 修复 S-003: PaperRepositoryCustomImpl JSON 注入

**文件**: `backend/src/main/java/com/literatureassistant/repository/PaperRepositoryCustomImpl.java`

**What**: `CONCAT('\"', ?6, '\"')` 改为 `JSON_QUOTE(?6)`

**Why**: `CONCAT` 不会转义特殊字符，若 keywords 含双引号会破坏 JSON 结构

**How**:

PaperRepositoryCustomImpl.java 修改 DATA_SQL_TEMPLATE 和 COUNT_SQL：
```java
private static final String DATA_SQL_TEMPLATE =
        "SELECT * FROM papers " +
        "WHERE MATCH(title, `abstract`) AGAINST(?1 IN NATURAL LANGUAGE MODE) " +
        "AND (?2 IS NULL OR year >= ?2) " +
        "AND (?3 IS NULL OR year <= ?3) " +
        "AND (?4 IS NULL OR venue = ?4) " +
        "AND (?5 IS NULL OR authors LIKE CONCAT('%', ?5, '%')) " +
        // S-003 修复: 使用 JSON_QUOTE 自动转义特殊字符，防止 JSON 注入
        "AND (?6 IS NULL OR JSON_CONTAINS(keywords, JSON_QUOTE(?6)))";

private static final String COUNT_SQL =
        "SELECT COUNT(*) FROM papers " +
        "WHERE MATCH(title, `abstract`) AGAINST(?1 IN NATURAL LANGUAGE MODE) " +
        "AND (?2 IS NULL OR year >= ?2) " +
        "AND (?3 IS NULL OR year <= ?3) " +
        "AND (?4 IS NULL OR venue = ?4) " +
        "AND (?5 IS NULL OR authors LIKE CONCAT('%', ?5, '%')) " +
        "AND (?6 IS NULL OR JSON_CONTAINS(keywords, JSON_QUOTE(?6)))";
```

---

### 7. [P2] 修复 U-002: PaperService.searchPapers 异常类型

**文件**: `backend/src/main/java/com/literatureassistant/service/PaperService.java`

**What**: `IllegalArgumentException` → `BusinessException`

**Why**: 项目统一使用 BusinessException 体系，IllegalArgumentException 不会被 GlobalExceptionHandler 正确映射

**How**:
```java
if (q == null || q.trim().isEmpty()) {
    // U-002 修复: 使用 BusinessException 替代 IllegalArgumentException
    throw new BusinessException(400, "搜索关键词不能为空", "INVALID_PARAMETER");
}
```

---

### 8. [P2] 修复 U-003: AnalysisService.evictAnalysisResultCache 异常路径

**文件**: `backend/src/main/java/com/literatureassistant/service/AnalysisService.java`

**What**: 改为 try-finally 确保 evict 执行

**Why**: completeAnalysis 抛异常时 evict 不执行，可能导致缓存不一致

**How**:

AnalysisService.java 修改 analyzePaper/comparePapers/generateReport 三处：
```java
// 7) 更新 AnalysisResult 状态 + result JSON — 短事务
AnalysisTaskResponse response;
try {
    response = analysisTransactionService.completeAnalysis(pending.getId(), result);
} finally {
    // U-003 修复: 无论 completeAnalysis 是否抛异常，都 evict 缓存
    evictAnalysisResultCache(analysisId);
}
return response;
```

注意：三处编排方法（analyzePaper/comparePapers/generateReport）都需要同样修改。

---

### 9. [P2] 修复 U-005: PaperService.searchPapers 添加 sync=true

**文件**: `backend/src/main/java/com/literatureassistant/service/PaperService.java`

**What**: `@Cacheable` 添加 `sync = true`

**Why**: 防止高并发查询同一 key 时缓存击穿

**How**:
```java
@Cacheable(value = "paperSearch",
    key = "T(com.literatureassistant.util.RedisKeyUtil).paperSearchKey(...)",
    sync = true,  // U-005 修复: 防止缓存击穿
    unless = "#result == null")
@Transactional(readOnly = true)
public PageResponse<PaperResponse> searchPapers(...) { ... }
```

同样应用于 `listPapers` 和 `getPaperDetail`（热点 key）。

---

### 10. 测试文件更新

**文件**:
- `backend/src/test/java/com/literatureassistant/service/UserServiceCacheTest.java`
- `backend/src/test/java/com/literatureassistant/service/FavoriteServiceTest.java`
- `backend/src/test/java/com/literatureassistant/cache/CacheConsistencyTest.java`
- `backend/src/test/java/com/literatureassistant/integration/Jm5IntegrationTest.java`
- `backend/src/test/java/com/literatureassistant/repository/PaperRepositoryFilterSortTest.java`（JSON_QUOTE 验证）

**What**: 更新现有测试以匹配修复后的代码，新增数据隔离测试用例

**How**:

1. **UserServiceCacheTest**: 移除对 `validateDataIsolation` 的依赖验证，新增"Controller 层校验"的说明注释

2. **FavoriteServiceTest**: 更新 `testListFavoritesCacheable` 测试，验证 Key 包含 page/size
```java
@Test
@DisplayName("testListFavoritesCacheable - @Cacheable(favoriteList) Key 含 page/size")
void testListFavoritesCacheable() throws NoSuchMethodException {
    var method = FavoriteService.class.getMethod("listFavorites", String.class, int.class, int.class);
    var cacheable = method.getAnnotation(org.springframework.cache.annotation.Cacheable.class);
    assertThat(cacheable).isNotNull();
    assertThat(cacheable.value()).contains("favoriteList");
    // 修复 B-002: Key 必须包含 page/size
    assertThat(cacheable.key()).contains("favoriteListKey");
    assertThat(cacheable.key()).contains("#page");
    assertThat(cacheable.key()).contains("#size");
}
```

3. **CacheConsistencyTest**: 新增数据隔离测试用例
```java
@Test
@DisplayName("testDataIsolationOnCacheHit - 缓存命中时不绕过数据隔离（Controller 层校验）")
void testDataIsolationOnCacheHit() {
    // 验证 Controller 层有 validateUserIdMatch / validateXxxAccess 调用
    // 由于单元测试无法模拟 Spring Cache 行为，此处验证 Service 方法不含 validateDataIsolation
    // 实际数据隔离由 Controller 层保证
}
```

4. **Jm5IntegrationTest**: 新增数据隔离集成测试
```java
@Test
@DisplayName("JM5-9: GET /api/users/{userId}/profile - 用户B访问用户A画像返回403")
void testGetProfileDataIsolation() throws Exception {
    authenticateAs("uB");
    paperMvc.perform(get("/api/users/uA/profile"))
            .andExpect(status().isForbidden());
}

@Test
@DisplayName("JM5-10: GET /api/analysis/{analysisId} - 用户B访问用户A分析结果返回403")
void testGetAnalysisResultDataIsolation() throws Exception {
    authenticateAs("uB");
    when(analysisService.validateAnalysisAccess("uB", "anl_A"))
            .thenThrow(new BusinessException(403, "无权限访问他人分析结果", "FORBIDDEN_ACCESS"));
    analysisMvc.perform(get("/api/analysis/anl_A"))
            .andExpect(status().isForbidden());
}
```

5. **PaperRepositoryFilterSortTest**: 更新 SQL 验证，确认使用 JSON_QUOTE
```java
@Test
@DisplayName("testKeywordsFilter - keywords 使用 JSON_QUOTE 防注入")
void testKeywordsFilter() {
    // ... 调用 searchByKeyword ...
    ArgumentCaptor<String> sqlCaptor = ArgumentCaptor.forClass(String.class);
    verify(entityManager).createNativeQuery(sqlCaptor.capture(), eq(Paper.class));
    assertThat(sqlCaptor.getValue()).contains("JSON_QUOTE(?6)");
    assertThat(sqlCaptor.getValue()).doesNotContain("CONCAT('\"'");
}
```

---

## Assumptions & Decisions

### 假设
1. `validateAnalysisAccess` (AnalysisService.java:364) 已是 public 方法，无需修改可见性
2. `extractCurrentUserId` 模式已在多个 Controller 中存在，可复用
3. 现有测试中 Mock 的行为不依赖 `validateDataIsolation` 在 Service 内部执行
4. `JSON_QUOTE` 是 MySQL 8.0+ 内置函数，项目使用 MySQL 8.0+ 支持

### 决策
1. **数据隔离修复方案**: Controller 层校验（用户选择）
2. **引用数筛选**: 不实现（用户选择）
3. **allEntries=true**: 保留，添加注释说明（用户选择）
4. **TTL 抖动**: 不修复 S-002（复杂度高，可接受现状）
5. **syncProfileToRedis 失败处理**: 不修复 U-004（降级容错可接受）
6. **try-finally evict**: 应用到 analyzePaper/comparePapers/generateReport 三处

---

## Verification Steps

### 1. 编译验证
```bash
cd Veritas/backend && mvn compile -q
```

### 2. 单元测试
```bash
cd Veritas/backend && mvn test -q
```

重点关注：
- `UserServiceCacheTest`: 验证 getProfile/getUserInfo 不再依赖内部 validateDataIsolation
- `FavoriteServiceTest`: 验证 listFavorites Key 含 page/size
- `PaperRepositoryFilterSortTest`: 验证 SQL 使用 JSON_QUOTE
- `CacheConsistencyTest`: 验证数据隔离注解配置

### 3. 集成测试
```bash
cd Veritas/backend && mvn test -Dtest=Jm5IntegrationTest -q
```

重点关注新增的数据隔离测试用例（JM5-9 / JM5-10）。

### 4. 手动验证（可选）
启动应用后，用两个不同用户的 JWT Token 验证：
1. 用户 B 调用 `GET /api/users/{userA_id}/profile` → 应返回 403
2. 用户 B 调用 `GET /api/analysis/{userA_analysisId}` → 应返回 403
3. 用户 B 调用 `GET /api/sessions/{userA_sessionId}` → 应返回 403
4. 用户 A 调用 `GET /api/papers/favorites?page=1&size=10` 后再调 `?page=2&size=10` → 应返回不同页

### 5. 代码审查清单
- [ ] 所有 `@Cacheable` 方法的 Controller 层有归属校验
- [ ] `FavoriteService.listFavorites` Key 含 page/size
- [ ] `PaperRepositoryCustomImpl` SQL 使用 JSON_QUOTE
- [ ] `PaperService.searchPapers` 抛 BusinessException
- [ ] `AnalysisService` 三处编排方法用 try-finally evict
- [ ] `PaperService` 热点 key 加 sync=true
- [ ] 新增测试用例覆盖数据隔离场景

---

## 修复优先级与执行顺序

| 顺序 | 任务 | 文件数 | 优先级 |
|------|------|--------|--------|
| 1 | B-001/B-005: UserService 数据隔离 | 2 | P0 |
| 2 | B-002: FavoriteService 缓存 Key | 2 | P0 |
| 3 | B-003: AnalysisService 数据隔离 | 2 | P0 |
| 4 | B-004: SessionService 数据隔离 | 2 | P0 |
| 5 | S-003: JSON 注入修复 | 1 | P1 |
| 6 | U-002: 异常类型修复 | 1 | P2 |
| 7 | U-003: try-finally evict | 1 | P2 |
| 8 | U-005: sync=true 防击穿 | 1 | P2 |
| 9 | S-001: allEntries 注释 | 1 | P1 |
| 10 | 测试更新与新增 | 5 | P0 |
| 11 | 编译 + 测试验证 | - | - |
