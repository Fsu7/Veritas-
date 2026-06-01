# PaperController + PaperService (List/Detail) Coding Task

> 任务编号：`task15_paper_controller_service_list_detail`
> 对应需求编号：`F2.2.1`、`F2.2.2`
> 里程碑：M3 前后端联调 / JM2 Java后端M2

---

## 1. Context（项目上下文）

| 字段 | 值 |
|------|-----|
| 项目 | XH-202630 科研文献智能助手 — 领域知识个性化生成与多智能体协同决策系统研究 |
| 版本 | v0.2 |
| 里程碑 | M3：前后端联调 / JM2：Java后端M2 |
| 涉及模块 | F2.2 论文管理模块（列表/详情） |
| 涉及层级 | `java_backend` + `data_layer` |

### 需求描述

实现论文管理模块的列表/详情功能：

- 新增 `PaperResponse` / `PaperDetailResponse` 两个 DTO
- 新增 `PaperMapper` (MapStruct) 做 `Paper` Entity ↔ DTO 转换（含 `authors` / `keywords` JSON 字符串解析与 re-encoding）
- `PaperService.listPapers(page, size)` 分页查询 + `PageResponse` 包装
- `PaperService.getPaperDetail(paperId)` 按 `paperId` 查询 + `@Cacheable(paperDetail)` 30min 缓存
- `PaperController` 新增 2 个端点（`GET /api/papers`、`GET /api/papers/{paperId}`）
- 所有 API 需 JWT 鉴权，Controller 只做参数接收与 Service 调用，禁止直接返回 `Paper` Entity
- Response 字段使用 `@JsonProperty` 输出 `snake_case`，与 Python AI 服务契约一致

### 参考文档

| 路径 | 用途 |
|------|------|
| `docs/backend/Java后端模块系统架构文档.md` | §5 论文管理模块设计、§6 DTO 规范、§8 API 端点 |
| `docs/database/数据库设计文档.md` | §3.5 papers 表结构 + JSON 字段格式、§4.3 缓存空间（paperDetail:30min） |
| `AGENTS.md` | §7.2 Redis 缓存 Key、§8.1 API 契约、§9.2 Java 后端规范 |
| `docs/backend/Java后端模块项目里程碑文档.md` | §3.4 JM2 任务分解、§4.4 JM2 验收检查点 |

---

## 2. Current Architecture（当前架构）

**涉及层级**：`Controller → Service → Repository → Database (MySQL + Redis)`

**已有实现（可直接复用）**：

| 文件 | 说明 | 复用方式 |
|------|------|---------|
| `entity/Paper.java` | Paper 实体：12 字段（含 `authors`/`keywords` JSON String） | direct_reuse |
| `repository/PaperRepository.java` | `findByPaperId` / `findByPaperIdIn` / `JpaRepository.findAll(Pageable)` | direct_reuse |
| `dto/common/ApiResponse.java` | `ApiResponse<T>` 统一响应包装 | direct_reuse |
| `dto/common/PageResponse.java` | `PageResponse<T>` 分页响应 + `fromPage()` 静态工厂 | direct_reuse |
| `exception/ResourceNotFoundException.java` | 资源不存在异常（404） | direct_reuse |
| `exception/GlobalExceptionHandler.java` | 全局异常处理（@RestControllerAdvice） | direct_reuse |
| `util/RedisKeyUtil.java` | `paperDetailKey(paperId)` Redis Key 生成 | direct_reuse |
| `config/RedisConfig.java` | `paperDetail` 缓存空间（TTL=30min）已配置 | direct_reuse |
| `mapper/UserMapper.java` | MapStruct + `expression` 处理枚举 dbValue 转换 | reference |
| `service/UserService.java` | 分层结构 + `@Cacheable`/`@CacheEvict` 使用 | reference |
| `controller/UserController.java` | `@RestController` + `@Valid` + `ApiResponse.success()` | reference |

---

## 3. Relevant Modules（相关模块）

### PaperResponse（新）

- 路径：`com.literatureassistant.dto.response.PaperResponse`
- 职责：论文列表项 DTO，`@JsonProperty` 输出 `snake_case`，`authors`/`keywords` 使用 `List<String>` 类型
- 关键字段：`paperId` (`@JsonProperty("paper_id")`)、`title`、`authors` (List)、`year`、`venue`、`keywords` (List)、`citationCount` (`@JsonProperty("citation_count")`)

### PaperDetailResponse（新）

- 路径：`com.literatureassistant.dto.response.PaperDetailResponse`
- 职责：论文详情 DTO，继承 `PaperResponse`，额外包含 `abstract` / `pdfUrl` / `createdAt` / `updatedAt`
- 关键字段：`abstractText` (`@JsonProperty("abstract")`，注意 Entity 字段名为 `abstractText`，输出 JSON 时为 `abstract`)、`pdfUrl` (`@JsonProperty("pdf_url")`)、`createdAt` / `updatedAt`

### PaperMapper（新）

- 路径：`com.literatureassistant.mapper.PaperMapper`
- 职责：MapStruct 映射器，注入 `ObjectMapper` 处理 `authors`/`keywords` JSON 字符串 ↔ `List<String>`
- 关键方法：`toResponse(Paper)` → `PaperResponse`、`toDetailResponse(Paper)` → `PaperDetailResponse`、自定义 `@Named` 方法 `jsonToList(String)`

### PaperService（新）

- 路径：`com.literatureassistant.service.PaperService`
- 职责：论文业务逻辑
- 关键方法：
  - `listPapers(int page, int size)` → `PageResponse<PaperResponse>`（page 从 1 开始，size 边界修正）
  - `getPaperDetail(String paperId)` → `PaperDetailResponse`（`@Cacheable("paperDetail", key="#paperId", unless="#result == null")`）

### PaperController（新）

- 路径：`com.literatureassistant.controller.PaperController`
- 职责：论文 API 入口
- 关键端点：
  - `@GetMapping` → `GET /api/papers?page=1&size=10` → 分页论文列表
  - `@GetMapping("/{paperId}")` → `GET /api/papers/{paperId}` → 论文详情

### PaperRepository（已有）

- 路径：`com.literatureassistant.repository.PaperRepository`
- 关键方法：`findByPaperId(String)` → `Optional<Paper>`、`findAll(Pageable)` → `Page<Paper>`

---

## 4. Files To Modify（待修改文件）

| 操作 | 路径 | 说明 |
|------|------|------|
| 新增 | `com/literatureassistant/dto/response/PaperResponse.java` | 7 字段 DTO，`@JsonProperty` 输出 `snake_case`，`authors`/`keywords` 为 `List<String>` |
| 新增 | `com/literatureassistant/dto/response/PaperDetailResponse.java` | 继承 `PaperResponse`，额外 4 字段（`abstract`/`pdfUrl`/`createdAt`/`updatedAt`） |
| 新增 | `com/literatureassistant/mapper/PaperMapper.java` | MapStruct 映射器，`toResponse` / `toDetailResponse` + 自定义 `jsonToList` 方法 |
| 新增 | `com/literatureassistant/service/PaperService.java` | 论文 Service，`listPapers` + `getPaperDetail`（含 `@Cacheable`） |
| 新增 | `com/literatureassistant/controller/PaperController.java` | 论文 Controller，2 个 GET 端点 |

---

## 5. Implementation Requirements（实现要求）

### 5.1 功能要求

| 编号 | 描述 | 优先级 | 验收条件 |
|------|------|--------|---------|
| FR-001 | `PaperResponse` DTO：7 字段，`@JsonProperty` 输出 `snake_case` | P0 | 字段正确映射，authors/keywords 为 List |
| FR-002 | `PaperDetailResponse` DTO：继承 PaperResponse + 4 字段（abstract/pdfUrl/createdAt/updatedAt） | P0 | abstract 字段名（非 abstractText） |
| FR-003 | `PaperMapper` (MapStruct)：`toResponse` + `toDetailResponse`，处理 JSON 字符串 ↔ List 转换 | P0 | 转换正确，注入 ObjectMapper |
| FR-004 | `PaperService.listPapers(int page, int size)` → `PageResponse<PaperResponse>` | P0 | page 从 1 开始，按 createdAt DESC 排序 |
| FR-005 | `PaperService.getPaperDetail(String paperId)` → `PaperDetailResponse`，`@Cacheable("paperDetail", key="#paperId", unless="#result == null")` | P0 | 缓存 30min，论文不存在抛 404 |
| FR-006 | `PaperController` 新增 2 个 GET 端点 | P0 | 仅做参数接收 + Service 调用 |
| FR-007 | JWT 鉴权：2 个端点均需 JWT 认证 | P0 | 未携带 Token 返回 401 |
| FR-008 | JSON 转换健壮性：null/空/非法 JSON → `List.of()` + log.warn | P1 | 不抛异常中断接口 |

### 5.2 跨系统一致性

- 字段命名：Java camelCase ↔ Python/JSON snake_case
- 关键映射：`paperId`↔`paper_id`、`citationCount`↔`citation_count`、`pdfUrl`↔`pdf_url`、`abstractText`↔`abstract`、`createdAt`↔`created_at`、`updatedAt`↔`updated_at`
- API 契约：
  - `GET /api/papers?page=1&size=10` → `PageResponse<PaperResponse>`
  - `GET /api/papers/{paperId}` → `PaperDetailResponse`
- 数据流转：前端请求 → PaperController → PaperService → PaperRepository.findAll/findByPaperId → Paper Entity → PaperMapper 转换（含 JSON 解析） → DTO → ApiResponse → JSON(snake_case)

### 5.3 降级要求

- 本任务不涉及 LLM 调用，无降级要求

### 5.4 安全要求

- 2 个端点均需 JWT 认证（非白名单路径）
- 论文为公共资源，不涉及用户级数据隔离
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

- Cache-Aside 模式：写 MySQL 后删 Redis 缓存
- `paperDetail` TTL = 30min（已配置，含 ±10% 随机偏移）
- 缓存 Key 使用 `RedisKeyUtil.paperDetailKey(paperId)`
- 缓存穿透防护：查询结果为空时缓存空值（TTL=60s）

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

---

## 7. Forbidden Actions（禁止行为）

- ❌ 输出伪代码或 TODO 注释
- ❌ 修改需求范围外的模块（UserService / SessionService / AnalysisService 等）
- ❌ 破坏三层分离架构（前端直接调 Python 等）
- ❌ 破坏分层调用规范（PaperController 直接操作 PaperRepository）
- ❌ Paper Entity 直接返回给前端
- ❌ 硬编码敏感配置
- ❌ 违反跨系统字段命名约定（输出 Java 驼峰而非 snake_case）
- ❌ 在循环中打印 INFO 及以上级别日志
- ❌ 使用 SQL 拼接
- ❌ Controller 中编写业务逻辑（Entity→DTO 转换、JSON 解析、Repository 调用）

---

## 8. Test Requirements（测试要求）

### 8.1 单元测试

| 测试类 | 验证点 |
|--------|--------|
| `PaperResponseTest` | `@JsonProperty` 映射：序列化/反序列化字段名为 snake_case |
| `PaperMapperTest` | JSON 字符串 ↔ List<String> 转换（含 null/空/非法 JSON 三种边界） |
| `PaperServiceTest` | listPapers 边界修正 + getPaperDetail 缓存命中（验证 Repository 不被重复调用） |

### 8.2 集成测试

- `PaperControllerTest`：完整 HTTP 链路（GET 列表/详情、未找到 404、未授权 401）

### 8.3 验证命令

```bash
cd Veritas/backend && mvn compile                                          # 编译
cd Veritas/backend && mvn test -Dtest=PaperResponseTest,PaperMapperTest,PaperServiceTest
cd Veritas/backend && mvn test                                             # 全部测试
```

---

## 9. Acceptance Criteria（验收标准）

- [ ] AC-001：`GET /api/papers?page=1&size=10` 返回 `PageResponse<PaperResponse>`
- [ ] AC-002：`GET /api/papers/{paperId}` 返回 `PaperDetailResponse`（含 abstract/pdfUrl/createdAt/updatedAt）
- [ ] AC-003：不存在的 paperId 返回 404
- [ ] AC-004：JSON 字段名使用 `snake_case`（`paper_id`/`citation_count`/`pdf_url`/`abstract`/`created_at`/`updated_at`）
- [ ] AC-005：PaperMapper 将 JSON 字符串反序列化为 `List<String>`，null/空字符串返回 `List.of()`
- [ ] AC-006：`getPaperDetail` 使用 `@Cacheable(value="paperDetail", key="#paperId", unless="#result == null")`
- [ ] AC-007：listPapers page 从 1 开始、size 默认 10、按 createdAt DESC 排序
- [ ] AC-008：未携带 Token 返回 401
- [ ] AC-009：Controller 不含业务逻辑（无 Entity→DTO 转换、无 Repository 调用）
- [ ] AC-010：所有单元测试通过，`mvn compile` + `mvn test` 均成功

---

## 10. 数据契约示例

### GET /api/papers?page=1&size=10

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
      }
    ],
    "total": 200,
    "page": 1,
    "size": 10,
    "total_pages": 20
  },
  "timestamp": 1716451200000
}
```

### GET /api/papers/arxiv_2024_001

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "paper_id": "arxiv_2024_001",
    "title": "Multi-Agent Systems: A Survey",
    "authors": ["Wang, L.", "Chen, X."],
    "year": 2024,
    "venue": "AAAI",
    "keywords": ["multi-agent", "survey"],
    "citation_count": 1200,
    "abstract": "This paper provides a comprehensive survey...",
    "pdf_url": "https://arxiv.org/pdf/2401.001",
    "created_at": "2026-05-23T10:00:00",
    "updated_at": "2026-05-23T10:00:00"
  },
  "timestamp": 1716451200000
}
```

### GET /api/papers/不存在的ID

```json
{
  "code": 404,
  "message": "Paper not found: invalid_id",
  "timestamp": 1716451200000
}
```

---

## 11. 后续建议

- 下一步（task16）将实现论文搜索功能（全文索引 + 条件过滤 + 排序），扩展 `PaperController` 和 `PaperService`
- 后续可考虑：论文收藏（`POST/DELETE /api/papers/{paperId}/favorite`）和批量导入（`POST /api/papers/import`）功能
- 论文筛选/排序（年份/会议/引用数）建议放在搜索功能中统一处理
- 性能优化方向：列表查询可考虑按 citation_count 缓存 Top-N 热门论文

---

> **任务完成后必须**：
> 1. 运行 `mvn compile && mvn test` 验证编译和测试
> 2. 手动验证 2 个端点的 HTTP 响应（使用 curl 或 Postman）
> 3. 在 `json_prompt/Coding.md` 的 backend 序号映射表中追加新行
