import os

import numpy as np
import pytest

from app.core.config import Settings
from app.exception import ModelNotLoadedException
from app.services.embedding_service import EmbeddingService

pytestmark = pytest.mark.asyncio

HAS_DASHSCOPE_KEY = bool(os.environ.get("DASHSCOPE_API_KEY", ""))


class TestEmbeddingServiceInit:

    async def test_initial_state(self):
        settings = Settings(DASHSCOPE_API_KEY="", EMBEDDING_MODEL_PATH="BAAI/bge-large-zh-v1.5")
        svc = EmbeddingService(settings)
        assert svc.dimension == 1024
        assert svc.status == "initializing"
        assert svc.model is None
        assert svc._api_client is None

    async def test_load_local_model(self, embedding_service):
        assert embedding_service.status == "loaded_local"
        assert embedding_service.model is not None
        assert embedding_service.dimension > 0


class TestEmbeddingServiceLocal:

    async def test_encode_single(self, embedding_service):
        result = await embedding_service.encode("测试文本")
        assert isinstance(result, np.ndarray)
        assert result.shape == (embedding_service.dimension,)
        assert result.dtype == np.float32

    async def test_encode_list(self, embedding_service):
        result = await embedding_service.encode(["文本A", "文本B", "文本C"])
        assert isinstance(result, np.ndarray)
        assert result.shape == (3, embedding_service.dimension)
        assert result.dtype == np.float32

    async def test_encode_batch(self, embedding_service):
        texts = [f"测试文本{i}" for i in range(10)]
        result = await embedding_service.encode_batch(texts, batch_size=3)
        assert isinstance(result, np.ndarray)
        assert result.shape == (10, embedding_service.dimension)
        assert result.dtype == np.float32

    async def test_vector_dimension(self, embedding_service):
        result = await embedding_service.encode("维度测试")
        assert result.shape[0] == embedding_service.dimension

    async def test_vector_normalized(self, embedding_service):
        result = await embedding_service.encode("归一化测试")
        norm = np.linalg.norm(result)
        assert abs(norm - 1.0) < 0.01


@pytest.mark.skipif(not HAS_DASHSCOPE_KEY, reason="DASHSCOPE_API_KEY not set")
class TestEmbeddingServiceAPI:

    async def test_api_connection(self):
        settings = Settings(
            DASHSCOPE_API_KEY=os.environ["DASHSCOPE_API_KEY"],
            DASHSCOPE_EMBEDDING_MODEL="text-embedding-v4",
            DASHSCOPE_EMBEDDING_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        svc = EmbeddingService(settings)
        await svc.load_model()
        assert svc.status == "loaded_api"

    async def test_api_encode_single(self):
        settings = Settings(
            DASHSCOPE_API_KEY=os.environ["DASHSCOPE_API_KEY"],
            DASHSCOPE_EMBEDDING_MODEL="text-embedding-v4",
            DASHSCOPE_EMBEDDING_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        svc = EmbeddingService(settings)
        await svc.load_model()
        result = await svc.encode("你好世界")
        assert isinstance(result, np.ndarray)
        assert result.shape == (svc.dimension,)

    async def test_api_encode_batch_performance(self):
        import time

        settings = Settings(
            DASHSCOPE_API_KEY=os.environ["DASHSCOPE_API_KEY"],
            DASHSCOPE_EMBEDDING_MODEL="text-embedding-v4",
            DASHSCOPE_EMBEDDING_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        svc = EmbeddingService(settings)
        await svc.load_model()
        texts = [f"测试文本{i}" for i in range(20)]
        start = time.time()
        result = await svc.encode_batch(texts, batch_size=10)
        elapsed = time.time() - start
        assert result.shape == (20, svc.dimension)
        assert elapsed < 30


class TestEmbeddingServiceError:

    async def test_encode_without_load(self):
        settings = Settings(DASHSCOPE_API_KEY="", EMBEDDING_MODEL_PATH="BAAI/bge-large-zh-v1.5")
        svc = EmbeddingService(settings)
        with pytest.raises(ModelNotLoadedException) as exc_info:
            await svc.encode("测试")
        assert exc_info.value.code == 503

    async def test_load_local_model_invalid_path(self):
        settings = Settings(
            DASHSCOPE_API_KEY="",
            EMBEDDING_MODEL_PATH="/nonexistent/model/path",
        )
        svc = EmbeddingService(settings)
        with pytest.raises(RuntimeError):
            await svc.load_model()
        assert svc.status == "error"
