from fastapi import APIRouter
from fastapi import Query
from loguru import logger

from app.core import events
from app.exception import AIServiceException
from app.models.schemas import (
    HybridSearchRequest,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    SearchSuggestResponse,
)

router = APIRouter()


@router.post("/", response_model=SearchResponse, response_model_by_alias=True)
async def search(request: SearchRequest) -> SearchResponse:
    if events.app_state.search_service is None:
        raise AIServiceException(code=503, message="SearchService未就绪")

    raw_results = await events.app_state.search_service.search(
        query=request.query,
        top_k=request.top_k,
        filters=request.filters,
    )

    results = []
    for item in raw_results:
        results.append(
            SearchResultItem(
                paper_id=item.get("paper_id") or item.get("paperId"),
                title=item.get("title"),
                abstract=item.get("abstract"),
                score=item.get("score", 0.0),
                year=item.get("year"),
                venue=item.get("venue"),
            )
        )

    logger.info(
        f"Search API completed: query='{request.query[:50]}', top_k={request.top_k}, "
        f"results={len(results)}"
    )

    return SearchResponse(results=results, total=len(results))


@router.post("/hybrid", response_model=SearchResponse, response_model_by_alias=True)
async def hybrid_search(request: HybridSearchRequest) -> SearchResponse:
    if events.app_state.search_service is None:
        raise AIServiceException(code=503, message="SearchService未就绪")

    user_profile = None
    if request.user_profile is not None:
        user_profile = {
            "education_level": request.user_profile.education_level,
            "research_field": request.user_profile.research_field,
            "knowledge_level": request.user_profile.knowledge_level,
            "preferred_style": request.user_profile.preferred_style,
        }

    raw_results = await events.app_state.search_service.hybrid_search(
        query=request.query,
        top_k=request.top_k,
        filters=request.filters,
    )

    if events.app_state.reranker is not None and raw_results:
        try:
            raw_results = await events.app_state.reranker.rerank(
                query=request.query,
                results=raw_results,
                user_profile=user_profile,
            )
        except Exception as e:
            logger.warning(f"Reranker failed in hybrid search endpoint: {e}")

    results = []
    for item in raw_results:
        score = item.get("rerank_score") or item.get("score", 0.0)
        results.append(
            SearchResultItem(
                paper_id=item.get("paper_id") or item.get("paperId"),
                title=item.get("title"),
                abstract=item.get("abstract"),
                score=score,
                year=item.get("year"),
                venue=item.get("venue"),
            )
        )

    logger.info(
        f"Hybrid search API completed: query='{request.query[:50]}', top_k={request.top_k}, "
        f"results={len(results)}"
    )

    return SearchResponse(results=results, total=len(results))


@router.get("/suggest", response_model=SearchSuggestResponse)
async def suggest(
    query: str = Query(..., min_length=1, max_length=100, description="搜索查询文本"),
) -> SearchSuggestResponse:
    if events.app_state.search_service is None:
        raise AIServiceException(code=503, message="SearchService未就绪")

    suggestions = await events.app_state.search_service.suggest(query=query)

    logger.info(
        f"Suggest API completed: query='{query[:50]}', suggestions={len(suggestions)}"
    )

    return SearchSuggestResponse(suggestions=suggestions, total=len(suggestions))
