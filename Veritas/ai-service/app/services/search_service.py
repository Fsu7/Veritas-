import asyncio
import time
from typing import Dict
from typing import List
from typing import Optional

from loguru import logger


class SearchService:

    RRF_K = 60

    def __init__(
        self,
        vector_store_service,
        embedding_service,
        reranker=None,
    ):
        self.vector_store_service = vector_store_service
        self.embedding_service = embedding_service
        self.reranker = reranker

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict] = None,
    ) -> List[dict]:
        start_time = time.perf_counter()
        try:
            query_embedding = await self.embedding_service.encode(query)
            raw_results = await self.vector_store_service.search(
                embedding=query_embedding.tolist(),
                top_k=top_k,
                filters=filters,
            )

            results = self._format_results(raw_results)

            if self.reranker is not None:
                try:
                    results = await self.reranker.rerank(query, results)
                except Exception as e:
                    logger.warning(f"Reranker failed in search, returning original results: {e}")

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"Semantic search completed: query='{query[:50]}', top_k={top_k}, "
                f"results={len(results)}, elapsed={elapsed_ms:.1f}ms"
            )
            return results

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(
                f"Semantic search failed: query='{query[:50]}', top_k={top_k}, "
                f"elapsed={elapsed_ms:.1f}ms, error={e}"
            )
            return []

    async def keyword_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict] = None,
    ) -> List[dict]:
        start_time = time.perf_counter()
        try:
            raw_results = await self.vector_store_service.search_by_keywords(
                query_text=query,
                top_k=top_k,
                filters=filters,
            )

            results = self._format_results(raw_results)

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"Keyword search completed: query='{query[:50]}', top_k={top_k}, "
                f"results={len(results)}, elapsed={elapsed_ms:.1f}ms"
            )
            return results

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(
                f"Keyword search failed: query='{query[:50]}', top_k={top_k}, "
                f"elapsed={elapsed_ms:.1f}ms, error={e}"
            )
            return []

    def _reciprocal_rank_fusion(
        self,
        list1: List[dict],
        list2: List[dict],
        k: int = 60,
    ) -> List[dict]:
        scores: Dict[str, float] = {}
        items: Dict[str, dict] = {}

        for rank, item in enumerate(list1):
            pid = item.get("paper_id") or item.get("paperId", "")
            if not pid:
                continue
            rrf_score = 1.0 / (k + rank + 1)
            scores[pid] = scores.get(pid, 0.0) + rrf_score
            if pid not in items:
                items[pid] = dict(item)

        for rank, item in enumerate(list2):
            pid = item.get("paper_id") or item.get("paperId", "")
            if not pid:
                continue
            rrf_score = 1.0 / (k + rank + 1)
            scores[pid] = scores.get(pid, 0.0) + rrf_score
            if pid not in items:
                items[pid] = dict(item)

        sorted_pids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        result = []
        for pid in sorted_pids:
            item = items[pid]
            item["rrf_score"] = scores[pid]
            result.append(item)

        return result

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict] = None,
    ) -> List[dict]:
        start_time = time.perf_counter()
        try:
            candidate_k = top_k * 2

            semantic_results, keyword_results = await asyncio.gather(
                self.search(query, top_k=candidate_k, filters=filters),
                self.keyword_search(query, top_k=candidate_k, filters=filters),
            )

            fused = self._reciprocal_rank_fusion(
                semantic_results, keyword_results, k=self.RRF_K
            )

            if self.reranker is not None:
                try:
                    fused = await self.reranker.rerank(query, fused)
                except Exception as e:
                    logger.warning(f"Reranker failed in hybrid_search, returning original results: {e}")

            results = fused[:top_k]

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"Hybrid search completed: query='{query[:50]}', top_k={top_k}, "
                f"semantic={len(semantic_results)}, keyword={len(keyword_results)}, "
                f"fused={len(results)}, elapsed={elapsed_ms:.1f}ms"
            )
            return results

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(
                f"Hybrid search failed: query='{query[:50]}', top_k={top_k}, "
                f"elapsed={elapsed_ms:.1f}ms, error={e}"
            )
            return []

    async def suggest(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[str]:
        start_time = time.perf_counter()
        try:
            titles = await self.vector_store_service.suggest_titles(query, top_k=top_k)

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"Suggest completed: query='{query[:50]}', "
                f"suggestions={len(titles)}, elapsed={elapsed_ms:.1f}ms"
            )
            return titles

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(
                f"Suggest failed: query='{query[:50]}', "
                f"elapsed={elapsed_ms:.1f}ms, error={e}"
            )
            return []

    def _format_results(self, raw_results: List[dict]) -> List[dict]:
        formatted = []
        for item in raw_results:
            formatted.append({
                "paper_id": item.get("paperId") or item.get("paper_id"),
                "title": item.get("title"),
                "abstract": item.get("abstract"),
                "score": item.get("score", 0.0),
                "year": item.get("year"),
                "venue": item.get("venue"),
                "citation_count": item.get("citation_count", 0),
            })
        return formatted
