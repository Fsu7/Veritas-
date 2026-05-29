import math
import time
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger


class Reranker:
    WEIGHT_RRF = 0.5
    WEIGHT_FIELD = 0.3
    WEIGHT_POPULARITY = 0.2
    YEAR_DECAY_RATE = 0.05
    RECENT_YEAR_THRESHOLD = 3
    TITLE_MATCH_BOOST = 0.1
    KEYWORD_DENSITY_WEIGHT = 0.05
    CITATION_BOOST_WEIGHT = 0.1
    PERSONALIZATION_BOOST = 0.05

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
                    score_rrf * self.WEIGHT_RRF
                    + field_score * self.WEIGHT_FIELD
                    + popularity_score * self.WEIGHT_POPULARITY
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

                composite_score += personalization_boost

                reranked = dict(result)
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
