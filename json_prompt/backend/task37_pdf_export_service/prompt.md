# Task 37：PDF导出服务（Day 6-7）

> **课题编号**：XH-202630
> **版本**：v0.5
> **里程碑**：JM5 缓存优化与功能完善（Week 9 Day 6-7）
> **功能编号**：F2.4.8（新增）
> **创建日期**：2026-06-17

---

## 1. Context（项目上下文）

### 项目
XH-202630 科研文献智能助手 — 领域知识个性化生成与多智能体协同决策系统研究

### 当前版本
v0.5 / JM5：缓存优化与功能完善（Week 9 Day 6-7）

### 需求描述
PDF导出服务：
- pom.xml 引入 iText 7（7.2.5）+ font-asian（中文字体）
- 新建 PdfExporter 工具类（Markdown→PDF转换：标题/段落/列表/代码块；citations 渲染为引用列表；中文字体嵌入；AI内容标注"AI生成，仅供参考"页脚；文件命名 `analysis_{analysisId}_{timestamp}.pdf`）
- 新建 ExportService（导出编排：查 AnalysisResult → 调 PdfExporter → 返回 byte[]）
- AnalysisController 新增 export 端点 `GET /api/analysis/{analysisId}/export?format=pdf`（返回 ResponseEntity<byte[]> + Content-Disposition: attachment；JWT鉴权 + 数据隔离校验）
- 异常处理：分析结果不存在/未完成时抛 BusinessException

### 参考文档
- `docs/backend/Java后端模块系统架构文档.md` — 第5章 分析服务模块（导出子模块）+ 第12章 API规范
- `docs/backend/Java后端模块项目里程碑文档.md` — 第7章 JM5 Week 9 Day 6-7
- `AGENTS.md` — 关键规则第7条 JWT认证+数据隔离 + 安全底线 AI内容标注

---

## 2. Current Architecture（当前架构）

### 涉及层级
- java_backend

### 相关模块
| 模块 | 路径 | 职责 |
|------|------|------|
| AnalysisController | `com.literatureassistant.controller` | 分析Controller，当前5端点，需新增 export 端点 |
| AnalysisService | `com.literatureassistant.service` | 分析服务，getAnalysisResult(userId, analysisId) 返回 AnalysisResponse |
| AnalysisResultDTO | `com.literatureassistant.dto.response` | 分析结果DTO：report(String Markdown) + citations(List<Map>) + status |
| AnalysisResponse | `com.literatureassistant.dto.response` | 分析响应DTO：analysisId/sessionId/status/type/result/createdAt |

### 已有实现
- `pom.xml` — Spring Boot 3.2.5 / Java 17，无 iText/POI 依赖
- `AnalysisController.java` — @RestController @RequestMapping(/api/analysis)，已有5端点 + extractCurrentUserId()
- `AnalysisService.java` — getAnalysisResult(userId, analysisId) 返回 AnalysisResponse，已有 @Cacheable(analysisResult)
- `AnalysisResultDTO.java` — report(String Markdown) + citations(List<Map<String,Object>>，元素含 index/paper_id/citation) + status(AnalysisStatus)
- `AnalysisResponse.java` — analysisId/sessionId/status/type/result/createdAt，@JsonProperty snake_case
- `ResourceNotFoundException.java` — 资源不存在异常
- `BusinessException.java` — 业务异常（code/message/errorKey）

---

## 3. Relevant Modules（关键模块）

### PdfExporter（新建）
- **路径**：`Veritas/backend/src/main/java/com/literatureassistant/util/PdfExporter.java`
- **职责**：PDF导出工具类：Markdown→PDF转换，citations渲染，中文字体，AI标注，文件命名
- **关键接口**：
  - `export(String analysisId, AnalysisResultDTO result)` — 导出PDF，返回byte[]
  - `renderMarkdown(Document, String markdown)` — Markdown→PDF渲染
  - `renderCitations(Document, List<Map> citations)` — citations 渲染为引用列表
  - `addFooter(Document)` — 添加页脚"AI生成，仅供参考"
  - `generateFileName(String analysisId)` — 生成文件名

### ExportService（新建）
- **路径**：`Veritas/backend/src/main/java/com/literatureassistant/service/ExportService.java`
- **职责**：导出编排服务：查 AnalysisResult → 调 PdfExporter → 返回 byte[]
- **关键接口**：`exportPdf(String userId, String analysisId)` — PDF导出编排

### AnalysisController（扩展）
- **路径**：`Veritas/backend/src/main/java/com/literatureassistant/controller/AnalysisController.java`
- **职责**：分析Controller，新增 export 端点
- **关键接口**：`exportAnalysis(@PathVariable analysisId, @RequestParam format, @AuthenticationPrincipal userId)` — 导出端点

---

## 4. Files To Modify（变更文件）

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 修改 | `pom.xml` | 新增 iText 7 依赖：itext7-core:7.2.5（pom）+ font-asian:7.2.5 |
| 新增 | `util/PdfExporter.java` | 新建PDF导出工具类 |
| 新增 | `service/ExportService.java` | 新建导出编排服务 |
| 修改 | `controller/AnalysisController.java` | 新增 exportAnalysis 端点 |
| 新增 | `util/PdfExporterTest.java` | PDF导出单元测试 |

---

## 5. Implementation Requirements（实现要求）

### 功能要求

| ID | 优先级 | 描述 | 验收条件 |
|----|--------|------|---------|
| FR-001 | P0 | pom.xml 引入 iText 7：itext7-core:7.2.5 + font-asian:7.2.5 | mvn compile 成功 |
| FR-002 | P0 | PdfExporter.export 创建 Document → 中文字体 → 渲染 Markdown → 渲染 citations → 页脚 → 返回 byte[] | 返回非空 byte[] |
| FR-003 | P0 | renderMarkdown 支持 #/##/### 标题、段落、- 列表、``` 代码块 | Markdown 语法正确渲染 |
| FR-004 | P0 | 中文字体嵌入：PdfFontFactory.createFont 加载思源宋体/Noto Sans CJK SC 或 STSong-Light | 中文不乱码 |
| FR-005 | P0 | renderCitations 渲染为 '[index] citation_text'，空 citations 不渲染 section | citations 正确渲染 |
| FR-006 | P0 | addFooter 每页页脚居中显示 'AI生成，仅供参考' | 页脚显示 |
| FR-007 | P0 | generateFileName 返回 analysis_{analysisId}_{yyyyMMddHHmmss}.pdf | 文件名规范 |
| FR-008 | P0 | ExportService.exportPdf：校验 → 查结果 → 状态校验 → 调 PdfExporter | 导出编排正确 |
| FR-009 | P0 | exportAnalysis 端点返回 ResponseEntity<byte[]> + Content-Disposition | 端点正确 |
| FR-010 | P0 | 数据隔离：analysisId 对应 Session.userId 必须等于 currentUserId | 用户A无法导出用户B结果 |
| FR-011 | P1 | 异常处理：不存在抛 ResourceNotFoundException，未完成抛 BusinessException | 异常正确抛出 |
| FR-012 | P1 | 大文件处理：report > 10000 字符不 OOM | 大文件导出成功 |

### 跨系统一致性
- **字段命名**：Java camelCase ↔ Python/JSON snake_case
  - analysisId ↔ analysis_id
  - paperId ↔ paper_id
- **API契约**：
  - `GET /api/analysis/{analysisId}/export?format=pdf`
  - 响应：binary PDF，Content-Type: application/pdf，Content-Disposition: attachment; filename="analysis_{id}_{timestamp}.pdf"
- **数据流转**：前端 GET → AnalysisController(JWT) → ExportService.exportPdf → AnalysisService.getAnalysisResult(@Cacheable) → PdfExporter.export → byte[] → ResponseEntity

### 安全要求
- **JWT鉴权**：export 端点必须 JWT 鉴权，userId 从 @AuthenticationPrincipal 获取
- **数据隔离**：analysisId 对应 Session.userId 必须等于 currentUserId
- **AI内容标注**：PDF 页脚必须显示"AI生成，仅供参考"

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

### 验证命令
```bash
cd Veritas/backend && mvn test -Dtest=PdfExporterTest
cd Veritas/backend && mvn compile
```

---

## 9. Acceptance Criteria（验收标准）

| ID | 验收标准 | 验证方式 |
|----|---------|---------|
| AC-001 | PDF 文件生成成功，可被 PDF 阅读器打开 | automated_test |
| AC-002 | Markdown 标题/段落/列表/代码块正确渲染 | automated_test |
| AC-003 | PDF 中文显示正常，无乱码 | automated_test |
| AC-004 | citations 引用列表正确编号 | automated_test |
| AC-005 | 页脚显示'AI生成，仅供参考' | automated_test |
| AC-006 | 文件名符合规范 | automated_test |
| AC-007 | Content-Disposition 头正确 | code_review |
| AC-008 | 数据隔离生效 | automated_test |
| AC-009 | 未完成分析导出抛 BusinessException | automated_test |
| AC-010 | 空 report 抛 BusinessException | automated_test |
| AC-011 | mvn test 全量通过 | automated_test |
