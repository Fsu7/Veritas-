import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from loguru import logger

from app.core.config import settings


class AgentStatus(str, Enum):
    WAITING = "waiting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentState:
    name: str
    status: AgentStatus = AgentStatus.WAITING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    progress: float = 0.0
    intermediate_result: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "name": self.name,
            "status": self.status.value if isinstance(self.status, AgentStatus) else self.status,
            "progress": self.progress,
        }
        if self.started_at is not None:
            result["started_at"] = self.started_at.isoformat()
        else:
            result["started_at"] = None
        if self.completed_at is not None:
            result["completed_at"] = self.completed_at.isoformat()
        else:
            result["completed_at"] = None
        result["duration_ms"] = self.duration_ms
        result["intermediate_result"] = self.intermediate_result
        result["error"] = self.error
        return result

    def update_progress(self, progress: float, intermediate_result: Optional[str] = None) -> None:
        self.progress = progress
        if intermediate_result is not None:
            self.intermediate_result = intermediate_result


class BaseAgent(ABC):

    def __init__(
        self,
        name: str,
        llm_service,
        prompt_manager,
        timeout: int = None,
    ) -> None:
        self.name = name
        self.llm_service = llm_service
        self.prompt_manager = prompt_manager
        self.state = AgentState(name=name)
        self.timeout = timeout if timeout is not None else settings.AGENT_TIMEOUT

    async def execute(self, input_data: dict, context: dict) -> dict:
        self.state.status = AgentStatus.RUNNING
        self.state.started_at = datetime.now()
        self.state.error = None
        self.state.intermediate_result = None
        logger.warning(f"Agent {self.name} started")

        try:
            prompt = self.build_prompt(input_data, context)

            result = await asyncio.wait_for(
                self._run(prompt, input_data, context),
                timeout=self.timeout,
            )

            self.state.status = AgentStatus.COMPLETED
            self.state.completed_at = datetime.now()
            self.state.duration_ms = int(
                (self.state.completed_at - self.state.started_at).total_seconds() * 1000
            )
            self.state.intermediate_result = self._summarize_result(result)
            logger.info(
                f"Agent {self.name} completed, duration={self.state.duration_ms}ms"
            )

            return result

        except asyncio.TimeoutError:
            self.state.status = AgentStatus.FAILED
            self.state.error = f"Agent {self.name} timed out after {self.timeout}s"
            logger.warning(self.state.error)
            return self._fallback_result(input_data)

        except Exception as e:
            self.state.status = AgentStatus.FAILED
            self.state.error = str(e)
            logger.error(f"Agent {self.name} failed: {e}")
            return self._fallback_result(input_data)

    @abstractmethod
    async def _run(
        self, prompt: str, input_data: dict, context: dict
    ) -> dict:
        pass

    @abstractmethod
    def build_prompt(self, input_data: dict, context: dict) -> str:
        pass

    def _fallback_result(self, input_data: dict) -> dict:
        return {
            "degraded": True,
            "agent": self.name,
            "error": self.state.error,
        }

    def _summarize_result(self, result: dict) -> str:
        return str(result)[:200]
