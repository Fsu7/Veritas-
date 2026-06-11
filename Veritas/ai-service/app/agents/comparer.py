"""对比员 Agent — 多论文方法对比与矛盾发现（task34 产出）

依据 task34_comparer_agent_core/prompt.json 实现。
职责：
    1. 接收 AnalyzerAgent 输出的多篇论文 5 维度分析结果（analysis_results）
    2. 调用 LLM 进行多论文对比与矛盾发现
    3. 输出结构化对比矩阵 {comparison_matrix, summary, contradictions, paper_count}
    4. LLM 失败时降级为基于规则的两两对比（C(N,2) 对 + 关键词矛盾检测），不阻塞 LangGraph

约束：4 个对比维度 + 5 类矛盾根因枚举 + 客观性原则（不裁决、不偏袒）
"""
import json
import re
from itertools import combinations
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from app.agents.base import BaseAgent


# ============================================================
# FR-014 类常量 — 便于测试和后续维护
# ============================================================

# 5 类矛盾根因枚举
VALID_ROOT_CAUSES = {
    "dataset_bias",
    "metric_difference",
    "condition_difference",
    "assumption_difference",
    "methodological_conflict",
}
# 默认根因（兜底）
DEFAULT_ROOT_CAUSE = "methodological_conflict"

# 4 个对比维度（与 AnalyzerAgent 的 5 维度对齐前 4 个）
COMPARE_DIMENSIONS = [
    "research_problem",
    "core_method",
    "main_experiments",
    "core_conclusions",
]

# 论文数边界
MIN_PAPERS = 2
MAX_PAPERS = 5

# 矛盾关键词集合（FR-008）
CONFLICT_KEYWORDS = [
    "但是",
    "然而",
    "不同于",
    "相比之下",
    "相反",
    "contradict",
    "however",
    "but",
    "unlike",
    "whereas",
    "on the other hand",
]

# 提示占位符
FALLBACK_NOTE = "论文未明确提及"

# AI 免责声明
AI_DISCLAIMER = "⚠️ 本对比由 AI 生成，仅供参考"

# 空对比结果（论文数 < MIN_PAPERS 时返回）
EMPTY_COMPARISON = {
    "comparison_matrix": {
        "dimensions": [],
        "papers": [],
        "similarities": [],
        "differences": [],
        "contradictions": [],
    },
    "summary": "",
    "contradictions": [],
    "paper_count": 0,
    "agent": "comparer",
}


class ComparerAgent(BaseAgent):
    """对比员 Agent — 对比研究员角色

    作为 LangGraph StateGraph 可选节点（仅在 requires_compare=True 时激活），
    位于 Analyzer 之后、Generator 之前。

    职责：
        1. 接收多篇论文 5 维度分析结果
        2. 通过 LLM 进行 4 维度对比 + 5 类矛盾根因分析
        3. 输出结构化对比矩阵 + summary + contradictions

    降级策略：LLM 调用失败/超时/JSON 解析失败/空输出时，
    自动回退到基于规则的 C(N,2) 两两对比 + 关键词矛盾检测，
    确保 LangGraph 流程不中断（ADR-002 可用性约束）。

    客观性原则：标注矛盾 + 分析根因，不裁决，不偏袒任何一方。
    """

    def __init__(
        self,
        llm_service,
        prompt_manager,
        personalization_service=None,
        timeout: int = 30,
        llm_temperature: float = 0.4,
        llm_max_tokens: int = 3072,
        min_papers_for_compare: int = MIN_PAPERS,
        max_papers_for_compare: int = MAX_PAPERS,
    ) -> None:
        """构造器

        Args:
            llm_service: LLM 服务实例（含三路降级）
            prompt_manager: PromptManager 实例（string.Template 渲染）
            personalization_service: PersonalizationService 实例（可选，个性化指令注入）
            timeout: 单次执行超时（秒），默认 30
            llm_temperature: 对比任务需要适度创造性（低于 Generator 0.7 但高于 Coordinator 0.3）
            llm_max_tokens: 对比矩阵可能较长，默认 3072
            min_papers_for_compare: 最少 2 篇
            max_papers_for_compare: 最多 5 篇，避免 LLM 上下文爆炸
        """
        super().__init__(
            name="comparer",
            llm_service=llm_service,
            prompt_manager=prompt_manager,
            timeout=timeout,
        )
        self.personalization_service = personalization_service
        self.llm_temperature = llm_temperature
        self.llm_max_tokens = llm_max_tokens
        self.min_papers_for_compare = min_papers_for_compare
        self.max_papers_for_compare = max_papers_for_compare

    # ============================================================
    # FR-002 build_prompt
    # ============================================================

    def build_prompt(self, input_data: dict, context: dict) -> str:
        """构建对比 Prompt

        从 input_data 提取 analysis_results（列表），序列化为 JSON 字符串。
        从 context 提取 user_profile，序列化为画像字符串。
        """
        analysis_results = input_data.get("analysis_results", []) or []
        paper_count = len(analysis_results)

        try:
            analysis_data_str = json.dumps(analysis_results, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to serialize analysis_results: {e}")
            analysis_data_str = str(analysis_results)

        user_profile = context.get("user_profile")
        user_profile_str = self._build_user_profile_summary(user_profile)

        base_prompt = self.prompt_manager.get_prompt(
            "comparer",
            analysis_data=analysis_data_str,
            user_profile=user_profile_str,
            paper_count=str(paper_count),
        )

        # 注入个性化指令
        personalization = self._get_personalization_instruction(context)
        if personalization:
            base_prompt += f"\n\n【个性化适配】{personalization}"

        return base_prompt

    # ============================================================
    # FR-003 _run
    # ============================================================

    async def _run(
        self, prompt: str, input_data: dict, context: dict
    ) -> dict:
        """核心执行逻辑：调 LLM 解析对比结果，计算 4 维度矩阵 + 矛盾根因

        进度轨迹：0.0 → 0.2 → 0.5 → 0.8 → 1.0
        """
        analysis_results = input_data.get("analysis_results", []) or []
        paper_count = len(analysis_results)

        # FR-015 入口校验
        if paper_count < self.min_papers_for_compare:
            logger.info(
                f"Comparer skipped: paper_count={paper_count} < "
                f"min_papers_for_compare={self.min_papers_for_compare}"
            )
            empty_result = {
                "comparison_matrix": {
                    "dimensions": list(COMPARE_DIMENSIONS),
                    "papers": [],
                    "similarities": [],
                    "differences": [],
                    "contradictions": [],
                },
                "summary": (
                    f"论文数 {paper_count} < {self.min_papers_for_compare}，无需对比"
                ),
                "contradictions": [],
                "paper_count": paper_count,
                "agent": self.name,
            }
            self.state.update_progress(1.0, f"Skipped: paper_count={paper_count}")
            return empty_result

        if paper_count > self.max_papers_for_compare:
            logger.warning(
                f"Comparer truncating: paper_count={paper_count} > "
                f"max_papers_for_compare={self.max_papers_for_compare}"
            )
            analysis_results = analysis_results[: self.max_papers_for_compare]
            paper_count = len(analysis_results)

        # Step 1: 准备 Prompt
        self.state.update_progress(0.2, "Building comparison prompt")
        logger.info(
            f"Comparer {self.name} started: paper_count={paper_count}, "
            f"dimensions={len(COMPARE_DIMENSIONS)}"
        )

        # Step 2: 调用 LLM（异常时降级到规则对比）
        try:
            full_prompt = prompt or self.build_prompt(input_data, context)
            self.state.update_progress(0.5, "Calling LLM for comparison")

            llm_output = await self.llm_service.generate(
                full_prompt,
                max_tokens=self.llm_max_tokens,
                temperature=self.llm_temperature,
            )
        except Exception as e:
            logger.warning(
                f"Comparer LLM call failed, falling back to rule-based: {e}"
            )
            return self._fallback_result(input_data)

        # Step 3: 解析 LLM 输出
        self.state.update_progress(0.8, "Parsing comparison matrix")

        if not llm_output or not llm_output.strip():
            logger.warning("Comparer LLM returned empty output, using fallback")
            return self._fallback_result(input_data)

        parsed = self._parse_comparison(llm_output, input_data)

        # 注入 analysis_results 信息（保留 paper_count）
        parsed["paper_count"] = paper_count
        parsed["agent"] = self.name

        # FR-012 AI 免责声明
        if isinstance(parsed.get("summary"), str):
            if AI_DISCLAIMER not in parsed["summary"]:
                parsed["summary"] = (
                    parsed["summary"].rstrip() + "\n\n" + AI_DISCLAIMER
                )

        # Step 4: 更新进度
        summary_text = self._summarize_comparison(parsed)
        self.state.update_progress(1.0, summary_text)
        logger.info(
            f"Comparer completed: paper_count={paper_count}, "
            f"similarities={len(parsed.get('comparison_matrix', {}).get('similarities', []))}, "
            f"differences={len(parsed.get('comparison_matrix', {}).get('differences', []))}, "
            f"contradictions={len(parsed.get('contradictions', []))}"
        )

        return parsed

    # ============================================================
    # FR-004 _parse_comparison
    # ============================================================

    def _parse_comparison(
        self, llm_output: str, input_data: dict
    ) -> dict:
        """解析 LLM 输出为结构化对比结果

        策略：
            1. 提取 JSON（```json / ```{ / raw）
            2. 校验 comparison_matrix 结构
            3. 校验矛盾根因 ∈ VALID_ROOT_CAUSES
            4. 失败时降级到 _rule_based_comparison
        """
        analysis_results = input_data.get("analysis_results", []) or []
        parsed_json = self._extract_json(llm_output)

        if parsed_json is not None:
            comparison_matrix = parsed_json.get(
                "comparison_matrix",
                {
                    "dimensions": list(COMPARE_DIMENSIONS),
                    "papers": [],
                    "similarities": [],
                    "differences": [],
                    "contradictions": [],
                },
            )
            # 规范化 dimensions
            if not comparison_matrix.get("dimensions"):
                comparison_matrix["dimensions"] = list(COMPARE_DIMENSIONS)

            # 校验 papers 是否包含所有 analysis_results 的 paper_id
            expected_paper_ids = {
                str(r.get("paper_id", "")) for r in analysis_results
            }
            existing_paper_ids = set(comparison_matrix.get("papers", []))
            missing = expected_paper_ids - existing_paper_ids - {""}
            if missing:
                logger.warning(
                    f"Comparer missing paper_ids in matrix.papers: {missing}"
                )
                comparison_matrix.setdefault("papers", []).extend(missing)

            # 校验矛盾根因
            contradictions = comparison_matrix.get("contradictions", []) or []
            validated_contradictions = []
            for c in contradictions:
                if not isinstance(c, dict):
                    continue
                c_copy = dict(c)
                root_cause = c_copy.get("root_cause")
                if root_cause not in VALID_ROOT_CAUSES:
                    logger.warning(
                        f"Invalid root_cause '{root_cause}' replaced with "
                        f"'{DEFAULT_ROOT_CAUSE}'"
                    )
                    c_copy["root_cause"] = DEFAULT_ROOT_CAUSE
                validated_contradictions.append(c_copy)
            comparison_matrix["contradictions"] = validated_contradictions

            summary = parsed_json.get("summary", "")
            if not isinstance(summary, str):
                summary = ""

            return {
                "comparison_matrix": comparison_matrix,
                "summary": summary,
                "contradictions": validated_contradictions,
            }

        # 失败时降级
        logger.warning("Comparer JSON parsing failed, using rule-based fallback")
        return self._rule_based_comparison(input_data)

    def _extract_json(self, text: str) -> Optional[dict]:
        """从 LLM 输出中提取 JSON（与 coordinator 同实现）"""
        if not text or not text.strip():
            return None

        cleaned = text.strip()

        # 1) ```json ... ```
        json_block = re.search(r"```json\s*(.*?)\s*```", cleaned, re.DOTALL)
        if json_block:
            try:
                return json.loads(json_block.group(1))
            except json.JSONDecodeError:
                pass

        # 2) ``` ... ```
        code_block = re.search(r"```\s*(.*?)\s*```", cleaned, re.DOTALL)
        if code_block:
            try:
                return json.loads(code_block.group(1))
            except json.JSONDecodeError:
                pass

        # 3) 首个 { ... } 块
        brace_start = cleaned.find("{")
        brace_end = cleaned.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            try:
                return json.loads(cleaned[brace_start : brace_end + 1])
            except json.JSONDecodeError:
                pass

        # 4) 整体文本
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None

    # ============================================================
    # FR-005 _rule_based_comparison
    # ============================================================

    def _rule_based_comparison(self, input_data: dict) -> dict:
        """基于规则的两两对比（LLM 不可用时的降级路径）

        对每对论文 (paper_i, paper_j)：
            1. 4 维度逐个比较
            2. 计算 summary 文本相似度（_calculate_similarity）
            3. 检测矛盾关键词（_detect_conflict_keywords）
        """
        analysis_results = input_data.get("analysis_results", []) or []
        paper_count = len(analysis_results)

        similarities: List[dict] = []
        differences: List[dict] = []
        contradictions: List[dict] = []
        paper_ids: List[str] = []

        # 收集所有 paper_id
        for r in analysis_results:
            pid = str(r.get("paper_id", ""))
            if pid:
                paper_ids.append(pid)

        # C(N,2) 两两对比
        for paper_i, paper_j in combinations(analysis_results, 2):
            pid_i = str(paper_i.get("paper_id", ""))
            pid_j = str(paper_j.get("paper_id", ""))
            pair_ids = sorted([pid_i, pid_j])

            for dimension in COMPARE_DIMENSIONS:
                text_i = self._extract_dimension_summary(paper_i, dimension)
                text_j = self._extract_dimension_summary(paper_j, dimension)

                similarity = self._calculate_similarity(text_i, text_j)

                entry = {
                    "dimension": dimension,
                    "papers": pair_ids,
                    "similarity": round(similarity, 4),
                    "description": "",
                }

                if similarity >= 0.6:
                    entry["description"] = (
                        f"两篇论文在 {dimension} 维度高度相似（相似度 {similarity:.2f}）"
                    )
                    similarities.append(entry)
                elif similarity <= 0.3:
                    entry["description"] = (
                        f"两篇论文在 {dimension} 维度差异显著（相似度 {similarity:.2f}）"
                    )
                    differences.append(entry)
                else:
                    entry["description"] = (
                        f"两篇论文在 {dimension} 维度中等相似（相似度 {similarity:.2f}）"
                    )
                    similarities.append(entry)
                    differences.append(entry)

            # 矛盾检测（仅在 core_conclusions 上做关键词匹配）
            conclusions_i = self._extract_dimension_summary(
                paper_i, "core_conclusions"
            )
            conclusions_j = self._extract_dimension_summary(
                paper_j, "core_conclusions"
            )
            keywords = self._detect_conflict_keywords(conclusions_i, conclusions_j)
            if keywords:
                contradictions.append({
                    "papers": pair_ids,
                    "topic": "core_conclusions",
                    "claim_a": conclusions_i[:100],
                    "claim_b": conclusions_j[:100],
                    "evidence_a": (
                        f"包含矛盾关键词：{', '.join(keywords)}"
                    ),
                    "evidence_b": (
                        f"包含矛盾关键词：{', '.join(keywords)}"
                    ),
                    "root_cause": DEFAULT_ROOT_CAUSE,
                    "resolution_suggestion": (
                        "基于当前证据无法判定，建议进一步验证实验设置差异"
                    ),
                })

        # C(N,2) 组合数（数学公式：N*(N-1)/2）
        n = len(analysis_results)
        pair_count = n * (n - 1) // 2

        summary_text = (
            f"基于规则的两两对比结果：{n} 篇论文生成 "
            f"{pair_count} 个对比对，"
            f"识别 {len(contradictions)} 处潜在矛盾。"
        )

        summary_with_disclaimer = (
            summary_text + "\n\n" + AI_DISCLAIMER
        )

        return {
            "comparison_matrix": {
                "dimensions": list(COMPARE_DIMENSIONS),
                "papers": paper_ids,
                "similarities": similarities,
                "differences": differences,
                "contradictions": contradictions,
            },
            "summary": summary_with_disclaimer,
            "contradictions": contradictions,
            "paper_count": paper_count,
            "agent": self.name,
        }

    # ============================================================
    # FR-006 _extract_dimension_summary
    # ============================================================

    def _extract_dimension_summary(self, result: dict, dimension: str) -> str:
        """从 analysis_result 中提取指定维度的 summary 文本

        处理 3 种类型：
            - dict 类型 → 取 summary 字段
            - str 类型 → 直接返回
            - None 或缺失 → 返回 FALLBACK_NOTE
        """
        if not isinstance(result, dict):
            return FALLBACK_NOTE

        dim_data = result.get(dimension)
        if dim_data is None:
            return FALLBACK_NOTE

        if isinstance(dim_data, str):
            return dim_data if dim_data.strip() else FALLBACK_NOTE

        if isinstance(dim_data, dict):
            summary = dim_data.get("summary", "")
            if isinstance(summary, str) and summary.strip():
                return summary
            return FALLBACK_NOTE

        return FALLBACK_NOTE

    # ============================================================
    # FR-007 _calculate_similarity
    # ============================================================

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算两段文本的关键词重叠率（简化 Jaccard 相似度）

        处理：
            - 空文本或相同文本 → 1.0
            - 完全不同的文本 → < 0.3
            - 部分重叠 → 0.3-0.7
        """
        # 归一化
        t1 = (text1 or "").strip()
        t2 = (text2 or "").strip()

        if not t1 and not t2:
            return 1.0
        if not t1 or not t2:
            return 0.0
        if t1 == t2:
            return 1.0

        # 中文字符 + 简单 n-gram（n=2）
        def _tokenize(text: str) -> set:
            tokens = set()
            # 单字符（中文友好）
            for ch in text:
                if ch.strip() and (ch.isalnum() or '\u4e00' <= ch <= '\u9fff'):
                    tokens.add(ch)
            # 2-gram
            for i in range(len(text) - 1):
                bigram = text[i:i + 2].strip()
                if bigram:
                    tokens.add(bigram)
            return tokens

        set1 = _tokenize(t1)
        set2 = _tokenize(t2)

        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0

        intersection = set1 & set2
        union = set1 | set2

        return len(intersection) / len(union) if union else 0.0

    # ============================================================
    # FR-008 _detect_conflict_keywords
    # ============================================================

    def _detect_conflict_keywords(self, text1: str, text2: str) -> List[str]:
        """检测两段文本中的矛盾关键词（不重复）"""
        t1 = (text1 or "").lower()
        t2 = (text2 or "").lower()

        found = []
        for kw in CONFLICT_KEYWORDS:
            if kw.lower() in t1 or kw.lower() in t2:
                if kw not in found:
                    found.append(kw)
        return found

    # ============================================================
    # FR-009 _summarize_comparison
    # ============================================================

    def _summarize_comparison(self, comparison_result: dict) -> str:
        """生成对比结果摘要字符串（用于 SSE 推送）"""
        paper_count = comparison_result.get("paper_count", 0)
        matrix = comparison_result.get("comparison_matrix", {})
        similarities_count = len(matrix.get("similarities", []))
        differences_count = len(matrix.get("differences", []))
        contradictions_count = len(comparison_result.get("contradictions", []))

        return (
            f"对比 {paper_count} 篇论文: "
            f"{similarities_count} 个相似点, "
            f"{differences_count} 个差异, "
            f"{contradictions_count} 个矛盾"
        )

    # ============================================================
    # FR-010 _fallback_result（覆盖 BaseAgent）
    # ============================================================

    def _fallback_result(self, input_data: dict) -> dict:
        """LLM 失败/超时/JSON 解析失败时调用规则对比，保证 LangGraph 不中断"""
        result = self._rule_based_comparison(input_data)
        result["degraded"] = True
        result["error"] = self.state.error
        logger.info("Comparer degraded to rule-based comparison")
        return result

    # ============================================================
    # FR-011 _summarize_result（覆盖 BaseAgent）
    # ============================================================

    def _summarize_result(self, result: dict) -> str:
        """覆盖基类，返回英文摘要格式"""
        paper_count = result.get("paper_count", 0)
        matrix = result.get("comparison_matrix", {})
        similarities_count = len(matrix.get("similarities", []))
        differences_count = len(matrix.get("differences", []))
        contradictions_count = len(result.get("contradictions", []))

        return (
            f"Compared {paper_count} papers: "
            f"{similarities_count} similarities, "
            f"{differences_count} differences, "
            f"{contradictions_count} contradictions"
        )

    # ============================================================
    # 辅助方法
    # ============================================================

    def _build_user_profile_summary(self, user_profile: Any) -> str:
        """将 user_profile 序列化为 key=value 格式字符串（供 Prompt 模板使用）"""
        if not user_profile:
            return "（用户未提供画像）"

        if not isinstance(user_profile, dict):
            return str(user_profile)

        parts = []
        for key in ("education_level", "research_field", "knowledge_level", "preferred_style"):
            if key in user_profile and user_profile[key]:
                parts.append(f"{key}={user_profile[key]}")
        return " / ".join(parts) if parts else "（用户未提供画像）"

    def _get_personalization_instruction(self, context: dict) -> str:
        """获取个性化指令片段（降级安全）"""
        if self.personalization_service is None:
            return ""
        user_profile = context.get("user_profile")
        if not user_profile:
            return ""
        try:
            return self.personalization_service.get_personalization_for_agent(
                "comparer", user_profile
            )
        except Exception as e:
            logger.warning(f"Personalization injection failed for comparer: {e}")
            return ""