import argparse
import asyncio
import json
import sys
from pathlib import Path

import chromadb
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import Settings
from scripts.import_papers import (
    clean_papers,
    fetch_papers_from_arxiv,
    fetch_papers_from_json,
    import_to_vector_db,
)
from app.services.embedding_service import EmbeddingService
from app.services.vector_store_service import VectorStoreService


async def rebuild_vector_db(
    count: int,
    category: str,
    chroma_path: str,
    dry_run: bool = False,
    batch_size: int = 50,
) -> None:
    if dry_run:
        logger.info(
            f"[DRY-RUN] Would rebuild vector DB: "
            f"delete collection 'papers', create new with HNSW(cosine/M=16/ef=200), "
            f"import {count} papers from arXiv category={category}"
        )
        return

    client = chromadb.PersistentClient(path=chroma_path)

    try:
        client.delete_collection("papers")
        logger.info("Deleted existing papers collection")
    except Exception:
        logger.info("No existing papers collection to delete")

    collection = client.get_or_create_collection(
        name="papers",
        metadata={
            "hnsw:space": "cosine",
            "hnsw:M": 16,
            "hnsw:construction_ef": 200,
        },
    )
    logger.info("Created new papers collection with HNSW(cosine/M=16/ef=200)")

    settings = Settings(CHROMA_PATH=chroma_path)

    papers = await fetch_papers_from_arxiv(category, count)
    cleaned = clean_papers(papers)

    if not cleaned:
        logger.warning("No papers to import after cleaning")
        return

    embedding_service = EmbeddingService(settings)
    await embedding_service.load_model()

    vector_store_service = VectorStoreService(settings)
    vector_store_service.client = client
    vector_store_service.collection = collection
    vector_store_service.status = "connected"

    result = await import_to_vector_db(
        cleaned, embedding_service, vector_store_service, batch_size
    )

    logger.info(f"Rebuild complete: {json.dumps(result, ensure_ascii=False)}")
    logger.info(f"Collection count: {collection.count()}")


async def incremental_update(
    count: int,
    category: str,
    chroma_path: str,
    dry_run: bool = False,
    batch_size: int = 50,
) -> None:
    client = chromadb.PersistentClient(path=chroma_path)

    try:
        collection = client.get_collection("papers")
    except Exception as e:
        logger.error(f"Papers collection not found: {e}")
        logger.info("Run rebuild mode first to create the collection")
        return

    existing_ids = set()
    offset = 0
    batch_limit = 100

    while True:
        results = collection.get(
            include=["metadatas"],
            limit=batch_limit,
            offset=offset,
        )
        if not results["ids"]:
            break

        for meta in results["metadatas"]:
            pid = meta.get("paper_id")
            if pid:
                existing_ids.add(pid)

        if len(results["ids"]) < batch_limit:
            break
        offset += batch_limit

    logger.info(f"Found {len(existing_ids)} existing paper_ids in collection")

    papers = await fetch_papers_from_arxiv(category, count)
    cleaned = clean_papers(papers)

    new_papers = [p for p in cleaned if p["paper_id"] not in existing_ids]
    logger.info(
        f"Fetched {len(cleaned)} papers, "
        f"{len(new_papers)} are new (not in existing {len(existing_ids)})"
    )

    if not new_papers:
        logger.info("No new papers to import")
        return

    if dry_run:
        logger.info(
            f"[DRY-RUN] Would import {len(new_papers)} new papers"
        )
        for i, p in enumerate(new_papers[:3]):
            logger.info(
                f"[DRY-RUN] New paper {i + 1}: "
                f"paper_id={p['paper_id']}, title={p['title'][:80]}"
            )
        return

    settings = Settings(CHROMA_PATH=chroma_path)

    embedding_service = EmbeddingService(settings)
    await embedding_service.load_model()

    vector_store_service = VectorStoreService(settings)
    vector_store_service.client = client
    vector_store_service.collection = collection
    vector_store_service.status = "connected"

    result = await import_to_vector_db(
        new_papers, embedding_service, vector_store_service, batch_size
    )

    logger.info(
        f"Incremental update complete: {json.dumps(result, ensure_ascii=False)}"
    )
    logger.info(f"Collection count: {collection.count()}")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build or update ChromaDB vector database"
    )
    parser.add_argument(
        "--mode",
        type=str,
        required=True,
        choices=["rebuild", "incremental"],
        help="Build mode: rebuild (full) or incremental",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=200,
        help="Number of papers to import (default: 200)",
    )
    parser.add_argument(
        "--category",
        type=str,
        default="cs.AI",
        help="arXiv category (default: cs.AI)",
    )
    parser.add_argument(
        "--chroma-path",
        type=str,
        default="./data/vector_db",
        help="ChromaDB path (default: ./data/vector_db)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode - show what would be done",
    )
    args = parser.parse_args()

    if args.mode == "rebuild":
        await rebuild_vector_db(
            count=args.count,
            category=args.category,
            chroma_path=args.chroma_path,
            dry_run=args.dry_run,
        )
    elif args.mode == "incremental":
        await incremental_update(
            count=args.count,
            category=args.category,
            chroma_path=args.chroma_path,
            dry_run=args.dry_run,
        )


if __name__ == "__main__":
    asyncio.run(main())
