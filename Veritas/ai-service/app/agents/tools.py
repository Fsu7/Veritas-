from typing import Callable, Dict, List, Optional

from loguru import logger


async def vector_search_tool(
    search_service,
    query: str,
    top_k: int = 20,
    filters: Optional[Dict] = None,
) -> List[dict]:
    try:
        return await search_service.search(query=query, top_k=top_k, filters=filters)
    except Exception as e:
        logger.warning(f"vector_search_tool failed: {e}")
        return []


async def keyword_search_tool(
    search_service,
    query: str,
    top_k: int = 20,
    filters: Optional[Dict] = None,
) -> List[dict]:
    try:
        return await search_service.keyword_search(query=query, top_k=top_k, filters=filters)
    except Exception as e:
        logger.warning(f"keyword_search_tool failed: {e}")
        return []


async def hybrid_search_tool(
    search_service,
    query: str,
    top_k: int = 10,
    filters: Optional[Dict] = None,
) -> List[dict]:
    try:
        return await search_service.hybrid_search(query=query, top_k=top_k, filters=filters)
    except Exception as e:
        logger.warning(f"hybrid_search_tool failed: {e}")
        return []


async def rerank_tool(
    reranker,
    query: str,
    results: List[dict],
    user_profile: Optional[Dict] = None,
) -> List[dict]:
    try:
        return await reranker.rerank(query, results, user_profile=user_profile)
    except Exception as e:
        logger.warning(f"rerank_tool failed, returning original results: {e}")
        return results


TOOL_REGISTRY: Dict[str, Callable] = {
    "vector_search": vector_search_tool,
    "keyword_search": keyword_search_tool,
    "hybrid_search": hybrid_search_tool,
    "rerank": rerank_tool,
}
