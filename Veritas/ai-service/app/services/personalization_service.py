import json
from pathlib import Path
from string import Template
from typing import Any, Dict, List, Optional

from loguru import logger


DIFFICULTY_MAP = {
    "beginner": {
        "level": 1,
        "term_density": 0.05,
        "explanation_style": "通俗类比+日常例子+避免术语",
        "example_requirement": "每个概念至少1个日常类比",
        "abstraction_level": "具体→抽象，逐步引导",
        "citation_depth": "仅引用核心结论",
    },
    "intermediate": {
        "level": 2,
        "term_density": 0.20,
        "explanation_style": "标准学术+术语定义+方法对比",
        "example_requirement": "关键方法需举例说明",
        "abstraction_level": "具体与抽象结合",
        "citation_depth": "引用方法+结论",
    },
    "advanced": {
        "level": 3,
        "term_density": 0.40,
        "explanation_style": "专业学术+深入分析+前沿讨论",
        "example_requirement": "仅在复杂概念时举例",
        "abstraction_level": "抽象为主，具体为辅",
        "citation_depth": "引用方法+实验+结论+局限",
    },
    "expert": {
        "level": 4,
        "term_density": 0.50,
        "explanation_style": "高度专业+数学原理+创新洞察",
        "example_requirement": "不需要示例，直接讨论",
        "abstraction_level": "纯抽象讨论，预设背景知识",
        "citation_depth": "完整引用含数学推导+实验细节+消融实验",
    },
}

STYLE_MAP = {
    "simple": {
        "tone": "日常用语+比喻",
        "paragraph": "短段落，口语化表达",
        "structure": "先举例后总结",
        "structure_example": "引言→要点→总结",
        "sentence_pattern": "短句为主，每句不超过25字，口语化表达",
        "transition_style": "使用首先/其次/最后",
        "audience_awareness": "面向非专业读者，避免行话",
    },
    "balanced": {
        "tone": "标准学术",
        "paragraph": "中等段落，逻辑清晰",
        "structure": "先总后分，标准学术结构",
        "structure_example": "引言→背景→对比→趋势→结论",
        "sentence_pattern": "中等句长，15-35字，逻辑连接词丰富",
        "transition_style": "使用此外/然而/因此",
        "audience_awareness": "面向有基础知识的读者，适度使用术语",
    },
    "technical": {
        "tone": "正式学术+引用",
        "paragraph": "长段落，严密论证",
        "structure": "严格学术结构，含公式和引用标注",
        "structure_example": "引言→相关工作→方法→实验→讨论→结论",
        "sentence_pattern": "长句为主，25-50字，含从句和嵌套结构",
        "transition_style": "使用基于上述/综上所述/值得注意的是",
        "audience_awareness": "面向领域专家，可直接使用专业术语",
    },
}

EDUCATION_ADAPTATION = {
    "undergraduate": {
        "text": "适当补充背景知识，使用类比说明，帮助建立知识体系",
        "background_knowledge": "补充基础概念和背景知识，使用类比帮助理解",
        "methodology_focus": "侧重方法的基本原理和应用场景",
        "innovation_emphasis": "关注方法的直观理解和实际应用",
        "teaching_applicability": "强调知识体系的建立和学习路径",
    },
    "master": {
        "text": "侧重方法论对比和实验设计分析，关注技术细节",
        "background_knowledge": "适度补充背景，重点在于方法论对比",
        "methodology_focus": "侧重方法论对比和实验设计分析",
        "innovation_emphasis": "关注技术创新点和实现细节",
        "teaching_applicability": "分析方法在教学和研究中的应用",
    },
    "phd": {
        "text": "关注创新点和前沿贡献，分析可扩展的研究方向",
        "background_knowledge": "预设背景知识，直接讨论前沿",
        "methodology_focus": "深入分析方法论的理论基础和数学原理",
        "innovation_emphasis": "关注研究创新点和前沿贡献，分析可扩展的研究方向",
        "teaching_applicability": "分析该研究对学科发展的推动作用",
    },
    "faculty": {
        "text": "关注教学适用性和知识体系构建，分析该研究在教学中的应用价值",
        "background_knowledge": "关注知识体系的完整性和教学适用性",
        "methodology_focus": "侧重方法的教学适用性和知识体系构建",
        "innovation_emphasis": "关注研究对学科知识体系的贡献",
        "teaching_applicability": "分析该研究在教学和学科发展中的应用价值",
    },
}

FIELD_EMPHASIS = {
    "NLP": {
        "text": "侧重自然语言处理相关方法和应用",
        "primary_keywords": ["自然语言处理", "文本分析", "语言模型", "语义理解"],
        "secondary_keywords": ["词嵌入", "注意力机制", "序列标注", "文本生成"],
        "methodology_bias": "侧重语言模型和文本处理方法",
        "evaluation_focus": "关注BLEU/ROUGE/困惑度等NLP指标",
    },
    "CV": {
        "text": "侧重计算机视觉相关方法和应用",
        "primary_keywords": ["计算机视觉", "图像识别", "目标检测", "图像分割"],
        "secondary_keywords": ["卷积网络", "特征提取", "视觉Transformer", "图像生成"],
        "methodology_bias": "侧重视觉模型和图像处理方法",
        "evaluation_focus": "关注mAP/IoU/准确率等CV指标",
    },
    "RL": {
        "text": "侧重强化学习相关方法和应用",
        "primary_keywords": ["强化学习", "策略优化", "奖励函数", "探索与利用"],
        "secondary_keywords": ["Q学习", "策略梯度", "多智能体", "模拟环境"],
        "methodology_bias": "侧重策略优化和奖励设计方法",
        "evaluation_focus": "关注累积奖励/收敛速度/样本效率等RL指标",
    },
    "多模态": {
        "text": "侧重多模态融合相关方法和应用",
        "primary_keywords": ["多模态", "跨模态", "视觉语言", "模态融合"],
        "secondary_keywords": ["对齐", "联合嵌入", "跨模态注意力", "模态缺失"],
        "methodology_bias": "侧重跨模态对齐和融合方法",
        "evaluation_focus": "关注跨模态检索/对齐精度等指标",
    },
    "知识图谱": {
        "text": "侧重知识图谱构建与推理相关方法和应用",
        "primary_keywords": ["知识图谱", "实体关系", "图推理", "知识嵌入"],
        "secondary_keywords": ["图神经网络", "链接预测", "实体对齐", "知识补全"],
        "methodology_bias": "侧重图结构和知识推理方法",
        "evaluation_focus": "关注Hits@K/MRR等知识图谱指标",
    },
    "推荐系统": {
        "text": "侧重推荐算法与用户建模相关方法和应用",
        "primary_keywords": ["推荐系统", "协同过滤", "用户建模", "个性化推荐"],
        "secondary_keywords": ["矩阵分解", "深度推荐", "冷启动", "多样性"],
        "methodology_bias": "侧重推荐算法和用户画像方法",
        "evaluation_focus": "关注NDCG/Recall/点击率等推荐指标",
    },
    "数据挖掘": {
        "text": "侧重数据挖掘与模式发现相关方法和应用",
        "primary_keywords": ["数据挖掘", "模式发现", "聚类分析", "异常检测"],
        "secondary_keywords": ["关联规则", "时序分析", "特征选择", "降维"],
        "methodology_bias": "侧重数据分析和模式挖掘方法",
        "evaluation_focus": "关注F1/AUC/覆盖率等挖掘指标",
    },
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

AGENT_PERSONALIZATION_MAP = {
    "coordinator": {
        "knowledge_level_instructions": {
            "beginner": "将任务分解为更细粒度的子任务，每个子任务附带背景知识补充。优先安排基础概念检索。",
            "intermediate": "按标准流程分解任务，确保每个子任务目标明确。安排方法论对比检索。",
            "advanced": "聚焦前沿研究和方法论深度分析，安排研究空白探索。减少基础概念检索。",
            "expert": "聚焦最前沿研究和创新方向，安排深度技术分析和跨领域关联探索。",
        },
        "education_level_instructions": {
            "undergraduate": "任务分解时增加背景知识检索子任务，帮助建立知识体系。",
            "master": "任务分解时侧重方法论对比和实验设计分析。",
            "phd": "任务分解时关注创新点和前沿贡献，安排可扩展方向探索。",
            "faculty": "任务分解时关注教学适用性和知识体系构建。",
        },
    },
    "retriever": {
        "knowledge_level_instructions": {
            "beginner": "检索Top5论文，侧重综述性和入门级论文。使用通俗关键词。",
            "intermediate": "检索Top10论文，兼顾综述和原始研究。使用标准学术关键词。",
            "advanced": "检索Top15论文，侧重原始研究和前沿工作。使用专业学术关键词。",
            "expert": "检索Top20论文，侧重最新前沿和突破性工作。使用精确学术术语。",
        },
        "education_level_instructions": {
            "undergraduate": "增加综述性论文的检索权重，降低技术深度要求。",
            "master": "平衡综述和原始研究论文，关注方法论细节。",
            "phd": "侧重原始研究论文和前沿工作，关注创新点。",
            "faculty": "兼顾教学适用性论文和前沿研究，关注知识体系。",
        },
    },
    "analyzer": {
        "knowledge_level_instructions": _ANALYZER_INSTRUCTIONS,
        "education_level_instructions": _ANALYZER_EDUCATION_INSTRUCTIONS,
    },
    "comparer": {
        "knowledge_level_instructions": {
            "beginner": "使用3个对比维度（研究问题、核心方法、主要结论），用通俗语言对比。",
            "intermediate": "使用4个对比维度（研究问题、核心方法、实验设计、主要结论），标准学术对比。",
            "advanced": "使用5个对比维度（研究问题、核心方法、实验设计、主要结论、局限性），深入专业对比。",
            "expert": "使用6个对比维度（研究问题、核心方法、实验设计、主要结论、局限性、创新点），全面深度对比。",
        },
        "education_level_instructions": {
            "undergraduate": "对比时补充背景知识，使用类比说明方法差异。",
            "master": "对比时侧重方法论差异和实验设计对比。",
            "phd": "对比时关注创新点差异和研究空白分析。",
            "faculty": "对比时关注教学适用性和知识体系差异。",
        },
    },
    "generator": {
        "knowledge_level_instructions": _GENERATOR_INSTRUCTIONS,
        "education_level_instructions": _GENERATOR_EDUCATION_INSTRUCTIONS,
    },
    "reviewer": {
        "knowledge_level_instructions": {
            "beginner": "审核时关注基础准确性：论断是否与原文一致，引用是否正确。降低审核严格度，重点关注事实错误。",
            "intermediate": "审核时关注方法论准确性和引用完整性。标准审核严格度。",
            "advanced": "审核时关注前沿准确性、引用完整性和逻辑严谨性。提高审核严格度。",
            "expert": "审核时关注前沿准确性、引用完整性、逻辑严谨性和数学推导正确性。最高审核严格度。",
        },
        "education_level_instructions": {
            "undergraduate": "审核时容忍通俗化表述，关注基础事实准确性。",
            "master": "审核时关注方法论描述准确性和实验结果一致性。",
            "phd": "审核时关注创新点描述准确性和前沿引用完整性。",
            "faculty": "审核时关注知识体系完整性和教学适用性。",
        },
    },
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

    def get_personalization_for_agent(
        self, agent_name: str, user_profile: dict
    ) -> str:
        """为指定Agent返回个性化指令片段"""
        try:
            profile = self._normalize_profile(user_profile)
            knowledge_level = profile.get("knowledge_level", _DEFAULT_KNOWLEDGE)
            education_level = profile.get("education_level", _DEFAULT_EDUCATION)

            agent_map = AGENT_PERSONALIZATION_MAP.get(agent_name)
            if agent_map is None:
                return ""

            knowledge_instructions = agent_map.get("knowledge_level_instructions", {})
            education_instructions = agent_map.get("education_level_instructions", {})

            parts: List[str] = []

            knowledge_instruction = knowledge_instructions.get(
                knowledge_level, knowledge_instructions.get(_DEFAULT_KNOWLEDGE, "")
            )
            if knowledge_instruction:
                parts.append(knowledge_instruction)

            education_instruction = education_instructions.get(
                education_level, education_instructions.get(_DEFAULT_EDUCATION, "")
            )
            if education_instruction:
                parts.append(education_instruction)

            return " ".join(parts) if parts else ""
        except Exception as e:
            logger.warning(f"get_personalization_for_agent failed: {e}")
            return ""

    def get_personalization_diff(
        self, profile_a: dict, profile_b: dict
    ) -> float:
        """计算两个用户画像的个性化差异度（0-1）"""
        try:
            norm_a = self._normalize_profile(profile_a)
            norm_b = self._normalize_profile(profile_b)

            dimensions = ["education_level", "knowledge_level", "preferred_style", "research_field"]
            diff_count = 0

            for dim in dimensions:
                val_a = norm_a.get(dim, "")
                val_b = norm_b.get(dim, "")
                if val_a != val_b:
                    diff_count += 1

            return round(diff_count / len(dimensions), 4)
        except Exception as e:
            logger.warning(f"get_personalization_diff failed: {e}")
            return 0.0

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
        entry = EDUCATION_ADAPTATION.get(education_level)
        if entry is None:
            entry = EDUCATION_ADAPTATION.get(_DEFAULT_EDUCATION)
        if isinstance(entry, dict):
            return entry.get("text", "")
        return str(entry)

    def get_term_density_target(self, knowledge_level: str) -> float:
        entry = DIFFICULTY_MAP.get(knowledge_level)
        if isinstance(entry, dict):
            return entry.get("term_density", TERM_DENSITY_TARGET.get(_DEFAULT_KNOWLEDGE, 0.20))
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
        entry = FIELD_EMPHASIS.get(research_field)
        if entry is None:
            return ""
        if isinstance(entry, dict):
            return entry.get("text", "")
        return str(entry)

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

        difficulty = DIFFICULTY_MAP.get(knowledge_level, {})
        term_density = difficulty.get("term_density", 0.20) if isinstance(difficulty, dict) else 0.20

        parts = [edu_label]
        if research_field:
            parts.append(f"{research_field}方向")
        parts.append(f"{know_label}知识水平")
        parts.append(f"{style_label}风格")
        parts.append(f"术语密度{int(term_density * 100)}%")

        return "/".join(parts)
