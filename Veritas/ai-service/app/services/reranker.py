import math
import time
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger


class Reranker:
    # task47: 主权重移至 __init__ 实例属性（从 settings 读取）
    # 次要常量保持类级不变
    YEAR_DECAY_RATE = 0.05
    RECENT_YEAR_THRESHOLD = 3
    TITLE_MATCH_BOOST = 0.1
    KEYWORD_DENSITY_WEIGHT = 0.05
    CITATION_BOOST_WEIGHT = 0.1
    PERSONALIZATION_BOOST = 0.05

    def __init__(self, settings=None, personalization_service=None):
        # task47: 主权重从 settings 读取，默认 0.5/0.3/0.2
        if settings is not None:
            self.weight_rrf = settings.RERANKER_WEIGHT_RRF
            self.weight_field = settings.RERANKER_WEIGHT_FIELD
            self.weight_popularity = settings.RERANKER_WEIGHT_POPULARITY
            # task55: 推荐策略权重
            self.rerank_weight = getattr(settings, "RERANK_WEIGHT", 0.7)
            self.recommendation_weight = getattr(settings, "RECOMMENDATION_WEIGHT", 0.3)
        else:
            self.weight_rrf = 0.5
            self.weight_field = 0.3
            self.weight_popularity = 0.2
            self.rerank_weight = 0.7
            self.recommendation_weight = 0.3

        # task55: 注入 personalization_service 用于 F3.4.6 推荐策略
        self.personalization_service = personalization_service

        # 权重归一化校验（允许 ±0.01 误差，仅警告不阻止初始化）
        total = self.weight_rrf + self.weight_field + self.weight_popularity
        if abs(total - 1.0) > 0.01:
            logger.warning(
                f"Reranker weights sum={total:.4f} != 1.0 "
                f"(rrf={self.weight_rrf}, field={self.weight_field}, "
                f"popularity={self.weight_popularity}), normalization skipped"
            )

    async def rerank(
        self,
        query: str,
        results: List[dict],
        user_profile: Optional[Dict] = None,
    ) -> List[dict]:
        start_time = time.time()
        try:
            if not results:
                logger.info("Rerank called with empty results, returning empty list")
                return []

            current_year = datetime.now().year
            query_keywords = query.lower().split()

            logger.debug(
                "Rerank params: query={}, result_count={}, user_profile={}, current_year={}",
                query,
                len(results),
                user_profile is not None,
                current_year,
            )

            scored_results = []
            for result in results:
                score_rrf = result.get("score", 0.0) or result.get("rrf_score", 0.0)
                title = (result.get("title") or "").lower()
                abstract = (result.get("abstract") or "").lower()
                citation_count = result.get("citation_count", 0) or 0
                paper_year = result.get("year", current_year) or current_year
                venue = (result.get("venue") or "").lower()
                keywords = result.get("keywords") or []

                title_match_boost = 0.0
                for kw in query_keywords:
                    if kw in title:
                        title_match_boost += self.TITLE_MATCH_BOOST

                abstract_len = len(abstract) if abstract else 1
                keyword_count = sum(1 for kw in query_keywords if kw in abstract)
                keyword_density_boost = (keyword_count / abstract_len) * self.KEYWORD_DENSITY_WEIGHT

                citation_boost = min(citation_count / 100, 1.0) * self.CITATION_BOOST_WEIGHT

                years_diff = current_year - paper_year
                if years_diff <= self.RECENT_YEAR_THRESHOLD:
                    score_year = 1.0
                else:
                    score_year = math.exp(-self.YEAR_DECAY_RATE * years_diff)

                field_score = (
                    title_match_boost
                    + keyword_density_boost
                    + citation_boost
                ) * score_year

                popularity_score = min(citation_count / 100, 1.0)

                composite_score = (
                    score_rrf * self.weight_rrf
                    + field_score * self.weight_field
                    + popularity_score * self.weight_popularity
                )

                personalization_boost = 0.0
                if user_profile is not None:
                    research_field = (user_profile.get("research_field") or "").lower()
                    if research_field:
                        if research_field in venue:
                            personalization_boost += self.PERSONALIZATION_BOOST
                        for kw in keywords:
                            if isinstance(kw, str) and research_field in kw.lower():
                                personalization_boost += self.PERSONALIZATION_BOOST
                                break

                # task55: F3.4.6 推荐策略
                # 当 user_profile 非空且有 personalization_service 时，使用推荐分加权
                use_recommendation = (
                    user_profile is not None
                    and self.personalization_service is not None
                    and hasattr(self.personalization_service, "get_recommendation_strategy")
                )

                reranked = dict(result)

                if use_recommendation:
                    # F3.4.6: 最终分 = rerank_score × 0.7 + recommendation_score × 0.3
                    try:
                        recommendation_score = self.personalization_service.get_recommendation_strategy(
                            user_profile, result
                        )
                    except Exception as rec_err:
                        logger.debug(f"get_recommendation_strategy failed: {rec_err}")
                        recommendation_score = 0.0
                    # 归一化 composite_score 到 [0, 1]（粗略归一化）
                    normalized_rerank = min(1.0, max(0.0, composite_score))
                    final_score = (
                        normalized_rerank * self.rerank_weight
                        + recommendation_score * self.recommendation_weight
                    )
                    reranked["rerank_score"] = final_score
                    reranked["recommendation_score"] = recommendation_score
                else:
                    # 向后兼容：user_profile 为空时退化为原逻辑（含 personalization_boost）
                    composite_score += personalization_boost
                    reranked["rerank_score"] = composite_score

                scored_results.append(reranked)

                logger.debug(
                    "Result: paper_id={}, score_rrf={:.4f}, field_score={:.4f}, "
                    "popularity_score={:.4f}, personalization_boost={:.4f}, "
                    "composite={:.4f}",
                    result.get("paper_id"),
                    score_rrf,
                    field_score,
                    popularity_score,
                    personalization_boost,
                    composite_score,
                )

            scored_results.sort(key=lambda x: x["rerank_score"], reverse=True)

            elapsed_ms = (time.time() - start_time) * 1000
            top1_score = scored_results[0]["rerank_score"] if scored_results else 0.0
            logger.info(
                "Rerank completed: input_count={}, output_count={}, top1_score={:.4f}, elapsed_ms={:.1f}",
                len(results),
                len(scored_results),
                top1_score,
                elapsed_ms,
            )

            return scored_results

        except Exception as e:
            logger.warning("Rerank failed, returning original results: {}", e)
            return results

    # ============================================================
    # task55: recommend() 推荐方法
    # ============================================================

    async def recommend(
        self,
        papers: List[dict],
        user_profile: Dict,
        user_history: List[dict],
    ) -> List[dict]:
        """基于用户画像和历史的推荐（task55 新增）

        Args:
            papers: 候选论文列表
            user_profile: 用户画像 4 维度
            user_history: 用户历史分析记录 [{paper_id, title, abstract, ...}]

        Returns:
            按推荐分降序排序的论文列表（含 recommendation_score 字段）
        """
        if not papers:
            return []

        if self.personalization_service is None:
            # 无 personalization_service 时退化为简单排序
            return sorted(papers, key=lambda x: x.get("score", 0.0), reverse=True)

        # 提取历史论文的关键词集合（用于历史相似度加分）
        history_keywords = set()
        history_topic_keywords = [
            "attention", "transformer", "rl", "reinforcement",
            "llm", "language model", "diffusion", "multimodal",
            "vision", "nlp", "cv", "robot", "agent",
        ]
        for h in user_history:
            h_abstract = (h.get("abstract") or "").lower()
            h_title = (h.get("title") or "").lower()
            h_text = h_abstract + " " + h_title
            for kw in history_topic_keywords:
                if kw in h_text:
                    history_keywords.add(kw)

        scored = []
        for paper in papers:
            # 基础推荐分（F3.4.6）
            try:
                rec_score = self.personalization_service.get_recommendation_strategy(
                    user_profile, paper
                )
            except Exception as e:
                logger.debug(f"get_recommendation_strategy failed: {e}")
                rec_score = 0.0

            # 历史相似度加分（最多 +0.2）
            paper_abstract = (paper.get("abstract") or "").lower()
            paper_title = (paper.get("title") or "").lower()
            paper_text = paper_abstract + " " + paper_title
            history_match = sum(1 for kw in history_keywords if kw in paper_text)
            history_boost = min(history_match * 0.05, 0.2)

            final_score = max(0.0, min(1.0, rec_score + history_boost))

            reranked = dict(paper)
            reranked["recommendation_score"] = final_score
            scored.append(reranked)

        scored.sort(key=lambda x: x["recommendation_score"], reverse=True)

        logger.info(
            "Recommend completed: input_count={}, output_count={}, "
            "top1_score={:.4f}, history_keywords={}",
            len(papers),
            len(scored),
            scored[0]["recommendation_score"] if scored else 0.0,
            len(history_keywords),
        )

        return scored
