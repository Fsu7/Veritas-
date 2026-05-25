import uuid

from fastapi import APIRouter
from loguru import logger

from app.core import events
from app.exception import AIServiceException
from app.models.schemas import AnalyzeRequest, AnalyzeResponse

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse, response_model_by_alias=True)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    if events.app_state.llm_service is None or events.app_state.llm_service.status != "loaded":
        raise AIServiceException(code=503, message="LLM服务未就绪")
    if events.app_state.embedding_service is None or events.app_state.embedding_service.status == "error":
        raise AIServiceException(code=503, message="Embedding服务未就绪")

    analysis_id = request.analysis_id or f"ana_{uuid.uuid4().hex[:12]}"
    logger.info(
        f"Analysis started: analysis_id={analysis_id}, "
        f"topic={request.topic}, user_id={request.user_id}"
    )

    return AnalyzeResponse(analysis_id=analysis_id, status="processing")
