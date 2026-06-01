import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph
from loguru import logger

from app.core.config import settings
from app.models.schemas import AnalyzeRequest


class WorkflowState(TypedDict):
    query: str
    user_profile: Dict[str, Any]
    analysis_type: str
    analysis_id: str
    sub_tasks: List[str]
    search_results: List[Dict]
    analysis_results: List[Dict]
    compare_result: Optional[Dict]
    report: Optional[str]
    review_result: Optional[Dict]
    citations: List[Dict]
    final_output: Optional[str]
    agent_states: Dict[str, Dict]
    errors: List[Dict]
    degraded: bool
    regenerate_count: int
    started_at: Optional[str]
    completed_at: Optional[str]


def _serialize_agent_state(agent) -> Dict[str, Any]:
    return agent.state.to_dict()


async def retrieve_node(state: WorkflowState, agent_instances: Dict[str, Any]) -> dict:
    retriever = agent_instances.get("retriever")
    if retriever is None:
        return {
            "search_results": [],
            "errors": state.get("errors", []) + [{"agent": "retriever", "error": "RetrieverAgent not found"}],
            "degraded": True,
            "agent_states": {**state.get("agent_states", {}), "retriever": {"name": "retriever", "status": "failed", "error": "Agent not found"}},
        }

    try:
        result = await retriever.execute(
            input_data={"query": state["query"], "top_k": 10, "topic": state["query"]},
            context={"user_profile": state.get("user_profile", {})},
        )
        papers = result.get("papers", [])
        return {
            "search_results": papers,
            "agent_states": {**state.get("agent_states", {}), "retriever": _serialize_agent_state(retriever)},
        }
    except Exception as e:
        logger.error(f"retrieve_node failed: {e}")
        return {
            "search_results": [],
            "errors": state.get("errors", []) + [{"agent": "retriever", "error": str(e)}],
            "degraded": True,
            "agent_states": {**state.get("agent_states", {}), "retriever": _serialize_agent_state(retriever)},
        }


async def analyze_node(state: WorkflowState, agent_instances: Dict[str, Any]) -> dict:
    analyzer = agent_instances.get("analyzer")
    if analyzer is None:
        return {
            "analysis_results": [],
            "errors": state.get("errors", []) + [{"agent": "analyzer", "error": "AnalyzerAgent not found"}],
            "degraded": True,
            "agent_states": {**state.get("agent_states", {}), "analyzer": {"name": "analyzer", "status": "failed", "error": "Agent not found"}},
        }

    try:
        result = await analyzer.execute(
            input_data={"papers": state.get("search_results", [])},
            context={"user_profile": state.get("user_profile", {})},
        )
        analysis_results = result.get("analysis_results", [])
        return {
            "analysis_results": analysis_results,
            "agent_states": {**state.get("agent_states", {}), "analyzer": _serialize_agent_state(analyzer)},
        }
    except Exception as e:
        logger.error(f"analyze_node failed: {e}")
        return {
            "analysis_results": [],
            "errors": state.get("errors", []) + [{"agent": "analyzer", "error": str(e)}],
            "degraded": True,
            "agent_states": {**state.get("agent_states", {}), "analyzer": _serialize_agent_state(analyzer)},
        }


async def generate_node(state: WorkflowState, agent_instances: Dict[str, Any]) -> dict:
    generator = agent_instances.get("generator")
    if generator is None:
        return {
            "report": "生成服务不可用，无法生成综述报告。",
            "citations": [],
            "errors": state.get("errors", []) + [{"agent": "generator", "error": "GeneratorAgent not found"}],
            "degraded": True,
            "agent_states": {**state.get("agent_states", {}), "generator": {"name": "generator", "status": "failed", "error": "Agent not found"}},
        }

    try:
        result = await generator.execute(
            input_data={
                "analysis_results": state.get("analysis_results", []),
                "compare_result": state.get("compare_result"),
            },
            context={"user_profile": state.get("user_profile", {})},
        )
        report = result.get("report", "")
        citations = result.get("citation_list", [])
        return {
            "report": report,
            "citations": citations,
            "agent_states": {**state.get("agent_states", {}), "generator": _serialize_agent_state(generator)},
        }
    except Exception as e:
        logger.error(f"generate_node failed: {e}")
        return {
            "report": "综述生成过程中发生错误，请稍后重试。",
            "citations": [],
            "errors": state.get("errors", []) + [{"agent": "generator", "error": str(e)}],
            "degraded": True,
            "agent_states": {**state.get("agent_states", {}), "generator": _serialize_agent_state(generator)},
        }


def build_agent_graph(agent_instances: Dict[str, Any]) -> StateGraph:
    async def _retrieve(state: WorkflowState) -> dict:
        return await retrieve_node(state, agent_instances)

    async def _analyze(state: WorkflowState) -> dict:
        return await analyze_node(state, agent_instances)

    async def _generate(state: WorkflowState) -> dict:
        return await generate_node(state, agent_instances)

    graph = StateGraph(WorkflowState)

    graph.add_node("retrieve", _retrieve)
    graph.add_node("analyze", _analyze)
    graph.add_node("generate", _generate)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "analyze")
    graph.add_edge("analyze", "generate")
    graph.add_edge("generate", END)

    return graph.compile()


async def run_workflow(request: AnalyzeRequest, agent_instances: Dict[str, Any]) -> dict:
    analysis_id = request.analysis_id or f"ana_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    user_profile_dict = {}
    if request.user_profile is not None:
        user_profile_dict = request.user_profile.model_dump(by_alias=False)

    initial_state: WorkflowState = {
        "query": request.topic,
        "user_profile": user_profile_dict,
        "analysis_type": request.analysis_type or "report",
        "analysis_id": analysis_id,
        "sub_tasks": [],
        "search_results": [],
        "analysis_results": [],
        "compare_result": None,
        "report": None,
        "review_result": None,
        "citations": [],
        "final_output": None,
        "agent_states": {},
        "errors": [],
        "degraded": False,
        "regenerate_count": 0,
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
    }

    try:
        compiled_graph = build_agent_graph(agent_instances)

        result_state = await asyncio.wait_for(
            compiled_graph.ainvoke(initial_state),
            timeout=settings.AGENT_FULL_TIMEOUT,
        )

        result_state["completed_at"] = datetime.now().isoformat()

        error_count = len(result_state.get("errors", []))
        is_degraded = result_state.get("degraded", False)
        degraded_reason = None

        if error_count >= 2:
            is_degraded = True
            failed_agents = [e.get("agent", "unknown") for e in result_state.get("errors", [])]
            degraded_reason = f"多Agent失败({', '.join(failed_agents)})，结果可能不完整"
        elif is_degraded and error_count == 1:
            failed_agent = result_state.get("errors", [{}])[0].get("agent", "unknown")
            degraded_reason = f"Agent {failed_agent} 失败，已降级处理"

        status = "completed"
        if is_degraded and error_count >= 2:
            status = "degraded"
        elif is_degraded:
            status = "degraded"

        return {
            "analysis_id": result_state.get("analysis_id", analysis_id),
            "status": status,
            "report": result_state.get("report"),
            "citations": result_state.get("citations", []),
            "agent_states": result_state.get("agent_states", {}),
            "errors": result_state.get("errors", []),
            "degraded": is_degraded,
            "degraded_reason": degraded_reason,
            "started_at": result_state.get("started_at"),
            "completed_at": result_state.get("completed_at"),
        }

    except asyncio.TimeoutError:
        logger.error(f"Workflow timed out after {settings.AGENT_FULL_TIMEOUT}s")
        return {
            "analysis_id": analysis_id,
            "status": "failed",
            "report": None,
            "citations": [],
            "agent_states": initial_state.get("agent_states", {}),
            "errors": [{"agent": "workflow", "error": f"全流程超时({settings.AGENT_FULL_TIMEOUT}s)"}],
            "degraded": True,
            "degraded_reason": f"全流程超时({settings.AGENT_FULL_TIMEOUT}s)，返回部分结果",
            "started_at": initial_state.get("started_at"),
            "completed_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        return {
            "analysis_id": analysis_id,
            "status": "failed",
            "report": None,
            "citations": [],
            "agent_states": initial_state.get("agent_states", {}),
            "errors": [{"agent": "workflow", "error": str(e)}],
            "degraded": True,
            "degraded_reason": f"工作流执行异常: {str(e)}",
            "started_at": initial_state.get("started_at"),
            "completed_at": datetime.now().isoformat(),
        }
