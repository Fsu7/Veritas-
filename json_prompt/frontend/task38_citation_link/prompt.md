# CitationLink引用溯源组件 — 点击引用弹出原文片段弹窗

## 任务概述
创建CitationLink.vue组件，支持点击综述中的[Author, Year]引用标注弹出el-dialog原文片段弹窗，弹窗内容包含原文片段+论文标题+跳转详情按钮，增强citation.ts引用解析。

## 里程碑
FM4：综述生成与Agent可视化完成（Day 7）

## 涉及模块
- F1.4 综述生成模块

## 文件变更
| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | Veritas/frontend/src/components/report/CitationLink.vue | 引用溯源弹窗组件 |
| 修改 | Veritas/frontend/src/utils/citation.ts | 增强引用解析 |

## 功能要求

### FR-001 [P0] 引用点击弹窗
点击[Author, Year]弹出el-dialog。

### FR-002 [P0] 弹窗内容
原文片段+论文标题+元数据+详情按钮。

### FR-003 [P0] 跳转论文详情
点击详情按钮router.push到/paper-detail/:paperId。

### FR-004 [P1] 弹窗关闭
遮罩/关闭按钮/ESC三种方式。

### FR-005 [P0] citation.ts增强
新增extractCitationData函数。

### FR-006 [P0] ReportView集成
引用点击改为触发弹窗。

## 验收标准
- [ ] 点击引用弹出弹窗
- [ ] 弹窗内容正确
- [ ] 详情按钮可用
- [ ] 弹窗关闭方式完整
- [ ] extractCitationData正确
- [ ] ReportView集成弹窗
