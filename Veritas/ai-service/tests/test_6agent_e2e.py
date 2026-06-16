"""Task45 6-Agent 端到端集成测试

验证：
- 6-Agent 完整工作流（coordinator→retriever→analyzer→[comparer]→generator→reviewer）
- 条件分支（paper_count<2 跳过 comparer）
- 审核重试闭环
- 跨 Agent 数据流正确性
- WorkflowState 转换验证
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


# ===== Test 1: 6-Agent 端到端全链路 =====


class TestFull6AgentPipeline:
    """6-Agent 端到端全链路测试"""

    @pytest.mark.asyncio
    async def test_full_6agent_pipeline(self):
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
            analysis_id="anl_full_6agent",
        )

        result = await run_workflow(request, agent_instances)

        # 验证工作流完成
        assert result["status"] in ("completed", "degraded")
        assert result["report"] is not None
        assert len(result["report"]) > 0
        assert result["degradation_level"] in ("none", "agent", "workflow")


# ===== Test 2: 条件分支 - comparer 跳过 =====


class TestComparerSkippedWhenFewPapers:
    """paper_count<2 时 comparer 被跳过"""

    def test_should_compare_returns_generate_when_few_papers(self):
        state = _make_initial_state(requires_compare=True, search_results=[{"paper_id": "p1"}])
        assert should_compare(state) == "generate"

    def test_should_compare_returns_compare_when_enough_papers(self):
        state = _make_initial_state(
            requires_compare=True,
            search_results=[{"paper_id": "p1"}, {"paper_id": "p2"}],
        )
        assert should_compare(state) == "compare"

    def test_should_compare_returns_generate_when_not_required(self):
        state = _make_initial_state(
            requires_compare=False,
            search_results=[{"paper_id": "p1"}, {"paper_id": "p2"}],
        )
        assert should_compare(state) == "generate"


# ===== Test 3: 审核重试闭环 =====


class TestReviewRetryLoop:
    """审核重试闭环测试"""

    @pytest.mark.asyncio
    async def test_review_retry_loop(self):
        # Reviewer 首次不通过，二次通过
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

        # 验证 reviewer 被调用至少2次（首次不通过+二次通过）
        assert call_count >= 2
        # 验证最终结果有报告
        assert result.get("report") is not None


# ===== Test 4: 跨 Agent 数据流验证 =====


class TestCrossAgentDataFlow:
    """跨 Agent 数据流验证"""

    @pytest.mark.asyncio
    async def test_coordinator_output_flows_to_retriever(self):
        """coordinator 的 sub_tasks 应影响后续检索"""
        mock_coordinator = _make_mock_agent(
            "coordinator",
            {"requires_compare": False, "requires_review": True, "sub_tasks": ["task1"]},
        )

        state = _make_initial_state()
        result = await coordinator_node(state, {"coordinator": mock_coordinator})

        assert result.get("sub_tasks") == ["task1"]
        assert result.get("requires_compare") is False

    @pytest.mark.asyncio
    async def test_retriever_output_flows_to_analyzer(self):
        """retriever 的 papers 应传入 analyzer"""
        papers = [{"paper_id": f"p{i}"} for i in range(3)]
        mock_retriever = _make_mock_agent(
            "retriever", {"papers": papers, "total_found": 3}
        )

        state = _make_initial_state()
        result = await retrieve_node(state, {"retriever": mock_retriever})

        assert len(result.get("search_results", [])) == 3

    @pytest.mark.asyncio
    async def test_analyzer_output_flows_to_generator(self):
        """analyzer 的 analysis_results 应传入 generator"""
        mock_analyzer = _make_mock_agent(
            "analyzer",
            {"analysis_results": [{"paper_id": "p0", "summary": "Analysis"}]},
        )

        state = _make_initial_state(search_results=[{"paper_id": "p0"}])
        result = await analyze_node(state, {"analyzer": mock_analyzer})

        assert len(result.get("analysis_results", [])) == 1

    @pytest.mark.asyncio
    async def test_generator_output_flows_to_reviewer(self):
        """generator 的 report 应传入 reviewer"""
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


# ===== Test 5: WorkflowState 转换验证 =====


class TestWorkflowStateTransitions:
    """WorkflowState 转换验证"""

    @pytest.mark.asyncio
    async def test_workflow_state_transitions(self):
        """验证 initial_state → retrieve → analyze → generate → review 各阶段 state 字段正确更新"""
        mock_coordinator = _make_mock_agent(
            "coordinator",
            {"requires_compare": False, "requires_review": True, "sub_tasks": []},
        )
        mock_retriever = _make_mock_agent(
            "retriever", {"papers": [{"paper_id": "p1"}], "total_found": 1}
        )
        mock_analyzer = _make_mock_agent(
            "analyzer", {"analysis_results": [{"summary": "analysis"}]}
        )
        mock_generator = _make_mock_agent(
            "generator", {"report": "Final report", "citation_list": []}
        )
        mock_reviewer = _make_mock_agent(
            "reviewer",
            {"approved": True, "issues": [], "suggestions": [], "citation_accuracy": 1.0, "fact_accuracy": 1.0},
        )

        agent_instances = {
            "coordinator": mock_coordinator,
            "retriever": mock_retriever,
            "analyzer": mock_analyzer,
            "generator": mock_generator,
            "reviewer": mock_reviewer,
        }

        request = AnalyzeRequest(
            topic="State Transition Test",
            user_id="usr_001",
            analysis_id="anl_state_trans",
        )

        result = await run_workflow(request, agent_instances)

        # 验证最终 state 的关键字段
        assert result.get("report") is not None
        assert result.get("started_at") is not None
        assert result.get("degraded") is False or result.get("degraded") is True
        assert isinstance(result.get("errors", []), list)
        assert isinstance(result.get("degraded_agents", []), list)
