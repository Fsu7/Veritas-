# 论文管理模块开发（F2.2 列表 / 详情 / 搜索）

## 功能描述

### 解决问题
- 后端无论文管理 API，前端无法拉取论文列表/详情/搜索结果
- 已有的 `PaperRepositoryCustomImpl`（task09）已实现 MySQL FULLTEXT 底层 SQL，但**无 Service 业务编排、Controller 端点、DTO 转换**
- AI 服务的混合检索（RAG）需要 Java 后端提供论文元数据查询/检索 API 作为数据源

### 实现功能
- **F2.2.1 论文列表**：分页查询论文，按 `createdAt DESC` 排序，30min 内缓存空值防穿透
- **F2.2.2 论文详情**：按 `paperId` 查询单篇，30min Redis 缓存（`paperDetail` 缓存区）
- **F2.2.3 论文搜索**：基于 MySQL FULLTEXT（ngram 中文分词），支持年份范围 + 会议过滤 + 相关度/年份/引用数排序，10min Redis 缓存（`paperSearch` 缓存区）

### 业务价值
- 为前端 F1.2 论文检索页面提供完整 API（与 Python AI 服务契约对齐）
- 缓存策略降低 MySQL 高频查询压力
- snake_case JSON 字段命名统一跨系统（Java↔Python↔Vue3）
- 为 F2.4 分析服务提供论文元数据查询能力（详情/收藏功能可复用）

---

## 实现逻辑

### 修改的核心文件列表

#### 业务代码（5 个新增）
| 文件 | 作用 |
|------|------|
| `dto/response/PaperResponse.java` | 论文列表项 DTO（7 字段，snake_case） |
| `dto/response/PaperDetailResponse.java` | 论文详情 DTO（继承 + 4 字段） |
| `mapper/PaperMapper.java` | MapStruct 映射器，JSON 字符串 ↔ List 转换 |
| `service/PaperService.java` | 业务编排：listPapers / getPaperDetail / searchPapers |
| `controller/PaperController.java` | 3 个 GET 端点 |

#### 增强（1 个修改）
| 文件 | 变更点 |
|------|--------|
| `exception/GlobalExceptionHandler.java` | 新增 `IllegalArgumentException → 400` 和 `MissingServletRequestParameterException → 400` 处理器 |

#### 测试代码（5 个新增）
| 文件 | 测试数 |
|------|--------|
| `test/dto/response/PaperResponseTest.java` | 4 |
| `test/mapper/PaperMapperTest.java` | 6 |
| `test/service/PaperServiceTest.java` | 6 |
| `test/service/PaperServiceSearchTest.java` | 9 |
| `test/controller/PaperControllerTest.java` | 8 |

### 使用的算法或设计模式
- **MapStruct 1.5.5 + Spring `uses` 注入**：自定义 JSON 转换通过 `JsonStringListHelper` Spring `@Component` 注入到生成的 `Impl`
- **Cache-Aside 模式**：`@Cacheable` 缓存读，`@CacheEvict` 缓存写
- **TTL 抖动防雪崩**：RedisConfig 已配置 ±10% 随机偏移
- **参数边界静默修正**：`page<1→1`、`size<1→10`、`size>100→100`
- **白名单降级**：非法 `sort` 值降级为 `relevance` + `log.warn`
- **@SuperBuilder 继承**：DTO 子类继承父类 Builder 链入父类字段

### 关键代码逻辑说明

#### PaperMapper 接口化 + Helper 注入
```java
@Mapper(componentModel = "spring", uses = {PaperMapper.JsonStringListHelper.class})
public interface PaperMapper {
    @Mapping(target = "authors", source = "authors", qualifiedByName = "jsonToList")
    PaperResponse toResponse(Paper paper);
    
    @Component
    class JsonStringListHelper {
        private final ObjectMapper objectMapper;
        // 4 场景容错：null/空串/合法 JSON/非法 JSON
    }
}
```

**为什么用 interface + Helper 而不是 abstract class？**
- Eclipse JDT 增量构建中，`abstract class @Mapper` 触发 MapStruct 在 Filer 中**重复创建**同名 `PaperMapperImpl.java`，导致 `FilerException: Source file already created`
- `interface` + `uses` 模式让 MapStruct 生成 `implements PaperMapper`（而非 `extends`），仅一次 Filer 调用

#### PaperService 三个方法

```java
// 列表
public PageResponse<PaperResponse> listPapers(int page, int size) {
    // 边界修正 + PageRequest + 映射
}

// 详情（30min 缓存）
@Cacheable(value = "paperDetail", key = "#paperId", unless = "#result == null")
public PaperDetailResponse getPaperDetail(String paperId) { ... }

// 搜索（10min 缓存 + 7 维 Key 隔离）
@Cacheable(value = "paperSearch",
    key = "T(java.lang.String).format('%s_%s_%s_%s_%s_%d_%d', #q, #yearFrom, #yearTo, #venue, #sort, #page, #size)")
public PageResponse<PaperResponse> searchPapers(...) {
    // q 校验 + yearFrom<=yearTo 校验 + sort 白名单 + 边界修正
}
```

---

## 接口变更

### 1. `GET /api/papers` — 论文列表

**Request**:
```
GET /api/papers?page=1&size=10
Authorization: Bearer <jwt-token>
```

**Response**:
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
  "timestamp": 1717209600000
}
```

### 2. `GET /api/papers/{paperId}` — 论文详情

**Request**:
```
GET /api/papers/arxiv_2024_001
Authorization: Bearer <jwt-token>
```

**Response**:
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
  "timestamp": 1717209600000
}
```

**Error Response（404）**:
```json
{
  "code": 404,
  "message": "Paper not found: nonexistent",
  "timestamp": 1717209600000
}
```

### 3. `GET /api/papers/search` — 论文搜索

**Request**:
```
GET /api/papers/search?q=multi-agent&yearFrom=2020&yearTo=2024&venue=AAAI&sort=relevance&page=1&size=10
Authorization: Bearer <jwt-token>
```

| Query Param | 必填 | 默认 | 说明 |
|-------------|------|------|------|
| `q` | ✅ | — | 搜索关键词（trim 后非空） |
| `yearFrom` | ❌ | — | 年份范围起始 |
| `yearTo` | ❌ | — | 年份范围结束 |
| `venue` | ❌ | — | 会议/期刊精确匹配 |
| `sort` | ❌ | `relevance` | `relevance` / `year` / `citations` |
| `page` | ❌ | `1` | 页码（从 1 开始） |
| `size` | ❌ | `10` | 每页条数（最大 100） |

**Response**: 同 `/api/papers` 的 `data` 结构

**Error Response（400）**:
```json
{
  "code": 400,
  "message": "缺少必填参数: q",
  "timestamp": 1717209600000
}
```

---

## 测试结果

| 测试类 | 测试场景 | 结果 |
|--------|---------|------|
| **PaperResponseTest** | 序列化输出 snake_case | ✅ 通过 |
| | 反序列化 snake_case JSON 映射 | ✅ 通过 |
| | PaperDetailResponse 序列化使用 `abstract` 字段名 | ✅ 通过 |
| | PaperDetailResponse 反序列化 `abstract` → `abstractText` | ✅ 通过 |
| **PaperMapperTest** | JSON 字符串正确解析为 List | ✅ 通过 |
| | authors/keywords 为 null 返回空列表 | ✅ 通过 |
| | authors/keywords 为空字符串返回空列表 | ✅ 通过 |
| | 非法 JSON 不抛异常，返回空列表 | ✅ 通过 |
| | toDetailResponse 完整映射 | ✅ 通过 |
| | toDetailResponse abstract 为 null | ✅ 通过 |
| **PaperServiceTest** | listPapers 正常分页（page-1） | ✅ 通过 |
| | listPapers page<1 修正为 1 | ✅ 通过 |
| | listPapers size<1 修正为 10 | ✅ 通过 |
| | listPapers size>100 限制为 100 | ✅ 通过 |
| | getPaperDetail 正常返回 | ✅ 通过 |
| | getPaperDetail 不存在抛 404 | ✅ 通过 |
| **PaperServiceSearchTest** | 正常搜索返回 PageResponse | ✅ 通过 |
| | q 为 null 抛 IllegalArgumentException | ✅ 通过 |
| | q 为空白抛 IllegalArgumentException | ✅ 通过 |
| | yearFrom>yearTo 抛 BusinessException | ✅ 通过 |
| | sort 非法值降级为 relevance | ✅ 通过 |
| | page<1 修正为 1 | ✅ 通过 |
| | size>100 限制为 100 | ✅ 通过 |
| | 无结果返回空 PageResponse | ✅ 通过 |
| | 批量调用 paperMapper.toResponse | ✅ 通过 |
| **PaperControllerTest** | GET /api/papers 返回 snake_case JSON | ✅ 通过 |
| | GET /api/papers 默认参数 | ✅ 通过 |
| | GET /api/papers/{id} 返回详情 JSON | ✅ 通过 |
| | GET /api/papers/{id} 不存在返回 404 | ✅ 通过 |
| | GET /api/papers/search 正常返回 | ✅ 通过 |
| | GET /api/papers/search 缺少 q 返回 400 | ✅ 通过 |
| | GET /api/papers/search q 为空返回 400 | ✅ 通过 |
| | GET /api/papers/search yearFrom>yearTo 返回 400 | ✅ 通过 |

**汇总**：
- 新增 33 个测试 **全部通过** ✅
- 完整测试套件 186/186 通过，剩余 4 个 `UserControllerTest` 失败为 pre-existing 已知问题（task12 plan 的 P2 修复项，与本任务无关）

---

## 相关文件

### 新增源代码
- [PaperResponse.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/main/java/com/literatureassistant/dto/response/PaperResponse.java)
- [PaperDetailResponse.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/main/java/com/literatureassistant/dto/response/PaperDetailResponse.java)
- [PaperMapper.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/main/java/com/literatureassistant/mapper/PaperMapper.java)
- [PaperService.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/main/java/com/literatureassistant/service/PaperService.java)
- [PaperController.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/main/java/com/literatureassistant/controller/PaperController.java)

### 修改源代码
- [GlobalExceptionHandler.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/main/java/com/literatureassistant/exception/GlobalExceptionHandler.java)

### 新增测试
- [PaperResponseTest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/test/java/com/literatureassistant/dto/response/PaperResponseTest.java)
- [PaperMapperTest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/test/java/com/literatureassistant/mapper/PaperMapperTest.java)
- [PaperServiceTest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/test/java/com/literatureassistant/service/PaperServiceTest.java)
- [PaperServiceSearchTest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/test/java/com/literatureassistant/service/PaperServiceSearchTest.java)
- [PaperControllerTest.java](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/backend/src/test/java/com/literatureassistant/controller/PaperControllerTest.java)

### 复用但未修改
- `entity/Paper.java` — 已存在的 JPA 实体
- `repository/PaperRepository.java` / `PaperRepositoryCustom.java` / `PaperRepositoryCustomImpl.java` — task09 已实现
- `config/RedisConfig.java` — paperDetail / paperSearch 缓存空间已配置
- `config/SecurityConfig.java` — `anyRequest().authenticated()` 已覆盖
- `dto/common/PageResponse.java` / `ApiResponse.java` / `ErrorCode.java` — 通用响应封装
- `exception/BusinessException.java` / `ResourceNotFoundException.java` — 异常体系
- `util/RedisKeyUtil.java` — Key 工具（已含 `paperDetailKey` / `searchResultKey`）

### 过程产物
- [plan_task15_16_paper_module.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/.trae/documents/plan_task15_16_paper_module.md) — 实施计划

### 配置变更
- 无（复用现有 `paperDetail` / `paperSearch` 缓存空间）
