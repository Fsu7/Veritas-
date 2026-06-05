"""Task27 集成测试 conftest — mock LLM/Chroma/Embedding fixture

为 Java→Python 联调测试提供统一的 mock 服务，避免真实 LLM 调用。
使用 unittest.mock.MagicMock + AsyncMock。
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app


# ===== mock 服务 fixture =====


@pytest.fixture()
def mock_llm_service():
    """返回固定文本的 LLM 服务 mock

    - status = "loaded"
    - providers = {"api": <MagicMock>}
    - active_provider.mode = "api"
    - generate() 返回固定文本
    """
    llm = MagicMock()
    llm.status = "loaded"

    api_provider = MagicMock()
    llm.providers = {"api": api_provider}

    active_provider = MagicMock()
    active_provider.mode = "api"
    llm.active_provider = active_provider

    llm.generate = AsyncMock(return_value="这是一段由 mock LLM 生成的固定文本。")
    llm.unload_model = AsyncMock()

    return llm


@pytest.fixture()
def mock_chroma():
    """返回固定论文数据的 ChromaDB mock

    - status = "connected"
    - collection.count() = 200
    """
    chroma = MagicMock()
    chroma.status = "connected"

    collection = MagicMock()
    collection.count.return_value = 200
    chroma.collection = collection

    chroma.close = AsyncMock()

    return chroma


@pytest.fixture()
def mock_embedding():
    """返回固定向量的 Embedding 服务 mock

    - status = "loaded_api"
    - dimension = 1024
    - embed() 返回固定 1024 维向量
    """
    embedding = MagicMock()
    embedding.status = "loaded_api"
    embedding.dimension = 1024

    import numpy as np

    fixed_vector = np.zeros(1024, dtype=np.float32).tolist()
    embedding.embed = AsyncMock(return_value=fixed_vector)
    embedding.load_model = AsyncMock()

    return embedding


@pytest.fixture()
def mock_prompt_manager():
    """Prompt 管理器 mock"""
    pm = MagicMock()
    pm.status = "loaded"
    pm.load_templates = AsyncMock()
    return pm


@pytest.fixture()
def mock_search_service():
    """搜索服务 mock — search() 返回固定论文结果"""
    svc = MagicMock()
    svc.search = AsyncMock(return_value=[
        {
            "paper_id": "arxiv_2024_001",
            "title": "Attention Is All You Need",
            "abstract": "We propose a new network architecture...",
            "score": 0.95,
            "year": 2017,
            "venue": "NeurIPS",
        },
        {
            "paper_id": "arxiv_2024_002",
            "title": "BERT: Pre-training of Deep Bidirectional Transformers",
            "abstract": "We introduce a new language representation model...",
            "score": 0.88,
            "year": 2019,
            "venue": "NAACL",
        },
    ])
    svc.suggest = AsyncMock(return_value=["Multi-Agent", "Transformer"])
    return svc


@pytest.fixture()
def mock_reranker():
    """Reranker mock"""
    reranker = MagicMock()
    reranker.rerank = AsyncMock(return_value=[
        {
            "paper_id": "arxiv_2024_001",
            "title": "Attention Is All You Need",
            "abstract": "We propose a new network architecture...",
            "rerank_score": 0.97,
            "year": 2017,
            "venue": "NeurIPS",
        },
    ])
    return reranker


@pytest.fixture()
def mock_app_state(
    mock_llm_service,
    mock_chroma,
    mock_embedding,
    mock_prompt_manager,
    mock_search_service,
    mock_reranker,
):
    """聚合所有 mock 服务的 app_state 字典

    用法：在 patch("app.xxx.events.app_state") 后赋值各属性。
    """
    return {
        "llm_service": mock_llm_service,
        "embedding_service": mock_embedding,
        "vector_store_service": mock_chroma,
        "prompt_manager": mock_prompt_manager,
        "search_service": mock_search_service,
        "reranker": mock_reranker,
    }


@pytest.fixture()
def client():
    """FastAPI TestClient（不含 lifespan，避免真实服务初始化）"""
    return TestClient(app)
