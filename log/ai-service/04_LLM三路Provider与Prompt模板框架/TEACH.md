# 技术教学文档

## 开发思路

### 需求分析过程
AI服务的核心依赖是大语言模型（LLM）调用，但不同部署环境下可用的LLM来源不同：
- 软件方（科大讯飞）可能提供内置云模型
- 用户可能自行配置第三方API（如阿里云百炼、DeepSeek）
- 开发/演示环境可能只有本地模型

因此需要一个**统一抽象层**，屏蔽底层差异，并具备**自动降级**能力确保服务可用性。

### 技术选型考虑
1. **LLM调用接口**：选择OpenAI SDK（`openai.AsyncOpenAI`）作为统一客户端，因为主流LLM服务商（DeepSeek、阿里云百炼、讯飞星火）均兼容OpenAI API格式
2. **本地模型推理**：选择HuggingFace Transformers + `run_in_executor`，而非vLLM/Ollama，因为项目预算有限（≤¥1500），单机部署，无需高并发推理服务
3. **Prompt模板引擎**：选择`string.Template`而非Jinja2，因为模板变量简单（仅需`$variable`替换），无需条件逻辑/循环等高级特性，`safe_substitute`还能防止未替换变量报错
4. **降级策略**：参考Circuit Breaker模式，但简化为线性降级链（A→B→C），5分钟恢复探测

### 架构设计思路

```
LLMService（门面）
    ├── providers: dict[str, LLMProvider]   # 已注册的Provider
    ├── active_provider: LLMProvider         # 当前活跃Provider
    ├── _degradation_state: dict             # 降级状态跟踪
    ├── _recovery_task: asyncio.Task         # 恢复探测定时任务
    │
    ├── BuiltinLLMProvider → AsyncOpenAI → 软件方模型
    ├── APILLMProvider      → AsyncOpenAI → 第三方API
    └── LocalLLMProvider    → Transformers → 本地模型
```

### 遇到的问题及解决方案

| 问题 | 解决方案 |
|------|---------|
| OpenAI SDK `stream=True` 返回awaitable而非async generator | 创建`MockAsyncStream`类实现`__aiter__`/`__anext__`，用`new_callable=AsyncMock, return_value=mock_stream` |
| `TextIteratorStreamer`是同步迭代器，无法直接`async for` | 使用`queue.Queue`+`threading.Thread`桥接，`run_in_executor`从队列取值 |
| `transformers`/`torch`在无GPU环境导入崩溃 | 延迟导入（方法内部`from transformers import ...`），避免模块级导入 |
| `_fallback()`调用`test_connection()`时类级别mock失效 | 初始化后Provider已是实例，需用`patch.object(instance, method)`而非`patch.object(Class, method)` |
| `gc`在`unload_model()`中是方法内导入 | 测试时用`patch("gc.collect")`而非`patch("app.services.llm_service.gc")` |

## 实现步骤

1. **Task06**：创建LLMProvider ABC + BuiltinLLMProvider + LLMService骨架
   - 定义`mode`/`generate()`/`generate_stream()`/`test_connection()`抽象接口
   - BuiltinLLMProvider使用`AsyncOpenAI`调用软件方模型
   - LLMService.initialize()尝试连接Builtin Provider
   - 编写18个测试验证

2. **Task07**：新增APILLMProvider + 扩展initialize()
   - APILLMProvider增加`LLM_API_KEY`必填验证
   - initialize()支持AUTO模式：Builtin失败→尝试API Provider
   - .env.example补充方案B配置示例（DeepSeek/讯飞星火/通义千问/阿里云百炼）
   - 测试扩展至28个

3. **Task08**：新增LocalLLMProvider + 完善三路降级
   - LocalLLMProvider使用`run_in_executor`包装CPU密集操作
   - `generate_stream()`使用`TextIteratorStreamer`+`threading.Thread`+`queue.Queue`
   - LLMService添加`_fallback()`/`_degradation_state`/`_recovery_task`
   - `generate()`/`generate_stream()`失败时自动降级重试
   - events.py on_shutdown调用`unload_model()`
   - .env.example补充方案C配置（Qwen2-7B/Qwen2-1.5B）
   - 测试扩展至47个

4. **Task09**：创建PromptManager + 6个Prompt模板 + Dockerfile
   - PromptManager使用`string.Template`+`safe_substitute`
   - 6个Agent模板：coordinator/retriever/analyzer/comparer/generator/reviewer
   - Dockerfile基于`python:3.10-slim`，含HEALTHCHECK
   - events.py添加prompt_manager全局变量
   - main.py /health添加prompts状态
   - 新增test_prompt_manager.py（12个测试）+ test_integration.py（6个测试）

## 解决了什么问题

### 核心问题描述
1. **LLM调用无统一抽象** — 各处直接调用OpenAI SDK，无法切换Provider
2. **单点故障** — 只依赖一个LLM源，该源不可用时整个服务瘫痪
3. **Prompt硬编码** — Agent的Prompt散落在代码中，难以维护和个性化
4. **无Docker化** — AI服务无法容器化部署

### 解决方案对比

| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| 直接调用OpenAI SDK | 简单 | 无法切换/降级 | ❌ |
| LangChain ChatModel | 生态丰富 | 过度依赖、抽象过深 | ❌ |
| 自定义Provider ABC + 降级 | 轻量、可控 | 需自行实现 | ✅ |
| Jinja2模板 | 功能强大 | 过度设计、依赖重 | ❌ |
| string.Template | 轻量、安全 | 无条件逻辑 | ✅ |

### 最终方案的优势
- **零外部依赖增加**：Provider ABC和PromptManager均为自研，不引入新依赖
- **降级透明**：调用方只需`await llm_service.generate()`，降级逻辑完全内聚
- **安全替换**：`safe_substitute`不会因缺少变量而报错，适合Prompt模板场景
- **延迟导入**：transformers/torch仅在需要时导入，不影响无GPU环境启动

## 变更内容

### 新增文件
- `app/services/prompt_manager.py` — PromptManager模板管理服务
- `prompts/coordinator.txt` — 协调者Agent Prompt模板（变量：$query, $user_profile）
- `prompts/retriever.txt` — 检索Agent Prompt模板（变量：$topic, $top_k）
- `prompts/analyzer.txt` — 分析Agent Prompt模板（变量：$paper_title, $paper_abstract, $extra_instruction）
- `prompts/comparer.txt` — 对比Agent Prompt模板（变量：$analysis_data）
- `prompts/generator.txt` — 生成Agent Prompt模板（变量：$personalization, $analysis_data, $comparison_data）
- `prompts/reviewer.txt` — 审核Agent Prompt模板（变量：$report_content, $original_papers）
- `Dockerfile` — AI服务Docker镜像构建文件
- `tests/test_prompt_manager.py` — PromptManager单元测试（12个测试）
- `tests/test_integration.py` — 集成测试（6个测试）

### 修改文件
- `app/services/llm_service.py`
  - 新增`LocalLLMProvider`类（load_model/generate/generate_stream/test_connection/unload_model）
  - LLMService新增`PROVIDER_PRIORITY`/`_degradation_state`/`_recovery_task`
  - LLMService新增`_fallback()`/`_start_recovery_task()`/`unload_model()`
  - `initialize()`扩展支持Local Provider + 抛出RuntimeError
  - `generate()`/`generate_stream()`增加失败降级重试逻辑
- `app/core/events.py`
  - 新增`prompt_manager`全局变量
  - `on_startup()`添加PromptManager加载
  - `on_shutdown()`调用`llm_service.unload_model()`
- `app/main.py`
  - `/health`端点添加`prompts`状态字段
- `.env.example`
  - 补充方案B详细配置示例（DeepSeek/讯飞星火/通义千问/阿里云百炼）
  - 补充方案C本地模型配置说明（Qwen2-7B/Qwen2-1.5B）
- `tests/test_llm.py`
  - 新增`TestLocalLLMProvider`（8个测试）
  - 新增`TestLLMServiceDegradation`（8个测试）
  - 更新`TestLLMService`适配initialize()抛出RuntimeError

### 配置变更
- `LLM_LOCAL_MODEL_PATH` — 新增，本地模型路径（如Qwen/Qwen2-1.5B-Instruct）
- `LLM_BUILTIN_API_KEY` — 新增，软件方模型API Key
- `LLM_BUILTIN_MODEL` — 新增，软件方模型名称

## 关键技术点

### 1. OpenAI SDK流式响应的Mock模式
```python
class MockAsyncStream:
    def __init__(self, chunks):
        self._chunks = chunks
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._chunks):
            raise StopAsyncIteration
        chunk = self._chunks[self._index]
        self._index += 1
        return chunk

# 关键：new_callable=AsyncMock, return_value=mock_stream
# 因为 stream=True 时 create() 返回 awaitable，await 后得到 async iterator
with patch.object(client.chat.completions, "create",
    new_callable=AsyncMock, return_value=mock_stream):
```

### 2. 同步迭代器→异步迭代器桥接
```python
# TextIteratorStreamer 是同步迭代器，不能直接 async for
# 解决方案：queue.Queue + threading.Thread + run_in_executor

text_queue: queue.Queue = queue.Queue()
finished = threading.Event()

def _enqueue():
    try:
        for text in streamer:       # 同步迭代
            text_queue.put(text)
    finally:
        finished.set()

enqueue_thread = threading.Thread(target=_enqueue)
enqueue_thread.start()

loop = asyncio.get_event_loop()
while not finished.is_set() or not text_queue.empty():
    try:
        text = await loop.run_in_executor(None, text_queue.get, True, 0.1)
        if text is not None:
            yield text               # 异步产出
    except queue.Empty:
        continue
```

### 3. 延迟导入避免环境依赖
```python
# ❌ 模块级导入 — 无GPU环境直接崩溃
from transformers import AutoModelForCausalLM

# ✅ 方法内延迟导入 — 仅在需要时导入，不影响启动
async def load_model(self) -> None:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, self._sync_load_model)

def _sync_load_model(self) -> None:
    from transformers import AutoModelForCausalLM, AutoTokenizer  # 延迟导入
    self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
    self.model = AutoModelForCausalLM.from_pretrained(...)
```

### 4. 降级恢复定时任务
```python
async def _recovery_loop():
    while True:
        await asyncio.sleep(300)  # 5分钟探测一次
        current_idx = self.PROVIDER_PRIORITY.index(self.active_provider.mode)
        for i in range(current_idx):  # 只尝试比当前更高级别的Provider
            provider_name = self.PROVIDER_PRIORITY[i]
            provider = self.providers.get(provider_name)
            if provider is None:
                continue
            try:
                await provider.test_connection()
                self.active_provider = provider  # 恢复到更高级别
                break
            except Exception:
                continue

self._recovery_task = asyncio.create_task(_recovery_loop())
```

## 经验总结

### 开发过程中的收获
1. **OpenAI SDK的stream行为**：`stream=True`时`create()`返回的是awaitable（需await后得到async iterator），而非直接返回async generator。这个坑在测试时暴露，需要MockAsyncStream类来正确模拟
2. **类级别mock vs 实例级别mock**：`patch.object(Class, method)`在类实例化后创建的实例上生效，但一旦mock context退出，后续对该实例的调用不再受mock影响。运行时降级测试需要`patch.object(instance, method)`
3. **string.Template的safe_substitute**：与`substitute`不同，`safe_substitute`在变量缺失时保留原始`$variable`文本而非抛出`KeyError`，这对Prompt模板场景非常实用——部分变量可选时不会中断渲染

### 踩过的坑及如何避免
1. **坑：`gc`在`unload_model()`中是方法内`import gc`**，测试时`patch("app.services.llm_service.gc")`找不到属性
   - 避免：方法内导入的模块应直接`patch("gc.collect")`而非通过模块路径
2. **坑：initialize()在所有Provider不可用时不抛异常，导致后续generate()莫名失败**
   - 避免：initialize()在active_provider为None时主动抛出RuntimeError，fail-fast原则
3. **坑：generate_stream()中TextIteratorStreamer的done属性不可靠**
   - 避免：使用独立的`threading.Event()`和`queue.Queue`桥接，而非依赖streamer.done

### 最佳实践建议
1. **Provider ABC设计**：抽象接口应尽量精简（4个方法），具体实现细节留给子类
2. **降级状态可观测**：`_degradation_state`应包含足够信息（当前Provider/降级次数/时间/失败计数），便于监控和调试
3. **Prompt模板变量命名**：使用`$variable`格式（string.Template），与Jinja2的`{{variable}}`区分，避免混淆
4. **Dockerfile层缓存**：先COPY requirements.txt并安装依赖，再COPY代码，代码变更不会导致依赖重装
5. **测试隔离**：每个Provider的测试应独立，降级测试需要精确控制mock的作用域
