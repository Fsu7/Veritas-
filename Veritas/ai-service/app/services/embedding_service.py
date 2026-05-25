import asyncio
from typing import Union

import numpy as np
from loguru import logger
from openai import AsyncOpenAI
from sentence_transformers import SentenceTransformer

from app.exception import ModelNotLoadedException


class EmbeddingService:

    EXPECTED_DIMENSION = 1024

    def __init__(self, settings):
        self.settings = settings
        self.model = None
        self._dimension: int | None = None
        self.status = "initializing"
        self._api_client = None

    @property
    def dimension(self) -> int | None:
        return self._dimension

    async def load_model(self) -> None:
        if self.settings.DASHSCOPE_API_KEY:
            try:
                self._init_dashscope_client()
                test_resp = await self._api_client.embeddings.create(
                    model=self.settings.DASHSCOPE_EMBEDDING_MODEL,
                    input=["test"],
                )
                dim = len(test_resp.data[0].embedding)
                self._dimension = dim
                self.status = "loaded_api"
                masked_key = self.settings.DASHSCOPE_API_KEY[:4] + "****"
                logger.info(
                    f"Embedding model loaded via DashScope API, "
                    f"model={self.settings.DASHSCOPE_EMBEDDING_MODEL}, "
                    f"dimension={dim}, key={masked_key}"
                )
                return
            except Exception as e:
                masked_key = self.settings.DASHSCOPE_API_KEY[:4] + "****"
                logger.warning(
                    f"DashScope API connection failed (key={masked_key}): {e}, "
                    f"falling back to local model"
                )
                self._api_client = None

        try:
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None,
                self._load_local_model,
            )
            if hasattr(self.model, 'get_embedding_dimension'):
                self._dimension = self.model.get_embedding_dimension()
            else:
                self._dimension = self.model.get_sentence_embedding_dimension()

            expected = getattr(self.settings, 'EMBEDDING_EXPECTED_DIMENSION', self.EXPECTED_DIMENSION)
            if self._dimension != expected:
                logger.warning(
                    f"Local model dimension={self._dimension} != expected={expected}, "
                    f"vector operations may fail with existing ChromaDB data"
                )

            self.status = "loaded_local"
            logger.info(
                f"Embedding model loaded via local "
                f"{self.settings.EMBEDDING_MODEL_PATH or 'BAAI/bge-m3'}, "
                f"dimension={self.dimension}, device={self.settings.EMBEDDING_DEVICE}"
            )
        except Exception as e:
            logger.error(f"Failed to load local embedding model: {e}")
            self.status = "error"
            raise RuntimeError("No embedding service available") from e

    def _load_local_model(self) -> SentenceTransformer:
        return SentenceTransformer(
            self.settings.EMBEDDING_MODEL_PATH or "BAAI/bge-m3",
            device=self.settings.EMBEDDING_DEVICE or "cpu",
        )

    def _init_dashscope_client(self) -> None:
        self._api_client = AsyncOpenAI(
            api_key=self.settings.DASHSCOPE_API_KEY,
            base_url=self.settings.DASHSCOPE_EMBEDDING_BASE_URL,
        )

    async def encode(self, text: Union[str, list]) -> np.ndarray:
        if self.model is not None:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.model.encode(text, normalize_embeddings=True),
            )
            return np.array(result, dtype=np.float32)

        if self._api_client is not None:
            return await self._encode_via_api(text)

        raise ModelNotLoadedException("Embedding model not loaded, call load_model() first")

    async def encode_batch(self, texts: list, batch_size: int = 32) -> np.ndarray:
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
        is_single = isinstance(text, str)
        if is_single:
            text = [text]

        try:
            response = await self._api_client.embeddings.create(
                model=self.settings.DASHSCOPE_EMBEDDING_MODEL,
                input=text,
            )
            embeddings = [item.embedding for item in response.data]
            result = np.array(embeddings, dtype=np.float32)
            if is_single:
                result = result[0]
            return result
        except Exception as e:
            logger.error(f"DashScope API embedding call failed: {e}")
            raise
