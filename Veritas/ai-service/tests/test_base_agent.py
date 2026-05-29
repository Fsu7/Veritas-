import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.base import AgentStatus, AgentState, BaseAgent


class ConcreteAgent(BaseAgent):

    async def _run(self, prompt: str, input_data: dict, context: dict) -> dict:
        return {"result": "ok", "prompt": prompt}

    def build_prompt(self, input_data: dict, context: dict) -> str:
        return f"prompt for {input_data.get('topic', 'unknown')}"


class SlowAgent(BaseAgent):

    async def _run(self, prompt: str, input_data: dict, context: dict) -> dict:
        await asyncio.sleep(10)
        return {"result": "should not reach"}

    def build_prompt(self, input_data: dict, context: dict) -> str:
        return "slow prompt"


class FailingAgent(BaseAgent):

    async def _run(self, prompt: str, input_data: dict, context: dict) -> dict:
        raise ValueError("intentional test error")

    def build_prompt(self, input_data: dict, context: dict) -> str:
        return "failing prompt"


def _make_mock_services():
    llm = MagicMock()
    pm = MagicMock()
    return llm, pm


class TestAgentStatusEnum:

    def test_status_values(self):
        assert AgentStatus.WAITING == "waiting"
        assert AgentStatus.RUNNING == "running"
        assert AgentStatus.COMPLETED == "completed"
        assert AgentStatus.FAILED == "failed"

    def test_status_json_serialization(self):
        result = json.dumps(AgentStatus.RUNNING)
        assert result == '"running"'

    def test_status_str_output(self):
        assert str(AgentStatus.WAITING) == "AgentStatus.WAITING"
        assert AgentStatus.WAITING.value == "waiting"

    def test_status_is_str(self):
        assert isinstance(AgentStatus.COMPLETED, str)
        assert AgentStatus.COMPLETED == "completed"


class TestAgentState:

    def test_creation_defaults(self):
        state = AgentState(name="retriever")
        assert state.name == "retriever"
        assert state.status == AgentStatus.WAITING
        assert state.started_at is None
        assert state.completed_at is None
        assert state.duration_ms is None
        assert state.progress == 0.0
        assert state.intermediate_result is None
        assert state.error is None

    def test_to_dict(self):
        now = datetime(2026, 5, 29, 10, 0, 0)
        state = AgentState(
            name="analyzer",
            status=AgentStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            duration_ms=1500,
            progress=1.0,
            intermediate_result="done",
        )
        d = state.to_dict()
        assert d["name"] == "analyzer"
        assert d["status"] == "completed"
        assert d["started_at"] == "2026-05-29T10:00:00"
        assert d["completed_at"] == "2026-05-29T10:00:00"
        assert d["duration_ms"] == 1500
        assert d["progress"] == 1.0
        assert d["intermediate_result"] == "done"
        assert d["error"] is None

    def test_to_dict_none_datetime(self):
        state = AgentState(name="retriever")
        d = state.to_dict()
        assert d["started_at"] is None
        assert d["completed_at"] is None

    def test_to_dict_json_serializable(self):
        now = datetime(2026, 5, 29, 10, 0, 0)
        state = AgentState(
            name="test",
            status=AgentStatus.RUNNING,
            started_at=now,
        )
        json_str = json.dumps(state.to_dict())
        assert "running" in json_str
        assert "2026-05-29" in json_str

    def test_update_progress(self):
        state = AgentState(name="retriever")
        state.update_progress(0.5, "found 5 papers")
        assert state.progress == 0.5
        assert state.intermediate_result == "found 5 papers"

    def test_update_progress_without_intermediate(self):
        state = AgentState(name="retriever")
        state.update_progress(0.3)
        assert state.progress == 0.3
        assert state.intermediate_result is None


class TestBaseAgentCannotInstantiate:

    def test_cannot_instantiate_abc(self):
        llm, pm = _make_mock_services()
        with pytest.raises(TypeError):
            BaseAgent(name="test", llm_service=llm, prompt_manager=pm)

    def test_subclass_without_run_cannot_instantiate(self):
        llm, pm = _make_mock_services()

        class IncompleteAgent(BaseAgent):
            def build_prompt(self, input_data, context):
                return ""

        with pytest.raises(TypeError):
            IncompleteAgent(name="test", llm_service=llm, prompt_manager=pm)

    def test_subclass_without_build_prompt_cannot_instantiate(self):
        llm, pm = _make_mock_services()

        class IncompleteAgent(BaseAgent):
            async def _run(self, prompt, input_data, context):
                return {}

        with pytest.raises(TypeError):
            IncompleteAgent(name="test", llm_service=llm, prompt_manager=pm)


class TestBaseAgentExecuteSuccess:

    @pytest.mark.asyncio
    async def test_execute_success_flow(self):
        llm, pm = _make_mock_services()
        agent = ConcreteAgent(name="test_agent", llm_service=llm, prompt_manager=pm, timeout=30)

        result = await agent.execute({"topic": "AI"}, {})

        assert result["result"] == "ok"
        assert agent.state.status == AgentStatus.COMPLETED
        assert agent.state.started_at is not None
        assert agent.state.completed_at is not None
        assert agent.state.duration_ms is not None
        assert agent.state.duration_ms >= 0
        assert agent.state.intermediate_result is not None

    @pytest.mark.asyncio
    async def test_execute_status_transitions(self):
        llm, pm = _make_mock_services()
        agent = ConcreteAgent(name="test_agent", llm_service=llm, prompt_manager=pm)

        assert agent.state.status == AgentStatus.WAITING

        await agent.execute({"topic": "test"}, {})

        assert agent.state.status == AgentStatus.COMPLETED


class TestBaseAgentExecuteTimeout:

    @pytest.mark.asyncio
    async def test_execute_timeout_returns_fallback(self):
        llm, pm = _make_mock_services()
        agent = SlowAgent(name="slow_agent", llm_service=llm, prompt_manager=pm, timeout=1)

        result = await agent.execute({}, {})

        assert result["degraded"] is True
        assert result["agent"] == "slow_agent"
        assert "timed out" in result["error"]
        assert agent.state.status == AgentStatus.FAILED

    @pytest.mark.asyncio
    async def test_execute_timeout_no_exception_raised(self):
        llm, pm = _make_mock_services()
        agent = SlowAgent(name="slow_agent", llm_service=llm, prompt_manager=pm, timeout=1)

        result = await agent.execute({}, {})
        assert "degraded" in result


class TestBaseAgentExecuteException:

    @pytest.mark.asyncio
    async def test_execute_exception_returns_fallback(self):
        llm, pm = _make_mock_services()
        agent = FailingAgent(name="fail_agent", llm_service=llm, prompt_manager=pm)

        result = await agent.execute({}, {})

        assert result["degraded"] is True
        assert result["agent"] == "fail_agent"
        assert "intentional test error" in result["error"]
        assert agent.state.status == AgentStatus.FAILED
        assert agent.state.error is not None

    @pytest.mark.asyncio
    async def test_execute_exception_no_propagation(self):
        llm, pm = _make_mock_services()
        agent = FailingAgent(name="fail_agent", llm_service=llm, prompt_manager=pm)

        result = await agent.execute({}, {})
        assert isinstance(result, dict)


class TestFallbackResultFormat:

    def test_fallback_result_structure(self):
        llm, pm = _make_mock_services()
        agent = ConcreteAgent(name="my_agent", llm_service=llm, prompt_manager=pm)
        agent.state.error = "something went wrong"

        result = agent._fallback_result({})

        assert result["degraded"] is True
        assert result["agent"] == "my_agent"
        assert result["error"] == "something went wrong"

    def test_fallback_result_with_input_data(self):
        llm, pm = _make_mock_services()
        agent = ConcreteAgent(name="test", llm_service=llm, prompt_manager=pm)
        agent.state.error = "timeout"

        result = agent._fallback_result({"topic": "AI"})
        assert result["degraded"] is True


class TestSummarizeResultTruncation:

    def test_short_result_not_truncated(self):
        llm, pm = _make_mock_services()
        agent = ConcreteAgent(name="test", llm_service=llm, prompt_manager=pm)

        short_result = {"key": "value"}
        summary = agent._summarize_result(short_result)
        assert len(summary) <= 200
        assert "key" in summary

    def test_long_result_truncated(self):
        llm, pm = _make_mock_services()
        agent = ConcreteAgent(name="test", llm_service=llm, prompt_manager=pm)

        long_result = {"data": "x" * 500}
        summary = agent._summarize_result(long_result)
        assert len(summary) <= 200

    def test_empty_result(self):
        llm, pm = _make_mock_services()
        agent = ConcreteAgent(name="test", llm_service=llm, prompt_manager=pm)

        summary = agent._summarize_result({})
        assert len(summary) <= 200
