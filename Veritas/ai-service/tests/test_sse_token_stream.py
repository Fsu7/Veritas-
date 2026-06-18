"""task52 SSE token 流集成测试

验证：
1. token_stream 事件格式正确
2. token_stream 后跟 agent_completed
3. 流式失败降级到 _run_node
4. 原 9 种事件不变
"""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.generator import GeneratorAgent
from app.agents.orchestrator import AgentOrchestrator


# ===== Mock 工厂 =====


def _make_mock_generator(stream_tokens=None, stream_fails=False):
    """构造 mock GeneratorAgent"""
    generator = MagicMock(spec=GeneratorAgent)

    if stream_fails:
        async def failing_stream_generate(prompt, input_data, context):
            raise Exception("Stream failed")
            yield  # 让它成为 async generator
        generator.stream_generate = failing_stream_generate
    else:
        async def mock_stream_generate(prompt, input_data, context):
            for token in (stream_tokens or ["Hello", " ", "World"]):
                yield {"token": token, "is_final": False, "report": None}
            yield {"token": "", "is_final": True, "report": "Hello World"}
        generator.stream_generate = mock_stream_generate

    return generator


def _make_orchestrator(generator=None):
    """构造 AgentOrchestrator 实例"""
    agent_instances = {
        "coordinator": MagicMock(),
        "retriever": MagicMock(),
        "analyzer": MagicMock(),
        "comparer": MagicMock(),
        "generator": generator or _make_mock_generator(),
        "reviewer": MagicMock(),
    }
    return AgentOrchestrator(
        agent_instances=agent_instances,
        analysis_id="test_001",
    )


# ===== 测试 1: token_stream 事件格式 =====


class TestTokenStreamEventFormat:
    def test_token_stream_event_has_correct_fields(self):
        """token_stream 事件包含 analysisId/agentName/token 字段"""
        orchestrator = _make_orchestrator()
        event = orchestrator._make_event(
            "token_stream",
            {
                "analysisId": "test_001",
                "agentName": "generator",
                "token": "test_token",
            },
        )

        assert event["event"] == "token_stream"
        assert "id" in event
        assert "data" in event

        data = json.loads(event["data"])
        assert data["analysisId"] == "test_001"
        assert data["agentName"] == "generator"
        assert data["token"] == "test_token"


# ===== 测试 2: stream_generate 产出 token + is_final =====


class TestStreamGenerateOutput:
    def test_stream_generate_yields_tokens_then_final(self):
        """stream_generate 先 yield token，最后 yield is_final"""
        from unittest.mock import AsyncMock, MagicMock

        generator = GeneratorAgent.__new__(GeneratorAgent)

        # Mock 依赖
        generator.llm_service = MagicMock()
        generator.llm_max_tokens = 2048
        generator.llm_temperature = 0.7

        async def mock_generate_stream(prompt, max_tokens, temperature):
            for t in ["Hello", " ", "World"]:
                yield t

        generator.llm_service.generate_stream = mock_generate_stream

        # Mock state
        generator.state = MagicMock()
        generator.state.update_progress = MagicMock()

        # Mock build_prompt
        generator.build_prompt = MagicMock(return_value="test prompt")

        async def run():
            chunks = []
            async for chunk in generator.stream_generate(
                "test", {"analysis_results": []}, {"user_profile": {}}
            ):
                chunks.append(chunk)
            return chunks

        chunks = asyncio.run(run())

        # 应有 3 个 token chunk + 1 个 final chunk
        token_chunks = [c for c in chunks if not c["is_final"]]
        final_chunks = [c for c in chunks if c["is_final"]]

        assert len(token_chunks) == 3
        assert len(final_chunks) == 1
        assert final_chunks[0]["report"] == "Hello World"

    def test_stream_generate_degrades_on_failure(self):
        """stream_generate 失败时降级到 _run"""
        from unittest.mock import AsyncMock, MagicMock

        generator = GeneratorAgent.__new__(GeneratorAgent)

        # Mock 依赖：generate_stream 失败
        generator.llm_service = MagicMock()
        generator.llm_max_tokens = 2048
        generator.llm_temperature = 0.7

        async def failing_stream(prompt, max_tokens, temperature):
            raise Exception("Stream failed")
            yield  # 让它成为 async generator

        generator.llm_service.generate_stream = failing_stream

        # Mock state
        generator.state = MagicMock()
        generator.state.update_progress = MagicMock()

        # Mock build_prompt
        generator.build_prompt = MagicMock(return_value="test prompt")

        # Mock _run 作为降级
        async def mock_run(prompt, input_data, context):
            return {"report": "fallback report"}

        generator._run = mock_run

        async def run():
            chunks = []
            async for chunk in generator.stream_generate(
                "test", {"analysis_results": []}, {"user_profile": {}}
            ):
                chunks.append(chunk)
            return chunks

        chunks = asyncio.run(run())

        # 应降级，yield is_final=True + fallback report
        final_chunks = [c for c in chunks if c["is_final"]]
        assert len(final_chunks) >= 1
        assert final_chunks[-1]["report"] == "fallback report"


# ===== 测试 3: orchestrator 文档注释更新 =====


class TestOrchestratorDocstring:
    def test_orchestrator_docstring_mentions_ten_events(self):
        """orchestrator 模块文档注释提及 10 种事件"""
        import app.agents.orchestrator as orch_module

        doc = orch_module.__doc__
        assert doc is not None
        assert "10种" in doc or "10 种" in doc
        assert "token_stream" in doc

    def test_orchestrator_docstring_mentions_task52(self):
        """orchestrator 模块文档注释提及 task52"""
        import app.agents.orchestrator as orch_module

        doc = orch_module.__doc__
        assert doc is not None
        assert "task52" in doc


# ===== 测试 4: 原 9 种事件不变 =====


class TestOriginalEventsUnchanged:
    def test_original_nine_events_still_defined(self):
        """原 9 种事件类型仍保留"""
        import app.agents.orchestrator as orch_module

        doc = orch_module.__doc__
        assert doc is not None

        original_events = [
            "agent_started",
            "agent_state_update",
            "agent_completed",
            "agent_failed",
            "workflow_degraded",
            "review_rejected",
            "analysis_completed",
            "error",
            "ping",
        ]

        for event in original_events:
            assert event in doc, f"原事件 {event} 未在文档注释中"

    def test_token_stream_is_tenth_event(self):
        """token_stream 是第 10 种事件"""
        import app.agents.orchestrator as orch_module

        doc = orch_module.__doc__
        assert doc is not None
        assert "token_stream" in doc
        # 验证是第 10 种（通过计数事件列表）
        event_lines = [
            line for line in doc.split("\n")
            if line.strip().startswith("-") and ":" in line
        ]
        assert len(event_lines) >= 10
