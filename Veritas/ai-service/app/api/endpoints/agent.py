from datetime import datetime

from fastapi import APIRouter
from loguru import logger

from app.agents.analyzer import AnalyzerAgent
from app.agents.generator import GeneratorAgent
from app.agents.graph import run_workflow
from app.agents.retriever import RetrieverAgent
from app.core import events
from app.exception import AIServiceException, ModelNotLoadedException
from app.models.schemas import AgentStateResponse, AnalyzeRequest, AnalyzeResponse

router = APIRouter()


def _build_agent_instances() -> dict:
    if events.app_state.llm_service is None or events.app_state.llm_service.status != "loaded":
        raise ModelNotLoadedException("LLM服务未就绪")
    if events.app_state.prompt_manager is None:
        raise ModelNotLoadedException("Prompt管理器未就绪")
    if events.app_state.search_service is None:
        raise ModelNotLoadedException("搜索服务未就绪")

    retriever = RetrieverAgent(
        llm_service=events.app_state.llm_service,
        prompt_manager=events.app_state.prompt_manager,
        search_service=events.app_state.search_service,
        reranker=events.app_state.reranker,
    )

    analyzer = AnalyzerAgent(
        llm_service=events.app_state.llm_service,
        prompt_manager=events.app_state.prompt_manager,
        personalization_service=getattr(events.app_state, "personalization_service", None),
    )

    generator = GeneratorAgent(
        llm_service=events.app_state.llm_service,
        prompt_manager=events.app_state.prompt_manager,
        personalization_service=getattr(events.app_state, "personalization_service", None),
    )

    return {
        "retriever": retriever,
        "analyzer": analyzer,
        "generator": generator,
    }


def _convert_agent_states(agent_states: dict) -> list[AgentStateResponse]:
    result = []
    for agent_name, state_dict in agent_states.items():
        result.append(
            AgentStateResponse(
                agent_name=agent_name,
                status=state_dict.get("status", "unknown"),
                progress=state_dict.get("progress"),
                intermediate_result=state_dict.get("intermediate_result"),
                duration_ms=state_dict.get("duration_ms"),
            )
        )
    return result


@router.post("/analyze", response_model=AnalyzeResponse, response_model_by_alias=True)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    try:
        agent_instances = _build_agent_instances()
    except ModelNotLoadedException as e:
        raise AIServiceException(code=503, message=e.message)

    logger.info(
        f"Analysis started: analysis_id={request.analysis_id}, "
        f"topic={request.topic}, user_id={request.user_id}"
    )

    try:
        result = await run_workflow(request, agent_instances)
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        raise AIServiceException(code=500, message="分析任务执行失败，请稍后重试")

    agent_state_list = _convert_agent_states(result.get("agent_states", {}))

    return AnalyzeResponse(
        analysis_id=result.get("analysis_id", request.analysis_id or ""),
        status=result.get("status", "completed"),
        report=result.get("report"),
        citations=result.get("citations"),
        agent_states=agent_state_list,
        degraded=result.get("degraded"),
        degraded_reason=result.get("degraded_reason"),
    )
