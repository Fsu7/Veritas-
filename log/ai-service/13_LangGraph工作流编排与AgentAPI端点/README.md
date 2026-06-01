# LangGraph工作流编排与Agent API端点

## 功能描述
- 解决了3个独立Agent（Retriever/Analyzer/Generator）缺乏协同编排机制的问题，通过LangGraph StateGraph实现线性工作流
- 实现了 `POST /api/agent/analyze` 端点，将FastAPI路由与LangGraph工作流完整连接
- 建立了Agent降级策略（单Agent失败跳过、多Agent失败标记降级）和120s全流程超时保护
- 业务价值：完成M2里程碑核心交付——3-Agent最小闭环（检索→分析→生成），为M4扩展6-Agent奠定基础

## 实现逻辑

### 修改的核心文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/agents/graph.py` | 新增 | LangGraph工作流核心：WorkflowState + 节点函数 + build_agent_graph + run_workflow |
| `app/api/endpoints/agent.py` | 重写 | Agent API端点：_build_agent_instances + _convert_agent_states + analyze |
| `app/models/schemas.py` | 修改 | 新增 AgentStateResponse、扩展 AnalyzeResponse |
| `app/agents/__init__.py` | 修改 | 新增导出 WorkflowState/build_agent_graph/run_workflow |
| `tests/test_graph.py` | 新增 | 16个单元测试 |
| `tests/test_agent_endpoint.py` | 新增 | 10个端点测试 |

### 使用的算法或设计模式

1. **LangGraph StateGraph模式** — 声明式DAG工作流编排，节点函数签名 `(state) -> partial_state`
2. **闭包模式（Closure Pattern）** — `build_agent_graph()` 内部闭包绑定 `agent_instances` 到节点函数，解决LangGraph节点函数无法传参的限制
3. **两级降级策略** — 单Agent失败：跳过+记录错误+degraded=True；多Agent失败(≥2)：严重降级+degraded_reason
4. **Cache-Aside缓存模式** — 端点层通过AppState单例获取服务实例

### 关键代码逻辑说明

**WorkflowState TypedDict (18字段)**:
```python
class WorkflowState(TypedDict):
    query: str                    # 用户查询
    user_profile: Dict[str, Any]  # 用户画像
    analysis_type: str            # 分析类型
    analysis_id: str              # 分析任务ID
    sub_tasks: List[str]          # 子任务列表(M4 Coordinator填充)
    search_results: List[Dict]    # 检索结果
    analysis_results: List[Dict]  # 分析结果
    compare_result: Optional[Dict] # 对比结果(M4 Comparer填充)
    report: Optional[str]         # 综述报告
    review_result: Optional[Dict] # 审核结果(M4 Reviewer填充)
    citations: List[Dict]         # 引用列表
    final_output: Optional[str]   # 最终输出
    agent_states: Dict[str, Dict] # 各Agent执行状态
    errors: List[Dict]            # 错误列表
    degraded: bool                # 是否降级
    regenerate_count: int         # 重试次数(M4 Reviewer使用)
    started_at: Optional[str]     # 开始时间
    completed_at: Optional[str]   # 完成时间
```

**3-Agent线性工作流**:
```
retrieve → analyze → generate → END
```

**节点函数统一模式**:
1. 从 `agent_instances` 获取Agent实例
2. Agent不存在 → 返回错误+degraded=True
3. Agent执行成功 → 返回结果+序列化状态
4. Agent执行异常 → 返回错误+degraded=True+序列化状态

**run_workflow 降级判定**:
- error_count >= 2 → 严重降级，列出所有失败Agent
- error_count == 1 + degraded=True → 单Agent降级
- asyncio.TimeoutError → 全流程超时，返回部分结果

## 接口变更

### Request — POST /api/agent/analyze
```json
{
  "topic": "Multi-Agent协同决策",
  "paperIds": ["arxiv_2024_001"],
  "userId": "usr_001",
  "userProfile": {
    "educationLevel": "master",
    "researchField": "NLP",
    "knowledgeLevel": "intermediate",
    "preferredStyle": "balanced"
  },
  "analysisType": "report",
  "analysisId": "anl_20240523_001"
}
```

### Response — AnalyzeResponse (camelCase)
```json
{
  "analysisId": "ana_20260530120000",
  "status": "completed",
  "report": "## 文献综述\n...",
  "citations": [{"index": 1, "paper_id": "arxiv_2024_001", "citation": "[Author, 2024]"}],
  "agentStates": [
    {"agentName": "retriever", "status": "completed", "progress": 1.0, "intermediateResult": "Found 10 papers", "durationMs": 1200},
    {"agentName": "analyzer", "status": "completed", "progress": 1.0, "durationMs": 8000},
    {"agentName": "generator", "status": "completed", "progress": 1.0, "durationMs": 15000}
  ],
  "degraded": false,
  "degradedReason": null
}
```

### 降级响应示例
```json
{
  "analysisId": "ana_20260530120000",
  "status": "degraded",
  "report": "综述生成过程中发生错误，请稍后重试。",
  "citations": [],
  "agentStates": [
    {"agentName": "retriever", "status": "completed", "progress": 1.0, "durationMs": 1200},
    {"agentName": "analyzer", "status": "failed", "progress": 0.0},
    {"agentName": "generator", "status": "failed", "progress": 0.0}
  ],
  "degraded": true,
  "degradedReason": "多Agent失败(analyzer, generator)，结果可能不完整"
}
```

## 测试结果

### test_graph.py (16个测试)
| 测试场景 | 结果 |
|---------|------|
| WorkflowState字段完整性验证 | ✅ 通过 |
| WorkflowState默认值验证 | ✅ 通过 |
| retrieve_node成功执行 | ✅ 通过 |
| retrieve_node异常处理 | ✅ 通过 |
| retrieve_node Agent不存在 | ✅ 通过 |
| analyze_node成功执行 | ✅ 通过 |
| analyze_node异常处理 | ✅ 通过 |
| generate_node成功执行 | ✅ 通过 |
| generate_node异常处理 | ✅ 通过 |
| build_agent_graph返回CompiledGraph | ✅ 通过 |
| build_agent_graph包含正确节点 | ✅ 通过 |
| run_workflow端到端执行 | ✅ 通过 |
| run_workflow超时处理 | ✅ 通过 |
| run_workflow多Agent失败降级 | ✅ 通过 |
| AgentState序列化JSON兼容 | ✅ 通过 |
| AgentState None字段序列化 | ✅ 通过 |

### test_agent_endpoint.py (10个测试)
| 测试场景 | 结果 |
|---------|------|
| analyze成功响应 | ✅ 通过 |
| 空topic验证 | ✅ 通过 |
| 缺少userId验证 | ✅ 通过 |
| 单Agent失败降级 | ✅ 通过 |
| 多Agent失败降级 | ✅ 通过 |
| camelCase响应格式 | ✅ 通过 |
| 服务未初始化503 | ✅ 通过 |
| _build_agent_instances成功 | ✅ 通过 |
| _build_agent_instances LLM未加载 | ✅ 通过 |
| AgentStateResponse转换 | ✅ 通过 |

**总计: 26/26 通过 (0.35s)**

## 相关文件

### 代码文件
- `Veritas/ai-service/app/agents/graph.py` — LangGraph工作流核心
- `Veritas/ai-service/app/api/endpoints/agent.py` — Agent API端点
- `Veritas/ai-service/app/models/schemas.py` — Pydantic数据模型
- `Veritas/ai-service/app/agents/__init__.py` — 模块导出
- `Veritas/ai-service/app/agents/base.py` — BaseAgent基类（已有）
- `Veritas/ai-service/app/agents/retriever.py` — RetrieverAgent（已有）
- `Veritas/ai-service/app/agents/analyzer.py` — AnalyzerAgent（已有）
- `Veritas/ai-service/app/agents/generator.py` — GeneratorAgent（已有）
- `Veritas/ai-service/app/core/events.py` — AppState单例（已有）
- `Veritas/ai-service/app/core/config.py` — Settings配置（已有）
- `Veritas/ai-service/app/exception.py` — 异常体系（已有）

### 测试文件
- `Veritas/ai-service/tests/test_graph.py` — 工作流单元测试
- `Veritas/ai-service/tests/test_agent_endpoint.py` — 端点测试

### 配置变更
- 无新增配置项，使用已有 `AGENT_TIMEOUT=30` 和 `AGENT_FULL_TIMEOUT=120`
