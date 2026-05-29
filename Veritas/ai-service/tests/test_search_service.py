import numpy as np
import pytest
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

from app.services.search_service import SearchService

pytestmark = pytest.mark.asyncio


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
def mock_reranker():
    reranker = MagicMock()
    reranker.rerank = AsyncMock()
    return reranker


@pytest.fixture
def search_service(mock_vector_store, mock_embedding):
    return SearchService(mock_vector_store, mock_embedding)


@pytest.fixture
def search_service_with_reranker(mock_vector_store, mock_embedding, mock_reranker):
    return SearchService(mock_vector_store, mock_embedding, reranker=mock_reranker)


class TestSemanticSearch:

    async def test_search_service_semantic_search(self, search_service, mock_embedding, mock_vector_store):
        fake_embedding = np.random.rand(1024).astype(np.float32)
        mock_embedding.encode.return_value = fake_embedding

        raw = [
            _make_raw_result("p1", "Paper One", "Abstract one", 0.95),
            _make_raw_result("p2", "Paper Two", "Abstract two", 0.85),
        ]
        mock_vector_store.search.return_value = raw

        results = await search_service.search("multi-agent", top_k=5, filters={"year": 2024})

        mock_embedding.encode.assert_awaited_once_with("multi-agent")
        mock_vector_store.search.assert_awaited_once_with(
            embedding=fake_embedding.tolist(),
            top_k=5,
            filters={"year": 2024},
        )
        assert len(results) == 2
        assert results[0]["paper_id"] == "p1"
        assert results[0]["title"] == "Paper One"
        assert results[0]["abstract"] == "Abstract one"
        assert results[0]["score"] == 0.95
        assert results[0]["year"] == 2024
        assert results[0]["venue"] == "arXiv"
        assert results[0]["citation_count"] == 10

    async def test_search_default_params(self, search_service, mock_embedding, mock_vector_store):
        fake_embedding = np.random.rand(1024).astype(np.float32)
        mock_embedding.encode.return_value = fake_embedding
        mock_vector_store.search.return_value = []

        await search_service.search("test query")

        mock_vector_store.search.assert_awaited_once_with(
            embedding=fake_embedding.tolist(),
            top_k=10,
            filters=None,
        )


class TestKeywordSearch:

    async def test_search_service_keyword_search(self, search_service, mock_vector_store):
        raw = [
            _make_raw_result("p3", "Keyword Paper", "Abstract kw", 0.70),
        ]
        mock_vector_store.search_by_keywords.return_value = raw

        results = await search_service.keyword_search("reinforcement learning", top_k=3, filters={"venue": "NeurIPS"})

        mock_vector_store.search_by_keywords.assert_awaited_once_with(
            query_text="reinforcement learning",
            top_k=3,
            filters={"venue": "NeurIPS"},
        )
        assert len(results) == 1
        assert results[0]["paper_id"] == "p3"
        assert results[0]["title"] == "Keyword Paper"

    async def test_keyword_search_default_params(self, search_service, mock_vector_store):
        mock_vector_store.search_by_keywords.return_value = []

        await search_service.keyword_search("test")

        mock_vector_store.search_by_keywords.assert_awaited_once_with(
            query_text="test",
            top_k=10,
            filters=None,
        )


class TestRRFFusion:

    async def test_rrf_fusion_with_overlap(self, search_service):
        list1 = [
            {"paperId": "p1", "title": "A", "score": 0.9},
            {"paperId": "p2", "title": "B", "score": 0.8},
            {"paperId": "p3", "title": "C", "score": 0.7},
        ]
        list2 = [
            {"paperId": "p2", "title": "B", "score": 0.95},
            {"paperId": "p4", "title": "D", "score": 0.85},
            {"paperId": "p1", "title": "A", "score": 0.75},
        ]

        result = search_service._reciprocal_rank_fusion(list1, list2, k=60)

        pids = [r["paperId"] for r in result]
        assert len(pids) == len(set(pids))

        p1_score = 1.0 / (60 + 0 + 1) + 1.0 / (60 + 2 + 1)
        p2_score = 1.0 / (60 + 1 + 1) + 1.0 / (60 + 0 + 1)
        p3_score = 1.0 / (60 + 2 + 1)
        p4_score = 1.0 / (60 + 1 + 1)

        expected_order = sorted(
            [("p1", p1_score), ("p2", p2_score), ("p3", p3_score), ("p4", p4_score)],
            key=lambda x: x[1],
            reverse=True,
        )
        assert [r["paperId"] for r in result] == [e[0] for e in expected_order]

        for r in result:
            assert "rrf_score" in r

        assert result[0]["rrf_score"] >= result[-1]["rrf_score"]

    async def test_rrf_fusion_dedup_preserves_first_occurrence(self, search_service):
        list1 = [{"paperId": "p1", "title": "From List1", "score": 0.9}]
        list2 = [{"paperId": "p1", "title": "From List2", "score": 0.8}]

        result = search_service._reciprocal_rank_fusion(list1, list2)

        assert len(result) == 1
        assert result[0]["title"] == "From List1"

    async def test_rrf_fusion_empty_lists(self, search_service):
        result = search_service._reciprocal_rank_fusion([], [])
        assert result == []

    async def test_rrf_fusion_one_empty(self, search_service):
        list1 = [{"paperId": "p1", "title": "A", "score": 0.9}]
        result = search_service._reciprocal_rank_fusion(list1, [])
        assert len(result) == 1
        assert result[0]["paperId"] == "p1"

    async def test_rrf_fusion_skips_empty_paper_id(self, search_service):
        list1 = [
            {"paperId": "", "title": "No ID", "score": 0.9},
            {"paperId": "p1", "title": "Valid", "score": 0.8},
        ]
        list2 = []

        result = search_service._reciprocal_rank_fusion(list1, list2)
        assert len(result) == 1
        assert result[0]["paperId"] == "p1"

    async def test_rrf_fusion_paper_id_fallback(self, search_service):
        list1 = [{"paper_id": "p1", "title": "A", "score": 0.9}]
        list2 = [{"paperId": "p2", "title": "B", "score": 0.8}]

        result = search_service._reciprocal_rank_fusion(list1, list2)
        assert len(result) == 2
        pids = set()
        for r in result:
            pids.add(r.get("paperId") or r.get("paper_id"))
        assert pids == {"p1", "p2"}


class TestHybridSearch:

    async def test_search_service_hybrid_search(self, search_service, mock_embedding, mock_vector_store):
        fake_embedding = np.random.rand(1024).astype(np.float32)
        mock_embedding.encode.return_value = fake_embedding

        semantic_raw = [
            _make_raw_result("p1", "Semantic A", "Abs A", 0.9),
            _make_raw_result("p2", "Semantic B", "Abs B", 0.8),
        ]
        keyword_raw = [
            _make_raw_result("p2", "Keyword B", "Abs B2", 0.95),
            _make_raw_result("p3", "Keyword C", "Abs C", 0.85),
        ]
        mock_vector_store.search.return_value = semantic_raw
        mock_vector_store.search_by_keywords.return_value = keyword_raw

        results = await search_service.hybrid_search("transformer", top_k=5, filters={"year": 2023})

        mock_embedding.encode.assert_awaited_once_with("transformer")
        mock_vector_store.search.assert_awaited_once()
        mock_vector_store.search_by_keywords.assert_awaited_once()

        call_kwargs = mock_vector_store.search.call_args
        assert call_kwargs.kwargs["top_k"] == 10

        call_kwargs_kw = mock_vector_store.search_by_keywords.call_args
        assert call_kwargs_kw.kwargs["top_k"] == 10

        assert len(results) <= 5
        assert all("rrf_score" in r for r in results)
        if len(results) > 1:
            assert results[0]["rrf_score"] >= results[1]["rrf_score"]

    async def test_hybrid_search_truncates_to_top_k(self, search_service, mock_embedding, mock_vector_store):
        fake_embedding = np.random.rand(1024).astype(np.float32)
        mock_embedding.encode.return_value = fake_embedding

        semantic_raw = [_make_raw_result(f"ps{i}", f"S{i}", f"Abs{i}", 0.9 - i * 0.05) for i in range(8)]
        keyword_raw = [_make_raw_result(f"pk{i}", f"K{i}", f"AbsK{i}", 0.9 - i * 0.05) for i in range(8)]
        mock_vector_store.search.return_value = semantic_raw
        mock_vector_store.search_by_keywords.return_value = keyword_raw

        results = await search_service.hybrid_search("test", top_k=3)
        assert len(results) == 3


class TestRerankerIntegration:

    async def test_no_reranker_skips_rerank(self, search_service, mock_embedding, mock_vector_store):
        fake_embedding = np.random.rand(1024).astype(np.float32)
        mock_embedding.encode.return_value = fake_embedding
        mock_vector_store.search.return_value = [_make_raw_result("p1", "A", "Abs", 0.9)]

        results = await search_service.search("test")

        assert results[0]["paper_id"] == "p1"

    async def test_reranker_called_in_search(self, search_service_with_reranker, mock_embedding, mock_vector_store, mock_reranker):
        fake_embedding = np.random.rand(1024).astype(np.float32)
        mock_embedding.encode.return_value = fake_embedding
        mock_vector_store.search.return_value = [_make_raw_result("p1", "A", "Abs", 0.9)]

        reranked = [{"paper_id": "p1", "title": "A", "abstract": "Abs", "score": 0.99, "year": 2024, "venue": "arXiv", "citation_count": 10}]
        mock_reranker.rerank.return_value = reranked

        results = await search_service_with_reranker.search("test")

        mock_reranker.rerank.assert_awaited_once()
        call_args = mock_reranker.rerank.call_args
        assert call_args.args[0] == "test"

    async def test_reranker_called_in_hybrid_search(self, search_service_with_reranker, mock_embedding, mock_vector_store, mock_reranker):
        fake_embedding = np.random.rand(1024).astype(np.float32)
        mock_embedding.encode.return_value = fake_embedding
        mock_vector_store.search.return_value = [_make_raw_result("p1", "A", "Abs", 0.9)]
        mock_vector_store.search_by_keywords.return_value = [_make_raw_result("p2", "B", "AbsB", 0.8)]

        reranked = [
            {"paper_id": "p2", "title": "B", "abstract": "AbsB", "score": 0.99, "year": 2024, "venue": "arXiv", "citation_count": 5},
            {"paper_id": "p1", "title": "A", "abstract": "Abs", "score": 0.88, "year": 2024, "venue": "arXiv", "citation_count": 10},
        ]
        mock_reranker.rerank.return_value = reranked

        results = await search_service_with_reranker.hybrid_search("test", top_k=2)

        assert mock_reranker.rerank.await_count == 2
        assert len(results) == 2
        assert results[0]["paper_id"] == "p2"

    async def test_reranker_failure_returns_original(self, search_service_with_reranker, mock_embedding, mock_vector_store, mock_reranker):
        fake_embedding = np.random.rand(1024).astype(np.float32)
        mock_embedding.encode.return_value = fake_embedding
        mock_vector_store.search.return_value = [_make_raw_result("p1", "A", "Abs", 0.9)]

        mock_reranker.rerank.side_effect = RuntimeError("reranker crashed")

        results = await search_service_with_reranker.search("test")

        assert len(results) == 1
        assert results[0]["paper_id"] == "p1"


class TestErrorHandling:

    async def test_embedding_encode_exception_returns_empty(self, search_service, mock_embedding):
        mock_embedding.encode.side_effect = RuntimeError("model not loaded")

        results = await search_service.search("test query")

        assert results == []

    async def test_vector_store_search_exception_returns_empty(self, search_service, mock_embedding, mock_vector_store):
        fake_embedding = np.random.rand(1024).astype(np.float32)
        mock_embedding.encode.return_value = fake_embedding
        mock_vector_store.search.side_effect = ConnectionError("chroma down")

        results = await search_service.search("test query")

        assert results == []

    async def test_keyword_search_exception_returns_empty(self, search_service, mock_vector_store):
        mock_vector_store.search_by_keywords.side_effect = ConnectionError("chroma down")

        results = await search_service.keyword_search("test query")

        assert results == []

    async def test_hybrid_search_exception_returns_empty(self, search_service, mock_embedding, mock_vector_store):
        fake_embedding = np.random.rand(1024).astype(np.float32)
        mock_embedding.encode.return_value = fake_embedding
        mock_vector_store.search.side_effect = RuntimeError("fail")
        mock_vector_store.search_by_keywords.return_value = []

        results = await search_service.hybrid_search("test query")

        assert results == []

    async def test_suggest_exception_returns_empty(self, search_service, mock_vector_store):
        mock_vector_store.suggest_titles.side_effect = RuntimeError("fail")

        results = await search_service.suggest("test")

        assert results == []


class TestSuggest:

    async def test_search_service_suggest(self, search_service, mock_vector_store):
        expected_titles = ["Multi-Agent Systems", "Multi-Task Learning", "Multi-Modal Fusion"]
        mock_vector_store.suggest_titles.return_value = expected_titles

        results = await search_service.suggest("multi", top_k=3)

        mock_vector_store.suggest_titles.assert_awaited_once_with("multi", top_k=3)
        assert results == expected_titles
        assert len(results) == 3

    async def test_suggest_default_top_k(self, search_service, mock_vector_store):
        mock_vector_store.suggest_titles.return_value = ["Title1"]

        await search_service.suggest("test")

        mock_vector_store.suggest_titles.assert_awaited_once_with("test", top_k=5)


class TestFormatResults:

    async def test_format_results_camel_to_snake(self, search_service):
        raw = [
            {
                "paperId": "p1",
                "title": "Test Paper",
                "abstract": "Abstract text",
                "score": 0.92,
                "year": 2024,
                "venue": "ICML",
                "citation_count": 42,
            }
        ]

        result = search_service._format_results(raw)

        assert len(result) == 1
        assert result[0]["paper_id"] == "p1"
        assert result[0]["title"] == "Test Paper"
        assert result[0]["abstract"] == "Abstract text"
        assert result[0]["score"] == 0.92
        assert result[0]["year"] == 2024
        assert result[0]["venue"] == "ICML"
        assert result[0]["citation_count"] == 42

    async def test_format_results_missing_fields_defaults(self, search_service):
        raw = [{"paperId": "p2", "title": "Minimal"}]

        result = search_service._format_results(raw)

        assert result[0]["abstract"] is None
        assert result[0]["score"] == 0.0
        assert result[0]["year"] is None
        assert result[0]["venue"] is None
        assert result[0]["citation_count"] == 0

    async def test_format_results_paper_id_fallback(self, search_service):
        raw = [{"paper_id": "p3", "title": "Snake Case"}]

        result = search_service._format_results(raw)

        assert result[0]["paper_id"] == "p3"

    async def test_format_results_empty_list(self, search_service):
        result = search_service._format_results([])
        assert result == []
