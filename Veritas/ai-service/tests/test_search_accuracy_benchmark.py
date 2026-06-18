"""task48 检索准确率基准测试 - 单元测试

验证：
1. 基准脚本可执行（Mock 模式）
2. MRR 计算正确
3. nDCG 计算正确
4. Recall 计算正确
5. test_queries.json 格式校验
"""
import asyncio
import json
import math
import os
import sys
from pathlib import Path

import pytest

# 确保项目根目录在 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tests.benchmark.search_accuracy_benchmark import (
    SearchAccuracyBenchmark,
    calc_mrr,
    calc_ndcg,
    calc_recall,
    calc_topk_accuracy,
)


# ===== 测试数据 =====

QUERIES_PATH = Path(__file__).parent / "benchmark" / "test_queries.json"
EXPECTED_PATH = Path(__file__).parent / "benchmark" / "expected_results.json"


# ===== 测试 1: 基准脚本可执行（Mock 模式） =====


class TestBenchmarkExecutable:
    def test_benchmark_runs_with_mock(self):
        """测试基准脚本在 Mock 模式下可正常运行"""
        benchmark = SearchAccuracyBenchmark(str(QUERIES_PATH), str(EXPECTED_PATH))
        asyncio.run(benchmark.setup(use_mock=True))
        results = asyncio.run(benchmark.run_benchmark())

        # 验证三种方法都有结果
        assert "semantic" in results
        assert "keyword" in results
        assert "hybrid" in results

        # 验证每个方法都有完整指标
        for method in ["semantic", "keyword", "hybrid"]:
            metrics = results[method]
            assert "mrr" in metrics
            assert "ndcg10" in metrics
            assert "recall10" in metrics
            assert "top5_acc" in metrics
            assert "top10_acc" in metrics
            assert 0.0 <= metrics["mrr"] <= 1.0
            assert 0.0 <= metrics["ndcg10"] <= 1.0
            assert 0.0 <= metrics["recall10"] <= 1.0
            assert 0.0 <= metrics["top5_acc"] <= 1.0


# ===== 测试 2: MRR 计算正确 =====


class TestMRRCalculation:
    def test_mrr_first_position(self):
        """相关结果在第 1 位，MRR=1.0"""
        results = [{"paper_id": "p1"}, {"paper_id": "p2"}]
        relevant = {"p1"}
        assert calc_mrr(results, relevant) == 1.0

    def test_mrr_second_position(self):
        """相关结果在第 2 位，MRR=0.5"""
        results = [{"paper_id": "p2"}, {"paper_id": "p1"}]
        relevant = {"p1"}
        assert calc_mrr(results, relevant) == 0.5

    def test_mrr_not_found(self):
        """相关结果不在列表中，MRR=0.0"""
        results = [{"paper_id": "p2"}, {"paper_id": "p3"}]
        relevant = {"p1"}
        assert calc_mrr(results, relevant) == 0.0

    def test_mrr_empty_results(self):
        """空结果，MRR=0.0"""
        assert calc_mrr([], {"p1"}) == 0.0


# ===== 测试 3: nDCG 计算正确 =====


class TestNDCGCalculation:
    def test_ndcg_ideal_order(self):
        """理想排序（高相关在前），nDCG=1.0"""
        results = [{"paper_id": "p1"}, {"paper_id": "p2"}]
        relevance = {"p1": 3, "p2": 2}
        ndcg = calc_ndcg(results, relevance, k=10)
        assert ndcg == pytest.approx(1.0, abs=1e-6)

    def test_ndcg_suboptimal_order(self):
        """次优排序（低相关在前），nDCG<1.0"""
        results = [{"paper_id": "p2"}, {"paper_id": "p1"}]
        relevance = {"p1": 3, "p2": 2}
        ndcg = calc_ndcg(results, relevance, k=10)
        assert 0.0 < ndcg < 1.0

    def test_ndcg_no_relevant(self):
        """无相关结果，nDCG=0.0"""
        results = [{"paper_id": "p1"}]
        relevance = {"p2": 3}
        assert calc_ndcg(results, relevance, k=10) == 0.0


# ===== 测试 4: Recall 计算正确 =====


class TestRecallCalculation:
    def test_recall_all_found(self):
        """所有相关结果都被检索到，Recall=1.0"""
        results = [{"paper_id": "p1"}, {"paper_id": "p2"}]
        relevant = {"p1", "p2"}
        assert calc_recall(results, relevant, k=10) == 1.0

    def test_recall_partial(self):
        """部分相关结果被检索到"""
        results = [{"paper_id": "p1"}, {"paper_id": "p3"}]
        relevant = {"p1", "p2"}
        assert calc_recall(results, relevant, k=10) == 0.5

    def test_recall_none_found(self):
        """无相关结果被检索到，Recall=0.0"""
        results = [{"paper_id": "p3"}, {"paper_id": "p4"}]
        relevant = {"p1", "p2"}
        assert calc_recall(results, relevant, k=10) == 0.0

    def test_recall_topk_limit(self):
        """k 限制生效"""
        results = [{"paper_id": "p1"}, {"paper_id": "p2"}, {"paper_id": "p3"}]
        relevant = {"p3"}
        # k=2 时 p3 不在 Top2
        assert calc_recall(results, relevant, k=2) == 0.0
        # k=3 时 p3 在 Top3
        assert calc_recall(results, relevant, k=3) == 1.0


# ===== 测试 5: test_queries.json 格式校验 =====


class TestQueriesFormat:
    def test_queries_json_valid_format(self):
        """test_queries.json 格式校验"""
        with open(QUERIES_PATH, "r", encoding="utf-8") as f:
            queries = json.load(f)

        assert isinstance(queries, list)
        assert len(queries) == 20  # 20 条查询

        zh_count = 0
        en_count = 0
        for q in queries:
            # 必填字段
            assert "id" in q, f"查询缺少 id 字段: {q}"
            assert "query" in q, f"查询缺少 query 字段: {q}"
            assert "language" in q, f"查询缺少 language 字段: {q}"
            assert "expected_top10" in q, f"查询缺少 expected_top10 字段: {q}"
            assert "relevance_scores" in q, f"查询缺少 relevance_scores 字段: {q}"

            # language 必须是 zh 或 en
            assert q["language"] in ("zh", "en"), f"language 必须是 zh/en: {q['language']}"

            if q["language"] == "zh":
                zh_count += 1
            else:
                en_count += 1

            # expected_top10 必须是列表
            assert isinstance(q["expected_top10"], list), "expected_top10 必须是列表"

            # relevance_scores 必须是字典
            assert isinstance(q["relevance_scores"], dict), "relevance_scores 必须是字典"

            # paper_id 格式校验（arxiv_ 开头）
            for pid in q["expected_top10"]:
                assert pid.startswith("arxiv_"), f"paper_id 格式错误: {pid}"

            # relevance_scores 的值在 0-3
            for pid, score in q["relevance_scores"].items():
                assert 0 <= score <= 3, f"relevance_score 超出范围: {pid}={score}"

        # 中文 10 + 英文 10
        assert zh_count == 10, f"中文查询数应为 10，实际 {zh_count}"
        assert en_count == 10, f"英文查询数应为 10，实际 {en_count}"

    def test_expected_results_json_valid_format(self):
        """expected_results.json 格式校验"""
        with open(EXPECTED_PATH, "r", encoding="utf-8") as f:
            expected = json.load(f)

        assert "queries" in expected
        assert isinstance(expected["queries"], list)
        assert len(expected["queries"]) == 20

        for q in expected["queries"]:
            assert "id" in q
            assert "query" in q
            assert "expected_top10" in q
            assert isinstance(q["expected_top10"], list)

            for item in q["expected_top10"]:
                assert "paper_id" in item
                assert "relevance_score" in item
                assert 0 <= item["relevance_score"] <= 3
                assert item["paper_id"].startswith("arxiv_")
