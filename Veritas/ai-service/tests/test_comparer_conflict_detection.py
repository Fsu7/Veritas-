"""task49 矛盾检测增强测试

验证：
1. 5 类根因各 1 测试（dataset_bias / metric_difference / condition_difference / assumption_difference / methodological_conflict）
2. should_compare 3 场景（paper_count<2 跳过 / paper_count>=2 且 requires_compare=True / requires_compare=False）
3. 降级路径（LLM 失败时 _rule_based_comparison 仍能输出）
4. 数值矛盾检测（_detect_conflicts 识别提升 vs 下降）
"""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.base import AgentStatus
from app.agents.comparer import (
    COMPARE_DIMENSIONS,
    DEFAULT_ROOT_CAUSE,
    VALID_ROOT_CAUSES,
    ComparerAgent,
)
from app.agents.graph import should_compare


# ===== Mock 工厂 =====


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
    pm.get_template = MagicMock(return_value="对比模板: $analysis_data")

    return llm, pm


def _make_analysis_result(paper_id, conclusions, method="method_x", experiments="exp1"):
    """构造单篇论文分析结果（维度直接在顶层，与 _extract_dimension_summary 对齐）"""
    return {
        "paper_id": paper_id,
        "research_problem": "测试问题",
        "core_method": method,
        "main_experiments": experiments,
        "core_conclusions": conclusions,
    }


# ===== 测试 1: 5 类根因 =====


class TestRootCauses:
    """验证 5 类矛盾根因枚举完整"""

    def test_all_five_root_causes_defined(self):
        """5 类根因均已定义"""
        expected = {
            "dataset_bias",
            "metric_difference",
            "condition_difference",
            "assumption_difference",
            "methodological_conflict",
        }
        assert VALID_ROOT_CAUSES == expected

    def test_default_root_cause_is_methodological_conflict(self):
        """默认根因为 methodological_conflict"""
        assert DEFAULT_ROOT_CAUSE == "methodological_conflict"

    def test_root_cause_dataset_bias_in_prompt(self):
        """dataset_bias 根因在 comparer.txt 中有 few-shot 示例"""
        with open("prompts/comparer.txt", "r", encoding="utf-8") as f:
            content = f.read()
        assert "dataset_bias" in content
        assert "SST-2" in content and "IMDB" in content

    def test_root_cause_condition_difference_in_prompt(self):
        """condition_difference 根因在 comparer.txt 中有 few-shot 示例"""
        with open("prompts/comparer.txt", "r", encoding="utf-8") as f:
            content = f.read()
        assert "condition_difference" in content

    def test_root_cause_methodological_conflict_in_prompt(self):
        """methodological_conflict 根因在 comparer.txt 中有提及"""
        with open("prompts/comparer.txt", "r", encoding="utf-8") as f:
            content = f.read()
        assert "methodological_conflict" in content


# ===== 测试 2: should_compare 3 场景 =====


class TestShouldCompare:
    """验证 graph.py should_compare 条件分支"""

    def test_skip_compare_when_paper_count_less_than_2(self):
        """paper_count < 2 跳过对比"""
        state = {"requires_compare": True, "search_results": [{"paper_id": "p1"}]}
        result = should_compare(state)
        assert result == "generate"

    def test_compare_when_paper_count_ge_2_and_requires_compare_true(self):
        """paper_count >= 2 且 requires_compare=True 进入对比"""
        state = {
            "requires_compare": True,
            "search_results": [{"paper_id": "p1"}, {"paper_id": "p2"}],
        }
        result = should_compare(state)
        assert result == "compare"

    def test_skip_compare_when_requires_compare_false(self):
        """requires_compare=False 跳过对比（即使论文数 >= 2）"""
        state = {
            "requires_compare": False,
            "search_results": [{"paper_id": "p1"}, {"paper_id": "p2"}],
        }
        result = should_compare(state)
        assert result == "generate"


# ===== 测试 3: 降级路径 =====


class TestDegradationPath:
    """验证 LLM 失败时降级到 _rule_based_comparison"""

    def test_fallback_to_rule_based_when_llm_fails(self):
        """LLM 失败时降级到规则对比"""
        llm, pm = _make_mock_services(llm_side_effect=Exception("LLM 超时"))
        agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

        input_data = {
            "analysis_results": [
                _make_analysis_result("p1", "方法X提升20%"),
                _make_analysis_result("p2", "方法X下降15%"),
            ],
            "user_profile": {},
        }

        result = asyncio_run(agent._run("test prompt", input_data, {}))

        # 降级路径应返回结构化结果
        assert isinstance(result, dict)
        assert "comparison_matrix" in result or "degraded" in result

    def test_rule_based_comparison_detects_contradictions(self):
        """规则对比能检测到矛盾"""
        llm, pm = _make_mock_services(llm_side_effect=Exception("LLM 失败"))
        agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

        input_data = {
            "analysis_results": [
                _make_analysis_result("p1", "方法X提升20%，优于基线"),
                _make_analysis_result("p2", "方法X下降15%，劣于基线"),
            ],
            "user_profile": {},
        }

        result = asyncio_run(agent._run("test prompt", input_data, {}))

        # 应检测到矛盾（数值或方向）
        contradictions = result.get("contradictions", [])
        assert len(contradictions) >= 1


# ===== 测试 4: 数值矛盾检测 =====


class TestNumericConflictDetection:
    """验证 _detect_conflicts 数值/方向矛盾检测"""

    def test_detect_numeric_conflict_increase_vs_decrease(self):
        """检测数值矛盾：提升 vs 下降"""
        llm, pm = _make_mock_services()
        agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

        text1 = "方法X在数据集D上提升 20%，效果显著"
        text2 = "方法X在数据集D上下降 15%，效果不佳"

        conflicts = agent._detect_conflicts(text1, text2)

        # 应检测到数值矛盾
        numeric_conflicts = [c for c in conflicts if c["type"] == "numeric"]
        assert len(numeric_conflicts) >= 1
        assert "数值方向相反" in numeric_conflicts[0]["keywords"]

    def test_detect_directional_conflict_better_vs_worse(self):
        """检测方向矛盾：优于 vs 劣于"""
        llm, pm = _make_mock_services()
        agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

        text1 = "方法X优于基线方法"
        text2 = "方法X劣于基线方法"

        conflicts = agent._detect_conflicts(text1, text2)

        # 应检测到方向矛盾
        directional_conflicts = [c for c in conflicts if c["type"] == "directional"]
        assert len(directional_conflicts) >= 1

    def test_detect_keyword_conflict_still_works(self):
        """关键词矛盾检测仍正常工作（向后兼容）"""
        llm, pm = _make_mock_services()
        agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

        text1 = "方法A效果好，然而成本高"
        text2 = "方法B成本低，但是效果一般"

        conflicts = agent._detect_conflicts(text1, text2)

        # 应检测到关键词矛盾
        keyword_conflicts = [c for c in conflicts if c["type"] == "keyword"]
        assert len(keyword_conflicts) >= 1

    def test_no_conflict_when_texts_aligned(self):
        """两段文本一致时无矛盾"""
        llm, pm = _make_mock_services()
        agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

        text1 = "方法X提升 20%，效果显著"
        text2 = "方法X提升 20%，效果显著"

        conflicts = agent._detect_conflicts(text1, text2)

        # 无数值/方向矛盾（关键词矛盾可能仍触发，但 numeric/directional 应为空）
        numeric_conflicts = [c for c in conflicts if c["type"] == "numeric"]
        directional_conflicts = [c for c in conflicts if c["type"] == "directional"]
        assert len(numeric_conflicts) == 0
        assert len(directional_conflicts) == 0


# ===== 辅助函数 =====


def asyncio_run(coro):
    """同步运行异步函数"""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is None:
        return asyncio.run(coro)
    else:
        # 已有事件循环时，创建新 loop 运行
        import threading

        result = []

        def run():
            new_loop = asyncio.new_event_loop()
            try:
                result.append(new_loop.run_until_complete(coro))
            finally:
                new_loop.close()

        t = threading.Thread(target=run)
        t.start()
        t.join()
        return result[0] if result else None
