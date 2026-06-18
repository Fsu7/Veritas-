"""task55 推荐策略测试

验证：
1. rerank() 接受 user_profile 输出个性化排序
2. NLP vs CV 用户 Top5 排序差异度 > 30%
3. recommend() 返回推荐论文列表含 recommendation_score
4. 推荐分范围 [0, 1]
5. 4 维度加权计算推荐分
6. RecommendationService.get_recommended_papers() 返回推荐列表
7. user_profile 为空时退化为原逻辑（向后兼容）
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.personalization_service import PersonalizationService
from app.services.reranker import Reranker
from app.services.recommendation_service import RecommendationService


# ===== 测试数据工厂 =====


def _make_papers():
    """构造 10 篇候选论文（NLP + CV 混合）"""
    return [
        {
            "paper_id": "p1", "title": "Transformer Attention for NLP",
            "abstract": "We propose a novel attention mechanism for natural language processing tasks. "
                        "Our method improves transformer architecture for language understanding. "
                        "Experiments on NLP benchmarks show significant gains.",
            "score": 0.9, "citation_count": 50, "year": 2024, "venue": "ACL",
            "keywords": ["NLP", "attention", "transformer"],
        },
        {
            "paper_id": "p2", "title": "CNN for Image Classification",
            "abstract": "This paper presents a convolutional neural network for computer vision. "
                        "We achieve state-of-the-art on image classification benchmarks. "
                        "Experiments demonstrate effectiveness for vision tasks.",
            "score": 0.85, "citation_count": 80, "year": 2023, "venue": "CVPR",
            "keywords": ["CV", "CNN", "image"],
        },
        {
            "paper_id": "p3", "title": "BERT Pre-training for Language Models",
            "abstract": "We pre-train a large language model using self-supervised learning. "
                        "The model achieves strong results on NLP understanding tasks. "
                        "Fine-tuning demonstrates broad applicability.",
            "score": 0.88, "citation_count": 200, "year": 2024, "venue": "NAACL",
            "keywords": ["NLP", "LLM", "pre-training"],
        },
        {
            "paper_id": "p4", "title": "Object Detection with YOLO",
            "abstract": "Real-time object detection using YOLO architecture for computer vision. "
                        "Our vision system processes images efficiently. "
                        "Experiments on COCO show improvements.",
            "score": 0.82, "citation_count": 120, "year": 2023, "venue": "ICCV",
            "keywords": ["CV", "detection", "YOLO"],
        },
        {
            "paper_id": "p5", "title": "GPT Language Model Generation",
            "abstract": "Generative pre-trained transformer for natural language generation. "
                        "Our language model produces coherent text. "
                        "The NLP community benefits from this work.",
            "score": 0.87, "citation_count": 150, "year": 2024, "venue": "EMNLP",
            "keywords": ["NLP", "LLM", "generation"],
        },
        {
            "paper_id": "p6", "title": "Image Segmentation with U-Net",
            "abstract": "Medical image segmentation using U-Net architecture in computer vision. "
                        "Our vision model handles medical images. "
                        "Experiments validate the approach.",
            "score": 0.80, "citation_count": 90, "year": 2022, "venue": "MICCAI",
            "keywords": ["CV", "segmentation", "U-Net"],
        },
        {
            "paper_id": "p7", "title": "Multimodal Vision-Language Model",
            "abstract": "A multimodal model combining vision and language. "
                        "Cross-modal alignment between images and text. "
                        "Experiments show strong performance on multimodal tasks.",
            "score": 0.86, "citation_count": 70, "year": 2024, "venue": "NeurIPS",
            "keywords": ["multimodal", "vision", "language"],
        },
        {
            "paper_id": "p8", "title": "Reinforcement Learning for Robotics",
            "abstract": "We apply reinforcement learning to robot control. "
                        "Our RL agent learns manipulation skills. "
                        "Experiments in simulation demonstrate effectiveness.",
            "score": 0.83, "citation_count": 60, "year": 2023, "venue": "ICRA",
            "keywords": ["RL", "robot", "reinforcement"],
        },
        {
            "paper_id": "p9", "title": "Diffusion Models for Image Generation",
            "abstract": "Denoising diffusion probabilistic models for image generation in CV. "
                        "Our diffusion model generates high-quality images. "
                        "Experiments show visual quality improvements.",
            "score": 0.84, "citation_count": 110, "year": 2024, "venue": "CVPR",
            "keywords": ["CV", "diffusion", "generation"],
        },
        {
            "paper_id": "p10", "title": "Graph Neural Networks for Knowledge Graphs",
            "abstract": "Graph neural networks for reasoning over knowledge graphs. "
                        "Our GNN model captures relational structure. "
                        "Experiments on link prediction show gains.",
            "score": 0.81, "citation_count": 45, "year": 2023, "venue": "KDD",
            "keywords": ["知识图谱", "GNN", "graph"],
        },
    ]


def _make_settings():
    """构造测试 Settings"""
    settings = MagicMock()
    settings.RERANKER_WEIGHT_RRF = 0.5
    settings.RERANKER_WEIGHT_FIELD = 0.3
    settings.RERANKER_WEIGHT_POPULARITY = 0.2
    settings.RERANK_WEIGHT = 0.7
    settings.RECOMMENDATION_WEIGHT = 0.3
    return settings


def _make_nlp_profile():
    return {
        "education_level": "master",
        "knowledge_level": "intermediate",
        "preferred_style": "balanced",
        "research_field": "NLP",
    }


def _make_cv_profile():
    return {
        "education_level": "master",
        "knowledge_level": "intermediate",
        "preferred_style": "balanced",
        "research_field": "CV",
    }


# ===== 测试 1: rerank 接受 user_profile =====


class TestRerankWithUserProfile:
    def test_rerank_with_user_profile(self):
        """rerank() 接受 user_profile 参数输出个性化排序"""
        settings = _make_settings()
        pers_service = PersonalizationService()
        reranker = Reranker(settings=settings, personalization_service=pers_service)

        papers = _make_papers()
        profile = _make_nlp_profile()

        results = asyncio.run(reranker.rerank("attention transformer", papers, user_profile=profile))

        # 应返回所有论文
        assert len(results) == 10
        # 每篇应有 rerank_score
        for r in results:
            assert "rerank_score" in r
            assert "recommendation_score" in r
        # 应按 rerank_score 降序
        scores = [r["rerank_score"] for r in results]
        assert scores == sorted(scores, reverse=True)


# ===== 测试 2: NLP vs CV 排序差异度 > 30% =====


class TestDifferentResearchFieldDifferentOrder:
    def test_different_research_field_different_order(self):
        """NLP vs CV 用户 Top5 排序差异度 > 30%"""
        settings = _make_settings()
        pers_service = PersonalizationService()
        reranker = Reranker(settings=settings, personalization_service=pers_service)

        papers = _make_papers()
        nlp_profile = _make_nlp_profile()
        cv_profile = _make_cv_profile()

        nlp_results = asyncio.run(reranker.rerank("deep learning", papers, user_profile=nlp_profile))
        cv_results = asyncio.run(reranker.rerank("deep learning", papers, user_profile=cv_profile))

        nlp_top5_ids = [r["paper_id"] for r in nlp_results[:5]]
        cv_top5_ids = [r["paper_id"] for r in cv_results[:5]]

        # 计算差异度：Top5 中不同论文数 / 5
        nlp_set = set(nlp_top5_ids)
        cv_set = set(cv_top5_ids)
        diff_count = len(nlp_set.symmetric_difference(cv_set))
        diff_ratio = diff_count / 5  # 最大 5*2=10，归一化到 /5

        # 差异度 > 30%（即至少 2 篇不同）
        assert diff_ratio > 0.3, (
            f"NLP vs CV Top5 差异度={diff_ratio:.2%} <= 30%, "
            f"NLP={nlp_top5_ids}, CV={cv_top5_ids}"
        )


# ===== 测试 3: recommend() 方法 =====


class TestRecommendMethod:
    def test_recommend_method(self):
        """recommend() 返回推荐论文列表含 recommendation_score"""
        settings = _make_settings()
        pers_service = PersonalizationService()
        reranker = Reranker(settings=settings, personalization_service=pers_service)

        papers = _make_papers()
        profile = _make_nlp_profile()
        history = [
            {"paper_id": "h1", "title": "Attention Mechanism Survey",
             "abstract": "A survey on attention mechanism in NLP and transformer models."}
        ]

        results = asyncio.run(reranker.recommend(papers, profile, history))

        # 应返回所有论文
        assert len(results) == 10
        # 每篇应有 recommendation_score
        for r in results:
            assert "recommendation_score" in r
        # 应按 recommendation_score 降序
        scores = [r["recommendation_score"] for r in results]
        assert scores == sorted(scores, reverse=True)


# ===== 测试 4: 推荐分范围 [0, 1] =====


class TestRecommendationScoreRange:
    def test_recommendation_score_range(self):
        """推荐分范围 [0, 1]"""
        settings = _make_settings()
        pers_service = PersonalizationService()
        reranker = Reranker(settings=settings, personalization_service=pers_service)

        papers = _make_papers()
        profile = _make_nlp_profile()
        history = []

        results = asyncio.run(reranker.recommend(papers, profile, history))

        for r in results:
            score = r["recommendation_score"]
            assert 0.0 <= score <= 1.0, f"recommendation_score={score} 超出 [0, 1]"


# ===== 测试 5: get_recommendation_strategy 4 维度加权 =====


class TestGetRecommendationStrategy:
    def test_get_recommendation_strategy(self):
        """4 维度加权计算推荐分"""
        pers_service = PersonalizationService()

        # NLP 用户 + NLP 论文 → 应得高分
        nlp_profile = _make_nlp_profile()
        nlp_paper = {
            "title": "Transformer for NLP",
            "abstract": "We study attention mechanism and transformer for natural language processing. "
                        "Experiments on language understanding tasks.",
            "venue": "ACL",
            "keywords": ["NLP", "transformer"],
        }
        nlp_score = pers_service.get_recommendation_strategy(nlp_profile, nlp_paper)
        assert 0.0 <= nlp_score <= 1.0
        # NLP 论文对 NLP 用户应得较高分（research_field 完全匹配）
        assert nlp_score > 0.5

        # CV 用户 + NLP 论文 → 应得较低分
        cv_profile = _make_cv_profile()
        cv_score = pers_service.get_recommendation_strategy(cv_profile, nlp_paper)
        assert 0.0 <= cv_score <= 1.0
        # CV 用户对 NLP 论文应得较低分（research_field 不匹配）
        assert cv_score < nlp_score

    def test_get_recommendation_strategy_empty_profile(self):
        """空画像时返回中性分"""
        pers_service = PersonalizationService()
        paper = {
            "title": "Test",
            "abstract": "A test paper.",
            "venue": "",
            "keywords": [],
        }
        score = pers_service.get_recommendation_strategy({}, paper)
        assert 0.0 <= score <= 1.0


# ===== 测试 6: RecommendationService =====


class TestRecommendationService:
    def test_recommendation_service(self):
        """get_recommended_papers() 返回推荐论文列表"""
        settings = _make_settings()
        pers_service = PersonalizationService()
        reranker = Reranker(settings=settings, personalization_service=pers_service)

        # Mock vector_store_service
        mock_vector_store = MagicMock()
        mock_vector_store.search_by_keywords = AsyncMock(
            return_value=[
                {
                    "paperId": "p1",
                    "title": "Transformer for NLP",
                    "abstract": "Attention mechanism for natural language processing.",
                    "score": 0.9,
                    "venue": "ACL",
                    "keywords": ["NLP"],
                },
                {
                    "paperId": "p2",
                    "title": "CNN for CV",
                    "abstract": "Convolutional neural network for computer vision.",
                    "score": 0.85,
                    "venue": "CVPR",
                    "keywords": ["CV"],
                },
            ]
        )

        rec_service = RecommendationService(
            personalization_service=pers_service,
            reranker=reranker,
            vector_store_service=mock_vector_store,
            settings=settings,
        )

        # 注入 user_profile 和 user_history
        profile = _make_nlp_profile()
        history = [
            {"paper_id": "h1", "title": "NLP Survey",
             "abstract": "A survey on natural language processing and attention mechanism."}
        ]

        results = asyncio.run(rec_service.get_recommended_papers(
            user_id="user_test",
            top_k=5,
            user_profile=profile,
            user_history=history,
        ))

        # 应返回推荐论文（候选池 2 篇，top_k=5）
        assert len(results) <= 5
        assert len(results) > 0
        for r in results:
            assert "recommendation_score" in r

    def test_recommendation_service_no_history(self):
        """无历史记录时返回空列表"""
        settings = _make_settings()
        pers_service = PersonalizationService()
        reranker = Reranker(settings=settings, personalization_service=pers_service)

        rec_service = RecommendationService(
            personalization_service=pers_service,
            reranker=reranker,
            vector_store_service=None,
            settings=settings,
        )

        results = asyncio.run(rec_service.get_recommended_papers(
            user_id="user_test",
            top_k=5,
            user_profile=_make_nlp_profile(),
            user_history=[],
        ))

        # 无历史 → 无候选 → 空列表
        assert results == []


# ===== 测试 7: 向后兼容（user_profile=None） =====


class TestRerankBackwardCompat:
    def test_rerank_without_user_profile_backward_compat(self):
        """user_profile 为空时退化为原逻辑（向后兼容）"""
        settings = _make_settings()
        pers_service = PersonalizationService()
        reranker = Reranker(settings=settings, personalization_service=pers_service)

        papers = _make_papers()

        # user_profile=None：应退化为原逻辑（无 recommendation_score 字段）
        results = asyncio.run(reranker.rerank("attention", papers, user_profile=None))

        assert len(results) == 10
        for r in results:
            assert "rerank_score" in r
            # user_profile=None 时不应有 recommendation_score
            assert "recommendation_score" not in r
        # 应按 rerank_score 降序
        scores = [r["rerank_score"] for r in results]
        assert scores == sorted(scores, reverse=True)
