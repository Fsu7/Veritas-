import json
import math
import os
import time
from typing import Dict
from typing import List
from typing import Set

import numpy as np
import pytest
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

from app.services.reranker import Reranker
from app.services.search_service import SearchService

QUERIES_PATH = os.path.join(
    os.path.dirname(__file__), "test_data", "search_queries.json"
)


def calc_mrr(results: List[dict], relevant_ids: Set[str]) -> float:
    if not results or not relevant_ids:
        return 0.0
    for i, item in enumerate(results):
        pid = item.get("paper_id") or item.get("paperId", "")
        if pid in relevant_ids:
            return 1.0 / (i + 1)
    return 0.0


def calc_ndcg(results: List[dict], relevant_ids: Set[str], k: int = 10) -> float:
    if not results or not relevant_ids:
        return 0.0
    top_k = results[:k]
    dcg = 0.0
    for i, item in enumerate(top_k):
        pid = item.get("paper_id") or item.get("paperId", "")
        rel = 1 if pid in relevant_ids else 0
        dcg += (2 ** rel - 1) / math.log2(i + 2)
    ideal_rels = sorted([1] * min(len(relevant_ids), k) + [0] * max(0, k - len(relevant_ids)), reverse=True)
    idcg = 0.0
    for i, rel in enumerate(ideal_rels):
        idcg += (2 ** rel - 1) / math.log2(i + 2)
    if idcg == 0.0:
        return 0.0
    return dcg / idcg


def calc_precision(results: List[dict], relevant_ids: Set[str], k: int = 10) -> float:
    if not results or not relevant_ids:
        return 0.0
    top_k = results[:k]
    relevant_count = sum(
        1
        for item in top_k
        if (item.get("paper_id") or item.get("paperId", "")) in relevant_ids
    )
    return relevant_count / k


def calc_recall(results: List[dict], relevant_ids: Set[str], k: int = 10) -> float:
    if not results or not relevant_ids:
        return 0.0
    top_k = results[:k]
    relevant_count = sum(
        1
        for item in top_k
        if (item.get("paper_id") or item.get("paperId", "")) in relevant_ids
    )
    return relevant_count / len(relevant_ids)


def _load_test_queries() -> List[dict]:
    with open(QUERIES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _make_result(paper_id, title, abstract, score, year=2024, venue="arXiv", citation_count=10, keywords=None):
    r = {
        "paper_id": paper_id,
        "title": title,
        "abstract": abstract,
        "score": score,
        "year": year,
        "venue": venue,
        "citation_count": citation_count,
    }
    if keywords is not None:
        r["keywords"] = keywords
    return r


def _make_raw_result(paper_id, title, abstract, score, year=2024, venue="arXiv", citation_count=10):
    return {
        "paperId": paper_id,
        "title": title,
        "abstract": abstract,
        "score": score,
        "year": year,
        "venue": venue,
        "citation_count": citation_count,
    }


@pytest.fixture
def mock_vector_store():
    svc = MagicMock()
    svc.search = AsyncMock()
    svc.search_by_keywords = AsyncMock()
    svc.suggest_titles = AsyncMock()
    return svc


@pytest.fixture
def mock_embedding():
    svc = MagicMock()
    svc.encode = AsyncMock()
    return svc


@pytest.fixture
def search_service(mock_vector_store, mock_embedding):
    return SearchService(mock_vector_store, mock_embedding)


@pytest.fixture
def search_service_with_reranker(mock_vector_store, mock_embedding):
    reranker = Reranker()
    return SearchService(mock_vector_store, mock_embedding, reranker=reranker)


SAMPLE_PAPERS = [
    {
        "paper_id": "arxiv_2401_0001",
        "title": "Multi-Agent Collaborative Decision Making via Large Language Models",
        "abstract": "We propose a novel multi-agent collaborative decision-making framework that leverages large language models for task decomposition, agent coordination, and result synthesis.",
        "year": 2024,
        "venue": "NeurIPS",
        "citation_count": 85,
        "keywords": ["multi-agent", "collaborative decision-making", "large language models", "task decomposition"],
    },
    {
        "paper_id": "arxiv_2401_0002",
        "title": "AgentBench: A Comprehensive Benchmark for LLM-based Agents",
        "abstract": "We present AgentBench, a comprehensive benchmark for evaluating large language model-based agents across diverse real-world tasks including coding, web navigation, and multi-turn dialogue.",
        "year": 2024,
        "venue": "ICML",
        "citation_count": 120,
        "keywords": ["agent benchmark", "LLM evaluation", "task planning", "reinforcement learning"],
    },
    {
        "paper_id": "arxiv_2401_0003",
        "title": "Retrieval-Augmented Generation for Scientific Literature: A Survey",
        "abstract": "This survey provides a comprehensive review of retrieval-augmented generation techniques applied to scientific literature, covering hybrid retrieval methods and personalized generation.",
        "year": 2023,
        "venue": "ACL",
        "citation_count": 200,
        "keywords": ["retrieval-augmented generation", "scientific literature", "hybrid retrieval", "survey"],
    },
    {
        "paper_id": "arxiv_2401_0004",
        "title": "Knowledge Graph-Enhanced Reasoning for Multi-Hop Question Answering",
        "abstract": "We introduce KG-RAG, a framework that combines knowledge graph reasoning with retrieval-augmented generation for multi-hop question answering.",
        "year": 2024,
        "venue": "AAAI",
        "citation_count": 60,
        "keywords": ["knowledge graph", "multi-hop reasoning", "question answering", "RAG"],
    },
    {
        "paper_id": "arxiv_2401_0005",
        "title": "Human-Agent Collaboration in Complex Task Environments",
        "abstract": "This paper investigates human-agent collaboration strategies in complex task environments where both human and AI agents contribute complementary expertise.",
        "year": 2023,
        "venue": "ACL",
        "citation_count": 45,
        "keywords": ["human-agent collaboration", "mixed-initiative", "adaptive autonomy", "user study"],
    },
]


class TestMetricCalculations:

    def test_mrr_first_position(self):
        results = [
            _make_result("p1", "A", "abs", 0.9),
            _make_result("p2", "B", "abs", 0.8),
        ]
        assert calc_mrr(results, {"p1"}) == 1.0

    def test_mrr_third_position(self):
        results = [
            _make_result("p1", "A", "abs", 0.9),
            _make_result("p2", "B", "abs", 0.8),
            _make_result("p3", "C", "abs", 0.7),
        ]
        assert calc_mrr(results, {"p3"}) == pytest.approx(1.0 / 3)

    def test_mrr_no_relevant(self):
        results = [
            _make_result("p1", "A", "abs", 0.9),
            _make_result("p2", "B", "abs", 0.8),
        ]
        assert calc_mrr(results, {"p99"}) == 0.0

    def test_mrr_empty_results(self):
        assert calc_mrr([], {"p1"}) == 0.0

    def test_mrr_empty_relevant_ids(self):
        results = [_make_result("p1", "A", "abs", 0.9)]
        assert calc_mrr(results, set()) == 0.0

    def test_ndcg_perfect_ranking(self):
        results = [
            _make_result("p1", "A", "abs", 0.9),
            _make_result("p2", "B", "abs", 0.8),
        ]
        ndcg = calc_ndcg(results, {"p1", "p2"}, k=10)
        assert ndcg == pytest.approx(1.0)

    def test_ndcg_worst_ranking(self):
        results = [
            _make_result("p_irr1", "X", "abs", 0.9),
            _make_result("p_irr2", "Y", "abs", 0.8),
            _make_result("p1", "A", "abs", 0.7),
        ]
        ndcg = calc_ndcg(results, {"p1"}, k=10)
        assert ndcg < 1.0
        assert ndcg > 0.0

    def test_ndcg_empty_results(self):
        assert calc_ndcg([], {"p1"}) == 0.0

    def test_ndcg_empty_relevant_ids(self):
        results = [_make_result("p1", "A", "abs", 0.9)]
        assert calc_ndcg(results, set()) == 0.0

    def test_precision_basic(self):
        results = [
            _make_result("p1", "A", "abs", 0.9),
            _make_result("p2", "B", "abs", 0.8),
            _make_result("p_irr", "C", "abs", 0.7),
            _make_result("p3", "D", "abs", 0.6),
        ]
        precision = calc_precision(results, {"p1", "p2", "p3"}, k=4)
        assert precision == pytest.approx(3.0 / 4)

    def test_precision_empty_results(self):
        assert calc_precision([], {"p1"}) == 0.0

    def test_recall_basic(self):
        results = [
            _make_result("p1", "A", "abs", 0.9),
            _make_result("p2", "B", "abs", 0.8),
            _make_result("p_irr", "C", "abs", 0.7),
        ]
        recall = calc_recall(results, {"p1", "p2", "p3"}, k=10)
        assert recall == pytest.approx(2.0 / 3)

    def test_recall_empty_relevant_ids(self):
        results = [_make_result("p1", "A", "abs", 0.9)]
        assert calc_recall(results, set()) == 0.0

    def test_recall_all_relevant_found(self):
        results = [
            _make_result("p1", "A", "abs", 0.9),
            _make_result("p2", "B", "abs", 0.8),
        ]
        recall = calc_recall(results, {"p1", "p2"}, k=10)
        assert recall == 1.0


@pytest.mark.asyncio
class TestSemanticSearchAccuracy:

    async def test_semantic_search_mrr_threshold(self, search_service, mock_embedding, mock_vector_store):
        fake_embedding = np.random.rand(1024).astype(np.float32)
        mock_embedding.encode.return_value = fake_embedding

        raw = [
            _make_raw_result("arxiv_2401_0001", "Multi-Agent Collaborative Decision Making", "Abstract", 0.95),
            _make_raw_result("arxiv_2401_0002", "AgentBench", "Abstract", 0.90),
            _make_raw_result("arxiv_2401_0005", "Human-Agent Collaboration", "Abstract", 0.85),
            _make_raw_result("irr_001", "Unrelated Paper", "Abstract", 0.50),
        ]
        mock_vector_store.search.return_value = raw

        results = await search_service.search("Multi-Agent", top_k=10)
        relevant_ids = {"arxiv_2401_0001", "arxiv_2401_0002", "arxiv_2401_0005"}
        mrr = calc_mrr(results, relevant_ids)
        assert mrr >= 0.6

    async def test_semantic_search_precision_threshold(self, search_service, mock_embedding, mock_vector_store):
        fake_embedding = np.random.rand(1024).astype(np.float32)
        mock_embedding.encode.return_value = fake_embedding

        raw = [
            _make_raw_result("arxiv_2401_0003", "RAG Survey", "Abstract", 0.95),
            _make_raw_result("arxiv_2401_0004", "KG-RAG", "Abstract", 0.90),
            _make_raw_result("irr_001", "Unrelated", "Abstract", 0.50),
            _make_raw_result("irr_002", "Unrelated2", "Abstract", 0.40),
        ]
        mock_vector_store.search.return_value = raw

        results = await search_service.search("retrieval-augmented generation", top_k=10)
        relevant_ids = {"arxiv_2401_0003", "arxiv_2401_0004"}
        precision = calc_precision(results, relevant_ids, k=4)
        assert precision >= 0.5

    async def test_semantic_search_with_test_queries(self, search_service, mock_embedding, mock_vector_store):
        fake_embedding = np.random.rand(1024).astype(np.float32)
        mock_embedding.encode.return_value = fake_embedding

        queries = _load_test_queries()
        all_raw = [_make_raw_result(p["paper_id"], p["title"], p["abstract"], 0.9 - i * 0.05, year=p["year"], venue=p["venue"], citation_count=p["citation_count"]) for i, p in enumerate(SAMPLE_PAPERS)]
        mock_vector_store.search.return_value = all_raw

        total_mrr = 0.0
        count = 0
        for q in queries:
            results = await search_service.search(q["query"], top_k=10)
            relevant_ids = set(q["relevant_paper_ids"])
            mrr = calc_mrr(results, relevant_ids)
            total_mrr += mrr
            count += 1

        avg_mrr = total_mrr / count if count > 0 else 0.0
        assert avg_mrr >= 0.5


@pytest.mark.asyncio
class TestRRFFusionEffectiveness:

    async def test_hybrid_mrr_gte_semantic(self, search_service, mock_embedding, mock_vector_store):
        fake_embedding = np.random.rand(1024).astype(np.float32)
        mock_embedding.encode.return_value = fake_embedding

        semantic_raw = [
            _make_raw_result("arxiv_2401_0001", "Multi-Agent", "Abstract", 0.95),
            _make_raw_result("arxiv_2401_0002", "AgentBench", "Abstract", 0.90),
            _make_raw_result("irr_001", "Unrelated", "Abstract", 0.50),
        ]
        keyword_raw = [
            _make_raw_result("arxiv_2401_0005", "Human-Agent Collaboration", "Abstract", 0.95),
            _make_raw_result("arxiv_2401_0001", "Multi-Agent", "Abstract", 0.90),
            _make_raw_result("arxiv_2401_0002", "AgentBench", "Abstract", 0.85),
        ]
        mock_vector_store.search.return_value = semantic_raw
        mock_vector_store.search_by_keywords.return_value = keyword_raw

        relevant_ids = {"arxiv_2401_0001", "arxiv_2401_0002", "arxiv_2401_0005"}

        semantic_results = await search_service.search("Multi-Agent collaboration", top_k=10)
        semantic_mrr = calc_mrr(semantic_results, relevant_ids)

        hybrid_results = await search_service.hybrid_search("Multi-Agent collaboration", top_k=10)
        hybrid_mrr = calc_mrr(hybrid_results, relevant_ids)

        assert hybrid_mrr >= semantic_mrr

    async def test_hybrid_precision_gte_semantic(self, search_service, mock_embedding, mock_vector_store):
        fake_embedding = np.random.rand(1024).astype(np.float32)
        mock_embedding.encode.return_value = fake_embedding

        semantic_raw = [
            _make_raw_result("arxiv_2401_0003", "RAG Survey", "Abstract", 0.95),
            _make_raw_result("irr_001", "Unrelated", "Abstract", 0.50),
            _make_raw_result("irr_002", "Unrelated2", "Abstract", 0.40),
        ]
        keyword_raw = [
            _make_raw_result("arxiv_2401_0004", "KG-RAG", "Abstract", 0.95),
            _make_raw_result("arxiv_2401_0003", "RAG Survey", "Abstract", 0.90),
        ]
        mock_vector_store.search.return_value = semantic_raw
        mock_vector_store.search_by_keywords.return_value = keyword_raw

        relevant_ids = {"arxiv_2401_0003", "arxiv_2401_0004"}

        semantic_results = await search_service.search("RAG", top_k=10)
        semantic_precision = calc_precision(semantic_results, relevant_ids, k=10)

        hybrid_results = await search_service.hybrid_search("RAG", top_k=10)
        hybrid_precision = calc_precision(hybrid_results, relevant_ids, k=10)

        assert hybrid_precision >= semantic_precision

    async def test_rrf_k_value_impact(self, search_service, mock_embedding, mock_vector_store):
        fake_embedding = np.random.rand(1024).astype(np.float32)
        mock_embedding.encode.return_value = fake_embedding

        semantic_raw = [
            _make_raw_result("p1", "A", "abs", 0.9),
            _make_raw_result("p2", "B", "abs", 0.8),
            _make_raw_result("p3", "C", "abs", 0.7),
        ]
        keyword_raw = [
            _make_raw_result("p4", "D", "abs", 0.9),
            _make_raw_result("p1", "A", "abs", 0.8),
            _make_raw_result("p5", "E", "abs", 0.7),
        ]
        mock_vector_store.search.return_value = semantic_raw
        mock_vector_store.search_by_keywords.return_value = keyword_raw

        relevant_ids = {"p1", "p2", "p3", "p4", "p5"}

        results_k30 = search_service._reciprocal_rank_fusion(semantic_raw, keyword_raw, k=30)
        results_k60 = search_service._reciprocal_rank_fusion(semantic_raw, keyword_raw, k=60)
        results_k120 = search_service._reciprocal_rank_fusion(semantic_raw, keyword_raw, k=120)

        mrr_k30 = calc_mrr(results_k30, relevant_ids)
        mrr_k60 = calc_mrr(results_k60, relevant_ids)
        mrr_k120 = calc_mrr(results_k120, relevant_ids)

        assert mrr_k30 > 0.0
        assert mrr_k60 > 0.0
        assert mrr_k120 > 0.0

        assert len(results_k30) == len(results_k60) == len(results_k120)

    async def test_rrf_complementary_results(self, search_service):
        semantic_only = [
            {"paper_id": "p1", "title": "Semantic Hit", "score": 0.9},
            {"paper_id": "p2", "title": "Semantic Hit 2", "score": 0.8},
        ]
        keyword_only = [
            {"paper_id": "p3", "title": "Keyword Hit", "score": 0.9},
            {"paper_id": "p4", "title": "Keyword Hit 2", "score": 0.8},
        ]

        fused = search_service._reciprocal_rank_fusion(semantic_only, keyword_only, k=60)

        fused_ids = {r.get("paper_id") or r.get("paperId", "") for r in fused}
        assert "p3" in fused_ids
        assert "p4" in fused_ids
        assert "p1" in fused_ids
        assert "p2" in fused_ids


@pytest.mark.asyncio
class TestRerankerImprovement:

    async def test_reranker_ndcg_improvement(self):
        reranker = Reranker()
        query = "multi-agent collaboration"
        results = [
            _make_result("irr_001", "Unrelated Paper", "Unrelated abstract", 0.9, year=2024, citation_count=10),
            _make_result("arxiv_2401_0001", "Multi-Agent Collaborative Decision Making", "multi-agent collaborative decision-making framework", 0.8, year=2024, citation_count=85),
            _make_result("irr_002", "Another Unrelated", "Some text", 0.7, year=2024, citation_count=5),
            _make_result("arxiv_2401_0005", "Human-Agent Collaboration", "human-agent collaboration strategies", 0.6, year=2023, citation_count=45),
        ]
        relevant_ids = {"arxiv_2401_0001", "arxiv_2401_0005"}

        ndcg_before = calc_ndcg(results, relevant_ids, k=10)

        reranked = await reranker.rerank(query, results)
        ndcg_after = calc_ndcg(reranked, relevant_ids, k=10)

        assert ndcg_after >= ndcg_before

    async def test_title_match_rerank_improvement(self):
        reranker = Reranker()
        query = "knowledge graph"
        results = [
            _make_result("p_irr", "Unrelated Paper", "Some abstract", 0.9, year=2024, citation_count=10),
            _make_result("arxiv_2401_0004", "Knowledge Graph-Enhanced Reasoning", "knowledge graph reasoning", 0.8, year=2024, citation_count=60),
        ]
        relevant_ids = {"arxiv_2401_0004"}

        rank_before = next(
            i for i, r in enumerate(results) if r["paper_id"] == "arxiv_2401_0004"
        )
        reranked = await reranker.rerank(query, results)
        rank_after = next(
            i for i, r in enumerate(reranked) if r["paper_id"] == "arxiv_2401_0004"
        )

        assert rank_after <= rank_before

    async def test_citation_rerank_improvement(self):
        reranker = Reranker()
        query = "survey"
        low_cite = _make_result("p_low", "Survey Paper A", "A survey on methods", 0.8, year=2024, citation_count=5)
        high_cite = _make_result("p_high", "Survey Paper B", "A survey on techniques", 0.8, year=2024, citation_count=200)
        results = [low_cite, high_cite]

        reranked = await reranker.rerank(query, results)

        high_idx = next(i for i, r in enumerate(reranked) if r["paper_id"] == "p_high")
        low_idx = next(i for i, r in enumerate(reranked) if r["paper_id"] == "p_low")
        assert high_idx < low_idx

    async def test_personalization_rerank_improvement(self):
        reranker = Reranker()
        query = "language model"
        nlp_paper = _make_result(
            "p_nlp", "Language Model Paper", "About language models",
            0.5, year=2024, venue="ACL", citation_count=10,
            keywords=["nlp", "transformer"],
        )
        cv_paper = _make_result(
            "p_cv", "Language Model Paper", "About language models",
            0.5, year=2024, venue="CVPR", citation_count=10,
            keywords=["computer vision", "cnn"],
        )
        results = [cv_paper, nlp_paper]

        reranked_no_profile = await reranker.rerank(query, results)
        reranked_with_profile = await reranker.rerank(
            query, [cv_paper, nlp_paper], user_profile={"research_field": "nlp"}
        )

        nlp_idx_no_profile = next(
            i for i, r in enumerate(reranked_no_profile) if r["paper_id"] == "p_nlp"
        )
        nlp_idx_with_profile = next(
            i for i, r in enumerate(reranked_with_profile) if r["paper_id"] == "p_nlp"
        )
        assert nlp_idx_with_profile <= nlp_idx_no_profile


@pytest.mark.asyncio
class TestSearchPerformance:

    async def test_semantic_search_latency(self, search_service, mock_embedding, mock_vector_store):
        fake_embedding = np.random.rand(1024).astype(np.float32)
        mock_embedding.encode.return_value = fake_embedding
        mock_vector_store.search.return_value = [
            _make_raw_result("p1", "A", "abs", 0.9),
        ]

        start = time.perf_counter()
        await search_service.search("test query", top_k=10)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100

    async def test_hybrid_search_latency(self, search_service, mock_embedding, mock_vector_store):
        fake_embedding = np.random.rand(1024).astype(np.float32)
        mock_embedding.encode.return_value = fake_embedding
        mock_vector_store.search.return_value = [
            _make_raw_result("p1", "A", "abs", 0.9),
        ]
        mock_vector_store.search_by_keywords.return_value = [
            _make_raw_result("p2", "B", "abs", 0.8),
        ]

        start = time.perf_counter()
        await search_service.hybrid_search("test query", top_k=10)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 200
