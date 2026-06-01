import asyncio
import json
from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.base import AgentState, AgentStatus, BaseAgent
from app.agents.graph import (
    WorkflowState,
    _serialize_agent_state,
    analyze_node,
    build_agent_graph,
    generate_node,
    retrieve_node,
    run_workflow,
)
from app.models.schemas import AnalyzeRequest, UserProfile


def _make_mock_agent(name: str, return_value: dict) -> AsyncMock:
    agent = AsyncMock()
    agent.name = name
    agent.state = AgentState(name=name)
    agent.state.status = AgentStatus.COMPLETED
    agent.state.started_at = datetime.now()
    agent.state.completed_at = datetime.now()
    agent.state.duration_ms = 1000
    agent.state.intermediate_result = f"{name} completed"
    agent.state.error = None
    agent.execute = AsyncMock(return_value=return_value)
    return agent


def _make_initial_state(**overrides) -> WorkflowState:
    base: WorkflowState = {
        "query": "Multi-Agent协同决策",
        "user_profile": {"education_level": "master", "research_field": "NLP", "knowledge_level": "intermediate", "preferred_style": "balanced"},
        "analysis_type": "report",
        "analysis_id": "anl_test_001",
        "sub_tasks": [],
        "search_results": [],
        "analysis_results": [],
        "compare_result": None,
        "report": None,
        "review_result": None,
        "citations": [],
        "final_output": None,
        "agent_states": {},
        "errors": [],
        "degraded": False,
        "regenerate_count": 0,
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
    }
    base.update(overrides)
    return base


class TestWorkflowStateFields:

    def test_workflow_state_has_all_required_fields(self):
        state = _make_initial_state()
        required_keys = [
            "query", "user_profile", "analysis_type", "analysis_id",
            "sub_tasks", "search_results", "analysis_results",
            "compare_result", "report", "review_result", "citations",
            "final_output", "agent_states", "errors", "degraded",
            "regenerate_count", "started_at", "completed_at",
        ]
        for key in required_keys:
            assert key in state, f"Missing key: {key}"

    def test_workflow_state_default_values(self):
        state = _make_initial_state()
        assert state["sub_tasks"] == []
        assert state["search_results"] == []
        assert state["analysis_results"] == []
        assert state["compare_result"] is None
        assert state["report"] is None
        assert state["review_result"] is None
        assert state["citations"] == []
        assert state["final_output"] is None
        assert state["agent_states"] == {}
        assert state["errors"] == []
        assert state["degraded"] is False
        assert state["regenerate_count"] == 0


class TestRetrieveNode:

    @pytest.mark.asyncio
    async def test_retrieve_node_success(self):
        papers = [{"paper_id": "p1", "title": "Paper 1", "score": 0.9}]
        mock_agent = _make_mock_agent("retriever", {"papers": papers, "total_found": 1})

        state = _make_initial_state()
        result = await retrieve_node(state, {"retriever": mock_agent})

        assert result["search_results"] == papers
        assert "retriever" in result["agent_states"]
        mock_agent.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_node_failure(self):
        mock_agent = _make_mock_agent("retriever", {})
        mock_agent.execute = AsyncMock(side_effect=Exception("Search failed"))
        mock_agent.state.status = AgentStatus.FAILED
        mock_agent.state.error = "Search failed"

        state = _make_initial_state()
        result = await retrieve_node(state, {"retriever": mock_agent})

        assert result["search_results"] == []
        assert result["degraded"] is True
        assert any(e["agent"] == "retriever" for e in result["errors"])

    @pytest.mark.asyncio
    async def test_retrieve_node_agent_not_found(self):
        state = _make_initial_state()
        result = await retrieve_node(state, {})

        assert result["search_results"] == []
        assert result["degraded"] is True


class TestAnalyzeNode:

    @pytest.mark.asyncio
    async def test_analyze_node_success(self):
        analysis = [{"paper_id": "p1", "research_problem": {"summary": "Test", "confidence": 0.8}}]
        mock_agent = _make_mock_agent("analyzer", {"analysis_results": analysis, "total_analyzed": 1, "degraded_papers": [], "extraction_quality": 0.8})

        state = _make_initial_state(search_results=[{"paper_id": "p1", "title": "Paper 1"}])
        result = await analyze_node(state, {"analyzer": mock_agent})

        assert result["analysis_results"] == analysis
        assert "analyzer" in result["agent_states"]

    @pytest.mark.asyncio
    async def test_analyze_node_failure(self):
        mock_agent = _make_mock_agent("analyzer", {})
        mock_agent.execute = AsyncMock(side_effect=Exception("Analysis failed"))
        mock_agent.state.status = AgentStatus.FAILED
        mock_agent.state.error = "Analysis failed"

        state = _make_initial_state(search_results=[{"paper_id": "p1"}])
        result = await analyze_node(state, {"analyzer": mock_agent})

        assert result["analysis_results"] == []
        assert result["degraded"] is True
        assert any(e["agent"] == "analyzer" for e in result["errors"])


class TestGenerateNode:

    @pytest.mark.asyncio
    async def test_generate_node_success(self):
        report = "## 文献综述\nTest report content"
        citations = [{"index": 1, "paper_id": "p1", "citation": "[Author, 2024]"}]
        mock_agent = _make_mock_agent("generator", {"report": report, "citation_list": citations, "term_density_actual": 0.15, "personalization_applied": {}})

        state = _make_initial_state(analysis_results=[{"paper_id": "p1"}])
        result = await generate_node(state, {"generator": mock_agent})

        assert result["report"] == report
        assert result["citations"] == citations
        assert "generator" in result["agent_states"]

    @pytest.mark.asyncio
    async def test_generate_node_failure(self):
        mock_agent = _make_mock_agent("generator", {})
        mock_agent.execute = AsyncMock(side_effect=Exception("Generation failed"))
        mock_agent.state.status = AgentStatus.FAILED
        mock_agent.state.error = "Generation failed"

        state = _make_initial_state(analysis_results=[{"paper_id": "p1"}])
        result = await generate_node(state, {"generator": mock_agent})

        assert result["degraded"] is True
        assert result["report"] is not None
        assert any(e["agent"] == "generator" for e in result["errors"])


class TestBuildAgentGraph:

    def test_build_agent_graph_returns_compiled_graph(self):
        mock_retriever = _make_mock_agent("retriever", {"papers": [], "total_found": 0})
        mock_analyzer = _make_mock_agent("analyzer", {"analysis_results": [], "total_analyzed": 0, "degraded_papers": [], "extraction_quality": 0.0})
        mock_generator = _make_mock_agent("generator", {"report": "test", "citation_list": [], "term_density_actual": 0.0, "personalization_applied": {}})

        agent_instances = {
            "retriever": mock_retriever,
            "analyzer": mock_analyzer,
            "generator": mock_generator,
        }

        graph = build_agent_graph(agent_instances)
        assert graph is not None

    def test_build_agent_graph_has_correct_nodes(self):
        mock_retriever = _make_mock_agent("retriever", {"papers": [], "total_found": 0})
        mock_analyzer = _make_mock_agent("analyzer", {"analysis_results": [], "total_analyzed": 0, "degraded_papers": [], "extraction_quality": 0.0})
        mock_generator = _make_mock_agent("generator", {"report": "test", "citation_list": [], "term_density_actual": 0.0, "personalization_applied": {}})

        agent_instances = {"retriever": mock_retriever, "analyzer": mock_analyzer, "generator": mock_generator}
        graph = build_agent_graph(agent_instances)

        node_names = list(graph.nodes.keys()) if hasattr(graph, 'nodes') else []
        expected_nodes = {"retrieve", "analyze", "generate", "__start__"}
        actual_nodes = set(node_names)
        assert expected_nodes.issubset(actual_nodes), f"Missing nodes: {expected_nodes - actual_nodes}"


class TestRunWorkflow:

    @pytest.mark.asyncio
    async def test_run_workflow_end_to_end(self):
        mock_retriever = _make_mock_agent("retriever", {"papers": [{"paper_id": "p1", "title": "Test"}], "total_found": 1})
        mock_analyzer = _make_mock_agent("analyzer", {"analysis_results": [{"paper_id": "p1"}], "total_analyzed": 1, "degraded_papers": [], "extraction_quality": 0.8})
        mock_generator = _make_mock_agent("generator", {"report": "## 综述\nTest", "citation_list": [], "term_density_actual": 0.1, "personalization_applied": {}})

        agent_instances = {"retriever": mock_retriever, "analyzer": mock_analyzer, "generator": mock_generator}

        request = AnalyzeRequest(
            topic="Multi-Agent",
            user_id="usr_001",
            user_profile=UserProfile(education_level="master", research_field="NLP", knowledge_level="intermediate", preferred_style="balanced"),
            analysis_type="report",
            analysis_id="anl_test_001",
        )

        result = await run_workflow(request, agent_instances)

        assert result["status"] in ("completed", "degraded")
        assert result["analysis_id"] == "anl_test_001"
        assert result["report"] is not None
        assert "agent_states" in result
        assert "errors" in result

    @pytest.mark.asyncio
    async def test_run_workflow_timeout(self):
        async def slow_execute(*args, **kwargs):
            await asyncio.sleep(200)
            return {"papers": []}

        mock_retriever = _make_mock_agent("retriever", {"papers": []})
        mock_retriever.execute = slow_execute
        mock_analyzer = _make_mock_agent("analyzer", {"analysis_results": [], "total_analyzed": 0, "degraded_papers": [], "extraction_quality": 0.0})
        mock_generator = _make_mock_agent("generator", {"report": "test", "citation_list": [], "term_density_actual": 0.0, "personalization_applied": {}})

        agent_instances = {"retriever": mock_retriever, "analyzer": mock_analyzer, "generator": mock_generator}

        request = AnalyzeRequest(
            topic="Multi-Agent",
            user_id="usr_001",
            analysis_id="anl_timeout_001",
        )

        with patch("app.agents.graph.settings") as mock_settings:
            mock_settings.AGENT_FULL_TIMEOUT = 0.1
            result = await run_workflow(request, agent_instances)

        assert result["status"] == "failed"
        assert result["degraded"] is True
        assert result["degraded_reason"] is not None

    @pytest.mark.asyncio
    async def test_run_workflow_multi_agent_failure(self):
        mock_retriever = _make_mock_agent("retriever", {})
        mock_retriever.execute = AsyncMock(side_effect=Exception("Retriever failed"))
        mock_retriever.state.status = AgentStatus.FAILED
        mock_retriever.state.error = "Retriever failed"

        mock_analyzer = _make_mock_agent("analyzer", {})
        mock_analyzer.execute = AsyncMock(side_effect=Exception("Analyzer failed"))
        mock_analyzer.state.status = AgentStatus.FAILED
        mock_analyzer.state.error = "Analyzer failed"

        mock_generator = _make_mock_agent("generator", {"report": "Fallback report", "citation_list": [], "term_density_actual": 0.0, "personalization_applied": {}})

        agent_instances = {"retriever": mock_retriever, "analyzer": mock_analyzer, "generator": mock_generator}

        request = AnalyzeRequest(
            topic="Multi-Agent",
            user_id="usr_001",
            analysis_id="anl_multi_fail_001",
        )

        result = await run_workflow(request, agent_instances)

        assert result["degraded"] is True
        assert result["degraded_reason"] is not None
        assert len(result["errors"]) >= 2


class TestAgentStateSerialization:

    def test_agent_state_to_dict_is_json_serializable(self):
        state = AgentState(name="retriever")
        state.status = AgentStatus.COMPLETED
        state.started_at = datetime.now()
        state.completed_at = datetime.now()
        state.duration_ms = 1500
        state.progress = 1.0
        state.intermediate_result = "Found 10 papers"

        result_dict = _serialize_agent_state(type("FakeAgent", (), {"state": state})())
        json_str = json.dumps(result_dict)
        parsed = json.loads(json_str)

        assert parsed["name"] == "retriever"
        assert parsed["status"] == "completed"
        assert parsed["duration_ms"] == 1500

    def test_agent_state_to_dict_with_none_fields(self):
        state = AgentState(name="analyzer")
        result_dict = _serialize_agent_state(type("FakeAgent", (), {"state": state})())
        json_str = json.dumps(result_dict)
        parsed = json.loads(json_str)

        assert parsed["name"] == "analyzer"
        assert parsed["started_at"] is None
        assert parsed["completed_at"] is None
