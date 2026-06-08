"""协调者 Agent — 项目经理角色（任务分解器）

依据 task32_coordinator_agent_core/prompt.json 实现。
职责：
    1. 接收用户 query + 用户画像 + analysis_type + paper_ids
    2. 调用 LLM 进行任务分解（task decomposition）
    3. 输出 2-5 个结构化子任务（retrieve/analyze/compare/generate/review）
    4. LLM 失败时降级为基于规则的任务分解（保证 LangGraph 流程不中断）
"""
import json
import re
from typing import Any, Dict, List, Optional

from loguru import logger

from app.agents.base import BaseAgent
from app.models.enums import AnalysisType


# ============================================================
# FR-013 类常量 — 便于测试和后续维护
# ============================================================

VALID_TASK_TYPES = {"retrieve", "analyze", "compare", "generate", "review"}
MIN_SUB_TASKS = 2
MAX_SUB_TASKS = 5
DEFAULT_ANALYSIS_TYPE = AnalysisType.REPORT.value  # "report"
DEFAULT_TOP_K = 10
DEFAULT_DIMENSIONS = [
    "research_problem",
    "core_method",
    "main_experiments",
    "core_conclusions",
    "limitations",
]
MAX_QUERY_LENGTH = 500  # FR-013 SR-002 Prompt 注入防护

# 任务类型顺序（依赖关系）
TASK_TYPE_ORDER = ["retrieve", "analyze", "compare", "generate", "review"]


# camelCase → snake_case 字段映射（兼容 Java 端跨系统字段）
_CAMEL_TO_SNAKE_MAP = {
    "educationLevel": "education_level",
    "knowledgeLevel": "knowledge_level",
    "preferredStyle": "preferred_style",
    "researchField": "research_field",
}


class CoordinatorAgent(BaseAgent):
    """协调者 Agent — 项目经理角色

    作为 LangGraph StateGraph 入口节点，负责将用户研究问题分解为
    2-5 个结构化子任务（retrieve/analyze/compare/generate/review），
    驱动下游 Agent 按子任务顺序执行。

    降级策略：LLM 调用失败/超时/JSON 解析失败时，自动回退到基于规则
    的任务分解，确保 LangGraph 流程不中断（ADR-002 可用性约束）。
    """

    def __init__(
        self,
        llm_service,
        prompt_manager,
        timeout: int = 30,
        llm_temperature: float = 0.3,
        llm_max_tokens: int = 1024,
    ) -> None:
        """构造器

        Args:
            llm_service: LLM 服务实例（含三路降级）
            prompt_manager: PromptManager 实例（string.Template 渲染）
            timeout: 单次执行超时（秒），默认 30
            llm_temperature: 任务分解需要更确定性的 JSON 输出，温度不宜过高
            llm_max_tokens: 分解结果较短，无需过大 token 预算
        """
        super().__init__(
            name="coordinator",
            llm_service=llm_service,
            prompt_manager=prompt_manager,
            timeout=timeout,
        )
        self.llm_temperature = llm_temperature
        self.llm_max_tokens = llm_max_tokens

    # ============================================================
    # FR-002 build_prompt
    # ============================================================

    def build_prompt(self, input_data: dict, context: dict) -> str:
        """构建协调者 Prompt

        从 input_data 提取 topic(必填) / paper_ids(可选) / analysis_type(枚举字符串)，
        从 context 提取 user_profile(4 维度 dict)，调用 prompt_manager 渲染模板。

        Returns:
            渲染后的 prompt 字符串
        """
        topic = self._sanitize_topic(input_data.get("topic", ""))
        paper_ids = input_data.get("paper_ids", []) or []
        analysis_type = input_data.get("analysis_type", DEFAULT_ANALYSIS_TYPE)

        # 序列化 user_profile 为 key=value 格式字符串
        user_profile = self._normalize_profile(context.get("user_profile") or {})
        user_profile_str = self._build_user_profile_summary(user_profile)

        # 序列化 paper_ids 为逗号分隔字符串（空时显示"用户未指定"）
        if paper_ids:
            paper_ids_str = ", ".join(str(pid) for pid in paper_ids)
        else:
            paper_ids_str = "（用户未指定）"

        return self.prompt_manager.get_prompt(
            "coordinator",
            query=topic,
            user_profile=user_profile_str,
            paper_ids=paper_ids_str,
            analysis_type=str(analysis_type),
        )

    # ============================================================
    # FR-003 _run
    # ============================================================

    async def _run(
        self, prompt: str, input_data: dict, context: dict
    ) -> dict:
        """核心执行逻辑：调 LLM 分解任务，解析输出，计算 requires_* 标记

        进度轨迹：0.0 → 0.2 → 0.5 → 0.8 → 1.0
        """
        topic = self._sanitize_topic(input_data.get("topic", ""))
        paper_ids = input_data.get("paper_ids", []) or []
        analysis_type = input_data.get("analysis_type", DEFAULT_ANALYSIS_TYPE)
        user_profile = self._normalize_profile(context.get("user_profile") or {})

        # Step 1: 准备 Prompt
        self.state.update_progress(0.2, "Decomposing task via LLM")
        logger.info(
            f"Coordinator {self.name} started: topic='{topic[:50]}', "
            f"paper_count={len(paper_ids)}, analysis_type={analysis_type}"
        )

        # Step 2: 调用 LLM（异常时降级到规则分解）
        try:
            full_prompt = prompt or self.build_prompt(input_data, context)
            self.state.update_progress(0.5, "Calling LLM for task breakdown")

            llm_output = await self.llm_service.generate(
                full_prompt,
                max_tokens=self.llm_max_tokens,
                temperature=self.llm_temperature,
            )
        except Exception as e:
            logger.warning(
                f"Coordinator LLM call failed, falling back to rule-based: {e}"
            )
            return self._fallback_result(input_data)

        # Step 3: 解析 LLM 输出
        self.state.update_progress(0.8, "Parsing task breakdown")

        if not llm_output or not llm_output.strip():
            logger.warning("Coordinator LLM returned empty output, using fallback")
            return self._fallback_result(input_data)

        sub_tasks = self._parse_task_breakdown(llm_output, input_data)

        # Step 4: 计算 requires_compare / requires_review
        flags = self._determine_required_tasks(input_data, sub_tasks)

        # Step 5: 生成 reasoning（如果有 LLM 输出中的 reasoning 字段，优先使用）
        reasoning = self._extract_reasoning(llm_output) or (
            f"Coordinator decomposed {len(sub_tasks)} sub-tasks: "
            f"{', '.join(t.get('task_type', 'unknown') for t in sub_tasks)}"
        )

        # Step 6: 更新进度
        summary = self._summarize_sub_tasks(sub_tasks)
        self.state.update_progress(1.0, summary)
        logger.info(f"Coordinator decomposed into {len(sub_tasks)} sub-tasks")

        return {
            "sub_tasks": sub_tasks,
            "reasoning": reasoning,
            "task_count": len(sub_tasks),
            "requires_compare": flags["requires_compare"],
            "requires_review": flags["requires_review"],
            "analysis_type": str(analysis_type),
            "paper_count": len(paper_ids),
            "agent": self.name,
        }

    # ============================================================
    # FR-004 _parse_task_breakdown
    # ============================================================

    def _parse_task_breakdown(
        self, llm_output: str, input_data: dict
    ) -> List[dict]:
        """解析 LLM 输出为结构化子任务列表

        策略：
            1. 尝试提取 ```json ... ``` 代码块
            2. 尝试提取首个 { ... } 块
            3. 尝试整体 JSON 解析
            4. 失败时降级到 _rule_based_decomposition

        强制 2-5 约束：
            - < MIN_SUB_TASKS：降级到规则分解
            - > MAX_SUB_TASKS：截断到前 5 个湃法 task_type ∈ VALID_TASK_TYPES 的项
        """
        parsed_sub_tasks: List[dict] = []

        # Step 1: 提取 JSON
        parsed_json = self._extract_json(llm_output)
        if parsed_json is not None:
            sub_tasks_candidate = parsed_json.get("sub_tasks", [])
            if isinstance(sub_tasks_candidate, list):
                for item in sub_tasks_candidate:
                    if not isinstance(item, dict):
                        continue
                    task_type = item.get("task_type")
                    if task_type in VALID_TASK_TYPES:
                        parsed_sub_tasks.append(item)

        # Step 2: 过滤非法 task_type 后检查数量
        if len(parsed_sub_tasks) < MIN_SUB_TASKS:
            logger.warning(
                f"Coordinator parse got {len(parsed_sub_tasks)} valid sub-tasks, "
                f"falling back to rule-based decomposition"
            )
            return self._rule_based_decomposition(input_data)

        # Step 3: 截断超过 5 个
        if len(parsed_sub_tasks) > MAX_SUB_TASKS:
            logger.warning(
                f"Coordinator parse got {len(parsed_sub_tasks)} sub-tasks, "
                f"truncating to {MAX_SUB_TASKS}"
            )
            parsed_sub_tasks = parsed_sub_tasks[:MAX_SUB_TASKS]

        return parsed_sub_tasks

    def _extract_json(self, text: str) -> Optional[dict]:
        """从 LLM 输出中提取 JSON

        返回第一个可解析的 dict。提取顺序：
            1. ```json ... ``` 代码块
            2. ``` ... ``` 代码块
            3. 首个 { ... } 块
            4. 整体文本
        """
        if not text or not text.strip():
            return None

        cleaned = text.strip()

        # 1) ```json ... ``` 块
        json_block = re.search(r"```json\s*(.*?)\s*```", cleaned, re.DOTALL)
        if json_block:
            try:
                return json.loads(json_block.group(1))
            except json.JSONDecodeError:
                pass

        # 2) ``` ... ``` 块
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

    def _extract_reasoning(self, llm_output: str) -> Optional[str]:
        """提取 LLM 输出中的 reasoning 字段（如果有）"""
        parsed = self._extract_json(llm_output)
        if parsed is None:
            return None
        reasoning = parsed.get("reasoning")
        if isinstance(reasoning, str) and reasoning.strip():
            return reasoning
        return None

    # ============================================================
    # FR-005 _rule_based_decomposition
    # ============================================================

    def _rule_based_decomposition(self, input_data: dict) -> List[dict]:
        """基于规则的启发式任务分解（LLM 不可用时的降级路径）

        策略：
            1. always 添加 retrieve
            2. always 添加 analyze
            3. paper_ids >= 2 且 analysis_type ∈ {compare, report} 添加 compare
            4. analysis_type != paper_analysis 添加 generate
            5. analysis_type ∈ {report, compare} 添加 review
        """
        topic = self._sanitize_topic(input_data.get("topic", ""))
        paper_ids = input_data.get("paper_ids", []) or []
        analysis_type = str(input_data.get("analysis_type", DEFAULT_ANALYSIS_TYPE))
        user_profile = self._normalize_profile(input_data.get("user_profile") or {})

        # 1) retrieve 子任务（总包含）
        keywords = [w for w in re.split(r"[\s,，。；;、]+", topic) if w][:5]
        sub_tasks: List[dict] = [
            {
                "task_type": "retrieve",
                "description": f"检索关于 '{topic}' 的相关论文",
                "keywords": keywords if keywords else [topic[:50]],
                "top_k": DEFAULT_TOP_K,
            }
        ]

        # 2) analyze 子任务（总包含）
        sub_tasks.append(
            {
                "task_type": "analyze",
                "description": "分析检索到的论文核心内容",
                "dimensions": list(DEFAULT_DIMENSIONS),
            }
        )

        # 3) compare 子任务（条件启用）
        flags = self._determine_required_tasks(input_data, [])
        if flags["requires_compare"]:
            sub_tasks.append(
                {
                    "task_type": "compare",
                    "description": "对比多篇论文的方法和结论",
                    "required": True,
                }
            )

        # 4) generate 子任务（非 paper_analysis 启用）
        if analysis_type != AnalysisType.PAPER_ANALYSIS.value:
            sub_tasks.append(
                {
                    "task_type": "generate",
                    "description": "生成个性化文献综述",
                    "style": self._infer_style_from_profile(user_profile),
                }
            )

        # 5) review 子任务（条件启用）
        if flags["requires_review"]:
            sub_tasks.append(
                {
                    "task_type": "review",
                    "description": "审核生成内容的准确性和引用",
                    "focus": ["事实核查", "引用核查"],
                }
            )

        return sub_tasks

    # ============================================================
    # FR-006 _determine_required_tasks
    # ============================================================

    def _determine_required_tasks(
        self, input_data: dict, sub_tasks: List[dict]
    ) -> dict:
        """基于 paper_ids 数量和 analysis_type 计算条件分支标记

        Returns:
            dict 含 requires_compare / requires_review / paper_count / analysis_type
        """
        paper_ids = input_data.get("paper_ids", []) or []
        analysis_type = str(input_data.get("analysis_type", DEFAULT_ANALYSIS_TYPE))

        return {
            "requires_compare": (
                len(paper_ids) >= 2
                and analysis_type
                in (
                    AnalysisType.COMPARE.value,
                    AnalysisType.REPORT.value,
                )
            ),
            "requires_review": analysis_type
            in (
                AnalysisType.REPORT.value,
                AnalysisType.COMPARE.value,
            ),
            "paper_count": len(paper_ids),
            "analysis_type": analysis_type,
        }

    # ============================================================
    # FR-007 _summarize_sub_tasks
    # ============================================================

    def _summarize_sub_tasks(self, sub_tasks: List[dict]) -> str:
        """生成子任务摘要字符串（用于 SSE 推送）

        格式：'分解为 N 个子任务: type1, type2, ...'
        最多展示前 5 个子任务类型。
        """
        if not sub_tasks:
            return "分解为 0 个子任务"

        types = [
            t.get("task_type", "unknown") for t in sub_tasks[:MAX_SUB_TASKS]
        ]
        suffix = "" if len(sub_tasks) <= MAX_SUB_TASKS else "..."
        return f"分解为 {len(sub_tasks)} 个子任务: {', '.join(types)}{suffix}"

    # ============================================================
    # FR-008 _fallback_result（覆盖 BaseAgent）
    # ============================================================

    def _fallback_result(self, input_data: dict) -> dict:
        """LLM 失败/超时/JSON 解析失败时调用规则分解，保证 LangGraph 不中断"""
        paper_ids = input_data.get("paper_ids", []) or []
        analysis_type = input_data.get("analysis_type", DEFAULT_ANALYSIS_TYPE)
        rule_based_sub_tasks = self._rule_based_decomposition(input_data)
        flags = self._determine_required_tasks(input_data, rule_based_sub_tasks)

        result = {
            "degraded": True,
            "agent": self.name,
            "sub_tasks": rule_based_sub_tasks,
            "reasoning": "LLM unavailable, using rule-based decomposition",
            "task_count": len(rule_based_sub_tasks),
            "requires_compare": flags["requires_compare"],
            "requires_review": flags["requires_review"],
            "analysis_type": str(analysis_type),
            "paper_count": len(paper_ids),
            "error": self.state.error,
        }
        logger.info(
            f"Coordinator degraded to rule-based: {len(rule_based_sub_tasks)} sub-tasks"
        )
        return result

    # ============================================================
    # FR-009 _summarize_result（覆盖 BaseAgent）
    # ============================================================

    def _summarize_result(self, result: dict) -> str:
        """覆盖基类，返回 'Decomposed into N sub-tasks: [...]' 格式字符串"""
        task_count = result.get("task_count", 0)
        sub_tasks = result.get("sub_tasks", [])
        types = [t.get("task_type", "unknown") for t in sub_tasks[:MAX_SUB_TASKS]]
        suffix = "" if len(sub_tasks) <= MAX_SUB_TASKS else "..."
        return f"Decomposed into {task_count} sub-tasks: {', '.join(types)}{suffix}"

    # ============================================================
    # FR-010 _infer_style_from_profile
    # ============================================================

    def _infer_style_from_profile(self, user_profile: dict) -> str:
        """从 user_profile.preferred_style 推断生成任务风格

        Returns:
            通俗风格 / 均衡风格 / 专业风格 / 学术风格（默认）
        """
        if not isinstance(user_profile, dict):
            return "学术风格"

        profile = self._normalize_profile(user_profile)
        preferred_style = profile.get("preferred_style")

        style_map = {
            "simple": "通俗风格",
            "balanced": "均衡风格",
            "technical": "专业风格",
        }
        return style_map.get(preferred_style, "学术风格")

    # ============================================================
    # SR-002 Prompt 注入防护：topic 长度限制 + 控制字符清理
    # ============================================================

    def _sanitize_topic(self, topic: Any) -> str:
        """清理 user topic 输入

        - 限制最大长度 MAX_QUERY_LENGTH
        - 移除控制字符（保留中英文、数字、常见标点）
        """
        if topic is None:
            return ""

        topic_str = str(topic).strip()

        # 移除控制字符（保留 ASCII 可打印字符 + 中文 + 常见标点）
        topic_str = re.sub(r"[^\w\s\u4e00-\u9fff\.,;:!?\"'\-_()\[\]/\\@#$%^&*+=<>~`|]", "", topic_str)
        # 合并多个连续空白
        topic_str = re.sub(r"\s+", " ", topic_str).strip()

        if len(topic_str) > MAX_QUERY_LENGTH:
            logger.warning(
                f"Coordinator topic exceeds {MAX_QUERY_LENGTH} chars, truncating"
            )
            topic_str = topic_str[:MAX_QUERY_LENGTH]

        return topic_str

    # ============================================================
    # 辅助方法
    # ============================================================

    def _normalize_profile(self, user_profile: Any) -> dict:
        """归一化 user_profile（兼容 camelCase 字段）"""
        if not isinstance(user_profile, dict):
            return {}
        normalized: Dict[str, Any] = {}
        for key, value in user_profile.items():
            if key in _CAMEL_TO_SNAKE_MAP:
                normalized[_CAMEL_TO_SNAKE_MAP[key]] = value
            else:
                normalized[key] = value
        return normalized

    def _build_user_profile_summary(self, profile: dict) -> str:
        """将 user_profile 序列化为 key=value 格式字符串（供 Prompt 模板使用）"""
        if not profile:
            return "（用户未提供画像）"

        parts: List[str] = []
        for key in ("education_level", "research_field", "knowledge_level", "preferred_style"):
            if key in profile and profile[key]:
                parts.append(f"{key}={profile[key]}")
        return " / ".join(parts) if parts else "（用户未提供画像）"