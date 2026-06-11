"""ReviewerAgent — 审核Agent核心逻辑

继承BaseAgent，接收生成Agent的综述报告和原始论文数据，
调用LLM进行事实核查、引用核查、逻辑完整性审核，
返回审核通过或修改建议。

审核通过条件：事实准确率>90%且引用准确率>90%。
"""
import json
import re
from typing import Any, Dict, List, Optional

from loguru import logger

from app.agents.base import BaseAgent


class ReviewerAgent(BaseAgent):

    def __init__(
        self,
        llm_service,
        prompt_manager,
        personalization_service=None,
        timeout: int = 30,
        llm_temperature: float = 0.3,
        llm_max_tokens: int = 2048,
    ) -> None:
        super().__init__(
            name="reviewer",
            llm_service=llm_service,
            prompt_manager=prompt_manager,
            timeout=timeout,
        )
        self.personalization_service = personalization_service
        self.llm_temperature = llm_temperature
        self.llm_max_tokens = llm_max_tokens

    def build_prompt(self, input_data: dict, context: dict) -> str:
        report = input_data.get("report", "")
        original_papers = input_data.get("original_papers", [])
        retry_context = input_data.get("retry_context", "")

        papers_json = json.dumps(original_papers, ensure_ascii=False) if original_papers else "无"

        base_prompt = self.prompt_manager.get_prompt(
            "reviewer",
            report_content=report,
            original_papers=papers_json,
            retry_context=retry_context,
        )

        # 注入个性化指令
        personalization = self._get_personalization_instruction(context)
        if personalization:
            base_prompt += f"\n\n【个性化适配】{personalization}"

        return base_prompt

    async def _run(
        self, prompt: str, input_data: dict, context: dict
    ) -> dict:
        report = input_data.get("report", "")
        original_papers = input_data.get("original_papers", [])

        self.state.update_progress(0.2, "Building review prompt")

        try:
            full_prompt = self.build_prompt(input_data, context)
        except Exception as e:
            logger.warning(f"build_prompt failed, using raw prompt: {e}")
            full_prompt = prompt

        self.state.update_progress(0.4, "Running LLM review")

        try:
            llm_output = await self.llm_service.generate(
                full_prompt,
                max_tokens=self.llm_max_tokens,
                temperature=self.llm_temperature,
            )
        except Exception as e:
            logger.warning(f"LLM generation failed: {e}")
            return {
                "approved": False,
                "degraded": True,
                "agent": self.name,
                "issues": [],
                "suggestions": [],
                "citation_accuracy": 0.0,
                "fact_accuracy": 0.0,
                "error": str(e),
            }

        if not llm_output or not llm_output.strip():
            logger.warning("LLM returned empty output for review")
            return {
                "approved": False,
                "degraded": True,
                "agent": self.name,
                "issues": [],
                "suggestions": [],
                "citation_accuracy": 0.0,
                "fact_accuracy": 0.0,
                "error": "LLM returned empty output",
            }

        self.state.update_progress(0.7, "Parsing review result")

        parsed = self._parse_review_result(llm_output)

        approved = self._determine_approval(parsed)

        issues = self._extract_issues(parsed)
        suggestions = self._extract_suggestions(parsed)
        citation_accuracy = self._calculate_citation_accuracy_from_result(parsed)
        fact_accuracy = self._calculate_fact_accuracy_from_result(parsed)

        self.state.update_progress(1.0, "Review completed")

        return {
            "approved": approved,
            "issues": issues,
            "suggestions": suggestions,
            "citation_accuracy": citation_accuracy,
            "fact_accuracy": fact_accuracy,
            "review_result": parsed.get("review_result", "需修改"),
            "fact_check": parsed.get("fact_check", []),
            "citation_check": parsed.get("citation_check", {}),
        }

    def _parse_review_result(self, llm_output: str) -> dict:
        """4级JSON解析降级：标准JSON → 代码块提取 → 正则提取 → 规则兜底"""
        if not llm_output or not llm_output.strip():
            return self._rule_based_review()

        cleaned = llm_output.strip()

        # Level 1: 标准JSON解析
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Level 2: 提取```json```代码块
        json_match = re.search(r"```json\s*(.*?)\s*```", cleaned, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON from ```json block")

        # Level 3: 提取任意```代码块
        code_match = re.search(r"```\s*(.*?)\s*```", cleaned, re.DOTALL)
        if code_match:
            try:
                return json.loads(code_match.group(1))
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON from ``` block")

        # Level 3.5: 提取首个{}块
        try:
            brace_start = cleaned.find("{")
            brace_end = cleaned.rfind("}")
            if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
                json_candidate = cleaned[brace_start:brace_end + 1]
                return json.loads(json_candidate)
        except json.JSONDecodeError:
            logger.warning("Failed to extract JSON from text")

        # Level 4: 正则提取关键字段
        try:
            return self._regex_extract_review(cleaned)
        except Exception as e:
            logger.warning(f"Regex extraction also failed: {e}")

        return self._rule_based_review()

    def _regex_extract_review(self, text: str) -> dict:
        """正则提取关键字段"""
        review_result = "需修改"
        if "通过" in text and "需修改" not in text:
            review_result = "通过"

        accuracy_rate = 0.0
        rate_match = re.search(r"accuracy_rate[\":\s]+(\d+\.?\d*)", text)
        if rate_match:
            try:
                accuracy_rate = float(rate_match.group(1))
            except ValueError:
                pass

        return {
            "review_result": review_result,
            "fact_check": [],
            "citation_check": {
                "total_citations": 0,
                "accurate_citations": 0,
                "accuracy_rate": accuracy_rate,
            },
            "suggestions": [],
        }

    def _rule_based_review(self) -> dict:
        """规则兜底：返回默认未通过结果"""
        return {
            "review_result": "需修改",
            "fact_check": [],
            "citation_check": {
                "total_citations": 0,
                "accurate_citations": 0,
                "accuracy_rate": 0.0,
            },
            "suggestions": [
                {
                    "section": "整体",
                    "issue": "审核结果解析失败",
                    "suggestion": "请重新生成综述内容",
                    "error_type": "logic_gap",
                }
            ],
        }

    def _determine_approval(self, parsed: dict) -> bool:
        """计算审核通过判定"""
        review_result = parsed.get("review_result", "")
        if review_result == "通过":
            return True

        fact_accuracy = self._calculate_fact_accuracy_from_result(parsed)
        citation_accuracy = self._calculate_citation_accuracy_from_result(parsed)

        if fact_accuracy >= 0.9 and citation_accuracy >= 0.9:
            return True

        return False

    def _calculate_fact_accuracy_from_result(self, parsed: dict) -> float:
        """从审核结果计算事实准确率"""
        fact_check = parsed.get("fact_check", [])
        if not fact_check:
            return 0.0

        accurate_count = 0
        for item in fact_check:
            if item.get("accurate", False):
                accurate_count += 1

        return round(accurate_count / len(fact_check), 4)

    def _calculate_citation_accuracy_from_result(self, parsed: dict) -> float:
        """从审核结果计算引用准确率"""
        citation_check = parsed.get("citation_check", {})
        if not citation_check:
            return 0.0

        accuracy_rate = citation_check.get("accuracy_rate", 0.0)
        try:
            return float(accuracy_rate)
        except (TypeError, ValueError):
            return 0.0

    def _extract_issues(self, parsed: dict) -> List[dict]:
        """提取问题列表"""
        issues: List[dict] = []
        fact_check = parsed.get("fact_check", [])
        for item in fact_check:
            if not item.get("accurate", True):
                issues.append({
                    "claim": item.get("claim", ""),
                    "error_type": item.get("error_type", "factual_error"),
                    "note": item.get("note", ""),
                })

        citation_check = parsed.get("citation_check", {})
        for item in citation_check.get("inaccurate_citations", []):
            issues.append({
                "citation": item.get("citation", ""),
                "error_type": item.get("error_type", "citation_error"),
                "issue": item.get("issue", ""),
            })

        return issues

    def _extract_suggestions(self, parsed: dict) -> List[dict]:
        """提取修改建议列表"""
        return parsed.get("suggestions", [])

    def _fallback_result(self, input_data: dict) -> dict:
        """降级时返回 approved=False（默认不通过），标注 degraded=True"""
        return {
            "approved": False,
            "degraded": True,
            "agent": self.name,
            "issues": [],
            "suggestions": [],
            "citation_accuracy": 0.0,
            "fact_accuracy": 0.0,
            "error": self.state.error,
        }

    def _summarize_result(self, result: dict) -> str:
        """摘要包含审核结果、问题数量、引用准确率"""
        approved = result.get("approved", False)
        status = "通过" if approved else "不通过"
        issue_count = len(result.get("issues", []))
        citation_accuracy = result.get("citation_accuracy", 0.0)
        return f"审核{status}，问题{issue_count}个，引用准确率{citation_accuracy:.0%}"

    def _get_personalization_instruction(self, context: dict) -> str:
        """获取个性化指令片段（降级安全）"""
        if self.personalization_service is None:
            return ""
        user_profile = context.get("user_profile")
        if not user_profile:
            return ""
        try:
            return self.personalization_service.get_personalization_for_agent(
                "reviewer", user_profile
            )
        except Exception as e:
            logger.warning(f"Personalization injection failed for reviewer: {e}")
            return ""
