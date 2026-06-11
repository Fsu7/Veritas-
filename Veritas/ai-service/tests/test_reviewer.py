"""test_reviewer — ReviewerAgent 单元测试"""
import json
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.reviewer import ReviewerAgent


@pytest.fixture
def mock_llm_service():
    service = AsyncMock()
    service.generate = AsyncMock(return_value="")
    return service


@pytest.fixture
def mock_prompt_manager():
    pm = MagicMock()
    pm.get_prompt = MagicMock(return_value="Review prompt for testing")
    return pm


@pytest.fixture
def reviewer_agent(mock_llm_service, mock_prompt_manager):
    return ReviewerAgent(
        llm_service=mock_llm_service,
        prompt_manager=mock_prompt_manager,
    )


class TestReviewerAgentCreation:
    """测试 ReviewerAgent 实例化"""

    def test_creation(self, reviewer_agent):
        assert reviewer_agent.name == "reviewer"
        assert reviewer_agent.llm_temperature == 0.3
        assert reviewer_agent.llm_max_tokens == 2048

    def test_inherits_base_agent(self, reviewer_agent):
        from app.agents.base import BaseAgent
        assert isinstance(reviewer_agent, BaseAgent)


class TestReviewerBuildPrompt:
    """测试 build_prompt() 方法"""

    def test_build_prompt_with_data(self, reviewer_agent, mock_prompt_manager):
        input_data = {
            "report": "## 引言\n综述内容...",
            "original_papers": [{"title": "Paper1", "year": 2023}],
        }
        context = {"user_profile": {}}

        prompt = reviewer_agent.build_prompt(input_data, context)

        mock_prompt_manager.get_prompt.assert_called_once()
        call_args = mock_prompt_manager.get_prompt.call_args
        assert call_args[0][0] == "reviewer" or call_args[1].get("agent_name") == "reviewer"

    def test_build_prompt_with_retry_context(self, reviewer_agent, mock_prompt_manager):
        input_data = {
            "report": "综述内容",
            "original_papers": [],
            "retry_context": "上次审核发现引用不准确",
        }
        context = {}

        reviewer_agent.build_prompt(input_data, context)

        call_args = mock_prompt_manager.get_prompt.call_args
        assert "retry_context" in call_args[1] or (len(call_args[0]) > 1 and "retry_context" in str(call_args))

    def test_build_prompt_empty_papers(self, reviewer_agent, mock_prompt_manager):
        input_data = {"report": "综述", "original_papers": []}
        context = {}

        reviewer_agent.build_prompt(input_data, context)

        call_args = mock_prompt_manager.get_prompt.call_args
        if len(call_args[0]) > 1:
            assert "无" in str(call_args[0]) or "无" in str(call_args[1])


class TestReviewerRunApproved:
    """测试审核通过场景"""

    @pytest.mark.asyncio
    async def test_run_approved(self, reviewer_agent, mock_llm_service):
        approved_json = json.dumps({
            "review_result": "通过",
            "fact_check": [
                {"claim": "Transformer是2017年提出的", "source": "Vaswani et al., 2017", "accurate": True, "note": "正确"},
            ],
            "citation_check": {
                "total_citations": 3,
                "accurate_citations": 3,
                "inaccurate_citations": [],
                "accuracy_rate": 1.0,
            },
            "suggestions": [],
        })
        mock_llm_service.generate = AsyncMock(return_value=approved_json)

        result = await reviewer_agent._run(
            "prompt",
            {"report": "综述内容", "original_papers": []},
            {},
        )

        assert result["approved"] is True
        assert result["fact_accuracy"] == 1.0
        assert result["citation_accuracy"] == 1.0

    @pytest.mark.asyncio
    async def test_run_approved_by_accuracy(self, reviewer_agent, mock_llm_service):
        """验证通过准确率判定通过"""
        approved_json = json.dumps({
            "review_result": "需修改",
            "fact_check": [
                {"claim": "A", "accurate": True},
                {"claim": "B", "accurate": True},
                {"claim": "C", "accurate": True},
                {"claim": "D", "accurate": True},
                {"claim": "E", "accurate": True},
                {"claim": "F", "accurate": True},
                {"claim": "G", "accurate": True},
                {"claim": "H", "accurate": True},
                {"claim": "I", "accurate": True},
                {"claim": "J", "accurate": False},
            ],
            "citation_check": {
                "total_citations": 10,
                "accurate_citations": 10,
                "accuracy_rate": 1.0,
            },
            "suggestions": [],
        })
        mock_llm_service.generate = AsyncMock(return_value=approved_json)

        result = await reviewer_agent._run(
            "prompt",
            {"report": "综述", "original_papers": []},
            {},
        )

        assert result["approved"] is True
        assert result["fact_accuracy"] == 0.9


class TestReviewerRunRejected:
    """测试审核不通过场景"""

    @pytest.mark.asyncio
    async def test_run_rejected(self, reviewer_agent, mock_llm_service):
        rejected_json = json.dumps({
            "review_result": "需修改",
            "fact_check": [
                {"claim": "错误论断", "source": "无", "accurate": False, "note": "与原文不符", "error_type": "factual_error"},
            ],
            "citation_check": {
                "total_citations": 5,
                "accurate_citations": 2,
                "inaccurate_citations": [
                    {"citation": "[Fake, 2020]", "issue": "引用不存在", "error_type": "citation_error"},
                ],
                "accuracy_rate": 0.4,
            },
            "suggestions": [
                {"section": "研究现状", "issue": "论断不准确", "suggestion": "修正论断", "error_type": "factual_error"},
            ],
        })
        mock_llm_service.generate = AsyncMock(return_value=rejected_json)

        result = await reviewer_agent._run(
            "prompt",
            {"report": "综述", "original_papers": []},
            {},
        )

        assert result["approved"] is False
        assert len(result["issues"]) >= 1
        assert len(result["suggestions"]) >= 1
        assert result["citation_accuracy"] == 0.4


class TestReviewerJsonParseFallback:
    """测试4级JSON解析降级"""

    @pytest.mark.asyncio
    async def test_parse_json_code_block(self, reviewer_agent, mock_llm_service):
        """验证从```json代码块提取"""
        output = '```json\n{"review_result": "通过", "fact_check": [], "citation_check": {"accuracy_rate": 1.0}, "suggestions": []}\n```'
        mock_llm_service.generate = AsyncMock(return_value=output)

        result = await reviewer_agent._run(
            "prompt",
            {"report": "综述", "original_papers": []},
            {},
        )

        assert result["approved"] is True

    @pytest.mark.asyncio
    async def test_parse_plain_json(self, reviewer_agent, mock_llm_service):
        """验证纯JSON文本解析"""
        output = '{"review_result": "需修改", "fact_check": [], "citation_check": {"accuracy_rate": 0.5}, "suggestions": []}'
        mock_llm_service.generate = AsyncMock(return_value=output)

        result = await reviewer_agent._run(
            "prompt",
            {"report": "综述", "original_papers": []},
            {},
        )

        assert result["approved"] is False

    @pytest.mark.asyncio
    async def test_parse_non_standard_json(self, reviewer_agent, mock_llm_service):
        """验证非标准JSON（带前后文字）解析"""
        output = '审核结果如下：\n{"review_result": "通过", "fact_check": [], "citation_check": {"accuracy_rate": 1.0}, "suggestions": []}\n以上是审核结果。'
        mock_llm_service.generate = AsyncMock(return_value=output)

        result = await reviewer_agent._run(
            "prompt",
            {"report": "综述", "original_papers": []},
            {},
        )

        assert result["approved"] is True

    @pytest.mark.asyncio
    async def test_parse_garbled_output(self, reviewer_agent, mock_llm_service):
        """验证完全无法解析时的规则兜底"""
        mock_llm_service.generate = AsyncMock(return_value="这是一段无法解析的文本，没有JSON格式。")

        result = await reviewer_agent._run(
            "prompt",
            {"report": "综述", "original_papers": []},
            {},
        )

        assert result["approved"] is False
        assert result.get("degraded") is not True


class TestReviewerTimeoutFallback:
    """测试超时降级"""

    @pytest.mark.asyncio
    async def test_timeout_fallback(self, reviewer_agent, mock_llm_service):
        """验证超时后返回降级结果"""
        mock_llm_service.generate = AsyncMock(side_effect=asyncio.TimeoutError())

        result = await reviewer_agent.execute(
            input_data={"report": "综述", "original_papers": []},
            context={},
        )

        assert result.get("degraded") is True or result.get("approved") is False

    @pytest.mark.asyncio
    async def test_llm_failure_fallback(self, reviewer_agent, mock_llm_service):
        """验证LLM调用失败时的降级"""
        mock_llm_service.generate = AsyncMock(side_effect=Exception("LLM service error"))

        result = await reviewer_agent._run(
            "prompt",
            {"report": "综述", "original_papers": []},
            {},
        )

        assert result["approved"] is False
        assert result["degraded"] is True


class TestReviewerAccuracyCalculation:
    """测试审核通过条件判定逻辑"""

    def test_determine_approval_explicit_pass(self, reviewer_agent):
        parsed = {"review_result": "通过", "fact_check": [], "citation_check": {}}
        assert reviewer_agent._determine_approval(parsed) is True

    def test_determine_approval_by_accuracy(self, reviewer_agent):
        parsed = {
            "review_result": "需修改",
            "fact_check": [
                {"accurate": True}] * 10,
            "citation_check": {"accuracy_rate": 0.95},
        }
        assert reviewer_agent._determine_approval(parsed) is True

    def test_determine_approval_low_fact_accuracy(self, reviewer_agent):
        parsed = {
            "review_result": "需修改",
            "fact_check": [
                {"accurate": True}] * 8 + [{"accurate": False}] * 2,
            "citation_check": {"accuracy_rate": 0.95},
        }
        assert reviewer_agent._determine_approval(parsed) is False

    def test_determine_approval_low_citation_accuracy(self, reviewer_agent):
        parsed = {
            "review_result": "需修改",
            "fact_check": [{"accurate": True}] * 10,
            "citation_check": {"accuracy_rate": 0.85},
        }
        assert reviewer_agent._determine_approval(parsed) is False

    def test_determine_approval_both_low(self, reviewer_agent):
        parsed = {
            "review_result": "需修改",
            "fact_check": [{"accurate": True}] * 5 + [{"accurate": False}] * 5,
            "citation_check": {"accuracy_rate": 0.5},
        }
        assert reviewer_agent._determine_approval(parsed) is False

    def test_fact_accuracy_boundary_90(self, reviewer_agent):
        """验证事实准确率恰好90%时通过"""
        parsed = {
            "review_result": "需修改",
            "fact_check": [{"accurate": True}] * 9 + [{"accurate": False}] * 1,
            "citation_check": {"accuracy_rate": 1.0},
        }
        assert reviewer_agent._determine_approval(parsed) is True

    def test_fact_accuracy_boundary_below_90(self, reviewer_agent):
        """验证事实准确率略低于90%时不通过"""
        parsed = {
            "review_result": "需修改",
            "fact_check": [{"accurate": True}] * 8 + [{"accurate": False}] * 2,
            "citation_check": {"accuracy_rate": 1.0},
        }
        assert reviewer_agent._determine_approval(parsed) is False
