import numpy as np
import pytest

from app.services.vector_store_service import VectorStoreService

pytestmark = pytest.mark.asyncio


DEFAULT_EMBEDDING_DIM = 1024


def _random_unit_vector(dim=DEFAULT_EMBEDDING_DIM):
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


class TestVectorStoreBatchAndQuery:

    async def test_add_papers_batch_basic(self, vector_store_service):
        total = 120
        ids = [f"batch_p{i:03d}" for i in range(total)]
        embeddings = [_random_unit_vector() for _ in range(total)]
        metadatas = [
            _make_metadata(f"batch_p{i:03d}", f"Batch Paper {i}", 2024, "ACL")
            for i in range(total)
        ]
        documents = [f"Abstract for batch paper {i}" for i in range(total)]

        await vector_store_service.add_papers_batch(
            ids, embeddings, metadatas, documents, batch_size=50
        )
        count = await vector_store_service.count()
        assert count == total

    async def test_add_papers_batch_invalid_lengths(self, vector_store_service):
        ids = ["p001", "p002", "p003"]
        embeddings = [_random_unit_vector() for _ in range(2)]
        metadatas = [
            _make_metadata("p001", "Paper 1", 2023, "ACL"),
            _make_metadata("p002", "Paper 2", 2024, "EMNLP"),
        ]
        documents = ["Abstract 1", "Abstract 2"]

        with pytest.raises(ValueError):
            await vector_store_service.add_papers_batch(
                ids, embeddings, metadatas, documents
            )

    async def test_add_papers_batch_invalid_dimension(self, vector_store_service):
        ids = ["p001"]
        embeddings = [[0.1] * 512]
        metadatas = [_make_metadata("p001", "Paper 1", 2023, "ACL")]
        documents = ["Abstract 1"]

        with pytest.raises(Exception):
            await vector_store_service.add_papers_batch(
                ids, embeddings, metadatas, documents
            )

    async def test_add_papers_batch_single_batch(self, vector_store_service):
        ids = ["sp001", "sp002"]
        embeddings = [_random_unit_vector() for _ in range(2)]
        metadatas = [
            _make_metadata("sp001", "Single Batch 1", 2024, "ACL"),
            _make_metadata("sp002", "Single Batch 2", 2024, "EMNLP"),
        ]
        documents = ["Abstract SB1", "Abstract SB2"]

        await vector_store_service.add_papers_batch(
            ids, embeddings, metadatas, documents, batch_size=50
        )
        count = await vector_store_service.count()
        assert count == 2

    async def test_get_paper_by_id_exists(self, vector_store_service):
        ids = ["gp001"]
        embeddings = [_random_unit_vector()]
        metadatas = [_make_metadata("gp001", "Get Paper Test", 2024, "ACL", 10)]
        documents = ["This is the abstract for get paper test."]

        await vector_store_service.add_papers(ids, embeddings, metadatas, documents)

        result = await vector_store_service.get_paper_by_id("gp001")
        assert result is not None
        assert result["paper_id"] == "gp001"
        assert result["title"] == "Get Paper Test"
        assert result["year"] == 2024
        assert result["venue"] == "ACL"
        assert result["citation_count"] == 10
        assert result["chunk_index"] == 0
        assert result["chunk_type"] == "title_abstract"
        assert result["document"] == "This is the abstract for get paper test."

    async def test_get_paper_by_id_not_exists(self, vector_store_service):
        result = await vector_store_service.get_paper_by_id("nonexistent_id")
        assert result is None

    async def test_update_paper_metadata_success(self, vector_store_service):
        ids = ["up001"]
        embeddings = [_random_unit_vector()]
        metadatas = [_make_metadata("up001", "Update Test", 2023, "ACL", 0)]
        documents = ["Abstract for update test."]

        await vector_store_service.add_papers(ids, embeddings, metadatas, documents)

        updated_metadata = _make_metadata("up001", "Update Test", 2023, "ACL", 42)
        await vector_store_service.update_paper_metadata("up001", updated_metadata)

        result = await vector_store_service.get_paper_by_id("up001")
        assert result is not None
        assert result["citation_count"] == 42

    async def test_update_paper_metadata_not_exists(self, vector_store_service):
        await vector_store_service.update_paper_metadata(
            "nonexistent_id", _make_metadata("nonexistent_id", "Ghost", 2024, "ACL")
        )
