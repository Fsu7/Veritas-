# Task 36：论文收藏/取消收藏 + 收藏列表API（Day 5）

> **课题编号**：XH-202630
> **版本**：v0.5
> **里程碑**：JM5 缓存优化与功能完善（Week 9 Day 5）
> **功能编号**：F2.2.4, F2.2.5, F2.2.6
> **创建日期**：2026-06-17

---

## 1. Context（项目上下文）

### 项目
XH-202630 科研文献智能助手 — 领域知识个性化生成与多智能体协同决策系统研究

### 当前版本
v0.5 / JM5：缓存优化与功能完善（Week 9 Day 5）

### 需求描述
论文收藏/取消收藏 + 收藏列表API：
- 新建 FavoriteService（收藏/取消收藏/收藏列表/收藏状态查询）
- PaperController 扩展3个端点：
  - `POST /api/papers/{paperId}/favorite`（收藏，幂等）
  - `DELETE /api/papers/{paperId}/favorite`（取消收藏，幂等）
  - `GET /api/papers/favorites`（收藏列表分页，含 paper 详情）
- 收藏列表缓存 @Cacheable(favoriteList, TTL=10min)
- 收藏操作 @CacheEvict(favoriteList)
- 数据隔离校验（userId 来自 JWT）
- 幂等性（重复收藏/取消收藏返回成功）
- 新建 FavoriteResponse DTO + FavoriteMapper

### 参考文档
- `docs/backend/Java后端模块系统架构文档.md` — 第4章 论文管理模块（收藏子模块）+ 第9章 缓存管理
- `docs/backend/Java后端模块项目里程碑文档.md` — 第7章 JM5 Week 9 Day 5
- `AGENTS.md` — 关键规则第6条 Cache-Aside + 第7条 JWT认证+数据隔离

---

## 2. Current Architecture（当前架构）

### 涉及层级
- java_backend
- data_layer

### 相关模块
| 模块 | 路径 | 职责 |
|------|------|------|
| PaperFavorite | `com.literatureassistant.entity` | 论文收藏Entity已存在，含 id/userId/paperId/createdAt + @PrePersist |
| PaperFavoriteRepository | `com.literatureassistant.repository` | 收藏Repository已存在3方法 |
| PaperController | `com.literatureassistant.controller` | 当前3端点，需扩展3个收藏端点 |
| RedisConfig | `com.literatureassistant.config` | 已配置6个缓存空间，需新增 favoriteList |
| PaperMapper | `com.literatureassistant.mapper` | 已存在 PaperMapper（MapStruct），可参考其模式 |

### 已有实现
- `PaperFavorite.java` — Entity：@Data @Builder @Entity @Table(paper_favorites)，字段 id/userId/paperId/createdAt
- `PaperFavoriteRepository.java` — findByUserIdOrderByCreatedAtDesc/existsByUserIdAndPaperId/deleteByUserIdAndPaperId
- `PaperController.java` — @RestController @RequestMapping(/api/papers)，已有 listPapers/searchPapers/getPaperDetail
- `RedisConfig.java` — cacheManager 配置6个缓存空间，TTL_JITTER_RATIO=0.1
- `PaperMapper.java` — @Mapper(componentModel=spring) + @Mapping qualifiedByName=jsonToList
- `PaperResponse.java` — paperId/title/authors/year/venue/keywords/citationCount + @JsonProperty snake_case
- `RedisKeyUtil.java` — 已有10个key方法，需新增 favoriteListKey(userId)

---

## 3. Relevant Modules（关键模块）

### FavoriteService（新建）
- **路径**：`Veritas/backend/src/main/java/com/literatureassistant/service/FavoriteService.java`
- **职责**：论文收藏业务：收藏/取消收藏/收藏列表/收藏状态查询，含缓存与幂等性
- **关键接口**：
  - `addFavorite(String userId, String paperId)` — 收藏论文（幂等）
  - `removeFavorite(String userId, String paperId)` — 取消收藏（幂等）
  - `listFavorites(String userId, int page, int size)` — 分页查询收藏列表（含 paper 详情）
  - `isFavorite(String userId, String paperId)` — 查询收藏状态

### PaperController（扩展）
- **路径**：`Veritas/backend/src/main/java/com/literatureassistant/controller/PaperController.java`
- **职责**：论文Controller，扩展3个收藏端点
- **关键接口**：
  - `addFavorite(@PathVariable paperId, @AuthenticationPrincipal userId)` — POST 收藏端点
  - `removeFavorite(@PathVariable paperId, @AuthenticationPrincipal userId)` — DELETE 取消收藏端点
  - `listFavorites(@AuthenticationPrincipal userId, page, size)` — GET 收藏列表端点

### FavoriteResponse（新建）
- **路径**：`Veritas/backend/src/main/java/com/literatureassistant/dto/response/FavoriteResponse.java`
- **职责**：收藏响应DTO，含收藏记录信息 + 论文详情
- **字段**：favoriteId/paperId(@JsonProperty paper_id)/title/authors/year/venue/citationCount(@JsonProperty citation_count)/createdAt(@JsonProperty created_at)

### FavoriteMapper（新建）
- **路径**：`Veritas/backend/src/main/java/com/literatureassistant/mapper/FavoriteMapper.java`
- **职责**：PaperFavorite + Paper → FavoriteResponse 转换
- **关键接口**：`toResponse(PaperFavorite favorite, Paper paper)`

---

## 4. Files To Modify（变更文件）

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `service/FavoriteService.java` | 新建收藏服务：addFavorite/removeFavorite/listFavorites/isFavorite，含 @Cacheable/@CacheEvict/@Transactional |
| 修改 | `controller/PaperController.java` | 扩展3个收藏端点：POST/DELETE/GET |
| 新增 | `dto/response/FavoriteResponse.java` | 新建收藏响应DTO，@JsonProperty snake_case |
| 新增 | `mapper/FavoriteMapper.java` | 新建 FavoriteMapper（MapStruct） |
| 修改 | `util/RedisKeyUtil.java` | 新增 favoriteListKey(userId) 方法 |
| 修改 | `config/RedisConfig.java` | 新增 favoriteList 缓存空间，TTL=10min |
| 新增 | `service/FavoriteServiceTest.java` | 收藏服务单元测试 |

---

## 5. Implementation Requirements（实现要求）

### 功能要求

| ID | 优先级 | 描述 | 验收条件 |
|----|--------|------|---------|
| FR-001 | P0 | POST /api/papers/{paperId}/favorite 收藏端点，JWT鉴权，幂等 | 重复收藏返回200成功 |
| FR-002 | P0 | DELETE /api/papers/{paperId}/favorite 取消收藏端点，幂等 | 重复取消返回200成功 |
| FR-003 | P0 | GET /api/papers/favorites 收藏列表分页，含论文详情 | 返回 PageResponse<FavoriteResponse> |
| FR-004 | P0 | 数据隔离：userId 来自 JWT，禁止前端传入 | userId 仅来自 @AuthenticationPrincipal |
| FR-005 | P0 | listFavorites 添加 @Cacheable(favoriteList, key=#userId)，TTL=10min | 相同 userId 第二次命中缓存 |
| FR-006 | P0 | addFavorite/removeFavorite 添加 @CacheEvict(favoriteList, key=#userId) | 写操作后缓存立即失效 |
| FR-007 | P1 | 幂等性：addFavorite 先判断 existsByUserIdAndPaperId，已存在直接返回 | 重复操作不产生副作用 |
| FR-008 | P1 | 收藏前校验 paperId 存在性，不存在抛 ResourceNotFoundException | 收藏不存在论文抛异常 |
| FR-009 | P0 | FavoriteResponse DTO 字段完整，JSON 输出 snake_case | DTO 字段完整 |
| FR-010 | P0 | FavoriteMapper 使用 MapStruct，authors/keywords 使用 JsonStringListHelper | Mapper 正确转换 |
| FR-011 | P0 | RedisKeyUtil 新增 favoriteListKey(userId)，返回 'user:favorites:' + userId | key 格式正确 |
| FR-012 | P0 | RedisConfig 新增 favoriteList 缓存空间，TTL=10min±10% | 缓存空间配置正确 |
| FR-013 | P0 | FavoriteService 使用 @Transactional：写操作 @Transactional，读操作 @Transactional(readOnly=true) | 事务注解正确 |

### 跨系统一致性
- **字段命名**：Java camelCase ↔ Python/JSON snake_case
  - paperId ↔ paper_id
  - userId ↔ user_id
  - favoriteId ↔ favorite_id
  - citationCount ↔ citation_count
  - createdAt ↔ created_at
- **API契约**：
  - `POST /api/papers/{paperId}/favorite` → ApiResponse<FavoriteResponse>
  - `DELETE /api/papers/{paperId}/favorite` → ApiResponse<Void>
  - `GET /api/papers/favorites?page=1&size=10` → ApiResponse<PageResponse<FavoriteResponse>>
- **数据流转**：前端 → PaperController(@AuthenticationPrincipal) → FavoriteService(@Cacheable/@CacheEvict/@Transactional) → PaperFavoriteRepository → MySQL paper_favorites 表

### 安全要求
- **JWT鉴权**：所有3个收藏端点必须 JWT 鉴权，userId 从 @AuthenticationPrincipal 获取
- **数据隔离**：查询/操作强制 WHERE user_id = currentUserId
- **SQL注入防护**：使用 Spring Data JPA 参数化查询

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
- favoriteList TTL=10min
- 缓存穿透防护：空值缓存 TTL=60s
- 缓存雪崩防护：TTL ±10% 随机偏移
- 单个缓存值不超过1MB

### 日志规范
- SLF4J + Logback
- 禁止在循环中打印INFO及以上级别日志
- 禁止输出敏感信息

### 数据库规范
- 字符集 utf8mb4 + utf8mb4_unicode_ci
- 主键 id BIGINT AUTO_INCREMENT
- 时间字段 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- 禁止 SELECT *，明确列出查询字段
- 大表查询必须分页

### 安全规范
- JWT Token (24h有效期) + Redis黑名单
- 数据隔离：WHERE user_id = currentUserId
- SQL注入防护：JPA参数化查询

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
| FA-009 | 使用SQL拼接 | SQL注入防护 | critical |
| FA-010 | 忽略降级场景 | 可用性约束ADR-003 | high |

---

## 8. Test Requirements（测试要求）

### 单元测试
| 测试名 | 描述 | 覆盖场景 |
|--------|------|---------|
| testAddFavorite | 验证收藏论文返回 FavoriteResponse | normal_flow |
| testAddFavoriteIdempotent | 验证重复收藏不抛异常 | boundary_condition |
| testAddFavoritePaperNotFound | 验证收藏不存在论文抛异常 | error_flow |
| testRemoveFavorite | 验证取消收藏 | normal_flow |
| testRemoveFavoriteIdempotent | 验证重复取消不抛异常 | boundary_condition |
| testListFavorites | 验证收藏列表分页，含论文详情 | normal_flow |
| testListFavoritesEmpty | 验证空收藏列表 | boundary_condition |
| testCacheEvictOnAdd | 验证收藏操作后缓存失效 | normal_flow |
| testCacheEvictOnRemove | 验证取消收藏后缓存失效 | normal_flow |
| testDataIsolation | 验证数据隔离 | normal_flow, boundary_condition |

### 验证命令
```bash
cd Veritas/backend && mvn test -Dtest=FavoriteServiceTest
cd Veritas/backend && mvn test
```

---

## 9. Acceptance Criteria（验收标准）

| ID | 验收标准 | 验证方式 |
|----|---------|---------|
| AC-001 | POST 收藏端点返回 ApiResponse<FavoriteResponse> | automated_test |
| AC-002 | 重复收藏不报错（幂等性） | automated_test |
| AC-003 | DELETE 取消收藏后 existsByUserIdAndPaperId 返回 false | automated_test |
| AC-004 | GET 收藏列表分页正确，含论文详情 | automated_test |
| AC-005 | 收藏/取消操作后 favoriteList 缓存立即失效 | automated_test |
| AC-006 | 数据隔离 — 用户A无法查询用户B的收藏 | automated_test |
| AC-007 | userId 来自 JWT，禁止前端传入 | code_review |
| AC-008 | 收藏不存在的论文抛 ResourceNotFoundException | automated_test |
| AC-009 | FavoriteResponse JSON 输出 snake_case | code_review |
| AC-010 | mvn test 全量通过 | automated_test |
