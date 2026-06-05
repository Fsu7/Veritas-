"""Task27 Python 侧联调测试 — Java→Python 5 种典型请求验证

覆盖 Java 后端调用 Python AI 服务的 camelCase 字段往返一致性：
1. analyze 请求 camelCase 解析
2. analyze 响应 camelCase 输出
3. search 请求/响应 camelCase 往返
4. /health 统一响应格式
5. /model/status camelCase 字段

使用 fastapi.testclient.TestClient + unittest.mock.patch
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


# ===== 辅助函数 =====


def _apply_mock_app_state(mock_state, mock_app_state):
    """将 mock_app_state 字典赋值到 mock_state 各属性"""
    mock_state.llm_service = mock_app_state["llm_service"]
    mock_state.embedding_service = mock_app_state["embedding_service"]
    mock_state.vector_store_service = mock_app_state["vector_store_service"]
    mock_state.prompt_manager = mock_app_state["prompt_manager"]
    mock_state.search_service = mock_app_state["search_service"]
    mock_state.reranker = mock_app_state["reranker"]


# ===== 测试用例 =====


class TestAnalyzeCamelCaseRequest:
    """1. Java 风格 camelCase 请求正确解析"""

    @patch("app.api.endpoints.agent.events.app_state")
    @patch("app.api.endpoints.agent.run_workflow", new_callable=AsyncMock)
    def test_analyze_camelcase_request(self, mock_run_workflow, mock_state, mock_app_state):
        """Java 端发送 camelCase 字段（paperIds/userProfile/analysisType/analysisId），
        Python 端能正确解析并传递到 workflow"""
        _apply_mock_app_state(mock_state, mock_app_state)

        # mock workflow 返回固定结果
        mock_run_workflow.return_value = {
            "analysis_id": "anl_20240523_001",
            "status": "completed",
            "report": "## 文献综述\n这是一份 mock 报告。",
            "citations": [{"index": 1, "paper_id": "arxiv_2024_001", "citation": "[Author, 2024]"}],
            "agent_states": {
                "retriever": {"name": "retriever", "status": "completed", "progress": 1.0, "duration_ms": 1200},
                "analyzer": {"name": "analyzer", "status": "completed", "progress": 1.0, "duration_ms": 8000},
                "generator": {"name": "generator", "status": "completed", "progress": 1.0, "duration_ms": 15000},
            },
            "degraded": False,
            "degraded_reason": None,
        }

        client = TestClient(app)

        # Java 风格 camelCase 请求体
        java_request = {
            "topic": "Multi-Agent协同决策",
            "paperIds": ["arxiv_2024_001", "arxiv_2024_002"],
            "userId": "usr_001",
            "userProfile": {
                "educationLevel": "master",
                "researchField": "NLP",
                "knowledgeLevel": "intermediate",
                "preferredStyle": "balanced",
            },
            "analysisType": "report",
            "analysisId": "anl_20240523_001",
        }

        response = client.post("/api/agent/analyze", json=java_request)
        assert response.status_code == 200

        # 验证 run_workflow 被调用，且 AnalyzeRequest 正确解析了 camelCase
        mock_run_workflow.assert_called_once()
        analyze_request = mock_run_workflow.call_args[0][0]
        assert analyze_request.paper_ids == ["arxiv_2024_001", "arxiv_2024_002"]
        assert analyze_request.user_id == "usr_001"
        assert analyze_request.analysis_type.value == "report"
        assert analyze_request.analysis_id == "anl_20240523_001"
        assert analyze_request.user_profile.education_level.value == "master"
        assert analyze_request.user_profile.research_field == "NLP"
        assert analyze_request.user_profile.knowledge_level.value == "intermediate"
        assert analyze_request.user_profile.preferred_style.value == "balanced"


class TestAnalyzeCamelCaseResponse:
    """2. 响应 data 字段为 camelCase"""

    @patch("app.api.endpoints.agent.events.app_state")
    @patch("app.api.endpoints.agent.run_workflow", new_callable=AsyncMock)
    def test_analyze_camelcase_response(self, mock_run_workflow, mock_state, mock_app_state):
        """响应 data 字段使用 camelCase（analysisId/agentStates/degradedReason），
        不出现 snake_case 键"""
        _apply_mock_app_state(mock_state, mock_app_state)

        mock_run_workflow.return_value = {
            "analysis_id": "anl_20240523_001",
            "status": "completed",
            "report": "## Mock 报告",
            "citations": [],
            "agent_states": {
                "retriever": {"name": "retriever", "status": "completed", "progress": 1.0, "duration_ms": 1200, "intermediate_result": "Found 10 papers"},
                "analyzer": {"name": "analyzer", "status": "completed", "progress": 1.0, "duration_ms": 8000},
                "generator": {"name": "generator", "status": "completed", "progress": 1.0, "duration_ms": 15000},
            },
            "degraded": False,
            "degraded_reason": None,
        }

        client = TestClient(app)

        response = client.post("/api/agent/analyze", json={
            "topic": "测试主题",
            "userId": "usr_001",
            "analysisType": "report",
            "analysisId": "anl_20240523_001",
        })
        assert response.status_code == 200

        body = response.json()
        data = body["data"]

        # 验证 camelCase 字段存在
        assert "analysisId" in data
        assert "agentStates" in data
        assert "degradedReason" in data

        # 验证 snake_case 字段不存在
        assert "analysis_id" not in data
        assert "agent_states" not in data
        assert "degraded_reason" not in data

        # 验证 agentStates 内部也是 camelCase
        agent_states = data["agentStates"]
        assert len(agent_states) > 0
        first_agent = agent_states[0]
        assert "agentName" in first_agent
        assert "durationMs" in first_agent
        assert "intermediateResult" in first_agent
        assert "agent_name" not in first_agent
        assert "duration_ms" not in first_agent
        assert "intermediate_result" not in first_agent


class TestSearchCamelCaseRoundtrip:
    """3. 搜索请求/响应 camelCase 一致"""

    @patch("app.api.endpoints.search.events.app_state")
    def test_search_camelcase_roundtrip(self, mock_state, mock_app_state, mock_search_service):
        """搜索请求 topK（camelCase）正确解析，响应 paperId/score（camelCase）正确输出"""
        mock_state.search_service = mock_search_service
        mock_state.reranker = mock_app_state["reranker"]

        client = TestClient(app)

        # Java 风格 camelCase 请求
        search_request = {
            "query": "Transformer注意力机制",
            "topK": 5,
            "filters": {"yearFrom": 2020, "yearTo": 2024, "venue": "ACL"},
        }

        response = client.post("/api/search/", json=search_request)
        assert response.status_code == 200

        body = response.json()
        data = body["data"]

        # 验证搜索服务被调用且 topK 正确解析
        mock_search_service.search.assert_called_once()
        call_kwargs = mock_search_service.search.call_args
        assert call_kwargs.kwargs.get("top_k") == 5 or call_kwargs[1].get("top_k") == 5

        # 验证响应结果使用 camelCase
        results = data["results"]
        assert len(results) > 0
        first_result = results[0]

        # camelCase 字段存在
        assert "paperId" in first_result
        assert "score" in first_result

        # snake_case 字段不存在
        assert "paper_id" not in first_result

        # 验证值正确
        assert first_result["paperId"] == "arxiv_2024_001"
        assert first_result["score"] == 0.95


class TestHealthResponseFormat:
    """4. /health 返回统一格式 {code, message, data, timestamp}"""

    @patch("app.main.app_state")
    def test_health_response_format(self, mock_state, mock_app_state):
        """GET /health 返回 {code, message, data, timestamp} 四字段，
        data 含 status + 6 组件状态"""
        _apply_mock_app_state(mock_state, mock_app_state)

        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200

        body = response.json()

        # 验证根级 4 字段
        assert set(body.keys()) == {"code", "message", "data", "timestamp"}
        assert body["code"] == 200
        assert body["message"] == "success"
        assert isinstance(body["timestamp"], int)

        # 验证 data 内容
        data = body["data"]
        assert data["status"] == "UP"
        assert data["llm"] == "loaded"
        assert data["embedding"] == "loaded_api"
        assert data["chroma"] == "connected"
        assert data["prompts"] == "loaded"
        assert data["searchService"] == "ready"
        assert data["reranker"] == "ready"


class TestModelStatusCamelCase:
    """5. /model/status 字段 camelCase"""

    @patch("app.api.endpoints.model.events.app_state")
    def test_model_status_camelcase(self, mock_state, mock_app_state):
        """GET /api/model/status 返回 camelCase 字段
        （activeLlmProvider/embeddingDimension/providerCandidates 等）"""
        _apply_mock_app_state(mock_state, mock_app_state)

        client = TestClient(app)

        response = client.get("/api/model/status")
        assert response.status_code == 200

        body = response.json()
        data = body["data"]

        # 验证 camelCase 字段存在
        assert "activeLlmProvider" in data
        assert "embeddingDimension" in data
        assert "providerCandidates" in data
        assert "chromaPaperCount" in data
        assert "gpuMemoryUsed" in data
        assert "llmProviderCount" in data
        assert "searchService" in data

        # 验证 snake_case 字段不存在
        assert "active_llm_provider" not in data
        assert "embedding_dimension" not in data
        assert "provider_candidates" not in data
        assert "chroma_paper_count" not in data
        assert "gpu_memory_used" not in data
        assert "llm_provider_count" not in data

        # 验证值正确
        assert data["activeLlmProvider"] == "api"
        assert data["embeddingDimension"] == 1024
        assert "api" in data["providerCandidates"]
        assert data["chromaPaperCount"] == 200
        assert data["llmProviderCount"] == 1
        assert data["searchService"] == "ready"
