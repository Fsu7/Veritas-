# AM3 收尾计划：修复 fail() HTTP 状态码回归 + 更新文档

## 摘要

AM3 里程碑 task24-task31 已全部完成，152 个 AM3 专项测试全部通过。但存在一个回归问题：`fail()` 返回的字典被 FastAPI 以 HTTP 200 返回，导致 `test_analyze_service_not_initialized` 失败。需修复所有 endpoint 的错误路径，使其 HTTP 状态码与业务码一致，并更新文档。

## 当前状态分析

### 核心问题

`fail(message=..., code=503)` 返回 `Dict[str, Any]`，FastAPI 默认以 HTTP 200 序列化返回。客户端收到的响应：
- HTTP 状态码：200（错误）
- Body：`{"code": 503, "message": "...", "data": null, "timestamp": ...}`

而 `/health` 端点已正确使用 `JSONResponse(status_code=..., content=ok(...))`，异常处理器也正确设置了 HTTP 状态码。

### 受影响文件

| 文件 | 问题 |
|------|------|
| `app/api/endpoints/agent.py` | L76: `return fail(...)` → HTTP 200; L87: `return fail(...)` → HTTP 200; L122: `return fail(...)` → HTTP 200 |
| `app/api/endpoints/search.py` | L22: `return fail(...)` → HTTP 200; L55: `return fail(...)` → HTTP 200; L110: `return fail(...)` → HTTP 200 |
| `app/api/endpoints/model.py` | L43: `return fail(...)` → HTTP 200 |
| `tests/test_agent_endpoint.py` | L220: `assert response.status_code == 503` 失败 |

### 不受影响

- `/health` 端点：已正确使用 `JSONResponse(status_code=..., content=...)`
- `AIServiceException` 处理器：已正确设置 HTTP 状态码
- `RequestValidationError` 处理器：已正确返回 HTTP 422

## 修改方案

### 方案：endpoint 错误路径改用 JSONResponse

将所有 `return fail(...)` 改为 `return JSONResponse(status_code=code, content=fail(...))`，与 `/health` 端点保持一致。

**优点**：
- HTTP 状态码与业务码一致，Java 端 WebClient 可根据 HTTP 状态码判断
- 与 `/health` 和异常处理器行为一致
- SSE 端点的 `fail()` 也需要处理（但 SSE 流中不应返回 JSONResponse，需特殊处理）

**SSE 端点特殊处理**：
`/analyze/stream` 端点的 `fail()` 路径（L122）是 SSE 启动前的错误，此时还未建立 SSE 流，可以返回 JSONResponse。但如果 SSE 流中途出错，应通过 SSE error 事件传递。

### 具体修改

#### 1. `app/utils/response.py` — 新增 `fail_response()` 辅助函数

```python
from fastapi.responses import JSONResponse

def fail_response(message: str, code: int = 500, data: Any = None) -> JSONResponse:
    """返回带正确 HTTP 状态码的失败响应"""
    return JSONResponse(status_code=code, content=fail(message=message, code=code, data=data))
```

#### 2. `app/api/endpoints/agent.py` — 3 处 `fail()` → `fail_response()`

- L76: `return fail(message=e.message, code=503)` → `return fail_response(message=e.message, code=503)`
- L87: `return fail(message="分析任务执行失败，请稍后重试", code=500)` → `return fail_response(message="分析任务执行失败，请稍后重试", code=500)`
- L122: `return fail(message=e.message, code=503)` → `return fail_response(message=e.message, code=503)`

#### 3. `app/api/endpoints/search.py` — 3 处 `fail()` → `fail_response()`

- L22: `return fail(message="SearchService未就绪", code=503)` → `return fail_response(...)`
- L55: `return fail(message="SearchService未就绪", code=503)` → `return fail_response(...)`
- L110: `return fail(message="SearchService未就绪", code=503)` → `return fail_response(...)`

#### 4. `app/api/endpoints/model.py` — 1 处 `fail()` → `fail_response()`

- L43: `return fail(message="LLM服务未就绪", code=503)` → `return fail_response(...)`

#### 5. `tests/test_agent_endpoint.py` — 增强断言

L220: 不仅验证 HTTP 503，还验证 body 格式：
```python
def test_analyze_service_not_initialized(self):
    _clear_app_state()
    response = client.post("/api/agent/analyze", json=VALID_REQUEST_BODY)
    assert response.status_code == 503
    body = response.json()
    assert body["code"] == 503
    assert "未就绪" in body["message"]
```

#### 6. 更新文档

- `docs/AM3_BUGFIX_LOG.md` — 新增 BUG-006
- `docs/AM3_TEST_REPORT.md` — 更新回归测试结果

## 验证步骤

1. 运行 `python3 -m pytest tests/test_agent_endpoint.py -v` — 验证修复
2. 运行 `python3 -m pytest tests/test_request_validation_response.py tests/test_sse_basic_push.py tests/test_health_model_status.py tests/test_field_mapping_consistency.py tests/test_degradation.py tests/test_sse_stability.py tests/test_sse_reconnect_frontend.py tests/test_integration_am3.py -v` — AM3 全量回归
3. 运行 `python3 -m pytest tests/ -v --ignore=tests/test_import_papers.py --tb=short` — 全量回归

## 决策记录

| 决策 | 选项 | 选择 | 理由 |
|------|------|------|------|
| fail() HTTP 状态码 | A: JSONResponse 包装 | A | 与 /health 和异常处理器一致，Java 端可依赖 HTTP 状态码 |
| | B: 仅改测试断言 | - | HTTP 200 + body.code=503 不符合 REST 语义 |
| 辅助函数位置 | A: response.py 新增 fail_response() | A | 集中管理，所有 endpoint 统一引用 |
| | B: 每个 endpoint 内联 JSONResponse | - | 重复代码，易遗漏 |
