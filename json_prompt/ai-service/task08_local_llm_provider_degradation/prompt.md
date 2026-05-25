# task08 — LocalLLMProvider（本地模型）+ 完整自动降级逻辑

## 项目
XH-202630 科研文献智能助手 — v0.1 M1：基础设施就绪 / AM1：项目骨架与模型层就绪

## 需求概述
在 task06/task07 基础上，实现 LocalLLMProvider（本地开源模型）+ 完整的三路自动降级逻辑，完成 LLM 服务模块的核心功能。

核心交付：
1. `services/llm_service.py` — LocalLLMProvider + 完整降级逻辑 + 状态跟踪 + 定时恢复
2. `events.py` — on_shutdown 释放 GPU 显存
3. `.env.example` — 方案 C 本地模型配置说明

## 影响范围

| 层级 | 涉及模块 |
|------|---------|
| python_ai_service | app/services/llm_service.py（修改：新增 LocalLLMProvider + 完善降级） |
| python_ai_service | app/core/events.py（修改：shutdown 释放模型） |
| python_ai_service | .env.example（修改：本地模型配置） |

## 核心实现要求

### LocalLLMProvider
- 继承 LLMProvider，`mode='local'`
- `__init__` 校验 `LLM_LOCAL_MODEL_PATH` 非空
- `load_model()` — 使用 `run_in_executor` 包装 Transformers 模型加载
- `generate()` — 使用 `run_in_executor` 包装 CPU 密集推理
- `generate_stream()` — 使用 `TextIteratorStreamer` + `threading.Thread` 流式输出
- `unload_model()` — 释放 GPU 显存（gc.collect + torch.cuda.empty_cache）

### 完整三路降级逻辑
- **initialize()** — AUTO 模式按 Builtin→API→Local 顺序初始化
- **_fallback()** — 运行时降级，按优先级切换 Provider
- **generate() 增强** — 失败时自动降级重试一次
- **_degradation_state** — 跟踪降级事件（fallback_count, last_fallback_at, consecutive_failures）
- **_recovery_task** — 每 5 分钟尝试恢复到更高级别 Provider

### 降级触发条件
- 连续 3 次调用失败
- 响应超时 30s
- HTTP 5xx

### 关键约束
- `load_model()` 和 `generate()` 必须使用 `run_in_executor` 避免阻塞事件循环
- 所有 Provider 失败时抛出 `LLMException`，不能静默失败
- 不修改 BuiltinLLMProvider / APILLMProvider 已有实现

## 文件清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `Veritas/ai-service/app/services/llm_service.py` | LocalLLMProvider + 完整降级 |
| 修改 | `Veritas/ai-service/app/core/events.py` | shutdown 释放模型 |
| 修改 | `Veritas/ai-service/.env.example` | 本地模型配置说明 |

## 验收标准
- [ ] `LocalLLMProvider` 继承 `LLMProvider`，`mode == 'local'`
- [ ] `load_model()` 使用 `run_in_executor` 避免阻塞
- [ ] `generate()` 使用 `run_in_executor` 包装推理
- [ ] `generate_stream()` 使用 `TextIteratorStreamer` 流式输出
- [ ] `unload_model()` 释放 GPU 显存
- [ ] `initialize()` 实现完整三路降级 Builtin→API→Local
- [ ] `_fallback()` 运行时按优先级切换 Provider
- [ ] `generate()` 失败时自动降级重试
- [ ] 所有 Provider 失败时抛出 `LLMException`
- [ ] `_degradation_state` 正确跟踪降级事件
- [ ] `_recovery_task` 每 5 分钟尝试恢复
- [ ] `on_shutdown` 调用 `unload_model` 释放资源
- [ ] 未修改已有 Provider 实现
