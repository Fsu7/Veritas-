from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Header
from loguru import logger
from sse_starlette.sse import EventSourceResponse

from app.agents.analyzer import AnalyzerAgent
from app.agents.comparer import ComparerAgent
from app.agents.coordinator import CoordinatorAgent
from app.agents.generator import GeneratorAgent
from app.agents.graph import run_workflow
from app.agents.orchestrator import AgentOrchestrator
from app.agents.retriever import RetrieverAgent
from app.agents.reviewer import ReviewerAgent
from app.core import events
from app.exception import AIServiceException, ModelNotLoadedException
from app.models.schemas import AgentStateResponse, AnalyzeRequest, AnalyzeResponse
from app.utils.response import fail_response, ok

router = APIRouter()


def _build_agent_instances() -> dict:
    if events.app_state.llm_service is None or events.app_state.llm_service.status != "loaded":
        raise ModelNotLoadedException("LLM服务未就绪")
    if events.app_state.prompt_manager is None:
        raise ModelNotLoadedException("Prompt管理器未就绪")
    if events.app_state.search_service is None:
        raise ModelNotLoadedException("搜索服务未就绪")

    coordinator = CoordinatorAgent(
        llm_service=events.app_state.llm_service,
        prompt_manager=events.app_state.prompt_manager,
        personalization_service=getattr(events.app_state, "personalization_service", None),
    )

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

    comparer = ComparerAgent(
        llm_service=events.app_state.llm_service,
        prompt_manager=events.app_state.prompt_manager,
        personalization_service=getattr(events.app_state, "personalization_service", None),
    )

    generator = GeneratorAgent(
        llm_service=events.app_state.llm_service,
        prompt_manager=events.app_state.prompt_manager,
        personalization_service=getattr(events.app_state, "personalization_service", None),
    )

    reviewer = ReviewerAgent(
        llm_service=events.app_state.llm_service,
        prompt_manager=events.app_state.prompt_manager,
        personalization_service=getattr(events.app_state, "personalization_service", None),
    )

    return {
        "coordinator": coordinator,
        "retriever": retriever,
        "analyzer": analyzer,
        "comparer": comparer,
        "generator": generator,
        "reviewer": reviewer,
    }


def _convert_agent_states(agent_states: dict) -> list[AgentStateResponse]:
    result = []
    for agent_name, state_dict in agent_states.items():
        is_degraded = state_dict.get("status") == "failed" or state_dict.get("degraded", False)
        result.append(
            AgentStateResponse(
                agent_name=agent_name,
                status=state_dict.get("status", "unknown"),
                progress=state_dict.get("progress"),
                intermediate_result=state_dict.get("intermediate_result"),
                duration_ms=state_dict.get("duration_ms"),
                error=state_dict.get("error"),
                started_at=state_dict.get("started_at"),
                completed_at=state_dict.get("completed_at"),
                degraded=is_degraded,
            )
        )
    return result


@router.post("/analyze")
async def analyze(request: AnalyzeRequest):
    """POST /api/agent/analyze — task24 改用统一响应 ok() 包装"""
    try:
        agent_instances = _build_agent_instances()
    except ModelNotLoadedException as e:
        return fail_response(message=e.message, code=503)

    logger.info(
        f"Analysis started: analysis_id={request.analysis_id}, "
        f"topic={request.topic}, user_id={request.user_id}"
    )

    try:
        result = await run_workflow(request, agent_instances)
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        return fail_response(message="分析任务执行失败，请稍后重试", code=500)

    agent_state_list = _convert_agent_states(result.get("agent_states", {}))

    # 计算 degradation_level（基于失败Agent数量）
    degraded_agents = result.get("degraded_agents", [])
    if len(degraded_agents) == 0:
        degradation_level = "none"
    elif len(degraded_agents) == 1:
        degradation_level = "partial"
    elif len(degraded_agents) == 2:
        degradation_level = "severe"
    else:
        degradation_level = "critical"

    response_data = AnalyzeResponse(
        analysis_id=result.get("analysis_id", request.analysis_id or ""),
        status=result.get("status", "completed"),
        report=result.get("report"),
        citations=result.get("citations"),
        agent_states=agent_state_list,
        degraded=result.get("degraded"),
        degraded_reason=result.get("degraded_reason"),
        degradation_level=degradation_level,
    )

    # model_dump(by_alias=True) 输出 camelCase
    return ok(data=response_data.model_dump(by_alias=True, exclude_none=False))


@router.post("/analyze/stream")
async def analyze_stream(
    request: AnalyzeRequest,
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
):
    """POST /api/agent/analyze/stream — task25 SSE 流式推送，task30/52 增强

    使用 sse-starlette EventSourceResponse 返回 SSE 流。
    事件类型（10种）：agent_started / agent_state_update / agent_completed /
              agent_failed / workflow_degraded / review_rejected /
              analysis_completed / error / ping / token_stream

    task30: 支持 Last-Event-ID Header 实现断线重连。
    task52: 新增 token_stream 事件，Generator 流式 token 实时推送。
    """
    try:
        agent_instances = _build_agent_instances()
    except ModelNotLoadedException as e:
        # 服务未就绪时无法启动流，返回统一错误
        return fail_response(message=e.message, code=503)

    analysis_id = request.analysis_id or f"ana_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # task30: 解析 Last-Event-ID（仅接受正整数）
    parsed_last_event_id = None
    if last_event_id is not None:
        try:
            parsed_last_event_id = int(last_event_id)
            if parsed_last_event_id <= 0:
                parsed_last_event_id = None
        except (ValueError, TypeError):
            parsed_last_event_id = None

    logger.info(
        f"SSE Analysis started: analysis_id={analysis_id}, "
        f"topic={request.topic}, user_id={request.user_id}, "
        f"last_event_id={parsed_last_event_id}"
    )

    orchestrator = AgentOrchestrator(
        agent_instances=agent_instances,
        analysis_id=analysis_id,
        last_event_id=parsed_last_event_id,
    )

    async def event_generator():
        """SSE 事件生成器"""
        async for sse_event in orchestrator.run_workflow_stream(request):
            yield {
                "id": sse_event["id"],
                "event": sse_event["event"],
                "data": sse_event["data"],
            }

    return EventSourceResponse(event_generator())
