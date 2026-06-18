# task56: 全功能集成测试 + AM5 验收

> **课题编号**：XH-202630
> **子项目**：科研文献助手 — AI 服务模块
> **里程碑**：M5 / AM5：混合检索与功能完善（验收里程碑）
> **AM5 天数**：Week 10 Day 6-7
> **版本**：v0.5
> **功能编号**：F3.1-F3.5
> **优先级**：P0
> **创建日期**：2026-06-17

---

## 1. 背景与上下文

### 1.1 项目背景

XH-202630 科研文献智能助手 — AM5 里程碑（混合检索与功能完善）的验收任务。task46-task55 已完成各子功能优化与实现，本任务进行端到端集成测试，验证 AM5 全部 12 项验收检查点，并完成 AM4 遗留的 6-Agent 工作流端到端验证。

### 1.2 任务需求

端到端集成测试，验证 AM5 全部 12 项验收检查点。覆盖 6-Agent 协同 + 混合检索 + 个性化 + 流式输出。AM4 遗留验证：6-Agent 工作流端到端运行成功（Coordinator/Comparer/Reviewer 正确激活）。降级场景测试：单 Agent 超时 / 多 Agent 失败 / LLM 降级。输出 AM5 阶段审阅报告，更新里程碑文档状态 ⬜ → ✅。

### 1.3 参考文档

| 文档 | 用途 |
|------|------|
| [docs/ai-service/AI服务模块系统架构文档.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块系统架构文档.md) | 了解 6-Agent 工作流和 AM5 全部功能 |
| [docs/ai-service/AI服务模块项目里程碑文档.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块项目里程碑文档.md) | 确认 AM5 验收检查点 12 项和验收标准 |
| [AGENTS.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/AGENTS.md) | 确认降级机制和验收规范 |

---

## 2. 当前架构

### 2.1 涉及层级

- `python_ai_service`

### 2.2 相关模块

| 层级 | 模块路径 | 描述 |
|------|---------|------|
| python_ai_service | `app.agents.graph` | 6-Agent LangGraph 工作流（Coordinator→Retriever→Analyzer→Comparer→Generator→Reviewer） |
| python_ai_service | `app.agents.orchestrator` | SSE 编排器，10 事件类型（含 token_stream） |
| python_ai_service | `app.services.search_service` | 混合检索（语义+关键词+RRF） |
| python_ai_service | `app.services.reranker` | 复合重排序 + 推荐策略 |
| python_ai_service | `app.services.llm_service` | LLM 三级降级 + 流式输出 |
| python_ai_service | `app.services.embedding_service` | 多 Provider Embedding（DashScope/Jina/OpenAI） |

### 2.3 现有实现

| 文件 | 描述 | 复用方式 |
|------|------|---------|
| `Veritas/ai-service/app/agents/graph.py` | 6-Agent 工作流已实现，AM4 遗留需端到端验证 | direct_reuse |
| `Veritas/ai-service/app/agents/orchestrator.py` | SSE 编排器已实现 10 事件 | direct_reuse |
| `Veritas/ai-service/app/services/search_service.py` | 混合检索已实现并优化（task46-task48, task54） | direct_reuse |
| `Veritas/ai-service/app/services/reranker.py` | 重排序+推荐策略已实现（task55） | direct_reuse |
| `Veritas/ai-service/app/services/llm_service.py` | LLM 流式输出已优化（task51） | direct_reuse |
| `Veritas/ai-service/app/services/embedding_service.py` | 多 Provider Embedding 已实现（task53） | direct_reuse |

---

## 3. 相关模块详情

### 3.1 WorkflowGraph

- **路径**：`Veritas/ai-service/app/agents/graph.py`
- **职责**：6-Agent LangGraph 工作流

| 方法 | 签名 | 描述 |
|------|------|------|
| `build_workflow` | `def build_workflow() -> StateGraph` | 构建 6-Agent 工作流图 |
| `should_compare` | `def should_compare(state: WorkflowState) -> str` | 条件分支：是否激活 ComparerAgent |
| `should_review` | `def should_review(state: WorkflowState) -> str` | 条件分支：是否激活 ReviewerAgent |

### 3.2 SSEStreamOrchestrator

- **路径**：`Veritas/ai-service/app/agents/orchestrator.py`
- **职责**：SSE 事件编排

| 方法 | 签名 | 描述 |
|------|------|------|
| `stream_workflow` | `async def stream_workflow(self, ...) -> AsyncGenerator[str, None]` | SSE 流式推送工作流事件 |

---

## 4. 待修改文件

| 操作 | 路径 | 说明 |
|------|------|------|
| create | `Veritas/ai-service/tests/e2e/test_am5_integration.py` | AM5 端到端集成测试：1) test_6agent_full_workflow 验证 6-Agent 协同端到端运行；2) test_hybrid_search_with_rerank 验证混合检索+重排序；3) test_personalization_in_workflow 验证个性化注入工作流；4) test_sse_token_stream_e2e 验证 SSE token 流端到端；5) test_degradation_single_agent_timeout 验证单 Agent 超时降级；6) test_degradation_multi_agent_failure 验证多 Agent 失败降级；7) test_degradation_llm_fallback 验证 LLM 降级。 |
| create | `Veritas/ai-service/tests/e2e/test_am5_acceptance.py` | AM5 验收检查点验证（12 项）：1) test_hybrid_search_parallel 验证语义+关键词并行；2) test_rrf_fusion_correct 验证 RRF 融合排序；3) test_personalized_ranking_different_users 验证不同用户不同排序；4) test_conflict_detection 验证矛盾发现；5) test_conflict_annotation_complete 验证 conflicts 数组完整；6) test_llm_stream_available 验证 generate_stream() 可用；7) test_first_token_under_2s 验证首字节<2秒；8) test_external_embedding_available 验证外接 Embedding 备选；9) test_retrieval_accuracy_over_85 验证检索准确率>85%；10) test_rerank_top5_quality 验证重排序 Top5 质量；11) test_hybrid_better_than_semantic 验证混合检索>纯语义；12) test_full_integration_pass 验证全功能集成。 |
| create | `Veritas/ai-service/tests/e2e/test_6agent_e2e.py` | AM4 遗留：6-Agent 工作流端到端测试：1) test_coordinator_activated 验证 Coordinator 正确激活；2) test_comparer_activated_when_papers_ge_2 验证 Comparer 在 papers>=2 时激活；3) test_reviewer_activated_when_report_nonempty 验证 Reviewer 在 report 非空时激活；4) test_full_workflow_output_contains_citations 验证输出含引用；5) test_full_workflow_output_personalized 验证输出个性化。 |
| create | `docs/ai-service/AM5阶段审阅报告.md` | AM5 阶段审阅报告：1) 12 项验收检查点结果（PASS/FAIL）；2) 性能指标（首字节延迟、检索准确率、Top5 差异度）；3) 已知问题与遗留项；4) AM6 前置建议；5) 里程碑文档状态更新建议（⬜ → ✅）。 |

---

## 5. 实现要求

### 5.1 功能需求（FR）

| ID | 优先级 | 描述 | 验收条件 |
|----|--------|------|---------|
| FR-001 | P0 | 端到端测试覆盖：6-Agent 协同 + 混合检索 + 个性化 + 流式输出：1) test_6agent_full_workflow：mock LLM/Embedding，输入主题+3篇论文，验证 6-Agent 依次执行，输出含综述报告；2) test_hybrid_search_with_rerank：验证 SearchService.hybrid_search() + Reranker.rerank() 端到端；3) test_personalization_in_workflow：验证 user_profile 注入工作流，输出个性化；4) test_sse_token_stream_e2e：验证 SSE 流含 token_stream 事件。 | 端到端测试 6-Agent 协同 + 混合检索 + 个性化 + 流式输出全部通过 |
| FR-002 | P0 | 验证 AM5 验收检查点 12 项全部通过：1) 混合检索: 语义+关键词并行（test_hybrid_search_parallel）；2) RRF融合: 融合排序正确（test_rrf_fusion_correct）；3) 个性化排序: 不同用户不同排序（test_personalized_ranking_different_users）；4) 矛盾发现: 检测论文间观点冲突（test_conflict_detection）；5) 矛盾标注: conflicts数组完整（test_conflict_annotation_complete）；6) LLM流式输出: generate_stream()可用（test_llm_stream_available）；7) 流式首字节: <2秒（test_first_token_under_2s）；8) 外接Embedding API: 备选方案可用（test_external_embedding_available）；9) 检索优化: 准确率>85%（test_retrieval_accuracy_over_85）；10) 重排序: Top5质量提升（test_rerank_top5_quality）；11) 混合检索准确率>纯语义检索（test_hybrid_better_than_semantic）；12) 全功能集成测试通过（test_full_integration_pass）。 | AM5 验收检查点 12 项全部通过 |
| FR-003 | P0 | AM4 遗留验证：6-Agent 工作流端到端运行成功（Coordinator/Comparer/Reviewer 正确激活）：1) test_coordinator_activated：验证 Coordinator 节点执行，输出 coordinator_result；2) test_comparer_activated_when_papers_ge_2：验证 requires_compare=True 且 papers>=2 时 should_compare 返回 'compare'，Comparer 执行；3) test_reviewer_activated_when_report_nonempty：验证 report 非空时 should_review 返回 'review'，Reviewer 执行；4) test_full_workflow_output_contains_citations：验证 Generator 输出含引用标记 [1][2]；5) test_full_workflow_output_personalized：验证输出含个性化调整（如难度适配）。 | 6-Agent 工作流端到端运行成功，Coordinator/Comparer/Reviewer 正确激活 |
| FR-004 | P0 | 降级场景测试：1) test_degradation_single_agent_timeout：mock Analyzer 超时，验证工作流降级继续，输出 degraded=True；2) test_degradation_multi_agent_failure：mock Analyzer+Comparer 失败（2+ Agent），验证 _should_degrade_workflow 触发，输出降级标记；3) test_degradation_llm_fallback：mock BuiltinLLM 失败，验证降级到 APILLM，输出 provider 降级日志。 | 降级场景测试通过：单 Agent 超时不阻塞流程 |
| FR-005 | P1 | 输出 AM5 阶段审阅报告 docs/ai-service/AM5阶段审阅报告.md：1) 12 项验收检查点结果表（检查点名/状态PASS|FAIL/证据/备注）；2) 性能指标汇总（首字节延迟 P95、检索准确率 Top5、Top5 排序差异度）；3) 已知问题与遗留项列表；4) AM6 前置建议（模型量化、HNSW 调优、部署文档）；5) 里程碑文档状态更新建议（AM5 验收检查点 ⬜ → ✅）。 | AM5 阶段审阅报告生成，里程碑文档状态更新 |

### 5.2 降级需求

| 场景 | 策略 |
|------|------|
| 单 Agent 超时 | 单 Agent 超时降级继续，输出 degraded=True |
| 多 Agent 失败 | 2+ Agent 失败触发 _should_degrade_workflow，输出降级标记 |
| LLM 降级 | BuiltinLLM 失败降级到 APILLM |

---

## 6. 约束

### 6.1 命名规范

| 对象 | Python |
|------|--------|
| 类名 | PascalCase |
| 函数/变量 | snake_case |
| 常量 | UPPER_SNAKE_CASE |
| 文件名 | snake_case.py |

### 6.2 分层规范

- 端到端测试在 `tests/e2e/`
- 审阅报告在 `docs/ai-service/`

### 6.3 错误处理

- 降级场景测试验证不阻塞流程，不抛异常

### 6.4 日志

- 日志库：Loguru
- 禁止：在端到端测试中打印 INFO 日志干扰断言

---

## 7. 禁止动作

| ID | 动作 | 原因 | 严重性 |
|----|------|------|--------|
| FA-001 | 输出伪代码或 TODO 注释 | 必须输出完整可执行代码 | critical |
| FA-002 | 在端到端测试中调用真实 LLM/Embedding API | 必须 mock 确保测试可复现 | critical |
| FA-003 | 修改 6-Agent 工作流代码 | 本任务仅测试验证，不改工作流 | high |
| FA-004 | 跳过任何一项验收检查点 | 12 项必须全部验证 | high |
| FA-005 | 在审阅报告中伪造 PASS 结果 | 必须基于测试实际结果 | critical |
| FA-006 | 修改里程碑文档状态 | 本任务仅建议更新，实际更新由用户确认 | medium |

---

## 8. 测试要求

### 8.1 端到端集成测试（7 项）

| 测试名 | 描述 | 框架 | 覆盖范围 |
|--------|------|------|---------|
| test_6agent_full_workflow | 6-Agent 协同端到端运行 | pytest | normal_flow, integration |
| test_hybrid_search_with_rerank | 混合检索+重排序端到端 | pytest | normal_flow, integration |
| test_personalization_in_workflow | 个性化注入工作流 | pytest | normal_flow, integration |
| test_sse_token_stream_e2e | SSE token 流端到端 | pytest | normal_flow, integration |
| test_degradation_single_agent_timeout | 单 Agent 超时降级 | pytest | error_flow, degradation |
| test_degradation_multi_agent_failure | 多 Agent 失败降级 | pytest | error_flow, degradation |
| test_degradation_llm_fallback | LLM 降级 | pytest | error_flow, degradation |

### 8.2 AM5 验收检查点测试（12 项）

| 测试名 | 描述 | 框架 |
|--------|------|------|
| test_hybrid_search_parallel | 验收1: 语义+关键词并行 | pytest |
| test_rrf_fusion_correct | 验收2: RRF 融合排序正确 | pytest |
| test_personalized_ranking_different_users | 验收3: 不同用户不同排序 | pytest |
| test_conflict_detection | 验收4: 矛盾发现 | pytest |
| test_conflict_annotation_complete | 验收5: conflicts 数组完整 | pytest |
| test_llm_stream_available | 验收6: generate_stream() 可用 | pytest |
| test_first_token_under_2s | 验收7: 首字节<2秒 | pytest |
| test_external_embedding_available | 验收8: 外接 Embedding 备选 | pytest |
| test_retrieval_accuracy_over_85 | 验收9: 检索准确率>85% | pytest |
| test_rerank_top5_quality | 验收10: 重排序 Top5 质量 | pytest |
| test_hybrid_better_than_semantic | 验收11: 混合检索>纯语义 | pytest |
| test_full_integration_pass | 验收12: 全功能集成 | pytest |

### 8.3 AM4 遗留测试（5 项）

| 测试名 | 描述 | 框架 |
|--------|------|------|
| test_coordinator_activated | AM4 遗留: Coordinator 激活 | pytest |
| test_comparer_activated_when_papers_ge_2 | AM4 遗留: Comparer 激活 | pytest |
| test_reviewer_activated_when_report_nonempty | AM4 遗留: Reviewer 激活 | pytest |
| test_full_workflow_output_contains_citations | AM4 遗留: 输出含引用 | pytest |
| test_full_workflow_output_personalized | AM4 遗留: 输出个性化 | pytest |

### 8.4 验证命令

```bash
cd Veritas/ai-service && python -m pytest tests/e2e/test_am5_integration.py tests/e2e/test_am5_acceptance.py tests/e2e/test_6agent_e2e.py -v
```

**预期结果**：24 个测试用例全部通过（7 集成 + 12 验收 + 5 AM4遗留）

---

## 9. 验收标准

| ID | 验收标准 | 验证方式 |
|----|---------|---------|
| AC-001 | AM5 验收检查点 12 项全部通过 | automated_test |
| AC-002 | 6-Agent 工作流端到端运行成功，输出含引用的个性化综述 | automated_test |
| AC-003 | 降级场景测试通过：单 Agent 超时不阻塞流程 | automated_test |
| AC-004 | AM5 阶段审阅报告生成，里程碑文档状态更新 | manual_test |
| AC-005 | AM4 遗留验证：Coordinator/Comparer/Reviewer 正确激活 | automated_test |
