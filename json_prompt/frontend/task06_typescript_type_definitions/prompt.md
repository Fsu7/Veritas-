# Task 06: TypeScript类型定义（5个类型文件）

## 任务概述

| 项目 | 内容 |
|------|------|
| **版本** | v0.1 |
| **里程碑** | M1 / FM1：项目骨架与基础设施就绪 |
| **涉及层级** | 前端 (frontend) |
| **功能编号** | F1.1, F1.2, F1.3, F1.4, F1.5 |

## 需求描述

创建5个TypeScript类型定义文件，覆盖前端全部业务域的类型需求，包括论文、用户画像、分析结果、Agent状态、通用响应等类型。所有interface使用export导出，枚举值使用联合字面量类型，字段命名使用camelCase。

## 影响范围

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `src/types/common.ts` | 通用类型：ApiResponse\<T\>、PageResponse\<T\> |
| 新增 | `src/types/paper.ts` | 论文类型：Paper、FilterParams |
| 新增 | `src/types/user.ts` | 用户类型：UserProfile、LoginResponse、ProfileResponse |
| 新增 | `src/types/analysis.ts` | 分析类型：AnalysisResult、StructuredAnalysis、CompareResult、Citation、Conflict、CompareRow |
| 新增 | `src/types/agent.ts` | Agent类型：AgentState、FlowData、FlowNode、FlowLink |

## 5个类型文件设计

### types/common.ts

| Interface | 字段 | 说明 |
|-----------|------|------|
| ApiResponse\<T\> | code, message, data: T, timestamp | 后端统一响应格式 |
| PageResponse\<T\> | items: T[], total, page, size, totalPages | 分页响应格式 |

### types/paper.ts

| Interface | 字段 | 说明 |
|-----------|------|------|
| Paper | paperId, title, authors: string[], abstract, year, venue?, keywords?, citationCount?, pdfUrl?, score?, recommendReason? | 论文实体 |
| FilterParams | yearFrom?, yearTo?, venue?, minCitations?, sort? | 筛选参数 |

### types/user.ts

| Interface | 字段 | 说明 |
|-----------|------|------|
| UserProfile | educationLevel(联合类型), researchField, knowledgeLevel(联合类型), preferredStyle(联合类型) | 用户画像4维度 |
| LoginResponse | token, userId, username, hasProfile | 登录响应 |
| ProfileResponse | educationLevel, researchField, knowledgeLevel, preferredStyle | 画像响应 |

### types/analysis.ts

| Interface | 字段 | 说明 |
|-----------|------|------|
| AnalysisResult | analysisId, status(联合类型), type(联合类型), result?, agentStates?, degraded?, degradedReason? | 分析结果 |
| StructuredAnalysis | researchQuestion, coreMethod, keyExperiments, coreFindings, limitations, plainExplanation? | 5维度分析 |
| CompareResult | table: CompareRow[], summary, conflicts: Conflict[] | 对比结果 |
| CompareRow | dimension, values: string[] | 对比表格行 |
| Citation | paperId, text, location | 引用信息 |
| Conflict | description, possibleReason, papers: string[] | 矛盾发现 |

### types/agent.ts

| Interface | 字段 | 说明 |
|-----------|------|------|
| AgentState | name, status(联合类型), progress?, intermediateResult?, durationMs?, error? | Agent执行状态 |
| FlowData | nodes: FlowNode[], links: FlowLink[] | ECharts流程图数据 |
| FlowNode | name, label, x, y | 流程图节点 |
| FlowLink | source, target | 流程图连线 |

## 跨系统字段映射

TypeScript camelCase ↔ JSON snake_case（Axios拦截器自动转换）：

| TypeScript | JSON |
|-----------|------|
| paperId | paper_id |
| citationCount | citation_count |
| educationLevel | education_level |
| knowledgeLevel | knowledge_level |
| preferredStyle | preferred_style |
| analysisId | analysis_id |
| intermediateResult | intermediate_result |
| durationMs | duration_ms |

## 实现要求

- 所有interface使用export导出
- 枚举字段使用联合字面量类型（如 `'undergraduate' | 'master'`），不使用enum关键字
- 字段命名使用camelCase
- 可选字段使用`?`标记
- analysis.ts需从agent.ts导入AgentState类型
- 每个interface添加JSDoc注释标注JSON字段映射

## 验收标准

- [ ] types/common.ts：ApiResponse\<T\>和PageResponse\<T\>定义完整
- [ ] types/paper.ts：Paper和FilterParams定义完整
- [ ] types/user.ts：UserProfile枚举字段使用联合字面量类型
- [ ] types/analysis.ts：6个interface定义完整
- [ ] types/agent.ts：AgentState/FlowData/FlowNode/FlowLink定义完整
- [ ] 所有字段使用camelCase命名
- [ ] 无any类型
- [ ] npx vue-tsc --noEmit 编译无错误

## 验证命令

```bash
cd Veritas/frontend && npx vue-tsc --noEmit
cd Veritas/frontend && npm run build
```
