import os
from pathlib import Path

import pytest

from app.services.prompt_manager import PromptManager


PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class TestPromptManagerInit:
    def test_default_status(self):
        pm = PromptManager()
        assert pm.status == "initializing"

    def test_default_templates_empty(self):
        pm = PromptManager()
        assert pm.templates == {}

    def test_custom_prompts_dir(self, tmp_path):
        pm = PromptManager(prompts_dir=str(tmp_path))
        assert pm.prompts_dir == tmp_path


class TestPromptManagerLoadTemplates:
    @pytest.mark.asyncio
    async def test_load_six_templates(self):
        pm = PromptManager(prompts_dir=str(PROMPTS_DIR))
        await pm.load_templates()
        assert pm.status == "loaded"
        assert len(pm.templates) == 6
        expected = {"analyzer", "comparer", "coordinator", "generator", "retriever", "reviewer"}
        assert set(pm.templates.keys()) == expected

    @pytest.mark.asyncio
    async def test_load_templates_missing_dir(self, tmp_path):
        missing_dir = tmp_path / "nonexistent"
        pm = PromptManager(prompts_dir=str(missing_dir))
        await pm.load_templates()
        assert pm.status == "loaded"
        assert len(pm.templates) == 0
        assert missing_dir.exists()

    @pytest.mark.asyncio
    async def test_load_templates_from_custom_dir(self, tmp_path):
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "test_agent.txt").write_text("Hello $name", encoding="utf-8")
        pm = PromptManager(prompts_dir=str(prompts_dir))
        await pm.load_templates()
        assert "test_agent" in pm.templates
        assert pm.status == "loaded"


class TestPromptManagerGetPrompt:
    @pytest.mark.asyncio
    async def test_get_prompt_analyzer(self):
        pm = PromptManager(prompts_dir=str(PROMPTS_DIR))
        await pm.load_templates()
        result = pm.get_prompt(
            "analyzer",
            paper_title="Test Paper",
            paper_abstract="Test abstract",
            extra_instruction="",
        )
        assert "Test Paper" in result
        assert "Test abstract" in result

    @pytest.mark.asyncio
    async def test_get_prompt_coordinator(self):
        pm = PromptManager(prompts_dir=str(PROMPTS_DIR))
        await pm.load_templates()
        result = pm.get_prompt(
            "coordinator",
            query="What is RAG?",
            user_profile='{"education_level": "master"}',
        )
        assert "What is RAG?" in result
        assert "master" in result

    @pytest.mark.asyncio
    async def test_get_prompt_safe_substitute(self):
        pm = PromptManager(prompts_dir=str(PROMPTS_DIR))
        await pm.load_templates()
        result = pm.get_prompt("analyzer", paper_title="Test")
        assert "Test" in result

    @pytest.mark.asyncio
    async def test_get_prompt_nonexistent_raises(self):
        pm = PromptManager(prompts_dir=str(PROMPTS_DIR))
        await pm.load_templates()
        with pytest.raises(KeyError, match="Prompt template not found: nonexistent"):
            pm.get_prompt("nonexistent")


class TestPromptManagerListTemplates:
    @pytest.mark.asyncio
    async def test_list_templates_sorted(self):
        pm = PromptManager(prompts_dir=str(PROMPTS_DIR))
        await pm.load_templates()
        names = pm.list_templates()
        assert names == sorted(names)
        assert names == ["analyzer", "comparer", "coordinator", "generator", "retriever", "reviewer"]

    @pytest.mark.asyncio
    async def test_list_templates_empty(self, tmp_path):
        empty_dir = tmp_path / "empty_prompts"
        empty_dir.mkdir()
        pm = PromptManager(prompts_dir=str(empty_dir))
        await pm.load_templates()
        assert pm.list_templates() == []
