# 6-Agent工作流降级与SSE状态结构

## 功能描述
- 解决了6-Agent LangGraph工作流的二级降级机制（Agent级+工作流级）缺失问题
- 实现了SSE事件数据结构增强，支持6-Agent全量状态推送
- 实现了AgentStateResponse数据模型扩展（error/started_at/completed_at/degraded字段）
- 实现了AnalyzeResponse降级等级字段（degradationLevel）
- 实现了端到端集成测试与个性化差异验证
- 业务价值：确保6-Agent工作流在任何Agent失败时仍能返回可用结果，前端可实时感知降级状态并展示

## 实现逻辑

### 修改的核心文件列表

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `app/agents/orchestrator.py` | 修改 | `_yield_final()` 添加 degradationLevel/degradedAgents；`_run_node()` 增强SSE事件数据结构 |
| `app/api/endpoints/agent.py` | 修改 | `_convert_agent_states()` 新增4字段映射；`analyze()` 计算 degradation_level |
| `app/models/schemas.py` | 修改 | AgentStateResponse +4字段；AnalyzeResponse +degradationLevel（前次会话已完成） |
| `app/agents/graph.py` | 修改 | WorkflowState扩展、6节点图、条件边、降级逻辑（前次会话已完成） |
| `tests/test_degradation.py` | 扩展 | 追加8个测试类验证降级机制 |
| `tests/test_sse_agent_state_structure.py` | 新建 | 10个测试类验证SSE事件结构 |
| `tests/test_6agent_e2e.py` | 新建 | 5个测试类验证6-Agent端到端 |
| `tests/test_personalization_difference.py` | 新建 | 4个测试类验证个性化差异 |
| `tests/test_sse_6agent_completeness.py` | 新建 | 5个测试类验证SSE事件完整性 |
| `tests/test_sse_basic_push.py` | 修复 | `_make_mock_agents()` 添加 coordinator 适配6-Agent |
| `tests/test_integration_am3.py` | 修复 | 同上 |

### 使用的算法或设计模式

1. **二级降级策略**：
   - Agent级降级：单Agent超时/异常时跳过并继续，`degraded_agents` 记录失败Agent
   - 工作流级降级：2+Agent失败时 `degradation_level='workflow'`，跳过可选Agent

2. **degradation_level 双语义**：
   - 内部（graph.py/orchestrator）：`'none'/'agent'/'workflow'`（工作流跟踪级别）
   - 对外（API/SSE）：`'none'/'partial'/'severe'/'critical'`（基于失败Agent数量）

3. **SSE事件增强**：9种事件类型，每种事件增加必要字段（analysisType/degraded/errorType/fallback等）

### 关键代码逻辑说明

- `_yield_final()` 调用 `_calculate_degradation_level()` 计算降级等级并加入 `analysis_completed` 事件
- `_convert_agent_states()` 从 state_dict 提取 error/started_at/completed_at，degraded 判断逻辑：`status=='failed' or state_dict.get('degraded', False)`
- `analyze()` 根据 `degraded_agents` 数量计算 degradation_level：0→none, 1→partial, 2→severe, 3+→critical

## 接口变更

### Request（无变更）
```json
{
  "topic": "Multi-Agent协同决策",
  "userId": "usr_001",
  "analysisType": "report",
  "userProfile": { "educationLevel": "master", "researchField": "NLP", "knowledgeLevel": "intermediate", "preferredStyle": "balanced" }
}
```

### Response（新增字段标注 ★）
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "analysisId": "anl_20240523_001",
    "status": "completed",
    "report": "## 文献综述\n...",
    "citations": [{"index": 1, "paperId": "arxiv_2024_001", "citation": "[Author, 2024]"}],
    "agentStates": [
      {
        "agentName": "retriever",
        "status": "completed",
        "progress": 1.0,
        "intermediateResult": "Found 10 papers",
        "durationMs": 1200,
        "error": null,           ★
        "startedAt": "2024-01-01T00:00:00",  ★
        "completedAt": "2024-01-01T00:00:01", ★
        "degraded": false        ★
      }
    ],
    "degraded": false,
    "degradedReason": null,
    "degradationLevel": "none"   ★
  },
  "timestamp": "2024-05-23T10:00:00"
}
```

### SSE 事件变更（新增字段标注 ★）

**analysis_completed 事件**：
```json
{
  "analysisId": "anl_001",
  "status": "completed",
  "finalReport": "## 报告内容",
  "degraded": false,
  "degradedReason": null,
  "totalDurationMs": 5000,
  "degradationLevel": "none",    ★
  "degradedAgents": []           ★
}
```

**agent_started 事件**：新增 `analysisType` 字段 ★
**agent_state_update 事件**：新增 `degraded`/`errorMessage` 字段 ★
**agent_completed 事件**：`intermediateResult` 改为完整结果（非截断），新增 `degraded` 字段 ★
**agent_failed 事件**：新增 `errorType`/`degraded`/`fallback` 字段 ★
**workflow_degraded 事件**（新增类型）：`{analysisId, degradedAgents, reason, fallbackMode}`

## 测试结果

| 测试场景 | 结果 |
|---------|------|
| Task 43: _should_degrade_workflow() 0/1/2个error判定 | 通过 |
| Task 43: WorkflowState降级字段初始化 | 通过 |
| Task 43: retrieve_node降级更新degraded_agents | 通过 |
| Task 43: review_node降级自动approved=True | 通过 |
| Task 43: generate_node降级返回非空报告 | 通过 |
| Task 43: orchestrator workflow_degraded SSE事件 | 通过 |
| Task 43: agent_failed事件含降级信息 | 通过 |
| Task 43: 降级场景report不为空 | 通过 |
| Task 44: AgentStateResponse新字段 | 通过 |
| Task 44: AnalyzeResponse degradationLevel | 通过 |
| Task 44: _convert_agent_states新字段映射 | 通过 |
| Task 44: SSE agent_started含analysisType | 通过 |
| Task 44: SSE agent_completed完整intermediateResult | 通过 |
| Task 44: SSE agent_failed含errorType/fallback | 通过 |
| Task 44: SSE workflow_degraded事件 | 通过 |
| Task 44: SSE analysis_completed含degradationLevel/degradedAgents | 通过 |
| Task 44: 6-Agent完整SSE事件序列 | 通过 |
| Task 45: 6-Agent端到端全链路 | 通过 |
| Task 45: comparer条件分支（跳过/执行） | 通过 |
| Task 45: 审核重试闭环 | 通过 |
| Task 45: 跨Agent数据流验证 | 通过 |
| Task 45: 个性化差异度>60%（Jaccard） | 通过 |
| Task 45: PersonalizationService差异>0.5 | 通过 |
| Task 45: SSE事件顺序和ID单调递增 | 通过 |
| Task 45: review_rejected事件 | 通过 |
| 全量回归测试（662 passed） | 通过 |

**是否通过：是**

## 相关文件

### 代码文件
- `Veritas/ai-service/app/agents/orchestrator.py`
- `Veritas/ai-service/app/api/endpoints/agent.py`
- `Veritas/ai-service/app/models/schemas.py`
- `Veritas/ai-service/app/agents/graph.py`
- `Veritas/ai-service/app/agents/__init__.py`

### 测试文件
- `Veritas/ai-service/tests/test_degradation.py`
- `Veritas/ai-service/tests/test_sse_agent_state_structure.py`
- `Veritas/ai-service/tests/test_6agent_e2e.py`
- `Veritas/ai-service/tests/test_personalization_difference.py`
- `Veritas/ai-service/tests/test_sse_6agent_completeness.py`
- `Veritas/ai-service/tests/test_sse_basic_push.py`
- `Veritas/ai-service/tests/test_integration_am3.py`

### 任务规格文件
- `json_prompt/ai-service/task42_complete_6agent_langgraph_workflow/prompt.json`
- `json_prompt/ai-service/task43_agent_workflow_degradation/prompt.json`
- `json_prompt/ai-service/task44_sse_agent_state_structure/prompt.json`
- `json_prompt/ai-service/task45_e2e_integration_personalization_test/prompt.json`

### 配置变更
- 无配置文件变更
