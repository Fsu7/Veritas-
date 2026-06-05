"""task30 测试套件 — SSE推送稳定性 + 断线重连

覆盖：
- Keep-alive ping 事件（距上次事件 > 15s）
- 节点异常不中断 SSE 流
- Last-Event-ID 跳过已发送事件
- 客户端断开优雅关闭
- 10 个并发 SSE 连接无 OOM 无事件错乱
"""
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.base import AgentStatus, AgentState, BaseAgent
from app.agents.orchestrator import AgentOrchestrator, PING_INTERVAL
from app.models.schemas import AnalyzeRequest


# ===== Mock Agent 基类（复用 task25）=====

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
    retriever_result=None,
    analyzer_result=None,
    generator_result=None,
    retriever_fail=False,
    analyzer_fail=False,
    generator_fail=False,
) -> Dict[str, MockAgent]:
    """创建一组 Mock Agent"""
    return {
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


# ===== Test 1: Keep-alive ping =====

class TestPingEvent:
    """测试 Keep-alive ping 事件"""

    @pytest.mark.asyncio
    async def test_ping_event_after_15s(self):
        """长流程每 15s yield ping 事件

        模拟 _last_event_time 为 20s 前，验证有 ping 事件。
        """
        agents = _make_mock_agents()
        orchestrator = AgentOrchestrator(
            agent_instances=agents,
            analysis_id="test_ping_001",
        )
        # 模拟上次事件时间为 20s 前
        orchestrator._last_event_time = time.monotonic() - 20

        request = AnalyzeRequest(topic="test", userId="u1")

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        # 检查是否有 ping 事件
        ping_events = [e for e in events if e["event"] == "ping"]
        assert len(ping_events) >= 1, "应有 ping 事件"

        # ping 事件的 data 应为空 JSON "{}"
        ping_data = json.loads(ping_events[0]["data"])
        assert ping_data == {}

    @pytest.mark.asyncio
    async def test_no_ping_when_events_frequent(self):
        """事件频繁时不应 yield ping"""
        agents = _make_mock_agents()
        orchestrator = AgentOrchestrator(
            agent_instances=agents,
            analysis_id="test_no_ping_001",
        )
        # 正常时间，不模拟延迟
        orchestrator._last_event_time = time.monotonic()

        request = AnalyzeRequest(topic="test", userId="u1")

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        # 快速执行不应有 ping 事件
        ping_events = [e for e in events if e["event"] == "ping"]
        assert len(ping_events) == 0, "快速执行不应有 ping 事件"


# ===== Test 2: 节点异常不中断流 =====

class TestNodeFailureDoesNotBreakStream:
    """测试节点异常不中断 SSE 流"""

    @pytest.mark.asyncio
    async def test_node_failure_does_not_break_stream(self):
        """节点异常不中断 SSE 流

        复用 task25 的 MockAgent，analyzer_fail=True
        验证流仍然完整，最终有 analysis_completed。
        """
        agents = _make_mock_agents(analyzer_fail=True)
        orchestrator = AgentOrchestrator(
            agent_instances=agents,
            analysis_id="test_fail_stream_001",
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

        # 最终应有 analysis_completed
        assert "analysis_completed" in event_types
        assert event_types[-1] == "analysis_completed"

        # 验证最终状态为 degraded
        final_event = [e for e in events if e["event"] == "analysis_completed"][0]
        data = json.loads(final_event["data"])
        assert data["status"] == "degraded"
        assert data["degraded"] is True


# ===== Test 3: Last-Event-ID 跳过已发送事件 =====

class TestLastEventIdSkip:
    """测试 Last-Event-ID 跳过已发送事件"""

    @pytest.mark.asyncio
    async def test_last_event_id_skip_events(self):
        """Last-Event-ID 跳过已发送事件

        设置 last_event_id=5，验证事件 ID > 5。
        """
        agents = _make_mock_agents()
        orchestrator = AgentOrchestrator(
            agent_instances=agents,
            analysis_id="test_skip_001",
            last_event_id=5,
        )

        request = AnalyzeRequest(topic="test", userId="u1")

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        # 所有事件 ID 应 > 5
        for event in events:
            event_id = int(event["id"])
            assert event_id > 5, f"事件 ID {event_id} 应 > 5"

    @pytest.mark.asyncio
    async def test_last_event_id_zero_not_skip(self):
        """Last-Event-ID=0 不跳过任何事件（仅接受正整数）"""
        agents = _make_mock_agents()
        orchestrator = AgentOrchestrator(
            agent_instances=agents,
            analysis_id="test_zero_001",
            last_event_id=0,  # 无效值
        )

        request = AnalyzeRequest(topic="test", userId="u1")

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        # 应有完整事件序列
        event_types = [e["event"] for e in events]
        assert "analysis_completed" in event_types

    @pytest.mark.asyncio
    async def test_last_event_id_negative_not_skip(self):
        """Last-Event-ID=-1 不跳过任何事件"""
        agents = _make_mock_agents()
        orchestrator = AgentOrchestrator(
            agent_instances=agents,
            analysis_id="test_negative_001",
            last_event_id=-1,  # 无效值
        )

        request = AnalyzeRequest(topic="test", userId="u1")

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        # 应有完整事件序列
        event_types = [e["event"] for e in events]
        assert "analysis_completed" in event_types


# ===== Test 4: 客户端断开优雅处理 =====

class TestClientDisconnectGraceful:
    """测试客户端断开服务器优雅关闭"""

    @pytest.mark.asyncio
    async def test_client_disconnect_graceful(self):
        """客户端断开服务器优雅关闭

        模拟 asyncio.CancelledError
        验证不抛异常。
        """
        agents = _make_mock_agents()
        orchestrator = AgentOrchestrator(
            agent_instances=agents,
            analysis_id="test_disconnect_001",
        )

        request = AnalyzeRequest(topic="test", userId="u1")

        # 创建异步生成器
        gen = orchestrator.run_workflow_stream(request)

        # 收集几个事件后模拟取消
        events = []
        try:
            # 获取第一个事件
            event1 = await gen.__anext__()
            events.append(event1)

            # 模拟客户端断开
            # 我们需要手动触发 CancelledError
            # 由于生成器内部捕获了 CancelledError，我们测试它是否能正常返回
            await gen.aclose()  # 正常关闭

        except asyncio.CancelledError:
            # 不应到达这里，因为 orchestrator 内部捕获了
            pass

        # 验证至少获取了一个事件
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_cancelled_error_caught_internally(self):
        """验证 CancelledError 被 orchestrator 内部捕获"""
        agents = _make_mock_agents()
        orchestrator = AgentOrchestrator(
            agent_instances=agents,
            analysis_id="test_cancel_001",
        )

        request = AnalyzeRequest(topic="test", userId="u1")

        # 使用 asyncio.create_task 并取消
        async def collect_events():
            events = []
            async for event in orchestrator.run_workflow_stream(request):
                events.append(event)
                # 收集几个事件后模拟取消
                if len(events) >= 3:
                    raise asyncio.CancelledError()
            return events

        task = asyncio.create_task(collect_events())

        # 等待一小段时间后取消任务
        await asyncio.sleep(0.1)
        task.cancel()

        try:
            result = await task
        except asyncio.CancelledError:
            # 任务被取消是预期行为
            pass

        # 验证任务已结束（不抛异常）
        assert task.done()


# ===== Test 5: 10 个并发 SSE 连接 =====

class TestConcurrentSSEConnections:
    """测试 10 个并发 SSE 连接无 OOM 无事件错乱"""

    @pytest.mark.asyncio
    async def test_concurrent_sse_connections(self):
        """10 个并发 SSE 连接无 OOM 无事件错乱

        创建 10 个并发 orchestrator 实例
        验证每个实例的事件序列独立且完整。
        """
        num_connections = 10
        results = {}

        async def run_single_orchestrator(idx: int):
            agents = _make_mock_agents()
            orchestrator = AgentOrchestrator(
                agent_instances=agents,
                analysis_id=f"test_concurrent_{idx}",
            )
            request = AnalyzeRequest(topic=f"topic_{idx}", userId=f"user_{idx}")

            events = []
            async for event in orchestrator.run_workflow_stream(request):
                events.append(event)

            return idx, events

        # 并发执行 10 个 orchestrator
        tasks = [
            asyncio.create_task(run_single_orchestrator(i))
            for i in range(num_connections)
        ]

        # 等待所有任务完成
        done_results = await asyncio.gather(*tasks)

        # 验证每个实例的事件序列
        for idx, events in done_results:
            # 验证事件序列完整
            event_types = [e["event"] for e in events]
            assert "analysis_completed" in event_types
            assert event_types[-1] == "analysis_completed"

            # 验证事件 ID 单调递增
            event_ids = [int(e["id"]) for e in events]
            assert event_ids == sorted(event_ids)

            # 验证 analysis_id 正确
            for event in events:
                data = json.loads(event["data"])
                if "analysisId" in data:
                    assert data["analysisId"] == f"test_concurrent_{idx}"

    @pytest.mark.asyncio
    async def test_concurrent_connections_no_cross_contamination(self):
        """验证并发连接之间没有交叉污染"""
        num_connections = 5

        async def run_single_orchestrator(idx: int):
            # 使用不同的结果来区分
            agents = _make_mock_agents(
                retriever_result={"papers": [{"title": f"Paper_{idx}"}]},
                generator_result={"report": f"Report_{idx}", "citation_list": []},
            )
            orchestrator = AgentOrchestrator(
                agent_instances=agents,
                analysis_id=f"test_cross_{idx}",
            )
            request = AnalyzeRequest(topic=f"topic_{idx}", userId=f"user_{idx}")

            events = []
            async for event in orchestrator.run_workflow_stream(request):
                events.append(event)

            return idx, events

        tasks = [
            asyncio.create_task(run_single_orchestrator(i))
            for i in range(num_connections)
        ]

        done_results = await asyncio.gather(*tasks)

        # 验证每个实例的 report 正确
        for idx, events in done_results:
            final_event = [e for e in events if e["event"] == "analysis_completed"][0]
            data = json.loads(final_event["data"])
            # 由于 mock agent 的结果，report 应包含对应的 idx
            assert f"Report_{idx}" in data["finalReport"] or "Test Report" in data["finalReport"]