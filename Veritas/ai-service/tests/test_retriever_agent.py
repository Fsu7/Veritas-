import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.base import AgentStatus, BaseAgent
from app.agents.retriever import RetrieverAgent
from app.agents.tools import (
    TOOL_REGISTRY,
    hybrid_search_tool,
    keyword_search_tool,
    rerank_tool,
    vector_search_tool,
)


def _make_mock_services():
    llm = AsyncMock()
    pm = MagicMock()
    pm.get_prompt = MagicMock(return_value="test prompt for $topic")
    search = AsyncMock()
    reranker = AsyncMock()
    return llm, pm, search, reranker


SAMPLE_PAPERS = [
    {
        "paper_id": "arxiv_2024_001",
        "title": "Multi-Agent Systems Survey",
        "abstract": "A comprehensive survey...",
        "score": 0.92,
        "year": 2024,
        "venue": "ACL",
    },
    {
        "paper_id": "arxiv_2024_002",
        "title": "LangGraph Workflow Design",
        "abstract": "Design patterns for LangGraph...",
        "score": 0.85,
        "year": 2024,
        "venue": "NeurIPS",
    },
]

VALID_STRATEGY_JSON = json.dumps({
    "core_keywords": ["Multi-Agent", "协同决策", "LangGraph"],
    "expanded_keywords": {"Multi-Agent": ["multi-agent system", "MAS"]},
    "search_strategy": "Multi-Agent AND 协同决策",
    "filters": {"year_range": "recent", "venue_type": "top"},
})


class TestRetrieverAgentBuildPrompt:

    def test_build_prompt_renders_template(self):
        llm, pm, search, _ = _make_mock_services()
        agent = RetrieverAgent(llm_service=llm, prompt_manager=pm, search_service=search)

        result = agent.build_prompt({"topic": "AI Agents", "top_k": 10}, {})

        pm.get_prompt.assert_called_once_with("retriever", topic="AI Agents", top_k="10")
        assert result == "test prompt for $topic"

    def test_build_prompt_default_top_k(self):
        llm, pm, search, _ = _make_mock_services()
        agent = RetrieverAgent(llm_service=llm, prompt_manager=pm, search_service=search)

        agent.build_prompt({"topic": "NLP"}, {})

        pm.get_prompt.assert_called_once_with("retriever", topic="NLP", top_k="10")


class TestRetrieverAgentRunSuccess:

    @pytest.mark.asyncio
    async def test_run_success_flow(self):
        llm, pm, search, _ = _make_mock_services()
        llm.generate = AsyncMock(return_value=VALID_STRATEGY_JSON)
        search.hybrid_search = AsyncMock(return_value=SAMPLE_PAPERS)

        agent = RetrieverAgent(llm_service=llm, prompt_manager=pm, search_service=search)
        result = await agent._run("prompt", {"topic": "Multi-Agent", "top_k": 10}, {})

        assert "papers" in result
        assert len(result["papers"]) == 2
        assert result["total_found"] == 2
        assert "search_strategy" in result
        assert agent.state.progress == 1.0

    @pytest.mark.asyncio
    async def test_run_inherits_base_agent(self):
        llm, pm, search, _ = _make_mock_services()
        agent = RetrieverAgent(llm_service=llm, prompt_manager=pm, search_service=search)
        assert isinstance(agent, BaseAgent)
        assert agent.name == "retriever"


class TestRetrieverAgentRunWithReranker:

    @pytest.mark.asyncio
    async def test_run_with_reranker_and_profile(self):
        llm, pm, search, reranker = _make_mock_services()
        llm.generate = AsyncMock(return_value=VALID_STRATEGY_JSON)
        search.hybrid_search = AsyncMock(return_value=SAMPLE_PAPERS)
        reranked = list(reversed(SAMPLE_PAPERS))
        reranker.rerank = AsyncMock(return_value=reranked)

        agent = RetrieverAgent(
            llm_service=llm, prompt_manager=pm,
            search_service=search, reranker=reranker,
        )
        context = {"user_profile": {"research_field": "NLP"}}
        result = await agent._run("prompt", {"topic": "Multi-Agent"}, context)

        reranker.rerank.assert_called_once()
        assert result["papers"] == reranked

    @pytest.mark.asyncio
    async def test_run_without_user_profile_skips_reranker(self):
        llm, pm, search, reranker = _make_mock_services()
        llm.generate = AsyncMock(return_value=VALID_STRATEGY_JSON)
        search.hybrid_search = AsyncMock(return_value=SAMPLE_PAPERS)

        agent = RetrieverAgent(
            llm_service=llm, prompt_manager=pm,
            search_service=search, reranker=reranker,
        )
        await agent._run("prompt", {"topic": "Multi-Agent"}, {})

        reranker.rerank.assert_not_called()


class TestRetrieverAgentLLMFailureDegradation:

    @pytest.mark.asyncio
    async def test_llm_failure_uses_fallback_topic(self):
        llm, pm, search, _ = _make_mock_services()
        llm.generate = AsyncMock(side_effect=Exception("LLM unavailable"))
        search.hybrid_search = AsyncMock(return_value=SAMPLE_PAPERS)

        agent = RetrieverAgent(llm_service=llm, prompt_manager=pm, search_service=search)
        result = await agent._run("prompt", {"topic": "AI Agents"}, {})

        search.hybrid_search.assert_called_once()
        assert result["papers"] == SAMPLE_PAPERS

    @pytest.mark.asyncio
    async def test_llm_timeout_uses_fallback_topic(self):
        llm, pm, search, _ = _make_mock_services()
        llm.generate = AsyncMock(side_effect=TimeoutError("LLM timeout"))
        search.hybrid_search = AsyncMock(return_value=SAMPLE_PAPERS)

        agent = RetrieverAgent(llm_service=llm, prompt_manager=pm, search_service=search)
        result = await agent._run("prompt", {"topic": "AI"}, {})

        assert result["total_found"] == 2


class TestRetrieverAgentSearchFailure:

    @pytest.mark.asyncio
    async def test_search_returns_empty(self):
        llm, pm, search, _ = _make_mock_services()
        llm.generate = AsyncMock(return_value=VALID_STRATEGY_JSON)
        search.hybrid_search = AsyncMock(return_value=[])

        agent = RetrieverAgent(llm_service=llm, prompt_manager=pm, search_service=search)
        result = await agent._run("prompt", {"topic": "nonexistent"}, {})

        assert result["papers"] == []
        assert result["total_found"] == 0


class TestParseSearchStrategyValidJson:

    def test_parse_valid_json(self):
        llm, pm, search, _ = _make_mock_services()
        agent = RetrieverAgent(llm_service=llm, prompt_manager=pm, search_service=search)

        result = agent._parse_search_strategy(VALID_STRATEGY_JSON, "fallback")

        assert "query" in result
        assert "Multi-Agent" in result["query"]
        assert "filters" in result

    def test_parse_json_with_code_block(self):
        llm, pm, search, _ = _make_mock_services()
        agent = RetrieverAgent(llm_service=llm, prompt_manager=pm, search_service=search)

        output = f"```json\n{VALID_STRATEGY_JSON}\n```"
        result = agent._parse_search_strategy(output, "fallback")

        assert "Multi-Agent" in result["query"]


class TestParseSearchStrategyInvalidJson:

    def test_parse_invalid_json_fallback(self):
        llm, pm, search, _ = _make_mock_services()
        agent = RetrieverAgent(llm_service=llm, prompt_manager=pm, search_service=search)

        result = agent._parse_search_strategy("not valid json at all", "AI Agents")

        assert result["query"] == "AI Agents"
        assert result["filters"] == {}

    def test_parse_empty_string_fallback(self):
        llm, pm, search, _ = _make_mock_services()
        agent = RetrieverAgent(llm_service=llm, prompt_manager=pm, search_service=search)

        result = agent._parse_search_strategy("", "fallback topic")

        assert result["query"] == "fallback topic"

    def test_parse_json_without_core_keywords(self):
        llm, pm, search, _ = _make_mock_services()
        agent = RetrieverAgent(llm_service=llm, prompt_manager=pm, search_service=search)

        output = json.dumps({"search_strategy": "test", "filters": {}})
        result = agent._parse_search_strategy(output, "fallback")

        assert result["query"] == "fallback"


class TestVectorSearchTool:

    @pytest.mark.asyncio
    async def test_vector_search_success(self):
        search = AsyncMock()
        search.search = AsyncMock(return_value=SAMPLE_PAPERS)

        result = await vector_search_tool(search, "AI", top_k=20)

        assert len(result) == 2
        search.search.assert_called_once_with(query="AI", top_k=20, filters=None)

    @pytest.mark.asyncio
    async def test_vector_search_failure(self):
        search = AsyncMock()
        search.search = AsyncMock(side_effect=Exception("DB error"))

        result = await vector_search_tool(search, "AI", top_k=20)

        assert result == []


class TestKeywordSearchTool:

    @pytest.mark.asyncio
    async def test_keyword_search_success(self):
        search = AsyncMock()
        search.keyword_search = AsyncMock(return_value=SAMPLE_PAPERS)

        result = await keyword_search_tool(search, "AI", top_k=20)

        assert len(result) == 2
        search.keyword_search.assert_called_once_with(query="AI", top_k=20, filters=None)

    @pytest.mark.asyncio
    async def test_keyword_search_failure(self):
        search = AsyncMock()
        search.keyword_search = AsyncMock(side_effect=Exception("DB error"))

        result = await keyword_search_tool(search, "AI", top_k=20)

        assert result == []


class TestHybridSearchTool:

    @pytest.mark.asyncio
    async def test_hybrid_search_success(self):
        search = AsyncMock()
        search.hybrid_search = AsyncMock(return_value=SAMPLE_PAPERS)

        result = await hybrid_search_tool(search, "AI", top_k=10)

        assert len(result) == 2
        search.hybrid_search.assert_called_once_with(query="AI", top_k=10, filters=None)

    @pytest.mark.asyncio
    async def test_hybrid_search_failure(self):
        search = AsyncMock()
        search.hybrid_search = AsyncMock(side_effect=Exception("Search error"))

        result = await hybrid_search_tool(search, "AI", top_k=10)

        assert result == []


class TestRerankTool:

    @pytest.mark.asyncio
    async def test_rerank_success(self):
        reranker = AsyncMock()
        reranked = list(reversed(SAMPLE_PAPERS))
        reranker.rerank = AsyncMock(return_value=reranked)

        result = await rerank_tool(reranker, "AI", SAMPLE_PAPERS, user_profile={"field": "NLP"})

        assert len(result) == 2
        reranker.rerank.assert_called_once()

    @pytest.mark.asyncio
    async def test_rerank_failure_returns_original(self):
        reranker = AsyncMock()
        reranker.rerank = AsyncMock(side_effect=Exception("Rerank error"))

        result = await rerank_tool(reranker, "AI", SAMPLE_PAPERS)

        assert result == SAMPLE_PAPERS

    @pytest.mark.asyncio
    async def test_rerank_without_profile(self):
        reranker = AsyncMock()
        reranker.rerank = AsyncMock(return_value=SAMPLE_PAPERS)

        result = await rerank_tool(reranker, "AI", SAMPLE_PAPERS)

        reranker.rerank.assert_called_once_with("AI", SAMPLE_PAPERS, user_profile=None)


class TestToolRegistry:

    def test_registry_contains_all_tools(self):
        assert "vector_search" in TOOL_REGISTRY
        assert "keyword_search" in TOOL_REGISTRY
        assert "hybrid_search" in TOOL_REGISTRY
        assert "rerank" in TOOL_REGISTRY

    def test_registry_has_four_entries(self):
        assert len(TOOL_REGISTRY) == 4

    def test_registry_mappings(self):
        assert TOOL_REGISTRY["vector_search"] is vector_search_tool
        assert TOOL_REGISTRY["keyword_search"] is keyword_search_tool
        assert TOOL_REGISTRY["hybrid_search"] is hybrid_search_tool
        assert TOOL_REGISTRY["rerank"] is rerank_tool
