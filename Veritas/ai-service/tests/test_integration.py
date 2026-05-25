from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings
from app.services.prompt_manager import PromptManager


PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class TestPromptManagerIntegration:
    @pytest.mark.asyncio
    async def test_prompt_manager_loads_all_templates(self):
        pm = PromptManager(prompts_dir=str(PROMPTS_DIR))
        await pm.load_templates()
        assert pm.status == "loaded"
        assert len(pm.templates) == 6

    @pytest.mark.asyncio
    async def test_all_agents_have_templates(self):
        pm = PromptManager(prompts_dir=str(PROMPTS_DIR))
        await pm.load_templates()
        agent_names = ["coordinator", "retriever", "analyzer", "comparer", "generator", "reviewer"]
        for name in agent_names:
            assert name in pm.templates, f"Missing template: {name}"

    @pytest.mark.asyncio
    async def test_analyzer_prompt_variable_substitution(self):
        pm = PromptManager(prompts_dir=str(PROMPTS_DIR))
        await pm.load_templates()
        result = pm.get_prompt(
            "analyzer",
            paper_title="Attention Is All You Need",
            paper_abstract="We propose a new network architecture based on attention",
            extra_instruction="Focus on the transformer architecture",
        )
        assert "Attention Is All You Need" in result
        assert "attention" in result
        assert "transformer architecture" in result

    @pytest.mark.asyncio
    async def test_generator_prompt_variable_substitution(self):
        pm = PromptManager(prompts_dir=str(PROMPTS_DIR))
        await pm.load_templates()
        result = pm.get_prompt(
            "generator",
            personalization="请使用通俗语言解释",
            analysis_data="[论文分析数据]",
            comparison_data="[对比分析数据]",
        )
        assert "通俗语言" in result
        assert "论文分析数据" in result
        assert "对比分析数据" in result

    @pytest.mark.asyncio
    async def test_reviewer_prompt_variable_substitution(self):
        pm = PromptManager(prompts_dir=str(PROMPTS_DIR))
        await pm.load_templates()
        result = pm.get_prompt(
            "reviewer",
            report_content="这是一篇关于RAG的综述",
            original_papers="[原始论文数据]",
        )
        assert "RAG" in result
        assert "原始论文数据" in result


class TestServiceHealthIntegration:
    @pytest.mark.asyncio
    async def test_health_check_structure(self):
        from app.main import app
        from httpx import ASGITransport, AsyncClient

        with patch(
            "app.core.events.embedding_service", MagicMock(status="loaded")
        ), patch(
            "app.core.events.vector_store_service", MagicMock(status="connected")
        ), patch(
            "app.core.events.llm_service", MagicMock(status="loaded")
        ), patch(
            "app.core.events.prompt_manager", MagicMock(status="loaded")
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/health")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "UP"
                assert "llm" in data
                assert "embedding" in data
                assert "chroma" in data
                assert "prompts" in data
