from typing import Optional

from loguru import logger

from app.agents.base import BaseAgent
from app.utils.json_parser import extract_json


class RetrieverAgent(BaseAgent):

    def __init__(
        self,
        llm_service,
        prompt_manager,
        search_service,
        reranker=None,
        personalization_service=None,
        timeout: int = 30,
    ) -> None:
        super().__init__(
            name="retriever",
            llm_service=llm_service,
            prompt_manager=prompt_manager,
            timeout=timeout,
        )
        self.search_service = search_service
        self.reranker = reranker
        self.personalization_service = personalization_service

    def build_prompt(self, input_data: dict, context: dict) -> str:
        top_k = input_data.get("top_k", 10)
        adjusted_top_k = self._adjust_top_k(top_k, context)

        base_prompt = self.prompt_manager.get_prompt(
            "retriever",
            topic=input_data.get("topic", ""),
            top_k=str(adjusted_top_k),
        )

        # 注入个性化指令
        personalization = self._get_personalization_instruction(context)
        if personalization:
            base_prompt += f"\n\n【个性化适配】{personalization}"

        return base_prompt

    async def _run(self, prompt: str, input_data: dict, context: dict) -> dict:
        top_k = input_data.get("top_k", 10)
        topic = input_data.get("topic", "")

        self.state.update_progress(0.2, "Generating search strategy")

        strategy = await self._generate_search_strategy(prompt, topic)

        query = strategy.get("query", topic)
        filters = strategy.get("filters", {})

        self.state.update_progress(0.6, f"Searching for: {query[:50]}")

        results = await self.search_service.hybrid_search(
            query=query, top_k=top_k, filters=filters if filters else None,
        )

        if self.reranker is not None:
            user_profile = context.get("user_profile")
            if user_profile is not None:
                self.state.update_progress(0.8, "Reranking results")
                try:
                    results = await self.reranker.rerank(
                        query, results, user_profile=user_profile,
                    )
                except Exception as e:
                    logger.warning(f"Reranker failed in RetrieverAgent: {e}")

        self.state.update_progress(
            1.0,
            f"Found {len(results)} relevant papers",
        )

        return {
            "papers": results[:top_k],
            "total_found": len(results),
            "search_strategy": strategy,
        }

    async def _generate_search_strategy(self, prompt: str, fallback_topic: str) -> dict:
        try:
            llm_output = await self.llm_service.generate(prompt)
            return self._parse_search_strategy(llm_output, fallback_topic)
        except Exception as e:
            logger.warning(
                f"LLM search strategy generation failed, using fallback: {e}"
            )
            return {"query": fallback_topic, "filters": {}}

    def _parse_search_strategy(self, llm_output: str, fallback_topic: str = "") -> dict:
        parsed = extract_json(llm_output)

        if not isinstance(parsed, dict):
            logger.warning(
                "Failed to parse search strategy JSON, using fallback topic"
            )
            return {"query": fallback_topic, "filters": {}}

        core_keywords = parsed.get("core_keywords", [])
        if core_keywords:
            query = " ".join(str(kw) for kw in core_keywords)
        else:
            query = fallback_topic

        filters = parsed.get("filters", {})
        if not isinstance(filters, dict):
            filters = {}

        return {"query": query, "filters": filters}

    def _adjust_top_k(self, default_top_k: int, context: dict) -> int:
        """根据 knowledge_level 调整检索数量"""
        if self.personalization_service is None:
            return default_top_k
        user_profile = context.get("user_profile")
        if not user_profile:
            return default_top_k
        try:
            profile = self.personalization_service._normalize_profile(user_profile)
            knowledge_level = profile.get("knowledge_level", "intermediate")
            top_k_map = {"beginner": 5, "intermediate": 10, "advanced": 15, "expert": 20}
            return top_k_map.get(knowledge_level, default_top_k)
        except Exception:
            return default_top_k

    def _get_personalization_instruction(self, context: dict) -> str:
        """获取个性化指令片段（降级安全）"""
        if self.personalization_service is None:
            return ""
        user_profile = context.get("user_profile")
        if not user_profile:
            return ""
        try:
            return self.personalization_service.get_personalization_for_agent(
                "retriever", user_profile
            )
        except Exception as e:
            logger.warning(f"Personalization injection failed for retriever: {e}")
            return ""
