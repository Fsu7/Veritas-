"""Task45 SSE 6-Agent 事件完整性测试

验证：
- 每个 Agent 均有 agent_started + agent_completed 事件
- comparer 跳过时无 comparer 事件
- workflow_degraded 事件
- review_rejected 事件
- SSE 事件顺序和 ID 单调递增
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.base import AgentState, AgentStatus, BaseAgent
from app.agents.orchestrator import AgentOrchestrator
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


def _make_failing_agent(name: str, error_msg: str) -> MagicMock:
    agent = MagicMock(spec=BaseAgent)
    agent.name = name
    agent.state = AgentState(name=name)
    agent.state.status = AgentStatus.FAILED
    agent.state.error = error_msg
    agent.execute = AsyncMock(side_effect=Exception(error_msg))
    agent._fallback_result = MagicMock(
        return_value={"degraded": True, "agent": name, "error": error_msg}
    )
    return agent


async def _collect_events(orchestrator: AgentOrchestrator, request: AnalyzeRequest) -> list:
    events = []
    async for event in orchestrator.run_workflow_stream(request):
        events.append(event)
    return events


# ===== Test 1: SSE 事件完整性 =====


class TestSSEEventCompleteness:
    """每个 Agent 均有 agent_started + agent_completed 事件"""

    @pytest.mark.asyncio
    async def test_each_agent_has_started_and_completed(self):
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
            "generator", {"report": "Report", "citation_list": []}
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
            topic="Event Completeness Test",
            user_id="usr_001",
            analysis_id="anl_completeness",
        )

        orchestrator = AgentOrchestrator(
            agent_instances=agent_instances,
            analysis_id="anl_completeness",
        )

        events = await _collect_events(orchestrator, request)

        # 收集每个 Agent 的 started 和 completed 事件
        started_agents = set()
        completed_agents = set()
        for e in events:
            if e["event"] == "agent_started":
                data = json.loads(e["data"])
                started_agents.add(data["agentName"])
            elif e["event"] == "agent_completed":
                data = json.loads(e["data"])
                completed_agents.add(data["agentName"])

        # 核心Agent（coordinator, retriever, analyzer, generator）必须有started+completed
        for agent_name in ["coordinator", "retriever", "analyzer", "generator"]:
            assert agent_name in started_agents, f"{agent_name} missing agent_started"
            assert agent_name in completed_agents, f"{agent_name} missing agent_completed"


# ===== Test 2: comparer 跳过时无事件 =====


class TestSSENoComparerWhenSkipped:
    """comparer 跳过时 SSE 无 comparer 事件"""

    @pytest.mark.asyncio
    async def test_no_comparer_events_when_skipped(self):
        # requires_compare=False → comparer 不执行
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
            "generator", {"report": "Report", "citation_list": []}
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
            topic="No Comparer Test",
            user_id="usr_001",
            analysis_id="anl_no_comparer",
        )

        orchestrator = AgentOrchestrator(
            agent_instances=agent_instances,
            analysis_id="anl_no_comparer",
        )

        events = await _collect_events(orchestrator, request)

        # 验证无 comparer 的 started/completed 事件
        for e in events:
            if e["event"] in ("agent_started", "agent_completed"):
                data = json.loads(e["data"])
                assert data.get("agentName") != "comparer", (
                    "comparer should not have events when skipped"
                )


# ===== Test 3: workflow_degraded 事件 =====


class TestSSEWorkflowDegradedEvent:
    """Agent 失败时 workflow_degraded 事件"""

    @pytest.mark.asyncio
    async def test_workflow_degraded_on_agent_failure(self):
        failing_analyzer = _make_failing_agent("analyzer", "Analyzer failed")
        mock_retriever = _make_mock_agent(
            "retriever", {"papers": [{"paper_id": "p1"}], "total_found": 1}
        )
        mock_generator = _make_mock_agent(
            "generator", {"report": "Report", "citation_list": []}
        )

        agent_instances = {
            "retriever": mock_retriever,
            "analyzer": failing_analyzer,
            "generator": mock_generator,
        }

        request = AnalyzeRequest(
            topic="Degraded Event Test",
            user_id="usr_001",
            analysis_id="anl_degraded_event",
        )

        orchestrator = AgentOrchestrator(
            agent_instances=agent_instances,
            analysis_id="anl_degraded_event",
        )

        events = await _collect_events(orchestrator, request)

        degraded_events = [e for e in events if e["event"] == "workflow_degraded"]
        assert len(degraded_events) >= 1

        data = json.loads(degraded_events[0]["data"])
        assert "degradedAgents" in data
        assert "analyzer" in data["degradedAgents"]


# ===== Test 4: review_rejected 事件 =====


class TestSSEReviewRejectedEvent:
    """审核不通过时 review_rejected 事件"""

    @pytest.mark.asyncio
    async def test_review_rejected_event(self):
        # Reviewer 首次不通过
        call_count = 0

        async def reviewer_execute(input_data, context):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "approved": False,
                    "issues": [{"claim": "test", "error_type": "factual"}],
                    "suggestions": [],
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
            "generator", {"report": "Report", "citation_list": []}
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
            "reviewer": mock_reviewer,
        }

        request = AnalyzeRequest(
            topic="Review Rejected Test",
            user_id="usr_001",
            analysis_id="anl_review_rejected",
        )

        orchestrator = AgentOrchestrator(
            agent_instances=agent_instances,
            analysis_id="anl_review_rejected",
        )

        events = await _collect_events(orchestrator, request)

        rejected_events = [e for e in events if e["event"] == "review_rejected"]
        assert len(rejected_events) >= 1

        data = json.loads(rejected_events[0]["data"])
        assert "agentName" in data
        assert data["agentName"] == "reviewer"
        assert "regenerateCount" in data
        assert "issues" in data


# ===== Test 5: SSE 事件顺序 =====


class TestSSEEventOrdering:
    """SSE 事件顺序和 ID 单调递增"""

    @pytest.mark.asyncio
    async def test_event_ids_monotonically_increasing(self):
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
            "generator", {"report": "Report", "citation_list": []}
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
            topic="Event Order Test",
            user_id="usr_001",
            analysis_id="anl_event_order",
        )

        orchestrator = AgentOrchestrator(
            agent_instances=agent_instances,
            analysis_id="anl_event_order",
        )

        events = await _collect_events(orchestrator, request)

        # 验证事件 ID 单调递增
        event_ids = [int(e["id"]) for e in events]
        for i in range(1, len(event_ids)):
            assert event_ids[i] > event_ids[i - 1], (
                f"Event ID not monotonically increasing: {event_ids[i-1]} -> {event_ids[i]}"
            )

    @pytest.mark.asyncio
    async def test_started_before_completed_for_each_agent(self):
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
            "generator", {"report": "Report", "citation_list": []}
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
            topic="Started Before Completed Test",
            user_id="usr_001",
            analysis_id="anl_started_before",
        )

        orchestrator = AgentOrchestrator(
            agent_instances=agent_instances,
            analysis_id="anl_started_before",
        )

        events = await _collect_events(orchestrator, request)

        # 收集每个 Agent 的 started 和 completed 事件索引
        agent_started_idx = {}
        agent_completed_idx = {}
        for i, e in enumerate(events):
            if e["event"] == "agent_started":
                data = json.loads(e["data"])
                agent_started_idx[data["agentName"]] = i
            elif e["event"] == "agent_completed":
                data = json.loads(e["data"])
                agent_completed_idx[data["agentName"]] = i

        # 验证每个 Agent 的 started 在 completed 之前
        for agent_name in agent_started_idx:
            if agent_name in agent_completed_idx:
                assert agent_started_idx[agent_name] < agent_completed_idx[agent_name], (
                    f"{agent_name}: agent_started (idx={agent_started_idx[agent_name]}) "
                    f"should come before agent_completed (idx={agent_completed_idx[agent_name]})"
                )

    @pytest.mark.asyncio
    async def test_analysis_completed_is_last_event(self):
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
            "generator", {"report": "Report", "citation_list": []}
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
            topic="Last Event Test",
            user_id="usr_001",
            analysis_id="anl_last_event",
        )

        orchestrator = AgentOrchestrator(
            agent_instances=agent_instances,
            analysis_id="anl_last_event",
        )

        events = await _collect_events(orchestrator, request)

        # analysis_completed 应为最后一个事件（排除可能的 ping 事件）
        non_ping_events = [e for e in events if e["event"] != "ping"]
        assert non_ping_events[-1]["event"] == "analysis_completed"
