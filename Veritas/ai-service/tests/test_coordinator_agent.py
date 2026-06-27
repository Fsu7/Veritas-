"""CoordinatorAgent 单元测试 — task32 测试覆盖

按 task32_coordinator_agent_core/prompt.json test_requirements 逐个实现：
- normal_flow / boundary_condition / error_flow / degradation
"""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.base import AgentStatus, BaseAgent
from app.agents.coordinator import (
    DEFAULT_ANALYSIS_TYPE,
    DEFAULT_DIMENSIONS,
    DEFAULT_TOP_K,
    MAX_QUERY_LENGTH,
    MAX_SUB_TASKS,
    MIN_SUB_TASKS,
    VALID_TASK_TYPES,
    CoordinatorAgent,
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
        return_value="coordinator prompt: query=$query, user_profile=$user_profile, paper_ids=$paper_ids, analysis_type=$analysis_type"
    )
    return llm, pm


SAMPLE_USER_PROFILE = {
    "education_level": "master",
    "research_field": "NLP",
    "knowledge_level": "intermediate",
    "preferred_style": "balanced",
}

SAMPLE_USER_PROFILE_CAMEL = {
    "educationLevel": "phd",
    "knowledgeLevel": "advanced",
    "preferredStyle": "technical",
    "researchField": "RL",
}


VALID_BREAKDOWN_JSON = json.dumps({
    "sub_tasks": [
        {"task_type": "retrieve", "description": "检索相关论文", "keywords": ["Multi-Agent"], "top_k": 10},
        {"task_type": "analyze", "description": "分析论文", "dimensions": DEFAULT_DIMENSIONS},
        {"task_type": "compare", "description": "对比论文", "required": True},
        {"task_type": "generate", "description": "生成综述", "style": "学术风格"},
        {"task_type": "review", "description": "审核内容", "focus": ["事实核查"]},
    ],
    "reasoning": "完整的多论文对比流程",
})


# ============================================================
# FR-001：继承 BaseAgent
# ============================================================


def test_coordinator_inherits_base_agent():
    """CoordinatorAgent 必须继承 BaseAgent"""
    llm, pm = _make_mock_services()
    agent = CoordinatorAgent(llm_service=llm, prompt_manager=pm)
    assert isinstance(agent, BaseAgent)
    assert agent.name == "coordinator"
    assert agent.timeout == 30  # 默认 AGENT_TIMEOUT


# ============================================================
# FR-002：build_prompt 渲染模板
# ============================================================


def test_build_prompt_renders_template():
    """build_prompt 应调用 prompt_manager.get_prompt('coordinator', ...)"""
    llm, pm = _make_mock_services()
    agent = CoordinatorAgent(llm_service=llm, prompt_manager=pm)

    input_data = {
        "topic": "Multi-Agent协同决策",
        "paper_ids": ["arxiv_2024_001", "arxiv_2024_002"],
        "analysis_type": "report",
    }
    context = {"user_profile": SAMPLE_USER_PROFILE}

    prompt = agent.build_prompt(input_data, context)

    pm.get_prompt.assert_called_once()
    call_args = pm.get_prompt.call_args
    args = call_args[0]
    kwargs = call_args[1]
    assert args[0] == "coordinator"
    assert kwargs["query"] == "Multi-Agent协同决策"
    assert "education_level=master" in kwargs["user_profile"]
    assert "arxiv_2024_001" in kwargs["paper_ids"]
    assert kwargs["analysis_type"] == "report"


def test_build_prompt_with_empty_paper_ids():
    """paper_ids 为空时 prompt 应正常渲染（不报错）"""
    llm, pm = _make_mock_services()
    agent = CoordinatorAgent(llm_service=llm, prompt_manager=pm)

    input_data = {"topic": "test topic", "paper_ids": [], "analysis_type": "report"}
    context = {"user_profile": {}}

    prompt = agent.build_prompt(input_data, context)

    pm.get_prompt.assert_called_once()
    call_args = pm.get_prompt.call_args
    kwargs = call_args[1]
    assert "（用户未指定）" in kwargs["paper_ids"]


# ============================================================
# FR-004：_parse_task_breakdown
# ============================================================


def test_parse_task_breakdown_valid_json():
    """合法 JSON 块 → 解析为子任务列表"""
    llm, pm = _make_mock_services()
    agent = CoordinatorAgent(llm_service=llm, prompt_manager=pm)

    input_data = {"topic": "test", "paper_ids": ["id1", "id2"], "analysis_type": "report"}

    # P3-17.3: _parse_task_breakdown 现在接收已解析的 JSON，需先调用 _extract_json
    parsed_json = agent._extract_json(VALID_BREAKDOWN_JSON)
    result = agent._parse_task_breakdown(parsed_json, input_data)

    assert len(result) == 5
    assert all(t["task_type"] in VALID_TASK_TYPES for t in result)


def test_parse_task_breakdown_invalid_json():
    """非法 JSON → 降级到 _rule_based_decomposition"""
    llm, pm = _make_mock_services()
    agent = CoordinatorAgent(llm_service=llm, prompt_manager=pm)

    input_data = {"topic": "test", "paper_ids": [], "analysis_type": "paper_analysis"}

    # P3-17.3: 非法 JSON 经 _extract_json 返回 None，触发降级
    parsed_json = agent._extract_json("not a json at all !!!")
    result = agent._parse_task_breakdown(parsed_json, input_data)

    # 降级到规则分解：paper_analysis + paper_ids=[] → 2 个子任务
    assert len(result) == 2
    assert result[0]["task_type"] == "retrieve"
    assert result[1]["task_type"] == "analyze"


def test_parse_task_breakdown_filter_invalid_task_types():
    """过滤掉不在 VALID_TASK_TYPES 中的 task_type"""
    llm, pm = _make_mock_services()
    agent = CoordinatorAgent(llm_service=llm, prompt_manager=pm)

    invalid_json = json.dumps({
        "sub_tasks": [
            {"task_type": "retrieve", "description": "ok"},
            {"task_type": "INVALID_TYPE", "description": "should be filtered"},
            {"task_type": "analyze", "description": "ok"},
        ]
    })

    input_data = {"topic": "test", "paper_ids": [], "analysis_type": "report"}
    parsed_json = agent._extract_json(invalid_json)
    result = agent._parse_task_breakdown(parsed_json, input_data)

    types = [t["task_type"] for t in result]
    assert "INVALID_TYPE" not in types
    assert "retrieve" in types
    assert "analyze" in types


def test_parse_task_breakdown_subtask_count_constraint():
    """强制 2-5 子任务约束：< 2 补全，> 5 截断"""
    llm, pm = _make_mock_services()
    agent = CoordinatorAgent(llm_service=llm, prompt_manager=pm)

    # 测试 < 2 → 降级
    few_json = json.dumps({"sub_tasks": [{"task_type": "retrieve", "description": "only one"}]})
    input_data = {"topic": "test", "paper_ids": [], "analysis_type": "report"}
    parsed_json = agent._extract_json(few_json)
    result = agent._parse_task_breakdown(parsed_json, input_data)
    # 降级路径：report + paper_ids=[] → 4 子任务（retrieve/analyze/generate/review）
    assert len(result) >= MIN_SUB_TASKS

    # 测试 > 5 → 截断
    many_json = json.dumps({
        "sub_tasks": [
            {"task_type": "retrieve", "description": f"task {i}"}
            for i in range(10)
        ]
    })
    parsed_json = agent._extract_json(many_json)
    result = agent._parse_task_breakdown(parsed_json, input_data)
    assert len(result) <= MAX_SUB_TASKS


# ============================================================
# FR-005：_rule_based_decomposition
# ============================================================


def test_rule_based_decomposition_paper_analysis():
    """paper_analysis + paper_ids=[] → 2 个子任务 (retrieve, analyze)"""
    llm, pm = _make_mock_services()
    agent = CoordinatorAgent(llm_service=llm, prompt_manager=pm)

    input_data = {"topic": "test topic", "paper_ids": [], "analysis_type": "paper_analysis"}

    result = agent._rule_based_decomposition(input_data)

    assert len(result) == 2
    assert result[0]["task_type"] == "retrieve"
    assert result[1]["task_type"] == "analyze"


def test_rule_based_decomposition_compare_with_multi_papers():
    """compare + paper_ids=[id1, id2] → 5 个子任务（含 review）"""
    llm, pm = _make_mock_services()
    agent = CoordinatorAgent(llm_service=llm, prompt_manager=pm)

    input_data = {"topic": "test", "paper_ids": ["id1", "id2"], "analysis_type": "compare"}

    result = agent._rule_based_decomposition(input_data)

    assert len(result) == 5
    types = [t["task_type"] for t in result]
    assert "retrieve" in types
    assert "analyze" in types
    assert "compare" in types
    assert "generate" in types
    assert "review" in types


def test_rule_based_decomposition_report_with_single_paper():
    """report + paper_ids=[id1] → 4 个子任务（无 compare）"""
    llm, pm = _make_mock_services()
    agent = CoordinatorAgent(llm_service=llm, prompt_manager=pm)

    input_data = {"topic": "test", "paper_ids": ["id1"], "analysis_type": "report"}

    result = agent._rule_based_decomposition(input_data)

    assert len(result) == 4
    types = [t["task_type"] for t in result]
    assert "compare" not in types
    assert "retrieve" in types
    assert "analyze" in types
    assert "generate" in types
    assert "review" in types


def test_rule_based_decomposition_report_with_multi_papers():
    """report + paper_ids=[id1, id2] → 5 个子任务（含 compare）"""
    llm, pm = _make_mock_services()
    agent = CoordinatorAgent(llm_service=llm, prompt_manager=pm)

    input_data = {"topic": "test", "paper_ids": ["id1", "id2"], "analysis_type": "report"}

    result = agent._rule_based_decomposition(input_data)

    assert len(result) == 5
    types = [t["task_type"] for t in result]
    assert "compare" in types


# ============================================================
# FR-006：_determine_required_tasks
# ============================================================


def test_determine_required_tasks_compare():
    """paper_ids=[id1,id2] + analysis_type=compare → requires_compare=True, requires_review=True"""
    llm, pm = _make_mock_services()
    agent = CoordinatorAgent(llm_service=llm, prompt_manager=pm)

    input_data = {"topic": "t", "paper_ids": ["id1", "id2"], "analysis_type": "compare"}

    flags = agent._determine_required_tasks(input_data, [])

    assert flags["requires_compare"] is True
    assert flags["requires_review"] is True
    assert flags["paper_count"] == 2


def test_determine_required_tasks_no_compare():
    """paper_ids=[] + analysis_type=report → requires_compare=False, requires_review=True"""
    llm, pm = _make_mock_services()
    agent = CoordinatorAgent(llm_service=llm, prompt_manager=pm)

    input_data = {"topic": "t", "paper_ids": [], "analysis_type": "report"}

    flags = agent._determine_required_tasks(input_data, [])

    assert flags["requires_compare"] is False
    assert flags["requires_review"] is True
    assert flags["paper_count"] == 0


# ============================================================
# FR-007：_summarize_sub_tasks
# ============================================================


def test_summarize_sub_tasks():
    """_summarize_sub_tasks 生成 '分解为 N 个子任务: ...' 摘要"""
    llm, pm = _make_mock_services()
    agent = CoordinatorAgent(llm_service=llm, prompt_manager=pm)

    # 5 子任务
    sub_tasks = [{"task_type": t} for t in ["retrieve", "analyze", "compare", "generate", "review"]]
    summary = agent._summarize_sub_tasks(sub_tasks)
    assert "5 个子任务" in summary
    assert "retrieve" in summary
    assert "review" in summary

    # 2 子任务
    sub_tasks = [{"task_type": "retrieve"}, {"task_type": "analyze"}]
    summary = agent._summarize_sub_tasks(sub_tasks)
    assert "2 个子任务" in summary
    assert "retrieve" in summary
    assert "analyze" in summary


# ============================================================
# FR-003：_run 正常流程
# ============================================================


@pytest.mark.asyncio
async def test_run_success_flow():
    """正常 LLM 流程：3 篇论文 + report → 返回完整结构"""
    llm, pm = _make_mock_services(llm_output=VALID_BREAKDOWN_JSON)
    agent = CoordinatorAgent(llm_service=llm, prompt_manager=pm)

    input_data = {
        "topic": "Multi-Agent协同决策",
        "paper_ids": ["id1", "id2", "id3"],
        "analysis_type": "report",
    }
    context = {"user_profile": SAMPLE_USER_PROFILE}

    result = await agent._run("", input_data, context)

    assert "sub_tasks" in result
    assert result["task_count"] == 5
    assert result["requires_compare"] is True
    assert result["requires_review"] is True
    assert result["analysis_type"] == "report"
    assert result["paper_count"] == 3
    assert result["agent"] == "coordinator"


# ============================================================
# FR-008 / FA-004 / FA-009：降级路径
# ============================================================


@pytest.mark.asyncio
async def test_run_llm_failure_fallback():
    """LLM 调用失败 → _fallback_result 规则分解降级"""
    llm, pm = _make_mock_services(llm_side_effect=RuntimeError("LLM timeout"))
    agent = CoordinatorAgent(llm_service=llm, prompt_manager=pm)

    input_data = {"topic": "test", "paper_ids": ["id1", "id2"], "analysis_type": "report"}
    context = {"user_profile": SAMPLE_USER_PROFILE}

    result = await agent._run("test prompt", input_data, context)

    assert result["degraded"] is True
    assert result["agent"] == "coordinator"
    assert len(result["sub_tasks"]) >= MIN_SUB_TASKS
    assert result["task_count"] >= MIN_SUB_TASKS


@pytest.mark.asyncio
async def test_run_llm_empty_output_fallback():
    """LLM 返回空字符串 → _rule_based_decomposition 降级"""
    llm, pm = _make_mock_services(llm_output="")
    agent = CoordinatorAgent(llm_service=llm, prompt_manager=pm)

    input_data = {"topic": "test", "paper_ids": ["id1"], "analysis_type": "report"}
    context = {"user_profile": SAMPLE_USER_PROFILE}

    result = await agent._run("test prompt", input_data, context)

    assert result["degraded"] is True
    assert len(result["sub_tasks"]) >= MIN_SUB_TASKS


def test_fallback_result_preserves_langgraph_flow():
    """_fallback_result 返回结构应包含 sub_tasks（>=2 项）"""
    llm, pm = _make_mock_services()
    agent = CoordinatorAgent(llm_service=llm, prompt_manager=pm)

    input_data = {"topic": "test", "paper_ids": ["id1", "id2"], "analysis_type": "report"}
    agent.state.error = "test error"

    result = agent._fallback_result(input_data)

    assert "sub_tasks" in result
    assert len(result["sub_tasks"]) >= MIN_SUB_TASKS
    assert result["degraded"] is True
    assert result["agent"] == "coordinator"


# ============================================================
# FR-010：_infer_style_from_profile
# ============================================================


def test_infer_style_from_profile():
    """_infer_style_from_profile 根据 preferred_style 返回中文风格描述"""
    llm, pm = _make_mock_services()
    agent = CoordinatorAgent(llm_service=llm, prompt_manager=pm)

    assert agent._infer_style_from_profile({"preferred_style": "simple"}) == "通俗风格"
    assert agent._infer_style_from_profile({"preferred_style": "technical"}) == "专业风格"
    assert agent._infer_style_from_profile({"preferred_style": "balanced"}) == "均衡风格"
    assert agent._infer_style_from_profile({}) == "学术风格"
    assert agent._infer_style_from_profile({"preferred_style": "unknown"}) == "学术风格"
    # 兼容 camelCase
    assert agent._infer_style_from_profile({"preferredStyle": "simple"}) == "通俗风格"


# ============================================================
# FR-009：_summarize_result
# ============================================================


def test_summarize_result():
    """_summarize_result 返回 'Decomposed into N sub-tasks: [...]' 格式字符串"""
    llm, pm = _make_mock_services()
    agent = CoordinatorAgent(llm_service=llm, prompt_manager=pm)

    result = {
        "task_count": 5,
        "sub_tasks": [{"task_type": t} for t in ["retrieve", "analyze", "compare", "generate", "review"]],
    }

    summary = agent._summarize_result(result)

    assert "Decomposed into 5 sub-tasks" in summary
    assert "retrieve" in summary
    assert "review" in summary


# ============================================================
# SR-002：_sanitize_topic 防护
# ============================================================


def test_sanitize_topic_length_limit():
    """_sanitize_topic 限制最大长度 MAX_QUERY_LENGTH"""
    llm, pm = _make_mock_services()
    agent = CoordinatorAgent(llm_service=llm, prompt_manager=pm)

    long_topic = "a" * (MAX_QUERY_LENGTH + 100)
    sanitized = agent._sanitize_topic(long_topic)

    assert len(sanitized) <= MAX_QUERY_LENGTH


def test_sanitize_topic_strip_control_chars():
    """_sanitize_topic 移除控制字符"""
    llm, pm = _make_mock_services()
    agent = CoordinatorAgent(llm_service=llm, prompt_manager=pm)

    # 包含控制字符
    dirty = "Multi\x00Agent\x01协同决策\x02"
    sanitized = agent._sanitize_topic(dirty)

    assert "\x00" not in sanitized
    assert "\x01" not in sanitized
    assert "\x02" not in sanitized
    assert "Multi" in sanitized
    assert "Agent" in sanitized


# ============================================================
# 集成测试：与真实 PromptManager 配合
# ============================================================


@pytest.mark.asyncio
async def test_coordinator_with_prompt_manager():
    """集成测试：CoordinatorAgent 与真实 PromptManager 配合"""
    from pathlib import Path

    from app.services.prompt_manager import PromptManager

    pm = PromptManager("prompts")
    await pm.load_templates()

    llm = AsyncMock()
    llm.generate = AsyncMock(return_value=VALID_BREAKDOWN_JSON)

    agent = CoordinatorAgent(llm_service=llm, prompt_manager=pm)

    input_data = {"topic": "test topic", "paper_ids": ["id1"], "analysis_type": "report"}
    context = {"user_profile": SAMPLE_USER_PROFILE}

    prompt = agent.build_prompt(input_data, context)

    # 验证模板已加载
    assert "coordinator" in pm.list_templates()
    # 验证渲染成功
    assert prompt != ""
    assert isinstance(prompt, str)