# FilterPanel筛选面板 + SortDropdown排序下拉框

## 任务概述
创建FilterPanel.vue（年份范围/会议/引用数筛选+重置）和SortDropdown.vue（相关度/时间/引用数排序）两个通用组件，新增FilterParams/SortParams类型定义，筛选排序参数与后端API对齐。

## 里程碑
FM4：综述生成与Agent可视化完成（Day 8）

## 涉及模块
- F1.2 论文检索模块

## 文件变更
| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | Veritas/frontend/src/components/common/FilterPanel.vue | 筛选面板组件 |
| 新增 | Veritas/frontend/src/components/common/SortDropdown.vue | 排序下拉框组件 |
| 修改 | Veritas/frontend/src/types/paper.ts | 新增FilterParams/SortParams类型 |
| 修改 | Veritas/frontend/src/stores/paperStore.ts | 新增筛选排序状态和方法 |

## 功能要求

### FR-001 [P0] 年份范围筛选
el-date-picker type='yearrange'。

### FR-002 [P0] 会议筛选
el-select multiple，AI/NLP会议列表。

### FR-003 [P1] 引用数筛选
el-input-number最小引用数。

### FR-004 [P0] 重置按钮
清空所有筛选条件。

### FR-005 [P0] 排序选项
相关度/时间/引用数，默认相关度。

### FR-006 [P0] 类型定义
FilterParams/SortParams与后端API对齐。

### FR-007 [P0] paperStore扩展
新增filters/sortBy状态，searchPapers传递参数。

## 验收标准
- [ ] 年份范围筛选正确
- [ ] 会议多选筛选正确
- [ ] 引用数筛选正确
- [ ] 重置按钮清空筛选
- [ ] 排序切换正确
- [ ] 类型与后端API对齐
- [ ] Store正确传递参数
