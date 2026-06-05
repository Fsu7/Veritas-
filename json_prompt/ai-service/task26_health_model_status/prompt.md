# AM3-3 — 健康检查完善 + 模型状态API

> **里程碑**: AM3：API完善与Java对接（Week 5-6）
> **版本**: v0.3
> **涉及层级**: python_ai_service + infra
> **功能编号**: F3.5.3 + F3.5.4 + F3.3.5

---

## 1. 任务目标

1. 完善 `/health` 端点：按架构文档 4.4.4 节 `critical_ok` 规则决定 200/503
2. 扩展 `GET /api/model/status`：返回 LLM/Embedding/Chroma 详细状态

---

## 2. 涉及文件

| 操作 | 路径 | 说明 |
|------|------|------|
| 修改 | `Veritas/ai-service/app/main.py` | /health critical_ok + 503 |
| 修改 | `Veritas/ai-service/app/models/schemas.py` | ModelStatusResponse 扩展 4 字段 |
| 修改 | `Veritas/ai-service/app/api/endpoints/model.py` | 完整填充响应 |
| 新增 | `Veritas/ai-service/tests/test_health_model_status.py` | pytest 测试 |

---

## 3. 健康检查 critical_ok 规则

```python
# app/main.py
@app.get("/health")
async def health_check():
    components = {
        "llm": app_state.llm_service.status if app_state.llm_service else "not_loaded",
        "embedding": app_state.embedding_service.status if app_state.embedding_service else "not_loaded",
        "chroma": app_state.vector_store_service.status if app_state.vector_store_service else "not_connected",
        "prompts": app_state.prompt_manager.status if app_state.prompt_manager else "not_loaded",
        "searchService": "ready" if app_state.search_service else "not_initialized",
        "reranker": "ready" if app_state.reranker else "not_initialized",
    }
    critical_ok = (
        components["llm"] == "loaded"
        and components["embedding"] in ("loaded", "loaded_api", "loaded_local")
        and components["chroma"] == "connected"
    )
    return JSONResponse(
        status_code=200 if critical_ok else 503,
        content=ok(data={"status": "UP" if critical_ok else "DEGRADED", **components}) if critical_ok
        else fail(message="DEGRADED", code=503, data={"status": "DEGRADED", **components}),
    )
```

---

## 4. ModelStatusResponse 扩展字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `providerCandidates` | List[str] | 是 | 所有加载的 LLM provider mode 列表 |
| `chromaPaperCount` | int | 否 | ChromaDB 论文数量 |
| `gpuMemoryUsed` | str | 否 | GPU 显存使用（如 "4.2GB / 16GB"） |
| `llmProviderCount` | int | 是 | 加载的 provider 数量 |

---

## 5. 验收标准

- [ ] `/health` 按 critical_ok 规则返回 200 或 503
- [ ] 响应 data 含 6 个组件状态
- [ ] `ModelStatusResponse` 扩展 4 字段
- [ ] `providerCandidates` 从 `llm_service.providers.keys()` 读取
- [ ] `chromaPaperCount` 从 `vector_store_service.collection.count()` 读取
- [ ] GPU 显存查询异常时返回 None
- [ ] 不暴露 API Key / 密码 / 内部 IP

---

## 6. 参考文档

- [AI服务架构 §4.4.4 健康检查](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块系统架构文档.md)
- [AI服务架构 §14.1 ModelStatusResponse](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块系统架构文档.md)

---

## 7. 下一步建议

- 任务 4（task27）将基于本任务的健康检查和模型状态，做 Java→Python 联调
- 建议在 `docker-compose.yml` 中配置 K8s/Docker 健康探针：
  ```yaml
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
  ```
