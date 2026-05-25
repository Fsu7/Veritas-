# task06 — LLM服务骨架 + BuiltinLLMProvider（软件方模型）

## 项目
XH-202630 科研文献智能助手 — v0.1 M1：基础设施就绪 / AM1：项目骨架与模型层就绪

## 需求概述
实现 LLM 服务骨架与 BuiltinLLMProvider（软件方云端模型服务），为后续 APILLMProvider 和 LocalLLMProvider 奠定基础。

核心交付：
1. `services/llm_service.py` — LLMMode 枚举 + LLMProvider 抽象基类 + BuiltinLLMProvider 实现 + LLMService 统一服务类
2. `events.py` 启动时初始化 LLMService（仅 BuiltinLLMProvider）
3. `main.py` /health 返回真实 LLM 状态
4. `.env.example` 补充 LLM 配置注释

## 影响范围

| 层级 | 涉及模块 |
|------|---------|
| python_ai_service | app/services/llm_service.py（新增） |
| python_ai_service | app/core/events.py（修改：加载 LLMService） |
| python_ai_service | app/main.py（修改：health 状态） |
| python_ai_service | .env.example（修改：补充注释） |

## 核心实现要求

### LLMMode 枚举
- `AUTO='auto'` — 自动模式，按优先级降级
- `BUILTIN='builtin'` — 强制使用软件方模型
- `API='api'` — 强制使用外接 API
- `LOCAL='local'` — 强制使用本地模型

### LLMProvider 抽象基类
定义统一接口：`mode` 属性、`generate()`、`generate_stream()`、`test_connection()`

### BuiltinLLMProvider
- 使用 `openai.AsyncOpenAI` 客户端
- `api_key=settings.LLM_BUILTIN_API_KEY`，`base_url=settings.LLM_BUILTIN_URL`
- `model_name=settings.LLM_BUILTIN_MODEL`
- `generate()` → `client.chat.completions.create()` 返回完整文本
- `generate_stream()` → `stream=True`，逐 Token 产出
- `test_connection()` → 发送极短 prompt 验证连接

### LLMService
- `initialize()` — 尝试创建 BuiltinLLMProvider 并 test_connection
- `generate()` / `generate_stream()` — 委托 active_provider
- 本任务**不实现降级逻辑**（task08 实现）

### 关键约束
- API Key 通过环境变量注入，禁止硬编码
- 必须使用 `AsyncOpenAI`，禁止同步客户端
- 日志中禁止输出完整 API Key
- 流式响应中 `delta.content` 可能为 None，必须判空

## 文件清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | `Veritas/ai-service/app/services/llm_service.py` | LLM 服务骨架 + BuiltinLLMProvider |
| 修改 | `Veritas/ai-service/app/core/events.py` | 启动时加载 LLMService |
| 修改 | `Veritas/ai-service/app/main.py` | /health 返回真实 LLM 状态 |
| 修改 | `Veritas/ai-service/.env.example` | 补充 LLM 配置注释 |

## 验收标准
- [ ] `LLMMode` 枚举包含 AUTO/BUILTIN/API/LOCAL 四种模式
- [ ] `LLMProvider` 抽象基类定义 4 个抽象接口
- [ ] `BuiltinLLMProvider` 使用 `AsyncOpenAI` 客户端，配置从 settings 读取
- [ ] `generate()` 返回完整文本字符串
- [ ] `generate_stream()` 逐 Token 产出，跳过 None content
- [ ] `LLMService.initialize()` 尝试初始化 BuiltinLLMProvider
- [ ] `generate()` 在 active_provider 为空时抛出 `ModelNotLoadedException`
- [ ] `events.py` 启动时创建全局 `llm_service` 实例
- [ ] `/health` 返回真实 LLM 状态而非 `'not_loaded'`
- [ ] 日志中不输出完整 API Key
- [ ] 单元测试全部通过
