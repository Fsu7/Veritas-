"""task56 AM4 遗留 6-Agent E2E 测试（AM5 回归验证）

验证 AM4 阶段的 6-Agent 工作流在 AM5 改动后仍然正常工作：
1. 6-Agent 完整工作流（coordinator→retriever→analyzer→[comparer]→generator→reviewer）
2. 条件分支（paper_count<2 跳过 comparer）
3. 审核重试闭环
4. 跨 Agent 数据流正确性
5. WorkflowState 转换验证

这是 AM5 阶段的回归测试，确保 task53-55 的改动未破坏 AM4 的 6-Agent 工作流。
"""
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.base import AgentState, AgentStatus, BaseAgent
from app.agents.graph import (
    WorkflowState,
    build_agent_graph,
    coordinator_node,
    compare_node,
    generate_node,
    retrieve_node,
    review_node,
    analyze_node,
    run_workflow,
    should_compare,
)
from app.models.schemas import AnalyzeRequest


# ===== 辅助函数 =====


def _make_mock_agent(
    name: str, return_value: dict, status: AgentStatus = AgentStatus.COMPLETED
) -> MagicMock:
    agent = MagicMock(spec=BaseAgent)
    agent.name = name
    agent.state = AgentState(name=name)
    agent.state.status = status
    agent.state.started_at = datetime.now()
    agent.state.completed_at = datetime.now()
    agent.state.duration_ms = 1000
    agent.state.intermediate_result = f"{name} completed"
    agent.state.error = None
    agent.execute = AsyncMock(return_value=return_value)
    agent._fallback_result = MagicMock(
        return_value={"degraded": True, "agent": name, "error": "failed"}
    )
    return agent


def _make_initial_state(**overrides) -> WorkflowState:
    state: WorkflowState = {
        "query": "Multi-Agent协同决策",
        "user_profile": {},
        "analysis_type": "report",
        "analysis_id": "anl_e2e_test",
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
        "requires_compare": False,
        "requires_review": True,
        "coordinator_result": None,
        "degraded_agents": [],
        "degradation_level": "none",
    }
    state.update(overrides)
    return state


# ===== Test 1: 6-Agent 端到端全链路（含 comparer） =====


class TestFull6AgentPipelineWithCompare:
    """6-Agent 完整工作流（含 comparer 分支）"""

    @pytest.mark.asyncio
    async def test_full_pipeline_with_compare_branch(self):
        """coordinator→retriever→analyzer→comparer→generator→reviewer 完整链路"""
        mock_coordinator = _make_mock_agent(
            "coordinator",
            {"requires_compare": True, "requires_review": True, "sub_tasks": ["task1", "task2"]},
        )
        mock_retriever = _make_mock_agent(
            "retriever",
            {"papers": [{"paper_id": f"p{i}"} for i in range(5)], "total_found": 5},
        )
        mock_analyzer = _make_mock_agent(
            "analyzer",
            {"analysis_results": [{"paper_id": "p0", "summary": "Analysis of p0"}]},
        )
        mock_comparer = _make_mock_agent(
            "comparer",
            {"comparisons": [{"dim": "methodology", "findings": "diff"}], "contradictions": []},
        )
        mock_generator = _make_mock_agent(
            "generator",
            {"report": "## 文献综述\n完整报告内容", "citation_list": [{"index": 1, "paper_id": "p0"}]},
        )
        mock_reviewer = _make_mock_agent(
            "reviewer",
            {"approved": True, "issues": [], "suggestions": [], "citation_accuracy": 0.95, "fact_accuracy": 0.9},
        )

        agent_instances = {
            "coordinator": mock_coordinator,
            "retriever": mock_retriever,
            "analyzer": mock_analyzer,
            "comparer": mock_comparer,
            "generator": mock_generator,
            "reviewer": mock_reviewer,
        }

        request = AnalyzeRequest(
            topic="Multi-Agent协同决策",
            user_id="usr_001",
            analysis_id="anl_full_with_compare",
        )

        result = await run_workflow(request, agent_instances)

        # 验证工作流完成
        assert result["status"] in ("completed", "degraded")
        assert result["report"] is not None
        assert len(result["report"]) > 0
        # comparer 应被调用
        assert mock_comparer.execute.called
        # reviewer 应被调用
        assert mock_reviewer.execute.called


# ===== Test 2: 6-Agent 端到端（跳过 comparer） =====


class TestFull6AgentPipelineSkipCompare:
    """6-Agent 完整工作流（paper_count<2 跳过 comparer）"""

    @pytest.mark.asyncio
    async def test_full_pipeline_skip_compare(self):
        """paper_count<2 时应跳过 comparer"""
        mock_coordinator = _make_mock_agent(
            "coordinator",
            {"requires_compare": True, "requires_review": True, "sub_tasks": ["task1"]},
        )
        mock_retriever = _make_mock_agent(
            "retriever",
            {"papers": [{"paper_id": "p1"}], "total_found": 1},  # 只有1篇
        )
        mock_analyzer = _make_mock_agent(
            "analyzer",
            {"analysis_results": [{"paper_id": "p1", "summary": "Analysis"}]},
        )
        mock_comparer = _make_mock_agent(
            "comparer",
            {"comparisons": [], "contradictions": []},
        )
        mock_generator = _make_mock_agent(
            "generator",
            {"report": "## 报告\n单篇论文分析", "citation_list": [{"index": 1, "paper_id": "p1"}]},
        )
        mock_reviewer = _make_mock_agent(
            "reviewer",
            {"approved": True, "issues": [], "suggestions": [], "citation_accuracy": 1.0, "fact_accuracy": 1.0},
        )

        agent_instances = {
            "coordinator": mock_coordinator,
            "retriever": mock_retriever,
            "analyzer": mock_analyzer,
            "comparer": mock_comparer,
            "generator": mock_generator,
            "reviewer": mock_reviewer,
        }

        request = AnalyzeRequest(
            topic="单篇论文分析",
            user_id="usr_001",
            analysis_id="anl_skip_compare",
        )

        result = await run_workflow(request, agent_instances)

        assert result["status"] in ("completed", "degraded")
        assert result["report"] is not None
        # comparer 不应被调用（paper_count<2）
        assert not mock_comparer.execute.called


# ===== Test 3: 条件分支 should_compare =====


class TestShouldCompareBranch:
    """should_compare 条件分支验证"""

    def test_should_compare_returns_generate_when_few_papers(self):
        """paper_count<2 时返回 'generate'"""
        state = _make_initial_state(requires_compare=True, search_results=[{"paper_id": "p1"}])
        assert should_compare(state) == "generate"

    def test_should_compare_returns_compare_when_enough_papers(self):
        """paper_count>=2 且 requires_compare=True 时返回 'compare'"""
        state = _make_initial_state(
            requires_compare=True,
            search_results=[{"paper_id": "p1"}, {"paper_id": "p2"}],
        )
        assert should_compare(state) == "compare"

    def test_should_compare_returns_generate_when_not_required(self):
        """requires_compare=False 时返回 'generate'"""
        state = _make_initial_state(
            requires_compare=False,
            search_results=[{"paper_id": "p1"}, {"paper_id": "p2"}],
        )
        assert should_compare(state) == "generate"


# ===== Test 4: 审核重试闭环 =====


class TestReviewRetryLoop:
    """审核不通过→重新生成→审核通过 闭环"""

    @pytest.mark.asyncio
    async def test_review_retry_loop(self):
        """首次审核不通过，重新生成后审核通过"""
        call_count = 0

        async def reviewer_execute(input_data, context):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "approved": False,
                    "issues": [{"claim": "test issue", "error_type": "factual"}],
                    "suggestions": [{"section": "1", "suggestion": "Fix issue"}],
                    "citation_accuracy": 0.5,
                    "fact_accuracy": 0.5,
                }
            return {
                "approved": True,
                "issues": [],
                "suggestions": [],
                "citation_accuracy": 0.9,
                "fact_accuracy": 0.9,
            }

        mock_coordinator = _make_mock_agent(
            "coordinator",
            {"requires_compare": False, "requires_review": True, "sub_tasks": []},
        )
        mock_retriever = _make_mock_agent(
            "retriever", {"papers": [{"paper_id": "p1"}], "total_found": 1}
        )
        mock_analyzer = _make_mock_agent(
            "analyzer", {"analysis_results": [{"summary": "test"}]}
        )
        mock_generator = _make_mock_agent(
            "generator", {"report": "Generated report", "citation_list": []}
        )
        mock_reviewer = MagicMock(spec=BaseAgent)
        mock_reviewer.name = "reviewer"
        mock_reviewer.state = AgentState(name="reviewer")
        mock_reviewer.state.status = AgentStatus.COMPLETED
        mock_reviewer.execute = reviewer_execute
        mock_reviewer._fallback_result = MagicMock(
            return_value={"degraded": True, "agent": "reviewer", "error": "failed"}
        )

        agent_instances = {
            "coordinator": mock_coordinator,
            "retriever": mock_retriever,
            "analyzer": mock_analyzer,
            "generator": mock_generator,
            "comparer": _make_mock_agent("comparer", {"comparisons": [], "contradictions": []}),
            "reviewer": mock_reviewer,
        }

        request = AnalyzeRequest(
            topic="Review Retry Test",
            user_id="usr_001",
            analysis_id="anl_review_retry",
        )

        result = await run_workflow(request, agent_instances)

        # reviewer 应被调用至少2次
        assert call_count >= 2
        # 最终应有报告
        assert result.get("report") is not None


# ===== Test 5: 跨 Agent 数据流验证 =====


class TestCrossAgentDataFlow:
    """验证 Agent 之间的数据流正确传递"""

    @pytest.mark.asyncio
    async def test_coordinator_to_retriever(self):
        """coordinator 的 sub_tasks 应传递到后续节点"""
        mock_coordinator = _make_mock_agent(
            "coordinator",
            {"requires_compare": False, "requires_review": True, "sub_tasks": ["task1"]},
        )
        state = _make_initial_state()
        result = await coordinator_node(state, {"coordinator": mock_coordinator})
        assert result.get("sub_tasks") == ["task1"]

    @pytest.mark.asyncio
    async def test_retriever_to_analyzer(self):
        """retriever 的 papers 应传递到 analyzer"""
        papers = [{"paper_id": f"p{i}"} for i in range(3)]
        mock_retriever = _make_mock_agent(
            "retriever", {"papers": papers, "total_found": 3}
        )
        state = _make_initial_state()
        result = await retrieve_node(state, {"retriever": mock_retriever})
        assert len(result.get("search_results", [])) == 3

    @pytest.mark.asyncio
    async def test_generator_to_reviewer(self):
        """generator 的 report 应传递到 reviewer"""
        mock_generator = _make_mock_agent(
            "generator",
            {"report": "Generated report", "citation_list": [{"index": 1}]},
        )
        state = _make_initial_state(
            analysis_results=[{"summary": "test"}],
            compare_result=None,
        )
        result = await generate_node(state, {"generator": mock_generator})
        assert result.get("report") == "Generated report"
        assert len(result.get("citations", [])) == 1
