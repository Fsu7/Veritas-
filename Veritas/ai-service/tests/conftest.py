import os

import pytest
import pytest_asyncio

from app.core.config import Settings


@pytest_asyncio.fixture(scope="function")
async def embedding_service():
    from app.services.embedding_service import EmbeddingService

    test_settings = Settings(
        DASHSCOPE_API_KEY="",
        EMBEDDING_MODEL_PATH="BAAI/bge-large-zh-v1.5",
        EMBEDDING_DEVICE="cpu",
    )
    svc = EmbeddingService(test_settings)
    await svc.load_model()
    yield svc


@pytest_asyncio.fixture(scope="function")
async def vector_store_service(tmp_path):
    from app.services.vector_store_service import VectorStoreService

    chroma_dir = str(tmp_path / "chroma_test")
    test_settings = Settings(
        CHROMA_PATH=chroma_dir,
    )
    svc = VectorStoreService(test_settings)
    await svc.initialize()
    yield svc
    await svc.close()
