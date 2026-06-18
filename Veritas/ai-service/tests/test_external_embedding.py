"""task53 外接 Embedding API 测试

验证：
1. Jina Provider 激活
2. OpenAI Provider 激活
3. DashScope Provider 激活
4. 维度不匹配抛异常
5. Provider 降级
6. OpenAI 降维（1536→1024 + L2归一化）
7. get_model_status 返回 provider 信息
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from app.core.config import Settings
from app.exception import ModelNotLoadedException
from app.services.embedding_service import (
    BaseEmbeddingProvider,
    DashScopeProvider,
    EmbeddingService,
    JinaProvider,
    OpenAIProvider,
)


# ===== Mock 工厂 =====


def _make_settings(**kwargs):
    """构造测试 Settings"""
    defaults = {
        "DASHSCOPE_API_KEY": "",
        "DASHSCOPE_EMBEDDING_MODEL": "text-embedding-v4",
        "DASHSCOPE_EMBEDDING_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "EMBEDDING_PROVIDER": "dashscope",
        "EMBEDDING_DIMENSION": 1024,
        "JINA_API_KEY": "",
        "OPENAI_API_KEY": "",
        "EMBEDDING_MODEL_PATH": "",
        "EMBEDDING_DEVICE": "cpu",
        "EMBEDDING_EXPECTED_DIMENSION": 1024,
    }
    defaults.update(kwargs)
    settings = MagicMock()
    for k, v in defaults.items():
        setattr(settings, k, v)
    return settings


# ===== 测试 1: Jina Provider 激活 =====


class TestJinaProviderActivation:
    def test_jina_provider_available_with_key(self):
        """配置 JINA_API_KEY 后 JinaProvider 可用"""
        settings = _make_settings(JINA_API_KEY="jina_test_key")
        provider = JinaProvider(settings)
        assert provider.is_available() is True
        assert provider.name == "jina"
        assert provider.dimension == 1024

    def test_jina_provider_unavailable_without_key(self):
        """未配置 JINA_API_KEY 时 JinaProvider 不可用"""
        settings = _make_settings(JINA_API_KEY="")
        provider = JinaProvider(settings)
        assert provider.is_available() is False


# ===== 测试 2: OpenAI Provider 激活 =====


class TestOpenAIProviderActivation:
    def test_openai_provider_available_with_key(self):
        """配置 OPENAI_API_KEY 后 OpenAIProvider 可用"""
        settings = _make_settings(OPENAI_API_KEY="sk-test_key")
        provider = OpenAIProvider(settings)
        assert provider.is_available() is True
        assert provider.name == "openai"
        assert provider.dimension == 1024  # 截断后维度

    def test_openai_provider_unavailable_without_key(self):
        """未配置 OPENAI_API_KEY 时 OpenAIProvider 不可用"""
        settings = _make_settings(OPENAI_API_KEY="")
        provider = OpenAIProvider(settings)
        assert provider.is_available() is False


# ===== 测试 3: DashScope Provider 激活 =====


class TestDashScopeProviderActivation:
    def test_dashscope_provider_available_with_key(self):
        """配置 DASHSCOPE_API_KEY 后 DashScopeProvider 可用"""
        settings = _make_settings(DASHSCOPE_API_KEY="sk-dashscope_key")
        provider = DashScopeProvider(settings)
        assert provider.is_available() is True
        assert provider.name == "dashscope"
        assert provider.dimension == 1024

    def test_dashscope_provider_unavailable_without_key(self):
        """未配置 DASHSCOPE_API_KEY 时 DashScopeProvider 不可用"""
        settings = _make_settings(DASHSCOPE_API_KEY="")
        provider = DashScopeProvider(settings)
        assert provider.is_available() is False


# ===== 测试 4: 维度不匹配抛异常 =====


class TestDimensionValidation:
    def test_dimension_mismatch_raises_exception(self):
        """Provider 维度与 EMBEDDING_DIMENSION 不匹配时抛异常"""
        settings = _make_settings(
            DASHSCOPE_API_KEY="sk-test",
            EMBEDDING_DIMENSION=768,  # 期望 768，但 DashScope 是 1024
        )

        service = EmbeddingService(settings)

        with pytest.raises(ModelNotLoadedException) as exc_info:
            asyncio.run(service.load_model())

        assert "dimension" in str(exc_info.value).lower()


# ===== 测试 5: Provider 降级 =====


class TestProviderFallback:
    def test_fallback_to_secondary_provider(self):
        """主 Provider 失败时降级到备用 Provider"""
        settings = _make_settings(
            DASHSCOPE_API_KEY="sk-dashscope",
            JINA_API_KEY="jina_key",
            EMBEDDING_PROVIDER="dashscope",
        )

        service = EmbeddingService(settings)
        asyncio.run(service.load_model())

        # 验证主 Provider 是 dashscope，备用包含 jina
        assert service._provider_name == "dashscope"
        fallback_names = [p.name for p in service.fallback_providers]
        assert "jina" in fallback_names

        # Mock 主 Provider 失败，备用 Provider 成功
        mock_fallback = MagicMock()
        mock_fallback.name = "jina"
        mock_fallback.embed_documents = AsyncMock(
            return_value=np.array([[0.1] * 1024], dtype=np.float32)
        )
        service.fallback_providers = [mock_fallback]

        # Mock 主 Provider 抛异常
        service.active_provider.embed_documents = AsyncMock(
            side_effect=Exception("DashScope API failed")
        )

        result = asyncio.run(service.encode("test text"))

        # 应降级到 jina
        assert result.shape == (1024,)
        mock_fallback.embed_documents.assert_called_once()


# ===== 测试 6: OpenAI 降维 =====


class TestOpenAIDimensionReduction:
    def test_openai_truncates_to_1024_and_normalizes(self):
        """OpenAI 1536维截断前1024 + L2归一化"""
        settings = _make_settings(OPENAI_API_KEY="sk-test")
        provider = OpenAIProvider(settings)

        # Mock httpx 响应
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        # 1536 维向量
        raw_embedding = [0.1] * 1536
        mock_response.json = MagicMock(return_value={
            "data": [{"embedding": raw_embedding}]
        })

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = asyncio.run(provider.embed_query("test"))

        # 应截断到 1024 维
        assert result.shape == (1024,)

        # 应 L2 归一化（范数≈1）
        norm = np.linalg.norm(result)
        assert abs(norm - 1.0) < 0.01


# ===== 测试 7: get_model_status 返回 provider 信息 =====


class TestModelStatus:
    def test_get_model_status_returns_provider_info(self):
        """get_model_status 返回 provider/dimension/fallbacks 信息"""
        settings = _make_settings(
            DASHSCOPE_API_KEY="sk-dashscope",
            JINA_API_KEY="jina_key",
            EMBEDDING_PROVIDER="dashscope",
        )

        service = EmbeddingService(settings)
        asyncio.run(service.load_model())

        status = service.get_model_status()

        assert status["status"] == "loaded_api"
        assert status["provider"] == "dashscope"
        assert status["dimension"] == 1024
        assert isinstance(status["fallbacks"], list)
        assert "jina" in status["fallbacks"]

    def test_get_model_status_when_disabled(self):
        """无可用 Provider 时 status 为 disabled"""
        settings = _make_settings(
            DASHSCOPE_API_KEY="",
            JINA_API_KEY="",
            OPENAI_API_KEY="",
        )

        service = EmbeddingService(settings)
        asyncio.run(service.load_model())

        status = service.get_model_status()
        assert status["status"] == "disabled"
        assert status["provider"] == ""
