"""Mock 失败 LLM Provider — Task29 降级机制验证测试

提供以下 fixture：
- failing_builtin_provider：generate() 抛 ConnectionError 的 mock builtin provider
- failing_all_providers：3 个 provider 都失败的 mock
- timeout_agent：execute() 会 asyncio.sleep(31) 模拟超时的 Agent
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.base import BaseAgent
from app.services.llm_service import LLMProvider


@pytest.fixture
def failing_builtin_provider():
    """generate() 抛 ConnectionError 的 mock builtin provider"""
    provider = MagicMock(spec=LLMProvider)
    provider.mode = "builtin"
    provider.generate = AsyncMock(
        side_effect=ConnectionError("Builtin provider connection failed")
    )
    provider.generate_stream = AsyncMock(
        side_effect=ConnectionError("Builtin provider connection failed")
    )
    provider.test_connection = AsyncMock(
        side_effect=ConnectionError("Builtin provider connection failed")
    )
    return provider


@pytest.fixture
def failing_all_providers():
    """3 个 provider 都失败的 mock"""
    builtin = MagicMock(spec=LLMProvider)
    builtin.mode = "builtin"
    builtin.generate = AsyncMock(
        side_effect=ConnectionError("Builtin provider connection failed")
    )
    builtin.generate_stream = AsyncMock(
        side_effect=ConnectionError("Builtin provider connection failed")
    )
    builtin.test_connection = AsyncMock(
        side_effect=ConnectionError("Builtin provider connection failed")
    )

    api = MagicMock(spec=LLMProvider)
    api.mode = "api"
    api.generate = AsyncMock(
        side_effect=ConnectionError("API provider connection failed")
    )
    api.generate_stream = AsyncMock(
        side_effect=ConnectionError("API provider connection failed")
    )
    api.test_connection = AsyncMock(
        side_effect=ConnectionError("API provider connection failed")
    )

    local = MagicMock(spec=LLMProvider)
    local.mode = "local"
    local.generate = AsyncMock(
        side_effect=RuntimeError("Local model not loaded")
    )
    local.generate_stream = AsyncMock(
        side_effect=RuntimeError("Local model not loaded")
    )
    local.test_connection = AsyncMock(
        side_effect=RuntimeError("Local model not loaded")
    )

    return {"builtin": builtin, "api": api, "local": local}


class SlowAgent(BaseAgent):
    """模拟超时的 Agent，_run() 会 sleep 31s"""

    def build_prompt(self, input_data: dict, context: dict) -> str:
        return "test prompt"

    async def _run(self, prompt: str, input_data: dict, context: dict) -> dict:
        await asyncio.sleep(31)  # 超过默认 AGENT_TIMEOUT(30s)
        return {"result": "should not reach here"}


@pytest.fixture
def timeout_agent():
    """execute() 会 asyncio.sleep(31) 模拟超时的 Agent

    timeout 设为 0.5s，_run sleeps 31s，触发 asyncio.TimeoutError
    """
    return SlowAgent(
        name="analyzer",
        llm_service=MagicMock(),
        prompt_manager=MagicMock(),
        timeout=0.5,
    )
