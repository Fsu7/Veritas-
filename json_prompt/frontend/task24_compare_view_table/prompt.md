# FM3-Task24 CompareView + CompareTable + 矛盾告警

## 任务概述
实现 `views/CompareView.vue`（占位→完整）、`components/analysis/CompareTable.vue`（新建）、扩展 `sessionStore.startCompare`。支持 URL 参数解析、对比分析 SSE 编排、维度×论文矩阵、矛盾点告警、生成对比综述 CTA。

## 里程碑
FM3：论文分析与对比页面完成（v0.3）

## 涉及模块
- `views/CompareView.vue`（修改）
- `components/analysis/CompareTable.vue`（新增）
- `stores/sessionStore.ts`（修改：新增 startCompare）
- `stores/paperStore.ts`（selectedPapers）

## 文件变更
| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | `Veritas/frontend/src/components/analysis/CompareTable.vue` | el-table + 矛盾告警 |
| 修改 | `Veritas/frontend/src/views/CompareView.vue` | 完整对比页 |
| 修改 | `Veritas/frontend/src/stores/sessionStore.ts` | startCompare 编排 |

## 功能要求
1. **FR-001** CompareTable：固定首列 + 横向滚动 + 动态论文列 + 矛盾 el-alert 列表
2. **FR-002** CompareView：URL 解析 → 2-5 篇保护 → startCompare → loading/empty/error → 论文摘要 + CompareTable + CTA
3. **FR-003** sessionStore.startCompare：复用 SSE/轮询骨架；完成后 result.comparison 缓存
4. **FR-004** 响应式：<992px 退化为卡片堆叠
5. **FR-005** 可访问性：aria-label/role

## 跨系统一致性
- `paperIds` ↔ `paper_ids`，`possibleReason` ↔ `possible_reason`

## 验收标准
- [ ] <2 篇重定向 /search
- [ ] CompareTable 列数=论文数
- [ ] 矛盾告警完整
- [ ] 组件代码 ≤ 300 行

## 验证命令
```bash
cd Veritas/frontend && npx vue-tsc --noEmit
cd Veritas/frontend && npx vitest run src/__tests__/views/CompareView.spec.ts
```
