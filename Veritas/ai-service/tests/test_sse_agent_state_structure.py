"""Task44 SSE Agent 状态结构测试

验证：
- AgentStateResponse 新字段（error/startedAt/completedAt/degraded）
- AnalyzeResponse degradationLevel 字段
- _convert_agent_states() 新字段映射
- SSE 事件数据结构增强（agent_started +analysisType、agent_completed +完整intermediateResult/degraded、
  agent_failed +errorType/degraded/fallback、analysis_completed +degradationLevel/degradedAgents、
  workflow_degraded 事件）
- 6-Agent 完整 SSE 事件序列
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.base import AgentState, AgentStatus, BaseAgent
from app.agents.orchestrator import AgentOrchestrator
from app.api.endpoints.agent import _convert_agent_states
from app.models.schemas import AgentStateResponse, AnalyzeResponse


# ===== 辅助函数 =====


def _make_mock_agent(
    name: str, return_value: dict, status: AgentStatus = AgentStatus.COMPLETED
) -> MagicMock:
    """创建 mock Agent 实例"""
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
    """创建执行失败的 mock Agent"""
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


# ===== Test 1: AgentStateResponse 新字段 =====


class TestAgentStateResponseNewFields:
    """验证 AgentStateResponse 包含新字段"""

    def test_contains_error_started_at_completed_at_degraded(self):
        r = AgentStateResponse(
            agent_name="retriever",
            status="completed",
            progress=1.0,
            intermediate_result="Found 10 papers",
            duration_ms=1200,
            error=None,
            started_at="2024-01-01T00:00:00",
            completed_at="2024-01-01T00:00:01",
            degraded=False,
        )
        assert r.error is None
        assert r.started_at == "2024-01-01T00:00:00"
        assert r.completed_at == "2024-01-01T00:00:01"
        assert r.degraded is False

    def test_camelcase_alias_output(self):
        r = AgentStateResponse(
            agent_name="analyzer",
            status="failed",
            error="timeout",
            started_at="2024-01-01T00:00:00",
            completed_at="2024-01-01T00:00:01",
            degraded=True,
        )
        dumped = r.model_dump(by_alias=True)
        assert "agentName" in dumped
        assert "error" in dumped
        assert "startedAt" in dumped
        assert "completedAt" in dumped
        assert "degraded" in dumped
        assert dumped["degraded"] is True

    def test_degraded_defaults_to_none(self):
        r = AgentStateResponse(agent_name="test", status="running")
        assert r.degraded is None


# ===== Test 2: AnalyzeResponse degradationLevel =====


class TestAnalyzeResponseDegradationLevel:
    """验证 AnalyzeResponse degradationLevel 字段"""

    def test_contains_degradation_level_field(self):
        r = AnalyzeResponse(
            analysis_id="anl_001",
            status="completed",
            degradation_level="none",
        )
        assert r.degradation_level == "none"

    def test_degradation_level_calculation(self):
        # 0 个降级 → none
        r0 = AnalyzeResponse(analysis_id="a", status="completed", degradation_level="none")
        assert r0.degradation_level == "none"
        # 1 个降级 → partial
        r1 = AnalyzeResponse(analysis_id="a", status="degraded", degradation_level="partial")
        assert r1.degradation_level == "partial"
        # 2 个降级 → severe
        r2 = AnalyzeResponse(analysis_id="a", status="degraded", degradation_level="severe")
        assert r2.degradation_level == "severe"
        # 3+ 个降级 → critical
        r3 = AnalyzeResponse(analysis_id="a", status="degraded", degradation_level="critical")
        assert r3.degradation_level == "critical"

    def test_degradation_level_camelcase_alias(self):
        r = AnalyzeResponse(
            analysis_id="a", status="completed", degradation_level="none"
        )
        dumped = r.model_dump(by_alias=True)
        assert "degradationLevel" in dumped
        assert dumped["degradationLevel"] == "none"


# ===== Test 3: _convert_agent_states 新字段映射 =====


class TestConvertAgentStatesNewFields:
    """验证 _convert_agent_states() 映射新字段"""

    def test_maps_error_started_at_completed_at_degraded(self):
        agent_states = {
            "retriever": {
                "status": "completed",
                "progress": 1.0,
                "intermediate_result": "Found 10 papers",
                "duration_ms": 1200,
                "error": None,
                "started_at": "2024-01-01T00:00:00",
                "completed_at": "2024-01-01T00:00:01",
            },
            "analyzer": {
                "status": "failed",
                "progress": 0.5,
                "intermediate_result": "",
                "duration_ms": 30000,
                "error": "Agent analyzer timed out after 30s",
                "started_at": "2024-01-01T00:00:02",
                "completed_at": "2024-01-01T00:00:32",
            },
        }
        result = _convert_agent_states(agent_states)
        assert len(result) == 2

        # retriever: completed, not degraded
        retriever_resp = result[0]
        assert retriever_resp.agent_name == "retriever"
        assert retriever_resp.error is None
        assert retriever_resp.degraded is False

        # analyzer: failed → degraded=True
        analyzer_resp = result[1]
        assert analyzer_resp.agent_name == "analyzer"
        assert analyzer_resp.error == "Agent analyzer timed out after 30s"
        assert analyzer_resp.degraded is True

    def test_degraded_flag_from_state_dict(self):
        agent_states = {
            "generator": {
                "status": "completed",
                "progress": 1.0,
                "intermediate_result": "Report generated",
                "duration_ms": 5000,
                "error": None,
                "degraded": True,
            },
        }
        result = _convert_agent_states(agent_states)
        assert result[0].degraded is True


# ===== Test 4: SSE agent_started 含 analysisType =====


class TestSSEAgentStartedHasAnalysisType:
    """验证 agent_started 事件包含 analysisType 字段"""

    @pytest.mark.asyncio
    async def test_agent_started_contains_analysis_type(self):
        from app.models.schemas import AnalyzeRequest

        mock_retriever = _make_mock_agent(
            "retriever", {"papers": [{"paper_id": "p1"}], "total_found": 1}
        )
        mock_analyzer = _make_mock_agent(
            "analyzer", {"analysis_results": [{"summary": "test"}]}
        )
        mock_generator = _make_mock_agent(
            "generator", {"report": "Report", "citation_list": []}
        )

        agent_instances = {
            "retriever": mock_retriever,
            "analyzer": mock_analyzer,
            "generator": mock_generator,
        }

        request = AnalyzeRequest(
            topic="Test topic",
            user_id="usr_001",
            analysis_type="compare",
            analysis_id="anl_analysis_type_test",
        )

        orchestrator = AgentOrchestrator(
            agent_instances=agent_instances,
            analysis_id="anl_analysis_type_test",
        )

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        started_events = [e for e in events if e["event"] == "agent_started"]
        assert len(started_events) >= 1
        for started_event in started_events:
            data = json.loads(started_event["data"])
            assert "analysisType" in data


# ===== Test 5: SSE agent_completed 含完整 intermediateResult =====


class TestSSEAgentCompletedHasFullIntermediateResult:
    """验证 agent_completed 事件 intermediateResult 为完整结果"""

    @pytest.mark.asyncio
    async def test_agent_completed_full_intermediate_result(self):
        from app.models.schemas import AnalyzeRequest

        full_result = {"papers": [{"paper_id": f"p{i}"} for i in range(10)], "total_found": 10}
        mock_retriever = _make_mock_agent("retriever", full_result)
        mock_analyzer = _make_mock_agent(
            "analyzer", {"analysis_results": [{"summary": "test"}]}
        )
        mock_generator = _make_mock_agent(
            "generator", {"report": "Report", "citation_list": []}
        )

        agent_instances = {
            "retriever": mock_retriever,
            "analyzer": mock_analyzer,
            "generator": mock_generator,
        }

        request = AnalyzeRequest(
            topic="Test topic",
            user_id="usr_001",
            analysis_id="anl_full_result_test",
        )

        orchestrator = AgentOrchestrator(
            agent_instances=agent_instances,
            analysis_id="anl_full_result_test",
        )

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        completed_events = [e for e in events if e["event"] == "agent_completed"]
        assert len(completed_events) >= 1

        # 验证 retriever 的 completed 事件含完整 intermediateResult
        retriever_completed = None
        for e in completed_events:
            data = json.loads(e["data"])
            if data.get("agentName") == "retriever":
                retriever_completed = data
                break

        assert retriever_completed is not None
        # intermediateResult 应为完整 JSON（包含所有10篇论文），而非截断
        ir = retriever_completed.get("intermediateResult", "")
        assert "p9" in ir  # 如果截断到200字符，无法包含 p9

        # 验证包含 degraded 字段
        assert "degraded" in retriever_completed


# ===== Test 6: SSE agent_failed 含 errorType/degraded/fallback =====


class TestSSEAgentFailedHasErrorTypeAndFallback:
    """验证 agent_failed 事件包含 errorType/degraded/fallback"""

    @pytest.mark.asyncio
    async def test_agent_failed_contains_error_type_and_fallback(self):
        from app.models.schemas import AnalyzeRequest

        failing_analyzer = _make_failing_agent("analyzer", "Analyzer crashed")
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
            topic="Test",
            user_id="usr_001",
            analysis_id="anl_failed_fields_test",
        )

        orchestrator = AgentOrchestrator(
            agent_instances=agent_instances,
            analysis_id="anl_failed_fields_test",
        )

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        failed_events = [e for e in events if e["event"] == "agent_failed"]
        assert len(failed_events) >= 1

        failed_data = json.loads(failed_events[0]["data"])
        assert "errorType" in failed_data
        assert failed_data.get("degraded") is True
        assert "fallback" in failed_data


# ===== Test 7: SSE workflow_degraded 事件 =====


class TestSSEWorkflowDegradedEvent:
    """验证 workflow_degraded SSE 事件"""

    @pytest.mark.asyncio
    async def test_workflow_degraded_event_on_agent_failure(self):
        from app.models.schemas import AnalyzeRequest

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
            topic="Test",
            user_id="usr_001",
            analysis_id="anl_wf_degraded_sse_test",
        )

        orchestrator = AgentOrchestrator(
            agent_instances=agent_instances,
            analysis_id="anl_wf_degraded_sse_test",
        )

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        degraded_events = [e for e in events if e["event"] == "workflow_degraded"]
        assert len(degraded_events) >= 1

        degraded_data = json.loads(degraded_events[0]["data"])
        assert "degradedAgents" in degraded_data
        assert "reason" in degraded_data
        assert "fallbackMode" in degraded_data


# ===== Test 8: SSE analysis_completed 含 degradationLevel/degradedAgents =====


class TestSSEAnalysisCompletedHasDegradationInfo:
    """验证 analysis_completed 事件包含 degradationLevel 和 degradedAgents"""

    @pytest.mark.asyncio
    async def test_analysis_completed_contains_degradation_info(self):
        from app.models.schemas import AnalyzeRequest

        mock_retriever = _make_mock_agent(
            "retriever", {"papers": [{"paper_id": "p1"}], "total_found": 1}
        )
        mock_analyzer = _make_mock_agent(
            "analyzer", {"analysis_results": [{"summary": "test"}]}
        )
        mock_generator = _make_mock_agent(
            "generator", {"report": "Report", "citation_list": []}
        )

        agent_instances = {
            "retriever": mock_retriever,
            "analyzer": mock_analyzer,
            "generator": mock_generator,
        }

        request = AnalyzeRequest(
            topic="Test",
            user_id="usr_001",
            analysis_id="anl_final_info_test",
        )

        orchestrator = AgentOrchestrator(
            agent_instances=agent_instances,
            analysis_id="anl_final_info_test",
        )

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        completed_events = [e for e in events if e["event"] == "analysis_completed"]
        assert len(completed_events) == 1

        final_data = json.loads(completed_events[0]["data"])
        assert "degradationLevel" in final_data
        assert "degradedAgents" in final_data
        assert isinstance(final_data["degradedAgents"], list)

    @pytest.mark.asyncio
    async def test_analysis_completed_degradation_level_on_failure(self):
        from app.models.schemas import AnalyzeRequest

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
            topic="Test",
            user_id="usr_001",
            analysis_id="anl_degradation_level_test",
        )

        orchestrator = AgentOrchestrator(
            agent_instances=agent_instances,
            analysis_id="anl_degradation_level_test",
        )

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        completed_events = [e for e in events if e["event"] == "analysis_completed"]
        assert len(completed_events) == 1

        final_data = json.loads(completed_events[0]["data"])
        # 1个Agent失败 → degradationLevel='partial'
        assert final_data["degradationLevel"] in ("partial", "severe", "critical")
        assert "analyzer" in final_data["degradedAgents"]


# ===== Test 9: 6-Agent 完整 SSE 事件序列 =====


class TestSSESixAgentsFullWorkflow:
    """验证6-Agent完整SSE事件序列"""

    @pytest.mark.asyncio
    async def test_six_agents_full_event_sequence(self):
        from app.models.schemas import AnalyzeRequest

        mock_coordinator = _make_mock_agent(
            "coordinator",
            {"requires_compare": False, "requires_review": True, "sub_tasks": ["task1"]},
        )
        mock_retriever = _make_mock_agent(
            "retriever", {"papers": [{"paper_id": "p1"}], "total_found": 1}
        )
        mock_analyzer = _make_mock_agent(
            "analyzer", {"analysis_results": [{"summary": "test"}]}
        )
        mock_generator = _make_mock_agent(
            "generator", {"report": "Full report", "citation_list": []}
        )
        mock_reviewer = _make_mock_agent(
            "reviewer",
            {"approved": True, "issues": [], "suggestions": [], "citation_accuracy": 0.9, "fact_accuracy": 0.9},
        )

        agent_instances = {
            "coordinator": mock_coordinator,
            "retriever": mock_retriever,
            "analyzer": mock_analyzer,
            "generator": mock_generator,
            "reviewer": mock_reviewer,
        }

        request = AnalyzeRequest(
            topic="6-Agent Test",
            user_id="usr_001",
            analysis_id="anl_6agent_test",
        )

        orchestrator = AgentOrchestrator(
            agent_instances=agent_instances,
            analysis_id="anl_6agent_test",
        )

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        # 验证每个 Agent 都有 started + completed 事件
        started_agents = set()
        completed_agents = set()
        for e in events:
            if e["event"] == "agent_started":
                data = json.loads(e["data"])
                started_agents.add(data["agentName"])
            elif e["event"] == "agent_completed":
                data = json.loads(e["data"])
                completed_agents.add(data["agentName"])

        # 至少有 coordinator, retriever, analyzer, generator
        assert "coordinator" in started_agents
        assert "retriever" in started_agents
        assert "analyzer" in started_agents
        assert "generator" in started_agents

        # 验证 analysis_completed 为最后一个事件
        assert events[-1]["event"] == "analysis_completed"


# ===== Test 10: SSE 全部事件类型 =====


class TestSSEAllEventTypesComplete:
    """验证 SSE 流包含预期的事件类型"""

    @pytest.mark.asyncio
    async def test_all_event_types_present(self):
        from app.models.schemas import AnalyzeRequest

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
            topic="Event Types Test",
            user_id="usr_001",
            analysis_id="anl_event_types_test",
        )

        orchestrator = AgentOrchestrator(
            agent_instances=agent_instances,
            analysis_id="anl_event_types_test",
        )

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        event_types = set(e["event"] for e in events)

        # 必须包含的事件类型
        assert "agent_started" in event_types
        assert "agent_state_update" in event_types
        assert "agent_completed" in event_types
        assert "analysis_completed" in event_types
