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
        loop = asyncio.get_event_loop()
        try:
            self.client = await loop.run_in_executor(
                None,
                lambda: chromadb.PersistentClient(
                    path=self.settings.CHROMA_PATH or "./data/vector_db"
                ),
            )

            self.collection = await loop.run_in_executor(
                None,
                lambda: self.client.get_or_create_collection(
                    name="papers",
                    metadata={
                        "hnsw:space": "cosine",
                        "hnsw:M": 16,
                        "hnsw:construction_ef": 200,
                    },
                ),
            )

            count = await loop.run_in_executor(None, self.collection.count)
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
        similarity_threshold: float = 0.0,
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
                distance = results["distances"][0][i]
                # task54: similarity_threshold 过滤
                # ChromaDB distance 越小越相似；similarity = 1 - distance
                # similarity_threshold > 0 时，过滤 similarity < threshold 的结果
                if similarity_threshold > 0.0 and (1.0 - distance) < similarity_threshold:
                    continue
                formatted.append(
                    {
                        "paperId": results["metadatas"][0][i].get("paper_id"),
                        "title": results["metadatas"][0][i].get("title"),
                        "abstract": results["documents"][0][i],
                        "score": 1 - distance,
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
        tokens: Optional[List[str]] = None,
        phrases: Optional[List[str]] = None,
    ) -> List[dict]:
        """关键词检索：支持多 token OR 查询和短语精确匹配。

        Args:
            query_text: 原始查询文本（向后兼容）
            top_k: 返回结果数
            filters: 元数据过滤条件
            tokens: 分词后的 token 列表（OR 查询）
            phrases: 短语列表（AND 精确匹配）
        """
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

        # 构建查询关键词列表：优先使用传入的 tokens + phrases，否则回退到原 split 逻辑
        if tokens is None and phrases is None:
            # 向后兼容：原逻辑按空格分词
            keywords = [kw.strip() for kw in query_text.split() if kw.strip()]
            if not keywords:
                return []
            use_or_query = False
        else:
            keywords = list(tokens or [])
            phrases = list(phrases or [])
            use_or_query = True
            if not keywords and not phrases:
                return []

        # 命中计数：多 token 命中时累加分数（修复原 seen_ids 先到先得问题）
        hit_counts: Dict[str, int] = {}
        all_results: Dict[str, dict] = {}

        if use_or_query:
            # 新逻辑：构建 where_document 组合查询
            # phrases 非空：每个 phrase 用 $contains 构建 AND 条件
            # tokens 非空：用 $or 构建 OR 条件
            # 同时存在：用 $and 组合
            where_doc_conditions = []

            if phrases:
                for phrase in phrases:
                    where_doc_conditions.append({"$contains": phrase})

            if keywords:
                if len(keywords) == 1:
                    where_doc_conditions.append({"$contains": keywords[0]})
                else:
                    where_doc_conditions.append(
                        {"$or": [{"$contains": kw} for kw in keywords]}
                    )

            # 构建 where_document
            if len(where_doc_conditions) == 0:
                return []
            elif len(where_doc_conditions) == 1:
                where_doc = where_doc_conditions[0]
            else:
                where_doc = {"$and": where_doc_conditions}

            # 执行单次组合查询
            combined_where = where_filter
            if where_filter:
                combined_where = {"$and": [where_filter, where_doc]}
            else:
                combined_where = where_doc

            try:
                results = self.collection.query(
                    query_texts=[query_text or (keywords[0] if keywords else "")],
                    n_results=top_k * 2,  # 多取一些用于后续排序
                    where=combined_where,
                    include=["metadatas", "distances", "documents"],
                )

                if results["ids"] and results["ids"][0]:
                    for i in range(len(results["ids"][0])):
                        pid = results["metadatas"][0][i].get("paper_id", "")
                        if pid:
                            doc_text = (results["documents"][0][i] or "").lower()
                            # 统计命中 token 数
                            hit_count = 0
                            for kw in keywords:
                                if kw.lower() in doc_text:
                                    hit_count += 1
                            for phrase in phrases:
                                if phrase.lower() in doc_text:
                                    hit_count += 2  # phrase 命中权重更高

                            hit_counts[pid] = hit_count
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
                logger.warning(f"Keyword search (OR query) failed: {e}")
                return []

            # 按命中数加权排序：命中越多分越高，相同命中数按 score 排序
            result_list = list(all_results.values())
            for item in result_list:
                pid = item["paperId"]
                # 命中数加权：每命中一个 token 加 0.1 分
                item["score"] = item.get("score", 0.0) + hit_counts.get(pid, 0) * 0.1
            result_list.sort(
                key=lambda x: (hit_counts.get(x["paperId"], 0), x.get("score", 0)),
                reverse=True,
            )
            return result_list[:top_k]

        else:
            # 原逻辑：逐关键词查询，去重合并
            seen_ids = set()
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
