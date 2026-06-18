# Task 33: 论文检索缓存 + 论文详情缓存完善

> **课题编号**：XH-202630
> **版本**：v0.5
> **里程碑**：JM5 缓存优化与功能完善（Week 9 Day 2）
> **功能编号**：F2.6.2, F2.2.1, F2.2.2, F2.2.3
> **创建日期**：2026-06-17

---

## 1. Context

### 1.1 项目
XH-202630 科研文献智能助手 — 领域知识个性化生成与多智能体协同决策系统研究

### 1.2 当前版本
v0.5 / JM5：缓存优化与功能完善（Week 9 Day 2）

### 1.3 需求描述
完善论文检索缓存与论文详情缓存：
- 修复 `paperSearch` 复合key中null参数拼成'null'字符串的风险
- 为 `listPapers` 方法添加缓存（TTL=10min）
- 实现缓存穿透防护（论文不存在时缓存空值TTL=60s）
- 缓存Key规范化使用RedisKeyUtil统一生成
- 验证 paperDetail/paperSearch 缓存命中率

### 1.4 参考文档
- `docs/backend/Java后端模块系统架构文档.md` — 第5章 论文管理模块 + 第9章 缓存管理模块
- `docs/backend/Java后端模块项目里程碑文档.md` — 第7章 JM5 Day 2 任务分解
- `AGENTS.md` — 关键规则第6条 Cache-Aside

---

## 2. Current Architecture

### 2.1 涉及层级
- java_backend
- data_layer（Redis）

### 2.2 相关模块
| 模块路径 | 职责 |
|---------|------|
| `com.literatureassistant.service.PaperService` | 论文管理业务，已实现缓存注解但有缺陷 |
| `com.literatureassistant.repository.PaperRepositoryCustomImpl` | 论文搜索自定义查询 |
| `com.literatureassistant.util.RedisKeyUtil` | Redis Key生成工具 |

### 2.3 已有实现
| 文件 | 描述 | 复用方式 |
|------|------|---------|
| `service/PaperService.java` | 已实现@Cacheable(paperDetail/paperSearch)，listPapers未缓存，复合key有null风险 | 扩展 |
| `repository/PaperRepositoryCustomImpl.java` | 已实现搜索+排序白名单 | 直接复用 |
| `config/RedisConfig.java` | 已配置paperDetail(30min)/paperSearch(10min) | 直接复用 |
| `util/RedisKeyUtil.java` | 已实现userProfileKey等方法 | 扩展 |

---

## 3. Relevant Modules

### 3.1 PaperService
- **路径**：`Veritas/backend/src/main/java/com/literatureassistant/service/PaperService.java`
- **职责**：论文管理业务，列表/详情/搜索，缓存管理
- **关键接口**：
  - `PageResponse<PaperResponse> listPapers(int page, int size)` — 当前未加缓存
  - `@Cacheable(value="paperDetail", key="#paperId") PaperDetailResponse getPaperDetail(String paperId)`
  - `@Cacheable(value="paperSearch", key="...复合key...") PageResponse<PaperResponse> searchPapers(...)` — 复合key有null风险

### 3.2 RedisKeyUtil
- **路径**：`Veritas/backend/src/main/java/com/literatureassistant/util/RedisKeyUtil.java`
- **职责**：Redis Key统一生成工具

---

## 4. Files To Modify

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 修改 | `service/PaperService.java` | 完善缓存注解：listPapers加缓存、getPaperDetail空值防护、searchPapers修复null key |
| 修改 | `util/RedisKeyUtil.java` | 新增 paperDetailKey/paperSearchKey/paperListKey 方法 |
| 修改 | `config/RedisConfig.java` | 新增 paperList 缓存空间（TTL=10min） |
| 新增 | `test/.../PaperServiceCacheTest.java` | 缓存命中、穿透防护、null key测试 |

---

## 5. Implementation Requirements

### 5.1 功能要求

| ID | 描述 | 优先级 | 验收条件 |
|----|------|--------|---------|
| FR-001 | 修复 paperSearch 复合key中null参数拼成'null'字符串的风险，使用RedisKeyUtil统一生成 | P0 | null参数不再拼成'null'字符串 |
| FR-002 | 为 listPapers 添加@Cacheable(paperList)，TTL=10min | P1 | 第二次调用直接返回缓存 |
| FR-003 | 完善 getPaperDetail 缓存穿透防护 | P1 | 论文不存在时缓存策略正确 |
| FR-004 | RedisKeyUtil 新增 paperDetailKey/paperSearchKey/paperListKey 方法 | P0 | 3个方法实现正确，null参数处理合理 |
| FR-005 | RedisConfig 新增 paperList 缓存空间（TTL=10min） | P1 | RedisConfig包含paperList，TTL=10min |
| FR-006 | 验证 paperDetail/paperSearch 缓存命中率 | P1 | 缓存命中率测试通过 |

### 5.2 跨系统一致性
- **字段命名**：Java camelCase ↔ Python/JSON snake_case
- **关键字段映射**：paperId↔paper_id, citationCount↔citation_count, abstractText↔abstract_text, pdfUrl↔pdf_url
- **数据流转**：前端 → Java PaperService（@Cacheable）→ MySQL papers 表

### 5.3 安全要求
- **数据隔离**：论文数据为公共数据，无需userId隔离
- **SQL注入**：缓存Key生成不得引入新的注入风险

---

## 6. Constraints

### 6.1 命名规范
- Java: 类名PascalCase, 方法/变量camelCase, 常量UPPER_SNAKE_CASE
- 数据库: 表名snake_case复数, 列名snake_case
- JSON: 字段名snake_case

### 6.2 分层规范
- Controller → Service → Repository → Client，禁止跨层
- Entity与DTO分离

### 6.3 缓存策略
- **模式**：Cache-Aside，写MySQL后删Redis缓存
- **TTL分层**：
  - paperDetail: 30min (27min~33min with ±10% jitter)
  - paperSearch: 10min (9min~11min with ±10% jitter)
  - paperList: 10min (9min~11min with ±10% jitter)
- **穿透防护**：查询结果为空时缓存空值（TTL=60s）
- **雪崩防护**：TTL添加±10%随机偏移
- **大小限制**：单个缓存值不超过1MB

### 6.4 日志规范
- SLF4J + Logback，禁止循环中打印INFO+日志，禁止输出敏感信息

### 6.5 数据库规范
- utf8mb4 + InnoDB，主键 id BIGINT AUTO_INCREMENT，禁止SELECT *

### 6.6 安全规范
- JPA参数化查询，禁止SQL拼接

---

## 7. Forbidden Actions

| ID | 禁止行为 | 原因 | 严重程度 |
|----|---------|------|---------|
| FA-001 | 输出伪代码或TODO注释 | 必须输出完整可执行代码 | critical |
| FA-002 | 修改需求范围外的模块 | 本任务仅涉及PaperService/RedisKeyUtil/RedisConfig | high |
| FA-003 | 破坏三层分离架构 | 架构约束ADR-001 | critical |
| FA-004 | 破坏分层调用规范 | 分层架构约束 | critical |
| FA-005 | Entity直接返回给前端 | 数据隔离与接口稳定性 | high |
| FA-006 | 硬编码敏感配置 | 安全约束 | critical |
| FA-007 | 违反跨系统字段命名约定 | 跨系统一致性约束 | high |
| FA-008 | 在循环中打印INFO及以上级别日志 | 性能约束 | medium |
| FA-009 | 使用SQL拼接 | SQL注入防护 | critical |
| FA-010 | 忽略降级场景 | 可用性约束 | high |

---

## 8. Test Requirements

### 8.1 单元测试

| 测试名称 | 描述 | 覆盖场景 |
|---------|------|---------|
| `PaperServiceCacheTest.getPaperDetail_cacheHit_returnsCached` | 验证paperDetail缓存命中 | normal_flow |
| `PaperServiceCacheTest.searchPapers_cacheHit_returnsCached` | 验证paperSearch缓存命中 | normal_flow |
| `PaperServiceCacheTest.searchPapers_nullParams_noKeyConflict` | 验证null参数不产生key冲突 | boundary_condition |
| `PaperServiceCacheTest.listPapers_cacheHit_returnsCached` | 验证paperList缓存命中 | normal_flow |
| `PaperServiceCacheTest.getPaperDetail_notFound_penetrationProtection` | 验证缓存穿透防护 | boundary_condition |
| `RedisKeyUtilTest.paperSearchKey_nullParams_handled` | 验证null参数处理 | boundary_condition |
| `RedisKeyUtilTest.paperDetailKey_format` | 验证Key格式 | normal_flow |
| `RedisKeyUtilTest.paperListKey_format` | 验证Key格式 | normal_flow |

### 8.2 验证命令
```bash
cd Veritas/backend && mvn test -Dtest=PaperServiceCacheTest
cd Veritas/backend && mvn test -Dtest=RedisKeyUtilTest
cd Veritas/backend && mvn compile
```

---

## 9. Acceptance Criteria

- [ ] AC-001: paperSearch复合key中null参数不再拼成'null'字符串
- [ ] AC-002: listPapers方法添加@Cacheable(paperList)缓存，TTL=10min
- [ ] AC-003: getPaperDetail缓存穿透防护生效
- [ ] AC-004: RedisKeyUtil新增3个方法，null参数处理合理
- [ ] AC-005: RedisConfig新增paperList缓存空间，TTL=10min
- [ ] AC-006: paperDetail/paperSearch缓存命中率验证通过
- [ ] AC-007: 未修改PaperService以外的Service类
- [ ] AC-008: mvn test 全部通过
