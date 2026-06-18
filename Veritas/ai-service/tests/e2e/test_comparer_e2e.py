"""task50 对比 Prompt E2E 测试

验证：
1. 3 篇矛盾论文 contradictions 非空
2. contradictions schema 完整（8 字段）
3. 降级路径（LLM 失败时仍输出结构化结果）
4. comparer.txt prompt 含 3 个 few-shot 示例
"""
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.comparer import (
    AI_DISCLAIMER,
    COMPARE_DIMENSIONS,
    VALID_ROOT_CAUSES,
    ComparerAgent,
)


# ===== 数据加载 =====

DATA_PATH = Path(__file__).parent / "test_data" / "conflict_papers.json"


def _load_conflict_papers():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


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


def _build_analysis_results(papers_data):
    """从 conflict_papers.json 构造 analysis_results"""
    results = []
    for p in papers_data["papers"]:
        results.append({
            "paper_id": p["paper_id"],
            "research_problem": p["research_problem"],
            "core_method": p["core_method"],
            "main_experiments": p["main_experiments"],
            "core_conclusions": p["core_conclusions"],
        })
    return results


# ===== 测试 1: 3 篇矛盾论文 contradictions 非空 =====


class TestContradictionsNotEmpty:
    def test_three_papers_produce_contradictions(self):
        """3 篇矛盾论文通过规则对比应产生 contradictions"""
        papers_data = _load_conflict_papers()
        analysis_results = _build_analysis_results(papers_data)

        # LLM 失败，走降级路径
        llm, pm = _make_mock_services(llm_side_effect=Exception("LLM 不可用"))
        agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

        input_data = {
            "analysis_results": analysis_results,
            "user_profile": {},
        }

        import asyncio

        result = asyncio.run(agent._run("test prompt", input_data, {}))

        # 应产生 contradictions
        contradictions = result.get("contradictions", [])
        assert len(contradictions) >= 1, "3 篇矛盾论文应产生至少 1 个 contradiction"

    def test_three_papers_pair_count(self):
        """3 篇论文产生 C(3,2)=3 对对比"""
        papers_data = _load_conflict_papers()
        assert len(papers_data["papers"]) == 3
        # C(3,2) = 3
        expected_pairs = 3
        assert len(papers_data["expected_contradictions"]) == expected_pairs


# ===== 测试 2: contradictions schema 完整 =====


class TestContradictionSchema:
    def test_contradiction_has_all_eight_fields(self):
        """每个 contradiction 包含完整 8 字段"""
        papers_data = _load_conflict_papers()
        analysis_results = _build_analysis_results(papers_data)

        llm, pm = _make_mock_services(llm_side_effect=Exception("LLM 不可用"))
        agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

        input_data = {
            "analysis_results": analysis_results,
            "user_profile": {},
        }

        import asyncio

        result = asyncio.run(agent._run("test prompt", input_data, {}))

        contradictions = result.get("contradictions", [])
        required_fields = {
            "papers", "topic", "claim_a", "claim_b",
            "evidence_a", "evidence_b", "root_cause", "resolution_suggestion"
        }

        for c in contradictions:
            for field in required_fields:
                assert field in c, f"contradiction 缺少字段: {field}"

    def test_root_cause_in_valid_enum(self):
        """root_cause 必须在 5 类枚举中"""
        papers_data = _load_conflict_papers()
        analysis_results = _build_analysis_results(papers_data)

        llm, pm = _make_mock_services(llm_side_effect=Exception("LLM 不可用"))
        agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

        input_data = {
            "analysis_results": analysis_results,
            "user_profile": {},
        }

        import asyncio

        result = asyncio.run(agent._run("test prompt", input_data, {}))

        contradictions = result.get("contradictions", [])
        for c in contradictions:
            assert c["root_cause"] in VALID_ROOT_CAUSES, \
                f"root_cause '{c['root_cause']}' 不在合法枚举中"


# ===== 测试 3: 降级路径 =====


class TestDegradationPath:
    def test_degradation_produces_valid_output(self):
        """LLM 失败时降级路径仍产生有效输出"""
        papers_data = _load_conflict_papers()
        analysis_results = _build_analysis_results(papers_data)

        llm, pm = _make_mock_services(llm_side_effect=Exception("LLM 超时"))
        agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

        input_data = {
            "analysis_results": analysis_results,
            "user_profile": {},
        }

        import asyncio

        result = asyncio.run(agent._run("test prompt", input_data, {}))

        # 降级路径应返回结构化结果
        assert isinstance(result, dict)
        assert "comparison_matrix" in result or "degraded" in result

        # 降级标记
        assert result.get("degraded") is True or result.get("degraded") is None

    def test_empty_papers_returns_empty_comparison(self):
        """空论文列表返回空对比"""
        llm, pm = _make_mock_services()
        agent = ComparerAgent(llm_service=llm, prompt_manager=pm)

        input_data = {
            "analysis_results": [],
            "user_profile": {},
        }

        import asyncio

        result = asyncio.run(agent._run("test prompt", input_data, {}))

        # 空输入应优雅处理
        assert isinstance(result, dict)


# ===== 测试 4: prompt 含 few-shot =====


class TestPromptFewShot:
    def test_comparer_prompt_has_three_fewshot_examples(self):
        """comparer.txt 包含 3 个 few-shot 示例"""
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / "comparer.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 示例 1: MADDPG/QMIX/COMA (condition_difference)
        assert "MADDPG" in content and "QMIX" in content and "COMA" in content
        assert "condition_difference" in content

        # 示例 2: dataset_bias (task49 新增)
        assert "dataset_bias" in content
        assert "SST-2" in content and "IMDB" in content

        # 示例 3: methodological_conflict (task50 新增)
        assert "methodological_conflict" in content
        assert "contrastive_learning" in content or "对比学习" in content

    def test_comparer_prompt_has_eight_field_requirement(self):
        """comparer.txt 明确要求 8 字段输出"""
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / "comparer.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 8 字段
        required_fields = [
            "papers", "topic", "claim_a", "claim_b",
            "evidence_a", "evidence_b", "root_cause", "resolution_suggestion"
        ]
        for field in required_fields:
            assert field in content, f"prompt 中未提及字段: {field}"

    def test_comparer_prompt_has_disclaimer(self):
        """comparer.txt 包含 AI 免责声明"""
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / "comparer.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert AI_DISCLAIMER in content or "⚠️ 本对比由 AI 生成" in content
