# Task 42-45 剩余工作实施计划

## 当前状态总结

### 已完成
- **Task 42** (6-Agent LangGraph workflow): 全部完成
  - graph.py: WorkflowState扩展、coordinator_node/compare_node、6节点图、条件边
  - orchestrator.py: NODE_ORDER更新、coordinator/comparer流式执行
  - agent.py: _build_agent_instances() 6个Agent
  - __init__.py: 导出更新
  - test_graph.py / test_graph_integration.py: 已更新

- **Task 43** (降级机制): 大部分完成
  - graph.py: degraded_agents/degradation_level字段、_should_degrade_workflow()、各节点Agent级降级
  - orchestrator.py: _should_degrade_workflow()、_calculate_degradation_level()、_degraded_agents跟踪、_run_node()中workflow_degraded SSE事件

- **Task 44** (SSE事件结构): 大部分完成
  - schemas.py: AgentStateResponse +4字段、AnalyzeResponse +degradation_level
  - orchestrator.py: _run_node()中SSE事件数据增强（agent_started +analysisType、agent_state_update +degraded/errorMessage、agent_failed +errorType/degraded/fallback、agent_completed +完整intermediateResult/degraded）

### 剩余工作

---

## Step 1: orchestrator.py _yield_final() 增强（Task 43+44 共用）

**文件**: `Veritas/ai-service/app/agents/orchestrator.py`
**位置**: `_yield_final()` 方法（第609-630行）

**修改内容**:
在 `analysis_completed` 事件中添加 `degradationLevel` 和 `degradedAgents` 字段：

```python
async def _yield_final(self, report: Optional[str]) -> AsyncIterator[Dict[str, str]]:
    error_count = len(self._errors)
    if error_count >= 2 or self._degraded:
        final_status = "degraded"
        # ... existing degraded_reason logic ...
    else:
        final_status = "completed"

    yield self._make_event("analysis_completed", {
        "analysisId": self.analysis_id,
        "status": final_status,
        "finalReport": report or "（无报告）",
        "degraded": self._degraded,
        "degradedReason": self._degraded_reason,
        "totalDurationMs": int((datetime.now() - self._start_time).total_seconds() * 1000),
        "degradationLevel": self._calculate_degradation_level(),  # 新增
        "degradedAgents": list(self._degraded_agents),            # 新增
    })
```

---

## Step 2: agent.py _convert_agent_states() 增强 + analyze() degradation_level（Task 44）

**文件**: `Veritas/ai-service/app/api/endpoints/agent.py`

### 2a: _convert_agent_states() 新字段映射

当前仅映射5个字段，需增加 error/started_at/completed_at/degraded：

```python
def _convert_agent_states(agent_states: dict) -> list[AgentStateResponse]:
    result = []
    for agent_name, state_dict in agent_states.items():
        # degraded判断：status=='failed' 或 state_dict中degraded=True
        is_degraded = state_dict.get("status") == "failed" or state_dict.get("degraded", False)

        result.append(
            AgentStateResponse(
                agent_name=agent_name,
                status=state_dict.get("status", "unknown"),
                progress=state_dict.get("progress"),
                intermediate_result=state_dict.get("intermediate_result"),
                duration_ms=state_dict.get("duration_ms"),
                error=state_dict.get("error"),                    # 新增
                started_at=state_dict.get("started_at"),          # 新增
                completed_at=state_dict.get("completed_at"),      # 新增
                degraded=is_degraded,                             # 新增
            )
        )
    return result
```

### 2b: analyze() 计算 degradation_level 并设置到 AnalyzeResponse

在 `analyze()` 端点中，根据 result 中的 degraded_agents 数量计算 degradation_level：

```python
# 在 response_data 构建前添加
degraded_agents = result.get("degraded_agents", [])
if len(degraded_agents) == 0:
    degradation_level = "none"
elif len(degraded_agents) == 1:
    degradation_level = "partial"
elif len(degraded_agents) == 2:
    degradation_level = "severe"
else:
    degradation_level = "critical"

response_data = AnalyzeResponse(
    analysis_id=result.get("analysis_id", request.analysis_id or ""),
    status=result.get("status", "completed"),
    report=result.get("report"),
    citations=result.get("citations"),
    agent_states=agent_state_list,
    degraded=result.get("degraded"),
    degraded_reason=result.get("degraded_reason"),
    degradation_level=degradation_level,  # 新增
)
```

---

## Step 3: 新建 tests/test_degradation.py 扩展（Task 43）

**文件**: `Veritas/ai-service/tests/test_degradation.py`

在现有8个测试类之后，新增以下测试类（不修改已有测试）：

1. **TestShouldDegradeWorkflow** - 验证 _should_degrade_workflow() 函数
   - test_no_errors_returns_false
   - test_one_error_returns_false
   - test_two_errors_returns_true

2. **TestWorkflowStateDegradationFields** - 验证 WorkflowState 新字段
   - test_initial_state_has_degradation_fields

3. **TestRetrieveNodeDegradedResult** - 验证 retrieve_node 降级处理
   - test_retrieve_node_degraded_updates_degraded_agents

4. **TestReviewNodeAutoApproveOnDegradation** - 验证 review_node 降级自动通过
   - test_review_node_degraded_auto_approves

5. **TestGenerateNodeFallbackReport** - 验证 generate_node 降级返回非空报告
   - test_generate_node_degraded_returns_nonempty_report

6. **TestOrchestratorWorkflowDegradedEvent** - 验证 orchestrator workflow_degraded SSE事件
   - test_workflow_degraded_event_on_multi_agent_failure

7. **TestOrchestratorAgentFailedWithDegradationLevel** - 验证 agent_failed 事件包含 degradationLevel
   - test_agent_failed_contains_degradation_info

8. **TestDegradedResultNotEmpty** - 验证任何降级场景下 report 不为空
   - test_degraded_workflow_returns_nonempty_report

---

## Step 4: 新建 tests/test_sse_agent_state_structure.py（Task 44）

**文件**: `Veritas/ai-service/tests/test_sse_agent_state_structure.py`

测试内容：
1. **TestAgentStateResponseNewFields** - 验证 AgentStateResponse 新字段
   - test_contains_error_started_at_completed_at_degraded
   - test_camelcase_alias_output

2. **TestAnalyzeResponseDegradationLevel** - 验证 AnalyzeResponse degradation_level
   - test_contains_degradation_level_field
   - test_degradation_level_calculation

3. **TestConvertAgentStatesNewFields** - 验证 _convert_agent_states() 新字段映射
   - test_maps_error_started_at_completed_at_degraded

4. **TestSSEAgentStartedHasAnalysisType** - 验证 agent_started 事件含 analysisType
5. **TestSSEAgentCompletedHasFullIntermediateResult** - 验证 agent_completed 完整结果
6. **TestSSEAgentFailedHasErrorTypeAndFallback** - 验证 agent_failed 事件含 errorType/degraded/fallback
7. **TestSSEWorkflowDegradedEvent** - 验证 workflow_degraded 事件
8. **TestSSEAnalysisCompletedHasDegradationInfo** - 验证 analysis_completed 含 degradationLevel/degradedAgents
9. **TestSSESixAgentsFullWorkflow** - 验证6-Agent完整SSE事件序列
10. **TestSSEAllEventTypesComplete** - 验证9种事件类型

---

## Step 5: 新建 tests/test_6agent_e2e.py（Task 45）

**文件**: `Veritas/ai-service/tests/test_6agent_e2e.py`

测试内容：
1. **TestFull6AgentPipeline** - 6-Agent端到端全链路
2. **TestComparerSkippedWhenFewPapers** - paper_count<2时comparer跳过
3. **TestComparerExecutedWhenEnoughPapers** - paper_count>=2时comparer执行
4. **TestReviewRetryLoop** - 审核重试闭环
5. **TestCrossAgentDataFlow** - 跨Agent数据流验证
6. **TestWorkflowStateTransitions** - WorkflowState转换验证

---

## Step 6: 新建 tests/test_personalization_difference.py（Task 45）

**文件**: `Veritas/ai-service/tests/test_personalization_difference.py`

测试内容：
1. **TestPersonalizationDiffExtremeProfiles** - get_personalization_diff() 极端画像>0.5
2. **TestPersonalizationDiversityE2E** - 个性化差异端到端（Jaccard差异度>60%）
3. **TestTermDensityDifference** - 术语密度差异验证
4. **TestStyleDifference** - 风格差异验证

---

## Step 7: 新建 tests/test_sse_6agent_completeness.py（Task 45）

**文件**: `Veritas/ai-service/tests/test_sse_6agent_completeness.py`

测试内容：
1. **TestSSEEventCompleteness** - 每个Agent均有agent_started+agent_completed
2. **TestSSENoComparerWhenSkipped** - comparer跳过时无事件
3. **TestSSEWorkflowDegradedEvent** - 降级事件
4. **TestSSEReviewRejectedEvent** - 审核拒绝事件
5. **TestSSEEventOrdering** - 事件顺序和ID单调递增

---

## Step 8: 运行全量测试验证

```bash
cd Veritas/ai-service && python -m pytest tests/ -v --tb=short
```

确保所有测试通过，无回归。

---

## 关键设计决策

1. **degradation_level 双语义共存**:
   - graph.py/orchestrator 内部: 'none'/'agent'/'workflow'（工作流跟踪级别）
   - API/SSE 对外: 'none'/'partial'/'severe'/'critical'（基于失败Agent数量的等级）
   - 两者在不同上下文中使用，不冲突

2. **_yield_final() 使用 _calculate_degradation_level()**:
   - 该方法基于 self._degraded_agents 数量计算
   - 返回 'none'/'partial'/'severe'/'critical'

3. **测试策略**:
   - 所有测试使用 mock，不调用真实 LLM API
   - test_degradation.py 仅新增测试类/方法，不修改已有断言
   - Task 45 测试依赖 Task 43/44 的代码修改先完成

4. **执行顺序**: Step 1 → Step 2 → Step 3/4（可并行）→ Step 5/6/7（可并行）→ Step 8
