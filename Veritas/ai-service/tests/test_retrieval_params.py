"""task54 检索参数优化测试

验证：
1. SEARCH_TOP_K 环境变量覆盖
2. similarity_threshold 过滤生效
3. threshold=0.0 不过滤
4. CHUNK_SIZE 环境变量覆盖
5. 调优脚本输出 Markdown 报告
"""
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest


# ===== 测试 1: SEARCH_TOP_K 环境变量覆盖 =====


class TestSearchTopKFromSettings:
    def test_top_k_from_settings(self):
        """SEARCH_TOP_K=15 环境变量覆盖默认值 10"""
        from app.core.config import Settings

        # 模拟环境变量
        with patch.dict(os.environ, {"SEARCH_TOP_K": "15"}):
            settings = Settings()
            assert settings.SEARCH_TOP_K == 15

    def test_top_k_default_value(self):
        """未设置环境变量时 SEARCH_TOP_K 默认 10"""
        from app.core.config import Settings

        with patch.dict(os.environ, {}, clear=False):
            # 临时移除环境变量
            old_val = os.environ.pop("SEARCH_TOP_K", None)
            try:
                settings = Settings()
                assert settings.SEARCH_TOP_K == 10
            finally:
                if old_val is not None:
                    os.environ["SEARCH_TOP_K"] = old_val


# ===== 测试 2: similarity_threshold 过滤 =====


class TestSimilarityThresholdFilter:
    def test_similarity_threshold_filter(self):
        """threshold=0.3 时低于阈值的结果不返回"""
        from app.services.vector_store_service import VectorStoreService

        service = VectorStoreService(settings=MagicMock())
        # Mock collection.query 返回 3 条结果，distance 不同
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["p1", "p2", "p3"]],
            "metadatas": [[
                {"paper_id": "p1", "title": "T1", "year": 2024, "venue": "v1", "citation_count": 10},
                {"paper_id": "p2", "title": "T2", "year": 2023, "venue": "v2", "citation_count": 5},
                {"paper_id": "p3", "title": "T3", "year": 2022, "venue": "v3", "citation_count": 1},
            ]],
            "distances": [[0.2, 0.6, 0.9]],  # similarity = 0.8, 0.4, 0.1
            "documents": [["abstract1", "abstract2", "abstract3"]],
        }
        service.collection = mock_collection

        # threshold=0.5：只保留 similarity >= 0.5 的（即 p1, similarity=0.8）
        results = asyncio.run(service.search(
            embedding=[0.1] * 1024,
            top_k=10,
            similarity_threshold=0.5,
        ))

        # p1 (sim=0.8) 保留；p2 (sim=0.4) 过滤；p3 (sim=0.1) 过滤
        assert len(results) == 1
        assert results[0]["paperId"] == "p1"

    def test_similarity_threshold_zero_no_filter(self):
        """threshold=0.0 时不过滤，返回全部结果"""
        from app.services.vector_store_service import VectorStoreService

        service = VectorStoreService(settings=MagicMock())
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["p1", "p2", "p3"]],
            "metadatas": [[
                {"paper_id": "p1", "title": "T1", "year": 2024, "venue": "v1", "citation_count": 10},
                {"paper_id": "p2", "title": "T2", "year": 2023, "venue": "v2", "citation_count": 5},
                {"paper_id": "p3", "title": "T3", "year": 2022, "venue": "v3", "citation_count": 1},
            ]],
            "distances": [[0.2, 0.6, 0.9]],
            "documents": [["abstract1", "abstract2", "abstract3"]],
        }
        service.collection = mock_collection

        # threshold=0.0：不过滤，返回全部 3 条
        results = asyncio.run(service.search(
            embedding=[0.1] * 1024,
            top_k=10,
            similarity_threshold=0.0,
        ))

        assert len(results) == 3


# ===== 测试 4: CHUNK_SIZE 环境变量覆盖 =====


class TestChunkSizeConfig:
    def test_chunk_size_config(self):
        """CHUNK_SIZE=256 环境变量覆盖默认值 512"""
        from app.core.config import Settings

        with patch.dict(os.environ, {"CHUNK_SIZE": "256"}):
            settings = Settings()
            assert settings.CHUNK_SIZE == 256

    def test_chunk_size_default(self):
        """CHUNK_SIZE 默认 512"""
        from app.core.config import Settings

        old_val = os.environ.pop("CHUNK_SIZE", None)
        try:
            settings = Settings()
            assert settings.CHUNK_SIZE == 512
        finally:
            if old_val is not None:
                os.environ["CHUNK_SIZE"] = old_val


# ===== 测试 5: 调优脚本输出 Markdown 报告 =====


class TestTuneScriptOutput:
    def test_tune_script_output(self):
        """调优脚本输出 Markdown 报告含 16 组合对比表"""
        from scripts.tune_retrieval_params import RetrievalParamTuner, TOP_K_GRID, THRESHOLD_GRID

        queries_path = "tests/benchmark/test_queries.json"
        expected_path = "tests/benchmark/expected_results.json"

        tuner = RetrievalParamTuner(queries_path, expected_path)
        results = asyncio.run(tuner.run_grid_search(use_mock=True))

        # 应有 16 组合（4 × 4）
        assert len(results) == len(TOP_K_GRID) * len(THRESHOLD_GRID)

        # 生成报告
        report = tuner.generate_report(results)

        # 报告应包含关键内容
        assert "# task54 检索参数调优报告" in report
        assert "组合对比表" in report
        assert "Top5 准确率" in report
        assert "最优组合" in report
        assert "AM5 硬指标" in report

        # 应有 16 行数据（不含表头）
        data_lines = [
            line for line in report.split("\n")
            if line.startswith("| ") and "top_k" not in line
        ]
        assert len(data_lines) == 16

    def test_tune_script_pass_threshold(self):
        """调优脚本 Mock 模式下最优组合 Top5 准确率 > 85%"""
        from scripts.tune_retrieval_params import RetrievalParamTuner

        tuner = RetrievalParamTuner(
            "tests/benchmark/test_queries.json",
            "tests/benchmark/expected_results.json",
        )
        results = asyncio.run(tuner.run_grid_search(use_mock=True))
        best = max(results, key=lambda x: x["top5_accuracy"])
        # Mock 模式下合理参数组合应 > 85%
        assert best["top5_accuracy"] > 0.85
