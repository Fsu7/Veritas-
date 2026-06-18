# Task 38：Word导出服务（Day 8-9）

> **课题编号**：XH-202630
> **版本**：v0.5
> **里程碑**：JM5 缓存优化与功能完善（Week 9 Day 8-9）
> **功能编号**：F2.4.8（新增）
> **创建日期**：2026-06-17

---

## 1. Context（项目上下文）

### 项目
XH-202630 科研文献智能助手 — 领域知识个性化生成与多智能体协同决策系统研究

### 当前版本
v0.5 / JM5：缓存优化与功能完善（Week 9 Day 8-9）

### 需求描述
Word导出服务：
- pom.xml 引入 Apache POI（5.2.3）
- 新建 WordExporter 工具类（Markdown→Word .docx 转换：标题/段落/列表/代码块；citations 渲染为引用列表；AI内容标注"AI生成，仅供参考"；文件命名 `analysis_{analysisId}_{timestamp}.docx`）
- ExportService 扩展支持 format=word
- AnalysisController export 端点扩展支持 format=word
- format 参数校验（仅允许 pdf/word，否则抛 BusinessException）

### 参考文档
- `docs/backend/Java后端模块系统架构文档.md` — 第5章 分析服务模块（导出子模块）+ 第12章 API规范
- `docs/backend/Java后端模块项目里程碑文档.md` — 第7章 JM5 Week 9 Day 8-9
- `AGENTS.md` — 关键规则第7条 JWT认证+数据隔离 + 安全底线 AI内容标注

---

## 2. Current Architecture（当前架构）

### 涉及层级
- java_backend

### 相关模块
| 模块 | 路径 | 职责 |
|------|------|------|
| AnalysisController | `com.literatureassistant.controller` | task37 已新增 export 端点（format=pdf），本任务扩展 format=word |
| ExportService | `com.literatureassistant.service` | task37 已实现 exportPdf，本任务扩展 exportWord + 统一 export 入口 |
| AnalysisResultDTO | `com.literatureassistant.dto.response` | 分析结果DTO：report + citations + status |
| PdfExporter | `com.literatureassistant.util` | task37 已实现，本任务新建 WordExporter 与之并列 |

### 已有实现
- `pom.xml` — task37 已引入 iText 7，本任务新增 Apache POI
- `AnalysisController.java` — task37 已新增 exportAnalysis 端点（format=pdf）
- `ExportService.java` — task37 已实现 exportPdf(userId, analysisId)
- `AnalysisResultDTO.java` — report(String Markdown) + citations(List<Map>) + status
- `BusinessException.java` — 业务异常（code/message/errorKey）

---

## 3. Relevant Modules（关键模块）

### WordExporter（新建）
- **路径**：`Veritas/backend/src/main/java/com/literatureassistant/util/WordExporter.java`
- **职责**：Word导出工具类：Markdown→Word .docx 转换，citations渲染，AI标注，文件命名
- **关键接口**：
  - `export(String analysisId, AnalysisResultDTO result)` — 导出Word，返回byte[]
  - `renderMarkdown(XWPFDocument, String markdown)` — Markdown→Word渲染
  - `renderCitations(XWPFDocument, List<Map> citations)` — citations 渲染为引用列表
  - `addFooter(XWPFDocument)` — 添加页脚"AI生成，仅供参考"
  - `generateFileName(String analysisId)` — 生成文件名

### ExportService（扩展）
- **路径**：`Veritas/backend/src/main/java/com/literatureassistant/service/ExportService.java`
- **职责**：导出编排服务，扩展支持 format=word
- **关键接口**：
  - `exportWord(String userId, String analysisId)` — Word导出编排
  - `export(String userId, String analysisId, String format)` — 统一导出入口

### AnalysisController（扩展）
- **路径**：`Veritas/backend/src/main/java/com/literatureassistant/controller/AnalysisController.java`
- **职责**：export 端点扩展支持 format=word
- **关键接口**：`exportAnalysis(@PathVariable analysisId, @RequestParam format, @AuthenticationPrincipal userId)`

---

## 4. Files To Modify（变更文件）

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 修改 | `pom.xml` | 新增 Apache POI 依赖：poi-ooxml:5.2.3 |
| 新增 | `util/WordExporter.java` | 新建Word导出工具类 |
| 修改 | `service/ExportService.java` | 新增 exportWord + 统一 export 入口 |
| 修改 | `controller/AnalysisController.java` | export 端点扩展支持 format=word |
| 新增 | `util/WordExporterTest.java` | Word导出单元测试 |

---

## 5. Implementation Requirements（实现要求）

### 功能要求

| ID | 优先级 | 描述 | 验收条件 |
|----|--------|------|---------|
| FR-001 | P0 | pom.xml 引入 Apache POI：poi-ooxml:5.2.3 | mvn compile 成功 |
| FR-002 | P0 | WordExporter.export 创建 XWPFDocument → 渲染 Markdown → 渲染 citations → 页脚 → 返回 byte[] | 返回非空 byte[] |
| FR-003 | P0 | renderMarkdown 支持 #/##/### 标题、段落、- 列表、``` 代码块 | Markdown 语法正确渲染 |
| FR-004 | P0 | 中文字体支持：setFontFamily('宋体') 或 'Microsoft YaHei' | 中文不乱码 |
| FR-005 | P0 | renderCitations 渲染为 '[index] citation_text'，空 citations 不渲染 section | citations 正确渲染 |
| FR-006 | P0 | addFooter 每页页脚居中显示 'AI生成，仅供参考' | 页脚显示 |
| FR-007 | P0 | generateFileName 返回 analysis_{analysisId}_{yyyyMMddHHmmss}.docx | 文件名规范 |
| FR-008 | P0 | ExportService.exportWord：校验 → 查结果 → 状态校验 → 调 WordExporter | 导出编排正确 |
| FR-009 | P0 | ExportService 统一 export(userId, id, format) 入口：pdf/word 分发，非法抛 BusinessException | 统一入口正确 |
| FR-010 | P0 | exportAnalysis 端点支持 format=word，Content-Type 正确 | 两种 format 均返回正确 Content-Type |
| FR-011 | P0 | 数据隔离：analysisId 对应 Session.userId = currentUserId | 用户A无法导出用户B结果 |
| FR-012 | P1 | format 参数校验：仅允许 pdf/word，否则抛 BusinessException(INVALID_FORMAT) | 非法 format 抛异常 |

### 跨系统一致性
- **字段命名**：Java camelCase ↔ Python/JSON snake_case
  - analysisId ↔ analysis_id
  - paperId ↔ paper_id
- **API契约**：
  - `GET /api/analysis/{analysisId}/export?format=word`
  - 响应：binary .docx，Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
- **数据流转**：前端 GET → AnalysisController(JWT) → ExportService.export(userId, id, word) → AnalysisService.getAnalysisResult(@Cacheable) → WordExporter.export → byte[] → ResponseEntity

### 安全要求
- **JWT鉴权**：export 端点必须 JWT 鉴权
- **数据隔离**：analysisId 对应 Session.userId 必须等于 currentUserId
- **AI内容标注**：Word 页脚必须显示"AI生成，仅供参考"

---

## 6. Constraints（约束）

### 命名规范
- Java: 类名PascalCase, 方法/变量camelCase, 常量UPPER_SNAKE_CASE, 文件PascalCase.java
- JSON: 字段名snake_case

### 分层规范
- Controller → Service → Repository → Client，禁止跨层
- Entity与DTO分离

### 错误处理
- BusinessException + GlobalExceptionHandler
- BusinessException含 code、message、errorKey

### 缓存策略
- analysisResult TTL=30min（已有，复用）

### 日志规范
- SLF4J + Logback
- 禁止循环内 INFO+ 日志

### 安全规范
- JWT Token (24h) + Redis黑名单
- 数据隔离：analysisId 对应 Session.userId = currentUserId
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
| testExportBasicMarkdown | 验证基础 Markdown 渲染 | normal_flow |
| testExportChineseText | 验证中文字体，无乱码 | normal_flow |
| testExportCitations | 验证 citations 渲染 | normal_flow, boundary_condition |
| testExportFooter | 验证页脚'AI生成，仅供参考' | normal_flow |
| testGenerateFileName | 验证文件名格式 | normal_flow |
| testExportEmptyReport | 验证空 report 抛 BusinessException | error_flow |
| testExportNotCompleted | 验证未完成抛 BusinessException | error_flow |
| testExportLargeReport | 验证大文件不 OOM | boundary_condition |
| testExportDataIsolation | 验证数据隔离 | normal_flow |
| testInvalidFormat | 验证非法 format 抛 BusinessException | error_flow |
| testExportPdfAndWord | 验证 pdf 和 word 均可导出 | normal_flow |

### 验证命令
```bash
cd Veritas/backend && mvn test -Dtest=WordExporterTest
cd Veritas/backend && mvn compile
```

---

## 9. Acceptance Criteria（验收标准）

| ID | 验收标准 | 验证方式 |
|----|---------|---------|
| AC-001 | Word 文件生成成功，.docx 格式可编辑 | automated_test |
| AC-002 | Markdown 语法正确渲染为Word段落 | automated_test |
| AC-003 | Word 中文显示正常，无乱码 | automated_test |
| AC-004 | citations 引用列表正确编号 | automated_test |
| AC-005 | 页脚显示'AI生成，仅供参考' | automated_test |
| AC-006 | 文件名符合规范 | automated_test |
| AC-007 | format=pdf 和 format=word 均可正常导出 | automated_test |
| AC-008 | 非法 format 参数抛 BusinessException | automated_test |
| AC-009 | 数据隔离生效 | automated_test |
| AC-010 | 未完成分析导出抛 BusinessException | automated_test |
| AC-011 | 空 report 抛 BusinessException | automated_test |
| AC-012 | mvn test 全量通过 | automated_test |
