import math
from datetime import datetime

import pytest

from app.services.reranker import Reranker

pytestmark = pytest.mark.asyncio


def _make_result(
    paper_id="p001",
    title="A Study of Neural Networks",
    abstract="This paper studies neural networks and deep learning.",
    score=0.5,
    rrf_score=None,
    year=2024,
    venue="ICML",
    citation_count=10,
    keywords=None,
):
    r = {
        "paper_id": paper_id,
        "title": title,
        "abstract": abstract,
        "score": score,
        "year": year,
        "venue": venue,
        "citation_count": citation_count,
    }
    if rrf_score is not None:
        r["rrf_score"] = rrf_score
    if keywords is not None:
        r["keywords"] = keywords
    return r


class TestRerankerTitleMatchBoost:
    async def test_title_match_ranks_higher(self):
        reranker = Reranker()
        query = "transformer attention"
        paper_with_match = _make_result(
            paper_id="p_match",
            title="Transformer Attention Mechanisms in NLP",
            abstract="A study of attention mechanisms.",
            score=0.5,
            year=2024,
            citation_count=0,
        )
        paper_without_match = _make_result(
            paper_id="p_no_match",
            title="Graph Neural Networks for Social Networks",
            abstract="A study of graph structures.",
            score=0.5,
            year=2024,
            citation_count=0,
        )
        results = await reranker.rerank(query, [paper_with_match, paper_without_match])
        assert results[0]["paper_id"] == "p_match"
        assert results[0]["rerank_score"] > results[1]["rerank_score"]

    async def test_title_match_boost_value(self):
        reranker = Reranker()
        query = "transformer"
        paper = _make_result(
            paper_id="p001",
            title="Transformer Models",
            abstract="irrelevant content",
            score=0.0,
            year=2024,
            citation_count=0,
        )
        results = await reranker.rerank(query, [paper])
        expected_title_boost = reranker.TITLE_MATCH_BOOST
        abstract = "irrelevant content"
        keyword_count = sum(1 for kw in query.lower().split() if kw in abstract)
        keyword_density = (keyword_count / len(abstract)) * reranker.KEYWORD_DENSITY_WEIGHT
        field_score = (expected_title_boost + keyword_density) * 1.0
        expected = 0.0 * 0.5 + field_score * 0.3 + 0.0 * 0.2
        assert abs(results[0]["rerank_score"] - expected) < 1e-9


class TestRerankerKeywordDensity:
    async def test_higher_keyword_density_ranks_higher(self):
        reranker = Reranker()
        query = "reinforcement learning"
        dense_paper = _make_result(
            paper_id="p_dense",
            title="Paper A",
            abstract="reinforcement learning",
            score=0.5,
            year=2024,
            citation_count=0,
        )
        sparse_paper = _make_result(
            paper_id="p_sparse",
            title="Paper B",
            abstract="reinforcement learning is a broad topic covering many areas of machine learning research",
            score=0.5,
            year=2024,
            citation_count=0,
        )
        results = await reranker.rerank(query, [dense_paper, sparse_paper])
        assert results[0]["paper_id"] == "p_dense"

    async def test_keyword_density_calculation(self):
        reranker = Reranker()
        query = "nlp"
        abstract = "nlp nlp nlp"
        paper = _make_result(
            paper_id="p001",
            title="Paper",
            abstract=abstract,
            score=0.0,
            year=2024,
            citation_count=0,
        )
        results = await reranker.rerank(query, [paper])
        keyword_count = sum(1 for kw in query.lower().split() if kw in abstract)
        density = (keyword_count / len(abstract)) * reranker.KEYWORD_DENSITY_WEIGHT
        field_score = density * 1.0
        expected = 0.0 * 0.5 + field_score * 0.3 + 0.0 * 0.2
        assert abs(results[0]["rerank_score"] - expected) < 1e-9


class TestRerankerCitationBoost:
    async def test_high_citation_ranks_higher(self):
        reranker = Reranker()
        query = "deep learning"
        high_cite = _make_result(
            paper_id="p_high",
            title="Deep Learning Paper",
            abstract="About deep learning.",
            score=0.5,
            year=2024,
            citation_count=200,
        )
        low_cite = _make_result(
            paper_id="p_low",
            title="Deep Learning Paper",
            abstract="About deep learning.",
            score=0.5,
            year=2024,
            citation_count=5,
        )
        results = await reranker.rerank(query, [high_cite, low_cite])
        assert results[0]["paper_id"] == "p_high"

    async def test_citation_normalized_to_one(self):
        reranker = Reranker()
        query = "test"
        paper_100 = _make_result(
            paper_id="p100",
            title="Paper",
            abstract="test",
            score=0.0,
            year=2024,
            citation_count=100,
        )
        paper_500 = _make_result(
            paper_id="p500",
            title="Paper",
            abstract="test",
            score=0.0,
            year=2024,
            citation_count=500,
        )
        results = await reranker.rerank(query, [paper_100, paper_500])
        assert results[0]["rerank_score"] == results[1]["rerank_score"]

    async def test_citation_boost_value(self):
        reranker = Reranker()
        query = "test"
        paper = _make_result(
            paper_id="p001",
            title="Paper",
            abstract="test",
            score=0.0,
            year=2024,
            citation_count=50,
        )
        results = await reranker.rerank(query, [paper])
        citation_boost = min(50 / 100, 1.0) * reranker.CITATION_BOOST_WEIGHT
        keyword_density = (1 / len("test")) * reranker.KEYWORD_DENSITY_WEIGHT
        field_score = (0.0 + keyword_density + citation_boost) * 1.0
        popularity_score = min(50 / 100, 1.0)
        expected = 0.0 * 0.5 + field_score * 0.3 + popularity_score * 0.2
        assert abs(results[0]["rerank_score"] - expected) < 1e-9


class TestRerankerYearDecay:
    async def test_recent_papers_no_decay(self):
        reranker = Reranker()
        current_year = datetime.now().year
        query = "test"
        recent_paper = _make_result(
            paper_id="p_recent",
            title="Paper",
            abstract="test",
            score=0.3,
            year=current_year,
            citation_count=50,
        )
        old_paper = _make_result(
            paper_id="p_old",
            title="Paper",
            abstract="test",
            score=0.3,
            year=current_year - 10,
            citation_count=50,
        )
        results = await reranker.rerank(query, [recent_paper, old_paper])
        assert results[0]["paper_id"] == "p_recent"

    async def test_within_threshold_no_decay(self):
        reranker = Reranker()
        current_year = datetime.now().year
        query = "test"
        paper = _make_result(
            paper_id="p001",
            title="Paper",
            abstract="test",
            score=0.0,
            year=current_year - reranker.RECENT_YEAR_THRESHOLD,
            citation_count=0,
        )
        results = await reranker.rerank(query, [paper])
        keyword_density = (1 / len("test")) * reranker.KEYWORD_DENSITY_WEIGHT
        field_score = keyword_density * 1.0
        expected = 0.0 * 0.5 + field_score * 0.3 + 0.0 * 0.2
        assert abs(results[0]["rerank_score"] - expected) < 1e-9

    async def test_old_paper_exponential_decay(self):
        reranker = Reranker()
        current_year = datetime.now().year
        delta = 10
        query = "test"
        paper = _make_result(
            paper_id="p_old",
            title="Paper",
            abstract="test",
            score=0.0,
            year=current_year - delta,
            citation_count=0,
        )
        results = await reranker.rerank(query, [paper])
        expected_decay = math.exp(-reranker.YEAR_DECAY_RATE * delta)
        keyword_density = (1 / len("test")) * reranker.KEYWORD_DENSITY_WEIGHT
        field_score = keyword_density * expected_decay
        expected = 0.0 * 0.5 + field_score * 0.3 + 0.0 * 0.2
        assert abs(results[0]["rerank_score"] - expected) < 1e-9


class TestRerankerPersonalization:
    async def test_venue_match_boosts_rank(self):
        reranker = Reranker()
        query = "language model"
        matching_paper = _make_result(
            paper_id="p_match",
            title="Language Model Paper",
            abstract="About language models.",
            score=0.5,
            year=2024,
            venue="ACL-NLP Workshop",
            citation_count=0,
        )
        non_matching_paper = _make_result(
            paper_id="p_no_match",
            title="Language Model Paper",
            abstract="About language models.",
            score=0.5,
            year=2024,
            venue="CVPR",
            citation_count=0,
        )
        profile = {"research_field": "nlp"}
        results = await reranker.rerank(
            query, [matching_paper, non_matching_paper], user_profile=profile
        )
        assert results[0]["paper_id"] == "p_match"

    async def test_keyword_match_boosts_rank(self):
        reranker = Reranker()
        query = "language model"
        matching_paper = _make_result(
            paper_id="p_kw",
            title="Language Model Paper",
            abstract="About language models.",
            score=0.5,
            year=2024,
            venue="ICML",
            citation_count=0,
            keywords=["nlp methods", "transformer"],
        )
        non_matching_paper = _make_result(
            paper_id="p_no_kw",
            title="Language Model Paper",
            abstract="About language models.",
            score=0.5,
            year=2024,
            venue="ICML",
            citation_count=0,
            keywords=["computer vision", "cnn"],
        )
        profile = {"research_field": "nlp"}
        results = await reranker.rerank(
            query, [matching_paper, non_matching_paper], user_profile=profile
        )
        assert results[0]["paper_id"] == "p_kw"

    async def test_no_profile_no_boost(self):
        reranker = Reranker()
        query = "test"
        paper = _make_result(
            paper_id="p001",
            title="Paper",
            abstract="test",
            score=0.3,
            year=2024,
            venue="ACL-NLP",
            citation_count=0,
        )
        results_with = await reranker.rerank(
            query, [paper], user_profile={"research_field": "nlp"}
        )
        results_without = await reranker.rerank(query, [paper])
        assert results_with[0]["rerank_score"] > results_without[0]["rerank_score"]
        assert abs(
            results_with[0]["rerank_score"] - results_without[0]["rerank_score"]
        ) == pytest.approx(reranker.PERSONALIZATION_BOOST)


class TestRerankerCompositeScore:
    async def test_composite_formula(self):
        reranker = Reranker()
        query = "deep learning"
        paper = _make_result(
            paper_id="p001",
            title="Deep Learning Survey",
            abstract="deep learning is a method for deep learning research",
            score=0.6,
            year=2024,
            citation_count=80,
        )
        results = await reranker.rerank(query, [paper])
        score_rrf = 0.6
        title_match_boost = 2 * reranker.TITLE_MATCH_BOOST
        abstract = "deep learning is a method for deep learning research"
        keyword_count = sum(1 for kw in query.lower().split() if kw in abstract)
        keyword_density = (keyword_count / len(abstract)) * reranker.KEYWORD_DENSITY_WEIGHT
        citation_boost = min(80 / 100, 1.0) * reranker.CITATION_BOOST_WEIGHT
        field_score = (title_match_boost + keyword_density + citation_boost) * 1.0
        popularity_score = min(80 / 100, 1.0)
        expected = (
            score_rrf * reranker.weight_rrf
            + field_score * reranker.weight_field
            + popularity_score * reranker.weight_popularity
        )
        assert abs(results[0]["rerank_score"] - expected) < 1e-9

    async def test_results_sorted_descending(self):
        reranker = Reranker()
        query = "transformer"
        papers = [
            _make_result(paper_id=f"p{i:03d}", title=f"Paper {i}", abstract="transformer", score=0.1 * i, year=2024, citation_count=i * 10)
            for i in range(1, 6)
        ]
        results = await reranker.rerank(query, papers)
        scores = [r["rerank_score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    async def test_rrf_score_used_when_score_missing(self):
        reranker = Reranker()
        query = "test"
        paper = _make_result(
            paper_id="p001",
            title="Paper",
            abstract="test",
            score=None,
            rrf_score=0.25,
            year=2024,
            citation_count=0,
        )
        del paper["score"]
        paper["rrf_score"] = 0.25
        results = await reranker.rerank(query, [paper])
        assert results[0]["rerank_score"] > 0.0


class TestRerankerErrorHandling:
    async def test_empty_list_returns_empty(self):
        reranker = Reranker()
        results = await reranker.rerank("query", [])
        assert results == []

    async def test_none_results_handled(self):
        reranker = Reranker()
        paper_no_title = {"paper_id": "p001", "abstract": "some text", "score": 0.5, "year": 2024, "citation_count": 0}
        results = await reranker.rerank("test", [paper_no_title])
        assert len(results) == 1
        assert "rerank_score" in results[0]

    async def test_missing_fields_handled(self):
        reranker = Reranker()
        paper_minimal = {"paper_id": "p001"}
        results = await reranker.rerank("test", [paper_minimal])
        assert len(results) == 1
        assert "rerank_score" in results[0]

    async def test_none_abstract_handled(self):
        reranker = Reranker()
        paper = _make_result(paper_id="p001", title="Paper", abstract=None, score=0.3, year=2024, citation_count=0)
        results = await reranker.rerank("test", [paper])
        assert len(results) == 1
        assert "rerank_score" in results[0]

    async def test_none_year_defaults_to_current(self):
        reranker = Reranker()
        current_year = datetime.now().year
        paper = _make_result(paper_id="p001", title="Paper", abstract="test", score=0.3, year=None, citation_count=0)
        results = await reranker.rerank("test", [paper])
        assert len(results) == 1
        keyword_density = (1 / len("test")) * reranker.KEYWORD_DENSITY_WEIGHT
        field_score = keyword_density * 1.0
        expected = 0.3 * 0.5 + field_score * 0.3 + 0.0 * 0.2
        assert abs(results[0]["rerank_score"] - expected) < 1e-9

    async def test_output_preserves_original_fields(self):
        reranker = Reranker()
        paper = _make_result(
            paper_id="p001",
            title="Test Paper",
            abstract="test abstract",
            score=0.5,
            year=2024,
            venue="ACL",
            citation_count=10,
        )
        results = await reranker.rerank("test", [paper])
        assert results[0]["paper_id"] == "p001"
        assert results[0]["title"] == "Test Paper"
        assert results[0]["abstract"] == "test abstract"
        assert results[0]["year"] == 2024
        assert results[0]["venue"] == "ACL"
        assert results[0]["citation_count"] == 10
        assert "rerank_score" in results[0]
