# 技术教学文档 — LangGraph工作流编排与Agent API端点

## 开发思路

### 需求分析过程

M2里程碑要求实现3-Agent最小闭环：Retriever→Analyzer→Generator。前序任务已完成3个Agent的独立实现（Task 19-21），但它们各自为战，缺少协同编排机制。需要：

1. **状态传递**：Retriever的检索结果需要传递给Analyzer，Analyzer的分析结果需要传递给Generator
2. **流程编排**：定义Agent执行顺序、条件分支、错误处理
3. **API暴露**：将工作流通过FastAPI端点对外提供服务
4. **降级保护**：单Agent失败不应导致整个流程崩溃

### 技术选型考虑

**为什么选LangGraph而非手写编排？**

| 方案 | 优点 | 缺点 |
|------|------|------|
| 手写async链 | 简单直接 | 难以扩展条件分支、重试循环 |
| LangChain Chain | 有抽象 | 不支持复杂状态图 |
| **LangGraph StateGraph** | 声明式DAG、条件边、状态持久化 | 学习曲线略高 |

选择LangGraph的核心原因：
- M4需要添加条件边（论文数≥2才执行Comparer）和重试循环（Reviewer审核不通过→重新生成）
- StateGraph的 `add_conditional_edges` 天然支持这些需求
- 工作流状态可序列化，为未来SSE推送和断点恢复奠定基础

### 架构设计思路

```
┌─────────────────────────────────────────────────┐
│ FastAPI Endpoint (agent.py)                      │
│  POST /api/agent/analyze                         │
│  ├─ _build_agent_instances() → 从AppState构建3Agent│
│  ├─ run_workflow(request, agents) → 调用LangGraph │
│  └─ _convert_agent_states() → 格式化响应          │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│ LangGraph Workflow (graph.py)                    │
│  WorkflowState (18字段TypedDict)                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ retrieve │→│ analyze  │→│ generate │→END    │
│  └──────────┘  └──────────┘  └──────────┘       │
│  build_agent_graph(agents) → CompiledGraph       │
│  run_workflow(req, agents) → dict result         │
└─────────────────────────────────────────────────┘
```

### 遇到的问题及解决方案

**问题1：LangGraph节点函数无法传参**

LangGraph节点函数签名固定为 `(state: WorkflowState) -> dict`，但需要访问 `agent_instances` 字典。

**解决方案：闭包模式（Closure Pattern）**

```python
def build_agent_graph(agent_instances: Dict[str, Any]):
    async def _retrieve(state: WorkflowState) -> dict:
        return await retrieve_node(state, agent_instances)  # 闭包捕获agent_instances
    # ...
    graph.add_node("retrieve", _retrieve)
```

外部函数 `retrieve_node` 保持纯逻辑可测试，闭包函数 `_retrieve` 负责绑定实例。

**问题2：CompiledGraph.nodes 不包含 `__end__`**

测试中验证节点列表时期望包含 `__end__`，但LangGraph的CompiledGraph不将 `__end__` 暴露为节点。

**解决方案**：只验证业务节点 + `__start__`：
```python
expected_nodes = {"retrieve", "analyze", "generate", "__start__"}
```

**问题3：跨系统字段命名（Java camelCase ↔ Python snake_case）**

Java后端期望camelCase响应，Python内部使用snake_case。

**解决方案**：Pydantic `Field(alias=...)` + `response_model_by_alias=True`
```python
class AnalyzeResponse(BaseModel):
    analysis_id: str = Field(alias="analysisId")
    degraded_reason: Optional[str] = Field(alias="degradedReason")

@router.post("/analyze", response_model=AnalyzeResponse, response_model_by_alias=True)
```

## 实现步骤

### 第一步：定义WorkflowState TypedDict

```python
class WorkflowState(TypedDict):
    query: str
    user_profile: Dict[str, Any]
    analysis_type: str
    analysis_id: str
    # ... 18个字段对齐AGENTS.md 3.2节
```

关键决策：使用TypedDict而非Pydantic BaseModel，因为LangGraph StateGraph要求状态类型支持字典式访问和部分更新（节点函数返回partial dict会被合并到完整状态中）。

### 第二步：实现3个节点函数

每个节点函数遵循统一模式：
1. 获取Agent实例 → 不存在则返回错误
2. 调用Agent.execute() → 成功则返回结果
3. 异常捕获 → 返回错误+degraded=True

```python
async def retrieve_node(state: WorkflowState, agent_instances: Dict[str, Any]) -> dict:
    retriever = agent_instances.get("retriever")
    if retriever is None:
        return {"search_results": [], "errors": [...], "degraded": True, ...}
    try:
        result = await retriever.execute(input_data={...}, context={...})
        return {"search_results": result.get("papers", []), ...}
    except Exception as e:
        return {"search_results": [], "errors": [...], "degraded": True, ...}
```

### 第三步：实现build_agent_graph

使用闭包模式绑定agent_instances，构建StateGraph：

```python
def build_agent_graph(agent_instances: Dict[str, Any]):
    async def _retrieve(state): return await retrieve_node(state, agent_instances)
    async def _analyze(state): return await analyze_node(state, agent_instances)
    async def _generate(state): return await generate_node(state, agent_instances)

    graph = StateGraph(WorkflowState)
    graph.add_node("retrieve", _retrieve)
    graph.add_node("analyze", _analyze)
    graph.add_node("generate", _generate)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "analyze")
    graph.add_edge("analyze", "generate")
    graph.add_edge("generate", END)
    return graph.compile()
```

### 第四步：实现run_workflow

包含初始状态构建、全流程超时、降级判定：

```python
async def run_workflow(request, agent_instances):
    initial_state = {...}  # 从AnalyzeRequest构建
    try:
        compiled_graph = build_agent_graph(agent_instances)
        result_state = await asyncio.wait_for(compiled_graph.ainvoke(initial_state), timeout=120)
        # 降级判定逻辑
        return {...}
    except asyncio.TimeoutError:
        return {"status": "failed", "degraded": True, ...}
    except Exception as e:
        return {"status": "failed", "degraded": True, ...}
```

### 第五步：实现Agent API端点

连接FastAPI路由到LangGraph工作流：

```python
@router.post("/analyze", response_model=AnalyzeResponse, response_model_by_alias=True)
async def analyze(request: AnalyzeRequest):
    agent_instances = _build_agent_instances()  # 从AppState构建
    result = await run_workflow(request, agent_instances)
    agent_state_list = _convert_agent_states(result["agent_states"])
    return AnalyzeResponse(...)
```

### 第六步：扩展Pydantic模型

新增 `AgentStateResponse` 和扩展 `AnalyzeResponse`，支持camelCase API契约。

### 第七步：编写测试

- `test_graph.py`: 16个测试覆盖节点函数、图构建、端到端执行、超时、降级
- `test_agent_endpoint.py`: 10个测试覆盖端点成功/验证/降级/camelCase/503

## 解决了什么问题

### 核心问题描述

3个Agent（Retriever/Analyzer/Generator）已独立实现，但缺乏：
1. 状态传递机制（检索结果→分析输入→生成输入）
2. 流程编排能力（顺序执行、错误处理、超时保护）
3. API服务暴露（外部系统无法调用Agent工作流）

### 解决方案对比

| 方案 | 可行性 | 扩展性 | M4适配 |
|------|--------|--------|--------|
| 手写async调用链 | ✅ | ❌ 难加条件边 | ❌ |
| Celery任务链 | ✅ | ⚠️ 重 | ⚠️ |
| **LangGraph StateGraph** | ✅ | ✅ 条件边/循环 | ✅ 天然支持 |

### 最终方案的优势

1. **声明式DAG**：工作流拓扑一目了然，M4添加条件边只需 `add_conditional_edges`
2. **状态自动合并**：节点函数返回partial dict，LangGraph自动合并到完整状态
3. **降级友好**：每个节点独立try/catch，失败不影响后续节点
4. **可观测性**：agent_states字段记录每个Agent的执行状态、耗时、中间结果

## 变更内容

### 新增文件
- `app/agents/graph.py` — LangGraph工作流核心（WorkflowState + 3节点函数 + build_agent_graph + run_workflow）
- `tests/test_graph.py` — 工作流单元测试（16个）
- `tests/test_agent_endpoint.py` — 端点测试（10个）

### 修改文件
- `app/agents/__init__.py` — 新增导出 WorkflowState, build_agent_graph, run_workflow
- `app/models/schemas.py` — 新增 AgentStateResponse 模型，扩展 AnalyzeResponse 添加 agent_states/degraded/degraded_reason 字段
- `app/api/endpoints/agent.py` — 从骨架重写为完整工作流集成

### 配置变更
- 无新增配置项，使用已有 `AGENT_TIMEOUT=30`（单Agent超时）和 `AGENT_FULL_TIMEOUT=120`（全流程超时）

## 关键技术点

### 1. LangGraph StateGraph核心概念

```python
from langgraph.graph import END, StateGraph

graph = StateGraph(WorkflowState)    # 1. 创建图，指定状态类型
graph.add_node("name", func)          # 2. 添加节点（函数签名: state -> partial_state）
graph.set_entry_point("name")         # 3. 设置入口节点
graph.add_edge("a", "b")             # 4. 添加固定边
graph.add_conditional_edges("a", fn)  # 5. 添加条件边（M4使用）
compiled = graph.compile()            # 6. 编译为可执行图
result = await compiled.ainvoke(init) # 7. 异步执行
```

**关键理解**：节点函数返回的是 **partial state**（部分状态），LangGraph会自动将其合并到完整状态中。这意味着：
- 只需返回当前节点修改的字段
- 不需要返回完整状态
- List/Dict字段需要手动合并（如 `errors: state.get("errors", []) + [new_error]`）

### 2. 闭包模式解决节点函数传参

LangGraph节点函数签名固定为 `(state) -> dict`，无法直接传递额外参数。闭包模式将外部变量捕获到内部函数中：

```python
def build_agent_graph(agent_instances):
    # 闭包捕获 agent_instances
    async def _retrieve(state):
        return await retrieve_node(state, agent_instances)
    # ...
```

**设计考量**：将纯逻辑（`retrieve_node`）与实例绑定（`_retrieve`）分离，使节点函数可独立测试。

### 3. Pydantic camelCase别名机制

跨系统API契约中，Java期望camelCase，Python内部用snake_case：

```python
class AgentStateResponse(BaseModel):
    agent_name: str = Field(alias="agentName")          # Python: agent_name → JSON: agentName
    intermediate_result: Optional[str] = Field(alias="intermediateResult")
    duration_ms: Optional[int] = Field(alias="durationMs")
    model_config = ConfigDict(populate_by_name=True)    # 允许两种命名都能反序列化

# 端点启用别名输出
@router.post("/analyze", response_model=AnalyzeResponse, response_model_by_alias=True)
```

### 4. 两级降级策略

```
正常流程: retrieve ✅ → analyze ✅ → generate ✅ → status: "completed"
单Agent失败: retrieve ✅ → analyze ❌ → generate ✅ → status: "degraded", degraded_reason: "Agent analyzer 失败"
多Agent失败: retrieve ✅ → analyze ❌ → generate ❌ → status: "degraded", degraded_reason: "多Agent失败(analyzer, generator)"
全流程超时: → status: "failed", degraded_reason: "全流程超时(120s)"
```

### 5. AgentState序列化

使用已有的 `AgentState.to_dict()` 方法，将Agent内部状态转为JSON可序列化字典：

```python
def _serialize_agent_state(agent) -> Dict[str, Any]:
    return agent.state.to_dict()
```

## 经验总结

### 开发过程中的收获

1. **LangGraph的partial state合并机制**是理解工作流的关键——节点函数不需要返回完整状态，只需返回修改的字段
2. **闭包模式**是解决框架函数签名限制的通用方案，在LangChain/LangGraph生态中广泛使用
3. **降级策略需要分层设计**——Agent级（跳过）、工作流级（标记降级）、LLM级（切换Provider）三层保护

### 踩过的坑及如何避免

1. **CompiledGraph.nodes不包含`__end__`** — 测试验证节点列表时，不要期望`__end__`出现在nodes中，它只是LangGraph内部的终止标记
2. **TypedDict vs Pydantic BaseModel** — LangGraph StateGraph要求状态类型支持字典式访问，必须用TypedDict而非BaseModel
3. **List字段需要手动合并** — LangGraph不会自动合并List字段，`errors: state.get("errors", []) + [new_error]` 是必须的
4. **Dict字段也需要手动合并** — `agent_states: {**state.get("agent_states", {}), "retriever": ...}` 确保不覆盖之前节点的状态

### 最佳实践建议

1. **节点函数与实例绑定分离** — 纯逻辑函数可独立测试，闭包函数负责绑定，两者职责清晰
2. **统一错误处理模式** — 每个节点函数遵循相同的 try/catch/降级 模式，便于维护和扩展
3. **测试优先验证降级路径** — 降级是生产环境最常见的场景，测试应覆盖各种失败组合
4. **为M4预留扩展点** — WorkflowState已包含 compare_result/review_result/regenerate_count 等M4字段，扩展时只需添加节点和条件边
