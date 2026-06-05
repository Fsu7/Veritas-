# FM3-Task23 PaperSelector + paperStore 选择逻辑

## 任务概述
实现 `components/paper/PaperSelector.vue` 论文选择器组件（最多 5 篇），扩展 `paperStore` 导出常量与 computed、完成 PaperCard checkbox 改造与 SearchView 集成。

## 里程碑
FM3：论文分析与对比页面完成（v0.3）

## 涉及模块
- `stores/paperStore.ts`（修改）
- `components/paper/PaperSelector.vue`（新增）
- `components/paper/PaperCard.vue`（修改）
- `views/SearchView.vue`（修改）

## 文件变更
| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `Veritas/frontend/src/stores/paperStore.ts` | 导出 MAX_SELECTED_PAPERS、3 个 computed、超限提示 |
| 新增 | `Veritas/frontend/src/components/paper/PaperSelector.vue` | 已选论文标签条 + 去对比 + 清空 |
| 修改 | `Veritas/frontend/src/components/paper/PaperCard.vue` | selectable=true 时显示 el-checkbox |
| 修改 | `Veritas/frontend/src/views/SearchView.vue` | 嵌入 PaperSelector + 传入 selectable/selected |

## 功能要求
1. **FR-001** paperStore 导出 `MAX_SELECTED_PAPERS=5`；新增 `isMaxSelected/canSelectMore/selectionCount`；超限 `ElMessage.warning('最多选择 5 篇论文')`
2. **FR-002** PaperSelector：`disabled?: boolean`；仅 selectionCount>0 渲染；顶部「已选 N/5」+ el-tag closable 横向列表；底部「清空选择」「去对比」按钮（<2 篇禁用）；emit `go-compare`
3. **FR-003** PaperCard `selectable=true` 时 header 右上角 el-checkbox（v-model='selected'），点击 emit('select')
4. **FR-004** SearchView 嵌入 PaperSelector + PaperCard `:selectable :selected`；handler 跳 `/compare?paperIds=...`

## 跨系统一致性
- TypeScript camelCase；store 状态名 paperId 保持

## 验收标准
- [ ] 5 篇上限 + 超限提示正确
- [ ] PaperSelector 0 篇不渲染，<2 篇禁用「去对比」
- [ ] SearchView 集成 PaperSelector + PaperCard checkbox 状态正确
- [ ] 组件代码 ≤ 300 行

## 验证命令
```bash
cd Veritas/frontend && npx vue-tsc --noEmit
cd Veritas/frontend && npx vitest run src/__tests__/stores/paperStore.spec.ts
```
