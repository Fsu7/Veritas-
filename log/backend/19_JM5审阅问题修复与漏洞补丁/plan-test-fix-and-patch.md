# JM5 审阅报告问题修复计划（续）— 测试修复 + ExportService 漏洞补丁

## Summary

接续上一轮修复工作。源代码层面的 10 项修复（B-001/B-005、B-002、B-003、B-004、S-001、S-003、U-002、U-003、U-005）已全部完成。本计划聚焦于剩余的两类工作：

1. **修复 4 个测试文件中的 8 个失败测试** — 因数据隔离校验从 Service 层上移到 Controller 层，导致现有测试的 Mock 不再被调用或期望异常不再抛出。
2. **补丁新发现的 ExportService 数据隔离漏洞** — `ExportService.getValidatedResult` 调用 `@Cacheable` 方法 `getAnalysisResult`，缓存命中时数据隔离校验被绕过（B-003 的延伸）。

**修复范围**: 1 个源文件（AnalysisController）+ 4 个测试文件
**修复策略**: 测试匹配新架构（校验在 Controller 层）+ ExportService 端点补齐 `validateAnalysisAccess` 调用

---

## Current State Analysis

### 已完成的源代码修复（无需再动）

| 编号 | 修复内容 | 文件 | 状态 |
|------|---------|------|------|
| B-001/B-005 | UserService.getProfile/getUserInfo 数据隔离 → Controller 层校验 | UserController.java + UserService.java | ✅ 已完成 |
| B-002 | FavoriteService.listFavorites 缓存 Key 缺分页参数 → 复合 Key + allEntries=true | FavoriteService.java + RedisKeyUtil.java | ✅ 已完成 |
| B-003 | AnalysisService.getAnalysisResult 数据隔离 → Controller 层调用 validateAnalysisAccess | AnalysisController.java + AnalysisService.java | ✅ 已完成 |
| B-004 | SessionService.getSessionDetail 数据隔离 → Controller 层调用 validateSessionAccess | SessionController.java + SessionService.java | ✅ 已完成 |
| S-001 | SessionService.createSession allEntries=true → 添加注释说明 | SessionService.java | ✅ 已完成 |
| S-003 | PaperRepositoryCustomImpl JSON 注入 → JSON_QUOTE | PaperRepositoryCustomImpl.java | ✅ 已完成 |
| U-002 | PaperService.searchPapers 异常类型 → BusinessException | PaperService.java | ✅ 已完成 |
| U-003 | AnalysisService 三处编排方法 → try-finally evict | AnalysisService.java | ✅ 已完成 |
| U-005 | PaperService 热点 key → sync=true | PaperService.java | ✅ 已完成 |

### 已完成的测试修复（无需再动）

| 测试文件 | 修复内容 | 状态 |
|---------|---------|------|
| FavoriteServiceTest.java | 验证 allEntries=true + Key 含 page/size | ✅ 已完成 |
| CacheConsistencyTest.java | 验证 allEntries=true + Key 含 page/size | ✅ 已完成 |
| PaperRepositoryFilterSortTest.java | 验证 JSON_QUOTE | ✅ 已完成 |
| Jm5IntegrationTest.java | 新增 JM5-9/10/11 数据隔离测试用例 | ✅ 已完成 |

### 待修复的测试（4 个文件，8 个测试）

#### 1. UserServiceProfileTest.java（2 个测试失败）

**根因**: Service 内部 `validateDataIsolation` 已移除（B-001 修复），但测试仍期望 Service 抛认证/越权异常。

| 测试方法 | 行号 | 失败原因 |
|---------|------|---------|
| `getProfile_notAuthenticated_throwsAuthenticationException` | 132-138 | 期望 Service 抛 AuthenticationException，但 Service 内部校验已移除，现在抛 ResourceNotFoundException（因为 SecurityContext 为空时 userProfileRepository.findByUserId 仍被调用） |
| `getProfile_forbiddenAccess_throwsBusinessException` | 142-149 | 期望 Service 抛 BusinessException(403)，但 Service 内部校验已移除 |

#### 2. UserControllerTest.java（2 个测试失败）

**根因**: Controller 层 `validateUserIdMatch` 直接抛异常，不会调用 Service，导致 Mock 的 `userService.getUserInfo`/`userService.getProfile` 抛异常不被调用（UnnecessaryStubbing）。且测试未设置 SecurityContext，Controller 层会抛 AuthenticationException(401) 而非 BusinessException(403)。

| 测试方法 | 行号 | 失败原因 |
|---------|------|---------|
| `getUserInfo_isolation_userBAccessUserA_returns403` | 228-236 | UnnecessaryStubbing + 未设置 SecurityContext |
| `getProfile_isolation_userBAccessUserA_returns403` | 239-247 | 同上 |

#### 3. AnalysisServiceQueryTest.java（3 个测试失败）

**根因**: Service 内部 `validateDataIsolation` 已移除（B-003 修复），`sessionRepository.findBySessionId` 不再被 `getAnalysisResult` 调用。

| 测试方法 | 行号 | 失败原因 |
|---------|------|---------|
| `getAnalysisResult_returns_dto_with_deserialized_result` | 116-137 | UnnecessaryStubbing — `sessionRepository.findBySessionId` Mock 不再被调用 |
| `getAnalysisResult_uses_cache_second_call` | 140-153 | 同上 |
| `getAnalysisResult_other_user_returns403` | 156-165 | Service 内部不再校验数据隔离，无法抛 403 |

#### 4. SessionServiceTest.java（2 个测试失败）

**根因**: Service 内部 `validateDataIsolation` 已移除（B-004 修复），但测试仍期望 Service 抛认证/越权异常。

| 测试方法 | 行号 | 失败原因 |
|---------|------|---------|
| `getSessionDetail_dataIsolationViolation_throws403` | 227-236 | 期望 Service 抛 BusinessException(403)，但 Service 内部校验已移除 |
| `getSessionDetail_unauthenticated_throws401` | 333-343 | 期望 Service 抛 AuthenticationException，但 Service 内部校验已移除 |

### 新发现：ExportService 数据隔离漏洞（B-003 延伸）

**文件**: `AnalysisController.java` 的 `exportAnalysis` 方法（行 166-191）
**文件**: `ExportService.java` 的 `getValidatedResult` 方法（行 96-106）

**问题描述**:
```java
// AnalysisController.exportAnalysis（当前代码）
@GetMapping("/{analysisId}/export")
public ResponseEntity<byte[]> exportAnalysis(...) {
    String currentUserId = ...;
    // ❌ 缺少 validateAnalysisAccess 调用！
    byte[] bytes = exportService.export(currentUserId, analysisId, format);
    ...
}

// ExportService.getValidatedResult
private AnalysisResultDTO getValidatedResult(String userId, String analysisId) {
    AnalysisResponse resp = analysisService.getAnalysisResult(userId, analysisId);  // ← @Cacheable 方法，缓存命中时校验被绕过
    ...
}
```

**攻击路径**:
1. 用户 A 调用 `GET /api/analysis/anl_A/export?format=pdf` → 缓存未命中 → `getAnalysisResult` 执行 → 缓存 key=`anl_A` 写入
2. 用户 B 调用 `GET /api/analysis/anl_A/export?format=pdf` → **缓存命中** → `getAnalysisResult` 直接返回用户 A 的分析结果 → 导出用户 A 的 PDF

**影响**: 用户 B 可导出任意 analysisId 的 PDF/Word 报告，泄露他人研究内容。

**修复方案**: 在 `AnalysisController.exportAnalysis` 中添加 `validateAnalysisAccess` 调用（与 `getAnalysisResult` 端点保持一致）。

---

## Proposed Changes

### 1. 修复 ExportService 数据隔离漏洞（B-003 延伸）

**文件**: `backend/src/main/java/com/literatureassistant/controller/AnalysisController.java`

**What**: 在 `exportAnalysis` 方法中添加 `validateAnalysisAccess` 调用

**Why**: `ExportService.getValidatedResult` 调用 `@Cacheable` 方法 `getAnalysisResult`，缓存命中时数据隔离校验被绕过，用户 B 可导出用户 A 的报告

**How**:

```java
@GetMapping("/{analysisId}/export")
public ResponseEntity<byte[]> exportAnalysis(
        @PathVariable String analysisId,
        @RequestParam(defaultValue = "pdf") String format,
        @AuthenticationPrincipal String userId) {
    String currentUserId = userId != null ? userId : extractCurrentUserId();
    if (currentUserId == null || currentUserId.isBlank()) {
        throw new AuthenticationException("未认证，请先登录");
    }
    log.info("REST exportAnalysis: userId={}, analysisId={}, format={}", currentUserId, analysisId, format);
    // 修复 B-003 延伸: 导出前校验资源归属，防止缓存命中绕过数据隔离
    analysisService.validateAnalysisAccess(currentUserId, analysisId);
    byte[] bytes = exportService.export(currentUserId, analysisId, format);
    ...
}
```

---

### 2. 修复 UserServiceProfileTest.java

**文件**: `backend/src/test/java/com/literatureassistant/service/UserServiceProfileTest.java`

**What**: 删除 2 个测试方法（数据隔离校验已上移到 Controller，Service 层不再负责认证/越权校验）

**Why**: Service 内部 `validateDataIsolation` 已移除（B-001 修复），这两个测试期望的异常不再抛出

**How**: 删除以下两个测试方法：
- `getProfile_notAuthenticated_throwsAuthenticationException`（行 130-138）
- `getProfile_forbiddenAccess_throwsBusinessException`（行 140-149）

同时移除不再使用的 import（如果有）：
- `com.literatureassistant.exception.AuthenticationException`（如果不再使用）
- `com.literatureassistant.exception.BusinessException`（如果不再使用）

**说明**: 数据隔离测试已由 `UserControllerTest` 和 `Jm5IntegrationTest` 覆盖。

---

### 3. 修复 UserControllerTest.java

**文件**: `backend/src/test/java/com/literatureassistant/controller/UserControllerTest.java`

**What**: 修改 2 个数据隔离测试，设置 SecurityContext 为用户 B，移除不再需要的 Service Mock

**Why**: Controller 层 `validateUserIdMatch` 直接抛异常，不会调用 Service，导致 Mock 不被调用（UnnecessaryStubbing）

**How**:

需要新增 import:
```java
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import java.util.List;
```

修改 `getUserInfo_isolation_userBAccessUserA_returns403`（行 227-236）:
```java
@Test
@DisplayName("GET /api/users/{userId} - 数据隔离: 用户B无法访问用户A的资料（Controller 层校验返回403）")
void getUserInfo_isolation_userBAccessUserA_returns403() throws Exception {
    // 设置 SecurityContext 为用户 B
    SecurityContextHolder.getContext().setAuthentication(
            new UsernamePasswordAuthenticationToken("usr_userB", null, List.of()));

    // 不再 Mock userService.getUserInfo — Controller 层 validateUserIdMatch 会直接抛 403
    mockMvc.perform(get("/api/users/usr_userA"))
            .andExpect(status().isForbidden())
            .andExpect(jsonPath("$.code").value(403));
}
```

修改 `getProfile_isolation_userBAccessUserA_returns403`（行 238-247）:
```java
@Test
@DisplayName("GET /api/users/{userId}/profile - 数据隔离: 用户B无法访问用户A的画像（Controller 层校验返回403）")
void getProfile_isolation_userBAccessUserA_returns403() throws Exception {
    // 设置 SecurityContext 为用户 B
    SecurityContextHolder.getContext().setAuthentication(
            new UsernamePasswordAuthenticationToken("usr_userB", null, List.of()));

    // 不再 Mock userService.getProfile — Controller 层 validateUserIdMatch 会直接抛 403
    mockMvc.perform(get("/api/users/usr_userA/profile"))
            .andExpect(status().isForbidden())
            .andExpect(jsonPath("$.code").value(403));
}
```

**注意**: 测试结束后需要清理 SecurityContext，可在 `@AfterEach` 中添加 `SecurityContextHolder.clearContext()`。

---

### 4. 修复 AnalysisServiceQueryTest.java

**文件**: `backend/src/test/java/com/literatureassistant/service/AnalysisServiceQueryTest.java`

**What**: 移除 2 个测试中不再需要的 `sessionRepository` Mock，删除 1 个不再适用的数据隔离测试

**Why**: Service 内部 `validateDataIsolation` 已移除（B-003 修复），`sessionRepository.findBySessionId` 不再被 `getAnalysisResult` 调用

**How**:

修改 `getAnalysisResult_returns_dto_with_deserialized_result`（行 116-137）:
- 移除 `when(sessionRepository.findBySessionId(SESSION_ID)).thenReturn(Optional.of(buildSession(CURRENT_USER_ID)))` 这一行

修改 `getAnalysisResult_uses_cache_second_call`（行 140-153）:
- 移除 `when(sessionRepository.findBySessionId(SESSION_ID)).thenReturn(Optional.of(buildSession(CURRENT_USER_ID)))` 这一行

删除 `getAnalysisResult_other_user_returns403`（行 155-165）:
- Service 内部不再校验数据隔离，此测试场景已由 `Jm5IntegrationTest.testGetAnalysisResultDataIsolation`（JM5-9）覆盖

**说明**: `getAnalysisStatus` 相关测试（行 171-212）仍需要 `sessionRepository` Mock，因为 `getAnalysisStatus` 方法内部仍然调用 `validateDataIsolation`（该方法不是 `@Cacheable` 方法，校验不会被绕过）。

---

### 5. 修复 SessionServiceTest.java

**文件**: `backend/src/test/java/com/literatureassistant/service/SessionServiceTest.java`

**What**: 删除 2 个测试方法（数据隔离校验已上移到 Controller，Service 层不再负责认证/越权校验）

**Why**: Service 内部 `validateDataIsolation` 已移除（B-004 修复），这两个测试期望的异常不再抛出

**How**: 删除以下两个测试方法：
- `getSessionDetail_dataIsolationViolation_throws403`（行 226-236）
- `getSessionDetail_unauthenticated_throws401`（行 333-343）

**说明**: 数据隔离测试已由 `SessionControllerTest` 和 `Jm5IntegrationTest` 覆盖。

---

### 6. 修复 SessionControllerTest.java（可选，提升测试严谨性）

**文件**: `backend/src/test/java/com/literatureassistant/controller/SessionControllerTest.java`

**What**: 修改 1 个数据隔离测试，设置 SecurityContext，Mock `validateSessionAccess` 抛异常

**Why**: 当前测试 Mock `sessionService.getSessionDetail` 抛异常，但 Controller 层会先调用 `validateSessionAccess`，测试逻辑不够严谨

**How**:

需要新增 import:
```java
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import java.util.List;
```

修改 `getSessionDetail_isolation_userBAccessUserA_returns403`（行 191-200）:
```java
@Test
@DisplayName("数据隔离: 用户B查询用户A的会话详情, validateSessionAccess 抛403 -> Controller 返回403")
void getSessionDetail_isolation_userBAccessUserA_returns403() throws Exception {
    // 设置 SecurityContext 为用户 B
    SecurityContextHolder.getContext().setAuthentication(
            new UsernamePasswordAuthenticationToken("usr_userB", null, List.of()));

    // Mock validateSessionAccess 抛 403（Controller 层先校验，校验失败不调用 getSessionDetail）
    doThrow(new BusinessException(403, "无权限访问他人会话", "FORBIDDEN_ACCESS"))
            .when(sessionService).validateSessionAccess("usr_userB", "ses_userA");

    mockMvc.perform(get("/api/sessions/ses_userA"))
            .andExpect(status().isForbidden())
            .andExpect(jsonPath("$.code").value(403));

    verify(sessionService).validateSessionAccess("usr_userB", "ses_userA");
    verify(sessionService, never()).getSessionDetail(anyString());
}
```

**注意**: 需要新增 `import static org.mockito.Mockito.never;` 和 `import static org.mockito.ArgumentMatchers.anyString;`（如果不存在）。

同时修改 `getSessionDetail_success`（行 133-152），添加 `doNothing().when(sessionService).validateSessionAccess(anyString(), anyString())` Mock，因为 Controller 现在会先调用 `validateSessionAccess`。

---

## Assumptions & Decisions

### 假设
1. `validateAnalysisAccess` (AnalysisService.java:379) 已是 public 方法，无需修改可见性
2. `validateSessionAccess` (SessionService.java:124) 已是 public 方法，无需修改可见性
3. MockitoExtension 默认 strict stubbing，未使用的 Mock 会报 UnnecessaryStubbing
4. `SecurityContextHolder` 在 MockMvc standaloneSetup 中可用（不依赖 Spring Security filter chain）

### 决策
1. **删除 vs 修改测试**: 对于 Service 层不再负责的校验（认证/越权），直接删除测试，因为数据隔离测试已由 Controller 测试和集成测试覆盖
2. **ExportService 漏洞修复**: 在 Controller 层添加 `validateAnalysisAccess` 调用，与 `getAnalysisResult` 端点保持一致
3. **SessionControllerTest 修复**: 标记为可选，因为当前测试能通过（Mock 行为巧合），但逻辑不严谨

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
- `UserServiceProfileTest`: 验证删除 2 个测试后剩余测试通过
- `UserControllerTest`: 验证修改后的 2 个数据隔离测试通过
- `AnalysisServiceQueryTest`: 验证修改后的测试通过（移除 sessionRepository Mock + 删除 other_user 测试）
- `SessionServiceTest`: 验证删除 2 个测试后剩余测试通过
- `SessionControllerTest`: 验证修改后的数据隔离测试通过（可选）
- `FavoriteServiceTest` / `CacheConsistencyTest` / `PaperRepositoryFilterSortTest` / `Jm5IntegrationTest`: 验证已修复的测试仍通过

### 3. 集成测试
```bash
cd Veritas/backend && mvn test -Dtest=Jm5IntegrationTest -q
```

### 4. 代码审查清单
- [ ] `AnalysisController.exportAnalysis` 添加 `validateAnalysisAccess` 调用
- [ ] `UserServiceProfileTest` 删除 2 个失效测试
- [ ] `UserControllerTest` 修改 2 个数据隔离测试（设置 SecurityContext + 移除 Service Mock）
- [ ] `AnalysisServiceQueryTest` 移除 2 个测试的 sessionRepository Mock + 删除 1 个失效测试
- [ ] `SessionServiceTest` 删除 2 个失效测试
- [ ] `SessionControllerTest` 修改数据隔离测试（可选）
- [ ] `mvn test` 全部通过

---

## 修复优先级与执行顺序

| 顺序 | 任务 | 文件数 | 优先级 |
|------|------|--------|--------|
| 1 | ExportService 数据隔离漏洞补丁（AnalysisController.exportAnalysis） | 1 | P0 |
| 2 | 修复 UserServiceProfileTest（删除 2 个失效测试） | 1 | P0 |
| 3 | 修复 UserControllerTest（修改 2 个数据隔离测试） | 1 | P0 |
| 4 | 修复 AnalysisServiceQueryTest（移除 Mock + 删除失效测试） | 1 | P0 |
| 5 | 修复 SessionServiceTest（删除 2 个失效测试） | 1 | P0 |
| 6 | 修复 SessionControllerTest（可选，提升测试严谨性） | 1 | P1 |
| 7 | 编译 + 测试验证 | - | - |
