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
    # Task 42: 6-Agent 工作流新增字段
    requires_compare: bool
    requires_review: bool
    coordinator_result: Optional[Dict]
    # Task 43: 降级机制新增字段
    degraded_agents: List[str]
    degradation_level: str


def _serialize_agent_state(agent) -> Dict[str, Any]:
    return agent.state.to_dict()


def should_compare(state: WorkflowState) -> str:
    """判断是否需要对比：requires_compare=True 且论文数>=2 时进入对比节点"""
    if state.get("requires_compare", False) and len(state.get("search_results", [])) >= 2:
        return "compare"
    return "generate"


def should_review(state: WorkflowState) -> bool:
    """判断是否需要审核：report非空且非退化时进入审核"""
    report = state.get("report", "")
    degraded = state.get("degraded", False)
    if not report or not report.strip():
        return False
    if degraded and not state.get("review_result"):
        return False
    return True


def should_regenerate(state: WorkflowState) -> str:
    """判断是否需要重新生成。

    审核不通过（approved=False）且 regenerate_count < 1 时返回 'regenerate'，
    否则返回 'end'。
    """
    review_result = state.get("review_result") or {}
    regenerate_count = state.get("regenerate_count", 0)

    approved = review_result.get("approved", True)
    if not approved and regenerate_count < 1:
        return "regenerate"

    return "end"


async def coordinator_node(state: WorkflowState, agent_instances: Dict[str, Any]) -> dict:
    """协调者节点：调用 CoordinatorAgent 进行任务分解，设置 requires_compare/requires_review 标记"""
    coordinator = agent_instances.get("coordinator")
    if coordinator is None:
        logger.warning("CoordinatorAgent not found, using default flags")
        return {
            "requires_compare": False,
            "requires_review": True,
            "sub_tasks": [],
            "coordinator_result": None,
            "degraded": True,
            "errors": state.get("errors", []) + [{"agent": "coordinator", "error": "Agent not found"}],
            "agent_states": {**state.get("agent_states", {}), "coordinator": {"name": "coordinator", "status": "failed", "error": "Agent not found"}},
        }

    try:
        result = await coordinator.execute(
            input_data={
                "topic": state["query"],
                "analysis_type": state.get("analysis_type", "report"),
                "paper_ids": state.get("user_profile", {}).get("paper_ids", []),
            },
            context={"user_profile": state.get("user_profile", {})},
        )

        requires_compare = result.get("requires_compare", False)
        requires_review = result.get("requires_review", True)
        sub_tasks = result.get("sub_tasks", [])

        update: Dict[str, Any] = {
            "requires_compare": requires_compare,
            "requires_review": requires_review,
            "sub_tasks": sub_tasks,
            "coordinator_result": result,
            "agent_states": {**state.get("agent_states", {}), "coordinator": _serialize_agent_state(coordinator)},
        }

        # 检查 coordinator 是否降级
        if result.get("degraded", False):
            update["degraded"] = True
            update["degraded_agents"] = state.get("degraded_agents", []) + ["coordinator"]
            update["degradation_level"] = "agent"
            update["errors"] = state.get("errors", []) + [{"agent": "coordinator", "error": result.get("error", "coordinator degraded")}]

        return update
    except Exception as e:
        logger.error(f"coordinator_node failed: {e}")
        return {
            "requires_compare": False,
            "requires_review": True,
            "sub_tasks": [],
            "coordinator_result": None,
            "degraded": True,
            "degraded_agents": state.get("degraded_agents", []) + ["coordinator"],
            "degradation_level": "agent",
            "errors": state.get("errors", []) + [{"agent": "coordinator", "error": str(e)}],
            "agent_states": {**state.get("agent_states", {}), "coordinator": _serialize_agent_state(coordinator)},
        }


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

        # 检查 retriever 是否降级
        if result.get("degraded", False):
            return {
                "search_results": [],
                "degraded": True,
                "degraded_agents": state.get("degraded_agents", []) + ["retriever"],
                "degradation_level": "agent",
                "errors": state.get("errors", []) + [{"agent": "retriever", "error": result.get("error", "retriever degraded")}],
                "agent_states": {**state.get("agent_states", {}), "retriever": _serialize_agent_state(retriever)},
            }

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

        # 检查 analyzer 是否降级
        if result.get("degraded", False):
            return {
                "analysis_results": [],
                "degraded": True,
                "degraded_agents": state.get("degraded_agents", []) + ["analyzer"],
                "degradation_level": "agent",
                "errors": state.get("errors", []) + [{"agent": "analyzer", "error": result.get("error", "analyzer degraded")}],
                "agent_states": {**state.get("agent_states", {}), "analyzer": _serialize_agent_state(analyzer)},
            }

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


async def compare_node(state: WorkflowState, agent_instances: Dict[str, Any]) -> dict:
    """对比节点：调用 ComparerAgent 进行多论文对比与矛盾发现"""
    comparer = agent_instances.get("comparer")
    if comparer is None:
        logger.warning("ComparerAgent not found, skipping comparison")
        return {
            "compare_result": None,
            "degraded": True,
            "degraded_agents": state.get("degraded_agents", []) + ["comparer"],
            "degradation_level": "agent",
            "errors": state.get("errors", []) + [{"agent": "comparer", "error": "Agent not found"}],
            "agent_states": {**state.get("agent_states", {}), "comparer": {"name": "comparer", "status": "failed", "error": "Agent not found"}},
        }

    try:
        result = await comparer.execute(
            input_data={"analysis_results": state.get("analysis_results", [])},
            context={"user_profile": state.get("user_profile", {})},
        )

        update: Dict[str, Any] = {
            "compare_result": result,
            "agent_states": {**state.get("agent_states", {}), "comparer": _serialize_agent_state(comparer)},
        }

        # 检查 comparer 是否降级
        if result.get("degraded", False):
            update["degraded"] = True
            update["degraded_agents"] = state.get("degraded_agents", []) + ["comparer"]
            update["degradation_level"] = "agent"
            update["errors"] = state.get("errors", []) + [{"agent": "comparer", "error": result.get("error", "comparer degraded")}]

        return update
    except Exception as e:
        logger.error(f"compare_node failed: {e}")
        return {
            "compare_result": None,
            "degraded": True,
            "degraded_agents": state.get("degraded_agents", []) + ["comparer"],
            "degradation_level": "agent",
            "errors": state.get("errors", []) + [{"agent": "comparer", "error": str(e)}],
            "agent_states": {**state.get("agent_states", {}), "comparer": _serialize_agent_state(comparer)},
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
        input_data = {
            "analysis_results": state.get("analysis_results", []),
            "compare_result": state.get("compare_result"),
        }

        # 重试上下文：当 regenerate_count > 0 时，将 review_result 中的 issues/suggestions 注入
        regenerate_count = state.get("regenerate_count", 0)
        if regenerate_count > 0:
            review_result = state.get("review_result") or {}
            issues = review_result.get("issues", [])
            suggestions = review_result.get("suggestions", [])
            if issues or suggestions:
                retry_context_parts: List[str] = []
                if issues:
                    retry_context_parts.append("上次审核发现的问题：")
                    for issue in issues:
                        retry_context_parts.append(
                            f"- {issue.get('claim', issue.get('citation', ''))} "
                            f"({issue.get('error_type', 'unknown')}: {issue.get('note', issue.get('issue', ''))})"
                        )
                if suggestions:
                    retry_context_parts.append("修改建议：")
                    for sug in suggestions:
                        retry_context_parts.append(
                            f"- [{sug.get('section', '')}] {sug.get('suggestion', '')}"
                        )
                input_data["retry_context"] = "\n".join(retry_context_parts)

        result = await generator.execute(
            input_data=input_data,
            context={"user_profile": state.get("user_profile", {})},
        )
        report = result.get("report", "")
        citations = result.get("citation_list", [])

        # 检查 generator 是否降级
        if result.get("degraded", False):
            return {
                "report": result.get("report", "综述生成过程中发生降级，返回部分结果。"),
                "citations": citations,
                "degraded": True,
                "degraded_agents": state.get("degraded_agents", []) + ["generator"],
                "degradation_level": "agent",
                "errors": state.get("errors", []) + [{"agent": "generator", "error": result.get("error", "generator degraded")}],
                "agent_states": {**state.get("agent_states", {}), "generator": _serialize_agent_state(generator)},
            }

        update: Dict[str, Any] = {
            "report": report,
            "citations": citations,
            "agent_states": {**state.get("agent_states", {}), "generator": _serialize_agent_state(generator)},
        }

        # 重新生成时递增 regenerate_count
        if regenerate_count > 0 or (state.get("review_result") and not state.get("review_result", {}).get("approved", True)):
            update["regenerate_count"] = regenerate_count + 1

        return update
    except Exception as e:
        logger.error(f"generate_node failed: {e}")
        return {
            "report": "综述生成过程中发生错误，请稍后重试。",
            "citations": [],
            "errors": state.get("errors", []) + [{"agent": "generator", "error": str(e)}],
            "degraded": True,
            "agent_states": {**state.get("agent_states", {}), "generator": _serialize_agent_state(generator)},
        }


async def review_node(state: WorkflowState, agent_instances: Dict[str, Any]) -> dict:
    """审核节点：调用 ReviewerAgent 审核生成结果"""
    reviewer = agent_instances.get("reviewer")
    if reviewer is None:
        # Reviewer 不存在时跳过审核，直接标记通过
        logger.warning("ReviewerAgent not found, skipping review")
        return {
            "review_result": {"approved": True, "issues": [], "suggestions": [], "citation_accuracy": 1.0, "fact_accuracy": 1.0},
            "agent_states": {**state.get("agent_states", {}), "reviewer": {"name": "reviewer", "status": "skipped", "error": "Agent not found"}},
        }

    try:
        report = state.get("report", "")
        original_papers = state.get("search_results", [])

        # 构建重试上下文
        regenerate_count = state.get("regenerate_count", 0)
        retry_context = ""
        if regenerate_count > 0:
            prev_review = state.get("review_result") or {}
            issues = prev_review.get("issues", [])
            suggestions = prev_review.get("suggestions", [])
            if issues or suggestions:
                parts: List[str] = []
                if issues:
                    parts.append("上次审核发现的问题：")
                    for issue in issues:
                        parts.append(f"- {issue.get('claim', issue.get('citation', ''))} ({issue.get('error_type', '')})")
                if suggestions:
                    parts.append("修改建议：")
                    for sug in suggestions:
                        parts.append(f"- [{sug.get('section', '')}] {sug.get('suggestion', '')}")
                retry_context = "\n".join(parts)

        result = await reviewer.execute(
            input_data={
                "report": report,
                "original_papers": original_papers,
                "retry_context": retry_context,
            },
            context={"user_profile": state.get("user_profile", {})},
        )

        review_result = {
            "approved": result.get("approved", False),
            "issues": result.get("issues", []),
            "suggestions": result.get("suggestions", []),
            "citation_accuracy": result.get("citation_accuracy", 0.0),
            "fact_accuracy": result.get("fact_accuracy", 0.0),
        }

        # 如果审核不通过，标记需要重新生成（不在此递增 regenerate_count）
        update: Dict[str, Any] = {
            "review_result": review_result,
            "agent_states": {**state.get("agent_states", {}), "reviewer": _serialize_agent_state(reviewer)},
        }

        # Reviewer 降级处理
        if result.get("degraded", False):
            update["degraded"] = True
            update["degraded_agents"] = state.get("degraded_agents", []) + ["reviewer"]
            update["degradation_level"] = "agent"
            update["errors"] = state.get("errors", []) + [{"agent": "reviewer", "error": "审核降级，跳过审核"}]
            # 降级时标记审核通过，不阻塞流程
            review_result["approved"] = True
            update["review_result"] = review_result

        return update
    except Exception as e:
        logger.error(f"review_node failed: {e}")
        return {
            "review_result": {"approved": True, "issues": [], "suggestions": [], "citation_accuracy": 0.0, "fact_accuracy": 0.0},
            "errors": state.get("errors", []) + [{"agent": "reviewer", "error": str(e)}],
            "degraded": True,
            "degraded_agents": state.get("degraded_agents", []) + ["reviewer"],
            "degradation_level": "agent",
            "agent_states": {**state.get("agent_states", {}), "reviewer": _serialize_agent_state(reviewer)},
        }


def _should_degrade_workflow(state: WorkflowState) -> bool:
    """判断是否需要工作流级降级：2个及以上Agent失败时返回True"""
    return len(state.get("errors", [])) >= 2


def build_agent_graph(agent_instances: Dict[str, Any]) -> StateGraph:
    async def _coordinator(state: WorkflowState) -> dict:
        return await coordinator_node(state, agent_instances)

    async def _retrieve(state: WorkflowState) -> dict:
        return await retrieve_node(state, agent_instances)

    async def _analyze(state: WorkflowState) -> dict:
        return await analyze_node(state, agent_instances)

    async def _compare(state: WorkflowState) -> dict:
        return await compare_node(state, agent_instances)

    async def _generate(state: WorkflowState) -> dict:
        return await generate_node(state, agent_instances)

    async def _review(state: WorkflowState) -> dict:
        return await review_node(state, agent_instances)

    def _should_compare(state: WorkflowState) -> str:
        return should_compare(state)

    def _should_review(state: WorkflowState) -> str:
        if should_review(state):
            return "review"
        return "end"

    def _should_regenerate(state: WorkflowState) -> str:
        return should_regenerate(state)

    graph = StateGraph(WorkflowState)

    # 6-Agent 节点
    graph.add_node("coordinator", _coordinator)
    graph.add_node("retrieve", _retrieve)
    graph.add_node("analyze", _analyze)
    graph.add_node("compare", _compare)
    graph.add_node("generate", _generate)
    graph.add_node("review", _review)

    # 入口节点为 coordinator
    graph.set_entry_point("coordinator")

    # 固定边
    graph.add_edge("coordinator", "retrieve")
    graph.add_edge("retrieve", "analyze")
    graph.add_edge("compare", "generate")

    # 条件边：analyzer → [compare | generate]
    graph.add_conditional_edges(
        "analyze",
        _should_compare,
        {"compare": "compare", "generate": "generate"},
    )

    # 条件边：generate → [review | END]
    graph.add_conditional_edges(
        "generate",
        _should_review,
        {"review": "review", "end": END},
    )

    # 条件边：review → [regenerate → generate | END]
    graph.add_conditional_edges(
        "review",
        _should_regenerate,
        {"regenerate": "generate", "end": END},
    )

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
        "requires_compare": False,
        "requires_review": False,
        "coordinator_result": None,
        "degraded_agents": [],
        "degradation_level": "none",
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

        review_result = result_state.get("review_result")
        regenerate_count = result_state.get("regenerate_count", 0)

        return {
            "analysis_id": result_state.get("analysis_id", analysis_id),
            "status": status,
            "report": result_state.get("report"),
            "citations": result_state.get("citations", []),
            "review_result": review_result,
            "regenerate_count": regenerate_count,
            "agent_states": result_state.get("agent_states", {}),
            "errors": result_state.get("errors", []),
            "degraded": is_degraded,
            "degraded_reason": degraded_reason,
            "started_at": result_state.get("started_at"),
            "completed_at": result_state.get("completed_at"),
            "degradation_level": result_state.get("degradation_level", "none"),
            "degraded_agents": result_state.get("degraded_agents", []),
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
            "degradation_level": "workflow",
            "degraded_agents": [],
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
            "degradation_level": "workflow",
            "degraded_agents": [],
        }
