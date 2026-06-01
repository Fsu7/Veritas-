# Task22: LangGraph WorkflowState定义 + 基础图编排

## 任务概述

| 项目 | 内容 |
|------|------|
| **版本** | v0.2 |
| **里程碑** | M2 / AM2：RAG检索与3-Agent基础可用 |
| **功能编号** | F3.1.7 |
| **涉及层级** | Python AI服务层 |

## 需求描述

实现LangGraph工作流编排核心：定义WorkflowState TypedDict + 构建基础StateGraph图，将已有的RetrieverAgent、AnalyzerAgent、GeneratorAgent三个Agent编排为"检索→分析→生成"的线性工作流。graph.py是6-Agent协同引擎的核心骨架，当前M2阶段先实现3-Agent线性流程，M4阶段再扩展为6-Agent含条件分支的完整工作流。

## 影响范围

### 新增文件
| 文件 | 说明 |
|------|------|
| `app/agents/graph.py` | LangGraph工作流核心：WorkflowState + 节点函数 + 图构建 + run_workflow入口 |

### 修改文件
| 文件 | 说明 |
|------|------|
| `app/agents/__init__.py` | 新增导出：WorkflowState、build_agent_graph、run_workflow |

### 已有可复用代码
- `agents/base.py` — BaseAgent基类（AgentStatus/AgentState/execute超时控制）
- `agents/retriever.py` — RetrieverAgent（hybrid_search→TopK论文）
- `agents/analyzer.py` — AnalyzerAgent（5维度LLM提取）
- `agents/generator.py` — GeneratorAgent（个性化综述生成）
- `core/events.py` — AppState全局状态管理
- `models/schemas.py` — AnalyzeRequest/AnalyzeResponse
- `models/enums.py` — AgentName/AgentStatus枚举

## 实现要求

### 核心功能

1. **WorkflowState TypedDict** — 包含输入/中间状态/输出/错误处理/元数据5类字段
2. **3个节点函数** — retrieve_node/analyze_node/generate_node，每个调用对应Agent并更新state
3. **build_agent_graph()** — 构建3-Agent线性流程图（retrieve→analyze→generate→END）
4. **run_workflow()** — 工作流入口函数，120s超时控制，返回结构化结果
5. **Agent级降级** — 单Agent失败不阻塞后续，记录errors，标记degraded
6. **工作流级降级** — 多Agent失败时返回降级结果+说明

### 降级策略

```
单Agent失败 → 记录error → 跳过 → 继续后续Agent → degraded=True
多Agent失败 → 标记严重降级 → 返回部分结果 + degraded_reason
全流程超时120s → 返回部分结果 + 超时说明
```

## 验收标准

- [ ] WorkflowState所有字段定义完整
- [ ] 3个节点函数正确调用Agent并更新state
- [ ] build_agent_graph返回可执行CompiledGraph
- [ ] run_workflow端到端执行成功
- [ ] 单Agent失败不阻塞，degraded=True
- [ ] 全流程超时返回降级结果
- [ ] agent_states可JSON序列化
- [ ] 未修改已有Agent内部逻辑

## 验证命令

```bash
cd Veritas/ai-service && python3 -m pytest tests/test_graph.py -v
cd Veritas/ai-service && python3 -c "from app.agents.graph import WorkflowState, build_agent_graph, run_workflow; print('Import OK')"
```

## 参考文档

- `docs/ai-service/AI服务模块系统架构文档.md` — 5.5节LangGraph工作流定义
- `docs/ai-service/AI服务模块项目里程碑文档.md` — 4.3节AM2任务分解
- `docs/架构决策记录(ADR).md` — ADR-002/ADR-003
- `AGENTS.md` — 3.2/3.3节工作流与降级
