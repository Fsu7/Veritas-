from fastapi import APIRouter

from app.core import events
from app.models.schemas import ModelStatusResponse

router = APIRouter()


@router.get("/status", response_model=ModelStatusResponse, response_model_by_alias=True)
async def model_status() -> ModelStatusResponse:
    return ModelStatusResponse(
        llm=events.app_state.llm_service.status if events.app_state.llm_service else "not_loaded",
        embedding=events.app_state.embedding_service.status if events.app_state.embedding_service else "not_loaded",
        chroma=events.app_state.vector_store_service.status if events.app_state.vector_store_service else "not_connected",
        prompts=events.app_state.prompt_manager.status if events.app_state.prompt_manager else "not_loaded",
        embedding_dimension=events.app_state.embedding_service.dimension if events.app_state.embedding_service else None,
        active_llm_provider=(
            events.app_state.llm_service.active_provider.mode
            if events.app_state.llm_service and events.app_state.llm_service.active_provider
            else None
        ),
    )
