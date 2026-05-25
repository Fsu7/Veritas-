from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import AsyncIterator

import asyncio
from loguru import logger
from openai import AsyncOpenAI

from app.exception import LLMException, ModelNotLoadedException


class LLMMode(str, Enum):
    AUTO = "auto"
    BUILTIN = "builtin"
    API = "api"
    LOCAL = "local"


class LLMProvider(ABC):

    @property
    @abstractmethod
    def mode(self) -> str:
        pass

    @abstractmethod
    async def generate(
        self, prompt: str, max_tokens: int = 2048, temperature: float = 0.7
    ) -> str:
        pass

    @abstractmethod
    async def generate_stream(
        self, prompt: str, max_tokens: int = 2048, temperature: float = 0.7
    ) -> AsyncIterator[str]:
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        pass


class BuiltinLLMProvider(LLMProvider):

    def __init__(self, settings) -> None:
        self._mode = "builtin"
        self.client = AsyncOpenAI(
            api_key=settings.LLM_BUILTIN_API_KEY or "builtin",
            base_url=settings.LLM_BUILTIN_URL,
        )
        self.model_name = settings.LLM_BUILTIN_MODEL or "literature-assistant-pro"

    @property
    def mode(self) -> str:
        return self._mode

    async def generate(
        self, prompt: str, max_tokens: int = 2048, temperature: float = 0.7
    ) -> str:
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content

    async def generate_stream(
        self, prompt: str, max_tokens: int = 2048, temperature: float = 0.7
    ) -> AsyncIterator[str]:
        stream = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content is not None:
                yield content

    async def test_connection(self) -> bool:
        await self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5,
        )
        return True


class APILLMProvider(LLMProvider):

    def __init__(self, settings) -> None:
        self._mode = "api"
        if not settings.LLM_API_KEY:
            raise ValueError("LLM_API_KEY is required for API provider")
        self.client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_API_BASE,
        )
        self.model_name = settings.LLM_MODEL_NAME

    @property
    def mode(self) -> str:
        return self._mode

    async def generate(
        self, prompt: str, max_tokens: int = 2048, temperature: float = 0.7
    ) -> str:
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content

    async def generate_stream(
        self, prompt: str, max_tokens: int = 2048, temperature: float = 0.7
    ) -> AsyncIterator[str]:
        stream = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content is not None:
                yield content

    async def test_connection(self) -> bool:
        await self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5,
        )
        return True


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

    async def generate(
        self, prompt: str, max_tokens: int = 2048, temperature: float = 0.7
    ) -> str:
        if self.model is None or self.tokenizer is None:
            raise ModelNotLoadedException("Local model not loaded")
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._sync_generate, prompt, max_tokens, temperature
        )

    def _sync_generate(self, prompt: str, max_tokens: int, temperature: float) -> str:
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=True,
        )
        return self.tokenizer.decode(
            outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True
        )

    async def generate_stream(
        self, prompt: str, max_tokens: int = 2048, temperature: float = 0.7
    ) -> AsyncIterator[str]:
        if self.model is None or self.tokenizer is None:
            raise ModelNotLoadedException("Local model not loaded")
        from transformers import TextIteratorStreamer
        import threading
        import queue

        streamer = TextIteratorStreamer(self.tokenizer, skip_special_tokens=True)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        generation_kwargs = {
            **inputs,
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "streamer": streamer,
            "do_sample": True,
        }
        thread = threading.Thread(target=self.model.generate, kwargs=generation_kwargs)
        thread.start()

        text_queue: queue.Queue = queue.Queue()
        finished = threading.Event()

        def _enqueue():
            try:
                for text in streamer:
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
                    yield text
            except queue.Empty:
                continue

        thread.join()
        enqueue_thread.join()

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


class LLMService:

    PROVIDER_PRIORITY = ["builtin", "api", "local"]

    def __init__(self, settings) -> None:
        self.settings = settings
        self.mode = settings.LLM_MODE
        self.providers: dict[str, LLMProvider] = {}
        self.active_provider: LLMProvider | None = None
        self._status = "initializing"
        self._degradation_state = {
            "current_provider": None,
            "fallback_count": 0,
            "last_fallback_at": None,
            "consecutive_failures": {},
        }
        self._recovery_task: asyncio.Task | None = None

    @property
    def status(self) -> str:
        return self._status

    async def initialize(self) -> None:
        if self.mode in (LLMMode.AUTO, LLMMode.BUILTIN):
            try:
                provider = BuiltinLLMProvider(self.settings)
                await provider.test_connection()
                self.providers["builtin"] = provider
                self.active_provider = provider
                self._status = "loaded"
                logger.info("LLM: Using builtin provider")
            except Exception as e:
                logger.warning(f"Builtin provider failed: {e}")

        if self.mode in (LLMMode.AUTO, LLMMode.API):
            if self.settings.LLM_API_KEY:
                try:
                    provider = APILLMProvider(self.settings)
                    await provider.test_connection()
                    self.providers["api"] = provider
                    if self.active_provider is None:
                        self.active_provider = provider
                        self._status = "loaded"
                        logger.info("LLM: Using API provider")
                    else:
                        logger.info("LLM: API provider available as fallback")
                except Exception as e:
                    logger.warning(f"API provider failed: {e}")

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
                self._degradation_state["last_fallback_at"] = datetime.now(
                    timezone.utc
                ).isoformat()
                logger.warning(f"LLM fallback: {current} → {provider_name}")
                return
            except Exception:
                continue
        raise LLMException("All LLM providers failed")

    def _start_recovery_task(self) -> None:
        async def _recovery_loop():
            while True:
                await asyncio.sleep(300)
                try:
                    current_mode = (
                        self.active_provider.mode if self.active_provider else "local"
                    )
                    current_idx = self.PROVIDER_PRIORITY.index(current_mode)
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
            try:
                await self._recovery_task
            except asyncio.CancelledError:
                pass
            self._recovery_task = None
        local_provider = self.providers.get("local")
        if local_provider is not None:
            await local_provider.unload_model()

    async def generate(
        self, prompt: str, max_tokens: int = 2048, temperature: float = 0.7
    ) -> str:
        if self.active_provider is None:
            raise ModelNotLoadedException("LLM service not initialized")
        try:
            return await self.active_provider.generate(prompt, max_tokens, temperature)
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            provider_name = self.active_provider.mode
            self._degradation_state["consecutive_failures"][provider_name] = (
                self._degradation_state["consecutive_failures"].get(provider_name, 0)
                + 1
            )
            try:
                await self._fallback()
                return await self.active_provider.generate(
                    prompt, max_tokens, temperature
                )
            except Exception as fallback_err:
                raise LLMException(str(fallback_err)) from fallback_err

    async def generate_stream(
        self, prompt: str, max_tokens: int = 2048, temperature: float = 0.7
    ) -> AsyncIterator[str]:
        if self.active_provider is None:
            raise ModelNotLoadedException("LLM service not initialized")
        try:
            async for token in self.active_provider.generate_stream(
                prompt, max_tokens, temperature
            ):
                yield token
        except Exception as e:
            logger.error(f"LLM stream failed: {e}")
            provider_name = self.active_provider.mode
            self._degradation_state["consecutive_failures"][provider_name] = (
                self._degradation_state["consecutive_failures"].get(provider_name, 0)
                + 1
            )
            try:
                await self._fallback()
                async for token in self.active_provider.generate_stream(
                    prompt, max_tokens, temperature
                ):
                    yield token
            except Exception as fallback_err:
                raise LLMException(str(fallback_err)) from fallback_err
