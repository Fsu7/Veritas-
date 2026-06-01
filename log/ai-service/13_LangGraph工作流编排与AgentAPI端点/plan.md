# Task 22 + Task 23 实施计划：LangGraph工作流编排 + Agent API端点

## 概述

依次执行两个任务：
- **Task 22**: 创建 `graph.py` — LangGraph StateGraph 工作流编排核心（3-Agent线性流程）
- **Task 23**: 修改 `agent.py` 端点 + 创建测试 — 接通工作流并编写端到端测试

---

## 当前实现状态

| 模块 | 状态 | 说明 |
|------|------|------|
| `agents/base.py` | ✅ 已实现 | AgentStatus/AgentState/BaseAgent，含to_dict()、30s超时、降级 |
| `agents/retriever.py` | ✅ 已实现 | RetrieverAgent，构造函数需 llm_service/prompt_manager/search_service/reranker |
| `agents/analyzer.py` | ✅ 已实现 | AnalyzerAgent，构造函数需 llm_service/prompt_manager/personalization_service(可选) |
| `agents/generator.py` | ✅ 已实现 | GeneratorAgent，构造函数需 llm_service/prompt_manager/personalization_service(可选) |
| `agents/graph.py` | ❌ 不存在 | 需创建 |
| `api/endpoints/agent.py` | ⚠️ 仅骨架 | 仅返回analysis_id+processing，未接通工作流 |
| `models/schemas.py` | ⚠️ 需扩展 | AnalyzeResponse缺少report/citations/agent_states/degraded/degraded_reason字段 |
| `core/events.py` | ✅ 已实现 | AppState含所有服务实例 |
| `models/enums.py` | ✅ 已实现 | AgentName/AgentStatus等枚举 |
| `exception.py` | ✅ 已实现 | ModelNotLoadedException已存在 |

---

## Task 22: LangGraph工作流编排 (graph.py)

### Step 1: 创建 `app/agents/graph.py`

**WorkflowState TypedDict 定义**（与AGENTS.md 3.2节对齐）：

```python
class WorkflowState(TypedDict):
    # 输入
    query: str
    user_profile: Dict[str, Any]
    analysis_type: str
    analysis_id: str
    # 中间状态
    sub_tasks: List[str]
    search_results: List[Dict]
    analysis_results: List[Dict]
    compare_result: Optional[Dict]
    report: Optional[str]
    review_result: Optional[Dict]
    citations: List[Dict]
    # 最终输出
    final_output: Optional[str]
    # Agent状态追踪
    agent_states: Dict[str, Dict]
    # 错误处理
    errors: List[Dict]
    degraded: bool
    regenerate_count: int
    # 元数据
    started_at: Optional[str]
    completed_at: Optional[str]
```

**3个节点函数**：
1. `retrieve_node(state, agent_instances)` → 调用RetrieverAgent，更新search_results
2. `analyze_node(state, agent_instances)` → 调用AnalyzerAgent，更新analysis_results
3. `generate_node(state, agent_instances)` → 调用GeneratorAgent，更新report/citations

每个节点函数：
- try-except包裹Agent调用
- 失败时记录errors、设置degraded=True、不阻塞后续
- AgentState dataclass → dict序列化（用已有的to_dict()方法）

**build_agent_graph(agent_instances)**：
- 创建StateGraph(WorkflowState)
- 添加3个节点
- 线性边：retrieve → analyze → generate → END
- M2阶段仅3-Agent线性流程

**run_workflow(request, agent_instances)**：
- 构建初始WorkflowState
- asyncio.wait_for执行图，超时120s
- 返回结果字典（含analysis_id/status/report/citations/agent_states/errors/degraded等）

### Step 2: 修改 `app/agents/__init__.py`

新增导出：`WorkflowState`, `build_agent_graph`, `run_workflow`

### Step 3: 创建 `tests/test_graph.py`

12个测试用例覆盖：
- WorkflowState字段完整性
- 3个节点正常/异常流程
- build_agent_graph图构建
- run_workflow端到端/超时/多Agent失败
- AgentState序列化

---

## Task 23: Agent API端点 + 测试

### Step 4: 扩展 `app/models/schemas.py`

**AnalyzeResponse** 需新增字段：
```python
class AnalyzeResponse(BaseModel):
    analysis_id: str = Field(..., alias="analysisId")
    status: str
    report: Optional[str] = None
    citations: Optional[List[Dict]] = None
    agent_states: Optional[List[AgentStateResponse]] = Field(default=None, alias="agentStates")
    degraded: Optional[bool] = None
    degraded_reason: Optional[str] = Field(default=None, alias="degradedReason")
```

**新增 AgentStateResponse**：
```python
class AgentStateResponse(BaseModel):
    agent_name: str = Field(alias="agentName")
    status: str
    progress: Optional[float] = None
    intermediate_result: Optional[str] = Field(default=None, alias="intermediateResult")
    duration_ms: Optional[int] = Field(default=None, alias="durationMs")
```

### Step 5: 重写 `app/api/endpoints/agent.py`

1. **analyze()端点**：
   - 调用 `_build_agent_instances()` 构建3个Agent
   - 调用 `run_workflow(request, agent_instances)` 执行工作流
   - 将结果映射为AnalyzeResponse
   - 异常时返回统一错误格式

2. **_build_agent_instances()**：
   - 从app_state获取服务依赖
   - 构建RetrieverAgent/AnalyzerAgent/GeneratorAgent
   - 服务未初始化时抛ModelNotLoadedException

3. **AgentStateResponse转换**：
   - agent_states dict → List[AgentStateResponse]

### Step 6: 创建 `tests/test_agent_endpoint.py`

9个测试用例覆盖：
- 正常流程
- 请求校验（空topic/非法analysis_type → 422）
- 单Agent降级
- 多Agent降级
- camelCase输出验证
- 服务未初始化（503）
- _build_agent_instances
- agent_state_response转换

---

## 文件变更清单

| 操作 | 文件路径 | 任务 |
|------|---------|------|
| **创建** | `app/agents/graph.py` | Task 22 |
| **修改** | `app/agents/__init__.py` | Task 22 |
| **创建** | `tests/test_graph.py` | Task 22 |
| **修改** | `app/models/schemas.py` | Task 23 |
| **修改** | `app/api/endpoints/agent.py` | Task 23 |
| **创建** | `tests/test_agent_endpoint.py` | Task 23 |

---

## 关键设计决策

1. **节点函数签名**：LangGraph节点函数签名 `(state: WorkflowState) -> dict`，但需访问agent_instances。方案：使用闭包/functools.partial在build_agent_graph中绑定agent_instances到节点函数。

2. **AgentState序列化**：已有 `AgentState.to_dict()` 方法，直接复用。

3. **AnalyzeResponse扩展**：新增字段而非替换，保持向后兼容。

4. **每次请求构建Agent实例**（FR-006 P2选项）：当前选择每次请求构建，避免修改AppState。M4阶段可优化为预构建。

5. **LangGraph版本**：requirements.txt中 `langgraph==0.2.28`，需确认StateGraph API兼容性。

---

## 验证命令

```bash
# Task 22 验证
cd Veritas/ai-service && python3 -m pytest tests/test_graph.py -v
cd Veritas/ai-service && python3 -c "from app.agents.graph import WorkflowState, build_agent_graph, run_workflow; print('Import OK')"

# Task 23 验证
cd Veritas/ai-service && python3 -m pytest tests/test_agent_endpoint.py -v
cd Veritas/ai-service && python3 -m pytest tests/test_graph.py tests/test_agent_endpoint.py -v
```
