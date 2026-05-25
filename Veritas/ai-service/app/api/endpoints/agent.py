import uuid

from fastapi import APIRouter
from loguru import logger

from app.core import events
from app.exception import AIServiceException
from app.models.schemas import AnalyzeRequest, AnalyzeResponse

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    if events.llm_service is None or events.llm_service.status != "loaded":
        raise AIServiceException(code=503, message="LLM服务未就绪")
    if events.embedding_service is None or events.embedding_service.status == "error":
        raise AIServiceException(code=503, message="Embedding服务未就绪")

    analysis_id = f"ana_{uuid.uuid4().hex[:12]}"
    logger.info(
        f"Analysis started: analysis_id={analysis_id}, "
        f"topic={request.topic}, user_id={request.user_id}"
    )

    return AnalyzeResponse(analysis_id=analysis_id, status="processing")
