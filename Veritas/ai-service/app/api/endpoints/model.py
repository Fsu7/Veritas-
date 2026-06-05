"""模型状态端点 — task26 升级"""
from typing import Optional

from fastapi import APIRouter

from app.core import events
from app.models.schemas import ModelStatusResponse
from app.utils.response import fail_response, ok

router = APIRouter()


def _safe_get_gpu_memory() -> Optional[str]:
    """task26 FR-005：GPU 显存查询，异常时返回 None 不抛 5xx"""
    try:
        import torch  # type: ignore

        if not torch.cuda.is_available():
            return None
        allocated = torch.cuda.memory_allocated() / (1024 ** 3)
        reserved = torch.cuda.memory_reserved() / (1024 ** 3)
        total = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
        return f"{allocated:.1f}GB / {total:.1f}GB"
    except Exception:
        return None


def _safe_get_chroma_count() -> Optional[int]:
    """task26 FR-004：ChromaDB 论文数量，异常时返回 None"""
    try:
        vss = events.app_state.vector_store_service
        if vss is None or vss.collection is None:
            return None
        return vss.collection.count()
    except Exception:
        return None


@router.get("/status")
async def model_status():
    """GET /api/model/status — task26 扩展 4 字段（providerCandidates/chromaPaperCount/gpuMemoryUsed/llmProviderCount）"""
    if events.app_state.llm_service is None:
        return fail_response(message="LLM服务未就绪", code=503)

    llm = events.app_state.llm_service

    # providerCandidates 来自已加载的 provider 字典
    provider_candidates = list(llm.providers.keys()) if llm.providers else []
    active_provider = llm.active_provider.mode if llm.active_provider else None

    response_data = ModelStatusResponse(
        llm=llm.status,
        embedding=(
            events.app_state.embedding_service.status
            if events.app_state.embedding_service
            else "not_loaded"
        ),
        chroma=(
            events.app_state.vector_store_service.status
            if events.app_state.vector_store_service
            else "not_connected"
        ),
        prompts=(
            events.app_state.prompt_manager.status
            if events.app_state.prompt_manager
            else "not_loaded"
        ),
        embedding_dimension=(
            events.app_state.embedding_service.dimension
            if events.app_state.embedding_service
            else None
        ),
        active_llm_provider=active_provider,
        provider_candidates=provider_candidates,
        chroma_paper_count=_safe_get_chroma_count(),
        gpu_memory_used=_safe_get_gpu_memory() if active_provider == "local" else None,
        llm_provider_count=len(provider_candidates),
        search_service="ready" if events.app_state.search_service else "not_initialized",
        reranker="ready" if events.app_state.reranker else "not_initialized",
    )

    return ok(data=response_data.model_dump(by_alias=True, exclude_none=False))
