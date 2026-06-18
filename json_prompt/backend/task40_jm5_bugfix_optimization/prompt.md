# Task 40：JM5 Bug修复 + 代码优化（Week10 D5-7）

> **课题编号**：XH-202630
> **版本**：v0.5
> **里程碑**：JM5 缓存优化与功能完善（Week 10 Day 5-7，JM5 收尾任务）
> **功能编号**：F2.6, F2.2, F2.4
> **创建日期**：2026-06-17

---

## 1. Context（项目上下文）

### 项目
XH-202630 科研文献智能助手 — 领域知识个性化生成与多智能体协同决策系统研究

### 当前版本
v0.5 / JM5：缓存优化与功能完善（Week 10 Day 5-7，JM5 收尾任务）

### 需求描述
JM5 Bug修复 + 代码优化：
- JM5 全量集成测试（task32-task39 功能联调）
- 缓存Key冲突回归测试（paperSearch null参数问题）
- 导出功能边界测试（大文件 report > 50000 字符 / 特殊字符 / 空 citations）
- 收藏功能并发测试（重复收藏竞态，@Transactional 保证一致性）
- 性能优化（缓存命中率达标 > 50%）
- JM5 验收检查点12项逐项核对（里程碑文档§7.4）
- 更新里程碑文档状态（JM5 → ✅）
- 修复 JM4 遗留 Strong Suggestion（S-001 SSE端点路由 / S-002 字段命名不一致）— 如时间允许

### 参考文档
- `docs/backend/Java后端模块系统架构文档.md` — 全模块架构 + 第9章 缓存管理 + 第12章 API规范
- `docs/backend/Java后端模块项目里程碑文档.md` — 第7章 JM5 验收检查点12项（§7.4）+ JM4 遗留 Strong Suggestion
- `AGENTS.md` — 关键规则全部7条

---

## 2. Current Architecture（当前架构）

### 涉及层级
- java_backend
- data_layer

### 相关模块
| 模块 | 路径 | 职责 |
|------|------|------|
| UserService | `com.literatureassistant.service` | task32 完善缓存（三重失效） |
| PaperService | `com.literatureassistant.service` | task33/35 完善缓存和筛选排序 |
| FavoriteService | `com.literatureassistant.service` | task36 实现收藏（幂等+缓存） |
| SessionService | `com.literatureassistant.service` | task34 完善缓存 |
| AnalysisService | `com.literatureassistant.service` | task34 完善缓存 |
| ExportService | `com.literatureassistant.service` | task37/38 实现 PDF/Word 导出 |
| PdfExporter | `com.literatureassistant.util` | task37 实现 PDF 导出 |
| WordExporter | `com.literatureassistant.util` | task38 实现 Word 导出 |
| RedisConfig | `com.literatureassistant.config` | 7个缓存空间 |
| AnalysisController | `com.literatureassistant.controller` | task37/38 新增 export 端点 |

### 已有实现
- `UserService.java` — task32 完善：@Cacheable + @CacheEvict 三重失效
- `PaperService.java` — task33/35 完善：@Cacheable + author/keywords/sortDirection
- `FavoriteService.java` — task36 新建：收藏/取消/列表 + 幂等性
- `SessionService.java` — task34 完善：@Cacheable(sessionState/sessionList)
- `AnalysisService.java` — task34 完善：@Cacheable + 写方法 @CacheEvict
- `ExportService.java` — task37/38 新建：exportPdf/exportWord + 统一入口
- `PdfExporter.java` — task37 新建：iText 7 + 中文字体 + AI标注
- `WordExporter.java` — task38 新建：Apache POI + AI标注
- `RedisConfig.java` — 7个缓存空间配置
- `AnalysisController.java` — task37/38 新增 export 端点

---

## 3. Relevant Modules（关键模块）

### Jm5IntegrationTest（新建）
- **路径**：`Veritas/backend/src/test/java/com/literatureassistant/integration/Jm5IntegrationTest.java`
- **职责**：JM5 全量集成测试：功能联调 + 边界测试 + 并发测试 + 验收检查点核对
- **关键接口**：
  - `testJm5FullFlow()` — 全流程联调：画像 → 检索 → 收藏 → 分析 → 导出
  - `testCacheKeyConflictRegression()` — 缓存Key冲突回归测试
  - `testExportLargeReport()` — 大文件边界测试（report > 50000 字符）
  - `testExportSpecialCharacters()` — 特殊字符测试（HTML/emoji/Unicode）
  - `testExportEmptyCitations()` — 空 citations 测试
  - `testFavoriteConcurrentAdd()` — 并发收藏测试（10线程）
  - `testCacheHitRateAcceptance()` — 缓存命中率达标验证
  - `testJm5AcceptanceChecklist()` — 12项验收检查点核对

---

## 4. Files To Modify（变更文件）

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `integration/Jm5IntegrationTest.java` | JM5全量集成测试（8个测试方法） |
| 修改 | `docs/backend/Java后端模块项目里程碑文档.md` | 更新 JM5 状态为 ✅ |

---

## 5. Implementation Requirements（实现要求）

### 功能要求

| ID | 优先级 | 描述 | 验收条件 |
|----|--------|------|---------|
| FR-001 | P0 | testJm5FullFlow：全流程联调（画像→检索→收藏→分析→导出） | 全流程无异常 |
| FR-002 | P0 | testCacheKeyConflictRegression：null参数处理回归测试 | 缓存Key无冲突 |
| FR-003 | P0 | testExportLargeReport：report > 50000 字符导出不 OOM | 大文件导出成功 |
| FR-004 | P0 | testExportSpecialCharacters：HTML/emoji/Unicode 正确渲染，无XSS | 特殊字符正确 |
| FR-005 | P0 | testExportEmptyCitations：citations=null/空列表不报错 | 空citations不报错 |
| FR-006 | P0 | testFavoriteConcurrentAdd：10线程并发收藏，最终仅1条记录 | 并发无数据不一致 |
| FR-007 | P0 | testCacheHitRateAcceptance：4个Service命中率 > 50% | 命中率达标 |
| FR-008 | P0 | testJm5AcceptanceChecklist：12项验收检查点逐项核对 | 12项全部通过 |
| FR-009 | P1 | 更新里程碑文档：JM5 状态 ⬜ → ✅，交付物11项 ⬜ → ✅，检查点12项 □ → ☑ | 文档更新完成 |
| FR-010 | P2 | 修复 JM4 遗留 Strong Suggestion（如时间允许） | 修复或记录 |

### 跨系统一致性
- **字段命名**：Java camelCase ↔ Python/JSON snake_case
  - userId ↔ user_id
  - paperId ↔ paper_id
  - analysisId ↔ analysis_id
  - sessionId ↔ session_id
  - sortDirection ↔ sort_direction
  - citationCount ↔ citation_count
  - createdAt ↔ created_at
- **API契约**：
  - `GET /api/papers/search` — 检索（含筛选排序）
  - `POST/DELETE /api/papers/{paperId}/favorite` — 收藏
  - `GET /api/papers/favorites` — 收藏列表
  - `GET /api/analysis/{analysisId}/export?format=pdf|word` — 导出
- **数据流转**：全流程：用户登录 → 画像缓存 → 论文检索（筛选排序）→ 收藏 → 分析 → 导出

### 安全要求
- **JWT鉴权**：全流程所有端点必须 JWT 鉴权
- **数据隔离**：userId 来自 JWT，用户A无法访问用户B的数据
- **AI内容标注**：导出文件含"AI生成，仅供参考"
- **XSS防护**：导出特殊字符测试，PDF/Word 不执行 HTML 脚本

---

## 6. Constraints（约束）

### 命名规范
- Java: 类名PascalCase, 方法/变量camelCase, 常量UPPER_SNAKE_CASE, 文件PascalCase.java
- 数据库: 表名snake_case复数, 列名snake_case
- JSON: 字段名snake_case

### 分层规范
- Controller → Service → Repository → Client，禁止跨层
- Entity与DTO分离

### 错误处理
- BusinessException + GlobalExceptionHandler
- BusinessException含 code、message、errorKey

### 缓存策略
- Cache-Aside：写MySQL后删Redis缓存
- TTL分层：userProfile/userInfo(1h) / paperDetail(30min) / paperSearch(10min) / analysisResult(30min) / sessionState(2h) / agentState(5min) / favoriteList(10min)
- 缓存穿透防护：空值缓存 TTL=60s
- 缓存雪崩防护：TTL ±10% 随机偏移
- 单个缓存值不超过1MB

### 日志规范
- SLF4J + Logback
- 禁止循环内 INFO+ 日志

### 数据库规范
- 字符集 utf8mb4 + utf8mb4_unicode_ci
- 主键 id BIGINT AUTO_INCREMENT
- 时间字段 created_at/updated_at
- 禁止 SELECT *，分页查询

### 安全规范
- JWT Token (24h) + Redis黑名单
- 数据隔离：WHERE user_id = currentUserId
- SQL注入防护：JPA参数化查询
- AI内容标注：AI生成，仅供参考

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
| testJm5FullFlow | 全流程联调 | normal_flow |
| testCacheKeyConflictRegression | 缓存Key冲突回归 | normal_flow, boundary_condition |
| testExportLargeReport | 大文件边界测试 | boundary_condition |
| testExportSpecialCharacters | 特殊字符测试 | boundary_condition |
| testExportEmptyCitations | 空 citations 测试 | boundary_condition |
| testFavoriteConcurrentAdd | 并发收藏测试 | normal_flow, boundary_condition |
| testCacheHitRateAcceptance | 缓存命中率达标 | normal_flow |
| testJm5AcceptanceChecklist | 12项验收检查点 | normal_flow |

### 集成测试
| 测试名 | 描述 | 涉及层级 |
|--------|------|---------|
| testJm5FullFlow | 全流程联调 | java_backend, data_layer |
| testFavoriteConcurrentAdd | 并发收藏测试 | java_backend, data_layer |

### 验证命令
```bash
cd Veritas/backend && mvn test -Dtest=Jm5IntegrationTest
cd Veritas/backend && mvn test
```

---

## 9. Acceptance Criteria（验收标准）

| ID | 验收标准 | 验证方式 |
|----|---------|---------|
| AC-001 | Jm5IntegrationTest 全部通过（8个测试方法） | automated_test |
| AC-002 | 缓存Key无冲突（null参数处理正确） | automated_test |
| AC-003 | 导出大文件（report > 50000 字符）不崩溃 | automated_test |
| AC-004 | 导出特殊字符正确渲染，无XSS | automated_test |
| AC-005 | 导出空 citations 不报错 | automated_test |
| AC-006 | 收藏并发测试无数据不一致，最终仅1条记录 | automated_test |
| AC-007 | 缓存命中率 > 50% | automated_test |
| AC-008 | JM5 验收检查点12项全部 ☑ | automated_test |
| AC-009 | 里程碑文档 JM5 状态更新为 ✅ | code_review |
| AC-010 | mvn test 全量通过 | automated_test |
| AC-011 | JM4 遗留 Strong Suggestion 修复或记录 | code_review |
