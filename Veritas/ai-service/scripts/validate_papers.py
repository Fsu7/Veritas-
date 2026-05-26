import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

import chromadb
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import Settings
from app.services.embedding_service import EmbeddingService
from app.services.vector_store_service import VectorStoreService


CHROMA_GET_BATCH_SIZE = 100

TEST_QUERIES = [
    {"query": "Multi-Agent协同决策", "min_top1_score": 0.5},
    {"query": "大语言模型", "min_top1_score": 0.5},
    {"query": "检索增强生成", "min_top1_score": 0.5},
]


def validate_vector_dimensions(collection) -> dict:
    abnormal_ids = []
    total = 0

    try:
        offset = 0
        while True:
            results = collection.get(
                include=["embeddings"],
                limit=CHROMA_GET_BATCH_SIZE,
                offset=offset,
            )
            if not results["ids"]:
                break

            for i, emb in enumerate(results["embeddings"]):
                total += 1
                if emb is not None and len(emb) != 1024:
                    abnormal_ids.append(results["ids"][i])

            if len(results["ids"]) < CHROMA_GET_BATCH_SIZE:
                break
            offset += CHROMA_GET_BATCH_SIZE

    except Exception as e:
        logger.error(f"validate_vector_dimensions failed: {e}")
        return {
            "passed": False,
            "total": total,
            "abnormal_count": len(abnormal_ids),
            "abnormal_ids": abnormal_ids,
            "error": str(e),
        }

    passed = len(abnormal_ids) == 0 and total > 0
    return {
        "passed": passed,
        "total": total,
        "abnormal_count": len(abnormal_ids),
        "abnormal_ids": abnormal_ids,
    }


def validate_metadata_integrity(collection) -> dict:
    incomplete_records = []
    total = 0
    required_fields = ["paper_id", "title", "year"]

    try:
        offset = 0
        while True:
            results = collection.get(
                include=["metadatas"],
                limit=CHROMA_GET_BATCH_SIZE,
                offset=offset,
            )
            if not results["ids"]:
                break

            for i, meta in enumerate(results["metadatas"]):
                total += 1
                missing = []
                for field in required_fields:
                    val = meta.get(field)
                    if val is None or (isinstance(val, str) and not val.strip()):
                        missing.append(field)

                if missing:
                    incomplete_records.append(
                        {
                            "paper_id": meta.get("paper_id", results["ids"][i]),
                            "missing_fields": missing,
                        }
                    )

            if len(results["ids"]) < CHROMA_GET_BATCH_SIZE:
                break
            offset += CHROMA_GET_BATCH_SIZE

    except Exception as e:
        logger.error(f"validate_metadata_integrity failed: {e}")
        return {
            "passed": False,
            "total": total,
            "incomplete_count": len(incomplete_records),
            "incomplete_records": incomplete_records,
            "error": str(e),
        }

    passed = len(incomplete_records) == 0 and total > 0
    return {
        "passed": passed,
        "total": total,
        "incomplete_count": len(incomplete_records),
        "incomplete_records": incomplete_records,
    }


def validate_no_duplicates(collection) -> dict:
    paper_ids = []

    try:
        offset = 0
        while True:
            results = collection.get(
                include=["metadatas"],
                limit=CHROMA_GET_BATCH_SIZE,
                offset=offset,
            )
            if not results["ids"]:
                break

            for meta in results["metadatas"]:
                pid = meta.get("paper_id")
                if pid:
                    paper_ids.append(pid)

            if len(results["ids"]) < CHROMA_GET_BATCH_SIZE:
                break
            offset += CHROMA_GET_BATCH_SIZE

    except Exception as e:
        logger.error(f"validate_no_duplicates failed: {e}")
        return {
            "passed": False,
            "total": len(paper_ids),
            "duplicate_count": 0,
            "duplicate_ids": [],
            "error": str(e),
        }

    from collections import Counter

    counts = Counter(paper_ids)
    duplicates = {pid: cnt for pid, cnt in counts.items() if cnt > 1}

    passed = len(duplicates) == 0
    return {
        "passed": passed,
        "total": len(paper_ids),
        "duplicate_count": len(duplicates),
        "duplicate_ids": list(duplicates.keys()),
    }


async def validate_search_quality(
    embedding_service: EmbeddingService,
    vector_store_service: VectorStoreService,
    test_queries: Optional[list] = None,
) -> dict:
    if test_queries is None:
        test_queries = TEST_QUERIES

    query_results = []

    for tq in test_queries:
        query = tq["query"]
        min_score = tq.get("min_top1_score", 0.5)

        try:
            query_embedding = await embedding_service.encode(query)
            if query_embedding.ndim == 1:
                query_embedding = query_embedding.tolist()
            else:
                query_embedding = query_embedding[0].tolist()

            results = await vector_store_service.search(
                embedding=query_embedding, top_k=10
            )

            top1_score = results[0]["score"] if results else 0.0
            top10_count = len(results)
            query_passed = top1_score >= min_score and top10_count > 0

            query_results.append(
                {
                    "query": query,
                    "top1_score": round(top1_score, 4),
                    "top10_count": top10_count,
                    "passed": query_passed,
                }
            )

        except Exception as e:
            logger.warning(f"Search quality test failed for '{query}': {e}")
            query_results.append(
                {
                    "query": query,
                    "top1_score": 0.0,
                    "top10_count": 0,
                    "passed": False,
                    "error": str(e),
                }
            )

    passed = all(qr["passed"] for qr in query_results)
    return {
        "passed": passed,
        "query_results": query_results,
    }


def generate_validation_report(
    total_papers: int,
    dimension_check: dict,
    metadata_check: dict,
    duplicate_check: dict,
    search_quality_check: Optional[dict] = None,
) -> dict:
    issues = []

    if not dimension_check.get("passed", True):
        issues.append(
            f"Vector dimension check failed: "
            f"{dimension_check.get('abnormal_count', 0)} vectors with wrong dimension"
        )

    if not metadata_check.get("passed", True):
        issues.append(
            f"Metadata integrity check failed: "
            f"{metadata_check.get('incomplete_count', 0)} records with missing fields"
        )

    if not duplicate_check.get("passed", True):
        issues.append(
            f"Duplicate check failed: "
            f"{duplicate_check.get('duplicate_count', 0)} duplicate paper_ids"
        )

    if search_quality_check and not search_quality_check.get("passed", True):
        issues.append("Search quality check failed: some queries below threshold")

    all_passed = len(issues) == 0

    report = {
        "total_papers": total_papers,
        "dimension_check": dimension_check,
        "metadata_check": metadata_check,
        "duplicate_check": duplicate_check,
        "search_quality_check": search_quality_check,
        "passed": all_passed,
        "issues": issues,
    }

    return report


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate papers data in ChromaDB"
    )
    parser.add_argument(
        "--chroma-path",
        type=str,
        default="./data/vector_db",
        help="ChromaDB path (default: ./data/vector_db)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-fix issues where possible",
    )
    args = parser.parse_args()

    settings = Settings(CHROMA_PATH=args.chroma_path)

    client = chromadb.PersistentClient(path=args.chroma_path)

    try:
        collection = client.get_collection("papers")
    except Exception as e:
        logger.error(f"Failed to get papers collection: {e}")
        report = generate_validation_report(
            total_papers=0,
            dimension_check={"passed": False, "error": str(e)},
            metadata_check={"passed": False, "error": str(e)},
            duplicate_check={"passed": False, "error": str(e)},
        )
        print(json.dumps(report, indent=2, ensure_ascii=False))
        sys.exit(1)

    total_papers = collection.count()
    if args.verbose:
        logger.info(f"Total papers in collection: {total_papers}")

    dimension_check = validate_vector_dimensions(collection)
    if args.verbose:
        logger.info(f"Dimension check: passed={dimension_check['passed']}")

    metadata_check = validate_metadata_integrity(collection)
    if args.verbose:
        logger.info(f"Metadata check: passed={metadata_check['passed']}")

    duplicate_check = validate_no_duplicates(collection)
    if args.verbose:
        logger.info(f"Duplicate check: passed={duplicate_check['passed']}")

    search_quality_check = None
    if total_papers > 0:
        try:
            embedding_service = EmbeddingService(settings)
            await embedding_service.load_model()

            vector_store_service = VectorStoreService(settings)
            await vector_store_service.initialize()

            search_quality_check = await validate_search_quality(
                embedding_service, vector_store_service
            )
            if args.verbose:
                logger.info(
                    f"Search quality check: passed={search_quality_check['passed']}"
                )

            await vector_store_service.close()
        except Exception as e:
            logger.warning(f"Search quality check skipped: {e}")
            search_quality_check = {
                "passed": False,
                "error": str(e),
                "query_results": [],
            }

    report = generate_validation_report(
        total_papers=total_papers,
        dimension_check=dimension_check,
        metadata_check=metadata_check,
        duplicate_check=duplicate_check,
        search_quality_check=search_quality_check,
    )

    report_json = json.dumps(report, indent=2, ensure_ascii=False)
    print(report_json)

    report_path = Path("validation_report.json")
    report_path.write_text(report_json, encoding="utf-8")
    logger.info(f"Validation report saved to {report_path}")

    if not report["passed"]:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
