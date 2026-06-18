# JM5 审阅问题修复与漏洞补丁

## 功能描述

### 解决了什么问题

JM5 阶段（缓存优化与功能完善）交付后由资深 Java 后端架构审阅工程师产出审阅报告，发现 **4 个 P0 严重数据隔离漏洞**、**3 个 P1/P2 重要问题**、**6 个 P2/P3 建议优化项**。本次任务逐一修复 P0/P1/P2 问题并补齐所有相关测试，使 JM5 达到生产级安全标准。

**核心问题**：`@Cacheable` 注解的语义是「缓存命中时方法体不执行」。JM5 中 4 个 `@Cacheable` 方法的内部 `validateDataIsolation` 校验在缓存命中时被绕过，导致用户 B 可命中用户 A 的缓存，读取/导出他人数据。这是一类系统性安全漏洞，本质上是 Spring Cache 语义理解不深所致。

### 实现了什么功能

1. **数据隔离漏洞修复（P0 ×4 + 延伸 ×1）**
   - B-001/B-005：`UserController` 新增 `validateUserIdMatch`，在调用 `@Cacheable` Service 前校验 `currentUserId == pathUserId`
   - B-003：`AnalysisController.getAnalysisResult` 调用 `validateAnalysisAccess` 校验 `analysisId` 归属
   - B-004：`SessionController.getSessionDetail` 调用 `validateSessionAccess` 校验 `sessionId` 归属
   - **B-003 延伸（新发现）**：`AnalysisController.exportAnalysis` 也调用 `validateAnalysisAccess`，防止用户 B 通过缓存命中导出用户 A 的 PDF/Word 报告

2. **缓存 Key 完整性修复（P0 ×1）**
   - B-002：`FavoriteService.listFavorites` 缓存 Key 从 `#userId` 扩展为 `RedisKeyUtil.favoriteListKey(#userId, #page, #size)`，避免不同分页查询命中同一缓存
   - 配套：`addFavorite`/`removeFavorite` 改用 `allEntries=true` 清空整个 `favoriteList` 缓存空间（折衷方案）

3. **JSON 注入防护（P1）**
   - S-003：`PaperRepositoryCustomImpl` SQL 的 `CONCAT('"', ?6, '"')` 改为 `JSON_QUOTE(?6)`，自动转义特殊字符

4. **缓存策略优化（P1/P2）**
   - S-001：`SessionService.createSession` 的 `allEntries=true` 添加设计决策注释
   - U-002：`PaperService.searchPapers` 抛 `BusinessException` 替代 `IllegalArgumentException`
   - U-003：`AnalysisService` 三处编排方法（analyzePaper/comparePapers/generateReport）改为 `try-finally` evict，确保缓存一致性
   - U-005：`PaperService` 热点 key（`listPapers`/`getPaperDetail`/`searchPapers`）添加 `sync=true` 防缓存击穿

5. **测试体系补全**
   - 新增 Jm5IntegrationTest 数据隔离测试用例 JM5-9/10/11
   - 修复 4 个测试文件中因校验上移导致的 8 个失败测试
   - 修复 2 个间接关联的测试（CachePenetrationAvalancheTest + PaperServiceSearchTest）

### 业务价值

- **安全性**：4 个 P0 数据隔离漏洞全部关闭，用户无法通过缓存命中绕过权限校验
- **功能正确性**：收藏列表分页查询彻底修复，不同 page/size 不再互相干扰
- **稳定性**：缓存防击穿（sync=true）+ 防雪崩（allEntries=true 折衷）+ 一致性（try-finally）三层防护
- **可维护性**：测试匹配新架构（Controller 层校验 + Service 信任入参），所有 445 个测试通过

## 实现逻辑

### 修改的核心文件列表

**源代码（1 个文件）**

| 文件 | 变更 |
|------|------|
| [AnalysisController.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/main/java/com/literatureassistant/controller/AnalysisController.java) | `exportAnalysis` 添加 `validateAnalysisAccess` 调用，修复 B-003 延伸漏洞 |

> 其余源代码修复在上一轮「JM5 审阅报告问题修复计划」中已完成，本轮聚焦测试修复 + 新漏洞补丁。

**测试文件（7 个文件）**

| 文件 | 变更 |
|------|------|
| [UserServiceProfileTest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/test/java/com/literatureassistant/service/UserServiceProfileTest.java) | 删除 2 个失效测试（B-001 校验已上移，Service 不再校验） |
| [UserControllerTest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/test/java/com/literatureassistant/controller/UserControllerTest.java) | 修改 2 个数据隔离测试：设置 SecurityContext + 移除 Service Mock；新增 `@BeforeEach`/`@AfterEach` 管理 SecurityContext |
| [AnalysisServiceQueryTest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/test/java/com/literatureassistant/service/AnalysisServiceQueryTest.java) | 移除 2 个测试中不再需要的 `sessionRepository` Mock + 删除 1 个失效测试 |
| [SessionServiceTest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/test/java/com/literatureassistant/service/SessionServiceTest.java) | 删除 2 个失效测试（B-004 校验已上移，Service 不再校验） |
| [CachePenetrationAvalancheTest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/test/java/com/literatureassistant/cache/CachePenetrationAvalancheTest.java) | 修改 3 个测试以匹配 B-002 修复（allEntries=true + 复合 Key） |
| [PaperServiceSearchTest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/test/java/com/literatureassistant/service/PaperServiceSearchTest.java) | 修改 2 个测试以匹配 U-002 修复（BusinessException 替代 IllegalArgumentException） |
| [Jm5IntegrationTest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/test/java/com/literatureassistant/integration/Jm5IntegrationTest.java) | 新增 JM5-9/10/11 数据隔离集成测试用例（上一轮已完成） |

### 使用的设计模式 / 关键思路

**核心架构模式：Controller 层校验 + Service 层信任入参**

```
HTTP Request
    ↓
Controller（统一拦截）
    ├─ JWT 认证（@AuthenticationPrincipal / SecurityContextHolder）
    ├─ 数据隔离校验（validateUserIdMatch / validateXxxAccess）
    │    ↓ 通过
    └─ Service @Cacheable 方法（信任入参，不做二次校验）
         ↓
       Repository
```

**为什么不能在 Service 层做校验？**
- `@Cacheable` 命中时，**方法体不执行**，内部 `validateDataIsolation` 形同虚设
- 必须将校验上移到 Controller 层，确保每次请求都执行校验
- 校验方式分两类：
  - **path variable 是 userId 的**（如 `/api/users/{userId}/profile`）：Controller 直接比较 `pathUserId == currentUserId`
  - **path variable 是资源 ID 的**（如 `/api/analysis/{analysisId}`）：Controller 调用 Service 的 `validateXxxAccess` 公开方法查 DB 校验

**缓存 Key 完整性原则**
- 影响结果的所有参数必须出现在缓存 Key 中
- `listFavorites(userId, page, size)` 漏掉 `page`/`size` 会导致不同分页查询互相干扰
- 折衷方案：`addFavorite`/`removeFavorite` 使用 `allEntries=true` 清空整个缓存空间（TTL=10min 较短，影响可控）

### 关键代码逻辑

**UserController.validateUserIdMatch（B-001/B-005 修复）**
```java
private void validateUserIdMatch(String userId) {
    String currentUserId = extractCurrentUserId();
    if (currentUserId == null || currentUserId.isBlank()) {
        throw new AuthenticationException("未认证，请先登录");
    }
    if (!currentUserId.equals(userId)) {
        throw new BusinessException(403, "无权限访问他人数据", "FORBIDDEN_ACCESS");
    }
}
```

**AnalysisController.exportAnalysis 补丁（B-003 延伸）**
```java
// 修复 B-003 延伸: 导出前校验资源归属，防止 @Cacheable 缓存命中绕过数据隔离。
analysisService.validateAnalysisAccess(currentUserId, analysisId);
byte[] bytes = exportService.export(currentUserId, analysisId, format);
```

**FavoriteService.listFavorites Key 扩展（B-002 修复）**
```java
@Cacheable(value = "favoriteList",
        key = "T(com.literatureassistant.util.RedisKeyUtil).favoriteListKey(#userId, #page, #size)",
        unless = "#result == null")
public PageResponse<FavoriteResponse> listFavorites(String userId, int page, int size) { ... }
```

**PaperRepositoryCustomImpl JSON 注入防护（S-003 修复）**
```sql
-- 修复前: AND (?6 IS NULL OR JSON_CONTAINS(keywords, CONCAT('"', ?6, '"')))
-- 修复后:
AND (?6 IS NULL OR JSON_CONTAINS(keywords, JSON_QUOTE(?6)))
```

**AnalysisService try-finally evict（U-003 修复）**
```java
AnalysisTaskResponse response;
try {
    response = analysisTransactionService.completeAnalysis(pending.getId(), result);
} finally {
    evictAnalysisResultCache(analysisId);  // 无论是否抛异常都 evict
}
```

## 接口变更

本任务无新接口，修复的是现有 GET 端点的内部校验逻辑。具体涉及：

### 接口 1: GET /api/users/{userId}
- **变更**：Controller 层新增 `validateUserIdMatch` 校验
- **行为变化**：用户 B 调用此接口访问用户 A 资料时，返回 403（之前可能返回缓存的用户 A 数据）

### 接口 2: GET /api/users/{userId}/profile
- **变更**：Controller 层新增 `validateUserIdMatch` 校验
- **行为变化**：用户 B 调用此接口访问用户 A 画像时，返回 403（之前缓存命中会绕过校验）

### 接口 3: GET /api/analysis/{analysisId}
- **变更**：Controller 层先调用 `validateAnalysisAccess` 校验，再调用 `getAnalysisResult`
- **行为变化**：用户 B 调用此接口访问用户 A 分析结果时，返回 403（之前缓存命中会绕过校验）

### 接口 4: GET /api/sessions/{sessionId}
- **变更**：Controller 层先调用 `validateSessionAccess` 校验，再调用 `getSessionDetail`
- **行为变化**：用户 B 调用此接口访问用户 A 会话详情时，返回 403（之前缓存命中会绕过校验）

### 接口 5: GET /api/analysis/{analysisId}/export（本轮新发现 B-003 延伸）
- **变更**：Controller 层添加 `validateAnalysisAccess` 校验
- **行为变化**：用户 B 调用此接口导出用户 A 分析结果时，返回 403（之前缓存命中会绕过校验，泄露报告内容）

### 接口 6: GET /api/papers/favorites
- **变更**：`listFavorites` 缓存 Key 包含 page/size，`addFavorite`/`removeFavorite` 改用 `allEntries=true`
- **行为变化**：不同分页查询不再互相干扰；新增/取消收藏会清空整个 `favoriteList` 缓存空间（TTL=10min）

### 统一响应格式

```json
// 成功
{
  "code": 200,
  "message": "success",
  "data": { ... },
  "timestamp": "2026-06-17T17:00:00Z"
}

// 数据隔离违规（修复后）
{
  "code": 403,
  "message": "无权限访问他人数据",
  "data": null,
  "timestamp": "2026-06-17T17:00:00Z"
}
```

## 测试结果

### 单元测试与集成测试

| 验证项 | 结果 |
|--------|------|
| `mvn compile` | ✅ 通过 |
| `mvn test`（全部 445 个测试） | ✅ **通过**（0 失败，0 错误） |

### 重点测试场景

| # | 测试场景 | 文件 | 结果 |
|---|---------|------|------|
| JM5-1 | 收藏论文 POST 返回 200 + FavoriteResponse | Jm5IntegrationTest | ✅ |
| JM5-2 | 取消收藏 DELETE 返回 200 | Jm5IntegrationTest | ✅ |
| JM5-3 | 收藏列表 GET 返回分页 PageResponse | Jm5IntegrationTest | ✅ |
| JM5-4 | PDF 导出返回 application/pdf | Jm5IntegrationTest | ✅ |
| JM5-5 | Word 导出返回 docx MIME | Jm5IntegrationTest | ✅ |
| JM5-6 | docx 别名路由到 WordExporter | Jm5IntegrationTest | ✅ |
| JM5-7 | 未认证导出返回 401 | Jm5IntegrationTest | ✅ |
| JM5-8 | 不支持的导出格式返回 400 | Jm5IntegrationTest | ✅ |
| **JM5-9** | **用户 B 访问用户 A 分析结果返回 403（B-003 修复验证）** | Jm5IntegrationTest | ✅ |
| JM5-10 | 用户 A 访问自己的分析结果返回 200 | Jm5IntegrationTest | ✅ |
| JM5-11 | 未认证访问分析结果返回 401 | Jm5IntegrationTest | ✅ |
| 新增 | 用户 B 访问用户 A 资料返回 403（B-001/B-005 修复验证） | UserControllerTest | ✅ |
| 新增 | 用户 B 访问用户 A 画像返回 403（B-001 修复验证） | UserControllerTest | ✅ |
| 新增 | SQL keywords 过滤使用 JSON_QUOTE 防注入（S-003 修复验证） | PaperRepositoryFilterSortTest | ✅ |
| 新增 | listFavorites Key 含 page/size + allEntries=true（B-002 修复验证） | CacheConsistencyTest / CachePenetrationAvalancheTest | ✅ |
| 新增 | searchPapers q 为 null 抛 BusinessException（U-002 修复验证） | PaperServiceSearchTest | ✅ |
| 新增 | searchPapers q 为空白抛 BusinessException（U-002 修复验证） | PaperServiceSearchTest | ✅ |
| 新增 | try-finally evict 保证缓存一致性（U-003 修复验证） | AnalysisServiceQueryTest | ✅ |

### 数据隔离攻击路径验证（手动）

| 攻击路径 | 修复前 | 修复后 |
|---------|--------|--------|
| 用户 B 调用 `GET /api/users/uA/profile` | 命中缓存返回用户 A 画像 | ✅ 返回 403 |
| 用户 B 调用 `GET /api/analysis/anl_A` | 命中缓存返回用户 A 分析结果 | ✅ 返回 403 |
| 用户 B 调用 `GET /api/sessions/ses_A` | 命中缓存返回用户 A 会话详情 | ✅ 返回 403 |
| 用户 B 调用 `GET /api/analysis/anl_A/export?format=pdf` | 命中缓存导出用户 A 报告 | ✅ 返回 403 |

## 相关文件

### 源代码文件
- [AnalysisController.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/main/java/com/literatureassistant/controller/AnalysisController.java) — `exportAnalysis` 添加 `validateAnalysisAccess` 调用

### 测试文件
- [UserServiceProfileTest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/test/java/com/literatureassistant/service/UserServiceProfileTest.java)
- [UserControllerTest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/test/java/com/literatureassistant/controller/UserControllerTest.java)
- [AnalysisServiceQueryTest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/test/java/com/literatureassistant/service/AnalysisServiceQueryTest.java)
- [SessionServiceTest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/test/java/com/literatureassistant/service/SessionServiceTest.java)
- [CachePenetrationAvalancheTest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/test/java/com/literatureassistant/cache/CachePenetrationAvalancheTest.java)
- [PaperServiceSearchTest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/test/java/com/literatureassistant/service/PaperServiceSearchTest.java)
- [Jm5IntegrationTest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/test/java/com/literatureassistant/integration/Jm5IntegrationTest.java)

### 过程产物
- [JM5-缓存优化与功能完善-审阅报告.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/log/阶段审阅报告/backend/JM5-缓存优化与功能完善-审阅报告.md) — 审阅原始报告（4 个 P0 + 3 个 P1/P2 + 6 个 P2/P3）
- [JM5-审阅报告问题修复计划.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/.trae/documents/JM5-审阅报告问题修复计划.md) — 上一轮源代码修复计划
- [JM5-审阅报告问题修复计划-续.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/.trae/documents/JM5-审阅报告问题修复计划-续.md) — 本轮测试修复 + ExportService 漏洞补丁计划