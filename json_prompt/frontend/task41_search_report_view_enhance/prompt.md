# SearchView完善 + ReportView完善 — 集成所有FM4新组件

## 任务概述
SearchView集成FilterPanel+SortDropdown+SearchInput（筛选+排序+防抖），ReportView集成ExportPanel+CitationLink+Agent可视化入口按钮。

## 里程碑
FM4：综述生成与Agent可视化完成（Day 10）

## 涉及模块
- F1.2 论文检索模块
- F1.4 综述生成模块

## 文件变更
| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | Veritas/frontend/src/views/SearchView.vue | 集成筛选+排序+防抖 |
| 修改 | Veritas/frontend/src/views/ReportView.vue | 集成导出+溯源+可视化入口 |

## 功能要求

### FR-001 [P0] SearchView布局重构
左侧FilterPanel(240px)+右侧SearchInput+SortDropdown+PaperCard。

### FR-002 [P0] SearchInput集成
替换原搜索输入框。

### FR-003 [P0] FilterPanel集成
筛选参数传递给paperStore。

### FR-004 [P0] SortDropdown集成
排序参数传递给paperStore。

### FR-005 [P0] ExportPanel集成
ReportView中可导出PDF/Word。

### FR-006 [P0] CitationLink集成
引用点击弹出溯源弹窗。

### FR-007 [P0] Agent可视化入口
'查看Agent协同过程'按钮跳转AgentFlowView。

## 验收标准
- [ ] SearchView筛选+排序+防抖完整
- [ ] 布局左侧筛选+右侧结果
- [ ] ReportView导出可用
- [ ] 引用点击弹出溯源弹窗
- [ ] 可视化入口按钮跳转正确
- [ ] 已有功能不受影响
