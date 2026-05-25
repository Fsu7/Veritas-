import numpy as np
import pytest

from app.services.vector_store_service import VectorStoreService

pytestmark = pytest.mark.asyncio


def _random_unit_vector(dim=1024):
    v = np.random.randn(dim).astype(np.float32)
    v = v / np.linalg.norm(v)
    return v.tolist()


def _make_metadata(paper_id, title, year, venue, citation_count=0):
    return {
        "paper_id": paper_id,
        "title": title,
        "year": year,
        "venue": venue,
        "citation_count": citation_count,
        "chunk_index": 0,
        "chunk_type": "title_abstract",
    }


class TestVectorStoreInit:

    async def test_initialize(self, vector_store_service):
        assert vector_store_service.status == "connected"

    async def test_collection_name(self, vector_store_service):
        assert vector_store_service.collection.name == "papers"

    async def test_empty_count(self, vector_store_service):
        count = await vector_store_service.count()
        assert count == 0


class TestVectorStoreCRUD:

    async def test_add_papers_and_count(self, vector_store_service):
        ids = ["p001", "p002", "p003"]
        embeddings = [_random_unit_vector() for _ in range(3)]
        metadatas = [
            _make_metadata("p001", "Paper 1", 2023, "ACL"),
            _make_metadata("p002", "Paper 2", 2024, "EMNLP"),
            _make_metadata("p003", "Paper 3", 2022, "NAACL"),
        ]
        documents = ["Abstract 1", "Abstract 2", "Abstract 3"]

        await vector_store_service.add_papers(ids, embeddings, metadatas, documents)
        count = await vector_store_service.count()
        assert count == 3

    async def test_add_papers_invalid_lengths(self, vector_store_service):
        ids = ["p001", "p002", "p003"]
        embeddings = [_random_unit_vector() for _ in range(2)]
        metadatas = [
            _make_metadata("p001", "Paper 1", 2023, "ACL"),
            _make_metadata("p002", "Paper 2", 2024, "EMNLP"),
        ]
        documents = ["Abstract 1", "Abstract 2"]

        with pytest.raises(ValueError):
            await vector_store_service.add_papers(ids, embeddings, metadatas, documents)

    async def test_delete_papers(self, vector_store_service):
        ids = ["p001", "p002", "p003"]
        embeddings = [_random_unit_vector() for _ in range(3)]
        metadatas = [
            _make_metadata("p001", "Paper 1", 2023, "ACL"),
            _make_metadata("p002", "Paper 2", 2024, "EMNLP"),
            _make_metadata("p003", "Paper 3", 2022, "NAACL"),
        ]
        documents = ["Abstract 1", "Abstract 2", "Abstract 3"]

        await vector_store_service.add_papers(ids, embeddings, metadatas, documents)
        await vector_store_service.delete_papers(["p001"])
        count = await vector_store_service.count()
        assert count == 2

    async def test_add_after_delete(self, vector_store_service):
        ids = ["p001", "p002", "p003"]
        embeddings = [_random_unit_vector() for _ in range(3)]
        metadatas = [
            _make_metadata("p001", "Paper 1", 2023, "ACL"),
            _make_metadata("p002", "Paper 2", 2024, "EMNLP"),
            _make_metadata("p003", "Paper 3", 2022, "NAACL"),
        ]
        documents = ["Abstract 1", "Abstract 2", "Abstract 3"]

        await vector_store_service.add_papers(ids, embeddings, metadatas, documents)
        await vector_store_service.delete_papers(["p001"])

        new_embedding = _random_unit_vector()
        await vector_store_service.add_papers(
            ["p004"],
            [new_embedding],
            [_make_metadata("p004", "Paper 4", 2024, "ACL")],
            ["Abstract 4"],
        )
        count = await vector_store_service.count()
        assert count == 3


class TestVectorStoreSearch:

    async def test_search_basic(self, vector_store_service):
        emb1 = _random_unit_vector()
        emb2 = _random_unit_vector()
        emb3 = _random_unit_vector()
        ids = ["p001", "p002", "p003"]
        embeddings = [emb1, emb2, emb3]
        metadatas = [
            _make_metadata("p001", "Paper 1", 2023, "ACL"),
            _make_metadata("p002", "Paper 2", 2024, "EMNLP"),
            _make_metadata("p003", "Paper 3", 2022, "NAACL"),
        ]
        documents = ["Abstract 1", "Abstract 2", "Abstract 3"]

        await vector_store_service.add_papers(ids, embeddings, metadatas, documents)

        results = await vector_store_service.search(emb2, top_k=2)
        assert len(results) == 2
        assert results[0]["paperId"] == "p002"
        assert results[0]["score"] > 0.9

    async def test_search_score_range(self, vector_store_service):
        emb1 = _random_unit_vector()
        emb2 = _random_unit_vector()
        emb3 = _random_unit_vector()
        ids = ["p001", "p002", "p003"]
        embeddings = [emb1, emb2, emb3]
        metadatas = [
            _make_metadata("p001", "Paper 1", 2023, "ACL"),
            _make_metadata("p002", "Paper 2", 2024, "EMNLP"),
            _make_metadata("p003", "Paper 3", 2022, "NAACL"),
        ]
        documents = ["Abstract 1", "Abstract 2", "Abstract 3"]

        await vector_store_service.add_papers(ids, embeddings, metadatas, documents)

        results = await vector_store_service.search(emb1, top_k=3)
        assert len(results) > 0
        assert results[0]["score"] > 0.9

    async def test_search_year_filter(self, vector_store_service):
        ids = ["p2020", "p2022", "p2024"]
        embeddings = [_random_unit_vector() for _ in range(3)]
        metadatas = [
            _make_metadata("p2020", "Paper 2020", 2020, "ACL"),
            _make_metadata("p2022", "Paper 2022", 2022, "EMNLP"),
            _make_metadata("p2024", "Paper 2024", 2024, "NAACL"),
        ]
        documents = ["Abstract 2020", "Abstract 2022", "Abstract 2024"]

        await vector_store_service.add_papers(ids, embeddings, metadatas, documents)

        results = await vector_store_service.search(
            embeddings[1], top_k=10, filters={"yearFrom": 2021, "yearTo": 2023}
        )
        for r in results:
            assert 2021 <= r["year"] <= 2023

    async def test_search_venue_filter(self, vector_store_service):
        ids = ["p001", "p002", "p003"]
        embeddings = [_random_unit_vector() for _ in range(3)]
        metadatas = [
            _make_metadata("p001", "Paper 1", 2023, "ACL"),
            _make_metadata("p002", "Paper 2", 2024, "EMNLP"),
            _make_metadata("p003", "Paper 3", 2022, "ACL"),
        ]
        documents = ["Abstract 1", "Abstract 2", "Abstract 3"]

        await vector_store_service.add_papers(ids, embeddings, metadatas, documents)

        results = await vector_store_service.search(
            embeddings[0], top_k=10, filters={"venue": "ACL"}
        )
        for r in results:
            assert r["venue"] == "ACL"

    async def test_search_empty_result(self, vector_store_service):
        query_emb = _random_unit_vector()
        results = await vector_store_service.search(query_emb, top_k=5)
        assert results == []
