"""Task29 降级机制验证测试 — 8 个用例

覆盖 3 层降级：
- LLM 级：builtin→api 降级、三路全失败 503
- Agent/Workflow 级：超时跳过继续、多 Agent 失败 degraded、全失败 500
- 错误码验证：422 参数错误、503 模型未就绪、408 Agent 超时
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.agents.base import AgentState, AgentStatus, BaseAgent
from app.agents.graph import run_workflow
from app.agents.orchestrator import AgentOrchestrator
from app.core.config import Settings
from app.exception import (
    AgentTimeoutException,
    LLMException,
    ModelNotLoadedException,
)
from app.main import app
from app.models.schemas import AnalyzeRequest
from app.services.llm_service import LLMService

# 加载 fixtures
pytest_plugins = ["tests.fixtures.mock_failing_providers"]


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


# ===== Test 1: LLM builtin → api 降级 =====


class TestLLMProviderFallback:
    """LLM Provider 降级测试"""

    @pytest.mark.asyncio
    async def test_llm_provider_fallback_builtin_to_api(
        self, failing_builtin_provider
    ):
        """builtin 失败 → api 降级

        - 使用 mock_failing_providers 让 builtin provider 抛 ConnectionError
        - 验证 LLMService 自动切换到 api provider
        - 验证 active_provider.mode == 'api'
        """
        settings = Settings(LLM_MODE="auto", LLM_TIMEOUT=10)
        service = LLMService(settings)

        # 设置 failing builtin provider 为当前活跃 provider
        service.providers["builtin"] = failing_builtin_provider
        service.active_provider = failing_builtin_provider
        service._status = "loaded"
        service._degradation_state["current_provider"] = "builtin"

        # 创建 working api provider
        api_provider = MagicMock()
        api_provider.mode = "api"
        api_provider.generate = AsyncMock(return_value="API fallback response")
        api_provider.test_connection = AsyncMock(return_value=True)
        service.providers["api"] = api_provider

        # 调用 generate，应该降级到 api
        result = await service.generate("test prompt")

        assert result == "API fallback response"
        assert service.active_provider.mode == "api"
        assert service._degradation_state["current_provider"] == "api"
        assert service._degradation_state["fallback_count"] == 1


# ===== Test 2: 三路全失败 → LLMException(503) =====


class TestLLMAllProvidersFailed:
    """LLM 三路全失败测试"""

    @pytest.mark.asyncio
    async def test_llm_all_providers_failed_throws_503(
        self, failing_all_providers
    ):
        """三路全失败 → LLMException(503)

        - mock builtin/api/local 均抛异常
        - 验证 LLMException.code == 503
        - 验证 message 含 'All LLM providers failed'
        """
        settings = Settings(LLM_MODE="auto", LLM_TIMEOUT=10)
        service = LLMService(settings)

        # 设置所有 provider 都失败
        for name, provider in failing_all_providers.items():
            service.providers[name] = provider

        service.active_provider = failing_all_providers["builtin"]
        service._status = "loaded"
        service._degradation_state["current_provider"] = "builtin"

        # 调用 generate，应该抛出 LLMException(503)
        with pytest.raises(LLMException) as exc_info:
            await service.generate("test prompt")

        assert exc_info.value.code == 503
        assert "All LLM providers failed" in exc_info.value.message


# ===== Test 3: Analyzer 超时 → Generator 继续 =====


class TestAgentTimeoutSkipContinue:
    """Agent 超时跳过继续测试"""

    @pytest.mark.asyncio
    async def test_agent_timeout_skip_continue(self, timeout_agent):
        """Analyzer 超时 → Generator 继续

        - 使用 mock Agent 让 analyzer 执行超时
        - 验证 generator 仍执行
        - 验证 response.status == 'degraded'
        """
        # 创建 mock retriever
        retriever = _make_mock_agent(
            "retriever", {"papers": [{"paper_id": "p1"}], "total_found": 1}
        )

        # 使用 timeout_agent 作为 analyzer
        analyzer = timeout_agent

        # 创建 mock generator
        generator = _make_mock_agent(
            "generator",
            {"report": "Generated report", "citation_list": []},
        )

        agent_instances = {
            "retriever": retriever,
            "analyzer": analyzer,
            "generator": generator,
        }

        request = AnalyzeRequest(
            topic="Multi-Agent",
            user_id="usr_001",
            analysis_id="anl_timeout_test",
        )

        orchestrator = AgentOrchestrator(
            agent_instances=agent_instances,
            analysis_id="anl_timeout_test",
        )

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        # 验证 generator 仍执行
        generator.execute.assert_called_once()

        # 验证有 agent_failed 事件（analyzer 超时）
        failed_events = [e for e in events if e["event"] == "agent_failed"]
        assert len(failed_events) >= 1
        assert any("analyzer" in e["data"] for e in failed_events)

        # 验证最终 status 为 degraded
        completed_events = [
            e for e in events if e["event"] == "analysis_completed"
        ]
        assert len(completed_events) == 1
        final_data = json.loads(completed_events[0]["data"])
        assert final_data["status"] == "degraded"


# ===== Test 4: 多 Agent 失败 → status='degraded' =====


class TestWorkflowMultiAgentFailureDegraded:
    """Workflow 多 Agent 失败降级测试"""

    @pytest.mark.asyncio
    async def test_workflow_multi_agent_failure_degraded(self):
        """retriever + analyzer 都失败 → status='degraded'

        - retriever + analyzer 都失败
        - 验证 generator 仍输出 report
        - 验证 status == 'degraded'
        """
        # 创建失败的 retriever 和 analyzer
        retriever = _make_failing_agent("retriever", "Retriever failed")
        analyzer = _make_failing_agent("analyzer", "Analyzer failed")

        # 创建成功的 generator
        generator = _make_mock_agent(
            "generator",
            {"report": "Fallback report", "citation_list": []},
        )

        agent_instances = {
            "retriever": retriever,
            "analyzer": analyzer,
            "generator": generator,
        }

        request = AnalyzeRequest(
            topic="Multi-Agent",
            user_id="usr_001",
            analysis_id="anl_multi_fail_test",
        )

        result = await run_workflow(request, agent_instances)

        # 验证 generator 仍输出 report
        assert result["report"] is not None

        # 验证 status == 'degraded'
        assert result["status"] == "degraded"
        assert result["degraded"] is True

        # 验证有 2 个错误
        assert len(result["errors"]) >= 2


# ===== Test 5: 全部失败 → 500 =====


class TestWorkflowAllAgentsFailed:
    """Workflow 全部 Agent 失败测试"""

    def test_workflow_all_agents_failed_returns_500(self):
        """全部失败 → 500

        - 3 个 Agent 全失败
        - 验证 response.code == 500
        """
        client = TestClient(app)

        with patch(
            "app.api.endpoints.agent._build_agent_instances"
        ) as mock_build, patch(
            "app.api.endpoints.agent.run_workflow",
            new_callable=AsyncMock,
            side_effect=Exception("All agents failed"),
        ) as mock_workflow:
            mock_build.return_value = {
                "retriever": MagicMock(),
                "analyzer": MagicMock(),
                "generator": MagicMock(),
            }

            response = client.post(
                "/api/agent/analyze",
                json={"topic": "test", "userId": "usr_001"},
            )

        body = response.json()
        assert body["code"] == 500
        # 验证统一响应格式
        assert set(body.keys()) == {"code", "message", "data", "timestamp"}


# ===== Test 6: 参数错误 → 422 =====


class TestValidationError422:
    """参数校验 422 测试"""

    def test_validation_error_422(self):
        """参数错误 → 422

        - 缺 userId / topic 为空 / 非法枚举值
        - 验证 422 + 统一格式
        """
        client = TestClient(app)

        # 缺 userId
        response = client.post(
            "/api/agent/analyze", json={"topic": "test"}
        )
        assert response.status_code == 422
        body = response.json()
        assert body["code"] == 422
        assert "userId" in body["message"]
        assert set(body.keys()) == {"code", "message", "data", "timestamp"}

        # topic 为空
        response = client.post(
            "/api/agent/analyze", json={"topic": "", "userId": "u1"}
        )
        assert response.status_code == 422
        body = response.json()
        assert body["code"] == 422
        assert "topic" in body["message"]

        # 非法枚举值
        response = client.post(
            "/api/agent/analyze",
            json={"topic": "test", "userId": "u1", "analysisType": "xxx"},
        )
        assert response.status_code == 422
        body = response.json()
        assert body["code"] == 422
        assert "analysisType" in body["message"]


# ===== Test 7: 模型未就绪 → 503 =====


class TestModelNotLoaded503:
    """模型未就绪 503 测试"""

    def test_model_not_loaded_503(self):
        """模型未就绪 → 503

        - llm_service=None
        - 验证 503 + 统一格式
        """
        from app.core import events

        # 保存原始状态
        original_llm = events.app_state.llm_service
        original_pm = events.app_state.prompt_manager
        original_ss = events.app_state.search_service

        # 设置 llm_service = None
        events.app_state.llm_service = None
        events.app_state.prompt_manager = None
        events.app_state.search_service = None

        try:
            client = TestClient(app)
            response = client.post(
                "/api/agent/analyze",
                json={"topic": "test", "userId": "usr_001"},
            )

            body = response.json()
            assert body["code"] == 503
            assert set(body.keys()) == {"code", "message", "data", "timestamp"}
        finally:
            # 恢复原始状态
            events.app_state.llm_service = original_llm
            events.app_state.prompt_manager = original_pm
            events.app_state.search_service = original_ss


# ===== Test 8: Agent 超时 → 408 =====


class TestAgentTimeout408:
    """Agent 超时 408 测试"""

    def test_agent_timeout_408(self):
        """Agent 超时 → 408

        - 验证 AgentTimeoutException.code == 408
        """
        exc = AgentTimeoutException("Agent analyzer timed out after 30s")
        assert exc.code == 408
        assert "timed out" in exc.message


# ===== Task 43: 降级机制增强测试 =====


class TestShouldDegradeWorkflow:
    """验证 _should_degrade_workflow() 辅助函数"""

    def test_no_errors_returns_false(self):
        from app.agents.graph import _should_degrade_workflow
        state = {"errors": []}
        assert _should_degrade_workflow(state) is False

    def test_one_error_returns_false(self):
        from app.agents.graph import _should_degrade_workflow
        state = {"errors": [{"agent": "retriever", "error": "timeout"}]}
        assert _should_degrade_workflow(state) is False

    def test_two_errors_returns_true(self):
        from app.agents.graph import _should_degrade_workflow
        state = {"errors": [
            {"agent": "retriever", "error": "timeout"},
            {"agent": "analyzer", "error": "failed"},
        ]}
        assert _should_degrade_workflow(state) is True


class TestWorkflowStateDegradationFields:
    """验证 WorkflowState 新增降级字段"""

    def test_initial_state_has_degradation_fields(self):
        from app.agents.graph import WorkflowState
        # 验证 TypedDict 包含新字段（通过类型注解检查）
        annotations = WorkflowState.__annotations__
        assert "degraded_agents" in annotations
        assert "degradation_level" in annotations


class TestRetrieveNodeDegradedResult:
    """验证 retrieve_node 降级处理"""

    @pytest.mark.asyncio
    async def test_retrieve_node_degraded_updates_degraded_agents(self):
        from app.agents.graph import retrieve_node
        # mock retriever 返回 degraded 结果
        mock_agent = MagicMock(spec=BaseAgent)
        mock_agent.name = "retriever"
        mock_agent.state = AgentState(name="retriever")
        mock_agent.state.status = AgentStatus.COMPLETED
        mock_agent.execute = AsyncMock(return_value={
            "papers": [],
            "degraded": True,
            "error": "retriever degraded",
        })

        state = {
            "query": "test",
            "user_profile": {},
            "errors": [],
            "degraded_agents": [],
            "agent_states": {},
        }
        result = await retrieve_node(state, {"retriever": mock_agent})
        assert "retriever" in result.get("degraded_agents", [])
        assert result.get("degraded") is True


class TestReviewNodeAutoApproveOnDegradation:
    """验证 review_node 降级时自动通过"""

    @pytest.mark.asyncio
    async def test_review_node_degraded_auto_approves(self):
        from app.agents.graph import review_node
        mock_agent = MagicMock(spec=BaseAgent)
        mock_agent.name = "reviewer"
        mock_agent.state = AgentState(name="reviewer")
        mock_agent.state.status = AgentStatus.COMPLETED
        mock_agent.execute = AsyncMock(return_value={
            "approved": False,
            "issues": [{"claim": "test issue"}],
            "suggestions": [],
            "citation_accuracy": 0.5,
            "fact_accuracy": 0.5,
            "degraded": True,
            "error": "reviewer degraded",
        })

        state = {
            "report": "Test report",
            "search_results": [],
            "review_result": None,
            "regenerate_count": 0,
            "errors": [],
            "degraded_agents": [],
            "agent_states": {},
        }
        result = await review_node(state, {"reviewer": mock_agent})
        assert result["review_result"]["approved"] is True
        assert "reviewer" in result.get("degraded_agents", [])


class TestGenerateNodeFallbackReport:
    """验证 generate_node 降级时返回非空报告"""

    @pytest.mark.asyncio
    async def test_generate_node_degraded_returns_nonempty_report(self):
        from app.agents.graph import generate_node
        mock_agent = MagicMock(spec=BaseAgent)
        mock_agent.name = "generator"
        mock_agent.state = AgentState(name="generator")
        mock_agent.state.status = AgentStatus.COMPLETED
        mock_agent.execute = AsyncMock(return_value={
            "report": "综述生成过程中发生降级，返回部分结果。",
            "citation_list": [],
            "degraded": True,
            "error": "generator degraded",
        })

        state = {
            "analysis_results": [],
            "compare_result": None,
            "review_result": None,
            "regenerate_count": 0,
            "errors": [],
            "degraded_agents": [],
            "agent_states": {},
        }
        result = await generate_node(state, {"generator": mock_agent})
        assert result.get("report") is not None
        assert len(result.get("report", "")) > 0
        assert "generator" in result.get("degraded_agents", [])


class TestOrchestratorWorkflowDegradedEvent:
    """验证 orchestrator workflow_degraded SSE 事件"""

    @pytest.mark.asyncio
    async def test_workflow_degraded_event_on_multi_agent_failure(self):
        # 创建两个失败的 Agent
        failing_retriever = _make_failing_agent("retriever", "Retriever failed")
        failing_analyzer = _make_failing_agent("analyzer", "Analyzer failed")
        mock_generator = _make_mock_agent(
            "generator", {"report": "Fallback report", "citation_list": []}
        )

        agent_instances = {
            "retriever": failing_retriever,
            "analyzer": failing_analyzer,
            "generator": mock_generator,
        }

        request = AnalyzeRequest(
            topic="Multi-Agent",
            user_id="usr_001",
            analysis_id="anl_wf_degraded_test",
        )

        orchestrator = AgentOrchestrator(
            agent_instances=agent_instances,
            analysis_id="anl_wf_degraded_test",
        )

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        # 验证 workflow_degraded 事件存在
        degraded_events = [e for e in events if e["event"] == "workflow_degraded"]
        assert len(degraded_events) >= 1

        # 验证事件数据包含必要字段
        degraded_data = json.loads(degraded_events[0]["data"])
        assert "degradedAgents" in degraded_data
        assert "reason" in degraded_data
        assert "fallbackMode" in degraded_data


class TestOrchestratorAgentFailedWithDegradationInfo:
    """验证 agent_failed 事件包含降级信息"""

    @pytest.mark.asyncio
    async def test_agent_failed_contains_degradation_info(self):
        failing_agent = _make_failing_agent("analyzer", "Analyzer crashed")
        mock_retriever = _make_mock_agent(
            "retriever", {"papers": [{"paper_id": "p1"}], "total_found": 1}
        )
        mock_generator = _make_mock_agent(
            "generator", {"report": "Report", "citation_list": []}
        )

        agent_instances = {
            "retriever": mock_retriever,
            "analyzer": failing_agent,
            "generator": mock_generator,
        }

        request = AnalyzeRequest(
            topic="Test",
            user_id="usr_001",
            analysis_id="anl_failed_info_test",
        )

        orchestrator = AgentOrchestrator(
            agent_instances=agent_instances,
            analysis_id="anl_failed_info_test",
        )

        events = []
        async for event in orchestrator.run_workflow_stream(request):
            events.append(event)

        # 验证 agent_failed 事件包含 errorType/degraded/fallback
        failed_events = [e for e in events if e["event"] == "agent_failed"]
        assert len(failed_events) >= 1
        failed_data = json.loads(failed_events[0]["data"])
        assert "errorType" in failed_data
        assert failed_data.get("degraded") is True
        assert "fallback" in failed_data


class TestDegradedResultNotEmpty:
    """验证任何降级场景下 report 不为空"""

    @pytest.mark.asyncio
    async def test_degraded_workflow_returns_nonempty_report(self):
        failing_retriever = _make_failing_agent("retriever", "Retriever failed")
        failing_analyzer = _make_failing_agent("analyzer", "Analyzer failed")
        mock_generator = _make_mock_agent(
            "generator", {"report": "Fallback report", "citation_list": []}
        )

        agent_instances = {
            "retriever": failing_retriever,
            "analyzer": failing_analyzer,
            "generator": mock_generator,
        }

        request = AnalyzeRequest(
            topic="Multi-Agent",
            user_id="usr_001",
            analysis_id="anl_nonempty_test",
        )

        result = await run_workflow(request, agent_instances)
        assert result.get("report") is not None
        assert len(result.get("report", "")) > 0
