# Task 35：论文筛选排序增强（Day 4）

> **课题编号**：XH-202630
> **版本**：v0.5
> **里程碑**：JM5 缓存优化与功能完善（Week 9 Day 4）
> **功能编号**：F2.2.3
> **创建日期**：2026-06-17

---

## 1. Context（项目上下文）

### 项目
XH-202630 科研文献智能助手 — 领域知识个性化生成与多智能体协同决策系统研究

### 当前版本
v0.5 / JM5：缓存优化与功能完善（Week 9 Day 4）

### 需求描述
论文筛选排序增强：
- PaperRepositoryCustomImpl 扩展过滤条件，新增 `author`（LIKE 模糊匹配）和 `keywords`（JSON_CONTAINS）过滤
- 排序增强：SORT_MAPPING 新增 `title` 排序项，支持 `sortDirection` 参数（asc/desc，默认 desc）
- PaperService.searchPapers 方法签名扩展（新增 author/keywords/sortDirection 参数）
- PaperController 搜索端点参数扩展
- 缓存Key同步更新（paperSearch key 包含 author/keywords/sortDirection）

### 参考文档
- `docs/backend/Java后端模块系统架构文档.md` — 第4章 论文管理模块 + 第9章 缓存管理
- `docs/backend/Java后端模块项目里程碑文档.md` — 第7章 JM5 Week 9 Day 4 筛选排序任务分解
- `AGENTS.md` — 关键规则第4条跨系统字段转换 + 第6条 Cache-Aside 写后删

---

## 2. Current Architecture（当前架构）

### 涉及层级
- java_backend
- data_layer

### 相关模块
| 模块 | 路径 | 职责 |
|------|------|------|
| PaperRepositoryCustomImpl | `com.literatureassistant.repository` | 论文全文检索+筛选+排序的自定义SQL实现，当前仅支持 yearFrom/yearTo/venue 过滤 + relevance/year/citations 排序（固定DESC） |
| PaperService | `com.literatureassistant.service` | 论文服务，searchPapers 已有 @Cacheable(paperSearch) 复合key，ALLOWED_SORTS 仅含 relevance/year/citations |
| PaperController | `com.literatureassistant.controller` | 论文Controller，searchPapers 端点参数：q/yearFrom/yearTo/venue/sort/page/size |
| Paper Entity | `com.literatureassistant.entity` | authors/keywords 字段为 JSON 列，citation_count 为引用数 |

### 已有实现
- `PaperRepositoryCustomImpl.java` — SORT_MAPPING=Map.of(relevance/year/citations, 固定DESC)；DATA_SQL_TEMPLATE 使用 String.format 拼接 ORDER BY
- `PaperRepositoryCustom.java` — 接口定义 searchByKeyword
- `PaperService.java` — ALLOWED_SORTS=Set.of(relevance/year/citations)；searchPapers 有 @Cacheable(paperSearch) 复合key
- `PaperController.java` — searchPapers 端点 @GetMapping(/search)
- `Paper.java` — Paper Entity：authors(JSON)/keywords(JSON)/year/venue/citation_count/title 字段
- `RedisKeyUtil.java` — 已有 paperDetailKey/paperListKey/searchResultKey 方法

---

## 3. Relevant Modules（关键模块）

### PaperRepositoryCustomImpl
- **路径**：`Veritas/backend/src/main/java/com/literatureassistant/repository/PaperRepositoryCustomImpl.java`
- **职责**：论文全文检索+筛选+排序的自定义SQL实现
- **关键接口**：
  - `searchByKeyword(String keyword, Integer yearFrom, Integer yearTo, String venue, String sort, Pageable pageable)` — 当前签名，需扩展
  - `SORT_MAPPING` — 排序白名单，需新增 title 项并支持方向参数
  - `DATA_SQL_TEMPLATE` — 数据SQL模板，需扩展 author LIKE 和 keywords JSON_CONTAINS 条件

### PaperRepositoryCustom
- **路径**：`Veritas/backend/src/main/java/com/literatureassistant/repository/PaperRepositoryCustom.java`
- **职责**：论文自定义Repository接口
- **关键接口**：`searchByKeyword` — 接口签名，需同步扩展

### PaperService
- **路径**：`Veritas/backend/src/main/java/com/literatureassistant/service/PaperService.java`
- **职责**：论文服务业务，检索/详情/列表
- **关键接口**：
  - `searchPapers` — 检索方法，需扩展签名和缓存key
  - `ALLOWED_SORTS` — 排序白名单，需新增 SORT_TITLE

### PaperController
- **路径**：`Veritas/backend/src/main/java/com/literatureassistant/controller/PaperController.java`
- **职责**：论文Controller，REST端点
- **关键接口**：`searchPapers` — 搜索端点，需新增 author/keywords/sortDirection 参数

---

## 4. Files To Modify（变更文件）

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 修改 | `repository/PaperRepositoryCustom.java` | 接口签名扩展：searchByKeyword 新增 String author, String keywords, String sortDirection 参数 |
| 修改 | `repository/PaperRepositoryCustomImpl.java` | SORT_MAPPING 新增 title 项；DATA_SQL_TEMPLATE/COUNT_SQL 扩展 author LIKE 和 keywords JSON_CONTAINS 条件；searchByKeyword 实现扩展；setParameters 扩展；排序方向支持 asc/desc |
| 修改 | `service/PaperService.java` | ALLOWED_SORTS 新增 title；searchPapers 签名扩展；@Cacheable key 扩展包含新参数；新增 ALLOWED_SORT_DIRECTIONS |
| 修改 | `controller/PaperController.java` | searchPapers 端点新增 @RequestParam author/keywords/sortDirection |
| 新增 | `repository/PaperRepositoryFilterSortTest.java` | 筛选排序单元测试 |

---

## 5. Implementation Requirements（实现要求）

### 功能要求

| ID | 优先级 | 描述 | 验收条件 |
|----|--------|------|---------|
| FR-001 | P0 | PaperRepositoryCustomImpl 新增 author 过滤：`AND (?N IS NULL OR authors LIKE CONCAT('%', ?N, '%'))` | 传入 author 时，结果集 authors JSON 包含该作者名 |
| FR-002 | P0 | PaperRepositoryCustomImpl 新增 keywords 过滤：`AND (?N IS NULL OR JSON_CONTAINS(keywords, CONCAT('"', ?N, '"')))` | 传入 keywords 时，结果集 keywords JSON 数组包含该关键词 |
| FR-003 | P0 | SORT_MAPPING 新增 title 排序项 | sort=title 时按论文标题排序 |
| FR-004 | P0 | 支持 sortDirection 参数（asc/desc），默认 desc。ORDER BY 动态拼接方向 | sortDirection=asc 升序，desc 降序，非法值 fallback desc |
| FR-005 | P0 | PaperService.ALLOWED_SORTS 新增 title；新增 ALLOWED_SORT_DIRECTIONS；searchPapers 签名扩展 | 签名包含所有新参数，校验逻辑完整 |
| FR-006 | P0 | @Cacheable(paperSearch) key 扩展包含 author/keywords/sortDirection | 不同参数组合缓存隔离 |
| FR-007 | P0 | PaperController.searchPapers 端点新增3参数 | 端点接受新参数并传递给 PaperService |
| FR-008 | P1 | 参数校验：sortDirection 仅允许 asc/desc，否则 fallback desc 并 warn | 非法值不抛异常，fallback desc |

### 跨系统一致性
- **字段命名**：Java camelCase ↔ Python/JSON snake_case
  - paperId ↔ paper_id
  - citationCount ↔ citation_count
  - yearFrom ↔ year_from
  - yearTo ↔ year_to
  - sortDirection ↔ sort_direction
- **API契约**：
  - `GET /api/papers/search?q=...&author=...&keywords=...&sort=title&sortDirection=asc`
  - 响应：`{code:200, data:{items:[...], total, page, size, totalPages}}`
- **数据流转**：前端 GET → PaperController → PaperService(@Cacheable) → PaperRepositoryCustomImpl(原生SQL) → MySQL papers 表

### 安全要求
- **SQL注入防护**：排序字段必须来自白名单（SORT_MAPPING），方向参数必须来自白名单（asc/desc），禁止用户输入直接拼接到SQL；author/keywords 使用参数化查询（?N 占位符）
- **数据隔离**：论文检索为公开数据，无需 userId 隔离；分页参数 size 上限 MAX_SIZE=100

---

## 6. Constraints（约束）

### 命名规范
- Java: 类名PascalCase, 方法/变量camelCase, 常量UPPER_SNAKE_CASE, 文件PascalCase.java
- 数据库: 表名snake_case复数, 列名snake_case
- JSON: 字段名snake_case

### 分层规范
- Controller → Service → Repository → Client，禁止跨层
- Entity与DTO分离，禁止直接返回Entity

### 错误处理
- BusinessException + GlobalExceptionHandler(@RestControllerAdvice)
- BusinessException含 code、message、errorKey 三字段

### 缓存策略
- Cache-Aside：写MySQL后删Redis缓存
- paperSearch TTL=10min
- 缓存穿透防护：空值缓存 TTL=60s
- 缓存雪崩防护：TTL ±10% 随机偏移
- 单个缓存值不超过1MB

### 日志规范
- SLF4J + Logback
- 禁止在循环中打印INFO及以上级别日志
- 禁止输出敏感信息

### 数据库规范
- 字符集 utf8mb4 + utf8mb4_unicode_ci
- 全文索引 WITH PARSER ngram
- 禁止 SELECT *，明确列出查询字段
- 大表查询必须分页

### 安全规范
- SQL注入防护：JPA参数化查询，排序字段白名单校验
- 数据隔离：论文检索公开数据，分页参数校验

---

## 7. Forbidden Actions（禁止行为）

| ID | 禁止行为 | 原因 | 严重程度 |
|----|---------|------|---------|
| FA-001 | 输出伪代码或TODO注释 | 必须输出完整可执行代码 | critical |
| FA-002 | 修改需求范围外的模块 | 避免引入无关变更 | high |
| FA-003 | 破坏三层分离架构 | 架构约束ADR-001 | critical |
| FA-004 | 破坏分层调用规范 | 分层架构约束 | critical |
| FA-005 | Entity直接返回给前端 | 数据隔离与接口稳定性 | high |
| FA-006 | 硬编码敏感配置 | 安全约束 | critical |
| FA-007 | 违反跨系统字段命名约定 | 跨系统一致性约束 | high |
| FA-008 | 在循环中打印INFO及以上级别日志 | 性能约束 | medium |
| FA-009 | 使用SQL拼接（必须参数化查询，排序字段白名单） | SQL注入防护 | critical |
| FA-010 | 忽略降级场景 | 可用性约束ADR-003 | high |

---

## 8. Test Requirements（测试要求）

### 单元测试
| 测试名 | 描述 | 覆盖场景 |
|--------|------|---------|
| testAuthorFilter | 验证 author 过滤：传入存在/不存在的作者名 | normal_flow, boundary_condition |
| testKeywordsFilter | 验证 keywords 过滤：传入存在/不存在的关键词 | normal_flow, boundary_condition |
| testTitleSort | 验证 sort=title 排序：结果按 title 字母序 | normal_flow |
| testSortDirectionAsc | 验证 sortDirection=asc 升序 | normal_flow |
| testSortDirectionDesc | 验证 sortDirection=desc 降序（默认） | normal_flow |
| testInvalidSortDirectionFallback | 验证非法 sortDirection fallback desc | error_flow, boundary_condition |
| testCombinedFilterSort | 验证组合条件：author+keywords+year+venue+sort+direction | normal_flow |
| testCacheKeyIsolation | 验证不同参数组合缓存key隔离 | normal_flow |

### 验证命令
```bash
cd Veritas/backend && mvn test -Dtest=PaperRepositoryFilterSortTest
cd Veritas/backend && mvn test -Dtest=PaperServiceCacheTest
```

---

## 9. Acceptance Criteria（验收标准）

| ID | 验收标准 | 验证方式 |
|----|---------|---------|
| AC-001 | author 过滤返回正确结果集 | automated_test |
| AC-002 | keywords 过滤返回正确结果集 | automated_test |
| AC-003 | sort=title 时结果按标题字母序排序 | automated_test |
| AC-004 | sortDirection=asc 升序，desc 降序 | automated_test |
| AC-005 | 非法 sortDirection fallback desc 不抛异常 | automated_test |
| AC-006 | 缓存Key包含新参数，缓存隔离正确 | automated_test |
| AC-007 | PaperController 端点接受新参数 | code_review |
| AC-008 | 排序字段白名单校验，无SQL注入风险 | code_review |
| AC-009 | mvn test 全量通过 | automated_test |
