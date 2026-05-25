from typing import Dict
from typing import List
from typing import Optional

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
