# FM3-Task31 FM3 综合验收测试

## 任务概述
FM3 里程碑端到端验收：编写 `__tests__/integration/fm3.spec.ts` 覆盖 16 项检查点（前端模块项目里程碑文档 5.4 节），含通俗解释、论文选择、对比表格、矛盾告警、综述页、Markdown 渲染、引用链接、个性化、降级、SSE 连接/重连/卸载、全流程；并创建 `docs/frontend/FM3-验收清单.md` 手动验收脚本。

## 里程碑
FM3：论文分析与对比页面完成（v0.3 验收里程碑）

## 涉及模块
- `__tests__/integration/fm3.spec.ts`（新增）
- `docs/frontend/FM3-验收清单.md`（新增）
- 全部 FM3 已完成任务（task21-task30）

## 文件变更
| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | `Veritas/frontend/src/__tests__/integration/fm3.spec.ts` | FM3 端到端测试套件 |
| 新增 | `docs/frontend/FM3-验收清单.md` | 手动验收脚本 |

## 功能要求
1. **FR-001** 测试 1：4 知识水平 + null 兜底
2. **FR-002** 测试 2：论文选择 2-5 篇 + 超限提示
3. **FR-003** 测试 3：对比表格 + 矛盾告警
4. **FR-004** 测试 4：综述 4 维度元信息
5. **FR-005** 测试 5：XSS + Markdown 标题 + 引用
6. **FR-006** 测试 6：引用链接触发 emit
7. **FR-007** 测试 7：4 知识水平个性化
8. **FR-008** 测试 8：降级标签 + tooltip
9. **FR-009** 测试 9：SSE 推送更新 agentStore
10. **FR-010** 测试 10：SSE 5 次重连后停止
11. **FR-011** 测试 11：组件卸载无内存泄漏
12. **FR-012** 测试 12：全流程端到端
13. **FR-013** 手动验收脚本

## 跨系统一致性
- `analysisId` ↔ `analysis_id`、`agentName` ↔ `agent_name`、`intermediateResult` ↔ `intermediate_result`、`durationMs` ↔ `duration_ms`、`degradedReason` ↔ `degraded_reason`

## 验收标准
- [ ] 16 项检查点全部通过
- [ ] XSS 防护
- [ ] SSE 重连 5 次后停止
- [ ] 组件卸载清理
- [ ] 4 知识水平差异化
- [ ] `npx vue-tsc --noEmit` + `npx vitest run` + `npm run build` 全通过

## 验证命令
```bash
cd Veritas/frontend && npx vue-tsc --noEmit
cd Veritas/frontend && npx vitest run
cd Veritas/frontend && npm run build
```
