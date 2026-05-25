from fastapi import APIRouter

from app.core import events
from app.models.schemas import ModelStatusResponse

router = APIRouter()


@router.get("/status", response_model=ModelStatusResponse)
async def model_status() -> ModelStatusResponse:
    return ModelStatusResponse(
        llm=events.llm_service.status if events.llm_service else "not_loaded",
        embedding=events.embedding_service.status if events.embedding_service else "not_loaded",
        chroma=events.vector_store_service.status if events.vector_store_service else "not_connected",
        prompts=events.prompt_manager.status if events.prompt_manager else "not_loaded",
        embedding_dimension=events.embedding_service.dimension if events.embedding_service else None,
        active_llm_provider=(
            events.llm_service.active_provider.mode
            if events.llm_service and events.llm_service.active_provider
            else None
        ),
    )
