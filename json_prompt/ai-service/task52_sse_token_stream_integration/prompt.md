# task52: SSE token 级流式推送集成

> **课题编号**：XH-202630
> **子项目**：科研文献助手 — AI 服务模块
> **里程碑**：M5 / AM5：混合检索与功能完善
> **AM5 天数**：Week 10 Day 1-2
> **版本**：v0.5
> **功能编号**：F3.5.2, F3.3.2
> **优先级**：P0
> **创建日期**：2026-06-17

---

## 1. 背景与上下文

### 1.1 项目背景

XH-202630 科研文献智能助手 — SSE 编排器已实现 9 种事件类型，但当前 orchestrator 仅推送 Agent 状态事件，未将 LLM token 流通过 SSE 推送给前端。task51 已优化 LLMService.generate_stream()，本任务将其集成到 SSE 推送链路。

### 1.2 任务需求

将 LLM token 流通过 SSE 推送给前端，新增 token_stream 事件（第 10 种 SSE 事件，不破坏原有 9 种）。GeneratorAgent 新增 stream_generate() 方法 yield token。orchestrator 在 Generator 节点执行时调用 stream_generate() 并 yield token_stream 事件。token 流结束后 yield agent_completed 事件包含完整 report。token 流失败时降级为非流式 generate()，yield agent_failed + 降级标记。

### 1.3 参考文档

| 文档 | 用途 |
|------|------|
| [docs/ai-service/AI服务模块系统架构文档.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块系统架构文档.md) | 了解 SSE 9 事件类型和 orchestrator 工作流 |
| [docs/ai-service/AI服务模块项目里程碑文档.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块项目里程碑文档.md) | 确认 AM5 Week 10 Day 1-2 SSE token 流集成交付物 |
| [AGENTS.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/AGENTS.md) | 确认 SSE 事件规范和 Agent 降级约束 |

---

## 2. 当前架构

### 2.1 涉及层级

- `python_ai_service`

### 2.2 相关模块

| 层级 | 模块路径 | 描述 |
|------|---------|------|
| python_ai_service | `app.agents.orchestrator` | SSE 编排器，已实现 9 事件类型 + PING 15s + Last-Event-ID |
| python_ai_service | `app.agents.generator` | GeneratorAgent 已实现 _run() 调用 LLMService.generate()，需新增 stream_generate() |
| python_ai_service | `app.api.endpoints.agent` | SSE 端点 /api/agent/analyze/stream，需支持 token_stream 事件 |
| python_ai_service | `app.services.llm_service` | LLMService.generate_stream() 已实现（task51 已优化首字节计时） |

### 2.3 现有实现

| 文件 | 描述 | 复用方式 |
|------|------|---------|
| `Veritas/ai-service/app/agents/orchestrator.py` | SSEStreamOrchestrator 已实现 9 事件：agent_started/agent_completed/agent_failed/analysis_progress/analysis_completed/analysis_failed/ping/error/degraded | extend |
| `Veritas/ai-service/app/agents/generator.py` | GeneratorAgent._run() 调用 LLMService.generate() 非流式生成 | extend |
| `Veritas/ai-service/app/api/endpoints/agent.py` | SSE 端点已实现，yield 9 种事件 | extend |
| `Veritas/ai-service/app/services/llm_service.py` | LLMService.generate_stream() 已实现并优化（task51） | direct_reuse |

---

## 3. 相关模块详情

### 3.1 SSEStreamOrchestrator

- **路径**：`Veritas/ai-service/app/agents/orchestrator.py`
- **职责**：SSE 事件编排，6-Agent 工作流状态推送

| 方法 | 签名 | 描述 |
|------|------|------|
| `stream_workflow` | `async def stream_workflow(self, ...) -> AsyncGenerator[str, None]` | 主流程：yield SSE 事件，需在 Generator 节点增加 token_stream |
| `_format_sse_event` | `def _format_sse_event(self, event: str, data: dict) -> str` | 格式化 SSE 事件 |

### 3.2 GeneratorAgent

- **路径**：`Veritas/ai-service/app/agents/generator.py`
- **职责**：综述生成 Agent

| 方法 | 签名 | 描述 |
|------|------|------|
| `_run` | `async def _run(self, prompt: str, input_data: dict, context: dict) -> dict` | 非流式生成，返回完整 report |
| `stream_generate` | `async def stream_generate(self, prompt: str, input_data: dict, context: dict) -> AsyncGenerator[dict, None]` | 新增：流式生成，yield {token: str, is_final: bool, report: Optional[str]} |

---

## 4. 待修改文件

| 操作 | 路径 | 说明 |
|------|------|------|
| modify | `Veritas/ai-service/app/agents/generator.py` | GeneratorAgent 新增 stream_generate() 方法：1) 调用 LLMService.generate_stream(prompt, **kwargs)；2) async for token in stream: yield {'token': token, 'is_final': False, 'report': None}；3) 流结束后拼接完整 report，yield {'token': '', 'is_final': True, 'report': full_report}；4) try-except 包裹，失败时降级调用 self._run() 并 yield 降级标记。 |
| modify | `Veritas/ai-service/app/agents/orchestrator.py` | 1) 在 NODE_ORDER 的 generator 节点执行处，调用 generator.stream_generate() 而非 _run()；2) async for chunk in generator.stream_generate(): if chunk['is_final']: 缓存 report 到 state；else: yield self._format_sse_event('token_stream', {'token': chunk['token'], 'analysisId': analysis_id, 'agentName': 'generator'})；3) token 流结束后 yield agent_completed 事件包含完整 report；4) token 流失败时 yield agent_failed 事件 + degraded 标记，降级为非流式 _run()。 |
| modify | `Veritas/ai-service/app/api/endpoints/agent.py` | SSE 端点 /api/agent/analyze/stream 无需修改代码（orchestrator yield 的事件自动透传），但需在 API 文档注释中新增 token_stream 事件说明。 |
| create | `Veritas/ai-service/tests/test_sse_token_stream.py` | 测试：1) test_token_stream_event_format 验证 token_stream 事件 data 含 token/analysisId/agentName；2) test_token_stream_followed_by_agent_completed 验证 token 流结束后 agent_completed 含完整 report；3) test_token_stream_fallback 验证流式失败降级为非流式；4) test_original_9_events_unchanged 验证原有 9 种事件不受影响。 |

---

## 5. 实现要求

### 5.1 功能需求（FR）

| ID | 优先级 | 描述 | 验收条件 |
|----|--------|------|---------|
| FR-001 | P0 | 新增 SSE 事件类型 token_stream：1) event='token_stream'；2) data JSON 含 token（字符串）、analysisId（分析ID）、agentName（固定为'generator'）；3) 每收到一个 LLM token 即 yield 一个 token_stream 事件；4) token 可能为空字符串（LLM 偶发），仍 yield 保持流连续性。 | SSE 流包含 token_stream 事件，每个 token 通过 data 推送 |
| FR-002 | P0 | GeneratorAgent 新增 stream_generate() 方法：1) 签名 async def stream_generate(self, prompt: str, input_data: dict, context: dict) -> AsyncGenerator[dict, None]；2) 调用 self.llm_service.generate_stream(prompt, **kwargs)；3) async for token in stream: yield {'token': token, 'is_final': False, 'report': None}；4) 流结束后拼接所有 token 为 full_report，yield {'token': '', 'is_final': True, 'report': full_report}；5) 更新 self.status 为 completed。 | GeneratorAgent.stream_generate() 正确 yield token 和 final report |
| FR-003 | P0 | orchestrator 在 Generator 节点执行时调用 stream_generate()：1) async for chunk in generator.stream_generate(...): if chunk['is_final']: state['report'] = chunk['report']；else: yield self._format_sse_event('token_stream', {'token': chunk['token'], 'analysisId': analysis_id, 'agentName': 'generator'})；2) token 流结束后 yield agent_completed 事件，data 含完整 report；3) 保持原有 agent_started 事件在 stream_generate 前推送。 | orchestrator 在 Generator 节点 yield token_stream 事件 |
| FR-004 | P0 | token 流结束后 yield agent_completed 事件包含完整 report：1) agent_completed 事件 data 含 agentName='generator'、status='completed'、result={'report': full_report}；2) full_report 为所有 token 拼接结果；3) 前端可通过 agent_completed 获取完整综述，不依赖 token_stream 拼接。 | token 流结束后 agent_completed 事件包含完整 report |
| FR-005 | P0 | token 流失败时降级为非流式 generate()：1) try-except 包裹 generator.stream_generate()；2) 捕获 Exception，logger.warning 输出降级原因；3) 降级调用 generator._run() 获取完整 report；4) yield agent_failed 事件含 degraded=True 标记；5) 随后 yield agent_completed 事件含降级生成的 report；6) 不中断 SSE 连接。 | token 流失败降级为非流式，不中断 SSE 连接 |
| FR-006 | P1 | 保持原有 9 种 SSE 事件不变：1) agent_started/agent_completed/agent_failed/analysis_progress/analysis_completed/analysis_failed/ping/error/degraded 保持原有格式和触发时机；2) token_stream 作为第 10 种事件新增；3) 其他 Agent（coordinator/retriever/analyzer/comparer/reviewer）仍使用 _run() 非流式，仅 generator 使用 stream_generate()。 | 原有 9 种 SSE 事件不受影响 |

### 5.2 降级需求

| 场景 | 策略 |
|------|------|
| 流式失败 | token 流失败降级为非流式 _run()，yield agent_failed + degraded 标记 |
| 多 Agent 失败 | N/A |

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

- Agent 在 `agents/`
- API 端点在 `api/endpoints/`
- 测试在 `tests/`

### 6.3 错误处理

- token 流失败降级为非流式，不中断 SSE
- 流式错误处理：`logger.warning` + 降级到 `_run()`

### 6.4 日志

- 日志库：Loguru
- 禁止：在每个 token yield 时打印日志

---

## 7. 禁止动作

| ID | 动作 | 原因 | 严重性 |
|----|------|------|--------|
| FA-001 | 输出伪代码或 TODO 注释 | 必须输出完整可执行代码 | critical |
| FA-002 | 修改原有 9 种 SSE 事件的格式或触发时机 | token_stream 为新增第 10 种，不破坏原有 | critical |
| FA-003 | 让其他 Agent（非 generator）也使用 stream_generate() | 仅 GeneratorAgent 流式，其他保持非流式 | high |
| FA-004 | 删除 GeneratorAgent._run() 方法 | stream_generate 失败时降级依赖 _run() | critical |
| FA-005 | 在 token_stream 事件中推送非 token 数据（如进度） | token_stream 专用于 LLM token，进度用 analysis_progress | medium |
| FA-006 | 修改 LLMService.generate_stream() 签名 | task51 已优化，本任务仅消费其输出 | high |

---

## 8. 测试要求

### 8.1 单元测试

| 测试名 | 描述 | 框架 | 覆盖范围 |
|--------|------|------|---------|
| test_token_stream_event_format | 验证 token_stream 事件 data 含 token/analysisId/agentName | pytest | normal_flow |
| test_token_stream_followed_by_agent_completed | 验证 token 流结束后 agent_completed 含完整 report | pytest | normal_flow, integration |
| test_token_stream_fallback | mock stream_generate 抛异常，验证降级为非流式 _run() | pytest | error_flow, degradation |
| test_original_9_events_unchanged | 验证原有 9 种 SSE 事件格式和触发时机不变 | pytest | regression |

### 8.2 验证命令

```bash
cd Veritas/ai-service && python -m pytest tests/test_sse_token_stream.py -v
```

**预期结果**：4 个测试用例全部通过

---

## 9. 验收标准

| ID | 验收标准 | 验证方式 |
|----|---------|---------|
| AC-001 | SSE 流包含 token_stream 事件，每个 token 通过 data 推送 | automated_test |
| AC-002 | token 流结束后 agent_completed 事件包含完整 report | automated_test |
| AC-003 | token 流失败降级为非流式，不中断 SSE 连接 | automated_test |
| AC-004 | 原有 9 种 SSE 事件格式和触发时机不变 | automated_test |
