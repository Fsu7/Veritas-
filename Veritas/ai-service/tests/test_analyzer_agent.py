import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.analyzer import DEFAULT_DIMENSIONS, FALLBACK_NOTE, AnalyzerAgent
from app.agents.base import AgentStatus, BaseAgent


def _make_mock_services():
    llm = AsyncMock()
    pm = MagicMock()
    pm.get_prompt = MagicMock(return_value="analyzer prompt for $paper_title")
    ps = MagicMock()
    ps.get_extra_instruction = MagicMock(return_value="")
    return llm, pm, ps


SAMPLE_PAPERS = [
    {
        "paper_id": "arxiv_2024_001",
        "title": "Attention Is All You Need",
        "abstract": "The dominant sequence transduction models are based on complex recurrent "
        "or convolutional neural networks. We propose a new simple network architecture, "
        "the Transformer, based solely on attention mechanisms. Experiments on two machine "
        "translation tasks show these models to be superior in quality while being more "
        "parallelizable. Our model achieves 28.4 BLEU on WMT 2014 English-to-German "
        "translation. We also show the Transformer generalizes well to English constituency "
        "parsing. The paper discusses the limitations of the approach including computational "
        "cost on long sequences and suggests future work.",
    },
    {
        "paper_id": "arxiv_2024_002",
        "title": "BERT: Pre-training of Deep Bidirectional Transformers",
        "abstract": "We introduce a new language representation model called BERT. Unlike recent "
        "language representation models, BERT is designed to pre-train deep bidirectional "
        "representations. The pre-trained BERT model can be fine-tuned with just one "
        "additional output layer to create state-of-the-art models for a wide range of tasks. "
        "BERT obtains new state-of-the-art results on eleven natural language processing tasks. "
        "We demonstrate the effectiveness of our approach through extensive experiments and "
        "ablation studies. The paper acknowledges the limitation of high computational cost "
        "during pre-training and the need for large amounts of data.",
    },
    {
        "paper_id": "arxiv_2024_003",
        "title": "GPT-4 Technical Report",
        "abstract": "We report the development of GPT-4, a large multimodal model that exhibits "
        "human-level performance on various professional and academic benchmarks. GPT-4 is a "
        "Transformer-based model pre-trained to predict the next token in a document. The "
        "post-training alignment process results in improved performance on factuality and "
        "adherence to the desired behavior. A core component of this approach is the RLHF "
        "method. We discuss the limitations and risks associated with the deployment of "
        "large language models.",
    },
]

VALID_ANALYSIS_JSON = json.dumps({
    "research_problem": {
        "summary": "论文要解决序列转导模型中循环/卷积网络计算效率低、难以并行化的问题...",
        "confidence": 0.92,
        "references": ["The dominant sequence transduction models..."],
    },
    "core_method": {
        "summary": "提出Transformer架构，完全基于注意力机制，摒弃循环和卷积...",
        "confidence": 0.95,
        "references": ["We propose a new simple network architecture..."],
    },
    "main_experiments": {
        "summary": "在WMT 2014英德和英法翻译任务上验证，使用BLEU评估指标...",
        "confidence": 0.88,
        "references": ["Experiments on two machine translation tasks..."],
    },
    "core_conclusions": {
        "summary": "Transformer在翻译质量上超越已有模型，且更易并行化...",
        "confidence": 0.90,
        "references": ["Our model achieves 28.4 BLEU..."],
    },
    "limitations": {
        "summary": "长序列上的计算成本较高，自注意力复杂度为O(n²)...",
        "confidence": 0.80,
        "references": ["The paper discusses the limitations..."],
    },
})

PARTIAL_ANALYSIS_JSON = json.dumps({
    "research_problem": {
        "summary": "论文研究深度双向预训练语言模型...",
        "confidence": 0.90,
        "references": ["We introduce a new language representation model..."],
    },
    "core_method": {
        "summary": "提出BERT模型，采用掩码语言建模和下一句预测...",
        "confidence": 0.88,
        "references": ["BERT is designed to pre-train deep bidirectional..."],
    },
    "main_experiments": {
        "summary": "在11个NLP任务上验证，取得SOTA结果...",
        "confidence": 0.85,
        "references": ["BERT obtains new state-of-the-art results..."],
    },
    "core_conclusions": {
        "summary": "双向预训练显著提升下游任务表现...",
        "confidence": 0.82,
        "references": ["We demonstrate the effectiveness..."],
    },
})

MALFORMED_OUTPUT = "抱歉，我无法分析这篇论文，因为摘要信息不足以进行深度分析。"

VALID_ANALYSIS_WITH_CODE_BLOCK = f"```json\n{VALID_ANALYSIS_JSON}\n```"

VALID_ANALYSIS_WITH_PLAIN_BLOCK = f"```\n{VALID_ANALYSIS_JSON}\n```"

VALID_ANALYSIS_WRAPPED = f"以下是分析结果：\n{VALID_ANALYSIS_JSON}\n以上分析仅供参考。"

EMPTY_DIMENSIONS = {dim: None for dim in DEFAULT_DIMENSIONS}


class TestAnalyzerAgentInit:

    def test_inherits_base_agent(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        assert isinstance(agent, BaseAgent)

    def test_name_is_analyzer(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        assert agent.name == "analyzer"

    def test_default_timeout(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        assert agent.timeout >= 0


class TestBuildPrompt:

    def test_build_prompt_calls_prompt_manager(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        result = agent.build_prompt(
            {"paper_title": "Test Title", "paper_abstract": "Test Abstract"}, {}
        )

        pm.get_prompt.assert_called_once_with(
            "analyzer",
            paper_title="Test Title",
            paper_abstract="Test Abstract",
            extra_instruction="",
        )
        assert result == "analyzer prompt for $paper_title"

    def test_build_prompt_with_user_profile(self):
        llm, pm, ps = _make_mock_services()
        agent = AnalyzerAgent(
            llm_service=llm, prompt_manager=pm, personalization_service=ps
        )
        context = {
            "user_profile": {
                "knowledge_level": "advanced",
                "education_level": "phd",
            }
        }

        result = agent.build_prompt(
            {"paper_title": "Test", "paper_abstract": "Abstract"}, context
        )

        call_kwargs = pm.get_prompt.call_args.kwargs
        assert call_kwargs["paper_title"] == "Test"
        assert call_kwargs["paper_abstract"] == "Abstract"
        assert "研究空白" in call_kwargs["extra_instruction"]


class TestGetExtraInstruction:

    def test_beginner(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)
        context = {"user_profile": {"knowledge_level": "beginner"}}

        result = agent._get_extra_instruction(context)

        assert "通俗解释" in result

    def test_intermediate(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)
        context = {"user_profile": {"knowledge_level": "intermediate"}}

        result = agent._get_extra_instruction(context)

        assert "方法对比" in result

    def test_advanced(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)
        context = {"user_profile": {"knowledge_level": "advanced"}}

        result = agent._get_extra_instruction(context)

        assert "研究空白" in result

    def test_expert(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)
        context = {"user_profile": {"knowledge_level": "expert"}}

        result = agent._get_extra_instruction(context)

        assert "前沿洞察" in result

    def test_none_profile(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        result = agent._get_extra_instruction({"user_profile": None})

        assert result == ""

    def test_no_knowledge_level(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)
        context = {"user_profile": {"education_level": "master"}}

        result = agent._get_extra_instruction(context)

        assert result == ""


class TestRunSuccessFlow:

    @pytest.mark.asyncio
    async def test_run_with_3_papers(self):
        llm, pm, _ = _make_mock_services()
        llm.generate = AsyncMock(return_value=VALID_ANALYSIS_JSON)
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        result = await agent._run(
            "prompt",
            {"papers": SAMPLE_PAPERS},
            {},
        )

        assert len(result["analysis_results"]) == 3
        assert result["degraded_papers"] == []
        assert result["total_analyzed"] == 3
        assert 0.0 < result["extraction_quality"] <= 1.0

    @pytest.mark.asyncio
    async def test_run_progress_updates(self):
        llm, pm, _ = _make_mock_services()
        llm.generate = AsyncMock(return_value=VALID_ANALYSIS_JSON)
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        await agent._run(
            "prompt",
            {"papers": SAMPLE_PAPERS},
            {},
        )

        assert agent.state.progress == 1.0
        assert "Analyzed 3 papers" in agent.state.intermediate_result

    @pytest.mark.asyncio
    async def test_run_result_structure(self):
        llm, pm, _ = _make_mock_services()
        llm.generate = AsyncMock(return_value=VALID_ANALYSIS_JSON)
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        result = await agent._run(
            "prompt",
            {"papers": [SAMPLE_PAPERS[0]]},
            {},
        )

        analysis = result["analysis_results"][0]
        for dim in DEFAULT_DIMENSIONS:
            assert dim in analysis
            assert "summary" in analysis[dim]
            assert "confidence" in analysis[dim]
            assert "references" in analysis[dim]
        assert "analysis_id" in analysis
        assert "paper_id" in analysis
        assert "ai_disclaimer" in analysis


class TestRunDegradation:

    @pytest.mark.asyncio
    async def test_single_paper_llm_failure_continues(self):
        llm, pm, _ = _make_mock_services()
        call_count = [0]

        async def mock_generate(prompt, max_tokens=2048, temperature=0.7):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("LLM error on second paper")
            return VALID_ANALYSIS_JSON

        llm.generate = mock_generate
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        result = await agent._run(
            "prompt",
            {"papers": SAMPLE_PAPERS},
            {},
        )

        assert result["total_analyzed"] == 3
        assert len(result["degraded_papers"]) == 1
        success_analysis = result["analysis_results"][0]
        assert success_analysis["degraded"] is False
        degraded_analysis = result["analysis_results"][1]
        assert degraded_analysis["degraded"] is True
        assert degraded_analysis["extraction_quality"] == 0.1

    @pytest.mark.asyncio
    async def test_all_papers_llm_failure(self):
        llm, pm, _ = _make_mock_services()
        llm.generate = AsyncMock(side_effect=Exception("LLM unavailable"))
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        result = await agent._run(
            "prompt",
            {"papers": SAMPLE_PAPERS},
            {},
        )

        assert len(result["analysis_results"]) == 3
        assert len(result["degraded_papers"]) == 3
        for ar in result["analysis_results"]:
            assert ar["degraded"] is True
            assert ar["extraction_quality"] == 0.1

    @pytest.mark.asyncio
    async def test_run_with_empty_papers(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        result = await agent._run("prompt", {"papers": []}, {})

        assert result["analysis_results"] == []
        assert result["degraded_papers"] == []
        assert result["total_analyzed"] == 0
        assert result["extraction_quality"] == 0.0


class TestParseAnalysisResult:

    def test_parse_valid_json(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        result = agent._parse_analysis_result(VALID_ANALYSIS_JSON)

        assert "research_problem" in result
        assert "core_method" in result
        assert "main_experiments" in result
        assert "core_conclusions" in result
        assert "limitations" in result
        assert result["research_problem"]["confidence"] == 0.92

    def test_parse_json_with_code_block(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        result = agent._parse_analysis_result(VALID_ANALYSIS_WITH_CODE_BLOCK)

        assert "research_problem" in result
        assert "core_method" in result

    def test_parse_json_with_plain_code_block(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        result = agent._parse_analysis_result(VALID_ANALYSIS_WITH_PLAIN_BLOCK)

        assert "research_problem" in result

    def test_parse_malformed_output_fallback(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        result = agent._parse_analysis_result(MALFORMED_OUTPUT, SAMPLE_PAPERS[0])

        for dim in DEFAULT_DIMENSIONS:
            assert dim in result
            assert "summary" in result[dim]
            assert "confidence" in result[dim]
        assert result["extraction_quality"] == 0.1

    def test_parse_empty_string_fallback(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        result = agent._parse_analysis_result("", SAMPLE_PAPERS[0])

        for dim in DEFAULT_DIMENSIONS:
            assert dim in result

    def test_parse_json_wrapped_in_text(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        result = agent._parse_analysis_result(VALID_ANALYSIS_WRAPPED)

        assert "research_problem" in result
        assert result["core_method"]["confidence"] == 0.95

    def test_parse_malformed_without_paper_returns_empty(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        result = agent._parse_analysis_result(MALFORMED_OUTPUT)

        assert result == EMPTY_DIMENSIONS


class TestValidateDimensions:

    def test_missing_dimension_filled(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)
        parsed = json.loads(PARTIAL_ANALYSIS_JSON)

        result = agent._validate_dimensions(parsed, SAMPLE_PAPERS[1])

        for dim in DEFAULT_DIMENSIONS:
            assert dim in result
            assert "summary" in result[dim]
            assert "confidence" in result[dim]
            assert "references" in result[dim]
        assert result["limitations"]["summary"] == FALLBACK_NOTE
        assert result["limitations"]["confidence"] == 0.3

    def test_confidence_clamped_high(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)
        parsed = {"research_problem": {"summary": "test", "confidence": 1.5}}

        result = agent._validate_dimensions(parsed, SAMPLE_PAPERS[0])

        assert result["research_problem"]["confidence"] == 1.0

    def test_confidence_clamped_low(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)
        parsed = {"research_problem": {"summary": "test", "confidence": -0.5}}

        result = agent._validate_dimensions(parsed, SAMPLE_PAPERS[0])

        assert result["research_problem"]["confidence"] == 0.0

    def test_confidence_none(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)
        parsed = {"research_problem": {"summary": "test", "confidence": None}}

        result = agent._validate_dimensions(parsed, SAMPLE_PAPERS[0])

        assert result["research_problem"]["confidence"] == 0.3

    def test_adds_disclaimer(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)
        parsed = json.loads(VALID_ANALYSIS_JSON)

        result = agent._validate_dimensions(parsed, SAMPLE_PAPERS[0])

        assert "ai_disclaimer" in result
        assert "AI" in result["ai_disclaimer"]

    def test_adds_analysis_id(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)
        parsed = json.loads(VALID_ANALYSIS_JSON)

        result = agent._validate_dimensions(parsed, SAMPLE_PAPERS[0])

        assert "analysis_id" in result
        assert len(result["analysis_id"]) > 0

    def test_none_dimension_confidence_is_03(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)
        parsed = {"research_problem": None}

        result = agent._validate_dimensions(parsed, SAMPLE_PAPERS[0])

        assert result["research_problem"]["confidence"] == 0.3

    def test_non_numeric_confidence_defaults_to_03(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)
        parsed = {"research_problem": {"summary": "test", "confidence": "high"}}

        result = agent._validate_dimensions(parsed, SAMPLE_PAPERS[0])

        assert result["research_problem"]["confidence"] == 0.3


class TestRuleBasedExtraction:

    def test_returns_all_5_dimensions(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        result = agent._rule_based_extraction(SAMPLE_PAPERS[0])

        for dim in DEFAULT_DIMENSIONS:
            assert dim in result
            assert "summary" in result[dim]
            assert "confidence" in result[dim]
            assert "references" in result[dim]

    def test_all_confidence_03(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        result = agent._rule_based_extraction(SAMPLE_PAPERS[0])

        for dim in DEFAULT_DIMENSIONS:
            assert result[dim]["confidence"] == 0.3

    def test_extraction_quality_low(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        result = agent._rule_based_extraction(SAMPLE_PAPERS[0])

        assert result["extraction_quality"] == 0.1
        assert "ai_disclaimer" in result


class TestExecuteIntegration:

    @pytest.mark.asyncio
    async def test_execute_normal_flow(self):
        llm, pm, _ = _make_mock_services()
        llm.generate = AsyncMock(return_value=VALID_ANALYSIS_JSON)
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        result = await agent.execute(
            {"papers": [SAMPLE_PAPERS[0]]},
            {"user_profile": {"knowledge_level": "intermediate"}},
        )

        assert agent.state.status == AgentStatus.COMPLETED
        assert "analysis_results" in result
        assert len(result["analysis_results"]) == 1
        assert agent.state.duration_ms is not None
        assert "extraction_quality" in result

    @pytest.mark.asyncio
    async def test_execute_error_flow(self):
        llm, pm, _ = _make_mock_services()
        llm.generate = AsyncMock(side_effect=RuntimeError("Unexpected error"))
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        result = await agent.execute(
            {"papers": [SAMPLE_PAPERS[0]]},
            {},
        )

        assert agent.state.status == AgentStatus.COMPLETED
        assert len(result.get("degraded_papers", [])) == 1
        assert result["extraction_quality"] == 0.3


class TestSummarizeResult:

    def test_summarize_success(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        result = agent._summarize_result({
            "total_analyzed": 3,
            "degraded_papers": [],
        })

        assert "3 papers successfully" in result

    def test_summarize_with_degraded(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        result = agent._summarize_result({
            "total_analyzed": 5,
            "degraded_papers": ["p1", "p2"],
        })

        assert "5 papers" in result
        assert "2 degraded" in result


class TestEmptyDimensions:

    def test_empty_dimensions_has_all_keys(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        result = agent._empty_dimensions()

        for dim in DEFAULT_DIMENSIONS:
            assert dim in result
            assert result[dim] is None
        assert len(result) == len(DEFAULT_DIMENSIONS)


class TestFallbackResult:

    @pytest.mark.asyncio
    async def test_fallback_result_extracts_from_all_papers(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        result = agent._fallback_result({"papers": SAMPLE_PAPERS})

        assert result["degraded"] is True
        assert len(result["analysis_results"]) == 3
        assert len(result["degraded_papers"]) == 3
        assert result["total_analyzed"] == 3
        assert result["extraction_quality"] == 0.1

    @pytest.mark.asyncio
    async def test_fallback_result_empty_papers(self):
        llm, pm, _ = _make_mock_services()
        agent = AnalyzerAgent(llm_service=llm, prompt_manager=pm)

        result = agent._fallback_result({"papers": []})

        assert result["degraded"] is True
        assert result["analysis_results"] == []
        assert result["total_analyzed"] == 0
