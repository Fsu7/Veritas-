import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.validate_papers import (
    generate_validation_report,
    validate_metadata_integrity,
    validate_no_duplicates,
    validate_vector_dimensions,
)


class TestValidateVectorDimensions:

    def test_all_correct_dimensions(self):
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": ["id1", "id2"],
            "embeddings": [
                [0.1] * 1024,
                [0.2] * 1024,
            ],
        }

        result = validate_vector_dimensions(mock_collection)
        assert result["passed"] is True
        assert result["total"] == 2
        assert result["abnormal_count"] == 0

    def test_wrong_dimensions(self):
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": ["id1", "id2"],
            "embeddings": [
                [0.1] * 1024,
                [0.2] * 768,
            ],
        }

        result = validate_vector_dimensions(mock_collection)
        assert result["passed"] is False
        assert result["abnormal_count"] == 1
        assert "id2" in result["abnormal_ids"]

    def test_empty_collection(self):
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": [],
            "embeddings": [],
        }

        result = validate_vector_dimensions(mock_collection)
        assert result["passed"] is False
        assert result["total"] == 0


class TestValidateMetadataIntegrity:

    def test_complete_metadata(self):
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": ["id1"],
            "metadatas": [
                {"paper_id": "arxiv_001", "title": "Paper 1", "year": 2024},
            ],
        }

        result = validate_metadata_integrity(mock_collection)
        assert result["passed"] is True
        assert result["incomplete_count"] == 0

    def test_missing_required_fields(self):
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": ["id1", "id2"],
            "metadatas": [
                {"paper_id": "arxiv_001", "title": "Paper 1", "year": 2024},
                {"paper_id": "", "title": "Paper 2"},
            ],
        }

        result = validate_metadata_integrity(mock_collection)
        assert result["passed"] is False
        assert result["incomplete_count"] == 1
        assert len(result["incomplete_records"]) == 1

    def test_empty_collection(self):
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": [],
            "metadatas": [],
        }

        result = validate_metadata_integrity(mock_collection)
        assert result["passed"] is False


class TestValidateNoDuplicates:

    def test_no_duplicates(self):
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": ["id1", "id2"],
            "metadatas": [
                {"paper_id": "arxiv_001"},
                {"paper_id": "arxiv_002"},
            ],
        }

        result = validate_no_duplicates(mock_collection)
        assert result["passed"] is True
        assert result["duplicate_count"] == 0

    def test_with_duplicates(self):
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": ["id1", "id2", "id3"],
            "metadatas": [
                {"paper_id": "arxiv_001"},
                {"paper_id": "arxiv_001"},
                {"paper_id": "arxiv_002"},
            ],
        }

        result = validate_no_duplicates(mock_collection)
        assert result["passed"] is False
        assert result["duplicate_count"] == 1
        assert "arxiv_001" in result["duplicate_ids"]

    def test_empty_collection(self):
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": [],
            "metadatas": [],
        }

        result = validate_no_duplicates(mock_collection)
        assert result["passed"] is True


class TestGenerateValidationReport:

    def test_all_passed(self):
        report = generate_validation_report(
            total_papers=200,
            dimension_check={"passed": True, "total": 200, "abnormal_count": 0, "abnormal_ids": []},
            metadata_check={"passed": True, "total": 200, "incomplete_count": 0, "incomplete_records": []},
            duplicate_check={"passed": True, "total": 200, "duplicate_count": 0, "duplicate_ids": []},
        )
        assert report["passed"] is True
        assert report["total_papers"] == 200
        assert len(report["issues"]) == 0

    def test_some_failed(self):
        report = generate_validation_report(
            total_papers=200,
            dimension_check={"passed": True, "total": 200, "abnormal_count": 0, "abnormal_ids": []},
            metadata_check={"passed": False, "total": 200, "incomplete_count": 5, "incomplete_records": []},
            duplicate_check={"passed": True, "total": 200, "duplicate_count": 0, "duplicate_ids": []},
        )
        assert report["passed"] is False
        assert len(report["issues"]) == 1

    def test_with_search_quality(self):
        report = generate_validation_report(
            total_papers=200,
            dimension_check={"passed": True, "total": 200, "abnormal_count": 0, "abnormal_ids": []},
            metadata_check={"passed": True, "total": 200, "incomplete_count": 0, "incomplete_records": []},
            duplicate_check={"passed": True, "total": 200, "duplicate_count": 0, "duplicate_ids": []},
            search_quality_check={
                "passed": True,
                "query_results": [
                    {"query": "test", "top1_score": 0.8, "top10_count": 10, "passed": True}
                ],
            },
        )
        assert report["passed"] is True
        assert report["search_quality_check"]["passed"] is True
