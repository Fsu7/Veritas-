# FM3-Task26 个性化输出展示 + 降级状态展示

## 任务概述
实现可复用 `DegradationBadge` 组件 + ReportView/AnalysisCard 个性化与降级展示，覆盖 4 种知识水平徽章、3 种报告类型徽章、4 维度画像摘要。

## 里程碑
FM3：论文分析与对比页面完成（v0.3）

## 涉及模块
- `components/common/DegradationBadge.vue`（新增）
- `components/analysis/AnalysisCard.vue`（替换内联降级 tag）
- `views/ReportView.vue`（个性化徽章 + 画像摘要）

## 文件变更
| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | `Veritas/frontend/src/components/common/DegradationBadge.vue` | 降级徽章 |
| 修改 | `Veritas/frontend/src/components/analysis/AnalysisCard.vue` | 改用 DegradationBadge |
| 修改 | `Veritas/frontend/src/views/ReportView.vue` | 个性化版本徽章 + 画像摘要 + 报告类型徽章 |

## 功能要求
1. **FR-001** DegradationBadge：degraded=false 不渲染；true 时 el-tag warning + el-tooltip 原因
2. **FR-002** AnalysisCard 用 DegradationBadge 替换内联降级 tag
3. **FR-003** ReportView 个性化版本徽章：4 种 knowledgeLevel + null 兜底
4. **FR-004** ReportView 画像摘要卡片：4 维度 + DegradationBadge 右上角
5. **FR-005** ReportView 报告类型徽章：3 种 result.type

## 跨系统一致性
- `knowledgeLevel` ↔ `knowledge_level`，`preferredStyle` ↔ `preferred_style`

## 验收标准
- [ ] DegradationBadge 4 状态正确
- [ ] AnalysisCard 改用 DegradationBadge
- [ ] ReportView 4 种知识水平徽章正确
- [ ] 画像摘要 4 维度齐全

## 验证命令
```bash
cd Veritas/frontend && npx vue-tsc --noEmit
cd Veritas/frontend && npx vitest run src/__tests__/components/common/DegradationBadge.spec.ts
```
