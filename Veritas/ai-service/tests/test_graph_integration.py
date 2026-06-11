"""test_graph_integration — 6-Agent全链路集成测试

验证 LangGraph 工作流中的条件边逻辑、审核重试、降级场景。
"""
import json
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.graph import (
    WorkflowState,
    build_agent_graph,
    should_review,
    should_regenerate,
    review_node,
    generate_node,
    run_workflow,
)
from app.agents.base import BaseAgent, AgentStatus


def _make_mock_agent(name: str, result: dict) -> MagicMock:
    """创建 Mock Agent"""
    agent = MagicMock(spec=BaseAgent)
    agent.name = name
    agent.state = MagicMock()
    agent.state.status = AgentStatus.COMPLETED
    agent.state.to_dict.return_value = {"name": name, "status": "completed", "progress": 1.0}
    agent.execute = AsyncMock(return_value=result)
    agent._last_result = result
    return agent


class TestShouldReview:
    """测试 should_review 条件函数"""

    def test_should_review_true(self):
        state = {"report": "综述内容", "degraded": False}
        assert should_review(state) is True

    def test_should_review_false_empty_report(self):
        state = {"report": "", "degraded": False}
        assert should_review(state) is False

    def test_should_review_false_none_report(self):
        state = {"report": None, "degraded": False}
        assert should_review(state) is False

    def test_should_review_false_whitespace(self):
        state = {"report": "   \n  ", "degraded": False}
        assert should_review(state) is False

    def test_should_review_false_degraded_no_review(self):
        state = {"report": "综述", "degraded": True, "review_result": None}
        assert should_review(state) is False

    def test_should_review_true_degraded_with_review(self):
        state = {"report": "综述", "degraded": True, "review_result": {"approved": False}}
        assert should_review(state) is True


class TestShouldRegenerate:
    """测试 should_regenerate 条件函数"""

    def test_should_regenerate_true(self):
        """审核不通过且 regenerate_count=0 时返回 regenerate"""
        state = {
            "review_result": {"approved": False},
            "regenerate_count": 0,
        }
        assert should_regenerate(state) == "regenerate"

    def test_should_regenerate_false_approved(self):
        """审核通过时返回 end"""
        state = {
            "review_result": {"approved": True},
            "regenerate_count": 0,
        }
        assert should_regenerate(state) == "end"

    def test_should_regenerate_false_max_retry(self):
        """regenerate_count>=1 时返回 end"""
        state = {
            "review_result": {"approved": False},
            "regenerate_count": 1,
        }
        assert should_regenerate(state) == "end"

    def test_should_regenerate_false_no_review(self):
        """无 review_result 时返回 end"""
        state = {
            "review_result": None,
            "regenerate_count": 0,
        }
        assert should_regenerate(state) == "end"


class TestBuildAgentGraph:
    """测试 build_agent_graph 编译"""

    def test_graph_compiles_with_reviewer(self):
        """验证包含 reviewer 的图可以编译"""
        mock_retriever = _make_mock_agent("retriever", {"papers": []})
        mock_analyzer = _make_mock_agent("analyzer", {"analysis_results": []})
        mock_generator = _make_mock_agent("generator", {"report": "综述", "citation_list": []})
        mock_reviewer = _make_mock_agent("reviewer", {"approved": True, "issues": [], "suggestions": []})

        agent_instances = {
            "retriever": mock_retriever,
            "analyzer": mock_analyzer,
            "generator": mock_generator,
            "reviewer": mock_reviewer,
        }

        graph = build_agent_graph(agent_instances)
        assert graph is not None

    def test_graph_compiles_without_reviewer(self):
        """验证不包含 reviewer 的图也可以编译"""
        mock_retriever = _make_mock_agent("retriever", {"papers": []})
        mock_analyzer = _make_mock_agent("analyzer", {"analysis_results": []})
        mock_generator = _make_mock_agent("generator", {"report": "综述", "citation_list": []})

        agent_instances = {
            "retriever": mock_retriever,
            "analyzer": mock_analyzer,
            "generator": mock_generator,
        }

        graph = build_agent_graph(agent_instances)
        assert graph is not None


class TestReviewNode:
    """测试 review_node"""

    @pytest.mark.asyncio
    async def test_review_agent_not_found_skip(self):
        """Reviewer 不存在时跳过审核，直接标记通过"""
        state = {
            "report": "综述内容",
            "search_results": [{"title": "Paper1"}],
            "regenerate_count": 0,
            "agent_states": {},
            "errors": [],
        }
        result = await review_node(state, {})
        assert result["review_result"]["approved"] is True

    @pytest.mark.asyncio
    async def test_review_agent_approved(self):
        """Reviewer 审核通过"""
        mock_reviewer = _make_mock_agent("reviewer", {
            "approved": True,
            "issues": [],
            "suggestions": [],
            "citation_accuracy": 1.0,
            "fact_accuracy": 1.0,
        })

        state = {
            "report": "综述内容",
            "search_results": [],
            "regenerate_count": 0,
            "agent_states": {},
            "errors": [],
        }
        result = await review_node(state, {"reviewer": mock_reviewer})
        assert result["review_result"]["approved"] is True

    @pytest.mark.asyncio
    async def test_review_agent_rejected(self):
        """Reviewer 审核不通过时 review_result.approved=False"""
        mock_reviewer = _make_mock_agent("reviewer", {
            "approved": False,
            "issues": [{"claim": "错误", "error_type": "factual_error"}],
            "suggestions": [],
            "citation_accuracy": 0.5,
            "fact_accuracy": 0.5,
        })

        state = {
            "report": "综述内容",
            "search_results": [],
            "regenerate_count": 0,
            "agent_states": {},
            "errors": [],
        }
        result = await review_node(state, {"reviewer": mock_reviewer})
        assert result["review_result"]["approved"] is False

    @pytest.mark.asyncio
    async def test_review_agent_timeout_degraded(self):
        """Reviewer 超时时降级处理"""
        mock_reviewer = _make_mock_agent("reviewer", {
            "approved": False,
            "degraded": True,
            "issues": [],
            "suggestions": [],
            "citation_accuracy": 0.0,
            "fact_accuracy": 0.0,
        })

        state = {
            "report": "综述内容",
            "search_results": [],
            "regenerate_count": 0,
            "agent_states": {},
            "errors": [],
        }
        result = await review_node(state, {"reviewer": mock_reviewer})
        # 降级时应标记审核通过，不阻塞流程
        assert result["review_result"]["approved"] is True
        assert result.get("degraded") is True


class TestFullWorkflow:
    """测试完整工作流"""

    @pytest.mark.asyncio
    async def test_full_workflow_with_review_approved(self):
        """6-Agent 全链路：审核通过"""
        mock_retriever = _make_mock_agent("retriever", {"papers": [{"title": "Paper1", "paper_id": "p1"}]})
        mock_analyzer = _make_mock_agent("analyzer", {"analysis_results": [{"paper_id": "p1", "paper_title": "Paper1"}]})
        mock_generator = _make_mock_agent("generator", {"report": "## 引言\n综述内容", "citation_list": []})
        mock_reviewer = _make_mock_agent("reviewer", {"approved": True, "issues": [], "suggestions": [], "citation_accuracy": 1.0, "fact_accuracy": 1.0})

        agent_instances = {
            "retriever": mock_retriever,
            "analyzer": mock_analyzer,
            "generator": mock_generator,
            "reviewer": mock_reviewer,
        }

        compiled_graph = build_agent_graph(agent_instances)

        initial_state: WorkflowState = {
            "query": "Transformer",
            "user_profile": {},
            "analysis_type": "report",
            "analysis_id": "test_001",
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
            "started_at": "2026-01-01T00:00:00",
            "completed_at": None,
        }

        result = await compiled_graph.ainvoke(initial_state)
        assert result.get("report") is not None
        assert result.get("review_result") is not None
        assert result["review_result"]["approved"] is True

    @pytest.mark.asyncio
    async def test_full_workflow_review_rejected_regenerate(self):
        """审核不通过→重新生成→再次审核"""
        call_count = {"reviewer": 0, "generator": 0}

        async def reviewer_execute(input_data, context):
            call_count["reviewer"] += 1
            if call_count["reviewer"] == 1:
                return {
                    "approved": False,
                    "issues": [{"claim": "错误", "error_type": "factual_error"}],
                    "suggestions": [{"section": "引言", "issue": "不准确", "suggestion": "修正", "error_type": "factual_error"}],
                    "citation_accuracy": 0.5,
                    "fact_accuracy": 0.5,
                }
            return {
                "approved": True,
                "issues": [],
                "suggestions": [],
                "citation_accuracy": 1.0,
                "fact_accuracy": 1.0,
            }

        async def generator_execute(input_data, context):
            call_count["generator"] += 1
            return {"report": "修正后的综述", "citation_list": []}

        mock_retriever = _make_mock_agent("retriever", {"papers": []})
        mock_analyzer = _make_mock_agent("analyzer", {"analysis_results": []})
        mock_generator = MagicMock(spec=BaseAgent)
        mock_generator.name = "generator"
        mock_generator.state = MagicMock()
        mock_generator.state.status = AgentStatus.COMPLETED
        mock_generator.state.to_dict.return_value = {"name": "generator", "status": "completed"}
        mock_generator.execute = generator_execute

        mock_reviewer = MagicMock(spec=BaseAgent)
        mock_reviewer.name = "reviewer"
        mock_reviewer.state = MagicMock()
        mock_reviewer.state.status = AgentStatus.COMPLETED
        mock_reviewer.state.to_dict.return_value = {"name": "reviewer", "status": "completed"}
        mock_reviewer.execute = reviewer_execute

        agent_instances = {
            "retriever": mock_retriever,
            "analyzer": mock_analyzer,
            "generator": mock_generator,
            "reviewer": mock_reviewer,
        }

        compiled_graph = build_agent_graph(agent_instances)

        initial_state: WorkflowState = {
            "query": "Transformer",
            "user_profile": {},
            "analysis_type": "report",
            "analysis_id": "test_002",
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
            "started_at": "2026-01-01T00:00:00",
            "completed_at": None,
        }

        result = await compiled_graph.ainvoke(initial_state)
        # 验证 reviewer 被调用了2次（首次不通过 + 重试后通过）
        assert call_count["reviewer"] == 2
        # 验证 generator 被调用了2次（首次 + 重试）
        assert call_count["generator"] == 2
        # 验证最终审核通过
        assert result["review_result"]["approved"] is True

    @pytest.mark.asyncio
    async def test_full_workflow_no_reviewer(self):
        """无 Reviewer 时跳过审核"""
        mock_retriever = _make_mock_agent("retriever", {"papers": []})
        mock_analyzer = _make_mock_agent("analyzer", {"analysis_results": []})
        mock_generator = _make_mock_agent("generator", {"report": "综述内容", "citation_list": []})

        agent_instances = {
            "retriever": mock_retriever,
            "analyzer": mock_analyzer,
            "generator": mock_generator,
        }

        compiled_graph = build_agent_graph(agent_instances)

        initial_state: WorkflowState = {
            "query": "Transformer",
            "user_profile": {},
            "analysis_type": "report",
            "analysis_id": "test_003",
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
            "started_at": "2026-01-01T00:00:00",
            "completed_at": None,
        }

        result = await compiled_graph.ainvoke(initial_state)
        assert result.get("report") is not None
        # Reviewer 不存在时应跳过审核，标记通过
        assert result["review_result"]["approved"] is True
