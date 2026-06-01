# Paper Search — Fulltext + Filter + Sort Coding Task

> 任务编号：`task16_paper_search_fulltext_filter_sort`
> 对应需求编号：`F2.2.3`
> 里程碑：M3 前后端联调 / JM2 Java后端M2

---

## 1. Context（项目上下文）

| 字段 | 值 |
|------|-----|
| 项目 | XH-202630 科研文献智能助手 — 领域知识个性化生成与多智能体协同决策系统研究 |
| 版本 | v0.2 |
| 里程碑 | M3：前后端联调 / JM2：Java后端M2 |
| 涉及模块 | F2.2.3 论文搜索 |
| 涉及层级 | `java_backend` + `data_layer` |

### 需求描述

实现论文搜索功能（全文索引 + 条件过滤 + 排序）：

- 利用已有 `PaperRepositoryCustomImpl.searchByKeyword` 做 MySQL FULLTEXT 全文检索
- 扩展 `PaperService` 新增 `searchPapers` 方法（参数校验 + 缓存 + Entity→DTO 转换）
- 扩展 `PaperController` 新增 `GET /api/papers/search` 端点（6 个 `@RequestParam`）
- 排序白名单：`relevance`（相关度）/ `year`（年份）/ `citations`（引用数）
- 条件过滤：年份范围 `yearFrom`/`yearTo` + 会议/期刊 `venue`
- 添加 `@Cacheable(value="paperSearch")` 缓存（TTL=10min）
- 所有 API 需 JWT 鉴权
- **注意：底层 `PaperRepositoryCustomImpl` 已在 task09 中完整实现，本次任务不改动**

### 参考文档

| 路径 | 用途 |
|------|------|
| `docs/backend/Java后端模块系统架构文档.md` | §5.2 PaperController/PaperService 搜索方法签名、§5.2.3 排序白名单设计 |
| `docs/database/数据库设计文档.md` | §3.5.4 全文索引 ft_title_abstract、§3.5.5 全文检索 SQL 示例、§4.3 paperSearch 缓存 10min |
| `AGENTS.md` | §7.2 search:result:{queryHash} TTL=10min、§8.1 API 契约 |
| `docs/backend/Java后端模块项目里程碑文档.md` | §3.4 JM2 论文搜索任务分解 |

---

## 2. Current Architecture（当前架构）

**涉及层级**：`Controller → Service → Repository → Database (MySQL FULLTEXT + Redis Cache)`

**已有实现（可直接复用）**：

| 文件 | 说明 | 复用方式 |
|------|------|---------|
| `repository/PaperRepositoryCustomImpl.java` | 全文检索实现：`searchByKeyword` — MATCH...AGAINST + year/venue 过滤 + SORT_MAPPING 白名单 + 分页 | **direct_reuse（不改动）** |
| `repository/PaperRepositoryCustom.java` | 自定义查询接口声明 | direct_reuse |
| `repository/PaperRepository.java` | JPA Repository（已继承 PaperRepositoryCustom） | direct_reuse |
| `entity/Paper.java` | Paper 实体：12 字段（含 title/abstract FULLTEXT、year/venue 过滤、citationCount 排序） | direct_reuse |
| `dto/response/PaperResponse.java` | 论文列表项 DTO（task15 新建） | direct_reuse |
| `mapper/PaperMapper.java` | MapStruct 映射器（task15 新建）：`toResponse(Paper)` 含 JSON 反序列化 | direct_reuse |
| `dto/common/PageResponse.java` | `PageResponse.fromPage(page, mappedList)` 分页响应 | direct_reuse |
| `dto/common/ApiResponse.java` | `ApiResponse<T>` 统一响应包装 | direct_reuse |
| `config/RedisConfig.java` | `paperSearch` 缓存空间 TTL=10min 已配置 | direct_reuse |
| `service/PaperService.java` | 论文 Service（task15 新建）：已有 `listPapers` + `getPaperDetail`，本次扩展添加 `searchPapers` | **extend** |
| `controller/PaperController.java` | 论文 Controller（task15 新建）：已有 2 个 GET 端点，本次扩展添加搜索端点 | **extend** |

---

## 3. Relevant Modules（相关模块）

### PaperController（扩展）

- 路径：`com.literatureassistant.controller.PaperController`
- 职责：新增 `searchPapers` 搜索端点
- 关键端点：
  - `@GetMapping("/search")` → `GET /api/papers/search?q=agent&sort=relevance&page=1&size=10`
  - 6 个 `@RequestParam`：`q`（必填）、`yearFrom`（可选）、`yearTo`（可选）、`venue`（可选）、`sort`（默认 relevance）、`page`（默认 1）、`size`（默认 10）
  - Controller 仅做参数接收 + 调用 Service + 返回 Response

### PaperService（扩展）

- 路径：`com.literatureassistant.service.PaperService`
- 职责：新增 `searchPapers` 搜索方法
- 关键方法：
  - `@Cacheable(value="paperSearch", key="String.format('%s_%s_%s_%s_%s_%d_%d', ...)")`
  - `searchPapers(q, yearFrom, yearTo, venue, sort, page, size)` → `PageResponse<PaperResponse>`
  - 参数校验 + 调用 `paperRepository.searchByKeyword` + `paperMapper.toResponse` 批量转换 + `PageResponse.fromPage` 包装

### PaperRepositoryCustomImpl（已有，不改动）

- 路径：`com.literatureassistant.repository.PaperRepositoryCustomImpl`
- 职责：MySQL FULLTEXT 全文检索 + 排序白名单 + 条件过滤 + 分页
- 关键方法：
  - `searchByKeyword(keyword, yearFrom, yearTo, venue, sort, pageable)` → `Page<Paper>`
  - `SORT_MAPPING`：`relevance` → `MATCH...AGAINST DESC`、`year` → `year DESC`、`citations` → `citation_count DESC`
  - SQL 参数化查询，使用 `EntityManager.createNativeQuery` + `setParameter`

---

## 4. Files To Modify（待修改文件）

| 操作 | 路径 | 说明 |
|------|------|------|
| **修改** | `com/literatureassistant/service/PaperService.java` | 新增 `searchPapers` 方法：参数校验 + 调用已有 `paperRepository.searchByKeyword` + `paperMapper.toResponse` 批量转换 + `@Cacheable("paperSearch")` 缓存 10min |
| **修改** | `com/literatureassistant/controller/PaperController.java` | 新增 `@GetMapping("/search")` 端点：6 个 `@RequestParam`（q/yFrom/yTo/venue/sort/page/size），调用 `paperService.searchPapers` |

---

## 5. Implementation Requirements（实现要求）

### 5.1 功能要求

| 编号 | 描述 | 优先级 | 验收条件 |
|------|------|--------|---------|
| FR-001 | `PaperController.searchPapers` 端点：`GET /api/papers/search` + 6 个 @RequestParam | P0 | q 必填，其他可选，无 q 返回 400 |
| FR-002 | `PaperService.searchPapers` 参数校验：q 非空、yearFrom≤yearTo、sort 白名单降级、page/size 边界修正 | P0 | 非法参数正确处理 |
| FR-003 | 调用 `paperRepository.searchByKeyword(q, ...)` 获取 `Page<Paper>` | P0 | 搜索词正确传递给底层 SQL |
| FR-004 | `@Cacheable(value="paperSearch", key=...)` 缓存 10min，空结果也缓存 | P0 | 缓存命中避免重复查库 |
| FR-005 | 三种排序正确：relevance（相关度）、year（年份降序）、citations（引用数降序） | P0 | 非法 sort 降级为 relevance |
| FR-006 | MySQL FULLTEXT：`MATCH(title, abstract) AGAINST(? IN NATURAL LANGUAGE MODE)` + ngram parser | P0 | 中英文关键词均可搜索 |
| FR-007 | 条件过滤：yearFrom/yearTo 年份范围 + venue 会议精确匹配 | P0 | 过滤正确，空参数不过滤 |
| FR-008 | JWT 鉴权：`GET /api/papers/search` 需 Token | P0 | 未认证返回 401 |
| FR-009 | 空结果处理：返回 `PageResponse(total=0, items=[])`，不返回 null | P1 | 前端正常显示"无结果" |

### 5.2 核心数据流

```
前端 Request
  GET /api/papers/search?q=agent&sort=relevance&page=1&size=10
    │
    ▼
PaperController.searchPapers(@RequestParam接收6个参数)
    │
    ▼
PaperService.searchPapers()
  ├─ 参数校验：q非空 / yearFrom≤yearTo / sort白名单 / page/size修正
  ├─ Redis Cache (paperSearch: 10min) [缓存命中] → 直接返回
  └─ [缓存未命中]
       │
       ▼
     paperRepository.searchByKeyword(q, from, to, venue, sort, pageable)
       │
       ▼
     PaperRepositoryCustomImpl
       ├─ SORT_MAPPING: 白名单校验sort参数 → ORDER BY 子句
       ├─ EntityManager.createNativeQuery(DATA_SQL_TEMPLATE)
       │   MATCH(title, abstract) AGAINST(?1 IN NATURAL LANGUAGE MODE)
       │   + AND (?2 IS NULL OR year >= ?2)      -- yearFrom过滤
       │   + AND (?3 IS NULL OR year <= ?3)      -- yearTo过滤
       │   + AND (?4 IS NULL OR venue = ?4)      -- venue过滤
       │   + ORDER BY {sortClause}               -- 排序
       ├─ setFirstResult/setMaxResults 分页
       └─ 返回 Page<Paper>
       │
       ▼
     paperMapper.toResponse 批量转换 (每篇Paper → PaperResponse)
       ├─ authors: JSON字符串 → List<String>
       └─ keywords: JSON字符串 → List<String>
       │
       ▼
     PageResponse.fromPage(paperPage, mappedList)
       │
       ▼
     回填 Redis 缓存 (TTL=10min)
       │
       ▼
     ApiResponse.success(pageResponse)
```

### 5.3 三种排序方式

| sort 值 | SQL ORDER BY | 说明 |
|---------|-------------|------|
| `relevance`（默认） | `MATCH(title, abstract) AGAINST(keyword IN NATURAL LANGUAGE MODE) DESC` | 按全文相关度降序 |
| `year` | `year DESC` | 按年份降序，最新排前 |
| `citations` | `citation_count DESC` | 按引用数降序，高引排前 |

### 5.4 缓存设计

```java
@Cacheable(
    value = "paperSearch",
    key = "T(java.lang.String).format('%s_%s_%s_%s_%s_%d_%d', #q, #yearFrom, #yearTo, #venue, #sort, #page, #size)"
)
```

- **缓存空间**：`paperSearch`（RedisConfig 已配置 TTL=10min + ±10% 随机偏移）
- **缓存 Key**：所有查询参数拼接，不同查询条件缓存隔离
- **空结果也缓存**：不设置 `unless`，防止缓存穿透
- **写后删**：后续收藏/导入操作应调用 `@CacheEvict(value="paperSearch", allEntries=true)` 清空搜索缓存

### 5.5 跨系统一致性

- 字段命名：Java camelCase ↔ JSON snake_case
- 关键映射：`paperId`↔`paper_id`、`citationCount`↔`citation_count`
- 复用 PaperResponse（task15 已实现 `@JsonProperty` 映射）

### 5.6 安全要求

- JWT 认证（非白名单路径）
- 底层 SQL 参数化查询（`setParameter`），禁止拼接
- 论文为公共资源，不涉及用户数据隔离

---

## 6. Constraints（约束）

### 6.1 命名规范

- Java：类名 PascalCase、方法/变量 camelCase、常量 UPPER_SNAKE_CASE
- JSON：字段名 `snake_case`
- 数据库：表名/列名 `snake_case`

### 6.2 分层规范

- `Controller → Service → Repository → CustomImpl`，禁止跨层
- Controller 仅做参数接收 + 调用 Service + 返回 Response
- Service 含业务逻辑（校验、转换、编排）
- Repositry/CustomImpl 含数据访问逻辑
- Entity 必须通过 DTO 转换后返回

### 6.3 错误处理

- `BusinessException` + `GlobalExceptionHandler`（`@RestControllerAdvice`）
- `q` 为空 → `IllegalArgumentException` → Spring 默认 400
- `yearFrom > yearTo` → `BusinessException(ErrorCode.INVALID_PARAMETER)`
- sort 非法值 → `log.warn` 降级为 `relevance`（不抛异常）

### 6.4 缓存策略

- Cache-Aside 模式
- `paperSearch` TTL = 10min（已配置 ±10% 随机偏移防雪崩）
- 空结果也缓存（防穿透）
- 缓存 Key 包含所有查询参数（不同条件缓存隔离）

### 6.5 数据库规范

- MySQL FULLTEXT ngram parser
- JPA + EntityManager 参数化查询，禁止 SQL 拼接
- 所有列表接口强制分页

---

## 7. Forbidden Actions（禁止行为）

- ❌ 输出伪代码或 TODO 注释
- ❌ 修改 `PaperRepositoryCustomImpl`（底层实现在 task09 已完成，本次仅调用）
- ❌ 修改需求范围外的模块（UserService/SessionService/AnalysisService 等）
- ❌ 破坏三层分离架构
- ❌ 破坏分层调用规范（Controller 直接操作 CustomImpl）
- ❌ Paper Entity 直接返回给前端
- ❌ 硬编码敏感配置
- ❌ 违反跨系统字段命名约定
- ❌ 在循环中打印 INFO 及以上级别日志
- ❌ **在 Service 层构建 SQL**（所有 SQL 由 PaperRepositoryCustomImpl 统一管理）
- ❌ **Controller 中编写业务逻辑**（参数校验、sort 白名单校验、Entity→DTO 转换等）

---

## 8. Test Requirements（测试要求）

### 8.1 单元测试

| 测试类 | 验证点 |
|--------|--------|
| `PaperServiceSearchTest` | q 为空/null 异常、yearFrom>yearTo 异常、sort 非法值降级、page/size 边界修正、缓存命中验证、空结果处理、paperMapper.toResponse 批量转换 |

### 8.2 集成测试

| 测试类 | 验证点 |
|--------|--------|
| `PaperRepositoryCustomImplTest` | 中/英文全文检索、年份/会议过滤、三种排序、非法 sort 降级、空结果 |
| `PaperControllerSearchTest` | 完整 HTTP 链路：正确搜索、过滤搜索、空结果、缺参数 400、未授权 401 |

### 8.3 验证命令

```bash
cd Veritas/backend && mvn compile                                          # 编译
cd Veritas/backend && mvn test -Dtest=PaperServiceSearchTest               # Service 测试
cd Veritas/backend && mvn test                                             # 全部测试
curl -H 'Authorization: Bearer <token>' \
  'http://localhost:8080/api/papers/search?q=agent&sort=relevance&page=1&size=5'
```

---

## 9. Acceptance Criteria（验收标准）

- [ ] AC-001：`GET /api/papers/search?q=agent` 返回 `ApiResponse<PageResponse<PaperResponse>>`
- [ ] AC-002：年份范围 + 会议过滤正确：`GET /api/papers/search?q=agent&yearFrom=2020&yearTo=2024&venue=AAAI`
- [ ] AC-003：搜索无结果返回 `PageResponse(total=0, items=[])`，不返回 null
- [ ] AC-004：缺少 `q` 参数返回 400
- [ ] AC-005：sort 非法值降级为 `relevance` + `log.warn`
- [ ] AC-006：`@Cacheable(value="paperSearch")` 缓存生效（第二次相同请求不查库）
- [ ] AC-007：三种排序方式均正确（relevance/year/citations）
- [ ] AC-008：page 从 1 开始，size 默认 10，边界值修正
- [ ] AC-009：未携带 Token 返回 401
- [ ] AC-010：Controller 不含业务逻辑
- [ ] AC-011：底层 SQL 使用参数化查询，无 SQL 拼接
- [ ] AC-012：`mvn compile` + `mvn test` 均成功

---

## 10. API 契约示例

### GET /api/papers/search?q=multi-agent&sort=relevance&yearFrom=2020&yearTo=2024&venue=AAAI&page=1&size=10

**Request**：
```
GET /api/papers/search?q=multi-agent&sort=relevance&yearFrom=2020&yearTo=2024&venue=AAAI&page=1&size=10
Authorization: Bearer <valid_jwt_token>
```

**Response**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "paper_id": "arxiv_2024_001",
        "title": "Multi-Agent Systems: A Survey",
        "authors": ["Wang, L.", "Chen, X."],
        "year": 2024,
        "venue": "AAAI",
        "keywords": ["multi-agent", "survey"],
        "citation_count": 1200
      },
      {
        "paper_id": "arxiv_2023_015",
        "title": "Cooperative Multi-Agent Reinforcement Learning",
        "authors": ["Li, M.", "Zhang, Y."],
        "year": 2023,
        "venue": "AAAI",
        "keywords": ["multi-agent", "reinforcement-learning"],
        "citation_count": 850
      }
    ],
    "total": 15,
    "page": 1,
    "size": 10,
    "total_pages": 2
  },
  "timestamp": 1716451200000
}
```

### GET /api/papers/search?q=关键词_无结果

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [],
    "total": 0,
    "page": 1,
    "size": 10,
    "total_pages": 0
  },
  "timestamp": 1716451200000
}
```

### GET /api/papers/search（缺少 q 参数）

```json
{
  "code": 400,
  "message": "搜索关键词不能为空",
  "timestamp": 1716451200000
}
```

---

## 11. 底层 SQL 参考（PaperRepositoryCustomImpl，已有，不改动）

```sql
-- DATA_SQL_TEMPLATE（根据sort参数拼接ORDER BY）
SELECT * FROM papers
WHERE MATCH(title, `abstract`) AGAINST(?1 IN NATURAL LANGUAGE MODE)
  AND (?2 IS NULL OR year >= ?2)       -- yearFrom
  AND (?3 IS NULL OR year <= ?3)       -- yearTo
  AND (?4 IS NULL OR venue = ?4)       -- venue
ORDER BY %s;                            -- sort clause

-- COUNT_SQL
SELECT COUNT(*) FROM papers
WHERE MATCH(title, `abstract`) AGAINST(?1 IN NATURAL LANGUAGE MODE)
  AND (?2 IS NULL OR year >= ?2)
  AND (?3 IS NULL OR year <= ?3)
  AND (?4 IS NULL OR venue = ?4);

-- SORT_MAPPING 白名单
relevance  → MATCH(title, `abstract`) AGAINST(?1 IN NATURAL LANGUAGE MODE) DESC
year       → year DESC
citations  → citation_count DESC
默认/非法   → year DESC
```

---

## 12. 依赖关系

```
task15 (PaperController/PaperService 基础)
    │
    ├── PaperResponse.java (复用)
    ├── PaperMapper.java (复用)
    ├── PaperService.java (扩展: 新增 searchPapers)
    └── PaperController.java (扩展: 新增 /search 端点)
    │
task16 (本次: 论文搜索)
    │
    ├── PaperService.java → 新增 searchPapers()
    └── PaperController.java → 新增 GET /api/papers/search
    │
    ▼
task09 (PaperRepositoryCustomImpl — 底层全文检索，已有，不改动)
```

---

## 13. 后续建议

- **下一步（task17）**：论文收藏功能（`POST/DELETE /api/papers/{paperId}/favorite`），收藏时需 `@CacheEvict(value="paperSearch", allEntries=true)` 清空搜索缓存
- **下一步（task18）**：批量导入论文（`POST /api/papers/import`），导入后也需清空搜索缓存
- **未来优化**：搜索关键词高亮 — 可考虑在 PaperResponse 中新增 `highlightTitle`/`highlightAbstract` 字段
- **未来优化**：搜索建议/自动补全 — 可基于论文关键词/title 构建 Trie 索引
- **降级考虑**：MySQL FULLTEXT 停用词表可能导致短关键词搜不到结果，前端建议提示用户使用更具体的搜索词

---

> **任务完成后必须**：
> 1. 运行 `mvn compile && mvn test` 验证编译和测试
> 2. 手动验证搜索端点的 HTTP 响应（使用 curl 或 Postman）
> 3. 验证缓存行为（第二次相同搜索不产生 SQL 查询）
> 4. 验证三种排序方式正确性
> 5. 在 `json_prompt/Coding.md` 的 backend 序号映射表中追加 task16 新行