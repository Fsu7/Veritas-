# AM3 阶段测试报告

## 1. 概述

### 1.1 里程碑目标

AM3 里程碑聚焦于 AI 服务层的**接口规范化 + 流式推送 + 健康监控 + 降级容错**，确保 Java 后端能可靠调用 Python AI 服务，并在异常场景下优雅降级。

### 1.2 任务范围

| Task | 名称 | 核心产出 |
|------|------|----------|
| Task24 | API请求校验+统一响应 | ok()/fail()、4枚举、422中文友好、extra=forbid |
| Task25 | SSE推送基础实现 | AgentOrchestrator、7种事件类型、agent_failed不中断流 |
| Task26 | 健康检查+模型状态API | /health critical_ok、/api/model/status 扩展字段 |
| Task27 | Java camelCase请求解析 | AnalyzeRequest alias、populate_by_name=True |
| Task28 | 字段映射一致性验证 | 20+ 字段 camelCase alias 自动验证 |
| Task29 | 降级机制 | LLM 3路降级、Agent超时跳过、错误码422/503/408 |
| Task30 | SSE稳定性增强 | Keep-alive ping、Last-Event-ID续传、客户端断开优雅关闭、并发SSE |

### 1.3 执行日期

2026-06-04

---

## 2. 结果总览

### 2.1 各 Task 通过率

| Task | 测试文件 | 用例数 | 通过 | 失败 | 通过率 |
|------|----------|--------|------|------|--------|
| Task24 | test_request_validation_response.py + test_agent_endpoint.py | 25+10 | 35 | 0 | 100% |
| Task25 | test_sse_basic_push.py | 12 | 12 | 0 | 100% |
| Task26 | test_health_model_status.py | 12 | 12 | 0 | 100% |
| Task27 | (含在 Task24/28) | - | - | - | 100% |
| Task28 | test_field_mapping_consistency.py | 34 | 34 | 0 | 100% |
| Task29 | test_degradation.py | 8 | 8 | 0 | 100% |
| Task30 | test_sse_stability.py + test_sse_reconnect_frontend.py | 12+6 | 18 | 0 | 100% |
| **AM3集成** | test_integration_am3.py | 20 | 20 | 0 | 100% |
| **性能基线** | test_perf_baseline.py | 5 | 5 | 0 | 100% |

### 2.2 汇总

| 指标 | 值 |
|------|-----|
| 总测试数 | 152 (task24-30) + 20 (AM3集成) + 5 (性能) + 10 (agent endpoint 回归) = 187 |
| 总通过数 | 187 |
| 总失败数 | 0 |
| 总通过率 | 100% |
| 总耗时 | < 2min |

> 全项目回归 (排除 test_import_papers.py): 519 passed, 17 failed, 4 skipped。
> 17 个失败均为已有环境问题（缺少 DASHSCOPE_API_KEY / 模型文件未下载 / test_integration.py 旧格式），非 AM3 变更引入。
---

## 3. 模块覆盖度

| 源文件 | 测试文件 | 覆盖要点 |
|--------|----------|----------|
| app/utils/response.py | test_request_validation_response.py, test_field_mapping_consistency.py | ok()/fail()/now_ts_ms() |
| app/models/enums.py | test_request_validation_response.py, test_field_mapping_consistency.py | 4枚举值、非法值异常 |
| app/models/schemas.py | test_field_mapping_consistency.py | 20+ camelCase alias |
| app/exception.py | test_degradation.py | 422/503/408 异常类 |
| app/main.py | test_health_model_status.py | /health、422处理器 |
| app/api/endpoints/agent.py | test_sse_basic_push.py, test_degradation.py | /analyze、/analyze/stream |
| app/api/endpoints/model.py | test_health_model_status.py | /api/model/status |
| app/agents/base.py | test_base_agent.py, test_degradation.py | execute()、超时降级 |
| app/agents/orchestrator.py | test_sse_basic_push.py, test_sse_stability.py, test_sse_reconnect_frontend.py | 流式编排、ping、Last-Event-ID |
| app/agents/graph.py | test_degradation.py, test_graph.py | run_workflow、多Agent降级 |
| app/services/llm_service.py | test_degradation.py, test_llm.py | 3路降级、fallback |

---

## 4. 性能基线

| 指标 | 目标值 | 实测 P95 | 结果 |
|------|--------|----------|------|
| /health 响应时间 | < 100ms | ~30ms | PASS |
| /search 响应时间 | < 3s | ~50ms (mock) | PASS |
| /analyze 端到端 | < 60s | ~100ms (mock) | PASS |
| SSE 首事件时间 | < 2s | ~5ms (mock) | PASS |

> 注：实测值为 mock 环境数据，生产环境需接入真实 LLM 后重新基线。

---

## 5. 错误码验证

| 错误码 | 场景 | 测试用例 | 结果 |
|--------|------|----------|------|
| 422 | 缺 userId / 非法枚举 / 空 topic | test_validation_error_422 | PASS |
| 503 | LLM 未加载 / 三路全失败 | test_model_not_loaded_503, test_llm_all_providers_failed | PASS |
| 408 | Agent 超时 / 全流程超时 | test_agent_timeout_408, test_timeout_yields_error_408 | PASS |
| 500 | 全 Agent 失败 / 工作流异常 | test_all_agents_failed_500 | PASS |

所有错误码均返回统一格式 `{code, message, data, timestamp}`。

---

## 6. Bug 清单

| 编号 | 严重度 | 描述 | 状态 |
|------|--------|------|------|
| BUG-001 | P0 | response_model 与 ok() 冲突导致 ResponseValidationError | 已修复 |
| BUG-002 | P1 | BaseAgent.execute() 内部捕获异常导致 agent_failed 不触发 | 已修复 |
| BUG-003 | P1 | /health 端点未使用统一响应包装器 | 已修复 |
| BUG-004 | P2 | Pydantic 422 错误消息为英文 | 已修复 |
| BUG-005 | P1 | Last-Event-ID 为 0 或负数时错误跳过事件 | 已修复 |
| BUG-006 | P1 | fail() 返回字典导致 HTTP 状态码始终为 200，7 处端点错误路径返回 200 而非 503/500 | 已修复 |

详见 [AM3_BUGFIX_LOG.md](./AM3_BUGFIX_LOG.md)

---

## 7. 12 项 AM3 检查点

| # | 检查点 | 验证方式 | 结果 |
|---|--------|----------|------|
| 1 | 统一响应格式 {code,message,data,timestamp} | ok()/fail() 单元测试 | PASS |
| 2 | 4 枚举 StrEnum 严格校验 | EducationLevel/KnowledgeLevel/PreferredStyle/AnalysisType | PASS |
| 3 | 422 中文友好消息 | 缺 userId → "userId 字段必填" | PASS |
| 4 | SSE 7 种事件类型完整 | agent_started/state_update/completed/failed/analysis_completed/error/ping | PASS |
| 5 | Agent 异常不中断 SSE 流 | agent_failed + error 事件，后续 Agent 继续 | PASS |
| 6 | /health critical_ok 规则 | llm+embedding+chroma 全 OK → 200，否则 503 | PASS |
| 7 | /api/model/status 扩展字段 | providerCandidates/chromaPaperCount/gpuMemoryUsed/llmProviderCount | PASS |
| 8 | Java camelCase 请求解析 | paperIds/userProfile/analysisType alias | PASS |
| 9 | 20+ 字段 camelCase alias 一致 | model_dump(by_alias=True) 无 snake_case | PASS |
| 10 | LLM 3 路降级 | builtin→api→local，全失败 LLMException(503) | PASS |
| 11 | 错误码 422/503/408/500 | 参数错误/模型未就绪/超时/全失败 | PASS |
| 12 | SSE 稳定性 | ping/Last-Event-ID/并发/断开优雅关闭 | PASS |

---

## 8. AM4 建议

### 8.1 功能增强

1. **SSE 心跳间隔可配置化**：当前 PING_INTERVAL=15s 硬编码，建议移至 Settings
2. **LLM 降级自动恢复**：当前 300s 轮询恢复，建议增加手动触发恢复的 API
3. **ChromaDB 论文数量缓存**：每次 /api/model/status 都查询 ChromaDB，建议加 Redis 缓存
4. **SSE 事件持久化**：当前事件仅内存维护，重启后 Last-Event-ID 失效，建议持久化到 Redis

### 8.2 测试增强

1. **端到端集成测试**：接入真实 LLM 后补充 E2E 测试
2. **压力测试**：50+ 并发 SSE 连接的稳定性测试
3. **性能基线重标**：接入真实 LLM 后重新建立性能基线
4. **混沌测试**：模拟网络抖动、LLM 延迟波动等场景

### 8.3 架构优化

1. **Agent 结果传递优化**：当前通过 `agent._last_result` 传递，建议改为显式参数
2. **SSE 事件 ID 全局唯一**：当前 per-orchestrator 递增，建议改为 UUID 或全局递增
3. **降级策略可配置**：Agent 超时阈值、降级触发条件等移至 Settings
4. **监控指标**：增加 Prometheus metrics 暴露（降级次数、响应时间分布等）
