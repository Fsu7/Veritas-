import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.agents.base import AgentState, AgentStatus
from app.api.endpoints.agent import _build_agent_instances, _convert_agent_states
from app.core import events
from app.exception import AIServiceException
from app.main import app
from app.models.schemas import AgentStateResponse, AnalyzeResponse

client = TestClient(app)


def _mock_app_state():
    mock_llm = MagicMock()
    mock_llm.status = "loaded"
    mock_llm.generate = AsyncMock(return_value="test output")

    mock_prompt_manager = MagicMock()
    mock_prompt_manager.get_prompt = MagicMock(return_value="test prompt")

    mock_search_service = MagicMock()
    mock_search_service.hybrid_search = AsyncMock(return_value=[])

    mock_reranker = MagicMock()

    events.app_state.llm_service = mock_llm
    events.app_state.prompt_manager = mock_prompt_manager
    events.app_state.search_service = mock_search_service
    events.app_state.reranker = mock_reranker

    return {
        "llm_service": mock_llm,
        "prompt_manager": mock_prompt_manager,
        "search_service": mock_search_service,
        "reranker": mock_reranker,
    }


def _clear_app_state():
    events.app_state.llm_service = None
    events.app_state.prompt_manager = None
    events.app_state.search_service = None
    events.app_state.reranker = None


VALID_REQUEST_BODY = {
    "topic": "Multi-Agent协同决策",
    "paperIds": ["arxiv_2024_001"],
    "userId": "usr_001",
    "userProfile": {
        "educationLevel": "master",
        "researchField": "NLP",
        "knowledgeLevel": "intermediate",
        "preferredStyle": "balanced",
    },
    "analysisType": "report",
    "analysisId": "anl_test_001",
}


class TestAnalyzeSuccess:

    def test_analyze_success(self):
        _mock_app_state()

        mock_workflow_result = {
            "analysis_id": "anl_test_001",
            "status": "completed",
            "report": "## 文献综述\nTest report",
            "citations": [{"index": 1, "paper_id": "p1", "citation": "[Author, 2024]"}],
            "agent_states": {
                "retriever": {"name": "retriever", "status": "completed", "progress": 1.0, "duration_ms": 1200, "intermediate_result": "Found 10 papers"},
                "analyzer": {"name": "analyzer", "status": "completed", "progress": 1.0, "duration_ms": 8000},
                "generator": {"name": "generator", "status": "completed", "progress": 1.0, "duration_ms": 15000},
            },
            "errors": [],
            "degraded": False,
            "degraded_reason": None,
        }

        with patch("app.api.endpoints.agent.run_workflow", new_callable=AsyncMock, return_value=mock_workflow_result):
            response = client.post("/api/agent/analyze", json=VALID_REQUEST_BODY)

        assert response.status_code == 200
        data = response.json()
        assert data["analysisId"] == "anl_test_001"
        assert data["status"] == "completed"
        assert data["report"] is not None
        assert data["degraded"] is False
        assert "agentStates" in data
        assert len(data["agentStates"]) == 3

        _clear_app_state()


class TestAnalyzeValidation:

    def test_analyze_validation_empty_topic(self):
        _mock_app_state()
        body = {**VALID_REQUEST_BODY, "topic": ""}
        response = client.post("/api/agent/analyze", json=body)
        assert response.status_code == 422
        _clear_app_state()

    def test_analyze_validation_missing_user_id(self):
        _mock_app_state()
        body = {k: v for k, v in VALID_REQUEST_BODY.items() if k != "userId"}
        response = client.post("/api/agent/analyze", json=body)
        assert response.status_code == 422
        _clear_app_state()


class TestAnalyzeDegraded:

    def test_analyze_degraded_single_agent_failure(self):
        _mock_app_state()

        mock_workflow_result = {
            "analysis_id": "anl_test_001",
            "status": "degraded",
            "report": "## 文献综述\nDegraded report",
            "citations": [],
            "agent_states": {
                "retriever": {"name": "retriever", "status": "completed", "progress": 1.0, "duration_ms": 1200},
                "analyzer": {"name": "analyzer", "status": "failed", "progress": 0.5, "error": "Analysis failed"},
                "generator": {"name": "generator", "status": "completed", "progress": 1.0, "duration_ms": 15000},
            },
            "errors": [{"agent": "analyzer", "error": "Analysis failed"}],
            "degraded": True,
            "degraded_reason": "Agent analyzer 失败，已降级处理",
        }

        with patch("app.api.endpoints.agent.run_workflow", new_callable=AsyncMock, return_value=mock_workflow_result):
            response = client.post("/api/agent/analyze", json=VALID_REQUEST_BODY)

        assert response.status_code == 200
        data = response.json()
        assert data["degraded"] is True
        assert data["degradedReason"] is not None

        _clear_app_state()

    def test_analyze_degraded_multi_agent_failure(self):
        _mock_app_state()

        mock_workflow_result = {
            "analysis_id": "anl_test_001",
            "status": "degraded",
            "report": "综述生成过程中发生错误，请稍后重试。",
            "citations": [],
            "agent_states": {
                "retriever": {"name": "retriever", "status": "failed", "error": "Search failed"},
                "analyzer": {"name": "analyzer", "status": "failed", "error": "Analysis failed"},
                "generator": {"name": "generator", "status": "completed", "progress": 1.0, "duration_ms": 15000},
            },
            "errors": [{"agent": "retriever", "error": "Search failed"}, {"agent": "analyzer", "error": "Analysis failed"}],
            "degraded": True,
            "degraded_reason": "多Agent失败(retriever, analyzer)，结果可能不完整",
        }

        with patch("app.api.endpoints.agent.run_workflow", new_callable=AsyncMock, return_value=mock_workflow_result):
            response = client.post("/api/agent/analyze", json=VALID_REQUEST_BODY)

        assert response.status_code == 200
        data = response.json()
        assert data["degraded"] is True
        assert "retriever" in data["degradedReason"] or "analyzer" in data["degradedReason"]

        _clear_app_state()


class TestAnalyzeResponseCamelCase:

    def test_analyze_response_camelcase(self):
        _mock_app_state()

        mock_workflow_result = {
            "analysis_id": "anl_test_001",
            "status": "completed",
            "report": "Test report",
            "citations": [],
            "agent_states": {
                "retriever": {"name": "retriever", "status": "completed", "progress": 1.0, "duration_ms": 1200, "intermediate_result": "Found 10 papers"},
            },
            "errors": [],
            "degraded": False,
            "degraded_reason": None,
        }

        with patch("app.api.endpoints.agent.run_workflow", new_callable=AsyncMock, return_value=mock_workflow_result):
            response = client.post("/api/agent/analyze", json=VALID_REQUEST_BODY)

        data = response.json()
        assert "analysisId" in data
        assert "agentStates" in data
        if data["agentStates"]:
            agent = data["agentStates"][0]
            assert "agentName" in agent
            assert "durationMs" in agent
            assert "intermediateResult" in agent
        assert "degradedReason" in data

        _clear_app_state()


class TestAnalyzeServiceNotInitialized:

    def test_analyze_service_not_initialized(self):
        _clear_app_state()
        response = client.post("/api/agent/analyze", json=VALID_REQUEST_BODY)
        assert response.status_code == 503


class TestBuildAgentInstances:

    def test_build_agent_instances_success(self):
        _mock_app_state()
        instances = _build_agent_instances()
        assert "retriever" in instances
        assert "analyzer" in instances
        assert "generator" in instances
        _clear_app_state()

    def test_build_agent_instances_llm_not_loaded(self):
        _mock_app_state()
        events.app_state.llm_service = None
        from app.exception import ModelNotLoadedException
        with pytest.raises(ModelNotLoadedException):
            _build_agent_instances()
        _clear_app_state()


class TestAgentStateResponseConversion:

    def test_agent_state_response_conversion(self):
        agent_states = {
            "retriever": {"name": "retriever", "status": "completed", "progress": 1.0, "duration_ms": 1200, "intermediate_result": "Found 10 papers"},
            "analyzer": {"name": "analyzer", "status": "running", "progress": 0.5, "duration_ms": None, "intermediate_result": None},
        }

        result = _convert_agent_states(agent_states)
        assert len(result) == 2
        assert isinstance(result[0], AgentStateResponse)
        assert result[0].agent_name == "retriever"
        assert result[0].status == "completed"
        assert result[0].duration_ms == 1200
