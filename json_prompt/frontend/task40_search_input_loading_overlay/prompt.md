# SearchInput搜索防抖组件 + LoadingOverlay加载遮罩

## 任务概述
创建SearchInput.vue（300ms防抖+清除+回车搜索+历史搜索标签）和LoadingOverlay.vue（全局加载遮罩+自定义文字）两个通用组件。

## 里程碑
FM4：综述生成与Agent可视化完成（Day 9）

## 涉及模块
- F1.2 论文检索模块

## 文件变更
| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | Veritas/frontend/src/components/common/SearchInput.vue | 搜索输入组件 |
| 新增 | Veritas/frontend/src/components/common/LoadingOverlay.vue | 加载遮罩组件 |

## 功能要求

### FR-001 [P0] 300ms防抖
300ms内多次输入只触发一次search事件。

### FR-002 [P0] 回车搜索
Enter键立即触发搜索（跳过防抖）。

### FR-003 [P0] 清除按钮
el-input clearable，emit clear事件。

### FR-004 [P1] 搜索中状态
loading时禁用输入+loading图标。

### FR-005 [P1] 历史搜索标签
最近10条localStorage，点击触发搜索，支持删除。

### FR-006 [P0] LoadingOverlay
el-overlay+v-loading，z-index:2000，自定义文字。

## 验收标准
- [ ] 300ms防抖正确
- [ ] 回车立即搜索
- [ ] 清除按钮可用
- [ ] 搜索中loading状态
- [ ] 历史标签正确
- [ ] 加载遮罩正确
