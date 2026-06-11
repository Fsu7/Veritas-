import json
import string
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.services.personalization_service import (
    DIFFICULTY_MAP,
    EDUCATION_ADAPTATION,
    FIELD_EMPHASIS,
    STYLE_MAP,
    TERM_DENSITY_TARGET,
    PersonalizationService,
)


PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


@pytest.fixture
def service():
    return PersonalizationService()


@pytest.fixture
def service_with_pm():
    pm = MagicMock()
    pm.get_prompt = MagicMock(return_value="rendered prompt content")
    return PersonalizationService(prompt_manager=pm)


SAMPLE_PROFILE_MASTER = {
    "education_level": "master",
    "knowledge_level": "intermediate",
    "preferred_style": "balanced",
    "research_field": "NLP",
}

SAMPLE_PROFILE_PHD = {
    "education_level": "phd",
    "knowledge_level": "advanced",
    "preferred_style": "technical",
    "research_field": "CV",
}

SAMPLE_PROFILE_CAMEL = {
    "educationLevel": "undergraduate",
    "knowledgeLevel": "beginner",
    "preferredStyle": "simple",
    "researchField": "RL",
}


def test_generator_prompt_structure():
    template_path = PROMPTS_DIR / "generator.txt"
    content = template_path.read_text(encoding="utf-8")

    assert "Role Block" in content or "身份定义" in content
    assert "Task Block" in content or "任务说明" in content
    assert "Input Block" in content or "输入数据" in content
    assert "Personalization Block" in content or "个性化适配" in content
    assert "Chain-of-Thought" in content or "推理链" in content
    assert "Output Schema" in content or "JSON Schema" in content
    assert "Constraint Block" in content or "行为边界" in content
    assert "Fallback Block" in content or "降级兼容" in content


def test_generator_prompt_variable_rendering():
    template_path = PROMPTS_DIR / "generator.txt"
    content = template_path.read_text(encoding="utf-8")
    template = string.Template(content)

    result = template.substitute(
        personalization="test personalization",
        analysis_data="[]",
        comparison_data="无",
        user_profile_summary="硕士/NLP方向/中级知识水平/均衡风格",
    )

    assert "test personalization" in result
    assert "硕士/NLP方向/中级知识水平/均衡风格" in result
    assert "$personalization" not in result
    assert "$analysis_data" not in result
    assert "$comparison_data" not in result
    assert "$user_profile_summary" not in result


def test_generator_prompt_empty_personalization():
    template_path = PROMPTS_DIR / "generator.txt"
    content = template_path.read_text(encoding="utf-8")
    template = string.Template(content)

    result = template.safe_substitute(
        personalization="",
        analysis_data="[]",
        comparison_data="无",
        user_profile_summary="默认用户",
    )

    assert isinstance(result, str)
    assert len(result) > 0
    assert "$personalization" not in result


def test_generator_prompt_json_schema():
    template_path = PROMPTS_DIR / "generator.txt"
    content = template_path.read_text(encoding="utf-8")

    assert "report" in content
    assert "citation_list" in content
    assert "term_density_actual" in content
    assert "personalization_applied" in content


def test_generator_prompt_cot_steps():
    template_path = PROMPTS_DIR / "generator.txt"
    content = template_path.read_text(encoding="utf-8")

    assert "Outline" in content
    assert "Draft" in content
    assert "Personalize" in content
    assert "Self-Check" in content


def test_get_personalization_block(service):
    block = service.get_personalization_block(SAMPLE_PROFILE_MASTER)

    assert "【学历适配】" in block
    assert "【术语密度目标】" in block
    assert "【写作风格】" in block
    assert "【领域侧重】" in block
    assert "方法论" in block or "实验设计" in block
    assert "20%" in block
    assert "标准学术" in block
    assert "自然语言处理" in block or "NLP" in block

    block_phd = service.get_personalization_block(SAMPLE_PROFILE_PHD)
    assert "创新" in block_phd or "前沿" in block_phd
    assert "40%" in block_phd
    assert "正式学术" in block_phd
    assert "计算机视觉" in block_phd or "CV" in block_phd

    profile_no_field = {
        "education_level": "master",
        "knowledge_level": "intermediate",
        "preferred_style": "balanced",
        "research_field": "",
    }
    block_no_field = service.get_personalization_block(profile_no_field)
    assert "【领域侧重】" not in block_no_field


def test_get_extra_instruction(service):
    analyzer_instruction = service.get_extra_instruction(
        SAMPLE_PROFILE_MASTER, agent_name="analyzer"
    )
    assert isinstance(analyzer_instruction, str)
    assert len(analyzer_instruction) > 0
    assert "标准学术" in analyzer_instruction or "术语" in analyzer_instruction

    generator_instruction = service.get_extra_instruction(
        SAMPLE_PROFILE_MASTER, agent_name="generator"
    )
    assert isinstance(generator_instruction, str)
    assert len(generator_instruction) > 0
    assert "综述" in generator_instruction or "学术" in generator_instruction

    assert analyzer_instruction != generator_instruction

    default_instruction = service.get_extra_instruction(
        SAMPLE_PROFILE_MASTER, agent_name=""
    )
    assert isinstance(default_instruction, str)
    assert len(default_instruction) > 0


def test_build_generation_prompt(service_with_pm):
    analysis_results = [
        {"paper_id": "p1", "paper_title": "Test Paper", "core_method": {"summary": "Test method"}}
    ]
    comparison_result = {"summary": "Test comparison"}
    user_profile = SAMPLE_PROFILE_MASTER

    prompt = service_with_pm.build_generation_prompt(
        analysis_results, comparison_result, user_profile
    )

    service_with_pm.prompt_manager.get_prompt.assert_called_once()
    call_kwargs = service_with_pm.prompt_manager.get_prompt.call_args
    assert call_kwargs[0][0] == "generator"
    assert "personalization" in call_kwargs[1]
    assert "analysis_data" in call_kwargs[1]
    assert "comparison_data" in call_kwargs[1]
    assert "user_profile_summary" in call_kwargs[1]


def test_unknown_enum_defaults(service):
    unknown_profile = {
        "education_level": "postdoc",
        "knowledge_level": "guru",
        "preferred_style": "ultra_formal",
        "research_field": "quantum_computing",
    }

    block = service.get_personalization_block(unknown_profile)
    assert "【学历适配】" in block
    assert "【术语密度目标】" in block
    assert "【写作风格】" in block

    edu_adapt = service.get_education_adaptation("postdoc")
    assert edu_adapt == EDUCATION_ADAPTATION["master"]["text"]

    density = service.get_term_density_target("guru")
    assert density == TERM_DENSITY_TARGET["intermediate"]

    style = service.get_style_guide("ultra_formal")
    assert "标准学术" in style

    field = service.get_field_emphasis("quantum_computing")
    assert field == ""


def test_camelcase_input(service):
    block = service.get_personalization_block(SAMPLE_PROFILE_CAMEL)

    assert "【学历适配】" in block
    assert "背景知识" in block or "类比" in block
    assert "5%" in block
    assert "日常用语" in block or "比喻" in block
    assert "强化学习" in block or "RL" in block

    instruction = service.get_extra_instruction(
        SAMPLE_PROFILE_CAMEL, agent_name="analyzer"
    )
    assert isinstance(instruction, str)
    assert len(instruction) > 0

    summary = service._build_user_profile_summary(SAMPLE_PROFILE_CAMEL)
    assert "本科" in summary
    assert "RL方向" in summary
    assert "入门" in summary
    assert "通俗" in summary


def test_no_prompt_manager():
    service_no_pm = PersonalizationService(prompt_manager=None)

    analysis_results = [{"paper_id": "p1", "paper_title": "Test"}]
    comparison_result = None
    user_profile = SAMPLE_PROFILE_MASTER

    prompt = service_no_pm.build_generation_prompt(
        analysis_results, comparison_result, user_profile
    )

    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_helper_methods(service):
    for level in ["undergraduate", "master", "phd", "faculty"]:
        adapt = service.get_education_adaptation(level)
        assert isinstance(adapt, str)
        assert len(adapt) > 0

    for level in ["beginner", "intermediate", "advanced", "expert"]:
        density = service.get_term_density_target(level)
        assert isinstance(density, float)
        assert 0.0 <= density <= 1.0

    for style in ["simple", "balanced", "technical"]:
        guide = service.get_style_guide(style)
        assert isinstance(guide, str)
        assert len(guide) > 0

    for field in ["NLP", "CV", "RL", "多模态"]:
        emphasis = service.get_field_emphasis(field)
        assert isinstance(emphasis, str)
        assert len(emphasis) > 0


def test_label_methods(service):
    assert service._education_label("undergraduate") == "本科"
    assert service._education_label("master") == "硕士"
    assert service._education_label("phd") == "博士"
    assert service._education_label("faculty") == "教师"
    assert service._education_label("unknown") == "未知"

    assert service._knowledge_label("beginner") == "入门"
    assert service._knowledge_label("intermediate") == "中级"
    assert service._knowledge_label("advanced") == "进阶"
    assert service._knowledge_label("expert") == "专家"
    assert service._knowledge_label("unknown") == "未知"

    assert service._style_label("simple") == "通俗"
    assert service._style_label("balanced") == "均衡"
    assert service._style_label("technical") == "专业"
    assert service._style_label("unknown") == "未知"


def test_prompt_manager_integration():
    from app.services.prompt_manager import PromptManager

    pm = PromptManager(prompts_dir=str(PROMPTS_DIR))
    pm.templates["generator"] = string.Template(
        (PROMPTS_DIR / "generator.txt").read_text(encoding="utf-8")
    )

    service_with_real_pm = PersonalizationService(prompt_manager=pm)

    analysis_results = [{"paper_id": "p1", "paper_title": "Test Paper"}]
    comparison_result = None
    user_profile = SAMPLE_PROFILE_MASTER

    prompt = service_with_real_pm.build_generation_prompt(
        analysis_results, comparison_result, user_profile
    )

    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert "$personalization" not in prompt
    assert "$analysis_data" not in prompt
    assert "$comparison_data" not in prompt
    assert "$user_profile_summary" not in prompt
    assert "硕士" in prompt or "NLP" in prompt


# ============================================================
# Task 39-40 新增测试：映射表结构验证 + 个性化接口
# ============================================================

from app.services.personalization_service import AGENT_PERSONALIZATION_MAP


DIFFICULTY_MAP_REQUIRED_KEYS = {
    "level", "term_density", "explanation_style",
    "example_requirement", "abstraction_level", "citation_depth",
}

STYLE_MAP_REQUIRED_KEYS = {
    "tone", "paragraph", "structure", "structure_example",
    "sentence_pattern", "transition_style", "audience_awareness",
}

EDUCATION_ADAPTATION_REQUIRED_KEYS = {
    "text", "background_knowledge", "methodology_focus",
    "innovation_emphasis", "teaching_applicability",
}

FIELD_EMPHASIS_REQUIRED_KEYS = {
    "text", "primary_keywords", "secondary_keywords",
    "methodology_bias", "evaluation_focus",
}


def test_difficulty_map_all_levels_have_6_keys():
    """验证 DIFFICULTY_MAP 4个级别均包含6个策略维度"""
    for level in ["beginner", "intermediate", "advanced", "expert"]:
        assert level in DIFFICULTY_MAP, f"Missing level: {level}"
        entry = DIFFICULTY_MAP[level]
        assert isinstance(entry, dict), f"DIFFICULTY_MAP['{level}'] should be dict"
        for key in DIFFICULTY_MAP_REQUIRED_KEYS:
            assert key in entry, f"DIFFICULTY_MAP['{level}'] missing key: {key}"
        assert isinstance(entry["term_density"], (int, float))
        assert 0.0 <= entry["term_density"] <= 1.0


def test_style_map_all_styles_have_7_keys():
    """验证 STYLE_MAP 3个风格均包含7个维度"""
    for style in ["simple", "balanced", "technical"]:
        assert style in STYLE_MAP, f"Missing style: {style}"
        entry = STYLE_MAP[style]
        assert isinstance(entry, dict), f"STYLE_MAP['{style}'] should be dict"
        for key in STYLE_MAP_REQUIRED_KEYS:
            assert key in entry, f"STYLE_MAP['{style}'] missing key: {key}"
        assert isinstance(entry[key], str) and len(entry[key]) > 0, \
            f"STYLE_MAP['{style}']['{key}'] should be non-empty str"


def test_education_adaptation_all_levels_have_strategy_dimensions():
    """验证 EDUCATION_ADAPTATION 4个学历层次均包含5个策略维度"""
    for level in ["undergraduate", "master", "phd", "faculty"]:
        assert level in EDUCATION_ADAPTATION, f"Missing level: {level}"
        entry = EDUCATION_ADAPTATION[level]
        assert isinstance(entry, dict), f"EDUCATION_ADAPTATION['{level}'] should be dict"
        for key in EDUCATION_ADAPTATION_REQUIRED_KEYS:
            assert key in entry, f"EDUCATION_ADAPTATION['{level}'] missing key: {key}"


def test_field_emphasis_all_fields_have_strategy_dimensions():
    """验证 FIELD_EMPHASIS 7个研究方向均包含5个策略维度"""
    for field in ["NLP", "CV", "RL", "多模态", "知识图谱", "推荐系统", "数据挖掘"]:
        assert field in FIELD_EMPHASIS, f"Missing field: {field}"
        entry = FIELD_EMPHASIS[field]
        assert isinstance(entry, dict), f"FIELD_EMPHASIS['{field}'] should be dict"
        for key in FIELD_EMPHASIS_REQUIRED_KEYS:
            assert key in entry, f"FIELD_EMPHASIS['{field}'] missing key: {key}"
        assert isinstance(entry["primary_keywords"], list)
        assert isinstance(entry["secondary_keywords"], list)


def test_get_personalization_for_agent_all_six(service):
    """验证 get_personalization_for_agent() 为6个Agent返回不同且非空的个性化指令"""
    profile = SAMPLE_PROFILE_MASTER
    results = {}
    for agent_name in ["coordinator", "retriever", "analyzer", "comparer", "generator", "reviewer"]:
        instruction = service.get_personalization_for_agent(agent_name, profile)
        assert isinstance(instruction, str), f"{agent_name} should return str"
        assert len(instruction) > 0, f"{agent_name} should return non-empty str"
        results[agent_name] = instruction

    # 验证不同Agent返回不同内容
    unique_values = set(results.values())
    assert len(unique_values) >= 3, "At least 3 agents should have different instructions"


def test_agent_personalization_map_coverage():
    """验证 AGENT_PERSONALIZATION_MAP 覆盖6个Agent × 4个知识水平 × 4个学历层次"""
    expected_agents = {"coordinator", "retriever", "analyzer", "comparer", "generator", "reviewer"}
    assert set(AGENT_PERSONALIZATION_MAP.keys()) == expected_agents

    for agent_name, agent_map in AGENT_PERSONALIZATION_MAP.items():
        assert "knowledge_level_instructions" in agent_map, \
            f"{agent_name} missing knowledge_level_instructions"
        assert "education_level_instructions" in agent_map, \
            f"{agent_name} missing education_level_instructions"

        knowledge_map = agent_map["knowledge_level_instructions"]
        for level in ["beginner", "intermediate", "advanced", "expert"]:
            assert level in knowledge_map, \
                f"{agent_name} knowledge_level_instructions missing {level}"
            assert isinstance(knowledge_map[level], str) and len(knowledge_map[level]) > 0

        education_map = agent_map["education_level_instructions"]
        for level in ["undergraduate", "master", "phd", "faculty"]:
            assert level in education_map, \
                f"{agent_name} education_level_instructions missing {level}"
            assert isinstance(education_map[level], str) and len(education_map[level]) > 0


def test_get_personalization_diff(service):
    """验证极端画像差异度 > 0.6"""
    beginner_profile = {
        "education_level": "undergraduate",
        "knowledge_level": "beginner",
        "preferred_style": "simple",
        "research_field": "NLP",
    }
    expert_profile = {
        "education_level": "phd",
        "knowledge_level": "expert",
        "preferred_style": "technical",
        "research_field": "CV",
    }
    diff = service.get_personalization_diff(beginner_profile, expert_profile)
    assert isinstance(diff, float)
    assert diff > 0.6, f"Expected diff > 0.6, got {diff}"


def test_get_personalization_diff_same_profile(service):
    """验证相同画像差异度 = 0"""
    diff = service.get_personalization_diff(SAMPLE_PROFILE_MASTER, SAMPLE_PROFILE_MASTER)
    assert diff == 0.0


def test_get_personalization_for_agent_unknown_agent(service):
    """验证未知Agent返回空字符串"""
    result = service.get_personalization_for_agent("nonexistent_agent", SAMPLE_PROFILE_MASTER)
    assert result == ""


def test_backward_compatibility_after_enhancement(service):
    """验证增强后所有方法仍正常工作"""
    # get_education_adaptation 返回 text 字段
    for level in ["undergraduate", "master", "phd", "faculty"]:
        result = service.get_education_adaptation(level)
        assert isinstance(result, str) and len(result) > 0

    # get_term_density_target 返回 float
    for level in ["beginner", "intermediate", "advanced", "expert"]:
        result = service.get_term_density_target(level)
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    # get_style_guide 返回 str
    for style in ["simple", "balanced", "technical"]:
        result = service.get_style_guide(style)
        assert isinstance(result, str) and len(result) > 0

    # get_field_emphasis 返回 str
    for field in ["NLP", "CV", "RL", "多模态"]:
        result = service.get_field_emphasis(field)
        assert isinstance(result, str) and len(result) > 0
