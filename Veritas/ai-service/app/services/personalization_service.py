import json
from pathlib import Path
from string import Template
from typing import Any, Dict, List, Optional

from loguru import logger


DIFFICULTY_MAP = {
    "beginner": 1,
    "intermediate": 2,
    "advanced": 3,
    "expert": 4,
}

STYLE_MAP = {
    "simple": {
        "tone": "日常用语+比喻",
        "paragraph": "短段落，口语化表达",
        "structure": "先举例后总结",
    },
    "balanced": {
        "tone": "标准学术",
        "paragraph": "中等段落，逻辑清晰",
        "structure": "先总后分，标准学术结构",
    },
    "technical": {
        "tone": "正式学术+引用",
        "paragraph": "长段落，严密论证",
        "structure": "严格学术结构，含公式和引用标注",
    },
}

EDUCATION_ADAPTATION = {
    "undergraduate": "适当补充背景知识，使用类比说明，帮助建立知识体系",
    "master": "侧重方法论对比和实验设计分析，关注技术细节",
    "phd": "关注创新点和前沿贡献，分析可扩展的研究方向",
    "faculty": "关注教学适用性和知识体系构建，分析该研究在教学中的应用价值",
}

FIELD_EMPHASIS = {
    "NLP": "侧重自然语言处理相关方法和应用",
    "CV": "侧重计算机视觉相关方法和应用",
    "RL": "侧重强化学习相关方法和应用",
    "多模态": "侧重多模态融合相关方法和应用",
    "知识图谱": "侧重知识图谱构建与推理相关方法和应用",
    "推荐系统": "侧重推荐算法与用户建模相关方法和应用",
    "数据挖掘": "侧重数据挖掘与模式发现相关方法和应用",
}

TERM_DENSITY_TARGET = {
    "beginner": 0.05,
    "intermediate": 0.20,
    "advanced": 0.40,
    "expert": 0.50,
}

_CAMEL_TO_SNAKE_MAP = {
    "educationLevel": "education_level",
    "knowledgeLevel": "knowledge_level",
    "preferredStyle": "preferred_style",
    "researchField": "research_field",
}

_DEFAULT_EDUCATION = "master"
_DEFAULT_KNOWLEDGE = "intermediate"
_DEFAULT_STYLE = "balanced"
_DEFAULT_FIELD = ""

_ANALYZER_INSTRUCTIONS = {
    "beginner": "请用通俗解释和类比说明，避免过多专业术语。对于复杂概念，请配合日常例子说明。",
    "intermediate": "请使用标准学术语言，适当引入术语定义。重点分析方法对比和实现细节。",
    "advanced": "请使用专业学术语言，深入分析研究空白和技术细节。讨论前沿趋势和潜在改进方向。",
    "expert": "请使用高度专业的学术语言，提供前沿洞察和创新建议。深入剖析方法论的数学原理和理论依据。",
}

_ANALYZER_EDUCATION_INSTRUCTIONS = {
    "undergraduate": "适当补充背景知识，帮助建立知识体系。",
    "master": "侧重方法论对比和实验设计分析。",
    "phd": "关注研究创新点和前沿贡献，分析可扩展的研究方向。",
    "faculty": "关注教学适用性和学科知识体系构建。分析该研究在教学中的应用价值。",
}

_GENERATOR_INSTRUCTIONS = {
    "beginner": "综述应使用通俗易懂的语言，配合日常类比说明专业概念，避免堆砌术语。",
    "intermediate": "综述应使用标准学术语言，适度使用专业术语，注重方法论对比和实验结果分析。",
    "advanced": "综述应使用专业学术语言，深入分析技术细节和研究空白，讨论前沿趋势和改进方向。",
    "expert": "综述应使用高度专业的学术语言，提供前沿洞察和创新建议，深入剖析方法论的理论依据。",
}

_GENERATOR_EDUCATION_INSTRUCTIONS = {
    "undergraduate": "写作时适当补充背景知识，使用类比帮助理解，注重知识体系的建立。",
    "master": "侧重方法论对比和实验设计分析，关注技术细节和实现方案。",
    "phd": "关注研究创新点和前沿贡献，分析可扩展的研究方向和潜在突破点。",
    "faculty": "关注教学适用性和知识体系构建，分析该研究在教学和学科发展中的应用价值。",
}


class PersonalizationService:

    def __init__(self, prompt_manager=None) -> None:
        self.prompt_manager = prompt_manager

    def get_personalization_block(self, user_profile: dict) -> str:
        profile = self._normalize_profile(user_profile)
        education_level = profile.get("education_level", _DEFAULT_EDUCATION)
        knowledge_level = profile.get("knowledge_level", _DEFAULT_KNOWLEDGE)
        preferred_style = profile.get("preferred_style", _DEFAULT_STYLE)
        research_field = profile.get("research_field", _DEFAULT_FIELD)

        parts: List[str] = []

        edu_adapt = self.get_education_adaptation(education_level)
        parts.append(f"【学历适配】{edu_adapt}")

        target = self.get_term_density_target(knowledge_level)
        parts.append(f"【术语密度目标】{int(target * 100)}%")

        style_guide = self.get_style_guide(preferred_style)
        parts.append(f"【写作风格】{style_guide}")

        if research_field:
            field_emphasis = self.get_field_emphasis(research_field)
            if field_emphasis:
                parts.append(f"【领域侧重】{field_emphasis}")

        return "\n".join(parts)

    def get_extra_instruction(
        self, user_profile: dict, agent_name: str = ""
    ) -> str:
        profile = self._normalize_profile(user_profile)
        knowledge_level = profile.get("knowledge_level", _DEFAULT_KNOWLEDGE)
        education_level = profile.get("education_level", _DEFAULT_EDUCATION)

        instruction_parts: List[str] = []

        if agent_name == "analyzer":
            knowledge_instructions = _ANALYZER_INSTRUCTIONS
            education_instructions = _ANALYZER_EDUCATION_INSTRUCTIONS
        elif agent_name == "generator":
            knowledge_instructions = _GENERATOR_INSTRUCTIONS
            education_instructions = _GENERATOR_EDUCATION_INSTRUCTIONS
        else:
            knowledge_instructions = _ANALYZER_INSTRUCTIONS
            education_instructions = _ANALYZER_EDUCATION_INSTRUCTIONS

        instruction = knowledge_instructions.get(
            knowledge_level, knowledge_instructions[_DEFAULT_KNOWLEDGE]
        )
        instruction_parts.append(instruction)

        edu_instruction = education_instructions.get(education_level, "")
        if edu_instruction:
            instruction_parts.append(edu_instruction)

        return " ".join(instruction_parts) if instruction_parts else ""

    def build_generation_prompt(
        self,
        analysis_results: list,
        comparison_result: dict,
        user_profile: dict,
    ) -> str:
        personalization = self.get_personalization_block(user_profile)
        analysis_data = json.dumps(analysis_results, ensure_ascii=False)
        comparison_data = (
            json.dumps(comparison_result, ensure_ascii=False)
            if comparison_result
            else "无"
        )
        user_profile_summary = self._build_user_profile_summary(user_profile)

        template_kwargs = {
            "personalization": personalization,
            "analysis_data": analysis_data,
            "comparison_data": comparison_data,
            "user_profile_summary": user_profile_summary,
        }

        if self.prompt_manager is not None:
            try:
                return self.prompt_manager.get_prompt(
                    "generator", **template_kwargs
                )
            except Exception as e:
                logger.warning(
                    f"prompt_manager.get_prompt failed, falling back to file: {e}"
                )

        try:
            prompts_dir = Path("prompts")
            template_path = prompts_dir / "generator.txt"
            if not template_path.exists():
                for parent in Path.cwd().rglob("prompts"):
                    candidate = parent / "generator.txt"
                    if candidate.exists():
                        template_path = candidate
                        break

            content = template_path.read_text(encoding="utf-8")
            template = Template(content)
            return template.safe_substitute(**template_kwargs)
        except Exception as e:
            logger.warning(f"File-based template loading failed: {e}")
            return (
                f"分析数据：{analysis_data}\n"
                f"对比数据：{comparison_data}\n"
                f"个性化指令：{personalization}\n"
                f"用户画像：{user_profile_summary}"
            )

    def get_education_adaptation(self, education_level: str) -> str:
        return EDUCATION_ADAPTATION.get(
            education_level, EDUCATION_ADAPTATION[_DEFAULT_EDUCATION]
        )

    def get_term_density_target(self, knowledge_level: str) -> float:
        return TERM_DENSITY_TARGET.get(
            knowledge_level, TERM_DENSITY_TARGET[_DEFAULT_KNOWLEDGE]
        )

    def get_style_guide(self, preferred_style: str) -> str:
        style = STYLE_MAP.get(preferred_style, STYLE_MAP[_DEFAULT_STYLE])
        tone = style.get("tone", "")
        paragraph = style.get("paragraph", "")
        structure = style.get("structure", "")
        return f"{tone}；段落风格：{paragraph}；结构要求：{structure}"

    def get_field_emphasis(self, research_field: str) -> str:
        return FIELD_EMPHASIS.get(research_field, "")

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

    def _education_label(self, level: str) -> str:
        labels = {
            "undergraduate": "本科",
            "master": "硕士",
            "phd": "博士",
            "faculty": "教师",
        }
        return labels.get(level, "未知")

    def _knowledge_label(self, level: str) -> str:
        labels = {
            "beginner": "入门",
            "intermediate": "中级",
            "advanced": "进阶",
            "expert": "专家",
        }
        return labels.get(level, "未知")

    def _style_label(self, style: str) -> str:
        labels = {
            "simple": "通俗",
            "balanced": "均衡",
            "technical": "专业",
        }
        return labels.get(style, "未知")

    def _build_user_profile_summary(self, user_profile: dict) -> str:
        profile = self._normalize_profile(user_profile)
        education_level = profile.get("education_level", _DEFAULT_EDUCATION)
        knowledge_level = profile.get("knowledge_level", _DEFAULT_KNOWLEDGE)
        preferred_style = profile.get("preferred_style", _DEFAULT_STYLE)
        research_field = profile.get("research_field", _DEFAULT_FIELD)

        edu_label = self._education_label(education_level)
        know_label = self._knowledge_label(knowledge_level)
        style_label = self._style_label(preferred_style)

        parts = [edu_label]
        if research_field:
            parts.append(f"{research_field}方向")
        parts.append(f"{know_label}知识水平")
        parts.append(f"{style_label}风格")

        return "/".join(parts)
