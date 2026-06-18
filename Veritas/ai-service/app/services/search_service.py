import asyncio
import re
import time
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from loguru import logger


# 停用词列表（模块级常量，避免硬编码到业务代码）
STOP_WORDS = frozenset({
    "a", "an", "the", "of", "for", "in", "on", "with", "and", "or", "to",
})

# 中文字符正则（CJK Unified Ideographs 基本区）
_CHINESE_CHAR_RE = re.compile(r"[\u4e00-\u9fff]")
# 双引号包裹的短语正则
_PHRASE_RE = re.compile(r'"([^"]+)"')
# 英文 token 正则（字母、数字、连字符）
_ENGLISH_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]*")


class SearchService:

    def __init__(
        self,
        vector_store_service,
        embedding_service,
        reranker=None,
        settings=None,
    ):
        self.vector_store_service = vector_store_service
        self.embedding_service = embedding_service
        self.reranker = reranker
        # task47: RRF_K 从 settings 读取，默认 60
        # task54: SEARCH_TOP_K / SEARCH_SIMILARITY_THRESHOLD 从 settings 读取
        if settings is not None:
            self.rrf_k = settings.RRF_K
            self.search_top_k = getattr(settings, "SEARCH_TOP_K", 10)
            self.similarity_threshold = getattr(settings, "SEARCH_SIMILARITY_THRESHOLD", 0.0)
        else:
            self.rrf_k = 60
            self.search_top_k = 10
            self.similarity_threshold = 0.0

    def _tokenize_query(self, query: str) -> Tuple[List[str], List[str]]:
        """查询分词：返回 (tokens, phrases)。

        分词规则：
        1. 双引号包裹部分作为 phrase 加入 phrases 列表（精确匹配）
        2. 英文按空格分词，转小写，过滤停用词
        3. 中文按 bigram 切分（每两个相邻中文字符为一个 token），单字中文字符作为独立 token
        4. 中英文混合查询同时产生英文 token 和中文 bigram
        """
        if not query or not query.strip():
            return [], []

        text = query.strip()

        # Step 1: 提取双引号包裹的短语
        phrases = []
        text_without_phrases = text
        for match in _PHRASE_RE.finditer(text):
            phrase = match.group(1).strip()
            if phrase:
                phrases.append(phrase)
        # 移除已提取的短语，避免重复分词
        text_without_phrases = _PHRASE_RE.sub(" ", text)

        tokens: List[str] = []

        # Step 2: 英文 token 提取
        for raw_token in text_without_phrases.split():
            # 处理 "Multi-Agent" 这类带连字符的 token，保留整体
            if _ENGLISH_TOKEN_RE.fullmatch(raw_token):
                token_lower = raw_token.lower()
                if token_lower not in STOP_WORDS and token_lower not in tokens:
                    tokens.append(token_lower)
            else:
                # 混合 token，提取其中的英文部分
                for sub_match in _ENGLISH_TOKEN_RE.finditer(raw_token):
                    token_lower = sub_match.group(0).lower()
                    if token_lower not in STOP_WORDS and token_lower not in tokens:
                        tokens.append(token_lower)

        # Step 3: 中文 bigram 切分
        # 收集所有中文字符（保持顺序）
        chinese_chars = [c for c in text_without_phrases if _CHINESE_CHAR_RE.match(c)]
        if chinese_chars:
            if len(chinese_chars) == 1:
                # 单字中文字符作为独立 token
                if chinese_chars[0] not in tokens:
                    tokens.append(chinese_chars[0])
            else:
                # bigram 切分
                for i in range(len(chinese_chars) - 1):
                    bigram = chinese_chars[i] + chinese_chars[i + 1]
                    if bigram not in tokens:
                        tokens.append(bigram)
                # 末尾单字（如果中文字符数为奇数且>1，最后一个字已在 bigram 中覆盖）
                # 注意：bigram 已覆盖所有字符，无需额外添加单字

        return tokens, phrases

    async def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict] = None,
    ) -> List[dict]:
        # task54: top_k=None 时用 settings.SEARCH_TOP_K，保留参数覆盖能力
        if top_k is None:
            top_k = self.search_top_k
        start_time = time.perf_counter()
        try:
            query_embedding = await self.embedding_service.encode(query)
            raw_results = await self.vector_store_service.search(
                embedding=query_embedding.tolist(),
                top_k=top_k,
                filters=filters,
                similarity_threshold=self.similarity_threshold,
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
        top_k: Optional[int] = None,
        filters: Optional[Dict] = None,
    ) -> List[dict]:
        """关键词检索：支持中文 bigram + 英文 token + 短语查询，失败降级为语义检索。"""
        # task54: top_k=None 时用 settings.SEARCH_TOP_K
        if top_k is None:
            top_k = self.search_top_k
        start_time = time.perf_counter()
        try:
            # 分词：获取 tokens 和 phrases
            tokens, phrases = self._tokenize_query(query)

            raw_results = await self.vector_store_service.search_by_keywords(
                query_text=query,
                top_k=top_k,
                filters=filters,
                tokens=tokens,
                phrases=phrases,
            )

            results = self._format_results(raw_results)

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"Keyword search completed: query='{query[:50]}', top_k={top_k}, "
                f"tokens={len(tokens)}, phrases={len(phrases)}, "
                f"results={len(results)}, elapsed={elapsed_ms:.1f}ms"
            )
            return results

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(
                f"Keyword search failed, degrading to semantic search: "
                f"query='{query[:50]}', top_k={top_k}, "
                f"elapsed={elapsed_ms:.1f}ms, error={e}"
            )
            # 降级为语义检索，不阻塞 hybrid_search 流程
            return await self.search(query, top_k=top_k, filters=filters)

    def _reciprocal_rank_fusion(
        self,
        list1: List[dict],
        list2: List[dict],
        k: Optional[int] = None,
    ) -> List[dict]:
        # task47: k 值从 self.rrf_k 读取（由 settings 注入），保留参数覆盖能力
        if k is None:
            k = self.rrf_k
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
        top_k: Optional[int] = None,
        filters: Optional[Dict] = None,
    ) -> List[dict]:
        # task54: top_k=None 时用 settings.SEARCH_TOP_K
        if top_k is None:
            top_k = self.search_top_k
        start_time = time.perf_counter()
        try:
            candidate_k = top_k * 2

            semantic_results, keyword_results = await asyncio.gather(
                self.search(query, top_k=candidate_k, filters=filters),
                self.keyword_search(query, top_k=candidate_k, filters=filters),
            )

            fused = self._reciprocal_rank_fusion(
                semantic_results, keyword_results, k=self.rrf_k
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
