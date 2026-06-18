"""task47: RRF/Reranker 参数调优测试

验证:
1. RRF_K 从 settings 读取（默认 60，环境变量覆盖）
2. Reranker 权重从 settings 读取
3. 权重归一化校验（和≠1.0 时 warning 不抛异常）
4. 调优脚本可执行
5. _reciprocal_rank_fusion 使用配置的 k 值
"""
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 确保可导入 app 包
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestRRFKFromSettings:
    """测试 RRF_K 从 settings 读取"""

    def test_rrf_k_default_value(self):
        """默认 RRF_K=60"""
        from app.core.config import Settings
        s = Settings(_env_file=None)
        assert s.RRF_K == 60

    def test_rrf_k_env_override(self, monkeypatch):
        """环境变量 RRF_K=90 覆盖默认值"""
        monkeypatch.setenv("RRF_K", "90")
        from app.core.config import Settings
        s = Settings(_env_file=None)
        assert s.RRF_K == 90

    def test_search_service_uses_settings_rrf_k(self):
        """SearchService 从 settings 读取 rrf_k"""
        from app.core.config import Settings
        from app.services.search_service import SearchService

        s = Settings(_env_file=None, RRF_K=120)
        vs = MagicMock()
        es = MagicMock()
        svc = SearchService(vs, es, settings=s)
        assert svc.rrf_k == 120

    def test_search_service_default_rrf_k_without_settings(self):
        """无 settings 时 rrf_k 默认 60"""
        from app.services.search_service import SearchService

        vs = MagicMock()
        es = MagicMock()
        svc = SearchService(vs, es, settings=None)
        assert svc.rrf_k == 60


class TestRerankerWeightsFromSettings:
    """测试 Reranker 权重从 settings 读取"""

    def test_reranker_default_weights(self):
        """无 settings 时使用默认权重 0.5/0.3/0.2"""
        from app.services.reranker import Reranker
        r = Reranker(settings=None)
        assert r.weight_rrf == 0.5
        assert r.weight_field == 0.3
        assert r.weight_popularity == 0.2

    def test_reranker_weights_from_settings(self):
        """从 settings 读取权重"""
        from app.services.reranker import Reranker

        s = MagicMock()
        s.RERANKER_WEIGHT_RRF = 0.7
        s.RERANKER_WEIGHT_FIELD = 0.2
        s.RERANKER_WEIGHT_POPULARITY = 0.1
        r = Reranker(settings=s)
        assert r.weight_rrf == 0.7
        assert r.weight_field == 0.2
        assert r.weight_popularity == 0.1

    def test_reranker_weights_env_override(self, monkeypatch):
        """环境变量覆盖权重"""
        monkeypatch.setenv("RERANKER_WEIGHT_RRF", "0.7")
        monkeypatch.setenv("RERANKER_WEIGHT_FIELD", "0.2")
        monkeypatch.setenv("RERANKER_WEIGHT_POPULARITY", "0.1")
        from app.core.config import Settings
        from app.services.reranker import Reranker

        s = Settings(_env_file=None)
        r = Reranker(settings=s)
        assert r.weight_rrf == 0.7
        assert r.weight_field == 0.2
        assert r.weight_popularity == 0.1


class TestWeightNormalizationWarning:
    """测试权重归一化校验"""

    def test_warning_when_weights_sum_not_one(self):
        """权重和≠1.0 时 logger.warning 但不抛异常"""
        from app.services import reranker as reranker_mod
        from app.services.reranker import Reranker

        s = MagicMock()
        s.RERANKER_WEIGHT_RRF = 0.5
        s.RERANKER_WEIGHT_FIELD = 0.2
        s.RERANKER_WEIGHT_POPULARITY = 0.1  # 和=0.8

        warning_calls = []
        original_warning = reranker_mod.logger.warning
        reranker_mod.logger.warning = lambda *args, **kwargs: warning_calls.append((args, kwargs))

        try:
            # 不应抛异常
            r = Reranker(settings=s)
            assert r is not None
            # 应有 warning 日志
            assert len(warning_calls) > 0
            warning_msg = str(warning_calls[0][0])
            assert "!= 1.0" in warning_msg
        finally:
            reranker_mod.logger.warning = original_warning

    def test_no_warning_when_weights_sum_one(self):
        """权重和=1.0 时无 warning"""
        from app.services import reranker as reranker_mod
        from app.services.reranker import Reranker

        s = MagicMock()
        s.RERANKER_WEIGHT_RRF = 0.5
        s.RERANKER_WEIGHT_FIELD = 0.3
        s.RERANKER_WEIGHT_POPULARITY = 0.2  # 和=1.0

        warning_calls = []
        original_warning = reranker_mod.logger.warning
        reranker_mod.logger.warning = lambda *args, **kwargs: warning_calls.append((args, kwargs))

        try:
            r = Reranker(settings=s)
            assert r is not None
            # 不应有归一化 warning（可能有其他 warning，但不含 "!= 1.0"）
            for args, _ in warning_calls:
                assert "!= 1.0" not in str(args)
        finally:
            reranker_mod.logger.warning = original_warning


class TestRRFFusionUsesConfiguredK:
    """测试 _reciprocal_rank_fusion 使用配置的 k 值"""

    def test_rrf_fusion_uses_configured_k(self):
        """验证 RRF 融合使用 k=90 而非默认 60"""
        from app.services.search_service import SearchService

        vs = MagicMock()
        es = MagicMock()
        svc = SearchService(vs, es, settings=None)
        svc.rrf_k = 90  # 覆盖为 90

        # 构造两个列表，paper_id 唯一
        list1 = [{"paper_id": "p1"}, {"paper_id": "p2"}]
        list2 = [{"paper_id": "p2"}, {"paper_id": "p3"}]

        result = svc._reciprocal_rank_fusion(list1, list2)

        # 验证 rrf_score 计算使用 k=90
        # p1: rank=0 in list1 → 1/(90+0+1) = 1/91
        # p2: rank=1 in list1 + rank=0 in list2 → 1/(90+1+1) + 1/(90+0+1) = 1/92 + 1/91
        # p3: rank=1 in list2 → 1/(90+1+1) = 1/92
        p1_score = next(r["rrf_score"] for r in result if r["paper_id"] == "p1")
        p2_score = next(r["rrf_score"] for r in result if r["paper_id"] == "p2")
        p3_score = next(r["rrf_score"] for r in result if r["paper_id"] == "p3")

        expected_p1 = 1.0 / (90 + 0 + 1)
        expected_p2 = 1.0 / (90 + 1 + 1) + 1.0 / (90 + 0 + 1)
        expected_p3 = 1.0 / (90 + 1 + 1)

        assert abs(p1_score - expected_p1) < 1e-9
        assert abs(p2_score - expected_p2) < 1e-9
        assert abs(p3_score - expected_p3) < 1e-9

    def test_rrf_fusion_explicit_k_override(self):
        """显式传 k 参数覆盖 self.rrf_k"""
        from app.services.search_service import SearchService

        vs = MagicMock()
        es = MagicMock()
        svc = SearchService(vs, es, settings=None)
        svc.rrf_k = 60

        list1 = [{"paper_id": "p1"}]
        list2 = [{"paper_id": "p2"}]

        result = svc._reciprocal_rank_fusion(list1, list2, k=120)

        p1_score = next(r["rrf_score"] for r in result if r["paper_id"] == "p1")
        expected_p1 = 1.0 / (120 + 0 + 1)
        assert abs(p1_score - expected_p1) < 1e-9


class TestTuneScriptExecutable:
    """测试调优脚本可执行"""

    def test_tune_script_runs_successfully(self):
        """subprocess 运行调优脚本，验证退出码 0 和输出含 Markdown 表格"""
        script_path = PROJECT_ROOT / "scripts" / "tune_rrf_reranker.py"
        assert script_path.exists(), f"Script not found: {script_path}"

        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(PROJECT_ROOT),
        )

        assert result.returncode == 0, f"Script failed: {result.stderr}"
        # 验证输出含 Markdown 表格
        assert "|" in result.stdout
        assert "Top5 准确率" in result.stdout or "top5_accuracy" in result.stdout.lower()

    def test_tune_script_generates_report_file(self):
        """验证脚本生成 logs/tune_rrf_reranker_results.md"""
        script_path = PROJECT_ROOT / "scripts" / "tune_rrf_reranker.py"
        subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            timeout=60,
            cwd=str(PROJECT_ROOT),
        )

        report_path = PROJECT_ROOT / "logs" / "tune_rrf_reranker_results.md"
        assert report_path.exists(), f"Report not generated: {report_path}"
        content = report_path.read_text(encoding="utf-8")
        assert "RRF" in content
        assert "Top5" in content
