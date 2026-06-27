"""EmbeddingService — task53 重构为多 Provider 架构

支持 DashScope / Jina / OpenAI 三种 Provider，可配置主 Provider + 降级链。
保留原有 encode/encode_batch 方法名（向后兼容 SearchService 调用）。

Provider 架构：
    BaseEmbeddingProvider (抽象基类)
        ├── DashScopeProvider  (阿里云百炼，1024维)
        ├── JinaProvider       (Jina AI，1024维)
        └── OpenAIProvider     (OpenAI，1536维截断前1024 + L2归一化)

降级策略：
    active_provider 失败 → 依次尝试 fallback_providers
"""
import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional, Union

import httpx
import numpy as np
from loguru import logger
from openai import AsyncOpenAI

from app.exception import ModelNotLoadedException


# ============================================================
# task53: Provider 抽象基类
# ============================================================


class BaseEmbeddingProvider(ABC):
    """Embedding Provider 抽象基类"""

    def __init__(self, name: str, dimension: int):
        self.name = name
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    @abstractmethod
    async def embed_query(self, text: str) -> np.ndarray:
        """单文本向量化"""
        pass

    @abstractmethod
    async def embed_documents(self, texts: List[str]) -> np.ndarray:
        """批量文本向量化"""
        pass

    def is_available(self) -> bool:
        """Provider 是否可用（子类可覆盖）"""
        return True

    async def close(self):
        pass


# ============================================================
# DashScopeProvider
# ============================================================


class DashScopeProvider(BaseEmbeddingProvider):
    """阿里云百炼 DashScope Embedding Provider"""

    def __init__(self, settings):
        super().__init__(name="dashscope", dimension=1024)
        self.settings = settings
        self._api_client: Optional[AsyncOpenAI] = None

        if settings.DASHSCOPE_API_KEY:
            try:
                from httpx import Timeout
                self._api_client = AsyncOpenAI(
                    api_key=settings.DASHSCOPE_API_KEY,
                    base_url=settings.DASHSCOPE_EMBEDDING_BASE_URL,
                    timeout=Timeout(30.0, connect=10.0),
                    max_retries=2,
                )
            except Exception as e:
                logger.warning(f"DashScope client init failed: {e}")

    def is_available(self) -> bool:
        return self._api_client is not None

    async def embed_query(self, text: str) -> np.ndarray:
        result = await self._embed_via_api([text])
        # task53: squeeze 2D (1, dim) → 1D (dim,)
        return result[0] if len(result) > 0 else np.zeros(self._dimension, dtype=np.float32)

    async def embed_documents(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.array([], dtype=np.float32).reshape(0, self._dimension)
        return await self._embed_via_api(texts)

    async def _embed_via_api(self, texts: List[str]) -> np.ndarray:
        if self._api_client is None:
            raise ModelNotLoadedException("DashScope client not initialized")

        try:
            response = await self._api_client.embeddings.create(
                model=self.settings.DASHSCOPE_EMBEDDING_MODEL,
                input=texts,
            )
            embeddings = [item.embedding for item in response.data]
            return np.array(embeddings, dtype=np.float32)
        except Exception as e:
            logger.error(f"DashScope API embedding call failed: {e}")
            raise


# ============================================================
# JinaProvider
# ============================================================


class JinaProvider(BaseEmbeddingProvider):
    """Jina AI Embedding Provider (jina-embeddings-v3, 1024维)"""

    JINA_API_URL = "https://api.jina.ai/v1/embeddings"
    JINA_MODEL = "jina-embeddings-v3"

    def __init__(self, settings):
        super().__init__(name="jina", dimension=1024)
        self.settings = settings
        self._api_key = settings.JINA_API_KEY if hasattr(settings, "JINA_API_KEY") else ""
        self._client: Optional[httpx.AsyncClient] = None
        if self._api_key:
            self._client = httpx.AsyncClient(timeout=30.0)

    def is_available(self) -> bool:
        return bool(self._api_key)

    async def embed_query(self, text: str) -> np.ndarray:
        result = await self._embed_via_api([text])
        # task53: squeeze 2D (1, dim) → 1D (dim,)
        return result[0] if len(result) > 0 else np.zeros(self._dimension, dtype=np.float32)

    async def embed_documents(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.array([], dtype=np.float32).reshape(0, self._dimension)
        return await self._embed_via_api(texts)

    async def _embed_via_api(self, texts: List[str]) -> np.ndarray:
        if not self._api_key:
            raise ModelNotLoadedException("Jina API key not configured")
        if self._client is None:
            raise ModelNotLoadedException("Jina client not initialized")
        try:
            response = await self._client.post(
                self.JINA_API_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.JINA_MODEL,
                    "input": texts,
                    "dimensions": self._dimension,
                },
            )
            response.raise_for_status()
            data = response.json()
            embeddings = [item["embedding"] for item in data["data"]]
            return np.array(embeddings, dtype=np.float32)
        except Exception as e:
            logger.error(f"Jina API embedding call failed: {e}")
            raise

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


# ============================================================
# OpenAIProvider
# ============================================================


class OpenAIProvider(BaseEmbeddingProvider):
    """OpenAI Embedding Provider (text-embedding-3-small, 1536维截断前1024 + L2归一化)"""

    OPENAI_API_URL = "https://api.openai.com/v1/embeddings"
    OPENAI_MODEL = "text-embedding-3-small"
    RAW_DIMENSION = 1536  # OpenAI 原始维度

    def __init__(self, settings):
        super().__init__(name="openai", dimension=1024)
        self.settings = settings
        self._api_key = settings.OPENAI_API_KEY if hasattr(settings, "OPENAI_API_KEY") else ""
        self._client: Optional[httpx.AsyncClient] = None
        if self._api_key:
            self._client = httpx.AsyncClient(timeout=30.0)

    def is_available(self) -> bool:
        return bool(self._api_key)

    async def embed_query(self, text: str) -> np.ndarray:
        result = await self._embed_via_api([text])
        # task53: squeeze 2D (1, dim) → 1D (dim,)
        return result[0] if len(result) > 0 else np.zeros(self._dimension, dtype=np.float32)

    async def embed_documents(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.array([], dtype=np.float32).reshape(0, self._dimension)
        return await self._embed_via_api(texts)

    async def _embed_via_api(self, texts: List[str]) -> np.ndarray:
        if not self._api_key:
            raise ModelNotLoadedException("OpenAI API key not configured")
        if self._client is None:
            raise ModelNotLoadedException("OpenAI client not initialized")
        try:
            response = await self._client.post(
                self.OPENAI_API_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.OPENAI_MODEL,
                    "input": texts,
                },
            )
            response.raise_for_status()
            data = response.json()
            embeddings = [item["embedding"] for item in data["data"]]
            result = np.array(embeddings, dtype=np.float32)

            # task53: 1536维截断前1024 + L2归一化
            if result.shape[-1] >= self._dimension:
                result = result[..., :self._dimension]
                # L2 归一化
                norms = np.linalg.norm(result, axis=-1, keepdims=True)
                norms[norms == 0] = 1.0
                result = result / norms

            return result
        except Exception as e:
            logger.error(f"OpenAI API embedding call failed: {e}")
            raise

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


# ============================================================
# LocalSentenceTransformerProvider (本地模型)
# ============================================================


class LocalSentenceTransformerProvider(BaseEmbeddingProvider):
    """本地 SentenceTransformer Embedding Provider (bge-m3 等)"""

    def __init__(self, settings):
        super().__init__(name="local", dimension=1024)
        self.settings = settings
        self._model = None
        self._loaded = False
        self._should_load = getattr(settings, "EMBEDDING_PROVIDER", "") == "local"
        if self._should_load:
            self._try_load_model()

    def _try_load_model(self):
        if self._loaded:
            return
        try:
            from sentence_transformers import SentenceTransformer
            model_path = self.settings.EMBEDDING_MODEL_PATH or "BAAI/bge-m3"
            device = self.settings.EMBEDDING_DEVICE or "cpu"
            self._model = SentenceTransformer(model_path, device=device)
            self._loaded = True
        except Exception as e:
            logger.warning(f"Local SentenceTransformer init failed: {e}")

    def is_available(self) -> bool:
        if not self._should_load:
            return False
        if not self._loaded:
            self._try_load_model()
        return self._model is not None

    async def embed_query(self, text: str) -> np.ndarray:
        import asyncio
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._model.encode(text, normalize_embeddings=True),
        )
        return np.array(result, dtype=np.float32)

    async def embed_documents(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.array([], dtype=np.float32).reshape(0, self._dimension)
        import asyncio
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._model.encode(texts, normalize_embeddings=True),
        )
        return np.array(result, dtype=np.float32)


# ============================================================
# EmbeddingService（重构后）
# ============================================================


class EmbeddingService:
    """Embedding 服务 — task53 重构为多 Provider 架构

    根据 settings.EMBEDDING_PROVIDER 选择 active_provider，
    其余 Provider 加入 fallback_providers 降级链。
    保留 encode/encode_batch 方法名（向后兼容）。
    """

    EXPECTED_DIMENSION = 1024

    # Provider 注册表
    PROVIDER_CLASSES = {
        "dashscope": DashScopeProvider,
        "jina": JinaProvider,
        "openai": OpenAIProvider,
        "local": LocalSentenceTransformerProvider,
    }

    def __init__(self, settings):
        self.settings = settings
        self.model = None  # 保留本地模型字段（向后兼容）
        self._dimension: Optional[int] = None
        self.status = "initializing"

        # task53: 多 Provider 架构
        self.active_provider: Optional[BaseEmbeddingProvider] = None
        self.fallback_providers: List[BaseEmbeddingProvider] = []
        self._provider_name: str = ""

        # 保留旧字段（向后兼容）
        self._api_client = None

    @property
    def dimension(self) -> Optional[int]:
        return self._dimension

    async def load_model(self) -> None:
        """初始化 Provider（根据 settings.EMBEDDING_PROVIDER 选择）"""
        provider_name = getattr(self.settings, "EMBEDDING_PROVIDER", "dashscope")
        expected_dim = getattr(self.settings, "EMBEDDING_DIMENSION", 1024)

        # 构建所有 Provider
        all_providers = {}
        for name, cls in self.PROVIDER_CLASSES.items():
            try:
                provider = cls(self.settings)
                if provider.is_available():
                    all_providers[name] = provider
            except Exception as e:
                logger.warning(f"Provider {name} init failed: {e}")

        if not all_providers:
            self.status = "disabled"
            logger.warning(
                "No embedding provider available. EmbeddingService will be unavailable."
            )
            return

        # 选择 active_provider
        if provider_name in all_providers:
            self.active_provider = all_providers[provider_name]
        else:
            # 配置的 Provider 不可用，取第一个可用的
            self.active_provider = list(all_providers.values())[0]
            logger.warning(
                f"Configured provider '{provider_name}' not available, "
                f"using '{self.active_provider.name}' instead"
            )

        self._provider_name = self.active_provider.name
        self._dimension = self.active_provider.dimension

        # 维度校验
        if self._dimension != expected_dim:
            raise ModelNotLoadedException(
                f"Provider {self._provider_name} dimension={self._dimension} "
                f"!= expected {expected_dim}"
            )

        # 其余 Provider 作为降级
        self.fallback_providers = [
            p for name, p in all_providers.items() if name != self._provider_name
        ]

        self.status = "loaded_local" if self._provider_name == "local" else "loaded_api"
        masked_key = ""
        if self._provider_name == "dashscope" and self.settings.DASHSCOPE_API_KEY:
            masked_key = self.settings.DASHSCOPE_API_KEY[:4] + "****"
        elif self._provider_name == "jina" and hasattr(self.settings, "JINA_API_KEY"):
            masked_key = (self.settings.JINA_API_KEY or "")[:4] + "****"
        elif self._provider_name == "openai" and hasattr(self.settings, "OPENAI_API_KEY"):
            masked_key = (self.settings.OPENAI_API_KEY or "")[:4] + "****"
        elif self._provider_name == "local":
            masked_key = self.settings.EMBEDDING_MODEL_PATH or "BAAI/bge-m3"

        logger.info(
            f"EmbeddingService initialized with provider={self._provider_name}, "
            f"dimension={self._dimension}, fallbacks={[p.name for p in self.fallback_providers]}, "
            f"key={masked_key}"
        )

    def _load_local_model(self):
        """保留本地模型加载（向后兼容）"""
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(
            self.settings.EMBEDDING_MODEL_PATH or "BAAI/bge-m3",
            device=self.settings.EMBEDDING_DEVICE or "cpu",
        )

    def _init_dashscope_client(self) -> None:
        """保留旧方法（向后兼容）"""
        from httpx import Timeout
        self._api_client = AsyncOpenAI(
            api_key=self.settings.DASHSCOPE_API_KEY,
            base_url=self.settings.DASHSCOPE_EMBEDDING_BASE_URL,
            timeout=Timeout(30.0, connect=10.0),
            max_retries=2,
        )

    async def encode(self, text: Union[str, list]) -> np.ndarray:
        """单文本或批量文本向量化（向后兼容方法名）"""
        # P1-18: 单文本缓存
        if isinstance(text, str):
            from app.core.cache import get_embedding_cache, _make_cache_key
            cache_key = _make_cache_key("embed", text)
            cached = await get_embedding_cache().get(cache_key)
            if cached is not None:
                logger.debug("Embedding cache hit")
                return cached

        # 本地模型路径（保留）
        if self.model is not None:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.model.encode(text, normalize_embeddings=True),
            )
            return np.array(result, dtype=np.float32)

        # task53: 多 Provider 路径
        if self.active_provider is None:
            raise ModelNotLoadedException("Embedding service not initialized")

        is_single = isinstance(text, str)
        texts = [text] if is_single else text

        try:
            result = await self.active_provider.embed_documents(texts)
            if is_single:
                result = result[0] if len(result) > 0 else np.zeros(self._dimension, dtype=np.float32)
            # P1-18: 缓存单文本 embedding
            if is_single:
                from app.core.cache import get_embedding_cache, _make_cache_key
                cache_key = _make_cache_key("embed", text)
                await get_embedding_cache().set(cache_key, result)
            return result
        except Exception as e:
            logger.warning(f"Active provider {self._provider_name} failed: {e}, trying fallbacks")
            # P2#7: 保留 last_error，最终异常消息使用最后一个 fallback 的错误
            last_error = e
            # 降级尝试
            for fb in self.fallback_providers:
                try:
                    result = await fb.embed_documents(texts)
                    if is_single:
                        result = result[0] if len(result) > 0 else np.zeros(self._dimension, dtype=np.float32)
                    # P1-18: 缓存单文本 embedding
                    if is_single:
                        from app.core.cache import get_embedding_cache, _make_cache_key
                        cache_key = _make_cache_key("embed", text)
                        await get_embedding_cache().set(cache_key, result)
                    logger.info(f"Fallback to provider {fb.name} succeeded")
                    return result
                except Exception as fb_err:
                    last_error = fb_err
                    logger.warning(f"Fallback provider {fb.name} also failed: {fb_err}")
                    continue

            raise ModelNotLoadedException(f"All embedding providers failed, last error: {last_error}")

    async def encode_batch(self, texts: list, batch_size: int = 32) -> np.ndarray:
        """批量文本向量化（向后兼容方法名）"""
        if not texts:
            dim = self._dimension or 1024
            return np.array([], dtype=np.float32).reshape(0, dim)

        if len(texts) <= batch_size:
            return await self.encode(texts)

        all_embeddings = []
        total = len(texts)
        for i in range(0, total, batch_size):
            batch = texts[i : i + batch_size]
            embeddings = await self.encode(batch)
            all_embeddings.append(embeddings)
            progress = min(i + batch_size, total) / total * 100
            logger.debug(
                f"encode_batch progress: batch {i // batch_size + 1}, "
                f"{min(i + batch_size, total)}/{total} ({progress:.1f}%)"
            )

        return np.vstack(all_embeddings)

    async def _encode_via_api(self, text: Union[str, list]) -> np.ndarray:
        """保留旧方法（向后兼容）"""
        return await self.encode(text)

    def get_model_status(self) -> dict:
        """返回模型状态信息（task53 新增）"""
        return {
            "status": self.status,
            "provider": self._provider_name,
            "dimension": self._dimension,
            "fallbacks": [p.name for p in self.fallback_providers],
        }

    async def unload_model(self) -> None:
        """关闭所有 Provider 的持久化 HTTP 客户端（P1-19）"""
        all_providers = []
        if self.active_provider is not None:
            all_providers.append(self.active_provider)
        all_providers.extend(self.fallback_providers)
        for provider in all_providers:
            try:
                await provider.close()
            except Exception as e:
                logger.warning(f"Failed to close provider {provider.name}: {e}")
        self.active_provider = None
        self.fallback_providers = []
        self.status = "unloaded"
