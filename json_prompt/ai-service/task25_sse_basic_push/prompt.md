# AM3-2 — SSE推送基础实现

> **里程碑**: AM3：API完善与Java对接（Week 5-6）
> **版本**: v0.3
> **涉及层级**: python_ai_service + java_backend + frontend
> **功能编号**: F3.5.1 + F3.1.7 + F3.1.8

---

## 1. 任务目标

在 `app/api/endpoints/agent.py` 扩展 `/api/agent/analyze/stream` 端点，使用 `sse-starlette.EventSourceResponse` 推送 Agent 状态事件。

事件类型：
- `agent_started` — Agent 开始执行
- `agent_state_update` — Agent 状态变更（含 progress/intermediateResult）
- `agent_completed` — Agent 完成
- `agent_failed` — Agent 失败（含 errorMessage）
- `analysis_completed` — 全流程完成
- `error` — 全局错误

---

## 2. 涉及文件

| 操作 | 路径 | 说明 |
|------|------|------|
| 新增 | `Veritas/ai-service/app/agents/orchestrator.py` | AgentOrchestrator 流式编排器 |
| 修改 | `Veritas/ai-service/app/agents/graph.py` | 节点流式化（保留同步版本） |
| 修改 | `Veritas/ai-service/app/api/endpoints/agent.py` | 新增 `/analyze/stream` 端点 |
| 新增 | `Veritas/ai-service/tests/test_sse_basic_push.py` | pytest + httpx.AsyncClient 测试 |

---

## 3. 关键设计

### 3.1 SSE 事件格式（严格遵循）

```text
event: agent_state_update
data: {"agentName":"retriever","status":"running","progress":0.3,"analysisId":"anl_001","timestamp":1700000000000}

```

注意：
- `event:` 和 `data:` 后必须有 1 个空格
- `data:` 必须是单行 JSON 字符串（不换行）
- 事件之间用 `\n\n` 分隔
- `timestamp` 必须是 int 毫秒

### 3.2 事件 payload 字段（camelCase）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `agentName` | string | 是 | retriever/analyzer/generator/coordinator/comparer/reviewer |
| `status` | string | 是 | waiting/running/completed/failed |
| `progress` | float | 否 | 0.0-1.0 |
| `intermediateResult` | string | 否 | 中间结果摘要 |
| `durationMs` | int | 否 | 节点耗时 |
| `analysisId` | string | 是 | 任务 ID |
| `timestamp` | int | 是 | 毫秒时间戳 |

### 3.3 Orchestrator 核心实现

```python
# app/agents/orchestrator.py
class AgentOrchestrator:
    async def run_workflow_stream(self, request, agent_instances):
        analysis_id = request.analysis_id or generate_id()
        yield self._event("analysis_started", {"analysisId": analysis_id, "timestamp": now_ts_ms()})
        
        for node_name in ["retrieve", "analyze", "generate"]:
            try:
                yield self._event("agent_started", {"agentName": node_name, "analysisId": analysis_id})
                node_fn = self._get_node_fn(node_name, agent_instances)
                result = await asyncio.wait_for(node_fn(...), timeout=settings.AGENT_TIMEOUT)
                yield self._event("agent_completed", {
                    "agentName": node_name, "status": "completed",
                    "durationMs": ..., "analysisId": analysis_id
                })
            except Exception as e:
                yield self._event("agent_failed", {
                    "agentName": node_name, "errorMessage": str(e), "analysisId": analysis_id
                })
                yield self._event("error", {
                    "analysisId": analysis_id, "errorCode": 500, "errorMessage": str(e)
                })
        
        yield self._event("analysis_completed", {
            "analysisId": analysis_id, "status": "completed", "finalReport": ...
        })
    
    def _event(self, name: str, data: dict) -> dict:
        return {"event": name, "data": json.dumps(data, ensure_ascii=False)}
```

---

## 4. 前后端协同重连策略

| 层 | 重连机制 |
|----|---------|
| **AI 端** | 15s 一次 keep-alive ping 事件（可选）；异常不主动断开，由客户端控制 |
| **Java 端** | WebClient 默认 30s 读取超时；不自动重连（由前端控制） |
| **前端** | `useSSE` composable 自动重连：3s 间隔，最多 5 次，使用 `Last-Event-ID` 头恢复进度 |

---

## 5. 验收标准

- [ ] `/api/agent/analyze/stream` 返回 `EventSourceResponse`
- [ ] SSE 事件格式严格符合 `event:\ndata:\n\n` 规范
- [ ] 事件 data 字段为 JSON 字符串，字段名 camelCase
- [ ] 正常流程事件序列完整：`agent_started → agent_state_update → agent_completed → ... → analysis_completed`
- [ ] Agent 异常 yield `agent_failed` + `error` 事件，不中断流
- [ ] 全流程 120s 超时触发 `error` 事件（`errorCode=408`）
- [ ] 与前端 `useSSE` 集成测试通过（事件解析正确）

---

## 6. 参考文档

- [AI服务架构 §4.4.1 SSE 推送](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块系统架构文档.md)
- [AI服务架构 §附录B.3 SSE事件格式](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块系统架构文档.md)
- [前端 useSSE Composable](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/json_prompt/frontend/task28_use_sse_composable/)

---

## 7. 下一步建议

- 任务 7（task30）将基于本任务进行 SSE 稳定性测试（心跳、断线重连、Last-Event-ID）
- 任务 8（task31）将做完整前后端集成测试
- 建议 Java 端使用 `WebClient.create().post().bodyValue(...).retrieve().bodyToFlux(String.class)` 解析 SSE
