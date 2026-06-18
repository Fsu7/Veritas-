"""task51 LLM 流式优化测试

验证：
1. 首字节日志（first_token_latency_ms）
2. 流式失败降级为非流式
3. 参数透传（max_tokens/temperature）
4. LLM_STREAM_TIMEOUT 配置
"""
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings


# ===== 测试 1: 首字节日志 =====


class TestFirstTokenLogging:
    def test_first_token_latency_logged(self):
        """首字节延迟被记录到日志"""
        from app.services.llm_service import LLMService

        # Mock provider
        mock_provider = MagicMock()
        mock_provider.mode = "test"

        async def mock_stream(prompt, max_tokens, temperature):
            yield "token1"
            yield "token2"

        mock_provider.generate_stream = mock_stream

        service = LLMService.__new__(LLMService)
        service.active_provider = mock_provider
        service._degradation_state = {"consecutive_failures": {}}

        # 捕获 logger.info 调用
        info_calls = []
        with patch("app.services.llm_service.logger") as mock_logger:
            mock_logger.info = lambda *args, **kwargs: info_calls.append((args, kwargs))

            async def run():
                tokens = []
                async for t in service.generate_stream("test", 100, 0.7):
                    tokens.append(t)
                return tokens

            tokens = asyncio.run(run())

        assert tokens == ["token1", "token2"]
        # 应有首字节日志
        first_token_logs = [
            c for c in info_calls
            if "first_token_latency_ms" in str(c[0])
        ]
        assert len(first_token_logs) >= 1


# ===== 测试 2: 流式失败降级为非流式 =====


class TestStreamDegradation:
    def test_stream_failure_degrades_to_non_stream(self):
        """流式失败时降级为非流式 generate()"""
        from app.services.llm_service import LLMService

        # Mock provider: 流式失败，非流式成功
        mock_provider = MagicMock()
        mock_provider.mode = "test"

        async def failing_stream(prompt, max_tokens, temperature):
            yield "partial"
            raise Exception("Stream interrupted")
            yield "never"  # 不会执行

        mock_provider.generate_stream = failing_stream
        mock_provider.generate = AsyncMock(return_value="full response")

        service = LLMService.__new__(LLMService)
        service.active_provider = mock_provider
        service._degradation_state = {"consecutive_failures": {}}

        # Mock _fallback
        async def mock_fallback():
            pass

        service._fallback = mock_fallback

        async def run():
            tokens = []
            async for t in service.generate_stream("test", 100, 0.7):
                tokens.append(t)
            return tokens

        tokens = asyncio.run(run())

        # 应降级为非流式，yield 完整响应
        assert "full response" in tokens
        # 非流式 generate 被调用
        mock_provider.generate.assert_called_once()

    def test_stream_failure_increments_failure_counter(self):
        """流式失败时递增失败计数器"""
        from app.services.llm_service import LLMService

        mock_provider = MagicMock()
        mock_provider.mode = "test_provider"

        async def failing_stream(prompt, max_tokens, temperature):
            raise Exception("Immediate failure")
            yield "never"

        mock_provider.generate_stream = failing_stream
        mock_provider.generate = AsyncMock(return_value="fallback response")

        service = LLMService.__new__(LLMService)
        service.active_provider = mock_provider
        service._degradation_state = {"consecutive_failures": {}}

        async def mock_fallback():
            pass

        service._fallback = mock_fallback

        async def run():
            tokens = []
            async for t in service.generate_stream("test", 100, 0.7):
                tokens.append(t)
            return tokens

        asyncio.run(run())

        # 失败计数器应递增
        assert service._degradation_state["consecutive_failures"]["test_provider"] >= 1


# ===== 测试 3: 参数透传 =====


class TestParameterPassThrough:
    def test_max_tokens_and_temperature_passed_to_provider(self):
        """max_tokens 和 temperature 透传给 provider"""
        from app.services.llm_service import LLMService

        mock_provider = MagicMock()
        mock_provider.mode = "test"

        captured_args = {}

        async def mock_stream(prompt, max_tokens, temperature):
            captured_args["prompt"] = prompt
            captured_args["max_tokens"] = max_tokens
            captured_args["temperature"] = temperature
            yield "token"

        mock_provider.generate_stream = mock_stream

        service = LLMService.__new__(LLMService)
        service.active_provider = mock_provider
        service._degradation_state = {"consecutive_failures": {}}

        async def run():
            tokens = []
            async for t in service.generate_stream("test prompt", 512, 0.3):
                tokens.append(t)
            return tokens

        asyncio.run(run())

        assert captured_args["prompt"] == "test prompt"
        assert captured_args["max_tokens"] == 512
        assert captured_args["temperature"] == 0.3


# ===== 测试 4: LLM_STREAM_TIMEOUT 配置 =====


class TestStreamTimeoutConfig:
    def test_llm_stream_timeout_default_value(self):
        """LLM_STREAM_TIMEOUT 默认值为 30"""
        settings = Settings()
        assert settings.LLM_STREAM_TIMEOUT == 30

    def test_llm_stream_timeout_from_env(self, monkeypatch):
        """LLM_STREAM_TIMEOUT 可从环境变量覆盖"""
        monkeypatch.setenv("LLM_STREAM_TIMEOUT", "60")
        settings = Settings()
        assert settings.LLM_STREAM_TIMEOUT == 60

    def test_llm_stream_timeout_is_int(self):
        """LLM_STREAM_TIMEOUT 类型为 int"""
        settings = Settings()
        assert isinstance(settings.LLM_STREAM_TIMEOUT, int)
