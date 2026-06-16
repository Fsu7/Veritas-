# FM4集成测试与验收 — 全功能集成测试+Bug修复

## 任务概述
FM4全功能集成测试与验收，验证15项验收检查点全部通过，修复发现的Bug。

## 里程碑
FM4：综述生成与Agent可视化完成（Day 11 — 验收里程碑）

## 涉及模块
- F1.2 论文检索模块
- F1.4 综述生成模块
- F1.5 Agent可视化模块

## 文件变更
| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | Veritas/frontend/src/__tests__/integration/fm4-acceptance.spec.ts | FM4验收测试 |

## 15项验收检查点

1. Agent流程图6节点+连线正确
2. Agent状态颜色4种正确+running动画
3. Agent状态面板6个Agent实时更新
4. 中间结果时间线+耗时柱状图正确
5. 流程图交互(tooltip/点击/resize)正确
6. PDF导出文件下载正确
7. Word导出文件下载正确
8. 引用溯源弹窗功能完整
9. 年份/会议/引用数筛选正确
10. 相关度/时间/引用排序正确
11. 300ms搜索防抖正确
12. API调用期间loading状态正确
13. ReportView导出+溯源+可视化入口完整
14. SearchView筛选+排序+防抖完整
15. SSE→agentStore→ECharts联调正常

## 验收标准
- [ ] 15/15验收检查点全部通过
