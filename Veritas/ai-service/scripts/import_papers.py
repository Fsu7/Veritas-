import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

import arxiv
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import Settings
from app.services.embedding_service import EmbeddingService
from app.services.vector_store_service import VectorStoreService
from app.utils.text_processing import chunk_text, clean_text


MAX_RETRIES = 3
RETRY_INTERVAL = 5


async def fetch_papers_from_arxiv(
    category: str, count: int, year_start: int | None = None
) -> list:
    papers = []
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            client = arxiv.Client()
            search = arxiv.Search(
                query=f"cat:{category}",
                max_results=count,
                sort_by=arxiv.SortCriterion.SubmittedDate,
            )

            for result in client.results(search):
                if year_start is not None and result.published.year < year_start:
                    continue

                entry_id = result.entry_id.split("/")[-1]
                entry_id = entry_id.split("v")[0]

                papers.append(
                    {
                        "paper_id": f"arxiv_{entry_id}",
                        "title": result.title,
                        "authors": [a.name for a in result.authors],
                        "abstract": result.summary.replace("\n", " "),
                        "year": result.published.year,
                        "venue": result.primary_category,
                        "keywords": result.categories,
                        "pdf_url": result.pdf_url,
                    }
                )

            logger.info(
                f"Fetched {len(papers)} papers from arXiv "
                f"(category={category}, count={count})"
            )
            return papers

        except Exception as e:
            logger.warning(
                f"arXiv API attempt {attempt}/{MAX_RETRIES} failed: {e}"
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_INTERVAL)
            else:
                logger.error(
                    f"arXiv API failed after {MAX_RETRIES} retries"
                )
                raise

    return papers


def fetch_papers_from_json(data_dir: str) -> list:
    papers = []
    data_path = Path(data_dir)

    if not data_path.exists():
        logger.warning(f"Data directory not found: {data_dir}")
        return papers

    for json_file in data_path.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                papers.extend(data)
            elif isinstance(data, dict) and "papers" in data:
                papers.extend(data["papers"])
            else:
                papers.append(data)

            logger.info(f"Loaded papers from {json_file.name}")
        except Exception as e:
            logger.warning(f"Failed to load {json_file.name}: {e}")

    logger.info(f"Loaded {len(papers)} papers from JSON files in {data_dir}")
    return papers


def clean_papers(papers: list) -> list:
    seen_titles = set()
    cleaned = []

    for p in papers:
        title = p.get("title", "").strip()
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)

        paper_id = p.get("paper_id", "")
        if paper_id.startswith("arxiv_"):
            raw_id = paper_id.replace("arxiv_", "", 1)
            raw_id = raw_id.split("v")[0]
            paper_id = f"arxiv_{raw_id}"

        abstract = p.get("abstract", "")
        import re
        abstract = re.sub(r"\s+", " ", abstract).strip()

        cleaned.append(
            {
                "paper_id": paper_id,
                "title": title,
                "authors": p.get("authors", []),
                "abstract": abstract,
                "year": p.get("year"),
                "venue": p.get("venue", ""),
                "keywords": p.get("keywords", []),
                "pdf_url": p.get("pdf_url", ""),
            }
        )

    logger.info(
        f"Cleaned papers: {len(papers)} -> {len(cleaned)} "
        f"(removed {len(papers) - len(cleaned)} duplicates)"
    )
    return cleaned


async def import_to_vector_db(
    papers: list,
    embedding_service: EmbeddingService,
    vector_store_service: VectorStoreService,
    batch_size: int = 50,
) -> dict:
    total = len(papers)
    success = 0
    failed = 0
    errors = []

    all_ids = []
    all_embeddings = []
    all_metadatas = []
    all_documents = []

    for i, paper in enumerate(papers):
        try:
            title = paper.get("title", "")
            abstract = paper.get("abstract", "")
            document = clean_text(f"{title}. {abstract}")

            if len(document) > 800:
                chunks = chunk_text(document, chunk_size=800, overlap=100)
            else:
                chunks = [
                    {
                        "chunk_index": 0,
                        "chunk_type": "title_abstract",
                        "content": document,
                    }
                ]

            chunk_texts = [c["content"] for c in chunks]
            embeddings = await embedding_service.encode_batch(chunk_texts)

            if embeddings.ndim == 1:
                embeddings = embeddings.reshape(1, -1)

            for j, chunk in enumerate(chunks):
                chunk_id = f"{paper['paper_id']}_chunk_{chunk['chunk_index']}"
                all_ids.append(chunk_id)
                all_embeddings.append(embeddings[j].tolist())
                all_metadatas.append(
                    {
                        "paper_id": paper["paper_id"],
                        "title": title,
                        "year": paper.get("year"),
                        "venue": paper.get("venue", ""),
                        "citation_count": 0,
                        "chunk_index": chunk["chunk_index"],
                        "chunk_type": chunk["chunk_type"],
                    }
                )
                all_documents.append(chunk["content"])

            success += 1
            logger.info(
                f"[{success + failed}/{total}] Processed {paper['paper_id']}: "
                f"{title[:60]} ({len(chunks)} chunks)"
            )

        except Exception as e:
            failed += 1
            errors.append(
                {"paper_id": paper.get("paper_id", "unknown"), "error": str(e)}
            )
            logger.warning(
                f"Failed to process paper {paper.get('paper_id', 'unknown')}: {e}"
            )

    if all_ids:
        await vector_store_service.add_papers_batch(
            paper_ids=all_ids,
            embeddings=all_embeddings,
            metadatas=all_metadatas,
            documents=all_documents,
            batch_size=batch_size,
        )

    result = {
        "total": total,
        "success": success,
        "failed": failed,
        "errors": errors,
    }
    logger.info(
        f"Import complete: total={total}, success={success}, failed={failed}"
    )
    return result


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import papers into ChromaDB vector store"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=200,
        help="Number of papers to download (default: 200)",
    )
    parser.add_argument(
        "--category",
        type=str,
        default="cs.AI",
        help="arXiv category (default: cs.AI)",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="arxiv",
        choices=["arxiv", "json"],
        help="Data source: arxiv or json (default: arxiv)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only fetch and clean, do not import to vector DB",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for vector DB import (default: 50)",
    )
    parser.add_argument(
        "--year-start",
        type=int,
        default=None,
        help="Only include papers published on/after this year (e.g. 2025)",
    )
    args = parser.parse_args()

    settings = Settings()

    if args.source == "arxiv":
        logger.info(
            f"Fetching {args.count} papers from arXiv (category={args.category}, "
            f"year_start={args.year_start})"
        )
        papers = await fetch_papers_from_arxiv(
            args.category, args.count, args.year_start
        )
    else:
        data_dir = os.environ.get("PAPERS_DATA_DIR", "./data/papers/")
        logger.info(f"Loading papers from JSON (dir={data_dir})")
        papers = fetch_papers_from_json(data_dir)

    cleaned = clean_papers(papers)

    if args.dry_run:
        logger.info(f"[DRY-RUN] Fetched {len(papers)} papers")
        logger.info(f"[DRY-RUN] After cleaning: {len(cleaned)} papers")

        estimated_chunks = 0
        for p in cleaned:
            doc = f"{p['title']}. {p['abstract']}"
            if len(doc) > 800:
                estimated_chunks += len(chunk_text(doc, chunk_size=800, overlap=100))
            else:
                estimated_chunks += 1

        logger.info(f"[DRY-RUN] Estimated chunks: {estimated_chunks}")

        for i, p in enumerate(cleaned[:3]):
            logger.info(
                f"[DRY-RUN] Sample {i + 1}: "
                f"paper_id={p['paper_id']}, title={p['title'][:80]}"
            )

        return

    embedding_service = EmbeddingService(settings)
    await embedding_service.load_model()

    vector_store_service = VectorStoreService(settings)
    await vector_store_service.initialize()

    result = await import_to_vector_db(
        cleaned, embedding_service, vector_store_service, args.batch_size
    )

    logger.info(f"Import result: {json.dumps(result, ensure_ascii=False)}")

    await vector_store_service.close()


if __name__ == "__main__":
    asyncio.run(main())
