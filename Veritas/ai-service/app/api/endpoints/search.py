from fastapi import APIRouter
from loguru import logger

from app.core import events
from app.exception import AIServiceException
from app.models.schemas import (
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)

router = APIRouter()


@router.post("/", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    if events.embedding_service is None or events.embedding_service.status == "error":
        raise AIServiceException(code=503, message="Embedding服务未就绪")
    if events.vector_store_service is None or events.vector_store_service.status != "connected":
        raise AIServiceException(code=503, message="ChromaDB未就绪")

    query_embedding = await events.embedding_service.encode(request.query)
    raw_results = await events.vector_store_service.search(
        embedding=query_embedding.tolist(),
        top_k=request.top_k,
        filters=request.filters,
    )

    results = []
    for item in raw_results:
        results.append(
            SearchResultItem(
                paper_id=item.get("paperId"),
                title=item.get("title"),
                abstract=item.get("abstract"),
                score=item.get("score", 0.0),
                year=item.get("year"),
                venue=item.get("venue"),
            )
        )

    logger.info(
        f"Search completed: query={request.query}, top_k={request.top_k}, "
        f"results={len(results)}"
    )

    return SearchResponse(results=results, total=len(results))
