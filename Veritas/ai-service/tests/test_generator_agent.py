import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.base import BaseAgent
from app.agents.generator import (
    AI_DISCLAIMER,
    ACADEMIC_TERMS,
    DIFFICULTY_MAP,
    EDUCATION_ADAPTATION,
    FIELD_EMPHASIS,
    REQUIRED_SECTIONS,
    STYLE_MAP,
    TERM_DENSITY_TARGET,
    GeneratorAgent,
)


@pytest.fixture
def mock_llm_service():
    service = MagicMock()
    service.generate = AsyncMock(return_value="## 引言\n测试综述内容\n\n## 研究现状\n现状描述\n\n## 方法对比\n方法描述\n\n## 研究趋势\n趋势描述\n\n## 参考文献\n参考内容")
    return service


@pytest.fixture
def mock_prompt_manager():
    manager = MagicMock()
    manager.get_prompt = MagicMock(return_value="rendered prompt")
    return manager


@pytest.fixture
def mock_personalization_service():
    service = MagicMock()
    service.get_personalization_block = MagicMock(
        return_value="【学历适配】侧重方法论对比\n【术语密度目标】20%"
    )
    return service


@pytest.fixture
def generator(mock_llm_service, mock_prompt_manager):
    return GeneratorAgent(
        llm_service=mock_llm_service,
        prompt_manager=mock_prompt_manager,
    )


@pytest.fixture
def generator_with_pers(mock_llm_service, mock_prompt_manager, mock_personalization_service):
    return GeneratorAgent(
        llm_service=mock_llm_service,
        prompt_manager=mock_prompt_manager,
        personalization_service=mock_personalization_service,
    )


SAMPLE_ANALYSIS_RESULTS = [
    {
        "paper_id": "paper_1",
        "paper_title": "Attention Is All You Need",
        "research_problem": {"summary": "序列建模问题", "confidence": 0.9, "references": []},
        "core_method": {"summary": "Transformer架构", "confidence": 0.95, "references": []},
        "main_experiments": {"summary": "WMT翻译任务", "confidence": 0.85, "references": []},
        "core_conclusions": {"summary": "自注意力机制有效", "confidence": 0.9, "references": []},
        "limitations": {"summary": "计算复杂度高", "confidence": 0.7, "references": []},
    },
    {
        "paper_id": "paper_2",
        "paper_title": "BERT: Pre-training of Deep Bidirectional Transformers",
        "research_problem": {"summary": "双向预训练问题", "confidence": 0.9, "references": []},
        "core_method": {"summary": "BERT掩码语言模型", "confidence": 0.95, "references": []},
        "main_experiments": {"summary": "GLUE基准测试", "confidence": 0.85, "references": []},
        "core_conclusions": {"summary": "双向预训练提升效果", "confidence": 0.9, "references": []},
        "limitations": {"summary": "预训练成本高", "confidence": 0.7, "references": []},
    },
    {
        "paper_id": "paper_3",
        "paper_title": "GPT-3: Language Models are Few-Shot Learners",
        "research_problem": {"summary": "少样本学习问题", "confidence": 0.9, "references": []},
        "core_method": {"summary": "大规模语言模型", "confidence": 0.95, "references": []},
        "main_experiments": {"summary": "多任务评测", "confidence": 0.85, "references": []},
        "core_conclusions": {"summary": "规模带来涌现能力", "confidence": 0.9, "references": []},
        "limitations": {"summary": "模型规模过大", "confidence": 0.7, "references": []},
    },
]


def test_generator_inherits_base_agent(generator):
    assert isinstance(generator, BaseAgent)
    assert generator.name == "generator"


def test_build_prompt_renders_template(generator, mock_prompt_manager):
    input_data = {
        "analysis_results": [{"paper_id": "p1"}],
        "compare_result": {"summary": "compare data"},
    }
    context = {"user_profile": {"education_level": "master", "knowledge_level": "intermediate", "preferred_style": "balanced"}}

    generator.build_prompt(input_data, context)

    mock_prompt_manager.get_prompt.assert_called_once()
    call_kwargs = mock_prompt_manager.get_prompt.call_args
    assert call_kwargs[0][0] == "generator"
    assert "personalization" in call_kwargs[1]
    assert "analysis_data" in call_kwargs[1]
    assert "comparison_data" in call_kwargs[1]


def test_build_personalization_block_with_profile(generator):
    profile = {
        "education_level": "undergraduate",
        "knowledge_level": "beginner",
        "preferred_style": "simple",
        "research_field": "NLP",
    }
    block = generator._build_personalization_block(profile)
    assert "通俗" in block or "类比" in block or "背景知识" in block
    assert "5%" in block
    assert "casual" in block
    assert "NLP" in block or "自然语言处理" in block

    profile_expert = {
        "education_level": "phd",
        "knowledge_level": "expert",
        "preferred_style": "technical",
    }
    block_expert = generator._build_personalization_block(profile_expert)
    assert "创新" in block_expert or "前沿" in block_expert
    assert "50%" in block_expert
    assert "formal" in block_expert


def test_build_personalization_block_without_profile(generator):
    block = generator._build_personalization_block(None)
    assert "master" in EDUCATION_ADAPTATION["master"] or "方法论" in block
    assert "20%" in block
    assert "standard" in block


def test_build_personalization_block_service_failure(generator_with_pers, mock_personalization_service):
    mock_personalization_service.get_personalization_block.side_effect = RuntimeError("service down")

    profile = {"education_level": "beginner", "knowledge_level": "beginner", "preferred_style": "simple"}
    block = generator_with_pers._build_personalization_block(profile)
    assert "5%" in block
    assert "casual" in block


@pytest.mark.asyncio
async def test_run_success_flow(generator, mock_llm_service, mock_prompt_manager):
    mock_llm_service.generate.return_value = (
        "## 引言\n综述引言\n\n"
        "## 研究现状\n现状\n\n"
        "## 方法对比\n对比\n\n"
        "## 研究趋势\n趋势\n\n"
        "## 参考文献\n文献\n\n"
        + AI_DISCLAIMER
    )
    mock_prompt_manager.get_prompt.return_value = "full prompt"

    input_data = {"analysis_results": SAMPLE_ANALYSIS_RESULTS}
    context = {"user_profile": {"education_level": "master", "knowledge_level": "intermediate", "preferred_style": "balanced"}}

    result = await generator._run("prompt", input_data, context)

    assert "report" in result
    assert "citation_list" in result
    assert "term_density_actual" in result
    assert "personalization_applied" in result
    assert isinstance(result["report"], str)
    assert len(result["report"]) > 0
    assert isinstance(result["citation_list"], list)
    assert 0.0 <= result["term_density_actual"] <= 1.0


@pytest.mark.asyncio
async def test_run_progress_updates(generator, mock_llm_service, mock_prompt_manager):
    mock_llm_service.generate.return_value = (
        "## 引言\n内容\n\n## 研究现状\n内容\n\n"
        "## 方法对比\n内容\n\n## 研究趋势\n内容\n\n## 参考文献\n内容\n\n"
        + AI_DISCLAIMER
    )
    mock_prompt_manager.get_prompt.return_value = "prompt"

    input_data = {"analysis_results": SAMPLE_ANALYSIS_RESULTS}
    context = {}

    generator.state.progress = 0.0
    await generator._run("prompt", input_data, context)

    assert generator.state.progress == 1.0


@pytest.mark.asyncio
async def test_run_llm_failure_fallback(generator, mock_llm_service, mock_prompt_manager):
    mock_llm_service.generate.side_effect = RuntimeError("LLM unavailable")
    mock_prompt_manager.get_prompt.return_value = "prompt"

    input_data = {"analysis_results": SAMPLE_ANALYSIS_RESULTS}
    context = {}

    result = await generator._run("prompt", input_data, context)

    assert result.get("degraded") is True
    assert isinstance(result.get("report"), str)
    assert len(result["report"]) > 0
    assert result["citation_list"] == []
    assert result["term_density_actual"] == 0.0


@pytest.mark.asyncio
async def test_run_empty_analysis_results(generator, mock_llm_service, mock_prompt_manager):
    mock_llm_service.generate.return_value = "## 引言\n暂无\n\n## 研究现状\n暂无\n\n## 方法对比\n暂无\n\n## 研究趋势\n暂无\n\n## 参考文献\n暂无\n\n" + AI_DISCLAIMER
    mock_prompt_manager.get_prompt.return_value = "prompt"

    input_data = {"analysis_results": []}
    context = {}

    result = await generator._run("prompt", input_data, context)

    assert "report" in result
    assert isinstance(result["report"], str)


def test_extract_citations_author_year(generator):
    report = "根据研究 [Vaswani et al., 2017]，Transformer架构被提出。另一项研究 [Devlin, 2019] 提出了BERT。"
    results = generator._extract_citations(report, SAMPLE_ANALYSIS_RESULTS)
    assert len(results) >= 2
    assert any("Vaswani" in c["citation"] for c in results)
    assert any("Devlin" in c["citation"] for c in results)


def test_extract_citations_numeric(generator):
    report = "根据研究 [1]，Transformer架构被提出。另一项研究 [2] 提出了BERT。[3] 提出了GPT-3。"
    results = generator._extract_citations(report, SAMPLE_ANALYSIS_RESULTS)
    numeric_citations = [c for c in results if c["citation"].startswith("[") and c["citation"].endswith("]") and c["citation"][1:-1].isdigit()]
    assert len(numeric_citations) >= 3
    assert numeric_citations[0]["paper_id"] == "paper_1"
    assert numeric_citations[1]["paper_id"] == "paper_2"
    assert numeric_citations[2]["paper_id"] == "paper_3"


def test_extract_citations_no_match(generator):
    report = "这是一段没有任何引用的普通文本。"
    results = generator._extract_citations(report, SAMPLE_ANALYSIS_RESULTS)
    assert results == []


def test_validate_report_all_sections(generator):
    report = (
        "## 引言\n内容\n\n"
        "## 研究现状\n内容\n\n"
        "## 方法对比\n内容\n\n"
        "## 研究趋势\n内容\n\n"
        "## 参考文献\n内容"
    )
    result = generator._validate_report(report)
    assert result["is_valid"] is True
    assert result["missing_sections"] == []


def test_validate_report_missing_sections(generator):
    report = "## 引言\n内容\n\n## 研究现状\n内容"
    result = generator._validate_report(report)
    assert result["is_valid"] is False
    assert len(result["missing_sections"]) > 0
    assert "方法对比" in result["missing_sections"]
    assert len(result["report"]) > len(report)


def test_calculate_term_density(generator):
    dense_report = (
        "The attention mechanism and transformer architecture use "
        "self-attention and multi-head attention for natural language processing. "
        "Fine-tuning and pre-training are key steps in deep learning. "
        "Gradient descent and stochastic gradient descent optimize the loss function. "
        "Overfitting is prevented by dropout and regularization."
    )
    density = generator._calculate_term_density(dense_report, "advanced")
    assert 0.0 <= density <= 1.0
    assert density > 0.05

    casual_report = "今天天气很好，我们去公园散步吧。"
    density_casual = generator._calculate_term_density(casual_report, "beginner")
    assert 0.0 <= density_casual <= 1.0
    assert density_casual < 0.1


def test_generate_fallback_report(generator):
    report = generator._generate_fallback_report(SAMPLE_ANALYSIS_RESULTS)
    assert "## 引言" in report
    assert "## 研究现状" in report
    assert "## 方法对比" in report
    assert "## 研究趋势" in report
    assert "## 参考文献" in report
    assert AI_DISCLAIMER in report

    report_empty = generator._generate_fallback_report([])
    assert "## 引言" in report_empty
    assert AI_DISCLAIMER in report_empty


def test_fallback_result_structure(generator):
    input_data = {"analysis_results": SAMPLE_ANALYSIS_RESULTS}
    result = generator._fallback_result(input_data)

    assert result["degraded"] is True
    assert result["agent"] == "generator"
    assert isinstance(result["report"], str)
    assert len(result["report"]) > 0
    assert result["citation_list"] == []
    assert result["term_density_actual"] == 0.0
    assert "education_adaptation" in result["personalization_applied"]
    assert "term_density_target" in result["personalization_applied"]
    assert "style_guide" in result["personalization_applied"]


def test_ai_disclaimer_present(generator, mock_llm_service, mock_prompt_manager):
    mock_llm_service.generate.return_value = (
        "## 引言\n内容\n\n## 研究现状\n内容\n\n"
        "## 方法对比\n内容\n\n## 研究趋势\n内容\n\n## 参考文献\n内容"
    )
    mock_prompt_manager.get_prompt.return_value = "prompt"

    report_without_disclaimer = "## 引言\n内容\n\n## 研究现状\n内容\n\n## 方法对比\n内容\n\n## 研究趋势\n内容\n\n## 参考文献\n内容"
    assert AI_DISCLAIMER not in report_without_disclaimer

    report_with_disclaimer = report_without_disclaimer + "\n\n" + AI_DISCLAIMER
    assert AI_DISCLAIMER in report_with_disclaimer

    count = report_with_disclaimer.count(AI_DISCLAIMER)
    assert count == 1

    fallback_report = generator._generate_fallback_report(SAMPLE_ANALYSIS_RESULTS)
    assert AI_DISCLAIMER in fallback_report
    assert fallback_report.count(AI_DISCLAIMER) == 1


def test_summarize_result_format(generator):
    result = {
        "report": "A" * 500,
        "citation_list": [{"index": 1}, {"index": 2}, {"index": 3}],
        "term_density_actual": 0.22,
    }
    summary = generator._summarize_result(result)
    assert "500" in summary
    assert "3 citations" in summary
    assert "22%" in summary
