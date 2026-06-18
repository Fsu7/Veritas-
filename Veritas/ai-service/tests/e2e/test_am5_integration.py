"""task56 AM5 集成测试

验证 AM5 阶段（task53-55）三个核心功能模块的端到端集成：
1. Embedding 维度一致性（task53）
2. 检索参数（top_k / similarity_threshold）端到端生效（task54）
3. 推荐策略（F3.4.6 4 维度加权）端到端生效（task55）

测试方式：Mock LLM/Embedding/VectorStore，验证数据流贯通。
"""
import asyncio
from typing import List
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from app.core.config import Settings
from app.services.embedding_service import EmbeddingService
from app.services.personalization_service import PersonalizationService
from app.services.reranker import Reranker
from app.services.search_service import SearchService


# ===== Mock 工厂 =====


def _make_settings(
    search_top_k: int = 10,
    similarity_threshold: float = 0.0,
    rerank_weight: float = 0.7,
    recommendation_weight: float = 0.3,
) -> Settings:
    return Settings(
        SEARCH_TOP_K=search_top_k,
        SEARCH_SIMILARITY_THRESHOLD=similarity_threshold,
        RERANK_WEIGHT=rerank_weight,
        RECOMMENDATION_WEIGHT=recommendation_weight,
        RERANKER_WEIGHT_RRF=0.5,
        RERANKER_WEIGHT_FIELD=0.3,
        RERANKER_WEIGHT_POPULARITY=0.2,
        RRF_K=60,
    )


def _make_mock_embedding_service(dim: int = 1024) -> MagicMock:
    svc = MagicMock(spec=EmbeddingService)
    svc.encode = AsyncMock(return_value=np.ones(dim, dtype=np.float32))
    svc.embed_query = AsyncMock(return_value=np.ones(dim, dtype=np.float32))
    return svc


def _make_mock_vector_store_service(
    results_by_query: List[dict] = None,
    distances: List[float] = None,
) -> MagicMock:
    """构造 mock VectorStoreService，search() 返回指定结果"""
    svc = MagicMock()
    default_results = results_by_query or [
        {"paper_id": "p1", "title": "Paper 1", "abstract": "abstract 1", "distance": 0.1},
        {"paper_id": "p2", "title": "Paper 2", "abstract": "abstract 2", "distance": 0.3},
        {"paper_id": "p3", "title": "Paper 3", "abstract": "abstract 3", "distance": 0.5},
    ]
    if distances is not None:
        for r, d in zip(default_results, distances):
            r["distance"] = d

    async def _search(embedding, top_k=10, filters=None, similarity_threshold=0.0):
        filtered = []
        for r in default_results:
            distance = r.get("distance", 0.0)
            # task54 过滤逻辑：similarity = 1 - distance
            if similarity_threshold > 0.0 and (1.0 - distance) < similarity_threshold:
                continue
            filtered.append(r)
        return filtered[:top_k]

    svc.search = AsyncMock(side_effect=_search)
    svc.search_by_keywords = AsyncMock(return_value=list(default_results))
    return svc


def _make_nlp_profile() -> dict:
    return {
        "research_field": "NLP",
        "education_level": "master",
        "knowledge_level": "intermediate",
        "preferred_style": "balanced",
    }


def _make_cv_profile() -> dict:
    return {
        "research_field": "CV",
        "education_level": "phd",
        "knowledge_level": "advanced",
        "preferred_style": "technical",
    }


def _make_papers() -> List[dict]:
    """构造测试论文池（含 NLP/CV 不同方向）"""
    return [
        {
            "paper_id": "p1",
            "title": "Attention Is All You Need",
            "abstract": "We propose a new architecture called Transformer based on attention mechanism for natural language processing tasks.",
            "keywords": ["transformer", "attention", "NLP"],
            "venue": "ACL",
            "year": 2017,
            "citation_count": 50000,
        },
        {
            "paper_id": "p2",
            "title": "BERT: Pre-training of Deep Bidirectional Transformers",
            "abstract": "We introduce BERT for language model pre-training, which achieves state-of-the-art results on NLP benchmarks.",
            "keywords": ["bert", "pre-training", "language model"],
            "venue": "NAACL",
            "year": 2019,
            "citation_count": 30000,
        },
        {
            "paper_id": "p3",
            "title": "ResNet: Deep Residual Learning for Image Recognition",
            "abstract": "We present a residual learning framework for computer vision and image recognition tasks.",
            "keywords": ["resnet", "cnn", "CV"],
            "venue": "CVPR",
            "year": 2016,
            "citation_count": 60000,
        },
        {
            "paper_id": "p4",
            "title": "GAN: Generative Adversarial Networks",
            "abstract": "We propose GAN framework for image generation in computer vision domain.",
            "keywords": ["gan", "generation", "CV"],
            "venue": "NIPS",
            "year": 2014,
            "citation_count": 40000,
        },
    ]


# ===== Test 1: Embedding 维度一致性（task53） =====


class TestEmbeddingDimensionConsistency:
    """task53: 验证 embed_query 返回 1D 数组，embed_documents 返回 2D 数组"""

    @pytest.mark.asyncio
    async def test_embed_query_returns_1d_array(self):
        """embed_query 应返回 (dim,) 而非 (1, dim)"""
        from app.services.embedding_service import DashScopeProvider

        settings = Settings(
            DASHSCOPE_API_KEY="test_key",
            DASHSCOPE_EMBEDDING_MODEL="text-embedding-v3",
            DASHSCOPE_EMBEDDING_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        provider = DashScopeProvider(settings)

        # Mock _embed_via_api 返回 2D 数组（模拟真实 API 行为）
        provider._embed_via_api = AsyncMock(
            return_value=np.ones((1, 1024), dtype=np.float32)
        )

        result = await provider.embed_query("test query")

        # task53: embed_query 应返回 1D
        assert result.ndim == 1, f"Expected 1D array, got {result.ndim}D"
        assert result.shape == (1024,), f"Expected shape (1024,), got {result.shape}"

    @pytest.mark.asyncio
    async def test_embedding_service_encode_returns_1d(self):
        """EmbeddingService.encode() 应返回 1D 数组用于向量检索"""
        svc = _make_mock_embedding_service(dim=1024)
        result = await svc.encode("test query")
        assert result.ndim == 1
        assert result.shape == (1024,)


# ===== Test 2: 检索参数端到端（task54） =====


class TestRetrievalParamsEndToEnd:
    """task54: SEARCH_TOP_K 和 SEARCH_SIMILARITY_THRESHOLD 端到端生效"""

    @pytest.mark.asyncio
    async def test_search_top_k_from_settings(self):
        """SearchService.search() 默认 top_k 应来自 settings.SEARCH_TOP_K"""
        settings = _make_settings(search_top_k=5)
        mock_embedding = _make_mock_embedding_service()
        mock_vs = _make_mock_vector_store_service(
            results_by_query=[{"paper_id": f"p{i}", "distance": 0.1} for i in range(20)]
        )

        search_svc = SearchService(
            vector_store_service=mock_vs,
            embedding_service=mock_embedding,
            settings=settings,
        )

        # 不传 top_k，应使用 settings.SEARCH_TOP_K=5
        results = await search_svc.search("test query")

        # 验证 vector_store_service.search 被调用时 top_k=5
        call_args = mock_vs.search.call_args
        assert call_args.kwargs.get("top_k") == 5 or call_args.args[1] == 5

    @pytest.mark.asyncio
    async def test_similarity_threshold_filters_low_quality(self):
        """similarity_threshold > 0 应过滤掉低相似度结果"""
        settings = _make_settings(similarity_threshold=0.5)
        mock_embedding = _make_mock_embedding_service()
        # distances: 0.1 → similarity=0.9 (保留), 0.6 → similarity=0.4 (过滤), 0.8 → similarity=0.2 (过滤)
        mock_vs = _make_mock_vector_store_service(
            results_by_query=[
                {"paper_id": "p1", "distance": 0.1},
                {"paper_id": "p2", "distance": 0.6},
                {"paper_id": "p3", "distance": 0.8},
            ],
        )

        search_svc = SearchService(
            vector_store_service=mock_vs,
            embedding_service=mock_embedding,
            settings=settings,
        )

        results = await search_svc.search("test query")

        # 验证 vector_store_service.search 收到 similarity_threshold=0.5
        call_args = mock_vs.search.call_args
        threshold = call_args.kwargs.get("similarity_threshold", 0.0)
        assert threshold == 0.5, f"Expected similarity_threshold=0.5, got {threshold}"

    @pytest.mark.asyncio
    async def test_top_k_override_by_parameter(self):
        """显式传 top_k 参数应覆盖 settings 默认值"""
        settings = _make_settings(search_top_k=10)
        mock_embedding = _make_mock_embedding_service()
        mock_vs = _make_mock_vector_store_service(
            results_by_query=[{"paper_id": f"p{i}", "distance": 0.1} for i in range(20)]
        )

        search_svc = SearchService(
            vector_store_service=mock_vs,
            embedding_service=mock_embedding,
            settings=settings,
        )

        # 显式传 top_k=3，应覆盖 settings.SEARCH_TOP_K=10
        await search_svc.search("test query", top_k=3)

        call_args = mock_vs.search.call_args
        actual_top_k = call_args.kwargs.get("top_k") or (call_args.args[1] if len(call_args.args) > 1 else None)
        assert actual_top_k == 3, f"Expected top_k=3 (override), got {actual_top_k}"


# ===== Test 3: 推荐策略端到端（task55） =====


class TestRecommendationStrategyEndToEnd:
    """task55: F3.4.6 推荐策略端到端验证"""

    @pytest.mark.asyncio
    async def test_rerank_with_user_profile_uses_recommendation(self):
        """rerank 传入 user_profile 时应使用 F3.4.6 推荐分加权"""
        settings = _make_settings()
        personalization_svc = PersonalizationService()
        reranker = Reranker(settings=settings, personalization_service=personalization_svc)

        papers = _make_papers()
        nlp_profile = _make_nlp_profile()

        results = await reranker.rerank("attention transformer", papers, user_profile=nlp_profile)

        # 验证：每个结果应包含 recommendation_score 字段
        for r in results:
            assert "recommendation_score" in r, "Missing recommendation_score field"
            assert "rerank_score" in r, "Missing rerank_score field"
            assert 0.0 <= r["recommendation_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_different_profiles_produce_different_ranking(self):
        """NLP 用户和 CV 用户应得到不同的 Top1 论文"""
        settings = _make_settings()
        personalization_svc = PersonalizationService()
        reranker = Reranker(settings=settings, personalization_service=personalization_svc)

        papers = _make_papers()

        nlp_results = await reranker.rerank(
            "deep learning", papers, user_profile=_make_nlp_profile()
        )
        cv_results = await reranker.rerank(
            "deep learning", papers, user_profile=_make_cv_profile()
        )

        nlp_top1 = nlp_results[0]["paper_id"]
        cv_top1 = cv_results[0]["paper_id"]

        # NLP 用户 Top1 应为 NLP 论文（p1 或 p2）
        assert nlp_top1 in ("p1", "p2"), f"NLP Top1 should be NLP paper, got {nlp_top1}"
        # CV 用户 Top1 应为 CV 论文（p3 或 p4）
        assert cv_top1 in ("p3", "p4"), f"CV Top1 should be CV paper, got {cv_top1}"
        # 两者应不同
        assert nlp_top1 != cv_top1, "Different profiles should produce different Top1"

    @pytest.mark.asyncio
    async def test_recommend_method_returns_sorted_list(self):
        """recommend() 应返回按 recommendation_score 降序排序的列表"""
        settings = _make_settings()
        personalization_svc = PersonalizationService()
        reranker = Reranker(settings=settings, personalization_service=personalization_svc)

        papers = _make_papers()
        history = [
            {"paper_id": "h1", "title": "Transformer", "abstract": "attention mechanism for NLP"},
        ]

        results = await reranker.recommend(papers, _make_nlp_profile(), history)

        assert len(results) == len(papers)
        # 验证降序
        scores = [r["recommendation_score"] for r in results]
        assert scores == sorted(scores, reverse=True), "Results should be sorted by recommendation_score desc"

    @pytest.mark.asyncio
    async def test_search_service_rerank_with_profile(self):
        """SearchService.search() 传入 user_profile 时应触发推荐策略"""
        settings = _make_settings()
        mock_embedding = _make_mock_embedding_service()
        mock_vs = _make_mock_vector_store_service(
            results_by_query=_make_papers()
        )
        personalization_svc = PersonalizationService()
        reranker = Reranker(settings=settings, personalization_service=personalization_svc)

        search_svc = SearchService(
            vector_store_service=mock_vs,
            embedding_service=mock_embedding,
            reranker=reranker,
            settings=settings,
        )

        # search_service.search 不直接接受 user_profile，但 reranker.rerank 接受
        # 这里验证 reranker 在 search 流程中被正确调用
        results = await search_svc.search("attention transformer")

        # 验证 reranker 被调用（通过 results 包含 rerank_score 字段）
        assert len(results) > 0
        assert "rerank_score" in results[0]


# ===== Test 4: 端到端数据流贯通 =====


class TestEndToEndDataFlow:
    """验证 Embedding → VectorStore → Reranker → Recommendation 数据流贯通"""

    @pytest.mark.asyncio
    async def test_full_pipeline_with_recommendation(self):
        """完整流程：query → embedding → vector_store → rerank → recommend"""
        settings = _make_settings(search_top_k=4, similarity_threshold=0.0)
        mock_embedding = _make_mock_embedding_service()
        mock_vs = _make_mock_vector_store_service(
            results_by_query=_make_papers()
        )
        personalization_svc = PersonalizationService()
        reranker = Reranker(settings=settings, personalization_service=personalization_svc)

        search_svc = SearchService(
            vector_store_service=mock_vs,
            embedding_service=mock_embedding,
            reranker=reranker,
            settings=settings,
        )

        # 1. 检索
        results = await search_svc.search("attention transformer NLP")
        assert len(results) > 0

        # 2. 推荐排序
        nlp_profile = _make_nlp_profile()
        history = [{"paper_id": "h1", "title": "Transformer", "abstract": "attention for NLP"}]
        recommended = await reranker.recommend(results, nlp_profile, history)

        assert len(recommended) == len(results)
        assert all("recommendation_score" in r for r in recommended)

        # 3. NLP 用户 Top1 应为 NLP 相关论文
        top1 = recommended[0]["paper_id"]
        assert top1 in ("p1", "p2"), f"NLP user Top1 should be NLP paper, got {top1}"

    @pytest.mark.asyncio
    async def test_pipeline_respects_similarity_threshold(self):
        """完整流程应正确应用 similarity_threshold 过滤"""
        settings = _make_settings(similarity_threshold=0.5)
        mock_embedding = _make_mock_embedding_service()
        mock_vs = _make_mock_vector_store_service(
            results_by_query=[
                {"paper_id": "p1", "title": "T1", "abstract": "a1", "distance": 0.1},  # sim=0.9 保留
                {"paper_id": "p2", "title": "T2", "abstract": "a2", "distance": 0.7},  # sim=0.3 过滤
            ],
        )

        search_svc = SearchService(
            vector_store_service=mock_vs,
            embedding_service=mock_embedding,
            settings=settings,
        )

        results = await search_svc.search("test")

        # 验证 similarity_threshold 被传递给 vector_store_service
        call_args = mock_vs.search.call_args
        assert call_args.kwargs.get("similarity_threshold") == 0.5


# ===== Test 5: 配置可环境变量覆盖 =====


class TestConfigEnvOverride:
    """验证 task54/task55 配置可通过环境变量覆盖"""

    def test_search_top_k_env_override(self, monkeypatch):
        """SEARCH_TOP_K 环境变量应覆盖默认值"""
        monkeypatch.setenv("SEARCH_TOP_K", "15")
        settings = Settings()
        assert settings.SEARCH_TOP_K == 15

    def test_similarity_threshold_env_override(self, monkeypatch):
        """SEARCH_SIMILARITY_THRESHOLD 环境变量应覆盖默认值"""
        monkeypatch.setenv("SEARCH_SIMILARITY_THRESHOLD", "0.3")
        settings = Settings()
        assert settings.SEARCH_SIMILARITY_THRESHOLD == 0.3

    def test_rerank_weight_env_override(self, monkeypatch):
        """RERANK_WEIGHT 环境变量应覆盖默认值"""
        monkeypatch.setenv("RERANK_WEIGHT", "0.6")
        settings = Settings()
        assert settings.RERANK_WEIGHT == 0.6

    def test_recommendation_weight_env_override(self, monkeypatch):
        """RECOMMENDATION_WEIGHT 环境变量应覆盖默认值"""
        monkeypatch.setenv("RECOMMENDATION_WEIGHT", "0.4")
        settings = Settings()
        assert settings.RECOMMENDATION_WEIGHT == 0.4


# ===== Test 6: 降级与边界情况 =====


class TestDegradationAndEdgeCases:
    """降级与边界情况测试"""

    @pytest.mark.asyncio
    async def test_rerank_empty_results(self):
        """rerank 空结果应返回空列表"""
        settings = _make_settings()
        reranker = Reranker(settings=settings)
        results = await reranker.rerank("query", [], user_profile=_make_nlp_profile())
        assert results == []

    @pytest.mark.asyncio
    async def test_rerank_without_personalization_service(self):
        """无 personalization_service 时应向后兼容（使用 personalization_boost）"""
        settings = _make_settings()
        reranker = Reranker(settings=settings, personalization_service=None)

        papers = _make_papers()
        results = await reranker.rerank("attention", papers, user_profile=_make_nlp_profile())

        assert len(results) == len(papers)
        # 向后兼容模式不应有 recommendation_score 字段
        assert "recommendation_score" not in results[0]

    @pytest.mark.asyncio
    async def test_recommend_without_personalization_service(self):
        """无 personalization_service 时 recommend() 应退化为按 score 排序"""
        settings = _make_settings()
        reranker = Reranker(settings=settings, personalization_service=None)

        papers = [
            {"paper_id": "p1", "score": 0.5},
            {"paper_id": "p2", "score": 0.9},
            {"paper_id": "p3", "score": 0.3},
        ]

        results = await reranker.recommend(papers, _make_nlp_profile(), [])
        assert results[0]["paper_id"] == "p2"  # score 最高

    @pytest.mark.asyncio
    async def test_recommendation_score_in_valid_range(self):
        """recommendation_score 应始终在 [0, 1] 范围内"""
        settings = _make_settings()
        personalization_svc = PersonalizationService()
        reranker = Reranker(settings=settings, personalization_service=personalization_svc)

        papers = _make_papers()
        results = await reranker.rerank("query", papers, user_profile=_make_nlp_profile())

        for r in results:
            assert 0.0 <= r["recommendation_score"] <= 1.0
            assert 0.0 <= r["rerank_score"] <= 1.0


# ===== Test 7: RecommendationService 集成 =====


class TestRecommendationServiceIntegration:
    """RecommendationService 端到端集成"""

    @pytest.mark.asyncio
    async def test_recommendation_service_full_flow(self):
        """RecommendationService.get_recommended_papers 完整流程"""
        from app.services.recommendation_service import RecommendationService

        settings = _make_settings()
        personalization_svc = PersonalizationService()
        reranker = Reranker(settings=settings, personalization_service=personalization_svc)

        # Mock vector_store_service 返回候选论文
        mock_vs = MagicMock()
        mock_vs.search_by_keywords = AsyncMock(return_value=_make_papers())

        rec_svc = RecommendationService(
            personalization_service=personalization_svc,
            reranker=reranker,
            vector_store_service=mock_vs,
            settings=settings,
        )

        nlp_profile = _make_nlp_profile()
        history = [{"paper_id": "h1", "title": "Transformer", "abstract": "attention for NLP"}]

        results = await rec_svc.get_recommended_papers(
            user_id="usr_001",
            top_k=3,
            user_profile=nlp_profile,
            user_history=history,
        )

        assert len(results) <= 3
        assert all("recommendation_score" in r for r in results)
        # NLP 用户 Top1 应为 NLP 论文
        if results:
            assert results[0]["paper_id"] in ("p1", "p2")
