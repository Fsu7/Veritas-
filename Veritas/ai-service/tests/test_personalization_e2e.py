"""端到端个性化效果测试 — Task 41

验证6-Agent个性化Prompt注入链路完整性：
1. 6个Agent的build_prompt()输出均包含个性化片段
2. RetrieverAgent的top_k随knowledge_level变化
3. 极端画像差异度 > 0.6
4. 空画像降级不抛异常
5. PersonalizationService异常时Agent不阻塞

所有测试使用mock，不调用真实LLM API（FA-018约束）。
"""
from unittest.mock import MagicMock, patch

import pytest

from app.services.personalization_service import PersonalizationService


# ============================================================
# Fixtures
# ============================================================

SAMPLE_PROFILE_BEGINNER = {
    "education_level": "undergraduate",
    "knowledge_level": "beginner",
    "preferred_style": "simple",
    "research_field": "NLP",
}

SAMPLE_PROFILE_EXPERT = {
    "education_level": "phd",
    "knowledge_level": "expert",
    "preferred_style": "technical",
    "research_field": "CV",
}

SAMPLE_PROFILE_MASTER = {
    "education_level": "master",
    "knowledge_level": "intermediate",
    "preferred_style": "balanced",
    "research_field": "NLP",
}


@pytest.fixture
def personalization_service():
    return PersonalizationService()


@pytest.fixture
def mock_prompt_manager():
    pm = MagicMock()
    pm.get_prompt = MagicMock(return_value="Base prompt content")
    return pm


@pytest.fixture
def mock_llm_service():
    return MagicMock()


@pytest.fixture
def mock_search_service():
    return MagicMock()


# ============================================================
# CoordinatorAgent 个性化注入测试
# ============================================================

def test_coordinator_build_prompt_has_personalization(
    mock_llm_service, mock_prompt_manager, personalization_service
):
    """验证 CoordinatorAgent.build_prompt() 输出包含【个性化适配】"""
    from app.agents.coordinator import CoordinatorAgent

    agent = CoordinatorAgent(
        llm_service=mock_llm_service,
        prompt_manager=mock_prompt_manager,
        personalization_service=personalization_service,
    )

    input_data = {"topic": "transformer", "paper_ids": [], "analysis_type": "report"}
    context = {"user_profile": SAMPLE_PROFILE_MASTER}

    prompt = agent.build_prompt(input_data, context)
    assert "【个性化适配】" in prompt
    assert "标准学术" in prompt or "方法论" in prompt


def test_coordinator_build_prompt_no_personalization_without_service(
    mock_llm_service, mock_prompt_manager
):
    """验证无 personalization_service 时不注入个性化指令"""
    from app.agents.coordinator import CoordinatorAgent

    agent = CoordinatorAgent(
        llm_service=mock_llm_service,
        prompt_manager=mock_prompt_manager,
    )

    input_data = {"topic": "transformer", "paper_ids": [], "analysis_type": "report"}
    context = {"user_profile": SAMPLE_PROFILE_MASTER}

    prompt = agent.build_prompt(input_data, context)
    assert "【个性化适配】" not in prompt


# ============================================================
# RetrieverAgent 个性化注入测试
# ============================================================

def test_retriever_build_prompt_has_personalization(
    mock_llm_service, mock_prompt_manager, mock_search_service, personalization_service
):
    """验证 RetrieverAgent.build_prompt() 含个性化指令"""
    from app.agents.retriever import RetrieverAgent

    agent = RetrieverAgent(
        llm_service=mock_llm_service,
        prompt_manager=mock_prompt_manager,
        search_service=mock_search_service,
        personalization_service=personalization_service,
    )

    input_data = {"topic": "NLP", "top_k": 10}
    context = {"user_profile": SAMPLE_PROFILE_MASTER}

    prompt = agent.build_prompt(input_data, context)
    assert "【个性化适配】" in prompt


def test_retriever_top_k_adjustment(
    mock_llm_service, mock_prompt_manager, mock_search_service, personalization_service
):
    """验证 top_k 随 knowledge_level 变化"""
    from app.agents.retriever import RetrieverAgent

    agent = RetrieverAgent(
        llm_service=mock_llm_service,
        prompt_manager=mock_prompt_manager,
        search_service=mock_search_service,
        personalization_service=personalization_service,
    )

    # beginner → top_k=5
    context_beginner = {"user_profile": SAMPLE_PROFILE_BEGINNER}
    prompt = agent.build_prompt({"topic": "test", "top_k": 10}, context_beginner)
    call_args = mock_prompt_manager.get_prompt.call_args
    assert call_args[1]["top_k"] == "5"

    # expert → top_k=20
    context_expert = {"user_profile": SAMPLE_PROFILE_EXPERT}
    prompt = agent.build_prompt({"topic": "test", "top_k": 10}, context_expert)
    call_args = mock_prompt_manager.get_prompt.call_args
    assert call_args[1]["top_k"] == "20"


def test_retriever_top_k_default_without_service(
    mock_llm_service, mock_prompt_manager, mock_search_service
):
    """验证无 personalization_service 时 top_k 不调整"""
    from app.agents.retriever import RetrieverAgent

    agent = RetrieverAgent(
        llm_service=mock_llm_service,
        prompt_manager=mock_prompt_manager,
        search_service=mock_search_service,
    )

    context = {"user_profile": SAMPLE_PROFILE_BEGINNER}
    agent.build_prompt({"topic": "test", "top_k": 10}, context)
    call_args = mock_prompt_manager.get_prompt.call_args
    assert call_args[1]["top_k"] == "10"


# ============================================================
# AnalyzerAgent 个性化注入测试
# ============================================================

def test_analyzer_build_prompt_uses_get_personalization_for_agent(
    mock_llm_service, mock_prompt_manager, personalization_service
):
    """验证 AnalyzerAgent 使用 get_personalization_for_agent"""
    from app.agents.analyzer import AnalyzerAgent

    agent = AnalyzerAgent(
        llm_service=mock_llm_service,
        prompt_manager=mock_prompt_manager,
        personalization_service=personalization_service,
    )

    input_data = {"paper_title": "Test Paper", "paper_abstract": "Abstract"}
    context = {"user_profile": SAMPLE_PROFILE_MASTER}

    prompt = agent.build_prompt(input_data, context)
    # 验证 prompt_manager.get_prompt 被调用且 extra_instruction 非空
    call_args = mock_prompt_manager.get_prompt.call_args
    extra_instruction = call_args[1].get("extra_instruction", "")
    assert len(extra_instruction) > 0


def test_analyzer_fallback_to_extra_instruction(
    mock_llm_service, mock_prompt_manager
):
    """验证无 personalization_service 时降级到 _get_extra_instruction"""
    from app.agents.analyzer import AnalyzerAgent

    agent = AnalyzerAgent(
        llm_service=mock_llm_service,
        prompt_manager=mock_prompt_manager,
    )

    input_data = {"paper_title": "Test Paper", "paper_abstract": "Abstract"}
    context = {"user_profile": SAMPLE_PROFILE_MASTER}

    prompt = agent.build_prompt(input_data, context)
    call_args = mock_prompt_manager.get_prompt.call_args
    extra_instruction = call_args[1].get("extra_instruction", "")
    assert len(extra_instruction) > 0


# ============================================================
# ComparerAgent 个性化注入测试
# ============================================================

def test_comparer_build_prompt_has_personalization(
    mock_llm_service, mock_prompt_manager, personalization_service
):
    """验证 ComparerAgent.build_prompt() 含【个性化适配】"""
    from app.agents.comparer import ComparerAgent

    agent = ComparerAgent(
        llm_service=mock_llm_service,
        prompt_manager=mock_prompt_manager,
        personalization_service=personalization_service,
    )

    input_data = {"analysis_results": [{"paper_id": "p1", "paper_title": "Test"}]}
    context = {"user_profile": SAMPLE_PROFILE_MASTER}

    prompt = agent.build_prompt(input_data, context)
    assert "【个性化适配】" in prompt


# ============================================================
# GeneratorAgent 个性化注入测试
# ============================================================

def test_generator_build_prompt_uses_personalization_service(
    mock_llm_service, mock_prompt_manager, personalization_service
):
    """验证 GeneratorAgent 使用 PersonalizationService"""
    from app.agents.generator import GeneratorAgent

    agent = GeneratorAgent(
        llm_service=mock_llm_service,
        prompt_manager=mock_prompt_manager,
        personalization_service=personalization_service,
    )

    input_data = {"analysis_results": [], "compare_result": None}
    context = {"user_profile": SAMPLE_PROFILE_MASTER}

    prompt = agent.build_prompt(input_data, context)
    # 验证 prompt_manager.get_prompt 被调用
    assert mock_prompt_manager.get_prompt.called
    call_args = mock_prompt_manager.get_prompt.call_args
    personalization = call_args[1].get("personalization", "")
    assert len(personalization) > 0
    # 应包含 Agent 个性化指令
    assert "Agent个性化指令" in personalization or "学历适配" in personalization


# ============================================================
# ReviewerAgent 个性化注入测试
# ============================================================

def test_reviewer_build_prompt_has_personalization(
    mock_llm_service, mock_prompt_manager, personalization_service
):
    """验证 ReviewerAgent.build_prompt() 含【个性化适配】"""
    from app.agents.reviewer import ReviewerAgent

    agent = ReviewerAgent(
        llm_service=mock_llm_service,
        prompt_manager=mock_prompt_manager,
        personalization_service=personalization_service,
    )

    input_data = {"report": "Test report", "original_papers": [], "retry_context": ""}
    context = {"user_profile": SAMPLE_PROFILE_MASTER}

    prompt = agent.build_prompt(input_data, context)
    assert "【个性化适配】" in prompt


# ============================================================
# 全链路测试
# ============================================================

def test_all_six_agents_personalization_injection(
    mock_llm_service, mock_prompt_manager, mock_search_service, personalization_service
):
    """验证6个Agent的build_prompt()输出均包含个性化片段"""
    from app.agents.coordinator import CoordinatorAgent
    from app.agents.retriever import RetrieverAgent
    from app.agents.analyzer import AnalyzerAgent
    from app.agents.comparer import ComparerAgent
    from app.agents.generator import GeneratorAgent
    from app.agents.reviewer import ReviewerAgent

    agents = {
        "coordinator": CoordinatorAgent(
            llm_service=mock_llm_service,
            prompt_manager=mock_prompt_manager,
            personalization_service=personalization_service,
        ),
        "retriever": RetrieverAgent(
            llm_service=mock_llm_service,
            prompt_manager=mock_prompt_manager,
            search_service=mock_search_service,
            personalization_service=personalization_service,
        ),
        "analyzer": AnalyzerAgent(
            llm_service=mock_llm_service,
            prompt_manager=mock_prompt_manager,
            personalization_service=personalization_service,
        ),
        "comparer": ComparerAgent(
            llm_service=mock_llm_service,
            prompt_manager=mock_prompt_manager,
            personalization_service=personalization_service,
        ),
        "generator": GeneratorAgent(
            llm_service=mock_llm_service,
            prompt_manager=mock_prompt_manager,
            personalization_service=personalization_service,
        ),
        "reviewer": ReviewerAgent(
            llm_service=mock_llm_service,
            prompt_manager=mock_prompt_manager,
            personalization_service=personalization_service,
        ),
    }

    context = {"user_profile": SAMPLE_PROFILE_MASTER}

    # coordinator
    prompt = agents["coordinator"].build_prompt(
        {"topic": "test", "paper_ids": [], "analysis_type": "report"}, context
    )
    assert "【个性化适配】" in prompt

    # retriever
    prompt = agents["retriever"].build_prompt(
        {"topic": "test", "top_k": 10}, context
    )
    assert "【个性化适配】" in prompt

    # analyzer — 使用 extra_instruction 方式
    prompt = agents["analyzer"].build_prompt(
        {"paper_title": "Test", "paper_abstract": "Abstract"}, context
    )
    call_args = mock_prompt_manager.get_prompt.call_args
    extra_instruction = call_args[1].get("extra_instruction", "")
    assert len(extra_instruction) > 0

    # comparer
    prompt = agents["comparer"].build_prompt(
        {"analysis_results": [{"paper_id": "p1"}]}, context
    )
    assert "【个性化适配】" in prompt

    # generator — 使用 personalization 变量
    prompt = agents["generator"].build_prompt(
        {"analysis_results": [], "compare_result": None}, context
    )
    call_args = mock_prompt_manager.get_prompt.call_args
    personalization = call_args[1].get("personalization", "")
    assert len(personalization) > 0

    # reviewer
    prompt = agents["reviewer"].build_prompt(
        {"report": "Test", "original_papers": [], "retry_context": ""}, context
    )
    assert "【个性化适配】" in prompt


# ============================================================
# 降级测试
# ============================================================

def test_personalization_empty_profile_fallback(
    mock_llm_service, mock_prompt_manager, mock_search_service, personalization_service
):
    """验证空画像降级不抛异常"""
    from app.agents.coordinator import CoordinatorAgent
    from app.agents.retriever import RetrieverAgent
    from app.agents.reviewer import ReviewerAgent

    agents = [
        CoordinatorAgent(
            llm_service=mock_llm_service,
            prompt_manager=mock_prompt_manager,
            personalization_service=personalization_service,
        ),
        RetrieverAgent(
            llm_service=mock_llm_service,
            prompt_manager=mock_prompt_manager,
            search_service=mock_search_service,
            personalization_service=personalization_service,
        ),
        ReviewerAgent(
            llm_service=mock_llm_service,
            prompt_manager=mock_prompt_manager,
            personalization_service=personalization_service,
        ),
    ]

    context_empty = {"user_profile": {}}
    context_none = {"user_profile": None}

    for agent in agents:
        # 空画像不应抛异常
        if agent.name == "coordinator":
            prompt = agent.build_prompt(
                {"topic": "test", "paper_ids": [], "analysis_type": "report"},
                context_empty,
            )
            assert isinstance(prompt, str)
        elif agent.name == "retriever":
            prompt = agent.build_prompt(
                {"topic": "test", "top_k": 10},
                context_empty,
            )
            assert isinstance(prompt, str)
        elif agent.name == "reviewer":
            prompt = agent.build_prompt(
                {"report": "test", "original_papers": [], "retry_context": ""},
                context_empty,
            )
            assert isinstance(prompt, str)


def test_personalization_diff_extreme_profiles(personalization_service):
    """验证极端画像差异度 > 0.6"""
    diff = personalization_service.get_personalization_diff(
        SAMPLE_PROFILE_BEGINNER, SAMPLE_PROFILE_EXPERT
    )
    assert diff > 0.6, f"Expected diff > 0.6, got {diff}"


def test_four_dimension_effectiveness(personalization_service):
    """验证4维度画像在个性化指令中体现"""
    # education_level 维度
    instruction_undergrad = personalization_service.get_personalization_for_agent(
        "analyzer", {"education_level": "undergraduate", "knowledge_level": "intermediate"}
    )
    instruction_phd = personalization_service.get_personalization_for_agent(
        "analyzer", {"education_level": "phd", "knowledge_level": "intermediate"}
    )
    assert instruction_undergrad != instruction_phd

    # knowledge_level 维度
    instruction_beginner = personalization_service.get_personalization_for_agent(
        "analyzer", {"education_level": "master", "knowledge_level": "beginner"}
    )
    instruction_expert = personalization_service.get_personalization_for_agent(
        "analyzer", {"education_level": "master", "knowledge_level": "expert"}
    )
    assert instruction_beginner != instruction_expert

    # preferred_style 维度（通过 get_personalization_block）
    block_simple = personalization_service.get_personalization_block(
        {"education_level": "master", "knowledge_level": "intermediate", "preferred_style": "simple"}
    )
    block_technical = personalization_service.get_personalization_block(
        {"education_level": "master", "knowledge_level": "intermediate", "preferred_style": "technical"}
    )
    assert block_simple != block_technical

    # research_field 维度
    block_nlp = personalization_service.get_personalization_block(
        {"education_level": "master", "knowledge_level": "intermediate", "preferred_style": "balanced", "research_field": "NLP"}
    )
    block_cv = personalization_service.get_personalization_block(
        {"education_level": "master", "knowledge_level": "intermediate", "preferred_style": "balanced", "research_field": "CV"}
    )
    assert block_nlp != block_cv


def test_personalization_service_failure_graceful(
    mock_llm_service, mock_prompt_manager, mock_search_service
):
    """验证 PersonalizationService 异常时 Agent 不阻塞"""
    from app.agents.coordinator import CoordinatorAgent

    # 创建一个会抛异常的 personalization_service
    broken_service = MagicMock()
    broken_service.get_personalization_for_agent = MagicMock(
        side_effect=RuntimeError("Service broken")
    )

    agent = CoordinatorAgent(
        llm_service=mock_llm_service,
        prompt_manager=mock_prompt_manager,
        personalization_service=broken_service,
    )

    input_data = {"topic": "test", "paper_ids": [], "analysis_type": "report"}
    context = {"user_profile": SAMPLE_PROFILE_MASTER}

    # 不应抛异常
    prompt = agent.build_prompt(input_data, context)
    assert isinstance(prompt, str)
    # 异常时不应包含个性化适配标记
    assert "【个性化适配】" not in prompt
