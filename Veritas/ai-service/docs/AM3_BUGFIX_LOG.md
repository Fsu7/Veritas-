# AM3 Bug 修复日志

> 记录 AM3 里程碑（task24~task30）实施过程中发现并修复的 Bug

---

## BUG-001: response_model 与 ok() 冲突导致 ResponseValidationError

| 项目 | 内容 |
|------|------|
| **编号** | BUG-001 |
| **发现阶段** | Task24 |
| **严重度** | P0 |
| **影响范围** | 所有使用 `response_model` + `ok()` 的端点 |
| **状态** | 已修复 |

### 问题描述

FastAPI 的 `response_model` 会对返回值做二次校验。当 endpoint 使用 `ok()` 包装返回字典时，`response_model=AnalyzeResponse` 期望返回 `AnalyzeResponse` 对象，但实际返回的是 `{"code": 200, "message": "success", "data": {...}, "timestamp": ...}`，导致 `ResponseValidationError`。

### 根因分析

`ok()` 返回的是 `Dict[str, Any]`，包含 `{code, message, data, timestamp}` 4 字段。而 `response_model=AnalyzeResponse` 期望返回值匹配 `AnalyzeResponse` 的 schema，两者结构不兼容。

### 修复方案

移除所有 endpoint 的 `response_model` 参数，统一使用 `ok()` / `fail()` 手动包装返回值。响应格式由 `ok()` / `fail()` 保证，不再依赖 FastAPI 的 `response_model` 自动校验。

### 回归测试

- `test_ok_4_required_fields`: 验证 ok() 返回 4 字段
- `test_fail_4_required_fields`: 验证 fail() 返回 4 字段
- `test_model_status_returns_unified_format`: 验证端点返回统一格式

---

## BUG-002: BaseAgent.execute() 内部捕获异常导致 agent_failed 不触发

| 项目 | 内容 |
|------|------|
| **编号** | BUG-002 |
| **发现阶段** | Task25 |
| **严重度** | P1 |
| **影响范围** | AgentOrchestrator 流式推送，agent_failed 事件 |
| **状态** | 已修复 |

### 问题描述

`BaseAgent.execute()` 方法内部捕获了所有异常（包括 `asyncio.TimeoutError` 和通用 `Exception`），返回 `_fallback_result()` 而不是抛出异常。这导致 `AgentOrchestrator._run_node()` 的 `try/except` 块无法捕获到异常，从而不会 yield `agent_failed` 事件。

### 根因分析

```python
# BaseAgent.execute() 原始逻辑
except Exception as e:
    self.state.status = AgentStatus.FAILED
    self.state.error = str(e)
    return self._fallback_result(input_data)  # 不抛异常，静默降级
```

`_run_node()` 依赖 `agent.state.status == AgentStatus.FAILED` 来判断是否 yield `agent_failed`，但早期版本未做此检查。

### 修复方案

在 `AgentOrchestrator._run_node()` 中，`agent.execute()` 返回后检查 `agent.state.status`：

```python
if agent.state.status == AgentStatus.FAILED:
    yield self._make_event("agent_failed", {...})
    yield self._make_event("error", {...})
else:
    yield self._make_event("agent_completed", {...})
```

### 回归测试

- `test_single_agent_failure_continues`: 验证 agent_failed 事件存在
- `test_agent_failed_event_has_error_message`: 验证 errorMessage 字段
- `test_error_event_has_error_code`: 验证 error 事件含 errorCode

---

## BUG-003: /health 端点未使用统一响应包装器

| 项目 | 内容 |
|------|------|
| **编号** | BUG-003 |
| **发现阶段** | Task26 |
| **严重度** | P1 |
| **影响范围** | /health 端点响应格式 |
| **状态** | 已修复 |

### 问题描述

`/health` 端点最初直接返回 `JSONResponse`，未使用 `ok()` 包装，导致响应格式与其他端点不一致（缺少 `code`/`message`/`timestamp` 字段）。

### 修复方案

重构 `/health` 端点，使用 `ok()` 包装返回值，并添加 `critical_ok` 规则判断 HTTP 状态码（200 vs 503）。

### 回归测试

- `test_health_response_has_unified_format`: 验证 4 字段结构
- `test_health_all_critical_ok_returns_200`: 验证 200 响应
- `test_health_llm_not_loaded_returns_503`: 验证 503 响应

---

## BUG-004: Pydantic 422 错误消息为英文，不符合中文友好要求

| 项目 | 内容 |
|------|------|
| **编号** | BUG-004 |
| **发现阶段** | Task24 |
| **严重度** | P2 |
| **影响范围** | 所有 Pydantic 校验失败的 422 响应 |
| **状态** | 已修复 |

### 问题描述

FastAPI 默认的 `RequestValidationError` 处理器返回英文错误消息（如 "field required"），不符合中文友好要求。

### 修复方案

添加自定义 `validation_exception_handler`，将 Pydantic 校验错误格式化为中文友好消息：

```python
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    message = _extract_chinese_field_message(exc.errors())
    return JSONResponse(status_code=422, content={
        "code": 422, "message": message, "data": None, "timestamp": now_ts_ms()
    })
```

### 回归测试

- `test_missing_userid_returns_422`: 验证中文消息含 "userId"
- `test_illegal_enum_returns_422`: 验证中文消息含 "analysisType"

---

## BUG-005: Last-Event-ID 为 0 或负数时错误跳过事件

| 项目 | 内容 |
|------|------|
| **编号** | BUG-005 |
| **发现阶段** | Task30 |
| **严重度** | P1 |
| **影响范围** | SSE 断线重连 |
| **状态** | 已修复 |

### 问题描述

`_should_skip_event()` 方法在 `last_event_id` 为 0 或负数时仍会跳过事件 ID <= 0 的事件，导致首个事件被错误跳过。

### 修复方案

在 `AgentOrchestrator.__init__()` 中，对 `last_event_id` 做合法性校验：仅接受正整数，0 或负数设为 `None`。

```python
if last_event_id is not None:
    try:
        parsed = int(last_event_id)
        if parsed <= 0:
            parsed = None
    except (ValueError, TypeError):
        parsed = None
```

### 回归测试

- `test_last_event_id_zero_not_skip`: 验证 0 不跳过
- `test_last_event_id_negative_not_skip`: 验证负数不跳过

---

## BUG-006: fail() 返回字典导致 HTTP 状态码始终为 200

| 项目 | 内容 |
|------|------|
| **编号** | BUG-006 |
| **发现阶段** | AM3 回归测试 |
| **严重度** | P1 |
| **影响范围** | agent.py / search.py / model.py 所有错误路径 |
| **状态** | 已修复 |

### 问题描述

`fail()` 返回 `Dict[str, Any]`，FastAPI 默认以 HTTP 200 序列化返回。例如 LLM 未就绪时应返回 HTTP 503，但实际返回 HTTP 200 + body `{"code": 503, ...}`。导致 `test_analyze_service_not_initialized` 断言 `status_code == 503` 失败。

### 根因分析

`fail()` 与 `ok()` 设计为纯字典工厂函数，方便组合使用。但 endpoint 中直接 `return fail(...)` 时，FastAPI 不会根据 body 中的 `code` 字段推断 HTTP 状态码。

### 修复方案

新增 `fail_response()` 辅助函数，返回 `JSONResponse` 并设置正确的 HTTP 状态码：

```python
def fail_response(message: str, code: int = 500, data: Any = None) -> JSONResponse:
    return JSONResponse(status_code=code, content=fail(message=message, code=code, data=data))
```

将所有 endpoint 错误路径的 `return fail(...)` 改为 `return fail_response(...)`，共 7 处：
- `agent.py`: L76, L87, L122
- `search.py`: L22, L55, L110
- `model.py`: L43

### 回归测试

- `test_analyze_service_not_initialized`: HTTP 503 + body.code == 503 + body.message 含"未就绪"
- `test_analyze_endpoint.py`: 10/10 通过
- AM3 全量: 176/176 通过

---

## Bug 统计

| 严重度 | 数量 | 已修复 |
|--------|------|--------|
| P0 | 1 | 1 |
| P1 | 4 | 4 |
| P2 | 1 | 1 |
| **合计** | **6** | **6** |
