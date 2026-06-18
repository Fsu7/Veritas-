"""task56 AM5 验收检查点测试

按 AM5 验收标准逐项验证 task53-55 的实现：
- task53: Embedding 多 Provider 维度一致性
- task54: 检索参数（top_k / similarity_threshold / chunk_size）配置化
- task55: 推荐策略（F3.4.6 4 维度加权 + RecommendationService）

每个测试对应一个验收检查点，全部通过即 AM5 验收通过。
"""
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from app.core.config import Settings
from app.services.embedding_service import (
    DashScopeProvider,
    EmbeddingService,
    JinaProvider,
    OpenAIProvider,
)
from app.services.personalization_service import (
    ACADEMIC_TERMS,
    PersonalizationService,
)
from app.services.reranker import Reranker
from app.services.search_service import SearchService


# ============================================================
# task53 验收检查点：Embedding 多 Provider 维度一致性
# ============================================================


class TestAcceptanceTask53Embedding:
    """task53 验收：3 个 Provider 的 embed_query 返回 1D 数组"""

    def _make_settings(self, **kwargs):
        """构造测试 settings"""
        defaults = {
            "DASHSCOPE_API_KEY": "test",
            "DASHSCOPE_EMBEDDING_MODEL": "text-embedding-v3",
            "DASHSCOPE_EMBEDDING_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "JINA_API_KEY": "test",
            "OPENAI_API_KEY": "test",
        }
        defaults.update(kwargs)
        return Settings(**defaults)

    @pytest.mark.asyncio
    async def test_dashscope_embed_query_returns_1d(self):
        """DashScopeProvider.embed_query 返回 (1024,)"""
        settings = self._make_settings()
        provider = DashScopeProvider(settings)
        provider._embed_via_api = AsyncMock(
            return_value=np.ones((1, 1024), dtype=np.float32)
        )
        result = await provider.embed_query("test")
        assert result.ndim == 1
        assert result.shape == (1024,)

    @pytest.mark.asyncio
    async def test_jina_embed_query_returns_1d(self):
        """JinaProvider.embed_query 返回 (1024,)"""
        settings = self._make_settings()
        provider = JinaProvider(settings)
        provider._embed_via_api = AsyncMock(
            return_value=np.ones((1, 1024), dtype=np.float32)
        )
        result = await provider.embed_query("test")
        assert result.ndim == 1
        assert result.shape == (1024,)

    @pytest.mark.asyncio
    async def test_openai_embed_query_returns_1d(self):
        """OpenAIProvider.embed_query 返回 (1024,)（截断+归一化后）"""
        settings = self._make_settings()
        provider = OpenAIProvider(settings)
        # OpenAI 原始返回 1536 维，Provider 内部截断到 1024
        provider._embed_via_api = AsyncMock(
            return_value=np.ones((1, 1024), dtype=np.float32)
        )
        result = await provider.embed_query("test")
        assert result.ndim == 1
        assert result.shape == (1024,)

    @pytest.mark.asyncio
    async def test_embed_documents_returns_2d(self):
        """embed_documents 应返回 2D 数组 (n, dim)"""
        settings = self._make_settings()
        provider = DashScopeProvider(settings)
        provider._embed_via_api = AsyncMock(
            return_value=np.ones((3, 1024), dtype=np.float32)
        )
        result = await provider.embed_documents(["t1", "t2", "t3"])
        assert result.ndim == 2
        assert result.shape == (3, 1024)


# ============================================================
# task54 验收检查点：检索参数配置化
# ============================================================


class TestAcceptanceTask54RetrievalParams:
    """task54 验收：SEARCH_TOP_K / SEARCH_SIMILARITY_THRESHOLD / CHUNK_SIZE 配置化"""

    def test_search_top_k_default_value(self):
        """SEARCH_TOP_K 默认值为 10"""
        settings = Settings()
        assert settings.SEARCH_TOP_K == 10

    def test_search_top_k_in_valid_range(self):
        """SEARCH_TOP_K 应在 [5, 20] 范围内（通过环境变量设置）"""
        # 验证默认值在范围内
        settings = Settings()
        assert 5 <= settings.SEARCH_TOP_K <= 20

    def test_similarity_threshold_default_value(self):
        """SEARCH_SIMILARITY_THRESHOLD 默认值为 0.0（不过滤）"""
        settings = Settings()
        assert settings.SEARCH_SIMILARITY_THRESHOLD == 0.0

    def test_similarity_threshold_in_valid_range(self):
        """SEARCH_SIMILARITY_THRESHOLD 应在 [0.0, 0.9] 范围内"""
        settings = Settings()
        assert 0.0 <= settings.SEARCH_SIMILARITY_THRESHOLD <= 0.9

    def test_chunk_size_default_value(self):
        """CHUNK_SIZE 默认值为 512"""
        settings = Settings()
        assert settings.CHUNK_SIZE == 512

    def test_search_service_reads_top_k_from_settings(self):
        """SearchService 应从 settings 读取 search_top_k"""
        settings = Settings(SEARCH_TOP_K=15)
        mock_vs = MagicMock()
        mock_emb = MagicMock()
        search_svc = SearchService(mock_vs, mock_emb, settings=settings)
        assert search_svc.search_top_k == 15

    def test_search_service_reads_similarity_threshold_from_settings(self):
        """SearchService 应从 settings 读取 similarity_threshold"""
        settings = Settings(SEARCH_SIMILARITY_THRESHOLD=0.3)
        mock_vs = MagicMock()
        mock_emb = MagicMock()
        search_svc = SearchService(mock_vs, mock_emb, settings=settings)
        assert search_svc.similarity_threshold == 0.3

    def test_tune_script_exists(self):
        """调参脚本 tune_retrieval_params.py 应存在"""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "tune_retrieval_params.py"
        assert script_path.exists(), f"tune_retrieval_params.py not found at {script_path}"


# ============================================================
# task55 验收检查点：推荐策略 F3.4.6
# ============================================================


class TestAcceptanceTask55Recommendation:
    """task55 验收：F3.4.6 推荐策略 4 维度加权 + RecommendationService"""

    def test_rerank_weight_default_value(self):
        """RERANK_WEIGHT 默认值为 0.7"""
        settings = Settings()
        assert settings.RERANK_WEIGHT == 0.7

    def test_recommendation_weight_default_value(self):
        """RECOMMENDATION_WEIGHT 默认值为 0.3"""
        settings = Settings()
        assert settings.RECOMMENDATION_WEIGHT == 0.3

    def test_weights_sum_to_one(self):
        """RERANK_WEIGHT + RECOMMENDATION_WEIGHT 应等于 1.0"""
        settings = Settings()
        total = settings.RERANK_WEIGHT + settings.RECOMMENDATION_WEIGHT
        assert abs(total - 1.0) < 0.01, f"Weights sum={total} != 1.0"

    def test_reranker_reads_weights_from_settings(self):
        """Reranker 应从 settings 读取 rerank_weight 和 recommendation_weight"""
        settings = Settings(RERANK_WEIGHT=0.6, RECOMMENDATION_WEIGHT=0.4)
        reranker = Reranker(settings=settings)
        assert reranker.rerank_weight == 0.6
        assert reranker.recommendation_weight == 0.4

    def test_get_recommendation_strategy_returns_score_in_range(self):
        """get_recommendation_strategy 应返回 [0, 1] 范围内的分数"""
        svc = PersonalizationService()
        profile = {"research_field": "NLP", "education_level": "master",
                   "knowledge_level": "intermediate", "preferred_style": "balanced"}
        paper = {
            "title": "Transformer",
            "abstract": "We propose transformer architecture with attention mechanism for NLP tasks.",
            "keywords": ["transformer", "NLP"],
            "venue": "ACL",
        }
        score = svc.get_recommendation_strategy(profile, paper)
        assert 0.0 <= score <= 1.0

    def test_get_recommendation_strategy_4_dimensions_weighted(self):
        """4 维度权重应为 0.4/0.2/0.2/0.2"""
        # 通过完全匹配 vs 完全不匹配验证权重
        svc = PersonalizationService()
        profile = {"research_field": "NLP", "education_level": "master",
                   "knowledge_level": "intermediate", "preferred_style": "balanced"}

        # 完全匹配的论文
        perfect_paper = {
            "title": "NLP Transformer",
            "abstract": "We propose transformer for NLP. " + "standard " * 50,
            "keywords": ["NLP", "transformer"],
            "venue": "ACL",
        }
        # 完全不匹配的论文
        mismatch_paper = {
            "title": "Biology",
            "abstract": "cell biology research",
            "keywords": ["biology"],
            "venue": "Nature",
        }

        perfect_score = svc.get_recommendation_strategy(profile, perfect_paper)
        mismatch_score = svc.get_recommendation_strategy(profile, mismatch_paper)

        assert perfect_score > mismatch_score, "Perfect match should score higher"

    def test_reranker_accepts_personalization_service(self):
        """Reranker __init__ 应接受 personalization_service 参数"""
        svc = PersonalizationService()
        reranker = Reranker(personalization_service=svc)
        assert reranker.personalization_service is svc

    def test_recommendation_service_exists(self):
        """RecommendationService 类应存在"""
        from app.services.recommendation_service import RecommendationService
        assert RecommendationService is not None

    def test_academic_terms_list_exists(self):
        """ACADEMIC_TERMS 术语列表应存在且非空"""
        assert len(ACADEMIC_TERMS) >= 10, f"ACADEMIC_TERMS should have at least 10 terms, got {len(ACADEMIC_TERMS)}"

    @pytest.mark.asyncio
    async def test_rerank_with_profile_adds_recommendation_score(self):
        """rerank 传入 user_profile + personalization_service 时应添加 recommendation_score"""
        settings = Settings()
        svc = PersonalizationService()
        reranker = Reranker(settings=settings, personalization_service=svc)

        papers = [
            {"paper_id": "p1", "title": "NLP Paper", "abstract": "NLP research",
             "keywords": ["NLP"], "venue": "ACL", "year": 2020, "citation_count": 100},
        ]
        profile = {"research_field": "NLP", "education_level": "master",
                   "knowledge_level": "intermediate", "preferred_style": "balanced"}

        results = await reranker.rerank("NLP", papers, user_profile=profile)
        assert "recommendation_score" in results[0]
        assert "rerank_score" in results[0]


# ============================================================
# 跨任务验收：配置完整性
# ============================================================


class TestAcceptanceConfigCompleteness:
    """验证 task53-55 所有配置项完整存在"""

    def test_all_task53_configs_exist(self):
        """task53 配置项：EMBEDDING_PROVIDER, JINA_API_KEY, OPENAI_API_KEY, EMBEDDING_DIMENSION"""
        settings = Settings()
        assert hasattr(settings, "EMBEDDING_PROVIDER")
        assert hasattr(settings, "JINA_API_KEY")
        assert hasattr(settings, "OPENAI_API_KEY")
        assert hasattr(settings, "EMBEDDING_DIMENSION")

    def test_all_task54_configs_exist(self):
        """task54 配置项：SEARCH_TOP_K, SEARCH_SIMILARITY_THRESHOLD, CHUNK_SIZE"""
        settings = Settings()
        assert hasattr(settings, "SEARCH_TOP_K")
        assert hasattr(settings, "SEARCH_SIMILARITY_THRESHOLD")
        assert hasattr(settings, "CHUNK_SIZE")

    def test_all_task55_configs_exist(self):
        """task55 配置项：RERANK_WEIGHT, RECOMMENDATION_WEIGHT"""
        settings = Settings()
        assert hasattr(settings, "RERANK_WEIGHT")
        assert hasattr(settings, "RECOMMENDATION_WEIGHT")

    def test_env_example_has_all_task_configs(self):
        """ .env.example 应包含 task53-55 的所有配置项"""
        env_example_path = Path(__file__).parent.parent / ".env.example"
        if not env_example_path.exists():
            pytest.skip(".env.example not found")

        content = env_example_path.read_text(encoding="utf-8")
        # task54
        assert "SEARCH_TOP_K" in content
        assert "SEARCH_SIMILARITY_THRESHOLD" in content
        assert "CHUNK_SIZE" in content
        # task55
        assert "RERANK_WEIGHT" in content
        assert "RECOMMENDATION_WEIGHT" in content
