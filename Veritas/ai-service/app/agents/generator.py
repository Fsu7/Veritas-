import json
import re
from typing import Any, Dict, List, Optional

from loguru import logger

from app.agents.base import AgentStatus, BaseAgent

REQUIRED_SECTIONS = ["引言", "研究现状", "方法对比", "研究趋势", "参考文献"]

TERM_DENSITY_TARGET = {
    "beginner": 0.05,
    "intermediate": 0.20,
    "advanced": 0.40,
    "expert": 0.50,
}

DIFFICULTY_MAP = {
    "beginner": 1,
    "intermediate": 2,
    "advanced": 3,
    "expert": 4,
}

STYLE_MAP = {
    "simple": "casual",
    "balanced": "standard",
    "technical": "formal",
}

EDUCATION_ADAPTATION = {
    "undergraduate": "适当补充背景知识，使用类比说明",
    "master": "侧重方法论对比和实验设计分析",
    "phd": "关注创新点和前沿贡献，分析可扩展方向",
    "faculty": "关注教学适用性和知识体系构建",
}

FIELD_EMPHASIS = {
    "NLP": "侧重自然语言处理相关方法和应用",
    "CV": "侧重计算机视觉相关方法和应用",
    "RL": "侧重强化学习相关方法和应用",
    "多模态": "侧重多模态融合相关方法和应用",
}

ACADEMIC_TERMS = [
    "attention mechanism",
    "gradient descent",
    "fine-tuning",
    "pre-training",
    "transformer",
    "neural network",
    "deep learning",
    "machine learning",
    "reinforcement learning",
    "natural language processing",
    "computer vision",
    "convolutional neural network",
    "recurrent neural network",
    "generative adversarial network",
    "variational autoencoder",
    "backpropagation",
    "stochastic gradient descent",
    "batch normalization",
    "dropout",
    "learning rate",
    "loss function",
    "overfitting",
    "underfitting",
    "regularization",
    "cross-validation",
    "feature extraction",
    "embedding",
    "tokenization",
    "semantic segmentation",
    "object detection",
    "image classification",
    "sequence-to-sequence",
    "self-attention",
    "multi-head attention",
    "positional encoding",
    "beam search",
    "temperature sampling",
    "top-k sampling",
    "perplexity",
    "bleu score",
    "rouge score",
    "f1 score",
    "precision",
    "recall",
    "accuracy",
    "auc",
    "roc curve",
    "hyperparameter",
    "epoch",
    "batch size",
]

AI_DISCLAIMER = "⚠️ 本内容由 AI 生成，仅供参考"

MAX_ANALYSIS_CHARS = 8000  # Prompt 中分析结果最大字符数（约 2000 tokens）

_CAMEL_TO_SNAKE_MAP = {
    "educationLevel": "education_level",
    "knowledgeLevel": "knowledge_level",
    "preferredStyle": "preferred_style",
    "researchField": "research_field",
}

_AUTHOR_YEAR_PATTERN = re.compile(
    r"\[([A-Z][a-z]+(?:\s+et\s+al\.)?,\s*\d{4})\]"
)
_NUMERIC_CITATION_PATTERN = re.compile(r"\[(\d+)\]")


class GeneratorAgent(BaseAgent):

    def __init__(
        self,
        llm_service,
        prompt_manager,
        personalization_service=None,
        timeout: int = 30,
        llm_temperature: float = 0.7,
        llm_max_tokens: int = 4096,
    ) -> None:
        super().__init__(
            name="generator",
            llm_service=llm_service,
            prompt_manager=prompt_manager,
            timeout=timeout,
        )
        self.personalization_service = personalization_service
        self.llm_temperature = llm_temperature
        self.llm_max_tokens = llm_max_tokens

    def build_prompt(self, input_data: dict, context: dict) -> str:
        analysis_results = input_data.get("analysis_results", [])
        compare_result = input_data.get("compare_result")

        analysis_data = self._truncate_analysis_for_prompt(analysis_results)
        comparison_data = (
            json.dumps(compare_result, ensure_ascii=False)
            if compare_result
            else "无"
        )

        user_profile = context.get("user_profile")
        personalization = self._build_personalization_block(user_profile)
        user_profile_summary = self._build_user_profile_summary(user_profile)

        return self.prompt_manager.get_prompt(
            "generator",
            personalization=personalization,
            analysis_data=analysis_data,
            comparison_data=comparison_data,
            user_profile_summary=user_profile_summary,
        )

    async def _run(
        self, prompt: str, input_data: dict, context: dict
    ) -> dict:
        analysis_results: List[dict] = input_data.get("analysis_results", [])
        compare_result = input_data.get("compare_result")
        user_profile = context.get("user_profile") or {}

        self.state.update_progress(0.2, "Building personalized prompt")

        try:
            full_prompt = self.build_prompt(input_data, context)
        except Exception as e:
            logger.warning(f"build_prompt failed, using raw prompt: {e}")
            full_prompt = prompt

        self.state.update_progress(0.4, "Generating literature review")

        try:
            llm_output = await self.llm_service.generate(
                full_prompt,
                max_tokens=self.llm_max_tokens,
                temperature=self.llm_temperature,
            )
        except Exception as e:
            logger.warning(f"LLM generation failed: {e}")
            fallback_report = self._generate_fallback_report(
                analysis_results, compare_result
            )
            return {
                "degraded": True,
                "agent": self.name,
                "report": fallback_report,
                "citation_list": [],
                "term_density_actual": 0.0,
                "personalization_applied": self._build_personalization_applied(
                    user_profile
                ),
                "error": str(e),
            }

        if not llm_output or not llm_output.strip():
            logger.warning("LLM returned empty output, using fallback report")
            fallback_report = self._generate_fallback_report(
                analysis_results, compare_result
            )
            return {
                "degraded": True,
                "agent": self.name,
                "report": fallback_report,
                "citation_list": [],
                "term_density_actual": 0.0,
                "personalization_applied": self._build_personalization_applied(
                    user_profile
                ),
                "error": "LLM returned empty output",
            }

        self.state.update_progress(0.7, "Extracting citations and validating")

        report = llm_output

        validation = self._validate_report(report)
        report = validation["report"]

        citation_list = self._extract_citations(report, analysis_results)

        knowledge_level = self._get_profile_field(
            user_profile, "knowledge_level", "intermediate"
        )
        term_density_actual = self._calculate_term_density(
            report, knowledge_level
        )

        personalization_applied = self._build_personalization_applied(
            user_profile
        )

        if AI_DISCLAIMER not in report:
            report = report.rstrip() + "\n\n" + AI_DISCLAIMER

        self.state.update_progress(1.0, "Report generation completed")

        return {
            "report": report,
            "citation_list": citation_list,
            "term_density_actual": term_density_actual,
            "personalization_applied": personalization_applied,
        }

    def _build_personalization_block(self, user_profile: Optional[dict]) -> str:
        if user_profile is None:
            return self._default_personalization_block()

        if self.personalization_service is not None:
            try:
                # 优先使用 get_personalization_for_agent 获取个性化指令
                agent_instruction = self.personalization_service.get_personalization_for_agent(
                    "generator", user_profile
                )
                block = self.personalization_service.get_personalization_block(
                    user_profile
                )
                if block:
                    # 如果有 agent 特定指令，追加到个性化块末尾
                    if agent_instruction:
                        block += f"\n【Agent个性化指令】{agent_instruction}"
                    return block
            except Exception as e:
                logger.warning(
                    f"Personalization service failed, using built-in mapping: {e}"
                )

        profile = self._normalize_profile(user_profile)
        education_level = profile.get("education_level", "master")
        knowledge_level = profile.get("knowledge_level", "intermediate")
        preferred_style = profile.get("preferred_style", "balanced")
        research_field = profile.get("research_field", "")

        parts: List[str] = []

        edu_adapt = EDUCATION_ADAPTATION.get(
            education_level, EDUCATION_ADAPTATION["master"]
        )
        parts.append(f"【学历适配】{edu_adapt}")

        target = TERM_DENSITY_TARGET.get(
            knowledge_level, TERM_DENSITY_TARGET["intermediate"]
        )
        parts.append(f"【术语密度目标】{int(target * 100)}%")

        style_guide = STYLE_MAP.get(preferred_style, STYLE_MAP["balanced"])
        parts.append(f"【写作风格】{style_guide}")

        if research_field:
            field_emphasis = FIELD_EMPHASIS.get(research_field, "")
            if field_emphasis:
                parts.append(f"【领域侧重】{field_emphasis}")

        return "\n".join(parts)

    def _default_personalization_block(self) -> str:
        return (
            f"【学历适配】{EDUCATION_ADAPTATION['master']}\n"
            f"【术语密度目标】{int(TERM_DENSITY_TARGET['intermediate'] * 100)}%\n"
            f"【写作风格】{STYLE_MAP['balanced']}"
        )

    def _build_user_profile_summary(self, user_profile: Optional[dict]) -> str:
        if user_profile is None:
            return "硕士/中级知识水平/均衡风格"

        if self.personalization_service is not None:
            try:
                summary = self.personalization_service._build_user_profile_summary(
                    user_profile
                )
                if summary:
                    return summary
            except Exception as e:
                logger.warning(
                    f"Personalization service summary failed: {e}"
                )

        profile = self._normalize_profile(user_profile)
        education_level = profile.get("education_level", "master")
        knowledge_level = profile.get("knowledge_level", "intermediate")
        preferred_style = profile.get("preferred_style", "balanced")
        research_field = profile.get("research_field", "")

        edu_labels = {
            "undergraduate": "本科",
            "master": "硕士",
            "phd": "博士",
            "faculty": "教师",
        }
        know_labels = {
            "beginner": "入门",
            "intermediate": "中级",
            "advanced": "进阶",
            "expert": "专家",
        }
        style_labels = {
            "simple": "通俗",
            "balanced": "均衡",
            "technical": "专业",
        }

        parts = [edu_labels.get(education_level, "硕士")]
        if research_field:
            parts.append(f"{research_field}方向")
        parts.append(f"{know_labels.get(knowledge_level, '中级')}知识水平")
        parts.append(f"{style_labels.get(preferred_style, '均衡')}风格")

        return "/".join(parts)

    def _extract_citations(
        self, report: str, analysis_results: List[dict]
    ) -> List[dict]:
        citation_list: List[dict] = []

        try:
            author_year_matches = _AUTHOR_YEAR_PATTERN.findall(report)
            for idx, match in enumerate(author_year_matches):
                paper_id = self._map_citation_to_paper(match, analysis_results)
                citation_list.append(
                    {"index": idx + 1, "paper_id": paper_id, "citation": match}
                )

            numeric_matches = _NUMERIC_CITATION_PATTERN.findall(report)
            offset = len(citation_list)
            for idx, match in enumerate(numeric_matches):
                num = int(match)
                paper_id = None
                if 1 <= num <= len(analysis_results):
                    paper_id = analysis_results[num - 1].get("paper_id")
                citation_list.append(
                    {
                        "index": offset + idx + 1,
                        "paper_id": paper_id,
                        "citation": f"[{match}]",
                    }
                )
        except Exception as e:
            logger.warning(f"Citation extraction failed: {e}")
            return []

        return citation_list

    def _map_citation_to_paper(
        self, citation: str, analysis_results: List[dict]
    ) -> Optional[str]:
        for result in analysis_results:
            title = result.get("paper_title", "").lower()
            if not title:
                continue
            citation_lower = citation.lower()
            author_part = citation_lower.split(",")[0].strip()
            if author_part in title:
                return result.get("paper_id")
        return None

    def _validate_report(self, report: str) -> dict:
        missing_sections: List[str] = []
        found_sections: List[str] = []

        for section in REQUIRED_SECTIONS:
            pattern = re.compile(
                rf"##\s*\d*\s*{re.escape(section)}", re.IGNORECASE
            )
            if pattern.search(report):
                found_sections.append(section)
            else:
                missing_sections.append(section)

        is_valid = len(missing_sections) == 0

        patched_report = report
        if missing_sections:
            logger.warning(
                f"Missing sections in report: {missing_sections}"
            )
            reference_pos = patched_report.rfind("##")
            if reference_pos != -1:
                insert_pos = reference_pos
            else:
                insert_pos = len(patched_report)

            fallback_parts: List[str] = []
            for section in missing_sections:
                fallback_parts.append(
                    f"\n## {section}\n\n（该章节内容待补充）\n"
                )

            insertion = "".join(fallback_parts)
            patched_report = (
                patched_report[:insert_pos]
                + insertion
                + patched_report[insert_pos:]
            )

        return {
            "is_valid": is_valid,
            "missing_sections": missing_sections,
            "report": patched_report,
        }

    def _calculate_term_density(
        self, report: str, knowledge_level: str
    ) -> float:
        if not report or not report.strip():
            return 0.0

        words = report.lower().split()
        total_words = len(words)
        if total_words == 0:
            return 0.0

        report_lower = report.lower()
        term_count = 0
        for term in ACADEMIC_TERMS:
            term_count += report_lower.count(term.lower())

        density = min(term_count / total_words, 1.0)
        return round(density, 4)

    def _generate_fallback_report(
        self,
        analysis_results: List[dict],
        compare_result: Optional[dict] = None,
    ) -> str:
        if not analysis_results:
            return (
                "## 引言\n\n暂无分析数据。\n\n"
                "## 研究现状\n\n暂无数据。\n\n"
                "## 方法对比\n\n暂无数据。\n\n"
                "## 研究趋势\n\n暂无数据。\n\n"
                "## 参考文献\n\n暂无。\n\n"
                + AI_DISCLAIMER
            )

        sections: List[str] = []

        sections.append("## 引言\n")
        sections.append(
            f"本综述基于{len(analysis_results)}篇论文的分析数据，"
            "对相关研究领域的现状、方法和发展趋势进行梳理。\n"
        )

        sections.append("\n## 研究现状\n")
        for idx, result in enumerate(analysis_results):
            title = result.get("paper_title", f"论文{idx + 1}")
            problem = self._extract_dimension_summary(
                result, "research_problem"
            )
            sections.append(f"\n**{title}**：{problem}\n")

        sections.append("\n## 方法对比\n")
        if compare_result and isinstance(compare_result, dict):
            summary = compare_result.get("summary", "")
            if summary:
                sections.append(f"\n{summary}\n")
            else:
                for idx, result in enumerate(analysis_results):
                    title = result.get("paper_title", f"论文{idx + 1}")
                    method = self._extract_dimension_summary(
                        result, "core_method"
                    )
                    sections.append(f"\n**{title}**：{method}\n")
        else:
            for idx, result in enumerate(analysis_results):
                title = result.get("paper_title", f"论文{idx + 1}")
                method = self._extract_dimension_summary(
                    result, "core_method"
                )
                sections.append(f"\n**{title}**：{method}\n")

        sections.append("\n## 研究趋势\n")
        trend_parts: List[str] = []
        for result in analysis_results:
            conclusion = self._extract_dimension_summary(
                result, "core_conclusions"
            )
            if conclusion:
                trend_parts.append(conclusion)
        if trend_parts:
            sections.append(
                "基于以上研究，该领域的主要发展趋势包括："
                + "；".join(trend_parts)
                + "。\n"
            )
        else:
            sections.append("暂无足够数据推断研究趋势。\n")

        sections.append("\n## 参考文献\n")
        for idx, result in enumerate(analysis_results):
            title = result.get("paper_title", f"论文{idx + 1}")
            year = result.get("year", "")
            year_str = f" ({year})" if year else ""
            sections.append(f"\n[{idx + 1}] {title}{year_str}\n")

        sections.append(f"\n\n{AI_DISCLAIMER}")

        return "".join(sections)

    def _extract_dimension_summary(
        self, result: dict, dimension: str
    ) -> str:
        dim_data = result.get(dimension)
        if dim_data is None:
            return "论文未明确提及"
        if isinstance(dim_data, str):
            return dim_data if dim_data.strip() else "论文未明确提及"
        if isinstance(dim_data, dict):
            summary = dim_data.get("summary", "")
            return summary if summary and summary.strip() else "论文未明确提及"
        return "论文未明确提及"

    def _fallback_result(self, input_data: dict) -> dict:
        analysis_results: List[dict] = input_data.get("analysis_results", [])
        compare_result = input_data.get("compare_result")

        fallback_report = self._generate_fallback_report(
            analysis_results, compare_result
        )

        return {
            "degraded": True,
            "agent": self.name,
            "report": fallback_report,
            "citation_list": [],
            "term_density_actual": 0.0,
            "personalization_applied": {
                "education_adaptation": EDUCATION_ADAPTATION.get(
                    "master", "侧重方法论对比和实验设计分析"
                ),
                "term_density_target": TERM_DENSITY_TARGET.get(
                    "intermediate", 0.20
                ),
                "style_guide": STYLE_MAP.get("balanced", "standard"),
            },
            "error": self.state.error,
        }

    def _summarize_result(self, result: dict) -> str:
        report = result.get("report", "")
        citation_count = len(result.get("citation_list", []))
        density = result.get("term_density_actual", 0.0)
        density_pct = int(density * 100)
        return f"Generated report: {len(report)} chars, {citation_count} citations, density={density_pct}%"

    def _build_personalization_applied(self, user_profile: dict) -> dict:
        if not user_profile:
            return {
                "education_adaptation": EDUCATION_ADAPTATION.get(
                    "master", "侧重方法论对比和实验设计分析"
                ),
                "term_density_target": TERM_DENSITY_TARGET.get(
                    "intermediate", 0.20
                ),
                "style_guide": STYLE_MAP.get("balanced", "standard"),
            }

        profile = self._normalize_profile(user_profile)
        education_level = profile.get("education_level", "master")
        knowledge_level = profile.get("knowledge_level", "intermediate")
        preferred_style = profile.get("preferred_style", "balanced")

        return {
            "education_adaptation": EDUCATION_ADAPTATION.get(
                education_level, EDUCATION_ADAPTATION["master"]
            ),
            "term_density_target": TERM_DENSITY_TARGET.get(
                knowledge_level, TERM_DENSITY_TARGET["intermediate"]
            ),
            "style_guide": STYLE_MAP.get(
                preferred_style, STYLE_MAP["balanced"]
            ),
        }

    def _normalize_profile(self, user_profile: dict) -> dict:
        if not isinstance(user_profile, dict):
            return {}
        normalized = {}
        for key, value in user_profile.items():
            if key in _CAMEL_TO_SNAKE_MAP:
                normalized[_CAMEL_TO_SNAKE_MAP[key]] = value
            else:
                normalized[key] = value
        return normalized

    def _get_profile_field(
        self, user_profile: dict, field: str, default: str
    ) -> str:
        profile = self._normalize_profile(user_profile)
        return profile.get(field, default)

    # ============================================================
    # P0-7: Token 爆炸防护 — 分析结果截断
    # ============================================================

    def _truncate_analysis_for_prompt(self, analysis_results: List[dict]) -> str:
        """截断分析结果，避免 Prompt 过长导致 Token 爆炸"""
        full_json = json.dumps(analysis_results, ensure_ascii=False)
        if len(full_json) <= MAX_ANALYSIS_CHARS:
            return full_json
        truncated = []
        for ar in analysis_results:
            truncated_ar = {
                "paper_id": ar.get("paper_id"),
                "paper_title": ar.get("paper_title", ""),
                "research_problem": self._truncate_dimension(ar.get("research_problem")),
                "core_method": self._truncate_dimension(ar.get("core_method")),
                "core_conclusions": self._truncate_dimension(ar.get("core_conclusions")),
            }
            truncated.append(truncated_ar)
        return json.dumps(truncated, ensure_ascii=False)

    @staticmethod
    def _truncate_dimension(dim_data) -> dict:
        """截断单个维度数据，保留 summary 前200字符"""
        if isinstance(dim_data, dict):
            summary = dim_data.get("summary", "")
            if isinstance(summary, str) and len(summary) > 200:
                return {"summary": summary[:200] + "...", "confidence": dim_data.get("confidence", 0.0)}
            return dim_data
        if isinstance(dim_data, str) and len(dim_data) > 200:
            return dim_data[:200] + "..."
        return dim_data

    # ============================================================
    # task52: stream_generate 流式生成方法
    # ============================================================

    async def stream_generate(
        self,
        prompt: str,
        input_data: dict,
        context: dict,
    ):
        """流式生成报告，逐 token yield

        Args:
            prompt: 基础 prompt（实际使用 build_prompt 构建完整 prompt）
            input_data: 输入数据（analysis_results / compare_result）
            context: 上下文（user_profile）

        Yields:
            dict: {'token': str, 'is_final': bool, 'report': Optional[str]}
                - token 非空、is_final=False: 流式 token
                - token 空、is_final=True、report 非空: 流结束，完整报告
        """
        from typing import AsyncGenerator

        analysis_results: List[dict] = input_data.get("analysis_results", [])
        compare_result = input_data.get("compare_result")
        user_profile = context.get("user_profile") or {}

        self.state.update_progress(0.2, "Building personalized prompt")

        try:
            full_prompt = self.build_prompt(input_data, context)
        except Exception as e:
            logger.warning(f"build_prompt failed, using raw prompt: {e}")
            full_prompt = prompt

        self.state.update_progress(0.4, "Streaming literature review")

        full_report_parts: List[str] = []

        try:
            async for token in self.llm_service.generate_stream(
                full_prompt,
                max_tokens=self.llm_max_tokens,
                temperature=self.llm_temperature,
            ):
                full_report_parts.append(token)
                yield {"token": token, "is_final": False, "report": None}

            # 流结束，拼接完整报告
            full_report = "".join(full_report_parts)
            self.state.update_progress(0.9, "Stream completed")

            yield {"token": "", "is_final": True, "report": full_report}

        except Exception as e:
            logger.warning(f"stream_generate failed, degrading to _run: {e}")
            # 降级调用 _run
            try:
                result = await self._run(prompt, input_data, context)
                fallback_report = result.get("report", "")
                yield {"token": "", "is_final": True, "report": fallback_report}
            except Exception as fallback_err:
                logger.error(f"stream_generate fallback also failed: {fallback_err}")
                yield {"token": "", "is_final": True, "report": ""}
