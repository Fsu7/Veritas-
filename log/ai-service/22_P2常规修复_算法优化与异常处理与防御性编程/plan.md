# P2 常规修复计划

> **来源**: [修复清单-2-常规(P2).md](file:///Users/achieve/Library/Mobile%20Documents/com%7Eapple%7ECloudDocs/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/修复清单-2-常规(P2).md)
> **条目数**: 17 项（16 主项 + 1 附录项）
> **决策**: Spring Boot 升级至 3.2.12（用户确认）

---

## 修复顺序

按依赖关系和风险分 4 批：
1. **Python 独立修复**（10 项）— 无跨文件依赖
2. **Java 独立修复**（4 项）— 无跨文件依赖
3. **配置修复**（2 项）— pom.xml + requirements.txt
4. **API 契约修复**（1 项）— Session 幂等性

---

## 批次 1：Python 独立修复（10 项）

### 1.1 [P2#1] search_service.py `_tokenize_query` List 去重 → Set

**文件**: `ai-service/app/services/search_service.py` 行 79-100
**当前**: `token_lower not in tokens`（List 线性查找 O(n)）
**修复**: 在 `_tokenize_query` 方法内增加 `seen: set` 辅助去重

```python
# 行 74 前增加
seen_tokens: set = set()

# 行 79 改为
if token_lower not in STOP_WORDS and token_lower not in seen_tokens:
    seen_tokens.add(token_lower)
    tokens.append(token_lower)

# 行 85 同理改为 seen_tokens
# 行 100 bigram 去重同理
```

**注意**: 需在英文 token 循环(行79,85)和中文 bigram 循环(行100)三处都改。但 `seen_tokens` 应跨英文和中文共享（避免英文 token 与中文 bigram 重复），初始化在方法开头。

### 1.2 [P2#2] vector_store_service.py 旧关键词检索路径删除

**文件**: `ai-service/app/services/vector_store_service.py` 行 375-414
**当前**: `tokens is None and phrases is None` 时走旧逐关键词查询路径
**修复**: 删除旧路径(行375-414)，在入口处(行276-287)将 `tokens is None and phrases is None` 的情况统一导向新 `$or` 查询路径

具体：将行276-287的 `use_or_query` 判断逻辑改为始终走新路径。当 `tokens` 和 `phrases` 都为 None 时，用 `query_text.split()` 生成 tokens 作为默认值。

### 1.3 [P2#3] llm_service.py LocalLLMProvider 线程泄漏

**文件**: `ai-service/app/services/llm_service.py` 行 229-255
**当前**: 非 daemon 线程，join 不在 finally 中
**修复**:
1. 行229: `thread = threading.Thread(target=..., daemon=True)`
2. 行242: `enqueue_thread = threading.Thread(target=_enqueue, daemon=True)`
3. 行245-255: 用 try/finally 包裹消费循环，finally 中执行带 timeout 的 join

```python
thread = threading.Thread(target=self.model.generate, kwargs=generation_kwargs, daemon=True)
thread.start()
# ... enqueue_thread 同理 daemon=True ...
try:
    loop = asyncio.get_running_loop()  # 同时修复 get_event_loop 弃用问题
    while not finished.is_set() or not text_queue.empty():
        # ... 消费循环 ...
finally:
    thread.join(timeout=5)
    enqueue_thread.join(timeout=5)
```

### 1.4 [P2#4] asyncio.gather 缺少 return_exceptions

**文件 A**: `ai-service/app/services/search_service.py` 行 244-247
**修复**:
```python
semantic_results_raw, keyword_results_raw = await asyncio.gather(
    self.search(query, top_k=candidate_k, filters=filters),
    self.keyword_search(query, top_k=candidate_k, filters=filters),
    return_exceptions=True,
)
# 过滤异常结果
semantic_results = semantic_results_raw if isinstance(semantic_results_raw, list) else []
keyword_results = keyword_results_raw if isinstance(keyword_results_raw, list) else []
if not isinstance(semantic_results_raw, list):
    logger.warning(f"Semantic search failed in gather: {semantic_results_raw}")
if not isinstance(keyword_results_raw, list):
    logger.warning(f"Keyword search failed in gather: {keyword_results_raw}")
```

**文件 B**: `ai-service/app/agents/analyzer.py` 行 85
**修复**: 添加 `return_exceptions=True`，在后续处理中检查每个结果是否为 Exception 实例
```python
gathered_raw = await asyncio.gather(*tasks, return_exceptions=True)
gathered = []
for item in gathered_raw:
    if isinstance(item, Exception):
        logger.warning(f"Analyze task failed in gather: {item}")
        gathered.append((0, None, None))  # 占位，后续按 idx 过滤
    else:
        gathered.append(item)
```
**注意**: 由于 `_analyze_paper_with_semaphore` 内部已有完整 try/except，gather 实际不会抛异常。但添加 `return_exceptions=True` 作为兜底防护。

### 1.5 [P2#5] search_service 级联降级双重静默

**文件**: `ai-service/app/services/search_service.py` 行 141-147, 182-190, 269-275
**当前**: 所有异常 catch 后返回 `[]`，调用方无法区分"无结果"与"出错"
**修复**: 在 SearchService 中增加 `_search_errors` 计数器属性，记录降级事件

```python
class SearchService:
    def __init__(self, ...):
        # ...
        self._degradation_count = 0  # 降级计数

    async def search(self, ...):
        try:
            # ...
        except Exception as e:
            self._degradation_count += 1
            logger.warning(f"Semantic search failed (degradation #{self._degradation_count}): ...")
            return []

    async def hybrid_search(self, ...):
        # ... gather 后检查两个结果是否都为空
        if not semantic_results and not keyword_results:
            logger.warning("Both semantic and keyword search returned empty - possible system degradation")
```

**设计决策**: 不改变返回值签名（保持 `List[dict]`），改用日志 + 计数器记录降级事件。这避免了修改所有调用方的签名。当两路都返回空时，输出明确的 warning 日志。

### 1.6 [P2#6] vector_store_service.update_paper_metadata 吞异常

**文件**: `ai-service/app/services/vector_store_service.py` 行 227-239
**当前**: catch Exception 后仅 warning，不 re-raise
**修复**: 移除 try/except，让异常自然传播。或保留 try 但 re-raise

```python
async def update_paper_metadata(self, paper_id: str, metadata: dict) -> None:
    if self.collection is None:
        raise RuntimeError("VectorStore not initialized")
    self.collection.update(ids=[paper_id], metadatas=[metadata])
    logger.info(f"Updated metadata for paper '{paper_id}'")
```

### 1.7 [P2#7] embedding_service.encode 降级异常信息用错

**文件**: `ai-service/app/services/embedding_service.py` 行 382-396
**当前**: 所有 fallback 失败后用 active provider 的原始错误 `e`
**修复**: 保留 `last_error` 变量

```python
except Exception as e:
    logger.warning(f"Active provider {self._provider_name} failed: {e}, trying fallbacks")
    last_error = e
    for fb in self.fallback_providers:
        try:
            result = await fb.embed_documents(texts)
            # ...
            return result
        except Exception as fb_err:
            last_error = fb_err
            logger.warning(f"Fallback provider {fb.name} also failed: {fb_err}")
            continue
    raise ModelNotLoadedException(f"All embedding providers failed, last error: {last_error}")
```

### 1.8 [P2#9] reranker.py year/citation_count 类型假设

**文件**: `ai-service/app/services/reranker.py` 行 74-75, 88, 90
**当前**: `or 0`/`or current_year` 不处理非数值字符串
**修复**: 添加类型转换守卫

```python
# 行 74-75 改为
raw_citation = result.get("citation_count", 0) or 0
raw_year = result.get("year", current_year) or current_year
try:
    citation_count = int(raw_citation)
except (ValueError, TypeError):
    citation_count = 0
try:
    paper_year = int(raw_year)
except (ValueError, TypeError):
    paper_year = current_year
```

### 1.9 [P2#10] reviewer.py fact_check 非 dict 守卫 + 默认值矛盾修复

**文件**: `ai-service/app/agents/reviewer.py` 行 245-249, 267-273
**当前**: 
1. 未做 `isinstance(item, dict)` 检查
2. `_calculate_fact_accuracy_from_result` 用 `item.get("accurate", False)` vs `_extract_issues` 用 `item.get("accurate", True)` — 默认值矛盾

**修复**:
1. 两处都添加 `isinstance(item, dict)` 守卫，跳过非 dict 元素
2. 统一默认值为 `False`（安全侧：未明确标记为准确的视为不准确）

```python
# _calculate_fact_accuracy_from_result (行 238-249)
def _calculate_fact_accuracy_from_result(self, parsed: dict) -> float:
    fact_check = parsed.get("fact_check", [])
    if not fact_check:
        return 0.0
    accurate_count = 0
    valid_count = 0
    for item in fact_check:
        if not isinstance(item, dict):
            continue
        valid_count += 1
        if item.get("accurate", False):
            accurate_count += 1
    if valid_count == 0:
        return 0.0
    return round(accurate_count / valid_count, 4)

# _extract_issues (行 263-283)
def _extract_issues(self, parsed: dict) -> List[dict]:
    issues: List[dict] = []
    fact_check = parsed.get("fact_check", [])
    for item in fact_check:
        if not isinstance(item, dict):
            continue
        if not item.get("accurate", False):  # 统一默认 False
            issues.append({
                "claim": item.get("claim", ""),
                "error_type": item.get("error_type", "factual_error"),
                "note": item.get("note", ""),
            })
    # citation_check 部分同理加 isinstance 守卫
    citation_check = parsed.get("citation_check", {})
    if isinstance(citation_check, dict):
        for item in citation_check.get("inaccurate_citations", []):
            if not isinstance(item, dict):
                continue
            issues.append({
                "citation": item.get("citation", ""),
                "error_type": item.get("error_type", "citation_error"),
                "issue": item.get("issue", ""),
            })
    return issues
```

### 1.10 [P2#11] vector_store_service.search 假设 ChromaDB 返回并行数组

**文件**: `ai-service/app/services/vector_store_service.py` 行 112-130
**当前**: 只检查 `results["ids"]`，直接索引 `distances`/`metadatas`/`documents`
**修复**: 添加防御性校验

```python
# 行 112 改为
ids_list = results.get("ids", [])
if not ids_list or not ids_list[0]:
    return []

ids = ids_list[0]
count = len(ids)
distances_list = results.get("distances", [[]])
metadatas_list = results.get("metadatas", [[]])
documents_list = results.get("documents", [[]])

distances = distances_list[0] if distances_list else []
metadatas = metadatas_list[0] if metadatas_list else []
documents = documents_list[0] if documents_list else []

for i in range(count):
    distance = distances[i] if i < len(distances) else 1.0
    metadata = metadatas[i] if i < len(metadatas) else {}
    document = documents[i] if i < len(documents) else ""
    # ... 格式化逻辑 ...
```

同样修复 `search_by_keywords` 新路径(行335-358)中的相同模式。

---

## 批次 2：Java 独立修复（4 项）

### 2.1 [P2#8] JwtUtil.java 安全事件日志级别

**文件**: `backend/.../util/JwtUtil.java` 行 65-84
**当前**: 所有异常用 `log.debug`
**修复**: 
- `SecurityException`（签名无效）→ `log.warn`
- `MalformedJwtException`（格式错误）→ `log.warn`
- `ExpiredJwtException`（过期）→ 保持 `log.debug`（正常业务事件）
- `UnsupportedJwtException` → 保持 `log.debug`
- `IllegalArgumentException`（空 token）→ 保持 `log.debug`

```java
} catch (ExpiredJwtException e) {
    log.debug("JWT token已过期: {}", maskToken(token));
} catch (MalformedJwtException e) {
    log.warn("JWT token格式错误: {}", maskToken(token));
} catch (SecurityException e) {
    log.warn("JWT签名无效: {}", maskToken(token));
} catch (UnsupportedJwtException e) {
    log.debug("不支持的JWT token: {}", maskToken(token));
} catch (IllegalArgumentException e) {
    log.debug("JWT token为空");
}
```

### 2.2 [P2#14] getAnalysisResult 重复查询 AnalysisResult

**文件**: `backend/.../controller/AnalysisController.java` 行 139-140, `backend/.../service/AnalysisService.java` 行 379-383
**当前**: `validateAnalysisAccess` 和 `getAnalysisResult` 各查一次 `findByAnalysisId`
**修复**: `validateAnalysisAccess` 改为返回 `AnalysisResult` 实体，`getAnalysisResult` 接收实体参数避免重复查询

**AnalysisService.java 修改**:
```java
// 行 379-383 改为
public AnalysisResult validateAnalysisAccess(String userId, String analysisId) {
    AnalysisResult entity = analysisResultRepository.findByAnalysisId(analysisId)
            .orElseThrow(() -> new ResourceNotFoundException("AnalysisResult", analysisId));
    validateDataIsolation(userId, entity.getSessionId());
    return entity;
}

// 行 238-254 改为新增重载方法
public AnalysisResponse getAnalysisResultFromEntity(AnalysisResult entity) {
    AnalysisResultDTO resultDto = deserializeResult(entity.getResult());
    return AnalysisResponse.builder()
            .analysisId(entity.getAnalysisId())
            .sessionId(entity.getSessionId())
            .status(entity.getStatus())
            .type(entity.getType())
            .result(resultDto)
            .createdAt(entity.getCreatedAt())
            .build();
}
// 原 getAnalysisResult(@Cacheable) 保留不变，用于缓存命中的快速路径
```

**AnalysisController.java 修改**:
```java
// 行 139-140 改为
AnalysisResult entity = analysisService.validateAnalysisAccess(currentUserId, analysisId);
AnalysisResponse response = analysisService.getAnalysisResult(currentUserId, analysisId);
// 注意：@Cacheable 命中时 getAnalysisResult 不查 DB；未命中时查 DB。
// validateAnalysisAccess 始终查 DB（安全校验不可省略）。
// 缓存命中时：1 次查询（validateAnalysisAccess）
// 缓存未命中时：2 次查询（validateAnalysisAccess + getAnalysisResult 内部）
// 这比之前的 3 次查询（validateAccess查AnalysisResult + validateDataIsolation查Session + getAnalysisResult再查AnalysisResult）减少了 1 次。
```

**设计决策**: 由于 `@Cacheable` 命中时方法体不执行，无法将缓存逻辑和校验逻辑合并到同一方法。保留 `@Cacheable` 的快速路径，同时减少缓存未命中时的重复查询。`getAnalysisResult` 仍保留 `@Cacheable` 以支持缓存命中时的零查询路径。

### 2.3 [P2#15] PaperRepositoryCustomImpl SELECT * + JSON LIKE

**文件**: `backend/.../repository/PaperRepositoryCustomImpl.java` 行 46-53
**当前**: `SELECT *` + `authors LIKE CONCAT('%', ?5, '%')`
**修复**:
1. `SELECT *` → 指定列（但 Paper 实体所有字段都可能被前端使用，需确认 PaperResponse 的字段映射）

**注意**: 经探索，`searchByKeyword` 返回 `Page<Paper>`（JPA 实体），不是 DTO。如果改为投影查询返回 Object[]，需要修改 Repository 接口签名和调用方代码。风险较大。

**保守方案**: 仅修复 `authors LIKE` → `JSON_CONTAINS`，`SELECT *` 保持不变（因为返回的是完整 Paper 实体，JPA 需要所有字段来构建实体对象）。

```java
// 行 52 改为
"AND (?5 IS NULL OR JSON_CONTAINS(authors, JSON_QUOTE(?5))) " +
```

**验证**: `authors` 列在 DDL 中是 `JSON` 类型（存储数组如 `["Author A", "Author B"]`）。`JSON_CONTAINS(authors, JSON_QUOTE(?5))` 会检查数组中是否包含匹配的作者名字符串。但注意 `JSON_QUOTE` 会给字符串加引号，如 `JSON_QUOTE('Author A')` → `"\"Author A\""`，然后 `JSON_CONTAINS(["Author A", "Author B"], "\"Author A\"")` → true。这是正确的用法。

但需注意：`LIKE '%xxx%'` 是模糊匹配，而 `JSON_CONTAINS` 是精确匹配。如果用户搜索 "Author"，`JSON_CONTAINS` 不会匹配 "Author A"。需要确认业务需求：
- 如果需要精确匹配作者名 → 用 `JSON_CONTAINS`
- 如果需要模糊搜索 → 用 `JSON_EXTRACT` + `LIKE`

**决策**: 保持 `LIKE` 模糊匹配但改用 `JSON_SEARCH` 或 `JSON_EXTRACT`：
```sql
AND (?5 IS NULL OR JSON_SEARCH(authors, 'one', CONCAT('%', ?5, '%')) IS NOT NULL)
```
但这仍然无法使用索引。最安全的方案：保持 `LIKE` 但明确标注为已知限制，等后续添加全文索引时优化。

**最终决策**: 仅将 `LIKE CONCAT('%', ?5, '%')` 改为 `JSON_SEARCH(authors, 'one', CONCAT('%', ?5, '%')) IS NOT NULL`。这至少利用了 MySQL 的 JSON 函数，语义更准确（在 JSON 数组内搜索而非整列文本匹配）。

### 2.4 [P2#16] @Cacheable 缓存击穿防护

**文件**: 6 个 `@Cacheable` 方法
**修复**: 为以下 6 个方法添加 `sync = true`：

| 文件 | 行号 | 方法 | 当前 | 修复后 |
|------|------|------|------|--------|
| AnalysisService.java | 238 | getAnalysisResult | 无 sync | `sync = true` |
| SessionService.java | 82 | listSessions | 无 sync | `sync = true` |
| SessionService.java | 107 | getSessionDetail | 无 sync | `sync = true` |
| FavoriteService.java | 132 | listFavorites | 无 sync | `sync = true` |
| UserService.java | 96 | getUserInfo | 无 sync | `sync = true` |
| UserService.java | 160 | getProfile | 无 sync | `sync = true` |

**缓存穿透**: `unless = "#result == null"` 保持不变。实现空值缓存需要自定义 `CacheInterceptor`，属于过度工程化。当前系统有 JWT 认证保护，恶意穿透风险低，暂不实现空值缓存。

---

## 批次 3：配置修复（2 项）

### 3.1 [P2#12] pom.xml Spring Boot 3.2.5 → 3.2.12

**文件**: `backend/pom.xml` 行 10
**修复**:
```xml
<!-- 行 10 -->
<version>3.2.12</version>
```

**验证**: `mvn dependency:tree` 确认 Spring Framework ≥ 6.1.13、Tomcat ≥ 10.1.24、Spring Security ≥ 6.2.8。

### 3.2 [P2#13] requirements.txt numpy 固定 + redis 添加

**文件**: `ai-service/requirements.txt`
**修复**:
```
# 行 28 改为
numpy==1.26.4

# 在 Utilities 部分后添加
# Redis（AI 服务直接读取画像 JSON）
redis==5.0.0
```

---

## 批次 4：API 契约修复（1 项）

### 4.1 [P2附录] SessionController/SessionService 幂等性

**文件**: `backend/.../controller/SessionController.java` 行 35-42, `backend/.../service/SessionService.java` 行 57-80, `backend/.../dto/request/SessionCreateRequest.java`

**修复方案**: 在 `SessionCreateRequest` 中添加可选的 `clientToken` 字段。Service 层基于 `(userId, clientToken)` 在 Redis 中做 5 分钟去重窗口。

**SessionCreateRequest.java 修改**: 添加 `clientToken` 字段
```java
private String clientToken;  // 客户端幂等令牌，5分钟内相同 token 返回已有会话
```

**SessionService.java 修改**:
```java
// 注入 RedisTemplate（已有）
public SessionResponse createSession(String userId, SessionCreateRequest request) {
    // ... userId 校验 ...
    
    // 幂等性检查
    if (request.getClientToken() != null && !request.getClientToken().isBlank()) {
        String idempotencyKey = "session:idempotency:" + userId + ":" + request.getClientToken();
        String existingSessionId = redisTemplate.opsForValue().get(idempotencyKey);
        if (existingSessionId != null) {
            // 返回已有会话
            return sessionRepository.findBySessionId(existingSessionId)
                    .map(sessionMapper::toResponse)
                    .orElseGet(() -> createNewSession(userId, request, idempotencyKey));
        }
    }
    
    return createNewSession(userId, request, 
        request.getClientToken() != null ? "session:idempotency:" + userId + ":" + request.getClientToken() : null);
}

private SessionResponse createNewSession(String userId, SessionCreateRequest request, String idempotencyKey) {
    String sessionId = "ses_" + UUID.randomUUID()...;
    Session session = ...;
    Session saved = sessionRepository.save(session);
    if (idempotencyKey != null) {
        redisTemplate.opsForValue().set(idempotencyKey, saved.getSessionId(), Duration.ofMinutes(5));
    }
    cacheEvictionHelper.evictByPatternAfterCommit(...);
    return sessionMapper.toResponse(saved);
}
```

---

## 假设与决策

| # | 决策 | 理由 |
|---|------|------|
| 1 | `_tokenize_query` 用共享 `seen_tokens` set | 避免英文 token 与中文 bigram 重复 |
| 2 | 旧关键词路径直接删除 | 新 `$or` 路径已完全覆盖功能 |
| 3 | 线程改 daemon + finally join | 最小改动解决泄漏 |
| 4 | gather 添加 return_exceptions + 结果过滤 | 兜底防护，不改变正常路径行为 |
| 5 | 降级静默用日志+计数器而非改签名 | 避免修改所有调用方 |
| 6 | update_paper_metadata 直接移除 try/catch | 让异常自然传播 |
| 7 | embedding 保留 last_error 变量 | 最小改动 |
| 8 | reranker 类型转换用 int() + try/except | 标准防御性编程 |
| 9 | reviewer 统一 accurate 默认值为 False | 安全侧：未标记准确视为不准确 |
| 10 | ChromaDB 返回用 .get() + 长度检查 | 防御性编程 |
| 11 | JwtUtil 仅 SecurityException + MalformedJwt 改 warn | 安全相关事件需可见 |
| 12 | AnalysisService.validateAnalysisAccess 返回实体 | 减少缓存未命中时的重复查询 |
| 13 | PaperRepository SQL 仅改 JSON_SEARCH | SELECT * 保留因返回 JPA 实体 |
| 14 | @Cacheable 仅加 sync=true | 空值缓存过度工程化 |
| 15 | Spring Boot 升级至 3.2.12 | 用户确认，最小风险 |
| 16 | numpy 固定为 1.26.4 | 不升级 chromadb，避免级联风险 |
| 17 | Session 幂等性用 Redis 5 分钟窗口 | 标准 Idempotency-Key 模式 |

---

## 验证步骤

### Python 验证
1. `cd ai-service && python -m pytest tests/test_search_service.py -v` — 验证 search_service 修改
2. `python -m pytest tests/test_reranker.py -v` — 验证 reranker 类型守卫
3. `python -m pytest tests/test_reviewer.py -v` — 验证 reviewer isinstance 守卫
4. `python -m pytest tests/test_vector_store.py -v` — 验证 vector_store 防御性校验
5. `python -c "from app.utils.text_processing import chunk_text; chunk_text('test', 100, 200)"` — 验证不崩溃
6. 手动构造边界数据测试 reranker 的 year="2023a" 场景

### Java 验证
1. `cd backend && mvn compile` — 验证编译通过
2. `mvn test -Dtest="AnalysisServiceTest"` — 验证 AnalysisService 修改
3. `mvn test -Dtest="SessionServiceTest"` — 验证 Session 幂等性
4. `mvn dependency:tree | grep spring-boot` — 验证版本升级
5. 检查日志输出：发送篡改 JWT 验证 warn 级别

### 文档更新
修复完成后在 `修复清单-2-常规(P2).md` 每个条目标注 `[已修复]` 状态。
