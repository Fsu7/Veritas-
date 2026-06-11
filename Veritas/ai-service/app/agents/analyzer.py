import json
import re
import uuid
from typing import Any, Dict, List, Optional

from loguru import logger

from app.agents.base import AgentStatus, BaseAgent

DEFAULT_DIMENSIONS = {
    "research_problem",
    "core_method",
    "main_experiments",
    "core_conclusions",
    "limitations",
}

FALLBACK_NOTE = "论文未明确提及"


class AnalyzerAgent(BaseAgent):

    def __init__(
        self,
        llm_service,
        prompt_manager,
        personalization_service=None,
        max_papers: int = 10,
        timeout: int = 30,
        llm_temperature: float = 0.3,
        llm_max_tokens: int = 2048,
    ) -> None:
        super().__init__(
            name="analyzer",
            llm_service=llm_service,
            prompt_manager=prompt_manager,
            timeout=timeout,
        )
        self.personalization_service = personalization_service
        self.max_papers = max_papers
        self.llm_temperature = llm_temperature
        self.llm_max_tokens = llm_max_tokens

    def build_prompt(self, input_data: dict, context: dict) -> str:
        extra_instruction = self._get_personalized_instruction(context)

        return self.prompt_manager.get_prompt(
            "analyzer",
            paper_title=input_data.get("paper_title", ""),
            paper_abstract=input_data.get("paper_abstract", ""),
            extra_instruction=extra_instruction,
        )

    async def _run(
        self, prompt: str, input_data: dict, context: dict
    ) -> dict:
        papers: List[dict] = input_data.get("papers", [])

        if not papers:
            self.state.update_progress(1.0, "No papers to analyze")
            return {
                "analysis_results": [],
                "degraded_papers": [],
                "total_analyzed": 0,
                "extraction_quality": 0.0,
            }

        papers = papers[: self.max_papers]
        total = len(papers)

        analysis_results: List[dict] = []
        degraded_papers: List[dict] = []

        for idx, paper in enumerate(papers):
            paper_id = paper.get("paper_id", f"paper_{idx}")
            progress = (idx + 1) / (total + 1)
            self.state.update_progress(
                progress, f"Analyzing paper {idx + 1}/{total}: {paper.get('title', '')[:50]}"
            )

            try:
                result = await self._analyze_single_paper(paper, context)
                result["paper_id"] = paper_id
                result["degraded"] = False
                analysis_results.append(result)
            except Exception as e:
                logger.warning(f"LLM analysis failed for paper {paper_id}: {e}")
                try:
                    fallback = self._rule_based_extraction(paper)
                    fallback["paper_id"] = paper_id
                    fallback["degraded"] = True
                    fallback["degraded_reason"] = str(e)
                    analysis_results.append(fallback)
                    degraded_papers.append(paper_id)
                except Exception as fallback_err:
                    logger.error(
                        f"Rule-based extraction also failed for {paper_id}: {fallback_err}"
                    )
                    degraded_papers.append(paper_id)

        self.state.update_progress(
            1.0,
            f"Analyzed {len(analysis_results)} papers, {len(degraded_papers)} degraded",
        )

        all_confidences = []
        for ar in analysis_results:
            for dim in DEFAULT_DIMENSIONS:
                dim_data = ar.get(dim)
                if isinstance(dim_data, dict):
                    all_confidences.append(dim_data.get("confidence", 0.0))

        extraction_quality = (
            sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
        )

        return {
            "analysis_results": analysis_results,
            "degraded_papers": degraded_papers,
            "total_analyzed": len(analysis_results),
            "extraction_quality": round(extraction_quality, 4),
        }

    async def _analyze_single_paper(self, paper: dict, context: dict) -> dict:
        paper_input = {
            "paper_title": paper.get("title", ""),
            "paper_abstract": paper.get("abstract", ""),
        }
        prompt = self.build_prompt(paper_input, context)

        llm_output = await self.llm_service.generate(
            prompt,
            max_tokens=self.llm_max_tokens,
            temperature=self.llm_temperature,
        )

        parsed = self._parse_analysis_result(llm_output, paper)
        validated = self._validate_dimensions(parsed, paper)
        return validated

    def _parse_analysis_result(self, llm_output: str, paper: dict = None) -> dict:
        if not llm_output or not llm_output.strip():
            logger.warning("Empty LLM output, using fallback")
            if paper is not None:
                return self._rule_based_extraction(paper)
            return self._empty_dimensions()

        cleaned = llm_output.strip()

        json_match = re.search(r"```json\s*(.*?)\s*```", cleaned, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON from ```json block, retrying")

        code_match = re.search(r"```\s*(.*?)\s*```", cleaned, re.DOTALL)
        if code_match:
            try:
                return json.loads(code_match.group(1))
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON from ``` block, retrying")

        try:
            brace_start = cleaned.find("{")
            brace_end = cleaned.rfind("}")
            if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
                json_candidate = cleaned[brace_start : brace_end + 1]
                return json.loads(json_candidate)
        except json.JSONDecodeError:
            logger.warning("Failed to extract JSON from text, using fallback")

        logger.error(f"All JSON parsing attempts failed for output: {cleaned[:200]}")
        if paper is not None:
            return self._rule_based_extraction(paper)
        return self._empty_dimensions()

    def _validate_dimensions(self, parsed: dict, paper: dict) -> dict:
        result: Dict[str, Any] = {}

        for dim in DEFAULT_DIMENSIONS:
            dim_data = parsed.get(dim)

            if dim_data is None:
                result[dim] = {
                    "summary": FALLBACK_NOTE,
                    "confidence": 0.3,
                    "references": [],
                }
                continue

            if isinstance(dim_data, str):
                result[dim] = {
                    "summary": dim_data if dim_data.strip() else FALLBACK_NOTE,
                    "confidence": 0.5,
                    "references": [],
                }
                continue

            if isinstance(dim_data, dict):
                summary = dim_data.get("summary", "")
                if not isinstance(summary, str) or not summary.strip():
                    summary = FALLBACK_NOTE

                raw_confidence = dim_data.get("confidence", 0.5)
                try:
                    confidence = float(raw_confidence)
                except (TypeError, ValueError):
                    confidence = 0.3
                confidence = max(0.0, min(1.0, confidence))

                references = dim_data.get("references", [])
                if not isinstance(references, list):
                    references = [str(references)] if references else []

                result[dim] = {
                    "summary": summary,
                    "confidence": confidence,
                    "references": references,
                }
                continue

            result[dim] = {
                "summary": FALLBACK_NOTE,
                "confidence": 0.3,
                "references": [],
            }

        paper_title = paper.get("title", "")
        result["paper_title"] = paper_title
        result["analysis_id"] = str(uuid.uuid4())
        result["ai_disclaimer"] = "⚠️ 本分析由 AI 生成，仅供参考"

        return result

    def _rule_based_extraction(self, paper: dict) -> dict:
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")

        abstract_preview = abstract[:300] if abstract else ""

        return {
            "paper_title": title,
            "research_problem": {
                "summary": (
                    f"基于标题'{title}'的规则提取" if not abstract else abstract_preview
                ),
                "confidence": 0.3,
                "references": [f"标题: {title}"] if not abstract else [],
            },
            "core_method": {
                "summary": FALLBACK_NOTE,
                "confidence": 0.3,
                "references": [],
            },
            "main_experiments": {
                "summary": FALLBACK_NOTE,
                "confidence": 0.3,
                "references": [],
            },
            "core_conclusions": {
                "summary": FALLBACK_NOTE,
                "confidence": 0.3,
                "references": [],
            },
            "limitations": {
                "summary": FALLBACK_NOTE,
                "confidence": 0.3,
                "references": [],
            },
            "ai_disclaimer": "⚠️ 本分析由 AI 生成，仅供参考",
            "extraction_quality": 0.1,
        }

    def _get_personalized_instruction(self, context: dict) -> str:
        """优先使用 get_personalization_for_agent，降级到 _get_extra_instruction"""
        user_profile = context.get("user_profile")
        if not user_profile:
            return ""

        if self.personalization_service is not None:
            try:
                instruction = self.personalization_service.get_personalization_for_agent(
                    "analyzer", user_profile
                )
                if instruction:
                    return instruction
            except Exception as e:
                logger.warning(f"Personalization service failed for analyzer: {e}")

        # 降级到旧接口
        return self._get_extra_instruction(context)

    def _get_extra_instruction(self, context: dict) -> str:
        user_profile = context.get("user_profile")

        if user_profile is None:
            return ""

        if self.personalization_service is not None:
            try:
                extra = self.personalization_service.get_extra_instruction(
                    user_profile, agent_name="analyzer"
                )
                if extra:
                    return extra
            except Exception as e:
                logger.warning(f"Personalization service failed: {e}")

        knowledge_level = user_profile.get("knowledge_level")
        if knowledge_level is None:
            return ""

        education_level = user_profile.get("education_level", "master")

        instruction_parts: List[str] = []

        knowledge_instructions = {
            "beginner": "请用通俗解释和类比说明，避免过多专业术语。对于复杂概念，请配合日常例子说明。",
            "intermediate": "请使用标准学术语言，适当引入术语定义。重点分析方法对比和实现细节。",
            "advanced": "请使用专业学术语言，深入分析研究空白和技术细节。讨论前沿趋势和潜在改进方向。",
            "expert": "请使用高度专业的学术语言，提供前沿洞察和创新建议。深入剖析方法论的数学原理和理论依据。",
        }
        instruction = knowledge_instructions.get(
            knowledge_level, knowledge_instructions["intermediate"]
        )
        instruction_parts.append(instruction)

        education_instructions = {
            "undergraduate": "适当补充背景知识，帮助建立知识体系。",
            "master": "侧重方法论对比和实验设计分析。",
            "phd": "关注研究创新点和前沿贡献，分析可扩展的研究方向。",
            "faculty": "关注教学适用性和学科知识体系构建。分析该研究在教学中的应用价值。",
        }
        edu_instruction = education_instructions.get(
            education_level, ""
        )
        if edu_instruction:
            instruction_parts.append(edu_instruction)

        return " ".join(instruction_parts) if instruction_parts else ""

    def _empty_dimensions(self) -> dict:
        return {dim: None for dim in DEFAULT_DIMENSIONS}

    def _fallback_result(self, input_data: dict) -> dict:
        degraded = super()._fallback_result(input_data)

        papers: List[dict] = input_data.get("papers", [])
        fallback_results: List[dict] = []
        degraded_papers: List[str] = []

        for idx, paper in enumerate(papers):
            paper_id = paper.get("paper_id", f"paper_{idx}")
            try:
                result = self._rule_based_extraction(paper)
                result["paper_id"] = paper_id
                fallback_results.append(result)
                degraded_papers.append(paper_id)
            except Exception as e:
                logger.error(f"Fallback extraction failed for {paper_id}: {e}")

        degraded.update({
            "analysis_results": fallback_results,
            "degraded_papers": degraded_papers,
            "total_analyzed": len(fallback_results),
            "extraction_quality": 0.1,
        })
        return degraded

    def _summarize_result(self, result: dict) -> str:
        total = result.get("total_analyzed", 0)
        degraded = len(result.get("degraded_papers", []))
        if degraded > 0:
            return f"Analyzed {total} papers ({degraded} degraded to rule-based)"
        return f"Analyzed {total} papers successfully"
