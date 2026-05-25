# Task06-09 LLM Provider + Prompt模板 + Dockerfile 执行计划

## 当前状态

- **Task06** ✅ 已完成 — BuiltinLLMProvider + LLMService骨架，18个测试全部通过
- **Task07** ⚠️ 代码已写，测试未运行 — APILLMProvider + initialize()扩展
- **Task08** ❌ 未开始 — LocalLLMProvider + 三路降级 + 恢复机制
- **Task09** ❌ 未开始 — PromptManager + 6个模板 + Dockerfile + 集成测试

---

## Task07: 验证 APILLMProvider（先跑测试）

### 步骤

1. **运行现有测试** — `cd Veritas/ai-service && python3 -m pytest tests/test_llm.py -v`
   - 验证Task06原有18个测试 + Task07新增API Provider测试全部通过
2. **如有失败则修复** — 根据错误信息调整代码

### 涉及文件（只读/验证）

- `app/services/llm_service.py` — 已含APILLMProvider
- `tests/test_llm.py` — 已含TestAPILLMProvider + 新LLMService测试

---

## Task08: LocalLLMProvider + 完整三路降级

### 步骤

#### 8-1. 在 llm_service.py 新增 LocalLLMProvider 类

在 `APILLMProvider` 类之后添加：

```python
class LocalLLMProvider(LLMProvider):
    def __init__(self, settings) -> None:
        self._mode = "local"
        if not settings.LLM_LOCAL_MODEL_PATH:
            raise ValueError("LLM_LOCAL_MODEL_PATH is required for local provider")
        self.model_path = settings.LLM_LOCAL_MODEL_PATH
        self.model = None
        self.tokenizer = None

    @property
    def mode(self) -> str:
        return self._mode

    async def load_model(self) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_load_model)

    def _sync_load_model(self) -> None:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path, torch_dtype="auto", device_map="auto"
        )
        logger.info(f"Local model loaded: {self.model_path}")

    async def generate(self, prompt, max_tokens=2048, temperature=0.7) -> str:
        if self.model is None or self.tokenizer is None:
            raise ModelNotLoadedException("Local model not loaded")
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_generate, prompt, max_tokens, temperature)

    def _sync_generate(self, prompt, max_tokens, temperature) -> str:
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        outputs = self.model.generate(**inputs, max_new_tokens=max_tokens, temperature=temperature, do_sample=True)
        return self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)

    async def generate_stream(self, prompt, max_tokens=2048, temperature=0.7) -> AsyncIterator[str]:
        if self.model is None or self.tokenizer is None:
            raise ModelNotLoadedException("Local model not loaded")
        from transformers import TextIteratorStreamer
        import threading
        streamer = TextIteratorStreamer(self.tokenizer, skip_special_tokens=True)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        generation_kwargs = {**inputs, "max_new_tokens": max_tokens, "temperature": temperature, "streamer": streamer, "do_sample": True}
        thread = threading.Thread(target=self.model.generate, kwargs=generation_kwargs)
        thread.start()
        loop = asyncio.get_event_loop()
        while thread.is_alive() or not streamer.done:
            try:
                text = await loop.run_in_executor(None, next, iter(streamer), None)
                if text is not None:
                    yield text
            except StopIteration:
                break
        thread.join()

    async def test_connection(self) -> bool:
        if self.model is not None and self.tokenizer is not None:
            return True
        raise ModelNotLoadedException("Local model not loaded")

    async def unload_model(self) -> None:
        if self.model is not None:
            del self.model
        if self.tokenizer is not None:
            del self.tokenizer
        self.model = None
        self.tokenizer = None
        import gc
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
        logger.info("Local model unloaded, GPU memory released")
```

**关键设计决策**：
- `load_model()` 和 `generate()` 使用 `run_in_executor` 避免阻塞事件循环
- `generate_stream()` 使用 `TextIteratorStreamer` + `threading.Thread` + `run_in_executor` 适配异步
- `unload_model()` 包含 `gc.collect()` + `torch.cuda.empty_cache()` 释放GPU显存
- `torch` 和 `transformers` 延迟导入（`import` 在方法内部），避免在无GPU环境启动时崩溃

#### 8-2. 完善 LLMService 三路降级逻辑

修改 `LLMService` 类：

1. **添加降级状态属性**：
```python
PROVIDER_PRIORITY = ["builtin", "api", "local"]

def __init__(self, settings):
    # ... 现有代码 ...
    self._degradation_state = {
        "current_provider": None,
        "fallback_count": 0,
        "last_fallback_at": None,
        "consecutive_failures": {},
    }
    self._recovery_task = None
```

2. **扩展 initialize()** — 在API Provider逻辑之后添加Local Provider：
```python
if self.mode in (LLMMode.AUTO, LLMMode.LOCAL):
    if self.settings.LLM_LOCAL_MODEL_PATH:
        try:
            provider = LocalLLMProvider(self.settings)
            await provider.load_model()
            await provider.test_connection()
            self.providers["local"] = provider
            if self.active_provider is None:
                self.active_provider = provider
                self._status = "loaded"
                logger.info("LLM: Using local provider")
            else:
                logger.info("LLM: Local provider available as fallback")
        except Exception as e:
            logger.warning(f"Local provider failed: {e}")

if self.active_provider is None:
    self._status = "error"
    raise RuntimeError("No LLM provider available")
else:
    self._degradation_state["current_provider"] = self.active_provider.mode
    self._start_recovery_task()
```

3. **实现 _fallback()**：
```python
async def _fallback(self) -> None:
    current = self.active_provider.mode if self.active_provider else None
    for provider_name in self.PROVIDER_PRIORITY:
        if provider_name == current:
            continue
        provider = self.providers.get(provider_name)
        if provider is None:
            continue
        try:
            await provider.test_connection()
            self.active_provider = provider
            self._degradation_state["current_provider"] = provider_name
            self._degradation_state["fallback_count"] += 1
            self._degradation_state["last_fallback_at"] = datetime.now(timezone.utc).isoformat()
            logger.warning(f"LLM fallback: {current} → {provider_name}")
            return
        except Exception:
            continue
    raise LLMException("All LLM providers failed")
```

4. **增强 generate() 和 generate_stream()** — 失败时降级重试：
```python
async def generate(self, prompt, max_tokens=2048, temperature=0.7) -> str:
    if self.active_provider is None:
        raise ModelNotLoadedException("LLM service not initialized")
    try:
        return await self.active_provider.generate(prompt, max_tokens, temperature)
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        provider_name = self.active_provider.mode
        self._degradation_state["consecutive_failures"][provider_name] = \
            self._degradation_state["consecutive_failures"].get(provider_name, 0) + 1
        try:
            await self._fallback()
            return await self.active_provider.generate(prompt, max_tokens, temperature)
        except Exception as fallback_err:
            raise LLMException(str(fallback_err)) from fallback_err
```

5. **实现 _start_recovery_task()**：
```python
def _start_recovery_task(self) -> None:
    async def _recovery_loop():
        while True:
            await asyncio.sleep(300)  # 5分钟
            try:
                current_idx = self.PROVIDER_PRIORITY.index(
                    self.active_provider.mode if self.active_provider else "local"
                )
                for i in range(current_idx):
                    provider_name = self.PROVIDER_PRIORITY[i]
                    provider = self.providers.get(provider_name)
                    if provider is None:
                        continue
                    try:
                        await provider.test_connection()
                        old = self.active_provider.mode
                        self.active_provider = provider
                        self._degradation_state["current_provider"] = provider_name
                        logger.info(f"LLM recovered: {old} → {provider_name}")
                        break
                    except Exception:
                        continue
            except Exception as e:
                logger.debug(f"Recovery check failed: {e}")

    self._recovery_task = asyncio.create_task(_recovery_loop())

async def unload_model(self) -> None:
    if self._recovery_task is not None:
        self._recovery_task.cancel()
        self._recovery_task = None
    local_provider = self.providers.get("local")
    if local_provider is not None:
        await local_provider.unload_model()
```

#### 8-3. 修改 events.py on_shutdown

```python
if llm_service is not None:
    try:
        await llm_service.unload_model()
    except Exception as e:
        logger.error(f"LLMService unload_model failed: {e}")
```

#### 8-4. 更新 .env.example 方案C

```env
# 方案C：本地模型（最低优先级，兜底方案）
# 支持Transformers兼容模型，推荐配置：
#
# Qwen2-7B-Instruct（需GPU显存≥16GB）:
# LLM_LOCAL_MODEL_PATH=Qwen/Qwen2-7B-Instruct
#
# Qwen2-1.5B-Instruct（CPU可运行，约4GB内存）:
# LLM_LOCAL_MODEL_PATH=Qwen/Qwen2-1.5B-Instruct
#
# LLM_LOCAL_MODEL_PATH=      # 本地模型路径，如 Qwen/Qwen2-7B-Instruct
```

#### 8-5. 补充 Local Provider + 降级测试

在 `tests/test_llm.py` 添加：

- `TestLocalLLMProvider` 类：初始化/mode/load_model/generate/unload_model/test_connection
- `TestLLMServiceDegradation` 类：三路降级初始化/运行时降级/降级状态跟踪/所有Provider失败
- 所有mock使用 `unittest.mock.patch` 模拟 `transformers` 模块

#### 8-6. 运行测试验证

```bash
cd Veritas/ai-service && python3 -m pytest tests/test_llm.py -v
```

### 涉及文件

| 文件 | 操作 |
|------|------|
| `app/services/llm_service.py` | 修改 — 新增LocalLLMProvider + 完善LLMService降级 |
| `app/core/events.py` | 修改 — on_shutdown添加unload_model |
| `.env.example` | 修改 — 补充方案C配置说明 |
| `tests/test_llm.py` | 修改 — 新增Local Provider和降级测试 |

---

## Task09: Prompt模板 + Dockerfile + 集成测试

### 步骤

#### 9-1. 创建 PromptManager

文件：`app/services/prompt_manager.py`

```python
from pathlib import Path
from string import Template
from typing import Dict

from loguru import logger


class PromptManager:

    def __init__(self, prompts_dir: str = "prompts") -> None:
        self.prompts_dir = Path(prompts_dir)
        self.templates: Dict[str, Template] = {}
        self.status = "initializing"

    async def load_templates(self) -> None:
        if not self.prompts_dir.exists():
            logger.warning(f"Prompts directory not found: {self.prompts_dir}")
            self.prompts_dir.mkdir(parents=True, exist_ok=True)
        for file_path in self.prompts_dir.glob("*.txt"):
            content = file_path.read_text(encoding="utf-8")
            self.templates[file_path.stem] = Template(content)
        self.status = "loaded"
        logger.info(f"Loaded {len(self.templates)} prompt templates")

    def get_prompt(self, agent_name: str, **kwargs) -> str:
        if agent_name not in self.templates:
            raise KeyError(f"Prompt template not found: {agent_name}")
        return self.templates[agent_name].safe_substitute(**kwargs)

    def list_templates(self) -> list[str]:
        return sorted(self.templates.keys())
```

#### 9-2. 创建6个Prompt模板文件

在 `prompts/` 目录下创建：

| 文件 | 角色 | 变量 |
|------|------|------|
| `coordinator.txt` | 项目经理 | $query, $user_profile |
| `retriever.txt` | 图书管理员 | $topic, $top_k |
| `analyzer.txt` | 论文审稿人 | $paper_title, $paper_abstract, $extra_instruction |
| `comparer.txt` | 对比研究员 | $analysis_data |
| `generator.txt` | 学术写手 | $personalization, $analysis_data, $comparison_data |
| `reviewer.txt` | 学术编辑 | $report_content, $original_papers |

**注意**：架构文档使用 `{{variable}}` 双花括号语法，但 `string.Template` 使用 `$variable` 语法。按开发规范文档要求使用 `string.Template`，因此模板变量统一使用 `$variable` 格式。

#### 9-3. 创建 Dockerfile

文件：`Veritas/ai-service/Dockerfile`

按架构文档§19.1规范，基于 `python:3.10-slim`，含HEALTHCHECK。

#### 9-4. 修改 events.py + main.py

- `events.py`：添加 `prompt_manager` 全局变量，`on_startup()` 中加载模板
- `main.py`：`/health` 添加 `prompts` 状态字段

#### 9-5. 创建 test_prompt_manager.py

测试：load_templates加载6个模板、get_prompt变量替换、safe_substitute未替换变量保留、模板不存在KeyError、list_templates排序

#### 9-6. 创建 test_integration.py

集成测试：FastAPI应用启动/健康检查/各组件状态/PromptManager+LLMService端到端

#### 9-7. 运行测试验证

```bash
cd Veritas/ai-service && python3 -m pytest tests/test_prompt_manager.py tests/test_integration.py -v
```

### 涉及文件

| 文件 | 操作 |
|------|------|
| `app/services/prompt_manager.py` | 新建 |
| `prompts/coordinator.txt` | 新建 |
| `prompts/retriever.txt` | 新建 |
| `prompts/analyzer.txt` | 新建 |
| `prompts/comparer.txt` | 新建 |
| `prompts/generator.txt` | 新建 |
| `prompts/reviewer.txt` | 新建 |
| `Dockerfile` | 新建 |
| `tests/test_prompt_manager.py` | 新建 |
| `tests/test_integration.py` | 新建 |
| `app/core/events.py` | 修改 |
| `app/main.py` | 修改 |

---

## 执行顺序

```
Task07验证 → Task08(8-1→8-2→8-3→8-4→8-5→8-6) → Task09(9-1→9-2→9-3→9-4→9-5→9-6→9-7)
```

## 风险与注意事项

1. **transformers延迟导入**：LocalLLMProvider中 `from transformers import ...` 必须在方法内部，避免在无GPU/无transformers环境启动时崩溃
2. **generate_stream异步适配**：TextIteratorStreamer是同步迭代器，需通过 `run_in_executor` 或 `asyncio.Queue` 适配到async for
3. **测试mock策略**：LocalLLMProvider测试需mock整个transformers模块（AutoModelForCausalLM/AutoTokenizer/TextIteratorStreamer）
4. **Prompt变量语法**：使用 `$variable`（string.Template）而非 `{{variable}}`（Jinja2），与开发规范一致
5. **降级状态线程安全**：`_degradation_state` 在单worker模式下无需加锁，但需注意recovery_task的cancel时机
