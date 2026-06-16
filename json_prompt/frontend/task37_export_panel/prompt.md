# ExportPanel导出面板组件 — PDF/Word导出

## 任务概述
创建ExportPanel.vue组件，支持PDF/Word两种格式导出综述报告，点击导出触发API调用+文件下载，导出中loading状态，导出失败ElMessage.error提示，AI生成内容标注。

## 里程碑
FM4：综述生成与Agent可视化完成（Day 6）

## 涉及模块
- F1.4 综述生成模块

## 文件变更
| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | Veritas/frontend/src/components/report/ExportPanel.vue | 导出面板组件 |
| 修改 | Veritas/frontend/src/api/analysis.ts | 新增exportPdf/exportWord API |

## 功能要求

### FR-001 [P0] PDF导出
点击导出PDF，调用API，Blob下载，文件名规范。

### FR-002 [P0] Word导出
点击导出Word，调用API，Blob下载。

### FR-003 [P0] 导出中loading
按钮loading+禁用，防止重复点击。

### FR-004 [P0] 导出失败处理
ElMessage.error提示，恢复按钮可用。

### FR-005 [P1] AI内容标注
面板底部显示'AI生成，仅供参考'。

### FR-006 [P0] API方法
analysis.ts新增exportPdf/exportWord，responseType='blob'。

## 验收标准
- [ ] PDF导出下载正确
- [ ] Word导出下载正确
- [ ] 导出中loading+禁用
- [ ] 导出失败有提示
- [ ] AI内容标注显示
- [ ] API responseType为blob
