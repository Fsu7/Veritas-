"""task25 测试套件 — SSE推送基础实现

覆盖：
- SSE 事件格式（event:\ndata:\n\n）
- 事件 data 字段 camelCase
- 正常流程事件序列完整性
- Agent 异常时 yield agent_failed + error，不中断流
- 端到端流式测试（mock LLM）
"""
import asyncio
import json
from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.agents.base import AgentStatus, AgentState, BaseAgent
from app.agents.orchestrator import AgentOrchestrator
from app.main import app
from app.models.schemas import AnalyzeRequest


# ===== Mock Agent 基类 =====

class MockAgent(BaseAgent):
    """测试用 Mock Agent"""

    def __init__(self, name: str, result: dict = None, should_fail: bool = False):
        # 手动初始化，跳过 BaseAgent.__init__ 的 llm_service/prompt_manager 参数
        self.name = name
        self.llm_service = None
        self.prompt_manager = None
        self.timeout = 30
        self.state = AgentState(name=name)
        self._mock_result = result or {}
        self._should_fail = should_fail

    async def _run(self, prompt: str, input_data: dict, context: dict) -> dict:
        if self._should_fail:
            raise RuntimeError(f"{self.name} failed")
        return self._mock_result

    def build_prompt(self, input_data: dict, context: dict) -> str:
        return f"Mock prompt for {self.name}"


def _make_mock_agents(
    coordinator_result=None,
    retriever_result=None,
    analyzer_result=None,
    generator_result=None,
    coordinator_fail=False,
    retriever_fail=False,
    analyzer_fail=False,
    generator_fail=False,
) -> Dict[str, MockAgent]:
    """创建一组 Mock Agent"""
    return {
        "coordinator": MockAgent(
            "coordinator",
            result=coordinator_result or {"requires_compare": False, "requires_review": True, "sub_tasks": []},
            should_fail=coordinator_fail,
        ),
        "retriever": MockAgent(
            "retriever",
            result=retriever_result or {"papers": [{"title": "Test Paper"}]},
            should_fail=retriever_fail,
        ),
        "analyzer": MockAgent(
            "analyzer",
            result=analyzer_result or {"analysis_results": [{"summary": "Test analysis"}]},
            should_fail=analyzer_fail,
        ),
        "generator": MockAgent(
            "generator",
            result=generator_result or {"report": "## Test Report", "citation_list": []},
            should_fail=generator_fail,
        ),
    }


# ===== FR-003: SSE 事件格式测试 =====

class TestSSEEventFormat:
    """测试 EventSourceResponse 输出符合 SSE 规范"""

    def test_event_dict_has_required_keys(self):
        """每个 SSE 事件必须包含 id/event/data 三个键"""
        orchestrator = AgentOrchestrator(
            agent_instances=_make_mock_agents(),
            analysis_id="test_001",
        )
        event = orchestrator._make_event("agent_started", {"agentName": "retriever"})
        assert "id" in event
        assert "event" in event
        assert "data" in event

    def test_event_data_is_json_string(self):
        """data 字段必须是 JSON 字符串"""
        orchestrator = AgentOrchestrator(
            agent_instances=_make_mock_agents(),
            analysis_id="test_001",
        )
        event = orchestrator._make_event("agent_started", {"agentName": "retriever"})
        assert isinstance(event["data"], str)
        # 能被 json.loads 解析
        parsed = json.loads(event["data"])
        assert parsed["agentName"] == "retriever"

    def test_event_id_is_monotonically_increasing(self):
        """事件 ID 单调递增"""
        orchestrator = AgentOrchestrator(
            agent_instances=_make_mock_agents(),
            analysis_id="test_001",
        )
        ids = []
        for i in range(5):
            event = orchestrator._make_event("test", {"index": i})
            ids.append(int(event["id"]))
        assert ids == sorted(ids)
        assert len(set(ids)) == 5  # 无重复


# ===== FR-004: camelCase payload 测试 =====

class TestSSECamelCasePayload:
    """测试事件 data JSON 解析后字段为 camelCase"""

    def test_agent_started_camelcase(self):
        orchestrator = AgentOrchestrator(
            agent_instances=_make_mock_agents(),
            analysis_id="test_001",
        )
        event = orchestrator._make_event("agent_started", {
            "agentName": "retriever",
            "status": "running",
            "analysisId": "test_001",
        })
        data = json.loads(event["data"])
        assert "agentName" in data
        assert "analysisId" in data
        # snake_case 不应出现
        assert "agent_name" not in data
        assert "analysis_id" not in data

    def test_agent_completed_camelcase(self):
        orchestrator = AgentOrchestrator(
            agent_instances=_make_mock_agents(),
            analysis_id="test_001",
        )
        event = orchestrator._make_event("agent_completed", {
            "agentName": "retriever",
            "status": "completed",
            "progress": 1.0,
            "analysisId": "test_001",
            "intermediateResult": "Found 10 papers",
            "durationMs": 1200,
        })
        data = json.loads(event["data"])
        assert "agentName" in data
        assert "intermediateResult" in data
        assert "durationMs" in data
        assert "intermediate_result" not in data
        assert "duration_ms" not in data

    def test_analysis_completed_camelcase(self):
        orchestrator = AgentOrchestrator(
            agent_instances=_make_mock_agents(),
            analysis_id="test_001",
        )
        event = orchestrator._make_event("analysis_completed", {
            "analysisId": "test_001",
            "status": "completed",
            "finalReport": "## Report",
            "degraded": False,
            "degradedReason": None,
            "totalDurationMs": 5000,
        })
        data = json.loads(event["data"])
        assert "finalReport" in data
        assert "degradedReason" in data
        assert "totalDurationMs" in data
        assert "final_report" not in data
        assert "degraded_reason" not in data
        assert "total_duration_ms" not in data

    def test_error_event_camelcase(self):
        orchestrator = AgentOrchestrator(
            agent_instances=_make_mock_agents(),
            analysis_id="test_001",
        )
        event = orchestrator._make_event("error", {
            "analysisId": "test_001",
            "errorCode": 500,
            "errorMessage": "Agent failed",
        })
        data = json.loads(event["data"])
        assert "errorCode" in data
        assert "errorMessage" in data
        assert "error_code" not in data


# ===== FR-001/FR-002: 事件序列测试 =====

class TestSSEEventSequence:
    """测试正常流程事件序列完整性"""

    @pytest.mark.asyncio
    async def test_normal_flow_event_sequence(self):
        """正常流程：每个 Agent 产生 started → state_update → completed，最后 analysis_completed"""
        agents = _make_mock_agents()
        orchestrator = AgentOrchestrator(
            agent_instances=agents,
            analysis_id="test_seq_001",
        )
        request = AnalyzeRequest(topic="test", userId="u1")

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        event_types = [e["event"] for e in events]

        # 每个 Agent 应有 started + state_update + completed
        for agent_name in ["retriever", "analyzer", "generator"]:
            # 验证 started
            started_events = [
                e for e in events
                if e["event"] == "agent_started"
                and json.loads(e["data"]).get("agentName") == agent_name
            ]
            assert len(started_events) >= 1, f"{agent_name} 缺少 agent_started 事件"

            # 验证 state_update
            update_events = [
                e for e in events
                if e["event"] == "agent_state_update"
                and json.loads(e["data"]).get("agentName") == agent_name
            ]
            assert len(update_events) >= 1, f"{agent_name} 缺少 agent_state_update 事件"

            # 验证 completed
            completed_events = [
                e for e in events
                if e["event"] == "agent_completed"
                and json.loads(e["data"]).get("agentName") == agent_name
            ]
            assert len(completed_events) >= 1, f"{agent_name} 缺少 agent_completed 事件"

        # 最后应有 analysis_completed
        assert "analysis_completed" in event_types

        # analysis_completed 是最后一个事件
        assert event_types[-1] == "analysis_completed"

    @pytest.mark.asyncio
    async def test_analysis_completed_has_final_report(self):
        """analysis_completed 事件含 finalReport"""
        agents = _make_mock_agents()
        orchestrator = AgentOrchestrator(
            agent_instances=agents,
            analysis_id="test_report_001",
        )
        request = AnalyzeRequest(topic="test", userId="u1")

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        final_event = [e for e in events if e["event"] == "analysis_completed"][0]
        data = json.loads(final_event["data"])
        assert "finalReport" in data
        assert data["status"] == "completed"
        assert data["degraded"] is False


# ===== FR-005: Agent 异常不中断流 =====

class TestSSEAgentFailureEvent:
    """测试 Agent 异常时 yield agent_failed + error 事件，不中断流"""

    @pytest.mark.asyncio
    async def test_single_agent_failure_continues(self):
        """单个 Agent 失败不中断流，后续 Agent 继续执行"""
        agents = _make_mock_agents(analyzer_fail=True)
        orchestrator = AgentOrchestrator(
            agent_instances=agents,
            analysis_id="test_fail_001",
        )
        request = AnalyzeRequest(topic="test", userId="u1")

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        event_types = [e["event"] for e in events]

        # 应有 agent_failed 事件
        assert "agent_failed" in event_types

        # 应有 error 事件
        assert "error" in event_types

        # generator 仍应执行
        generator_completed = [
            e for e in events
            if e["event"] == "agent_completed"
            and json.loads(e["data"]).get("agentName") == "generator"
        ]
        assert len(generator_completed) >= 1, "generator 应在 analyzer 失败后继续执行"

        # 最终应为 degraded
        final_event = [e for e in events if e["event"] == "analysis_completed"][0]
        data = json.loads(final_event["data"])
        assert data["status"] == "degraded"
        assert data["degraded"] is True

    @pytest.mark.asyncio
    async def test_agent_failed_event_has_error_message(self):
        """agent_failed 事件含 errorMessage"""
        agents = _make_mock_agents(analyzer_fail=True)
        orchestrator = AgentOrchestrator(
            agent_instances=agents,
            analysis_id="test_errmsg_001",
        )
        request = AnalyzeRequest(topic="test", userId="u1")

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        failed_events = [e for e in events if e["event"] == "agent_failed"]
        assert len(failed_events) >= 1
        # 查找 analyzer 的 failed 事件
        analyzer_failed = [
            e for e in failed_events
            if json.loads(e["data"]).get("agentName") == "analyzer"
        ]
        assert len(analyzer_failed) >= 1
        data = json.loads(analyzer_failed[0]["data"])
        assert "errorMessage" in data

    @pytest.mark.asyncio
    async def test_error_event_has_error_code(self):
        """error 事件含 errorCode"""
        agents = _make_mock_agents(analyzer_fail=True)
        orchestrator = AgentOrchestrator(
            agent_instances=agents,
            analysis_id="test_errcode_001",
        )
        request = AnalyzeRequest(topic="test", userId="u1")

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        error_events = [e for e in events if e["event"] == "error"]
        assert len(error_events) >= 1
        data = json.loads(error_events[0]["data"])
        assert "errorCode" in data
        assert data["errorCode"] == 500

    @pytest.mark.asyncio
    async def test_missing_agent_yields_failed(self):
        """Agent 不存在时 yield agent_failed + error"""
        agents = _make_mock_agents()
        del agents["analyzer"]  # 移除 analyzer
        orchestrator = AgentOrchestrator(
            agent_instances=agents,
            analysis_id="test_missing_001",
        )
        request = AnalyzeRequest(topic="test", userId="u1")

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        # 应有 analyzer 的 agent_failed
        failed_events = [
            e for e in events
            if e["event"] == "agent_failed"
            and json.loads(e["data"]).get("agentName") == "analyzer"
        ]
        assert len(failed_events) >= 1


# ===== FR-006: 全流程超时 =====

class TestSSEWorkflowTimeout:
    """测试全流程超时 120s 触发 error 事件"""

    @pytest.mark.asyncio
    async def test_timeout_yields_error_408(self):
        """模拟超时场景：检查超时后 yield error 事件（errorCode=408）"""
        agents = _make_mock_agents()
        orchestrator = AgentOrchestrator(
            agent_instances=agents,
            analysis_id="test_timeout_001",
        )
        # 模拟已超时（修改 start_time 为 200s 前）
        from datetime import timedelta
        orchestrator._start_time = datetime.now() - timedelta(seconds=200)

        request = AnalyzeRequest(topic="test", userId="u1")

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        event_types = [e["event"] for e in events]

        # 应有 error 事件
        assert "error" in event_types
        error_events = [e for e in events if e["event"] == "error"]
        data = json.loads(error_events[0]["data"])
        assert data["errorCode"] == 408

        # 仍应有 analysis_completed
        assert "analysis_completed" in event_types
        final_data = json.loads(
            [e for e in events if e["event"] == "analysis_completed"][0]["data"]
        )
        assert final_data["status"] == "degraded"


# ===== 端到端 SSE 端点测试 =====

class TestSSEEndpoint:
    """测试 /api/agent/analyze/stream SSE 端点"""

    def test_stream_endpoint_exists(self):
        """SSE 端点存在且可访问"""
        # 注意：由于服务未启动，agent_instances 会失败
        # 但至少验证路由注册正确
        from app.api.router import api_router
        routes = [r.path for r in api_router.routes]
        assert "/agent/analyze/stream" in routes or any(
            "/analyze/stream" in str(r.path) for r in api_router.routes
        )
