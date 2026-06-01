# Task23: Agent调用API端点 + 端到端测试

## 任务概述

| 项目 | 内容 |
|------|------|
| **版本** | v0.2 |
| **里程碑** | M2 / AM2：RAG检索与3-Agent基础可用 |
| **功能编号** | F3.5.1, F3.1.7 |
| **涉及层级** | Python AI服务层 |

## 需求描述

实现Agent调用API端点（POST /api/agent/analyze），将FastAPI路由层与LangGraph工作流接通，使外部请求能端到端触发3-Agent协同分析并返回结构化结果。同时编写完整的端到端测试代码，验证从HTTP请求到工作流执行到响应返回的全链路。

## 影响范围

### 修改文件
| 文件 | 说明 |
|------|------|
| `app/api/endpoints/agent.py` | 重写analyze()端点：构建Agent实例→调用run_workflow→格式化响应 |

### 新增文件
| 文件 | 说明 |
|------|------|
| `tests/test_agent_endpoint.py` | Agent API端点端到端测试 |

### 依赖关系
- **前置任务**：task22（graph.py WorkflowState + LangGraph基础图）
- **已有代码**：RetrieverAgent/AnalyzerAgent/GeneratorAgent + AppState + Pydantic模型

## 实现要求

### 核心功能

1. **重写analyze()端点** — 接收AnalyzeRequest → 构建Agent实例 → 调用run_workflow → 返回AnalyzeResponse
2. **_build_agent_instances()** — 从app_state获取服务依赖，构建3个Agent实例
3. **响应格式映射** — run_workflow返回dict → AnalyzeResponse（camelCase输出）
4. **AgentStateResponse转换** — agent_states字典 → List[AgentStateResponse]
5. **错误处理** — 服务未初始化返回503，Agent降级返回degraded=True

### API契约

```
POST /api/agent/analyze
请求（camelCase）:
{
  "topic": "Multi-Agent协同决策",
  "paperIds": ["arxiv_2024_001"],
  "userProfile": {"educationLevel":"master","researchField":"NLP","knowledgeLevel":"intermediate","preferredStyle":"balanced"},
  "analysisType": "report",
  "analysisId": "anl_001"
}

响应（camelCase）:
{
  "analysisId": "anl_001",
  "status": "completed",
  "report": "## 文献综述\n...",
  "citations": [{"paperId":"arxiv_2024_001","text":"原文片段"}],
  "agentStates": [
    {"agentName":"retriever","status":"completed","durationMs":1200,"intermediateResult":"找到10篇论文"},
    {"agentName":"analyzer","status":"completed","durationMs":8000},
    {"agentName":"generator","status":"completed","durationMs":15000}
  ],
  "degraded": false,
  "degradedReason": null
}
```

### 测试覆盖

| 场景 | 说明 |
|------|------|
| 正常流程 | mock 3个Agent成功，返回200 + AnalyzeResponse |
| 请求校验 | 空topic→422，非法analysis_type→422 |
| 单Agent降级 | mock analyzer失败，degraded=True |
| 多Agent降级 | mock 2个Agent失败，degraded=True + degraded_reason |
| 服务未初始化 | llm_service=None→503 |
| camelCase验证 | 响应字段名为camelCase格式 |

## 验收标准

- [ ] POST /api/agent/analyze返回AnalyzeResponse格式
- [ ] 响应字段名为camelCase
- [ ] Agent实例从app_state获取，不硬编码
- [ ] 端点函数仅做分发和格式化
- [ ] 请求校验生效（422）
- [ ] Agent降级返回degraded=True
- [ ] 服务未初始化返回503
- [ ] 测试覆盖正常/异常/降级/校验场景
- [ ] 未修改graph.py/retriever.py/analyzer.py/generator.py
- [ ] 错误响应不暴露堆栈

## 验证命令

```bash
cd Veritas/ai-service && python3 -m pytest tests/test_agent_endpoint.py -v
cd Veritas/ai-service && python3 -m pytest tests/test_graph.py tests/test_agent_endpoint.py -v
```

## 参考文档

- `docs/ai-service/AI服务模块系统架构文档.md` — 4.4.1节Agent调用接口
- `docs/ai-service/AI服务模块项目里程碑文档.md` — 4.3节AM2 Day7
- `AGENTS.md` — 8.2/8.4/8.5节API契约
