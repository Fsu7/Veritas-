"""AgentOrchestrator — task25 产出，task30 增强

流式 Agent 编排器，封装 run_workflow_stream() 异步生成器。
每个 Agent 执行过程通过 SSE 事件实时推送状态给 Java 后端。

事件类型：
  - agent_started     : Agent 开始执行
  - agent_state_update: Agent 状态变更（progress 更新）
  - agent_completed    : Agent 正常完成
  - agent_failed       : Agent 执行失败（不中断流）
  - analysis_completed : 全流程结束
  - error              : 错误事件
  - ping               : keep-alive 心跳（task30）

SSE 格式：event: <name>\ndata: <json_string>\n\n

task30 增强：
  - Keep-alive ping：距上次事件 > 15s 时自动 yield ping 事件
  - Last-Event-ID：支持断线重连，跳过已发送事件
  - 客户端断开优雅处理：捕获 asyncio.CancelledError
"""
import asyncio
import json
import time
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

from loguru import logger

from app.agents.base import AgentStatus, BaseAgent
from app.core.config import settings
from app.models.schemas import AnalyzeRequest

# Keep-alive ping 间隔（秒）
PING_INTERVAL = 15


class AgentOrchestrator:
    """流式 Agent 编排器 — task25 产出，task30 增强"""

    NODE_ORDER = ["retriever", "analyzer", "generator"]

    def __init__(
        self,
        agent_instances: Dict[str, BaseAgent],
        analysis_id: str,
        last_event_id: Optional[int] = None,
    ):
        self.agent_instances = agent_instances
        self.analysis_id = analysis_id
        self._event_id = 0
        self._start_time = datetime.now()
        self._errors: List[Dict[str, str]] = []
        self._degraded = False
        self._degraded_reason: Optional[str] = None
        # task30: Last-Event-ID 支持
        self._last_event_id_filter = last_event_id
        # task30: keep-alive ping 时间戳
        self._last_event_time = time.monotonic()

    def _next_event_id(self) -> int:
        self._event_id += 1
        return self._event_id

    def _make_event(self, event_type: str, data: Dict[str, Any]) -> Dict[str, str]:
        """构造 SSE 事件字典，data 字段为 JSON 字符串（camelCase）"""
        return {
            "id": str(self._next_event_id()),
            "event": event_type,
            "data": json.dumps(data, ensure_ascii=False),
        }

    def _should_skip_event(self, event_id: int) -> bool:
        """task30: 判断事件是否应被跳过（Last-Event-ID 过滤）"""
        if self._last_event_id_filter is not None and event_id <= self._last_event_id_filter:
            return True
        return False

    def _maybe_ping(self) -> Optional[Dict[str, str]]:
        """task30: 检查是否需要 yield ping 事件

        距上次事件时间 > PING_INTERVAL 秒时返回 ping 事件，否则返回 None。
        """
        now = time.monotonic()
        if now - self._last_event_time > PING_INTERVAL:
            self._last_event_time = now
            return {
                "id": str(self._next_event_id()),
                "event": "ping",
                "data": "{}",
            }
        return None

    def _update_event_time(self) -> None:
        """task30: 更新上次事件时间戳"""
        self._last_event_time = time.monotonic()

    async def run_workflow_stream(
        self,
        request: AnalyzeRequest,
    ) -> AsyncIterator[Dict[str, str]]:
        """流式工作流主入口，yield SSE 事件字典

        每个 Agent 执行完毕后立即 yield 事件，实现实时推送。
        task30: 支持 keep-alive ping、Last-Event-ID 过滤、客户端断开优雅处理。
        """
        try:
            user_profile_dict = {}
            if request.user_profile is not None:
                user_profile_dict = request.user_profile.model_dump(by_alias=False)

            search_results: list = []
            analysis_results: list = []
            report: Optional[str] = None

            # === Retriever ===
            # task30: 节点执行前检查 ping
            ping = self._maybe_ping()
            if ping and not self._should_skip_event(int(ping["id"])):
                yield ping

            async for event in self._run_node(
                node_name="retriever",
                input_data={"query": request.topic, "top_k": 10, "topic": request.topic},
                context={"user_profile": user_profile_dict},
            ):
                if self._should_skip_event(int(event["id"])):
                    continue
                self._update_event_time()
                yield event

            # 获取 retriever 执行结果
            retriever = self.agent_instances.get("retriever")
            if retriever and retriever.state.status == AgentStatus.COMPLETED:
                search_results = self._get_last_result(retriever, "papers", [])

            # 超时检查
            if self._check_timeout():
                timeout_event = self._make_timeout_event()
                if not self._should_skip_event(int(timeout_event["id"])):
                    self._update_event_time()
                    yield timeout_event
                async for event in self._yield_final(report):
                    if self._should_skip_event(int(event["id"])):
                        continue
                    self._update_event_time()
                    yield event
                return

            # === Analyzer ===
            ping = self._maybe_ping()
            if ping and not self._should_skip_event(int(ping["id"])):
                yield ping

            async for event in self._run_node(
                node_name="analyzer",
                input_data={"papers": search_results},
                context={"user_profile": user_profile_dict},
            ):
                if self._should_skip_event(int(event["id"])):
                    continue
                self._update_event_time()
                yield event

            analyzer = self.agent_instances.get("analyzer")
            if analyzer and analyzer.state.status == AgentStatus.COMPLETED:
                analysis_results = self._get_last_result(analyzer, "analysis_results", [])

            if self._check_timeout():
                timeout_event = self._make_timeout_event()
                if not self._should_skip_event(int(timeout_event["id"])):
                    self._update_event_time()
                    yield timeout_event
                async for event in self._yield_final(report):
                    if self._should_skip_event(int(event["id"])):
                        continue
                    self._update_event_time()
                    yield event
                return

            # === Generator ===
            ping = self._maybe_ping()
            if ping and not self._should_skip_event(int(ping["id"])):
                yield ping

            async for event in self._run_node(
                node_name="generator",
                input_data={
                    "analysis_results": analysis_results,
                    "compare_result": None,
                },
                context={"user_profile": user_profile_dict},
            ):
                if self._should_skip_event(int(event["id"])):
                    continue
                self._update_event_time()
                yield event

            generator = self.agent_instances.get("generator")
            if generator and generator.state.status == AgentStatus.COMPLETED:
                gen_result = self._get_last_result(generator, None, {})
                report = gen_result.get("report") if isinstance(gen_result, dict) else None

            # 最终事件
            async for event in self._yield_final(report):
                if self._should_skip_event(int(event["id"])):
                    continue
                self._update_event_time()
                yield event

        except asyncio.CancelledError:
            # task30: 客户端断开，优雅关闭流
            logger.debug(f"SSE stream cancelled for analysis_id={self.analysis_id}")
            return

    def _get_last_result(self, agent: BaseAgent, key: Optional[str], default: Any) -> Any:
        """从 Agent 的 intermediate_result 中提取上次执行结果

        由于 BaseAgent.execute() 不存储完整结果，我们利用
        agent.state.intermediate_result（截断到200字符的摘要）。
        实际上，我们需要在 _run_node 中保存结果。
        """
        # 使用 _last_result 属性（在 _run_node 中设置）
        result = getattr(agent, '_last_result', default)
        if key is not None and isinstance(result, dict):
            return result.get(key, default)
        return result

    def _check_timeout(self) -> bool:
        elapsed = (datetime.now() - self._start_time).total_seconds()
        return elapsed > settings.AGENT_FULL_TIMEOUT

    def _make_timeout_event(self) -> Dict[str, str]:
        self._degraded = True
        self._degraded_reason = f"全流程超时({settings.AGENT_FULL_TIMEOUT}s)"
        return self._make_event("error", {
            "analysisId": self.analysis_id,
            "errorCode": 408,
            "errorMessage": f"全流程超时({settings.AGENT_FULL_TIMEOUT}s)",
        })

    async def _run_node(
        self,
        node_name: str,
        input_data: dict,
        context: dict,
    ) -> AsyncIterator[Dict[str, str]]:
        """执行单个 Agent 并 yield SSE 事件"""
        agent = self.agent_instances.get(node_name)

        if agent is None:
            yield self._make_event("agent_failed", {
                "agentName": node_name,
                "status": "failed",
                "analysisId": self.analysis_id,
                "errorMessage": f"{node_name} Agent not found",
            })
            yield self._make_event("error", {
                "analysisId": self.analysis_id,
                "errorCode": 500,
                "errorMessage": f"{node_name} Agent not found",
            })
            self._errors.append({"agent": node_name, "error": "Agent not found"})
            self._degraded = True
            return

        # agent_started
        yield self._make_event("agent_started", {
            "agentName": node_name,
            "status": "running",
            "analysisId": self.analysis_id,
            "timestamp": int(datetime.now().timestamp() * 1000),
        })

        # agent_state_update (running)
        yield self._make_event("agent_state_update", {
            "agentName": node_name,
            "status": "running",
            "progress": 0.1,
            "analysisId": self.analysis_id,
            "intermediateResult": "",
            "durationMs": 0,
        })

        try:
            result = await agent.execute(input_data=input_data, context=context)
            # 保存完整结果到 agent 实例上，供后续节点使用
            agent._last_result = result

            state_dict = agent.state.to_dict()

            # 检查 agent 是否在 execute 内部降级（超时/异常被 BaseAgent 捕获）
            if agent.state.status == AgentStatus.FAILED:
                # Agent 内部降级，yield agent_failed + error 事件
                yield self._make_event("agent_failed", {
                    "agentName": state_dict.get("name", node_name),
                    "status": "failed",
                    "analysisId": self.analysis_id,
                    "errorMessage": agent.state.error or "Agent 执行失败",
                    "durationMs": state_dict.get("duration_ms"),
                })
                yield self._make_event("error", {
                    "analysisId": self.analysis_id,
                    "errorCode": 500,
                    "errorMessage": f"{node_name} failed: {agent.state.error or 'unknown'}"[:200],
                })
                self._errors.append({"agent": node_name, "error": agent.state.error or "unknown"})
                self._degraded = True
            else:
                # agent 正常完成
                camel_state = {
                    "agentName": state_dict.get("name", node_name),
                    "status": state_dict.get("status", "completed"),
                    "progress": 1.0,
                    "analysisId": self.analysis_id,
                    "intermediateResult": state_dict.get("intermediate_result") or "",
                    "durationMs": state_dict.get("duration_ms"),
                }
                yield self._make_event("agent_completed", camel_state)

        except Exception as e:
            agent._last_result = agent._fallback_result(input_data)
            state_dict = agent.state.to_dict()
            yield self._make_event("agent_failed", {
                "agentName": node_name,
                "status": "failed",
                "analysisId": self.analysis_id,
                "errorMessage": str(e)[:200],
                "durationMs": state_dict.get("duration_ms"),
            })
            yield self._make_event("error", {
                "analysisId": self.analysis_id,
                "errorCode": 500,
                "errorMessage": f"{node_name} failed: {str(e)[:200]}",
            })
            self._errors.append({"agent": node_name, "error": str(e)})
            self._degraded = True

    async def _yield_final(self, report: Optional[str]) -> AsyncIterator[Dict[str, str]]:
        """yield analysis_completed 最终事件"""
        error_count = len(self._errors)
        if error_count >= 2 or self._degraded:
            final_status = "degraded"
            if error_count == 1 and not self._degraded_reason:
                failed_agent = self._errors[0].get("agent", "unknown")
                self._degraded_reason = f"Agent {failed_agent} 失败，已降级处理"
            elif not self._degraded_reason:
                failed_agents = [e.get("agent", "unknown") for e in self._errors]
                self._degraded_reason = f"多Agent失败({', '.join(failed_agents)})，结果可能不完整"
        else:
            final_status = "completed"

        yield self._make_event("analysis_completed", {
            "analysisId": self.analysis_id,
            "status": final_status,
            "finalReport": report or "（无报告）",
            "degraded": self._degraded,
            "degradedReason": self._degraded_reason,
            "totalDurationMs": int((datetime.now() - self._start_time).total_seconds() * 1000),
        })
