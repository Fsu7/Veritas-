# task51: LLM 流式输出优化（首字节 < 2s）

> **课题编号**：XH-202630
> **子项目**：科研文献助手 — AI 服务模块
> **里程碑**：M5 / AM5：混合检索与功能完善
> **AM5 天数**：Week 9 Day 6-7
> **版本**：v0.5
> **功能编号**：F3.3.2, F3.3.5
> **优先级**：P0
> **创建日期**：2026-06-17

---

## 1. 背景与上下文

### 1.1 项目背景

XH-202630 科研文献智能助手 — LLM 服务采用三级降级架构（Builtin → API → Local），已实现 generate_stream() 流式输出。但当前实现缺乏首字节延迟计时，无法验证 AM5 验收硬指标"首字节 < 2 秒"。

### 1.2 任务需求

优化 LLM generate_stream() 首字节延迟，验证 < 2 秒（AM5 验收硬指标）。记录首字节时间戳并日志输出 first_token_latency_ms。流式输出失败时降级为非流式 generate()，不阻塞流程。支持 max_tokens/temperature 参数透传。提供基准测试脚本测量 10 次首字节延迟，输出 P50/P95/P99。

### 1.3 参考文档

| 文档 | 用途 |
|------|------|
| [docs/ai-service/AI服务模块系统架构文档.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块系统架构文档.md) | 了解 LLM 三级降级架构和 generate_stream 接口 |
| [docs/ai-service/AI服务模块项目里程碑文档.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块项目里程碑文档.md) | 确认 AM5 Week 9 Day 6-7 流式输出优化交付物和首字节<2秒硬指标 |
| [AGENTS.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/AGENTS.md) | 确认 LLM 降级约束和流式输出规范 |

---

## 2. 当前架构

### 2.1 涉及层级

- `python_ai_service`

### 2.2 相关模块

| 层级 | 模块路径 | 描述 |
|------|---------|------|
| python_ai_service | `app.services.llm_service` | LLMService 已实现三级降级（Builtin/API/Local）+ generate_stream()，但无首字节计时 |
| python_ai_service | `app.core.config` | Settings 配置类，需新增 LLM_STREAM_TIMEOUT |
| python_ai_service | `app.services.llm_service.BuiltinLLMProvider` | 内置 LLM Provider，generate_stream() 已实现 |
| python_ai_service | `app.services.llm_service.APILLMProvider` | API LLM Provider（DashScope/DeepSeek），generate_stream() 已实现 |
| python_ai_service | `app.services.llm_service.LocalLLMProvider` | 本地 LLM Provider，generate_stream() 已实现 |

### 2.3 现有实现

| 文件 | 描述 | 复用方式 |
|------|------|---------|
| `Veritas/ai-service/app/services/llm_service.py` | LLMService.generate_stream() 委托给 active_provider.generate_stream()，已有降级逻辑 | extend |
| `Veritas/ai-service/app/core/config.py` | Settings 配置类已存在，需新增 LLM_STREAM_TIMEOUT 配置项 | extend |

---

## 3. 相关模块详情

### 3.1 LLMService

- **路径**：`Veritas/ai-service/app/services/llm_service.py`
- **职责**：LLM 统一接口，三级降级，流式输出

| 方法 | 签名 | 描述 |
|------|------|------|
| `generate_stream` | `async def generate_stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]` | 流式生成，yield token，需增加首字节计时 |
| `generate` | `async def generate(self, prompt: str, **kwargs) -> str` | 非流式生成，流式失败时降级调用 |
| `_fallback_provider` | `def _fallback_provider(self, failed_provider: str) -> Optional[BaseLLMProvider]` | Provider 降级逻辑 |

### 3.2 BaseLLMProvider

- **路径**：`Veritas/ai-service/app/services/llm_service.py`
- **职责**：LLM Provider 抽象基类

| 方法 | 签名 | 描述 |
|------|------|------|
| `generate_stream` | `async def generate_stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]` | 子类实现流式生成 |

---

## 4. 待修改文件

| 操作 | 路径 | 说明 |
|------|------|------|
| modify | `Veritas/ai-service/app/services/llm_service.py` | 1) LLMService.generate_stream() 增加首字节计时：记录 stream_start_time，首个 token yield 前记录 first_token_time，计算 first_token_latency_ms 并 logger.info 输出；2) 流式失败（Provider 抛异常或超时）时降级调用 self.generate() 并 yield 完整结果；3) generate_stream 支持 max_tokens/temperature 参数透传到 provider.generate_stream()。 |
| modify | `Veritas/ai-service/app/core/config.py` | Settings 类新增 LLM_STREAM_TIMEOUT: int = 30（秒），支持环境变量覆盖。用于 generate_stream 的整体超时控制。 |
| create | `Veritas/ai-service/tests/benchmark/llm_stream_latency_benchmark.py` | 基准测试脚本：1) 调用 LLMService.generate_stream() 10 次，每次记录首字节延迟；2) 输出 P50/P95/P99 统计；3) 输出 Markdown 报告；4) 验证 P95 < 2000ms（AM5 验收硬指标）。 |
| create | `Veritas/ai-service/tests/test_llm_stream_optimization.py` | 单元测试：1) test_first_token_latency_logged 验证日志含 first_token_latency_ms；2) test_stream_fallback_to_non_stream 验证流式失败降级为非流式；3) test_max_tokens_temperature_passthrough 验证参数透传；4) test_stream_timeout_config 验证 LLM_STREAM_TIMEOUT 配置生效。 |

---

## 5. 实现要求

### 5.1 功能需求（FR）

| ID | 优先级 | 描述 | 验收条件 |
|----|--------|------|---------|
| FR-001 | P0 | LLMService.generate_stream() 增加首字节计时：1) 在调用 provider.generate_stream() 前记录 stream_start_time = time.perf_counter()；2) 在首个 token yield 前记录 first_token_time，计算 first_token_latency_ms = (first_token_time - stream_start_time) * 1000；3) 使用 logger.info 输出 'first_token_latency_ms={value}'；4) 仅首个 token 计时，后续 token 不重复计时。 | generate_stream() 日志包含 first_token_latency_ms |
| FR-002 | P0 | 首字节延迟 < 2000ms（AM5 验收硬指标）：1) 基准测试脚本测量 10 次首字节延迟；2) 计算 P95；3) 验证 P95 < 2000ms。若不达标，在基准测试报告中输出 WARNING 并建议优化方向（如预热连接、减少 prompt 长度）。 | 首字节延迟 P95 < 2000ms |
| FR-003 | P0 | 流式输出失败时降级为非流式 generate()：1) try-except 包裹 provider.generate_stream()；2) 捕获 Exception（含 TimeoutError、ConnectionError）；3) logger.warning 输出降级原因；4) 调用 self.generate(prompt, **kwargs) 获取完整结果；5) yield 完整结果（作为单个 token）；6) 不抛出异常，不阻塞流程。 | 流式失败降级为非流式，不抛出异常 |
| FR-004 | P1 | 支持 max_tokens / temperature 参数透传：1) generate_stream(self, prompt, **kwargs) 接受 max_tokens 和 temperature；2) 透传到 provider.generate_stream(prompt, max_tokens=..., temperature=...)；3) 若 provider 不支持参数，忽略不报错。 | max_tokens/temperature 参数正确透传到 provider |
| FR-005 | P1 | 基准测试脚本 tests/benchmark/llm_stream_latency_benchmark.py：1) 循环 10 次调用 LLMService.generate_stream()；2) 捕获日志中的 first_token_latency_ms（或自行计时）；3) 计算 P50/P95/P99；4) 输出 Markdown 报告到 tests/benchmark/reports/llm_stream_latency_report.md；5) 验证 P95 < 2000ms，不达标输出 WARNING。 | 基准测试脚本输出 P50/P95/P99 统计 |

### 5.2 降级需求

| 场景 | 策略 |
|------|------|
| 流式失败 | 流式失败降级为非流式 generate()，yield 完整结果 |
| Provider 失败 | Provider 降级链：Builtin → API → Local（已有逻辑保持不变） |

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

- LLM 服务在 `services/`
- 配置在 `core/`
- 基准测试在 `tests/benchmark/`
- 单元测试在 `tests/`

### 6.3 错误处理

- 流式失败降级为非流式，不抛出异常
- LLM 错误处理：`logger.warning` + 降级到 `generate()`

### 6.4 日志

- 日志库：Loguru
- 必需日志：`first_token_latency_ms={value}`
- 禁止：在每个 token yield 时打印日志

---

## 7. 禁止动作

| ID | 动作 | 原因 | 严重性 |
|----|------|------|--------|
| FA-001 | 输出伪代码或 TODO 注释 | 必须输出完整可执行代码 | critical |
| FA-002 | 修改三级降级链顺序（Builtin→API→Local） | 降级链已定义，仅增加流式→非流式降级 | high |
| FA-003 | 删除现有 generate() 非流式方法 | 流式降级依赖 generate() | critical |
| FA-004 | 在基准测试中调用真实 LLM API 且不 mock | 基准测试可调用真实 API，但需在 README 说明成本 | medium |
| FA-005 | 修改 Provider 子类的 generate_stream 签名 | 仅修改 LLMService 层，Provider 层保持不变 | high |
| FA-006 | 引入 async_timeout 或 asyncio.wait_for 包裹流式生成 | 流式生成是无限迭代器，不能用 wait_for 超时 | medium |

---

## 8. 测试要求

### 8.1 单元测试

| 测试名 | 描述 | 框架 | 覆盖范围 |
|--------|------|------|---------|
| test_first_token_latency_logged | 验证 generate_stream() 日志含 first_token_latency_ms | pytest | normal_flow |
| test_stream_fallback_to_non_stream | mock provider.generate_stream 抛异常，验证降级到 generate() | pytest | error_flow, degradation |
| test_max_tokens_temperature_passthrough | 验证 max_tokens/temperature 透传到 provider | pytest | normal_flow |
| test_stream_timeout_config | 验证 LLM_STREAM_TIMEOUT 配置项可从环境变量读取 | pytest | normal_flow |

### 8.2 基准测试

| 测试名 | 描述 | 框架 | 覆盖范围 |
|--------|------|------|---------|
| llm_stream_latency_benchmark | 基准测试：10 次首字节延迟，输出 P50/P95/P99 | pytest | performance |

### 8.3 验证命令

```bash
# 单元测试
cd Veritas/ai-service && python -m pytest tests/test_llm_stream_optimization.py -v
# 预期：4 个单元测试全部通过

# 基准测试
cd Veritas/ai-service && python tests/benchmark/llm_stream_latency_benchmark.py
# 预期：输出 Markdown 报告，P95 < 2000ms
```

---

## 9. 验收标准

| ID | 验收标准 | 验证方式 |
|----|---------|---------|
| AC-001 | generate_stream() 日志包含 first_token_latency_ms | automated_test |
| AC-002 | 首字节延迟 P95 < 2000ms | automated_test |
| AC-003 | 流式失败降级为非流式，不抛出异常 | automated_test |
| AC-004 | max_tokens/temperature 参数正确透传到 provider | automated_test |
| AC-005 | 基准测试脚本输出 P50/P95/P99 统计报告 | manual_test |
