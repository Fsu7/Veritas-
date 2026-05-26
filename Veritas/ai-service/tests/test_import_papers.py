import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.import_papers import (
    clean_papers,
    fetch_papers_from_json,
    import_to_vector_db,
)


def _make_paper(paper_id, title, abstract="Test abstract", year=2024):
    return {
        "paper_id": paper_id,
        "title": title,
        "authors": ["Author A"],
        "abstract": abstract,
        "year": year,
        "venue": "ACL",
        "keywords": ["cs.AI"],
        "pdf_url": "https://arxiv.org/pdf/test",
    }


class TestFetchPapersFromArxiv:

    @pytest.mark.asyncio
    async def test_fetch_success(self):
        mock_result = MagicMock()
        mock_result.entry_id = "http://arxiv.org/abs/2401.0001v1"
        mock_result.title = "Test Paper"
        mock_result.authors = [MagicMock(name="Author")]
        mock_result.authors[0].name = "Author A"
        mock_result.summary = "Test abstract"
        mock_result.published = MagicMock()
        mock_result.published.year = 2024
        mock_result.primary_category = "cs.AI"
        mock_result.categories = ["cs.AI"]
        mock_result.pdf_url = "https://arxiv.org/pdf/2401.0001"

        with patch("scripts.import_papers.arxiv.Client") as MockClient:
            mock_client = MockClient.return_value
            mock_client.results.return_value = [mock_result]

            from scripts.import_papers import fetch_papers_from_arxiv

            papers = await fetch_papers_from_arxiv("cs.AI", 1)
            assert len(papers) == 1
            assert papers[0]["paper_id"] == "arxiv_2401.0001"
            assert papers[0]["title"] == "Test Paper"


class TestFetchPapersFromJson:

    def test_load_json_list(self, tmp_path):
        papers = [
            _make_paper("arxiv_001", "Paper 1"),
            _make_paper("arxiv_002", "Paper 2"),
        ]
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(papers), encoding="utf-8")

        result = fetch_papers_from_json(str(tmp_path))
        assert len(result) == 2

    def test_load_json_with_papers_key(self, tmp_path):
        data = {"papers": [_make_paper("arxiv_001", "Paper 1")]}
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(data), encoding="utf-8")

        result = fetch_papers_from_json(str(tmp_path))
        assert len(result) == 1

    def test_empty_directory(self, tmp_path):
        result = fetch_papers_from_json(str(tmp_path))
        assert result == []

    def test_nonexistent_directory(self):
        result = fetch_papers_from_json("/nonexistent/path")
        assert result == []


class TestCleanPapers:

    def test_dedup_by_title(self):
        papers = [
            _make_paper("arxiv_001", "Same Title"),
            _make_paper("arxiv_002", "Same Title"),
            _make_paper("arxiv_003", "Different Title"),
        ]
        result = clean_papers(papers)
        assert len(result) == 2
        assert result[0]["title"] == "Same Title"
        assert result[1]["title"] == "Different Title"

    def test_paper_id_format(self):
        papers = [
            _make_paper("arxiv_2401.0001v2", "Paper 1"),
        ]
        result = clean_papers(papers)
        assert result[0]["paper_id"] == "arxiv_2401.0001"

    def test_strip_whitespace(self):
        papers = [
            _make_paper("arxiv_001", "  Title with spaces  ", "  Abstract  "),
        ]
        result = clean_papers(papers)
        assert result[0]["title"] == "Title with spaces"

    def test_abstract_whitespace_normalization(self):
        papers = [
            _make_paper("arxiv_001", "Paper", "Abstract   with   spaces"),
        ]
        result = clean_papers(papers)
        assert "  " not in result[0]["abstract"]

    def test_empty_title_removed(self):
        papers = [
            _make_paper("arxiv_001", ""),
            _make_paper("arxiv_002", "Valid Title"),
        ]
        result = clean_papers(papers)
        assert len(result) == 1


class TestImportToVectorDb:

    @pytest.mark.asyncio
    async def test_basic_import(self):
        papers = [
            _make_paper("arxiv_001", "Paper 1", "Short abstract"),
            _make_paper("arxiv_002", "Paper 2", "Short abstract"),
        ]

        mock_embedding = AsyncMock()
        dim = 1024
        mock_embedding.encode_batch = AsyncMock(
            return_value=np.random.randn(1, dim).astype(np.float32)
        )
        mock_embedding.status = "loaded_api"

        mock_vss = AsyncMock()
        mock_vss.add_papers_batch = AsyncMock()

        result = await import_to_vector_db(papers, mock_embedding, mock_vss)

        assert result["total"] == 2
        assert result["success"] == 2
        assert result["failed"] == 0
        assert mock_vss.add_papers_batch.called

    @pytest.mark.asyncio
    async def test_single_failure_not_blocking(self):
        papers = [
            _make_paper("arxiv_001", "Paper 1", "Short abstract"),
            _make_paper("arxiv_002", "Paper 2", "Short abstract"),
            _make_paper("arxiv_003", "Paper 3", "Short abstract"),
        ]

        dim = 1024
        call_count = 0

        async def mock_encode_batch(texts, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("Embedding failed for paper 2")
            return np.random.randn(len(texts), dim).astype(np.float32)

        mock_embedding = AsyncMock()
        mock_embedding.encode_batch = mock_encode_batch

        mock_vss = AsyncMock()
        mock_vss.add_papers_batch = AsyncMock()

        result = await import_to_vector_db(papers, mock_embedding, mock_vss)

        assert result["total"] == 3
        assert result["failed"] >= 1
