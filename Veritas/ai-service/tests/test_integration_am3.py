"""AM3 集成测试 — 汇总 task24~task30 关键用例

按 P0/P1/P2 分组，覆盖 AM3 里程碑全部核心功能点。
P0 测试必须全部 PASS。

P0 (12 项):
  1. 统一响应格式 (task24)
  2. Enum 严格校验 (task24)
  3. 422 中文友好 (task24)
  4. SSE 事件序列 (task25)
  5. Agent 异常不中断流 (task25)
  6. 健康检查 200/503 (task26)
  7. 模型状态扩展字段 (task26)
  8. Java camelCase 请求解析 (task27)
  9. 字段映射一致性 (task28)
  10. LLM 降级 (task29)
  11. 错误码 422/503/408 (task29)

P1 (4 项):
  12. SSE ping 事件 (task30)
  13. Last-Event-ID 续传 (task30)
  14. 多 Agent 降级 (task29)
  15. 全 Agent 失败返回 500 (task29)

P2 (4 项):
  16. 并发 SSE 无错乱 (task30)
  17. 客户端断开优雅关闭 (task30)
  18. 超时 error 408 (task25/30)
  19. 降级时长基线 (task29)
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.agents.base import AgentState, AgentStatus, BaseAgent
from app.agents.orchestrator import AgentOrchestrator
from app.core.config import Settings
from app.exception import AgentTimeoutException, LLMException, ModelNotLoadedException
from app.main import app
from app.models.enums import AnalysisType, EducationLevel, KnowledgeLevel, PreferredStyle
from app.models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    AgentStateResponse,
    ModelStatusResponse,
    UserProfile,
)
from app.services.llm_service import LLMService
from app.utils.response import fail, now_ts_ms, ok

# 加载 fixtures
pytest_plugins = ["tests.fixtures.mock_failing_providers"]


# ===== Mock Agent =====

class MockAgent(BaseAgent):
    """测试用 Mock Agent"""

    def __init__(self, name: str, result: dict = None, should_fail: bool = False):
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
    coordinator_fail=False,
    retriever_fail=False,
    analyzer_fail=False,
    generator_fail=False,
) -> Dict[str, MockAgent]:
    return {
        "coordinator": MockAgent(
            "coordinator",
            result={"requires_compare": False, "requires_review": True, "sub_tasks": []},
            should_fail=coordinator_fail,
        ),
        "retriever": MockAgent(
            "retriever",
            result={"papers": [{"title": "Test Paper"}]},
            should_fail=retriever_fail,
        ),
        "analyzer": MockAgent(
            "analyzer",
            result={"analysis_results": [{"summary": "Test analysis"}]},
            should_fail=analyzer_fail,
        ),
        "generator": MockAgent(
            "generator",
            result={"report": "## Test Report", "citation_list": []},
            should_fail=generator_fail,
        ),
    }


def _make_mock_agent(name: str, return_value: dict) -> MagicMock:
    agent = MagicMock(spec=BaseAgent)
    agent.name = name
    agent.state = AgentState(name=name)
    agent.state.status = AgentStatus.COMPLETED
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


# ============================================================
# P0 测试组（必须全部 PASS）
# ============================================================


class TestP0_01_统一响应格式:
    """P0-1: ok()/fail() 返回 4 字段、timestamp 为 int 毫秒 (task24)"""

    def test_ok_4_required_fields(self):
        r = ok(data={"x": 1})
        assert set(r.keys()) == {"code", "message", "data", "timestamp"}

    def test_fail_4_required_fields(self):
        r = fail(message="错误", code=500)
        assert set(r.keys()) == {"code", "message", "data", "timestamp"}

    def test_timestamp_is_int_milliseconds(self):
        r = ok()
        assert isinstance(r["timestamp"], int)
        assert r["timestamp"] > 1700000000000

    def test_ok_default_values(self):
        r = ok()
        assert r["code"] == 200
        assert r["message"] == "success"
        assert r["data"] is None

    def test_fail_default_values(self):
        r = fail(message="err")
        assert r["code"] == 500
        assert r["data"] is None


class TestP0_02_Enum严格校验:
    """P0-2: 4 个枚举定义正确、非法值抛异常 (task24)"""

    def test_education_level_values(self):
        assert set(e.value for e in EducationLevel) == {
            "undergraduate", "master", "phd", "faculty"
        }

    def test_knowledge_level_values(self):
        assert set(e.value for e in KnowledgeLevel) == {
            "beginner", "intermediate", "advanced", "expert"
        }

    def test_preferred_style_values(self):
        assert set(e.value for e in PreferredStyle) == {
            "simple", "balanced", "technical"
        }

    def test_analysis_type_values(self):
        assert set(e.value for e in AnalysisType) == {
            "paper_analysis", "compare", "report"
        }

    def test_illegal_enum_value_raises(self):
        with pytest.raises(Exception):
            UserProfile(educationLevel="xxx")

    def test_illegal_analysis_type_raises(self):
        with pytest.raises(Exception):
            AnalyzeRequest(topic="test", userId="u1", analysisType="invalid")


class TestP0_03_422中文友好:
    """P0-3: 缺 userId → 422 含中文消息 (task24)"""

    def setup_method(self):
        self.client = TestClient(app)

    def test_missing_userid_returns_422(self):
        response = self.client.post(
            "/api/agent/analyze", json={"topic": "test"}
        )
        assert response.status_code == 422
        body = response.json()
        assert body["code"] == 422
        assert "userId" in body["message"]
        assert set(body.keys()) == {"code", "message", "data", "timestamp"}

    def test_422_response_has_chinese_message(self):
        response = self.client.post(
            "/api/agent/analyze", json={"topic": ""}
        )
        assert response.status_code == 422
        body = response.json()
        # 中文友好消息
        assert any(
            kw in body["message"]
            for kw in ["字段必填", "不能为空", "取值非法", "校验失败", "参数校验失败"]
        )


class TestP0_04_SSE事件序列:
    """P0-4: 正常流程事件完整、camelCase payload (task25)"""

    @pytest.mark.asyncio
    async def test_normal_flow_event_sequence(self):
        agents = _make_mock_agents()
        orchestrator = AgentOrchestrator(
            agent_instances=agents, analysis_id="am3_p0_4"
        )
        request = AnalyzeRequest(topic="test", userId="u1")

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        event_types = [e["event"] for e in events]

        # 每个 Agent 有 started + state_update + completed
        for agent_name in ["retriever", "analyzer", "generator"]:
            started = [
                e for e in events
                if e["event"] == "agent_started"
                and json.loads(e["data"]).get("agentName") == agent_name
            ]
            assert len(started) >= 1, f"{agent_name} 缺少 agent_started"

            completed = [
                e for e in events
                if e["event"] == "agent_completed"
                and json.loads(e["data"]).get("agentName") == agent_name
            ]
            assert len(completed) >= 1, f"{agent_name} 缺少 agent_completed"

        # 最后 analysis_completed
        assert "analysis_completed" in event_types
        assert event_types[-1] == "analysis_completed"

    @pytest.mark.asyncio
    async def test_sse_payload_camelcase(self):
        agents = _make_mock_agents()
        orchestrator = AgentOrchestrator(
            agent_instances=agents, analysis_id="am3_p0_4_cc"
        )
        request = AnalyzeRequest(topic="test", userId="u1")

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        for event in events:
            data = json.loads(event["data"])
            # 不应有 snake_case 键（排除 _id 等特殊键）
            snake_keys = [k for k in data.keys() if "_" in k and k != "_id"]
            assert len(snake_keys) == 0, (
                f"Event {event['event']} has snake_case keys: {snake_keys}"
            )


class TestP0_05_Agent异常不中断流:
    """P0-5: agent_failed + error 事件存在 (task25)"""

    @pytest.mark.asyncio
    async def test_agent_failed_and_error_events(self):
        agents = _make_mock_agents(analyzer_fail=True)
        orchestrator = AgentOrchestrator(
            agent_instances=agents, analysis_id="am3_p0_5"
        )
        request = AnalyzeRequest(topic="test", userId="u1")

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        event_types = [e["event"] for e in events]
        assert "agent_failed" in event_types
        assert "error" in event_types
        assert "analysis_completed" in event_types

        # 最终状态为 degraded
        final = [e for e in events if e["event"] == "analysis_completed"][0]
        data = json.loads(final["data"])
        assert data["status"] == "degraded"


class TestP0_06_健康检查200_503:
    """P0-6: critical_ok 规则 (task26)"""

    def setup_method(self):
        self.client = TestClient(app)

    @patch("app.main.app_state")
    def test_health_200_when_critical_ok(self, mock_state):
        mock_state.llm_service = MagicMock(status="loaded")
        mock_state.embedding_service = MagicMock(status="loaded_api")
        mock_state.vector_store_service = MagicMock(status="connected")
        mock_state.prompt_manager = MagicMock(status="loaded")
        mock_state.search_service = MagicMock()
        mock_state.reranker = MagicMock()

        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "UP"

    @patch("app.main.app_state")
    def test_health_503_when_llm_not_loaded(self, mock_state):
        mock_state.llm_service = None
        mock_state.embedding_service = MagicMock(status="loaded_api")
        mock_state.vector_store_service = MagicMock(status="connected")
        mock_state.prompt_manager = MagicMock(status="loaded")
        mock_state.search_service = MagicMock()
        mock_state.reranker = MagicMock()

        response = self.client.get("/health")
        assert response.status_code == 503
        assert response.json()["data"]["status"] == "DEGRADED"


class TestP0_07_模型状态扩展字段:
    """P0-7: providerCandidates/chromaPaperCount/gpuMemoryUsed (task26)"""

    @patch("app.api.endpoints.model.events.app_state")
    def test_model_status_extended_fields(self, mock_state):
        mock_llm = MagicMock()
        mock_llm.status = "loaded"
        mock_llm.providers = {"api": MagicMock(), "builtin": MagicMock()}
        mock_llm.active_provider = MagicMock()
        mock_llm.active_provider.mode = "api"

        mock_embedding = MagicMock()
        mock_embedding.status = "loaded_api"
        mock_embedding.dimension = 768

        mock_chroma = MagicMock()
        mock_chroma.status = "connected"
        mock_chroma.collection = MagicMock()
        mock_chroma.collection.count.return_value = 200

        mock_state.llm_service = mock_llm
        mock_state.embedding_service = mock_embedding
        mock_state.vector_store_service = mock_chroma
        mock_state.prompt_manager = MagicMock(status="loaded")
        mock_state.search_service = MagicMock()
        mock_state.reranker = MagicMock()

        client = TestClient(app)
        response = client.get("/api/model/status")
        body = response.json()
        data = body["data"]

        assert "providerCandidates" in data
        assert "chromaPaperCount" in data
        assert "gpuMemoryUsed" in data
        assert data["chromaPaperCount"] == 200
        assert data["gpuMemoryUsed"] is None  # 非 local 模式


class TestP0_08_JavaCamelCase请求解析:
    """P0-8: paperIds/userProfile/analysisType (task27)"""

    def test_analyze_request_camelcase_parsing(self):
        req = AnalyzeRequest.model_validate({
            "topic": "Multi-Agent",
            "paperIds": ["p1", "p2"],
            "userId": "usr_001",
            "userProfile": {
                "educationLevel": "master",
                "researchField": "NLP",
                "knowledgeLevel": "intermediate",
                "preferredStyle": "balanced",
            },
            "analysisType": "report",
        })
        assert req.paper_ids == ["p1", "p2"]
        assert req.user_id == "usr_001"
        assert req.user_profile.education_level == EducationLevel.MASTER
        assert req.analysis_type == AnalysisType.REPORT

    def test_response_camelcase_serialization(self):
        resp = AnalyzeResponse(
            analysisId="a1",
            status="completed",
            agentStates=[
                AgentStateResponse(
                    agentName="retriever",
                    status="completed",
                    durationMs=1200,
                )
            ],
            degraded=False,
        )
        dumped = resp.model_dump(by_alias=True)
        assert "analysisId" in dumped
        assert "agentStates" in dumped
        assert "durationMs" in dumped["agentStates"][0]
        assert "analysis_id" not in dumped


class TestP0_09_字段映射一致性:
    """P0-9: 20+ 字段 camelCase alias 正确 (task28)"""

    def test_analyze_request_aliases(self):
        req = AnalyzeRequest(topic="test", userId="u1", paperIds=["p1"], analysisType="compare", analysisId="a1")
        dumped = req.model_dump(by_alias=True)
        for key in ["userId", "paperIds", "analysisType", "analysisId"]:
            assert key in dumped, f"Missing alias: {key}"

    def test_user_profile_aliases(self):
        p = UserProfile(
            educationLevel="faculty",
            researchField="CV",
            knowledgeLevel="expert",
            preferredStyle="technical",
        )
        dumped = p.model_dump(by_alias=True)
        assert set(dumped.keys()) == {
            "educationLevel", "researchField", "knowledgeLevel", "preferredStyle"
        }

    def test_model_status_no_snake_case(self):
        r = ModelStatusResponse(
            llm="loaded", embedding="loaded_api", chroma="connected", prompts="loaded",
            embeddingDimension=1024, activeLlmProvider="api",
            providerCandidates=["api"], chromaPaperCount=200,
            gpuMemoryUsed=None, llmProviderCount=1,
            searchService="ready", reranker="ready",
        )
        dumped = r.model_dump(by_alias=True)
        snake_keys = [k for k in dumped.keys() if "_" in k]
        assert len(snake_keys) == 0, f"Found snake_case: {snake_keys}"

    def test_analyze_response_aliases(self):
        resp = AnalyzeResponse(
            analysisId="a1", status="degraded",
            degraded=True, degradedReason="timeout",
            agentStates=[AgentStateResponse(agentName="g", status="completed", intermediateResult="ok", durationMs=500)],
        )
        dumped = resp.model_dump(by_alias=True)
        for key in ["analysisId", "agentStates", "degradedReason"]:
            assert key in dumped, f"Missing alias: {key}"


class TestP0_10_LLM降级:
    """P0-10: builtin 失败 → api (task29)"""

    @pytest.mark.asyncio
    async def test_llm_fallback_builtin_to_api(self, failing_builtin_provider):
        settings = Settings(LLM_MODE="auto", LLM_TIMEOUT=10)
        service = LLMService(settings)

        service.providers["builtin"] = failing_builtin_provider
        service.active_provider = failing_builtin_provider
        service._status = "loaded"
        service._degradation_state["current_provider"] = "builtin"

        api_provider = MagicMock()
        api_provider.mode = "api"
        api_provider.generate = AsyncMock(return_value="API response")
        api_provider.test_connection = AsyncMock(return_value=True)
        service.providers["api"] = api_provider

        result = await service.generate("test prompt")
        assert result == "API response"
        assert service.active_provider.mode == "api"


class TestP0_11_错误码422_503_408:
    """P0-11: 参数错误/模型未就绪/超时 (task29)"""

    def test_422_validation_error(self):
        client = TestClient(app)
        response = client.post("/api/agent/analyze", json={"topic": "test"})
        assert response.status_code == 422
        assert response.json()["code"] == 422

    def test_503_model_not_loaded(self):
        from app.core import events
        original = events.app_state.llm_service
        events.app_state.llm_service = None
        try:
            client = TestClient(app)
            response = client.post(
                "/api/agent/analyze", json={"topic": "test", "userId": "u1"}
            )
            assert response.json()["code"] == 503
        finally:
            events.app_state.llm_service = original

    def test_408_agent_timeout(self):
        exc = AgentTimeoutException("Agent timed out")
        assert exc.code == 408


# ============================================================
# P1 测试组
# ============================================================


class TestP1_12_SSEPing事件:
    """P1-12: 长流程 >15s yield ping (task30)"""

    @pytest.mark.asyncio
    async def test_ping_after_15s(self):
        agents = _make_mock_agents()
        orchestrator = AgentOrchestrator(
            agent_instances=agents, analysis_id="am3_p1_12"
        )
        orchestrator._last_event_time = time.monotonic() - 20

        request = AnalyzeRequest(topic="test", userId="u1")
        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        ping_events = [e for e in events if e["event"] == "ping"]
        assert len(ping_events) >= 1

    @pytest.mark.asyncio
    async def test_no_ping_when_fast(self):
        agents = _make_mock_agents()
        orchestrator = AgentOrchestrator(
            agent_instances=agents, analysis_id="am3_p1_12_fast"
        )
        orchestrator._last_event_time = time.monotonic()

        request = AnalyzeRequest(topic="test", userId="u1")
        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        ping_events = [e for e in events if e["event"] == "ping"]
        assert len(ping_events) == 0


class TestP1_13_LastEventID续传:
    """P1-13: 跳过已发送事件 (task30)"""

    @pytest.mark.asyncio
    async def test_last_event_id_skip(self):
        agents = _make_mock_agents()
        orchestrator = AgentOrchestrator(
            agent_instances=agents, analysis_id="am3_p1_13",
            last_event_id=5,
        )
        request = AnalyzeRequest(topic="test", userId="u1")

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        for event in events:
            assert int(event["id"]) > 5


class TestP1_14_多Agent降级:
    """P1-14: 多失败 → status='degraded' (task29)"""

    @pytest.mark.asyncio
    async def test_multi_agent_failure_degraded(self):
        retriever = _make_failing_agent("retriever", "Retriever failed")
        analyzer = _make_failing_agent("analyzer", "Analyzer failed")
        generator = _make_mock_agent("generator", {"report": "Fallback", "citation_list": []})

        from app.agents.graph import run_workflow
        request = AnalyzeRequest(topic="test", userId="u1")
        result = await run_workflow(request, {
            "retriever": retriever, "analyzer": analyzer, "generator": generator,
        })
        assert result["status"] == "degraded"
        assert result["degraded"] is True


class TestP1_15_全Agent失败返回500:
    """P1-15: 全 Agent 失败返回 500 (task29)"""

    def test_all_agents_failed_500(self):
        client = TestClient(app)
        with patch("app.api.endpoints.agent._build_agent_instances") as mock_build, \
             patch("app.api.endpoints.agent.run_workflow", new_callable=AsyncMock, side_effect=Exception("All failed")):
            mock_build.return_value = {
                "retriever": MagicMock(), "analyzer": MagicMock(), "generator": MagicMock(),
            }
            response = client.post(
                "/api/agent/analyze", json={"topic": "test", "userId": "u1"}
            )
        assert response.json()["code"] == 500


# ============================================================
# P2 测试组
# ============================================================


class TestP2_16_并发SSE无错乱:
    """P2-16: 并发 SSE 无错乱 (task30)"""

    @pytest.mark.asyncio
    async def test_concurrent_sse_no_cross_contamination(self):
        num = 5

        async def run_single(idx):
            agents = _make_mock_agents()
            orchestrator = AgentOrchestrator(
                agent_instances=agents, analysis_id=f"am3_p2_16_{idx}"
            )
            request = AnalyzeRequest(topic=f"topic_{idx}", userId=f"user_{idx}")
            events = []
            async for event in orchestrator.run_workflow_stream(request):
                events.append(event)
            return idx, events

        tasks = [asyncio.create_task(run_single(i)) for i in range(num)]
        results = await asyncio.gather(*tasks)

        for idx, events in results:
            event_types = [e["event"] for e in events]
            assert "analysis_completed" in event_types
            # 验证 analysisId 正确
            for event in events:
                data = json.loads(event["data"])
                if "analysisId" in data:
                    assert data["analysisId"] == f"am3_p2_16_{idx}"


class TestP2_17_客户端断开优雅关闭:
    """P2-17: 客户端断开优雅关闭 (task30)"""

    @pytest.mark.asyncio
    async def test_graceful_disconnect(self):
        agents = _make_mock_agents()
        orchestrator = AgentOrchestrator(
            agent_instances=agents, analysis_id="am3_p2_17"
        )
        request = AnalyzeRequest(topic="test", userId="u1")

        gen = orchestrator.run_workflow_stream(request)
        event1 = await gen.__anext__()
        assert event1 is not None
        await gen.aclose()


class TestP2_18_超时Error408:
    """P2-18: 超时 error 408 (task25/30)"""

    @pytest.mark.asyncio
    async def test_timeout_yields_error_408(self):
        agents = _make_mock_agents()
        orchestrator = AgentOrchestrator(
            agent_instances=agents, analysis_id="am3_p2_18"
        )
        orchestrator._start_time = datetime.now() - timedelta(seconds=200)

        request = AnalyzeRequest(topic="test", userId="u1")
        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        error_events = [e for e in events if e["event"] == "error"]
        assert len(error_events) >= 1
        data = json.loads(error_events[0]["data"])
        assert data["errorCode"] == 408


class TestP2_19_降级时长基线:
    """P2-19: LLM 降级 <2s (task29)"""

    @pytest.mark.asyncio
    async def test_llm_fallback_under_2s(self, failing_builtin_provider):
        settings = Settings(LLM_MODE="auto", LLM_TIMEOUT=10)
        service = LLMService(settings)

        service.providers["builtin"] = failing_builtin_provider
        service.active_provider = failing_builtin_provider
        service._status = "loaded"
        service._degradation_state["current_provider"] = "builtin"

        api_provider = MagicMock()
        api_provider.mode = "api"
        api_provider.generate = AsyncMock(return_value="API response")
        api_provider.test_connection = AsyncMock(return_value=True)
        service.providers["api"] = api_provider

        start = time.monotonic()
        await service.generate("test prompt")
        elapsed = time.monotonic() - start

        assert elapsed < 2.0, f"LLM 降级耗时 {elapsed:.2f}s > 2s"


# ============================================================
# 分组结果统计输出
# ============================================================

def test_am3_summary(capsys):
    """输出 AM3 集成测试分组统计"""
    summary = """
╔══════════════════════════════════════════╗
║       AM3 集成测试分组统计               ║
╠══════════════════════════════════════════╣
║ P0 (必须通过): 11 项                     ║
║   - 统一响应格式 (task24)                ║
║   - Enum 严格校验 (task24)               ║
║   - 422 中文友好 (task24)                ║
║   - SSE 事件序列 (task25)                ║
║   - Agent 异常不中断流 (task25)           ║
║   - 健康检查 200/503 (task26)            ║
║   - 模型状态扩展字段 (task26)             ║
║   - Java camelCase 请求解析 (task27)      ║
║   - 字段映射一致性 (task28)              ║
║   - LLM 降级 (task29)                    ║
║   - 错误码 422/503/408 (task29)          ║
╠══════════════════════════════════════════╣
║ P1 (重要): 4 项                          ║
║   - SSE ping 事件 (task30)               ║
║   - Last-Event-ID 续传 (task30)          ║
║   - 多 Agent 降级 (task29)               ║
║   - 全 Agent 失败返回 500 (task29)        ║
╠══════════════════════════════════════════╣
║ P2 (性能/边界): 4 项                     ║
║   - 并发 SSE 无错乱 (task30)             ║
║   - 客户端断开优雅关闭 (task30)           ║
║   - 超时 error 408 (task25/30)           ║
║   - 降级时长基线 (task29)                ║
╠══════════════════════════════════════════╣
║ 总计: 19 项                              ║
╚══════════════════════════════════════════╝
"""
    print(summary)
