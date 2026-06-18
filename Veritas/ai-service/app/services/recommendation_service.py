"""RecommendationService — task55 推荐服务

基于用户画像和历史分析记录推荐相关论文。
历史记录通过 Java 后端 API 获取（本任务 mock）。
"""
from typing import Dict, List, Optional

from loguru import logger


class RecommendationService:
    """推荐服务 — task55 新增

    工作流：
        1. 获取用户画像（personalization_service）
        2. 获取用户历史分析记录（Java 后端 API，本任务 mock）
        3. 构建候选论文池（历史论文的相似论文，ChromaDB 相似检索）
        4. 调用 reranker.recommend() 排序
        5. 返回 top_k 推荐论文
    """

    def __init__(
        self,
        personalization_service,
        reranker,
        vector_store_service=None,
        settings=None,
    ):
        self.personalization_service = personalization_service
        self.reranker = reranker
        self.vector_store_service = vector_store_service
        self.settings = settings

    async def get_recommended_papers(
        self,
        user_id: str,
        top_k: int = 10,
        user_profile: Optional[dict] = None,
        user_history: Optional[List[dict]] = None,
    ) -> List[dict]:
        """获取推荐论文列表

        Args:
            user_id: 用户 ID
            top_k: 返回数量
            user_profile: 用户画像（可选，为空时调用 personalization_service 获取）
            user_history: 用户历史分析记录（可选，为空时调用 _fetch_user_history）

        Returns:
            推荐论文列表（含 recommendation_score 字段）
        """
        try:
            # 1. 获取用户画像
            if user_profile is None:
                user_profile = await self._fetch_user_profile(user_id)
            if not user_profile:
                logger.warning(f"No user profile for user_id={user_id}")
                return []

            # 2. 获取用户历史
            if user_history is None:
                user_history = await self._fetch_user_history(user_id)

            # 3. 构建候选论文池
            candidates = await self._build_candidates(user_history, top_k=top_k * 5)
            if not candidates:
                logger.info(f"No candidates for user_id={user_id}")
                return []

            # 4. 调用 reranker.recommend 排序
            recommended = await self.reranker.recommend(
                candidates, user_profile, user_history
            )

            return recommended[:top_k]
        except Exception as e:
            logger.warning(f"get_recommended_papers failed: {e}")
            return []

    async def _fetch_user_profile(self, user_id: str) -> dict:
        """从 personalization_service 获取用户画像

        注意：personalization_service 当前无 get_user_profile 方法，
        返回空 dict 由调用方注入。未来可对接 Java 后端用户画像 API。
        """
        if hasattr(self.personalization_service, "get_user_profile"):
            try:
                result = self.personalization_service.get_user_profile(user_id)
                # 兼容同步/异步
                if hasattr(result, "__await__"):
                    return await result
                return result
            except Exception as e:
                logger.warning(f"get_user_profile failed: {e}")
        return {}

    async def _fetch_user_history(self, user_id: str) -> List[dict]:
        """从 Java 后端 API 获取用户历史分析记录

        实际实现应调用 Java 后端 /api/analysis/history?userId=xxx
        本任务返回空列表，由调用方注入 user_history 参数
        """
        # 实际实现示例（未来对接）：
        # async with httpx.AsyncClient() as client:
        #     resp = await client.get(f"{JAVA_BACKEND_URL}/api/analysis/history",
        #                            params={"userId": user_id})
        #     return resp.json().get("data", [])
        return []

    async def _build_candidates(
        self, user_history: List[dict], top_k: int = 50
    ) -> List[dict]:
        """构建候选论文池：历史分析论文的相似论文

        通过 ChromaDB 关键词检索获取历史论文的相似论文。
        """
        if not user_history or self.vector_store_service is None:
            return []

        candidates = []
        seen_ids = set()

        # 最多取最近 5 篇历史论文
        for h in user_history[:5]:
            h_abstract = h.get("abstract") or ""
            h_title = h.get("title") or ""
            # 优先用 abstract 检索，回退到 title
            query_text = h_abstract if h_abstract else h_title
            if not query_text:
                continue
            try:
                if hasattr(self.vector_store_service, "search_by_keywords"):
                    results = await self.vector_store_service.search_by_keywords(
                        query_text=query_text,
                        top_k=top_k,
                    )
                    for r in results:
                        pid = r.get("paperId") or r.get("paper_id")
                        if pid and pid not in seen_ids:
                            seen_ids.add(pid)
                            candidates.append(r)
            except Exception as e:
                logger.warning(f"Similar search failed for history paper: {e}")
                continue

        return candidates
