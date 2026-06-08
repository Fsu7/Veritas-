"""ComparerAgent 单元测试 — task34 测试覆盖

按 task34_comparer_agent_core/prompt.json test_requirements 逐个实现：
- normal_flow / boundary_condition / error_flow / degradation
"""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.base import AgentStatus, BaseAgent
from app.agents.comparer import (
    AI_DISCLAIMER,
    COMPARE_DIMENSIONS,
    CONFLICT_KEYWORDS,
    DEFAULT_ROOT_CAUSE,
    FALLBACK_NOTE,
    MAX_PAPERS,
    MIN_PAPERS,
    VALID_ROOT_CAUSES,
    ComparerAgent,
)


# ============================================================
# Mock 工厂
# ============================================================


def _make_mock_services(llm_output=None, llm_side_effect=None):
    """构造 mock LLMService 和 PromptManager"""
    llm = AsyncMock()
    if llm_side_effect is not None:
        llm.generate = AsyncMock(side_effect=llm_side_effect)
    elif llm_output is not None:
        llm.generate = AsyncMock(return_value=llm_output)
    else:
        llm.generate = AsyncMock(return_value="")

    pm = MagicMock()
    pm.get_prompt = MagicMock(
        return_value="comparer prompt: analysis_data=$analysis_data, user_profile=$user_profile, paper_count=$paper_count"
    )
    return llm, pm


SAMPLE_USER_PROFILE = {
    "education_level": "phd",
    "research_field": "RL",
    "knowledge_level": "advanced",
    "preferred_style": "technical",
}


def _make_paper(paper_id: str, title: str, conclusions: str, method: str = "方法描述"):
    """构造测试用单篇论文分析结果"""
    return {
        "paper_id": paper_id,
        "paper_title": title,
        "research_problem": {"summary": f"{title}的研究问题：探索相关算法", "confidence": 0.9, "references": []},
        "core_method": {"summary": method, "confidence": 0.9, "references": []},
        "main_experiments": {"summary": "在标准数据集上验证", "confidence": 0.85, "references": []},
        "core_conclusions": {"summary": conclusions, "confidence": 0.9, "references": []},
        "limitations": {"summary": FALLBACK_NOTE, "confidence": 0.5, "references": []},
    }


SAMPLE_3_PAPERS = [
    _make_paper(
        "arxiv_maddpg",
        "MADDPG: Multi-Agent Actor-Critic",
        "MADDPG 在多智能体环境中表现出色，但是收敛速度较慢",
        "基于 Actor-Critic 的多智能体强化学习方法",
    ),
    _make_paper(
        "arxiv_qmix",
        "QMIX: Monotonic Value Function",
        "QMIX 通过值分解实现高效协作，然而在大规模场景下泛化能力有限",
        "基于单调值函数分解的多智能体学习方法",
    ),
    _make_paper(
        "arxiv_coma",
        "COMA: Counterfactual Multi-Agent",
        "COMA 使用反事实基线提升性能，相比之下在稀疏奖励环境中表现更好",
        "基于反事实多智能体策略梯度方法",
    ),
]


VALID_COMPARISON_JSON = json.dumps({
    "comparison_matrix": {
        "dimensions": list(COMPARE_DIMENSIONS),
        "papers": ["arxiv_maddpg", "arxiv_qmix", "arxiv_coma"],
        "similarities": [
            {"dimension": "research_problem", "papers": ["arxiv_maddpg", "arxiv_qmix"], "similarity": 0.7, "description": "都是多智能体强化学习"},
        ],
        "differences": [
            {"dimension": "core_method", "papers": ["arxiv_maddpg", "arxiv_qmix"], "description": "Actor-Critic vs 值函数分解"},
        ],
        "contradictions": [
            {
                "papers": ["arxiv_maddpg", "arxiv_qmix"],
                "topic": "core_conclusions",
                "claim_a": "MADDPG 收敛速度较慢",
                "claim_b": "QMIX 大规模场景泛化能力有限",
                "evidence_a": "实验显示 10000 步收敛",
                "evidence_b": "在 8 智能体场景表现下降",
                "root_cause": "methodological_conflict",
                "resolution_suggestion": "建议在统一实验环境下进一步验证",
            },
        ],
    },
    "summary": "3 篇 RL 论文对比完成",
    "contradictions": [],
})


# ============================================================
# FR-001：继承 BaseAgent
# ============================================================


def test_comparer_inherits_base_agent():
    """ComparerAgent 必须继承 BaseAgent"""
    llm, pm = _make_mock_services()
    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)
    assert isinstance(agent, BaseAgent)
    assert agent.name == "comparer"
    assert agent.timeout == 30


# ============================================================
# FR-002：build_prompt 渲染模板
# ============================================================


def test_build_prompt_renders_template():
    """build_prompt 应调用 prompt_manager.get_prompt('comparer', ...)"""
    llm, pm = _make_mock_services()
    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

    input_data = {"analysis_results": SAMPLE_3_PAPERS}
    context = {"user_profile": SAMPLE_USER_PROFILE}

    prompt = agent.build_prompt(input_data, context)

    pm.get_prompt.assert_called_once()
    call_args = pm.get_prompt.call_args
    args = call_args[0]
    kwargs = call_args[1]
    assert args[0] == "comparer"
    assert kwargs["paper_count"] == "3"
    assert "education_level=phd" in kwargs["user_profile"]
    assert "arxiv_maddpg" in kwargs["analysis_data"]


def test_build_prompt_with_two_papers():
    """2 篇论文时 build_prompt 应正常渲染"""
    llm, pm = _make_mock_services()
    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

    input_data = {"analysis_results": SAMPLE_3_PAPERS[:2]}
    context = {"user_profile": SAMPLE_USER_PROFILE}

    prompt = agent.build_prompt(input_data, context)

    pm.get_prompt.assert_called_once()
    assert pm.get_prompt.call_args[1]["paper_count"] == "2"


# ============================================================
# FR-004：_parse_comparison
# ============================================================


def test_parse_comparison_valid_json():
    """合法 JSON 块 → 解析为对比矩阵"""
    llm, pm = _make_mock_services()
    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

    input_data = {"analysis_results": SAMPLE_3_PAPERS}

    result = agent._parse_comparison(VALID_COMPARISON_JSON, input_data)

    assert "comparison_matrix" in result
    assert "summary" in result
    assert "contradictions" in result
    assert result["comparison_matrix"]["papers"] == [
        "arxiv_maddpg",
        "arxiv_qmix",
        "arxiv_coma",
    ]


def test_parse_comparison_invalid_json():
    """非法 JSON → 降级到 _rule_based_comparison"""
    llm, pm = _make_mock_services()
    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

    input_data = {"analysis_results": SAMPLE_3_PAPERS}

    result = agent._parse_comparison("not a json at all !!!", input_data)

    # 降级路径：3 篇论文 → C(3,2)=3 对
    assert "comparison_matrix" in result
    assert len(result["comparison_matrix"]["similarities"]) > 0


def test_parse_comparison_invalid_root_cause():
    """非法 root_cause → 替换为 'methodological_conflict'"""
    llm, pm = _make_mock_services()
    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

    invalid_json = json.dumps({
        "comparison_matrix": {
            "dimensions": list(COMPARE_DIMENSIONS),
            "papers": ["a", "b"],
            "contradictions": [
                {
                    "papers": ["a", "b"],
                    "topic": "test",
                    "claim_a": "x",
                    "claim_b": "y",
                    "evidence_a": "x evidence",
                    "evidence_b": "y evidence",
                    "root_cause": "INVALID_ROOT_CAUSE",  # 非法值
                    "resolution_suggestion": "test",
                }
            ],
        },
        "summary": "test",
        "contradictions": [],
    })

    input_data = {"analysis_results": SAMPLE_3_PAPERS[:2]}
    result = agent._parse_comparison(invalid_json, input_data)

    # 验证根因被替换
    contradictions = result["comparison_matrix"]["contradictions"]
    assert len(contradictions) >= 1
    assert contradictions[0]["root_cause"] == DEFAULT_ROOT_CAUSE


def test_parse_comparison_missing_paper_id():
    """缺失 paper_id → 自动补全"""
    llm, pm = _make_mock_services()
    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

    json_without_papers = json.dumps({
        "comparison_matrix": {
            "dimensions": list(COMPARE_DIMENSIONS),
            "papers": [],  # 缺失
            "similarities": [],
            "differences": [],
            "contradictions": [],
        },
        "summary": "test",
        "contradictions": [],
    })

    input_data = {"analysis_results": SAMPLE_3_PAPERS[:2]}
    result = agent._parse_comparison(json_without_papers, input_data)

    # 应自动补全 paper_ids
    papers = result["comparison_matrix"]["papers"]
    assert "arxiv_maddpg" in papers
    assert "arxiv_qmix" in papers


# ============================================================
# FR-005：_rule_based_comparison
# ============================================================


def test_rule_based_comparison_with_three_papers():
    """3 篇论文 → C(3,2)=3 个对比对"""
    llm, pm = _make_mock_services()
    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

    input_data = {"analysis_results": SAMPLE_3_PAPERS}

    result = agent._rule_based_comparison(input_data)

    assert result["paper_count"] == 3
    assert len(result["comparison_matrix"]["papers"]) == 3
    # 4 维度 × 3 对 = 12 项 similarities + differences
    assert (
        len(result["comparison_matrix"]["similarities"])
        + len(result["comparison_matrix"]["differences"])
        >= 12
    )


def test_rule_based_comparison_detects_conflict_keywords():
    """关键词检测矛盾（但是/然而/however 等）"""
    llm, pm = _make_mock_services()
    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

    input_data = {"analysis_results": SAMPLE_3_PAPERS}

    result = agent._rule_based_comparison(input_data)

    # SAMPLE_3_PAPERS 的 conclusions 含 "但是"、"然而"、"相比之下"
    assert len(result["contradictions"]) >= 1, (
        f"Expected >=1 contradiction, got {len(result['contradictions'])}"
    )
    # 至少一个矛盾包含关键词
    keywords_found = []
    for c in result["contradictions"]:
        # 直接调用 _detect_conflict_keywords 验证
        keywords_found.extend(
            agent._detect_conflict_keywords(
                c["claim_a"], c["claim_b"]
            )
        )
    # 至少有一个 CONFLICT_KEYWORDS 列表中的关键词被识别
    assert any(kw in keywords_found for kw in CONFLICT_KEYWORDS), (
        f"Expected at least one CONFLICT_KEYWORDS hit, found {keywords_found}"
    )


# ============================================================
# FR-006：_extract_dimension_summary
# ============================================================


def test_extract_dimension_summary_dict():
    """dict 类型 → 取 summary 字段"""
    llm, pm = _make_mock_services()
    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

    paper = {"research_problem": {"summary": "测试研究问题", "confidence": 0.9}}
    result = agent._extract_dimension_summary(paper, "research_problem")
    assert result == "测试研究问题"


def test_extract_dimension_summary_str():
    """str 类型 → 原样返回"""
    llm, pm = _make_mock_services()
    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

    paper = {"research_problem": "字符串类型的字段"}
    result = agent._extract_dimension_summary(paper, "research_problem")
    assert result == "字符串类型的字段"


def test_extract_dimension_summary_none():
    """None/缺失 → 返回 '论文未明确提及'"""
    llm, pm = _make_mock_services()
    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

    paper = {}
    result = agent._extract_dimension_summary(paper, "research_problem")
    assert result == FALLBACK_NOTE


# ============================================================
# FR-007：_calculate_similarity
# ============================================================


def test_calculate_similarity_identical():
    """相同文本 → 1.0"""
    llm, pm = _make_mock_services()
    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

    text = "多智能体强化学习算法"
    sim = agent._calculate_similarity(text, text)
    assert sim == 1.0


def test_calculate_similarity_completely_different():
    """完全不同文本 → < 0.3"""
    llm, pm = _make_mock_services()
    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

    sim = agent._calculate_similarity("多智能体强化学习算法", "计算机视觉图像识别")
    assert sim < 0.3


# ============================================================
# FR-008：_detect_conflict_keywords
# ============================================================


def test_detect_conflict_keywords_chinese():
    """检测中文矛盾关键词"""
    llm, pm = _make_mock_services()
    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

    text1 = "本文方法效果很好，但是计算开销较大"
    text2 = "本文方法效果良好，然而训练时间长"

    found = agent._detect_conflict_keywords(text1, text2)
    assert "但是" in found
    assert "然而" in found


def test_detect_conflict_keywords_english():
    """检测英文矛盾关键词"""
    llm, pm = _make_mock_services()
    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

    text1 = "The method works well, however it has limitations"
    text2 = "We propose a different approach, unlike previous work"

    found = agent._detect_conflict_keywords(text1, text2)
    assert "however" in [f.lower() for f in found]
    assert "unlike" in [f.lower() for f in found]


# ============================================================
# FR-009：_summarize_comparison
# ============================================================


def test_summarize_comparison():
    """_summarize_comparison 生成 '对比 N 篇论文: M 个相似点, K 个差异, L 个矛盾' 摘要"""
    llm, pm = _make_mock_services()
    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

    result = {
        "paper_count": 5,
        "comparison_matrix": {
            "similarities": [{}] * 10,
            "differences": [{}] * 8,
        },
        "contradictions": [{}] * 2,
    }

    summary = agent._summarize_comparison(result)
    assert "5 篇论文" in summary
    assert "10 个相似点" in summary
    assert "8 个差异" in summary
    assert "2 个矛盾" in summary


# ============================================================
# FR-003：_run 正常流程
# ============================================================


@pytest.mark.asyncio
async def test_run_success_flow():
    """正常 LLM 流程：3 篇论文 → 返回完整结构"""
    llm, pm = _make_mock_services(llm_output=VALID_COMPARISON_JSON)
    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

    input_data = {"analysis_results": SAMPLE_3_PAPERS}
    context = {"user_profile": SAMPLE_USER_PROFILE}

    result = await agent._run("", input_data, context)

    assert "comparison_matrix" in result
    assert result["paper_count"] == 3
    assert result["agent"] == "comparer"
    assert AI_DISCLAIMER in result["summary"]


# ============================================================
# FR-015：入口校验
# ============================================================


@pytest.mark.asyncio
async def test_run_with_single_paper_returns_empty():
    """1 篇论文 → 返回空对比结构"""
    llm, pm = _make_mock_services()
    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

    input_data = {"analysis_results": SAMPLE_3_PAPERS[:1]}
    context = {"user_profile": SAMPLE_USER_PROFILE}

    result = await agent._run("", input_data, context)

    assert result["paper_count"] == 1
    assert "无需对比" in result["summary"] or result["paper_count"] < MIN_PAPERS


@pytest.mark.asyncio
async def test_run_with_too_many_papers_truncates():
    """6 篇论文 → 截断到 5 篇"""
    llm, pm = _make_mock_services(llm_output=VALID_COMPARISON_JSON)
    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

    too_many = [_make_paper(f"paper_{i}", f"Paper {i}", "结论X") for i in range(6)]
    input_data = {"analysis_results": too_many}
    context = {"user_profile": SAMPLE_USER_PROFILE}

    result = await agent._run("", input_data, context)

    assert result["paper_count"] == MAX_PAPERS


# ============================================================
# FR-010 / FA-009：降级路径
# ============================================================


@pytest.mark.asyncio
async def test_run_llm_failure_fallback():
    """LLM 调用失败 → 降级到 _rule_based_comparison"""
    llm, pm = _make_mock_services(llm_side_effect=RuntimeError("LLM timeout"))
    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

    input_data = {"analysis_results": SAMPLE_3_PAPERS}
    context = {"user_profile": SAMPLE_USER_PROFILE}

    result = await agent._run("test prompt", input_data, context)

    assert result["degraded"] is True
    assert result["agent"] == "comparer"
    assert "comparison_matrix" in result


@pytest.mark.asyncio
async def test_run_llm_empty_output_fallback():
    """LLM 空输出 → 降级到 _rule_based_comparison"""
    llm, pm = _make_mock_services(llm_output="")
    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

    input_data = {"analysis_results": SAMPLE_3_PAPERS}
    context = {"user_profile": SAMPLE_USER_PROFILE}

    result = await agent._run("test prompt", input_data, context)

    assert result["degraded"] is True
    assert "comparison_matrix" in result


def test_fallback_result_preserves_langgraph_flow():
    """_fallback_result 返回 4 维度结构"""
    llm, pm = _make_mock_services()
    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

    input_data = {"analysis_results": SAMPLE_3_PAPERS}
    agent.state.error = "test error"

    result = agent._fallback_result(input_data)

    assert "comparison_matrix" in result
    assert result["comparison_matrix"]["dimensions"] == list(COMPARE_DIMENSIONS)
    assert result["degraded"] is True


# ============================================================
# FR-012：AI 免责声明
# ============================================================


def test_ai_disclaimer_in_summary():
    """summary 末尾始终包含 AI 免责声明"""
    llm, pm = _make_mock_services()
    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

    input_data = {"analysis_results": SAMPLE_3_PAPERS}
    result = agent._rule_based_comparison(input_data)

    assert AI_DISCLAIMER in result["summary"]


# ============================================================
# FR-011：_summarize_result
# ============================================================


def test_summarize_result():
    """_summarize_result 返回英文摘要格式"""
    llm, pm = _make_mock_services()
    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

    result = {
        "paper_count": 3,
        "comparison_matrix": {
            "similarities": [{}] * 5,
            "differences": [{}] * 4,
        },
        "contradictions": [{}] * 1,
    }

    summary = agent._summarize_result(result)

    assert "Compared 3 papers" in summary
    assert "5 similarities" in summary
    assert "4 differences" in summary
    assert "1 contradictions" in summary


# ============================================================
# 集成测试：与真实 PromptManager 配合
# ============================================================


@pytest.mark.asyncio
async def test_comparer_with_prompt_manager():
    """集成测试：ComparerAgent 与真实 PromptManager 配合"""
    from app.services.prompt_manager import PromptManager

    pm = PromptManager("prompts")
    await pm.load_templates()

    llm = AsyncMock()
    llm.generate = AsyncMock(return_value=VALID_COMPARISON_JSON)

    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

    input_data = {"analysis_results": SAMPLE_3_PAPERS}
    context = {"user_profile": SAMPLE_USER_PROFILE}

    prompt = agent.build_prompt(input_data, context)

    assert "comparer" in pm.list_templates()
    assert prompt != ""
    assert isinstance(prompt, str)


@pytest.mark.asyncio
async def test_comparer_with_analyzer_chain():
    """集成测试：AnalyzerAgent → ComparerAgent 完整链路"""
    from app.services.prompt_manager import PromptManager

    pm = PromptManager("prompts")
    await pm.load_templates()

    llm = AsyncMock()
    llm.generate = AsyncMock(return_value=VALID_COMPARISON_JSON)

    from app.agents.comparer import ComparerAgent

    agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

    # 模拟 AnalyzerAgent 输出 → ComparerAgent 输入
    analyzer_output = {
        "analysis_results": SAMPLE_3_PAPERS,
    }

    result = await agent._run(
        "",
        analyzer_output,
        {"user_profile": SAMPLE_USER_PROFILE},
    )

    # 验证 ContrarianAgent 输出供 GeneratorAgent 消费
    assert "comparison_matrix" in result
    assert "contradictions" in result
    assert "summary" in result
    assert result["paper_count"] == 3
    # GeneratorAgent 消费的字段
    assert "dimensions" in result["comparison_matrix"]
    assert "papers" in result["comparison_matrix"]