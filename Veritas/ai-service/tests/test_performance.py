import os
import time

import numpy as np
import pytest

from app.core.config import Settings
from app.services.embedding_service import EmbeddingService

pytestmark = pytest.mark.asyncio

HAS_DASHSCOPE_KEY = bool(os.environ.get("DASHSCOPE_API_KEY", ""))


class TestEmbeddingPerformanceLocal:

    async def test_encode_single_dimension(self, embedding_service):
        result = await embedding_service.encode("测试文本")
        assert isinstance(result, np.ndarray)
        assert result.shape[0] == embedding_service.dimension
        assert result.dtype == np.float32

    async def test_encode_batch_100_texts_under_10s(self, embedding_service):
        texts = [f"这是第{i}条测试文本，用于验证批量编码性能" for i in range(100)]
        start = time.time()
        result = await embedding_service.encode_batch(texts, batch_size=32)
        elapsed = time.time() - start
        assert isinstance(result, np.ndarray)
        assert result.shape == (100, embedding_service.dimension)
        assert elapsed < 10, f"100 texts encoding took {elapsed:.2f}s, expected < 10s"

    async def test_encode_batch_10_texts_performance(self, embedding_service):
        texts = [f"性能测试文本{i}" for i in range(10)]
        start = time.time()
        result = await embedding_service.encode_batch(texts, batch_size=10)
        elapsed = time.time() - start
        assert result.shape == (10, embedding_service.dimension)
        assert elapsed < 5, f"10 texts encoding took {elapsed:.2f}s, expected < 5s"


@pytest.mark.skipif(not HAS_DASHSCOPE_KEY, reason="DASHSCOPE_API_KEY not set")
class TestEmbeddingPerformanceAPI:

    async def test_api_encode_batch_100_texts_under_30s(self):
        settings = Settings(
            DASHSCOPE_API_KEY=os.environ["DASHSCOPE_API_KEY"],
            DASHSCOPE_EMBEDDING_MODEL="text-embedding-v4",
            DASHSCOPE_EMBEDDING_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        svc = EmbeddingService(settings)
        await svc.load_model()
        texts = [f"API性能测试文本{i}" for i in range(100)]
        start = time.time()
        result = await svc.encode_batch(texts, batch_size=20)
        elapsed = time.time() - start
        assert result.shape == (100, svc.dimension)
        assert elapsed < 30, f"API 100 texts took {elapsed:.2f}s, expected < 30s"
