from typing import Dict
from typing import List
from typing import Optional

import asyncio
import chromadb
from loguru import logger

from app.exception import VectorStoreException


class VectorStoreService:

    EXPECTED_DIMENSION = 1024

    def __init__(self, settings):
        self.settings = settings
        self.client = None
        self.collection = None
        self.status = "disconnected"

    async def initialize(self) -> None:
        try:
            self.client = chromadb.PersistentClient(
                path=self.settings.CHROMA_PATH or "./data/vector_db"
            )

            self.collection = self.client.get_or_create_collection(
                name="papers",
                metadata={
                    "hnsw:space": "cosine",
                    "hnsw:M": 16,
                    "hnsw:construction_ef": 200,
                },
            )

            count = self.collection.count()
            self.status = "connected"
            logger.info(f"ChromaDB initialized, papers count={count}")
        except Exception as e:
            self.status = "error"
            logger.error(f"ChromaDB initialization failed: {e}")
            raise VectorStoreException(f"ChromaDB initialization failed: {e}") from e

    async def add_papers(
        self,
        paper_ids: List[str],
        embeddings: List[List[float]],
        metadatas: List[dict],
        documents: List[str],
    ) -> None:
        if not (len(paper_ids) == len(embeddings) == len(metadatas) == len(documents)):
            raise ValueError(
                f"Parameter lengths mismatch: "
                f"ids={len(paper_ids)}, embeddings={len(embeddings)}, "
                f"metadatas={len(metadatas)}, documents={len(documents)}"
            )

        if embeddings:
            actual_dim = len(embeddings[0])
            if actual_dim != self.EXPECTED_DIMENSION:
                raise VectorStoreException(
                    f"Embedding dimension mismatch: got {actual_dim}, "
                    f"expected {self.EXPECTED_DIMENSION}. "
                    f"Ensure the embedding model outputs {self.EXPECTED_DIMENSION}-dim vectors."
                )

        self.collection.add(
            ids=paper_ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )
        logger.info(f"Added {len(paper_ids)} papers to ChromaDB")

    async def search(
        self,
        embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict] = None,
    ) -> List[dict]:
        where_filter = None
        if filters:
            conditions = []
            if filters.get("yearFrom"):
                conditions.append({"year": {"$gte": filters["yearFrom"]}})
            if filters.get("yearTo"):
                conditions.append({"year": {"$lte": filters["yearTo"]}})
            if filters.get("venue"):
                conditions.append({"venue": {"$eq": filters["venue"]}})
            if conditions:
                where_filter = (
                    {"$and": conditions} if len(conditions) > 1 else conditions[0]
                )

        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=where_filter,
            include=["metadatas", "distances", "documents"],
        )

        formatted = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                formatted.append(
                    {
                        "paperId": results["metadatas"][0][i].get("paper_id"),
                        "title": results["metadatas"][0][i].get("title"),
                        "abstract": results["documents"][0][i],
                        "score": 1 - results["distances"][0][i],
                        "year": results["metadatas"][0][i].get("year"),
                        "venue": results["metadatas"][0][i].get("venue"),
                        "citation_count": results["metadatas"][0][i].get("citation_count", 0),
                    }
                )

        return formatted

    async def delete_papers(self, paper_ids: List[str]) -> None:
        self.collection.delete(ids=paper_ids)
        logger.info(f"Deleted {len(paper_ids)} papers from ChromaDB")

    async def count(self) -> int:
        if self.collection is None:
            return 0
        return self.collection.count()

    async def close(self) -> None:
        self.client = None
        self.collection = None
        self.status = "disconnected"

    async def add_papers_batch(
        self,
        paper_ids: List[str],
        embeddings: List[List[float]],
        metadatas: List[dict],
        documents: List[str],
        batch_size: int = 50,
    ) -> None:
        if not (len(paper_ids) == len(embeddings) == len(metadatas) == len(documents)):
            raise ValueError(
                f"Parameter lengths mismatch: "
                f"ids={len(paper_ids)}, embeddings={len(embeddings)}, "
                f"metadatas={len(metadatas)}, documents={len(documents)}"
            )

        if embeddings:
            actual_dim = len(embeddings[0])
            if actual_dim != self.EXPECTED_DIMENSION:
                raise VectorStoreException(
                    f"Embedding dimension mismatch: got {actual_dim}, "
                    f"expected {self.EXPECTED_DIMENSION}. "
                    f"Ensure the embedding model outputs {self.EXPECTED_DIMENSION}-dim vectors."
                )

        total = len(paper_ids)
        total_batches = (total + batch_size - 1) // batch_size
        added_count = 0

        for i in range(0, total, batch_size):
            batch_end = min(i + batch_size, total)
            batch_ids = paper_ids[i:batch_end]
            batch_embeddings = embeddings[i:batch_end]
            batch_metadatas = metadatas[i:batch_end]
            batch_documents = documents[i:batch_end]

            self.collection.add(
                ids=batch_ids,
                embeddings=batch_embeddings,
                metadatas=batch_metadatas,
                documents=batch_documents,
            )
            added_count += len(batch_ids)
            batch_num = i // batch_size + 1
            logger.info(
                f"Batch {batch_num}/{total_batches} added, "
                f"{added_count} papers total"
            )

            if i + batch_size < total:
                await asyncio.sleep(0.5)

        logger.info(f"Batch import complete: {added_count} papers added in {total_batches} batches")

    async def get_paper_by_id(self, paper_id: str) -> Optional[dict]:
        try:
            results = self.collection.get(
                ids=[paper_id],
                include=["metadatas", "documents"],
            )
            if not results["ids"]:
                return None

            metadata = results["metadatas"][0] if results["metadatas"] else {}
            document = results["documents"][0] if results["documents"] else ""

            return {
                "paper_id": metadata.get("paper_id"),
                "title": metadata.get("title"),
                "year": metadata.get("year"),
                "venue": metadata.get("venue"),
                "citation_count": metadata.get("citation_count"),
                "chunk_index": metadata.get("chunk_index"),
                "chunk_type": metadata.get("chunk_type"),
                "document": document,
            }
        except Exception as e:
            logger.warning(f"Failed to get paper by id '{paper_id}': {e}")
            return None

    async def update_paper_metadata(
        self, paper_id: str, metadata: dict
    ) -> None:
        try:
            self.collection.update(
                ids=[paper_id],
                metadatas=[metadata],
            )
            logger.info(f"Updated metadata for paper '{paper_id}'")
        except Exception as e:
            logger.warning(
                f"Failed to update metadata for paper '{paper_id}': {e}"
            )

    async def search_by_keywords(
        self,
        query_text: str,
        top_k: int = 10,
        filters: Optional[Dict] = None,
    ) -> List[dict]:
        if self.collection is None:
            return []

        where_filter = None
        if filters:
            conditions = []
            if filters.get("yearFrom"):
                conditions.append({"year": {"$gte": filters["yearFrom"]}})
            if filters.get("yearTo"):
                conditions.append({"year": {"$lte": filters["yearTo"]}})
            if filters.get("venue"):
                conditions.append({"venue": {"$eq": filters["venue"]}})
            if conditions:
                where_filter = (
                    {"$and": conditions} if len(conditions) > 1 else conditions[0]
                )

        keywords = [kw.strip() for kw in query_text.split() if kw.strip()]
        if not keywords:
            return []

        seen_ids = set()
        all_results = {}

        for keyword in keywords:
            try:
                where_doc = {"$contains": keyword}
                combined_where = where_filter
                if where_filter:
                    combined_where = {"$and": [where_filter, where_doc]}
                else:
                    combined_where = where_doc

                results = self.collection.query(
                    query_texts=[keyword],
                    n_results=top_k,
                    where=combined_where,
                    include=["metadatas", "distances", "documents"],
                )

                if results["ids"] and results["ids"][0]:
                    for i in range(len(results["ids"][0])):
                        pid = results["metadatas"][0][i].get("paper_id", "")
                        if pid and pid not in seen_ids:
                            seen_ids.add(pid)
                            all_results[pid] = {
                                "paperId": pid,
                                "title": results["metadatas"][0][i].get("title"),
                                "abstract": results["documents"][0][i],
                                "score": 1 - results["distances"][0][i],
                                "year": results["metadatas"][0][i].get("year"),
                                "venue": results["metadatas"][0][i].get("venue"),
                                "citation_count": results["metadatas"][0][i].get("citation_count", 0),
                            }
            except Exception as e:
                logger.warning(f"Keyword search failed for '{keyword}': {e}")
                continue

        result_list = list(all_results.values())
        result_list.sort(key=lambda x: x.get("score", 0), reverse=True)
        return result_list[:top_k]

    async def suggest_titles(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[str]:
        if self.collection is None:
            return []

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k * 3,
                include=["metadatas"],
            )

            titles = []
            seen = set()
            if results["ids"] and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    title = results["metadatas"][0][i].get("title", "")
                    if title and title not in seen:
                        seen.add(title)
                        titles.append(title)
                        if len(titles) >= top_k:
                            break

            return titles
        except Exception as e:
            logger.warning(f"Title suggestion failed for '{query}': {e}")
            return []
