"""task26 测试套件 — 健康检查完善 + 模型状态API

覆盖：
- /health critical_ok 规则（200 vs 503）
- /health 6 组件状态
- /api/model/status 统一响应格式
- /api/model/status 扩展字段（providerCandidates/chromaPaperCount/gpuMemoryUsed/llmProviderCount）
- GPU 显存查询异常返回 None
- ChromaDB 论文数量安全查询
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


class TestHealthCriticalOk:
    """测试 /health critical_ok 规则"""

    def setup_method(self):
        self.client = TestClient(app)

    @patch("app.main.app_state")
    def test_health_all_critical_ok_returns_200(self, mock_state):
        """核心组件全 OK 时返回 200 + UP"""
        mock_llm = MagicMock()
        mock_llm.status = "loaded"
        mock_embedding = MagicMock()
        mock_embedding.status = "loaded_api"
        mock_chroma = MagicMock()
        mock_chroma.status = "connected"
        mock_prompts = MagicMock()
        mock_prompts.status = "loaded"
        mock_search = MagicMock()
        mock_reranker = MagicMock()

        mock_state.llm_service = mock_llm
        mock_state.embedding_service = mock_embedding
        mock_state.vector_store_service = mock_chroma
        mock_state.prompt_manager = mock_prompts
        mock_state.search_service = mock_search
        mock_state.reranker = mock_reranker

        response = self.client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["status"] == "UP"

    @patch("app.main.app_state")
    def test_health_llm_not_loaded_returns_503(self, mock_state):
        """LLM 未加载返回 503 + DEGRADED"""
        mock_state.llm_service = None
        mock_state.embedding_service = MagicMock(status="loaded_api")
        mock_state.vector_store_service = MagicMock(status="connected")
        mock_state.prompt_manager = MagicMock(status="loaded")
        mock_state.search_service = MagicMock()
        mock_state.reranker = MagicMock()

        response = self.client.get("/health")
        assert response.status_code == 503
        body = response.json()
        assert body["data"]["status"] == "DEGRADED"

    @patch("app.main.app_state")
    def test_health_embedding_not_loaded_returns_503(self, mock_state):
        """Embedding 未加载返回 503"""
        mock_state.llm_service = MagicMock(status="loaded")
        mock_state.embedding_service = None
        mock_state.vector_store_service = MagicMock(status="connected")
        mock_state.prompt_manager = MagicMock(status="loaded")
        mock_state.search_service = MagicMock()
        mock_state.reranker = MagicMock()

        response = self.client.get("/health")
        assert response.status_code == 503

    @patch("app.main.app_state")
    def test_health_chroma_not_connected_returns_503(self, mock_state):
        """ChromaDB 未连接返回 503"""
        mock_state.llm_service = MagicMock(status="loaded")
        mock_state.embedding_service = MagicMock(status="loaded_api")
        mock_state.vector_store_service = None
        mock_state.prompt_manager = MagicMock(status="loaded")
        mock_state.search_service = MagicMock()
        mock_state.reranker = MagicMock()

        response = self.client.get("/health")
        assert response.status_code == 503

    @patch("app.main.app_state")
    def test_health_has_6_components(self, mock_state):
        """响应含 6 个组件状态"""
        mock_state.llm_service = MagicMock(status="loaded")
        mock_state.embedding_service = MagicMock(status="loaded_api")
        mock_state.vector_store_service = MagicMock(status="connected")
        mock_state.prompt_manager = MagicMock(status="loaded")
        mock_state.search_service = MagicMock()
        mock_state.reranker = MagicMock()

        response = self.client.get("/health")
        body = response.json()
        data = body["data"]
        assert "llm" in data
        assert "embedding" in data
        assert "chroma" in data
        assert "prompts" in data
        assert "searchService" in data
        assert "reranker" in data

    @patch("app.main.app_state")
    def test_health_response_has_unified_format(self, mock_state):
        """健康检查返回统一格式 {code, message, data, timestamp}"""
        mock_state.llm_service = MagicMock(status="loaded")
        mock_state.embedding_service = MagicMock(status="loaded_api")
        mock_state.vector_store_service = MagicMock(status="connected")
        mock_state.prompt_manager = MagicMock(status="loaded")
        mock_state.search_service = MagicMock()
        mock_state.reranker = MagicMock()

        response = self.client.get("/health")
        body = response.json()
        assert set(body.keys()) == {"code", "message", "data", "timestamp"}
        assert isinstance(body["timestamp"], int)


class TestModelStatus:
    """测试 /api/model/status 端点"""

    def setup_method(self):
        self.client = TestClient(app)

    def test_model_status_llm_not_loaded_503(self):
        """LLM 未就绪返回 503"""
        response = self.client.get("/api/model/status")
        # 未启动时 llm_service=None → fail(503)
        body = response.json()
        assert body["code"] == 503
        assert set(body.keys()) == {"code", "message", "data", "timestamp"}

    @patch("app.api.endpoints.model.events.app_state")
    def test_model_status_returns_unified_format(self, mock_state):
        """返回统一格式 {code, message, data, timestamp}"""
        mock_llm = MagicMock()
        mock_llm.status = "loaded"
        mock_llm.providers = {"api": MagicMock()}
        mock_llm.active_provider = MagicMock()
        mock_llm.active_provider.mode = "api"

        mock_embedding = MagicMock()
        mock_embedding.status = "loaded_api"
        mock_embedding.dimension = 768

        mock_chroma = MagicMock()
        mock_chroma.status = "connected"

        mock_prompts = MagicMock()
        mock_prompts.status = "loaded"

        mock_state.llm_service = mock_llm
        mock_state.embedding_service = mock_embedding
        mock_state.vector_store_service = mock_chroma
        mock_state.prompt_manager = mock_prompts
        mock_state.search_service = MagicMock()
        mock_state.reranker = MagicMock()

        response = self.client.get("/api/model/status")
        body = response.json()
        assert body["code"] == 200
        assert set(body.keys()) == {"code", "message", "data", "timestamp"}
        assert body["data"] is not None

    @patch("app.api.endpoints.model.events.app_state")
    def test_model_status_has_extended_fields(self, mock_state):
        """ModelStatusResponse 含 task26 扩展字段"""
        mock_llm = MagicMock()
        mock_llm.status = "loaded"
        mock_llm.providers = {"api": MagicMock(), "builtin": MagicMock()}
        mock_llm.active_provider = MagicMock()
        mock_llm.active_provider.mode = "api"

        mock_embedding = MagicMock()
        mock_embedding.status = "loaded_api"
        mock_embedding.dimension = 768

        mock_chroma = MagicMock()
        mock_chroma.status = "connected"
        mock_chroma.collection = MagicMock()
        mock_chroma.collection.count.return_value = 200

        mock_prompts = MagicMock()
        mock_prompts.status = "loaded"

        mock_state.llm_service = mock_llm
        mock_state.embedding_service = mock_embedding
        mock_state.vector_store_service = mock_chroma
        mock_state.prompt_manager = mock_prompts
        mock_state.search_service = MagicMock()
        mock_state.reranker = MagicMock()

        response = self.client.get("/api/model/status")
        body = response.json()
        data = body["data"]
        # 扩展字段
        assert "providerCandidates" in data
        assert "chromaPaperCount" in data
        assert "gpuMemoryUsed" in data
        assert "llmProviderCount" in data
        assert data["llmProviderCount"] == 2
        assert "api" in data["providerCandidates"]

    @patch("app.api.endpoints.model.events.app_state")
    def test_model_status_gpu_memory_none_when_no_local(self, mock_state):
        """非 local 模式 GPU 为 None"""
        mock_llm = MagicMock()
        mock_llm.status = "loaded"
        mock_llm.providers = {"api": MagicMock()}
        mock_llm.active_provider = MagicMock()
        mock_llm.active_provider.mode = "api"  # 非 local

        mock_embedding = MagicMock()
        mock_embedding.status = "loaded_api"
        mock_embedding.dimension = 768

        mock_chroma = MagicMock()
        mock_chroma.status = "connected"

        mock_prompts = MagicMock()
        mock_prompts.status = "loaded"

        mock_state.llm_service = mock_llm
        mock_state.embedding_service = mock_embedding
        mock_state.vector_store_service = mock_chroma
        mock_state.prompt_manager = mock_prompts
        mock_state.search_service = MagicMock()
        mock_state.reranker = MagicMock()

        response = self.client.get("/api/model/status")
        body = response.json()
        assert body["data"]["gpuMemoryUsed"] is None

    @patch("app.api.endpoints.model.events.app_state")
    def test_model_status_chroma_paper_count_safe(self, mock_state):
        """chromaPaperCount 安全查询，异常时返回 None"""
        mock_llm = MagicMock()
        mock_llm.status = "loaded"
        mock_llm.providers = {"api": MagicMock()}
        mock_llm.active_provider = MagicMock()
        mock_llm.active_provider.mode = "api"

        mock_embedding = MagicMock()
        mock_embedding.status = "loaded_api"
        mock_embedding.dimension = 768

        mock_chroma = MagicMock()
        mock_chroma.status = "connected"
        mock_chroma.collection = None  # collection 为 None

        mock_prompts = MagicMock()
        mock_prompts.status = "loaded"

        mock_state.llm_service = mock_llm
        mock_state.embedding_service = mock_embedding
        mock_state.vector_store_service = mock_chroma
        mock_state.prompt_manager = mock_prompts
        mock_state.search_service = MagicMock()
        mock_state.reranker = MagicMock()

        response = self.client.get("/api/model/status")
        body = response.json()
        assert body["data"]["chromaPaperCount"] is None

    @patch("app.api.endpoints.model.events.app_state")
    def test_model_status_has_search_service_and_reranker(self, mock_state):
        """model status 含 searchService 和 reranker 状态"""
        mock_llm = MagicMock()
        mock_llm.status = "loaded"
        mock_llm.providers = {"api": MagicMock()}
        mock_llm.active_provider = MagicMock()
        mock_llm.active_provider.mode = "api"

        mock_embedding = MagicMock()
        mock_embedding.status = "loaded_api"
        mock_embedding.dimension = 768

        mock_chroma = MagicMock()
        mock_chroma.status = "connected"

        mock_prompts = MagicMock()
        mock_prompts.status = "loaded"

        mock_state.llm_service = mock_llm
        mock_state.embedding_service = mock_embedding
        mock_state.vector_store_service = mock_chroma
        mock_state.prompt_manager = mock_prompts
        mock_state.search_service = MagicMock()
        mock_state.reranker = MagicMock()

        response = self.client.get("/api/model/status")
        body = response.json()
        assert body["data"]["searchService"] == "ready"
        assert body["data"]["reranker"] == "ready"
