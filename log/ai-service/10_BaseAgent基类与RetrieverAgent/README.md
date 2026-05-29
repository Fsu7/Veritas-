# BaseAgent基类与RetrieverAgent开发

## 功能描述
- **解决了什么问题**：6-Agent协同引擎缺少统一的Agent基类和状态管理机制，无法实现超时控制、降级处理和SSE状态推送
- **实现了什么功能**：
  - AgentStatus枚举（WAITING/RUNNING/COMPLETED/FAILED），JSON序列化友好
  - AgentState数据类，支持SSE推送所需的全部字段（name/status/started_at/completed_at/duration_ms/progress/intermediate_result/error）
  - BaseAgent抽象基类，提供统一execute()入口（含超时控制、状态管理、降级处理）
  - RetrieverAgent检索Agent，实现LLM策略生成→hybrid_search→可选rerank的完整检索流程
  - tools.py工具模块，4个检索工具函数+TOOL_REGISTRY注册表
- **业务价值**：为6-Agent协同引擎奠定基础，所有具体Agent（Retriever/Analyzer/Comparer/Generator/Reviewer/Coordinator）均继承BaseAgent，实现统一的状态管理和降级机制

## 实现逻辑

### 修改的核心文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/agents/base.py` | 新建 | AgentStatus + AgentState + BaseAgent |
| `app/agents/retriever.py` | 新建 | RetrieverAgent |
| `app/agents/tools.py` | 新建 | 4个工具函数 + TOOL_REGISTRY |
| `app/agents/__init__.py` | 修改 | 导出所有公共类 |
| `tests/test_base_agent.py` | 新建 | 24个BaseAgent测试用例 |
| `tests/test_retriever_agent.py` | 新建 | 26个RetrieverAgent测试用例 |

### 使用的算法或设计模式

1. **模板方法模式（Template Method）**：BaseAgent.execute()定义执行骨架（状态管理→构建Prompt→超时控制→核心逻辑→降级处理），子类通过_run()和build_prompt()实现具体逻辑
2. **策略模式（Strategy）**：TOOL_REGISTRY将工具名映射到函数，Agent可动态调用不同检索工具
3. **降级模式（Fallback/Degradation）**：三层降级——LLM策略失败→直接检索；检索失败→空结果；Agent超时→fallback_result
4. **依赖注入（DI）**：BaseAgent通过构造函数接收llm_service/prompt_manager/search_service，便于测试Mock

### 关键代码逻辑说明

**BaseAgent.execute() 流程**：
```
execute(input_data, context)
  → state.status = RUNNING, started_at = now
  → build_prompt(input_data, context)
  → asyncio.wait_for(_run(prompt, input_data, context), timeout=30s)
  → 成功: status=COMPLETED, duration_ms, intermediate_result
  → 超时: status=FAILED, return _fallback_result()
  → 异常: status=FAILED, return _fallback_result()
```

**RetrieverAgent._run() 流程**：
```
_run(prompt, input_data, context)
  → progress=0.2: LLM生成检索策略
  → _parse_search_strategy: 解析JSON提取core_keywords
  → progress=0.6: hybrid_search(query, top_k, filters)
  → progress=0.8: 可选rerank(有reranker且有user_profile时)
  → progress=1.0: 返回 {papers, total_found, search_strategy}
```

## 接口变更

### Request — Agent执行请求
```json
{
  "input_data": {
    "topic": "Multi-Agent协同决策",
    "top_k": 10
  },
  "context": {
    "user_profile": {
      "education_level": "master",
      "research_field": "NLP",
      "knowledge_level": "intermediate",
      "preferred_style": "balanced"
    }
  }
}
```

### Response — RetrieverAgent成功返回
```json
{
  "papers": [
    {
      "paper_id": "arxiv_2024_001",
      "title": "Multi-Agent Systems Survey",
      "abstract": "A comprehensive survey...",
      "score": 0.92,
      "year": 2024,
      "venue": "ACL"
    }
  ],
  "total_found": 2,
  "search_strategy": {
    "query": "Multi-Agent 协同决策 LangGraph",
    "filters": {"year_range": "recent", "venue_type": "top"}
  }
}
```

### Response — Agent降级返回
```json
{
  "degraded": true,
  "agent": "retriever",
  "error": "Agent retriever timed out after 30s"
}
```

### Response — AgentState SSE推送格式
```json
{
  "name": "retriever",
  "status": "running",
  "started_at": "2026-05-29T10:00:00",
  "completed_at": null,
  "duration_ms": null,
  "progress": 0.6,
  "intermediate_result": "Searching for: Multi-Agent 协同决策",
  "error": null
}
```

## 测试结果

- **test_agent_status_enum**：枚举值正确、JSON序列化输出字符串、str()输出正确 → ✅ 通过
- **test_agent_state_creation_and_to_dict**：创建默认值、to_dict()输出、datetime序列化、update_progress() → ✅ 通过
- **test_base_agent_cannot_instantiate**：ABC不可实例化、缺少抽象方法不可实例化 → ✅ 通过
- **test_base_agent_execute_success**：WAITING→RUNNING→COMPLETED状态转换、duration_ms有值 → ✅ 通过
- **test_base_agent_execute_timeout**：超时后status=FAILED、返回降级结果、不抛异常 → ✅ 通过
- **test_base_agent_execute_exception**：异常后status=FAILED、error有值、返回降级结果 → ✅ 通过
- **test_fallback_result_format**：degraded=True、agent名称、error信息 → ✅ 通过
- **test_summarize_result_truncation**：截断200字符 → ✅ 通过
- **test_retriever_agent_build_prompt**：Prompt渲染正确 → ✅ 通过
- **test_retriever_agent_run_success**：正常检索流程 → ✅ 通过
- **test_retriever_agent_run_with_reranker**：含reranker+user_profile流程 → ✅ 通过
- **test_retriever_agent_llm_failure_degradation**：LLM失败降级为直接检索 → ✅ 通过
- **test_parse_search_strategy**：JSON解析+降级 → ✅ 通过
- **test_tools**：4个工具函数正常+异常处理 → ✅ 通过
- **test_tool_registry**：4个工具映射 → ✅ 通过

**是否通过**：是（50个pytest测试全部通过）

## 相关文件

### 新增代码文件
- `Veritas/ai-service/app/agents/base.py` — AgentStatus枚举、AgentState数据类、BaseAgent抽象基类
- `Veritas/ai-service/app/agents/retriever.py` — RetrieverAgent检索Agent
- `Veritas/ai-service/app/agents/tools.py` — 检索工具函数+TOOL_REGISTRY
- `Veritas/ai-service/tests/test_base_agent.py` — BaseAgent单元测试（24个用例）
- `Veritas/ai-service/tests/test_retriever_agent.py` — RetrieverAgent+tools单元测试（26个用例）

### 修改文件
- `Veritas/ai-service/app/agents/__init__.py` — 导出AgentStatus/AgentState/BaseAgent/RetrieverAgent/TOOL_REGISTRY

### 配置文件变更
- 无（使用已有settings.AGENT_TIMEOUT=30）
