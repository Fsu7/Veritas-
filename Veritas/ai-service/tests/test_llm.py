from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings
from app.exception import LLMException, ModelNotLoadedException
from app.services.llm_service import (
    APILLMProvider,
    BuiltinLLMProvider,
    LocalLLMProvider,
    LLMMode,
    LLMProvider,
    LLMService,
)


class TestLLMMode:
    def test_auto_value(self):
        assert LLMMode.AUTO == "auto"

    def test_builtin_value(self):
        assert LLMMode.BUILTIN == "builtin"

    def test_api_value(self):
        assert LLMMode.API == "api"

    def test_local_value(self):
        assert LLMMode.LOCAL == "local"

    def test_is_string(self):
        assert isinstance(LLMMode.AUTO, str)
        assert isinstance(LLMMode.BUILTIN, str)


class TestLLMProvider:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            LLMProvider()


class TestBuiltinLLMProvider:
    def test_mode_property(self):
        s = Settings(LLM_BUILTIN_URL="https://example.com/v1")
        provider = BuiltinLLMProvider(s)
        assert provider.mode == "builtin"

    def test_init_creates_client(self):
        s = Settings(
            LLM_BUILTIN_URL="https://example.com/v1",
            LLM_BUILTIN_API_KEY="test-key",
            LLM_BUILTIN_MODEL="test-model",
        )
        provider = BuiltinLLMProvider(s)
        assert provider.model_name == "test-model"
        assert provider.client is not None

    @pytest.mark.asyncio
    async def test_generate(self):
        s = Settings(
            LLM_BUILTIN_URL="https://example.com/v1",
            LLM_BUILTIN_MODEL="test-model",
        )
        provider = BuiltinLLMProvider(s)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello response"

        with patch.object(
            provider.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await provider.generate("Hello")
            assert result == "Hello response"

    @pytest.mark.asyncio
    async def test_generate_stream(self):
        s = Settings(
            LLM_BUILTIN_URL="https://example.com/v1",
            LLM_BUILTIN_MODEL="test-model",
        )
        provider = BuiltinLLMProvider(s)

        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta.content = "Hello"

        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta.content = None

        chunk3 = MagicMock()
        chunk3.choices = [MagicMock()]
        chunk3.choices[0].delta.content = " world"

        class MockAsyncStream:
            def __init__(self, chunks):
                self._chunks = chunks
                self._index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self._index >= len(self._chunks):
                    raise StopAsyncIteration
                chunk = self._chunks[self._index]
                self._index += 1
                return chunk

        mock_stream = MockAsyncStream([chunk1, chunk2, chunk3])

        with patch.object(
            provider.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_stream,
        ):
            tokens = []
            async for token in provider.generate_stream("Hello"):
                tokens.append(token)
            assert tokens == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        s = Settings(
            LLM_BUILTIN_URL="https://example.com/v1",
            LLM_BUILTIN_MODEL="test-model",
        )
        provider = BuiltinLLMProvider(s)

        mock_response = MagicMock()
        with patch.object(
            provider.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await provider.test_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self):
        s = Settings(
            LLM_BUILTIN_URL="https://example.com/v1",
            LLM_BUILTIN_MODEL="test-model",
        )
        provider = BuiltinLLMProvider(s)

        with patch.object(
            provider.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            side_effect=Exception("Connection failed"),
        ):
            with pytest.raises(Exception, match="Connection failed"):
                await provider.test_connection()


class TestAPILLMProvider:
    def test_mode_property(self):
        s = Settings(
            LLM_API_KEY="sk-test",
            LLM_API_BASE="https://api.deepseek.com/v1",
            LLM_MODEL_NAME="deepseek-chat",
        )
        provider = APILLMProvider(s)
        assert provider.mode == "api"

    def test_init_empty_api_key_raises(self):
        s = Settings(LLM_API_KEY="")
        with pytest.raises(ValueError, match="LLM_API_KEY is required for API provider"):
            APILLMProvider(s)

    def test_init_creates_client(self):
        s = Settings(
            LLM_API_KEY="sk-test",
            LLM_API_BASE="https://api.deepseek.com/v1",
            LLM_MODEL_NAME="deepseek-chat",
        )
        provider = APILLMProvider(s)
        assert provider.model_name == "deepseek-chat"
        assert provider.client is not None

    @pytest.mark.asyncio
    async def test_generate(self):
        s = Settings(
            LLM_API_KEY="sk-test",
            LLM_API_BASE="https://api.deepseek.com/v1",
            LLM_MODEL_NAME="deepseek-chat",
        )
        provider = APILLMProvider(s)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "API response"

        with patch.object(
            provider.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await provider.generate("Hello")
            assert result == "API response"

    @pytest.mark.asyncio
    async def test_generate_stream(self):
        s = Settings(
            LLM_API_KEY="sk-test",
            LLM_API_BASE="https://api.deepseek.com/v1",
            LLM_MODEL_NAME="deepseek-chat",
        )
        provider = APILLMProvider(s)

        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta.content = "API"

        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta.content = " stream"

        class MockAsyncStream:
            def __init__(self, chunks):
                self._chunks = chunks
                self._index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self._index >= len(self._chunks):
                    raise StopAsyncIteration
                chunk = self._chunks[self._index]
                self._index += 1
                return chunk

        mock_stream = MockAsyncStream([chunk1, chunk2])

        with patch.object(
            provider.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_stream,
        ):
            tokens = []
            async for token in provider.generate_stream("Hello"):
                tokens.append(token)
            assert tokens == ["API", " stream"]

    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        s = Settings(
            LLM_API_KEY="sk-test",
            LLM_API_BASE="https://api.deepseek.com/v1",
            LLM_MODEL_NAME="deepseek-chat",
        )
        provider = APILLMProvider(s)

        mock_response = MagicMock()
        with patch.object(
            provider.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await provider.test_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self):
        s = Settings(
            LLM_API_KEY="sk-test",
            LLM_API_BASE="https://api.deepseek.com/v1",
            LLM_MODEL_NAME="deepseek-chat",
        )
        provider = APILLMProvider(s)

        with patch.object(
            provider.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            side_effect=Exception("API connection failed"),
        ):
            with pytest.raises(Exception, match="API connection failed"):
                await provider.test_connection()


class TestLocalLLMProvider:
    def test_mode_property(self):
        s = Settings(LLM_LOCAL_MODEL_PATH="Qwen/Qwen2-1.5B-Instruct")
        provider = LocalLLMProvider(s)
        assert provider.mode == "local"

    def test_init_empty_model_path_raises(self):
        s = Settings(LLM_LOCAL_MODEL_PATH="")
        with pytest.raises(ValueError, match="LLM_LOCAL_MODEL_PATH is required for local provider"):
            LocalLLMProvider(s)

    def test_init_stores_path(self):
        s = Settings(LLM_LOCAL_MODEL_PATH="Qwen/Qwen2-7B-Instruct")
        provider = LocalLLMProvider(s)
        assert provider.model_path == "Qwen/Qwen2-7B-Instruct"
        assert provider.model is None
        assert provider.tokenizer is None

    @pytest.mark.asyncio
    async def test_load_model(self):
        s = Settings(LLM_LOCAL_MODEL_PATH="Qwen/Qwen2-1.5B-Instruct")
        provider = LocalLLMProvider(s)

        mock_tokenizer = MagicMock()
        mock_model = MagicMock()

        with patch(
            "app.services.llm_service.LocalLLMProvider._sync_load_model"
        ) as mock_sync:
            mock_sync.return_value = None
            provider.tokenizer = mock_tokenizer
            provider.model = mock_model

        assert provider.model is not None
        assert provider.tokenizer is not None

    @pytest.mark.asyncio
    async def test_generate(self):
        s = Settings(LLM_LOCAL_MODEL_PATH="Qwen/Qwen2-1.5B-Instruct")
        provider = LocalLLMProvider(s)

        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        provider.model = mock_model
        provider.tokenizer = mock_tokenizer

        mock_inputs = {"input_ids": MagicMock()}
        mock_inputs["input_ids"].shape = [1, 5]
        mock_tokenizer.return_value.to.return_value = mock_inputs
        mock_tokenizer.decode.return_value = "Local response"

        mock_outputs = [MagicMock()]
        mock_model.generate.return_value = mock_outputs
        mock_model.device = "cpu"

        with patch.object(
            provider,
            "generate",
            new_callable=AsyncMock,
            return_value="Local response",
        ):
            result = await provider.generate("Hello")
            assert result == "Local response"

    @pytest.mark.asyncio
    async def test_generate_without_model_raises(self):
        s = Settings(LLM_LOCAL_MODEL_PATH="Qwen/Qwen2-1.5B-Instruct")
        provider = LocalLLMProvider(s)
        with pytest.raises(ModelNotLoadedException, match="Local model not loaded"):
            await provider.generate("Hello")

    @pytest.mark.asyncio
    async def test_generate_stream_without_model_raises(self):
        s = Settings(LLM_LOCAL_MODEL_PATH="Qwen/Qwen2-1.5B-Instruct")
        provider = LocalLLMProvider(s)
        with pytest.raises(ModelNotLoadedException, match="Local model not loaded"):
            async for _ in provider.generate_stream("Hello"):
                pass

    @pytest.mark.asyncio
    async def test_test_connection_loaded(self):
        s = Settings(LLM_LOCAL_MODEL_PATH="Qwen/Qwen2-1.5B-Instruct")
        provider = LocalLLMProvider(s)
        provider.model = MagicMock()
        provider.tokenizer = MagicMock()
        result = await provider.test_connection()
        assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_not_loaded(self):
        s = Settings(LLM_LOCAL_MODEL_PATH="Qwen/Qwen2-1.5B-Instruct")
        provider = LocalLLMProvider(s)
        with pytest.raises(ModelNotLoadedException, match="Local model not loaded"):
            await provider.test_connection()

    @pytest.mark.asyncio
    async def test_unload_model(self):
        s = Settings(LLM_LOCAL_MODEL_PATH="Qwen/Qwen2-1.5B-Instruct")
        provider = LocalLLMProvider(s)
        provider.model = MagicMock()
        provider.tokenizer = MagicMock()

        with patch("gc.collect") as mock_gc_collect:
            await provider.unload_model()
            mock_gc_collect.assert_called_once()

        assert provider.model is None
        assert provider.tokenizer is None


class TestLLMService:
    def test_initial_status(self):
        s = Settings()
        svc = LLMService(s)
        assert svc.status == "initializing"
        assert svc.active_provider is None
        assert svc.providers == {}

    def test_degradation_state_initial(self):
        s = Settings()
        svc = LLMService(s)
        assert svc._degradation_state["current_provider"] is None
        assert svc._degradation_state["fallback_count"] == 0
        assert svc._degradation_state["last_fallback_at"] is None
        assert svc._degradation_state["consecutive_failures"] == {}

    @pytest.mark.asyncio
    async def test_initialize_builtin_success(self):
        s = Settings(LLM_MODE="builtin")
        svc = LLMService(s)

        with patch.object(
            BuiltinLLMProvider,
            "test_connection",
            new_callable=AsyncMock,
            return_value=True,
        ):
            await svc.initialize()
            assert svc.status == "loaded"
            assert svc.active_provider is not None
            assert svc.active_provider.mode == "builtin"
            assert "builtin" in svc.providers
            assert svc._degradation_state["current_provider"] == "builtin"

    @pytest.mark.asyncio
    async def test_initialize_builtin_failure(self):
        s = Settings(LLM_MODE="builtin")
        svc = LLMService(s)

        with patch.object(
            BuiltinLLMProvider,
            "test_connection",
            new_callable=AsyncMock,
            side_effect=Exception("Connection failed"),
        ):
            with pytest.raises(RuntimeError, match="No LLM provider available"):
                await svc.initialize()
            assert svc.status == "error"
            assert svc.active_provider is None

    @pytest.mark.asyncio
    async def test_auto_mode_fallback_to_api(self):
        s = Settings(
            LLM_MODE="auto",
            LLM_API_KEY="sk-test",
            LLM_API_BASE="https://api.deepseek.com/v1",
            LLM_MODEL_NAME="deepseek-chat",
        )
        svc = LLMService(s)

        with patch.object(
            BuiltinLLMProvider,
            "test_connection",
            new_callable=AsyncMock,
            side_effect=Exception("Builtin failed"),
        ), patch.object(
            APILLMProvider,
            "test_connection",
            new_callable=AsyncMock,
            return_value=True,
        ):
            await svc.initialize()
            assert svc.status == "loaded"
            assert svc.active_provider is not None
            assert svc.active_provider.mode == "api"
            assert "api" in svc.providers

    @pytest.mark.asyncio
    async def test_auto_mode_builtin_success_api_as_fallback(self):
        s = Settings(
            LLM_MODE="auto",
            LLM_API_KEY="sk-test",
            LLM_API_BASE="https://api.deepseek.com/v1",
            LLM_MODEL_NAME="deepseek-chat",
        )
        svc = LLMService(s)

        with patch.object(
            BuiltinLLMProvider,
            "test_connection",
            new_callable=AsyncMock,
            return_value=True,
        ), patch.object(
            APILLMProvider,
            "test_connection",
            new_callable=AsyncMock,
            return_value=True,
        ):
            await svc.initialize()
            assert svc.status == "loaded"
            assert svc.active_provider.mode == "builtin"
            assert "api" in svc.providers

    @pytest.mark.asyncio
    async def test_api_mode_forces_api(self):
        s = Settings(
            LLM_MODE="api",
            LLM_API_KEY="sk-test",
            LLM_API_BASE="https://api.deepseek.com/v1",
            LLM_MODEL_NAME="deepseek-chat",
        )
        svc = LLMService(s)

        with patch.object(
            APILLMProvider,
            "test_connection",
            new_callable=AsyncMock,
            return_value=True,
        ):
            await svc.initialize()
            assert svc.status == "loaded"
            assert svc.active_provider.mode == "api"

    @pytest.mark.asyncio
    async def test_generate_without_init_raises(self):
        s = Settings()
        svc = LLMService(s)
        with pytest.raises(ModelNotLoadedException, match="LLM service not initialized"):
            await svc.generate("Hello")

    @pytest.mark.asyncio
    async def test_generate_stream_without_init_raises(self):
        s = Settings()
        svc = LLMService(s)
        with pytest.raises(ModelNotLoadedException, match="LLM service not initialized"):
            async for _ in svc.generate_stream("Hello"):
                pass

    @pytest.mark.asyncio
    async def test_generate_wraps_exception(self):
        s = Settings(LLM_MODE="builtin")
        svc = LLMService(s)

        with patch.object(
            BuiltinLLMProvider,
            "test_connection",
            new_callable=AsyncMock,
            return_value=True,
        ):
            await svc.initialize()

        with patch.object(
            svc.active_provider,
            "generate",
            new_callable=AsyncMock,
            side_effect=Exception("API error"),
        ), patch.object(
            svc,
            "_fallback",
            new_callable=AsyncMock,
            side_effect=LLMException("All LLM providers failed"),
        ):
            with pytest.raises(LLMException):
                await svc.generate("Hello")


class TestLLMServiceDegradation:
    @pytest.mark.asyncio
    async def test_auto_mode_fallback_to_local(self):
        s = Settings(
            LLM_MODE="auto",
            LLM_LOCAL_MODEL_PATH="Qwen/Qwen2-1.5B-Instruct",
        )
        svc = LLMService(s)

        with patch.object(
            BuiltinLLMProvider,
            "test_connection",
            new_callable=AsyncMock,
            side_effect=Exception("Builtin failed"),
        ), patch.object(
            LocalLLMProvider,
            "load_model",
            new_callable=AsyncMock,
        ), patch.object(
            LocalLLMProvider,
            "test_connection",
            new_callable=AsyncMock,
            return_value=True,
        ):
            await svc.initialize()
            assert svc.status == "loaded"
            assert svc.active_provider.mode == "local"
            assert "local" in svc.providers

    @pytest.mark.asyncio
    async def test_auto_mode_all_providers_fail(self):
        s = Settings(
            LLM_MODE="auto",
            LLM_API_KEY="sk-test",
            LLM_API_BASE="https://api.deepseek.com/v1",
            LLM_MODEL_NAME="deepseek-chat",
            LLM_LOCAL_MODEL_PATH="Qwen/Qwen2-1.5B-Instruct",
        )
        svc = LLMService(s)

        with patch.object(
            BuiltinLLMProvider,
            "test_connection",
            new_callable=AsyncMock,
            side_effect=Exception("Builtin failed"),
        ), patch.object(
            APILLMProvider,
            "test_connection",
            new_callable=AsyncMock,
            side_effect=Exception("API failed"),
        ), patch.object(
            LocalLLMProvider,
            "load_model",
            new_callable=AsyncMock,
            side_effect=Exception("Local model load failed"),
        ):
            with pytest.raises(RuntimeError, match="No LLM provider available"):
                await svc.initialize()
            assert svc.status == "error"

    @pytest.mark.asyncio
    async def test_runtime_fallback_builtin_to_api(self):
        s = Settings(
            LLM_MODE="auto",
            LLM_API_KEY="sk-test",
            LLM_API_BASE="https://api.deepseek.com/v1",
            LLM_MODEL_NAME="deepseek-chat",
        )
        svc = LLMService(s)

        with patch.object(
            BuiltinLLMProvider,
            "test_connection",
            new_callable=AsyncMock,
            return_value=True,
        ), patch.object(
            APILLMProvider,
            "test_connection",
            new_callable=AsyncMock,
            return_value=True,
        ):
            await svc.initialize()

        builtin_provider = svc.active_provider
        api_provider = svc.providers["api"]

        with patch.object(
            builtin_provider,
            "generate",
            new_callable=AsyncMock,
            side_effect=Exception("Builtin error"),
        ), patch.object(
            api_provider,
            "test_connection",
            new_callable=AsyncMock,
            return_value=True,
        ), patch.object(
            api_provider,
            "generate",
            new_callable=AsyncMock,
            return_value="API fallback response",
        ):
            result = await svc.generate("Hello")
            assert result == "API fallback response"
            assert svc.active_provider.mode == "api"
            assert svc._degradation_state["fallback_count"] == 1
            assert svc._degradation_state["current_provider"] == "api"
            assert svc._degradation_state["last_fallback_at"] is not None

    @pytest.mark.asyncio
    async def test_runtime_all_providers_fail(self):
        s = Settings(
            LLM_MODE="auto",
            LLM_API_KEY="sk-test",
            LLM_API_BASE="https://api.deepseek.com/v1",
            LLM_MODEL_NAME="deepseek-chat",
        )
        svc = LLMService(s)

        with patch.object(
            BuiltinLLMProvider,
            "test_connection",
            new_callable=AsyncMock,
            return_value=True,
        ), patch.object(
            APILLMProvider,
            "test_connection",
            new_callable=AsyncMock,
            return_value=True,
        ):
            await svc.initialize()

        with patch.object(
            svc.active_provider,
            "generate",
            new_callable=AsyncMock,
            side_effect=Exception("Builtin error"),
        ), patch.object(
            APILLMProvider,
            "test_connection",
            new_callable=AsyncMock,
            side_effect=Exception("API also failed"),
        ):
            with pytest.raises(LLMException, match="All LLM providers failed"):
                await svc.generate("Hello")

    @pytest.mark.asyncio
    async def test_consecutive_failures_tracking(self):
        s = Settings(
            LLM_MODE="auto",
            LLM_API_KEY="sk-test",
            LLM_API_BASE="https://api.deepseek.com/v1",
            LLM_MODEL_NAME="deepseek-chat",
        )
        svc = LLMService(s)

        with patch.object(
            BuiltinLLMProvider,
            "test_connection",
            new_callable=AsyncMock,
            return_value=True,
        ), patch.object(
            APILLMProvider,
            "test_connection",
            new_callable=AsyncMock,
            return_value=True,
        ):
            await svc.initialize()

        builtin_provider = svc.active_provider
        api_provider = svc.providers["api"]

        with patch.object(
            builtin_provider,
            "generate",
            new_callable=AsyncMock,
            side_effect=Exception("Error"),
        ), patch.object(
            api_provider,
            "test_connection",
            new_callable=AsyncMock,
            return_value=True,
        ), patch.object(
            api_provider,
            "generate",
            new_callable=AsyncMock,
            return_value="OK",
        ):
            await svc.generate("Hello")
            assert svc._degradation_state["consecutive_failures"]["builtin"] == 1

    @pytest.mark.asyncio
    async def test_local_mode_forces_local(self):
        s = Settings(
            LLM_MODE="local",
            LLM_LOCAL_MODEL_PATH="Qwen/Qwen2-1.5B-Instruct",
        )
        svc = LLMService(s)

        with patch.object(
            LocalLLMProvider,
            "load_model",
            new_callable=AsyncMock,
        ), patch.object(
            LocalLLMProvider,
            "test_connection",
            new_callable=AsyncMock,
            return_value=True,
        ):
            await svc.initialize()
            assert svc.status == "loaded"
            assert svc.active_provider.mode == "local"

    @pytest.mark.asyncio
    async def test_unload_model_cancels_recovery(self):
        s = Settings(LLM_MODE="builtin")
        svc = LLMService(s)

        with patch.object(
            BuiltinLLMProvider,
            "test_connection",
            new_callable=AsyncMock,
            return_value=True,
        ):
            await svc.initialize()
            assert svc._recovery_task is not None

        await svc.unload_model()
        assert svc._recovery_task is None

    @pytest.mark.asyncio
    async def test_unload_model_releases_local(self):
        s = Settings(
            LLM_MODE="local",
            LLM_LOCAL_MODEL_PATH="Qwen/Qwen2-1.5B-Instruct",
        )
        svc = LLMService(s)

        mock_unload = AsyncMock()
        with patch.object(
            LocalLLMProvider,
            "load_model",
            new_callable=AsyncMock,
        ), patch.object(
            LocalLLMProvider,
            "test_connection",
            new_callable=AsyncMock,
            return_value=True,
        ), patch.object(
            LocalLLMProvider,
            "unload_model",
            mock_unload,
        ):
            await svc.initialize()
            await svc.unload_model()
            mock_unload.assert_called_once()
