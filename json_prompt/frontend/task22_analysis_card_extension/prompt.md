# FM3-Task22 AnalysisCard 扩展（通俗解释+降级标签+个性化适配）

## 任务概述
扩展 `components/analysis/AnalysisCard.vue`：新增耗时与研究方向 props、显示降级原因 tooltip、按 `knowledgeLevel` 渲染个性化提示卡片、按 `analysis.type` 渲染 footer 元信息，保持单文件 ≤ 300 行，向后兼容现有 PaperDetailView 调用。

## 里程碑
FM3：论文分析与对比页面完成（v0.3）

## 涉及模块
- `components/analysis/AnalysisCard.vue`（修改）
- `components/analysis/PlainExplanation.vue`（协同展示）
- `types/analysis.ts`（AnalysisResult/StructuredAnalysis）
- `stores/userStore.ts`（profile.knowledgeLevel 决策）

## 文件变更
| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `Veritas/frontend/src/components/analysis/AnalysisCard.vue` | 扩展 props/header/footer/降级/个性化 |

## 功能要求
1. **FR-001** 新增 props：`durationMs?: number`、`researchField?: string`，向后兼容
2. **FR-002** header 改造：左侧标题 + 类型徽章（paper_analysis/compare/report），中部 AI 标注，右侧降级 tag + 耗时徽章
3. **FR-003** 降级：`degraded=true` 时 el-tag + el-tooltip 原因；某维度为空时该维度标题右侧加「已降级」
4. **FR-004** 个性化：5 维度下、PlainExplanation 上加 el-collapse「📌 个性化提示」，按 4 种 `knowledgeLevel` 渲染不同文案
5. **FR-005** footer：按 `analysis.type` 渲染「基于 N 篇文献 / 仅单篇」等元信息，事件签名 `generate-report`/`select-compare` 不变

## 跨系统一致性
- `durationMs` ↔ `duration_ms`、`degradedReason` ↔ `degraded_reason`、`researchField` ↔ `research_field`

## 验收标准
- [ ] 4 种知识水平渲染对应个性化提示
- [ ] 降级 tag + tooltip 正确联动
- [ ] 组件代码 ≤ 300 行
- [ ] TypeScript strict 模式无错误

## 验证命令
```bash
cd Veritas/frontend && npx vue-tsc --noEmit
cd Veritas/frontend && npx vitest run src/__tests__/components/analysis/AnalysisCard.spec.ts
```
