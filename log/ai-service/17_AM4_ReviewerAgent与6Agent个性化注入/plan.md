# Task 36-41 实施计划：AM4 6-Agent协同与个性化引擎

## 概述

本计划覆盖 AM4 里程碑的 6 个任务（Task 36-41），实现 ReviewerAgent、审核重试闭环、个性化引擎完善、6-Agent 全链路个性化注入。

## 当前状态分析

### 已实现
- `base.py` — BaseAgent 基类完整
- `coordinator.py` — CoordinatorAgent 完整，但未接入 graph/orchestrator
- `retriever.py` — RetrieverAgent 完整
- `analyzer.py` — AnalyzerAgent 完整
- `comparer.py` — ComparerAgent 完整，但未接入 graph/orchestrator
- `generator.py` — GeneratorAgent 完整（含内置个性化映射）
- `personalization_service.py` — 基础版完整（DIFFICULTY_MAP 仅数值，STYLE_MAP 仅 3 维度）
- `prompts/reviewer.txt` — 基础模板存在（$variable 语法，非 7-Block 结构）
- `graph.py` — 3 节点线性图（retrieve→analyze→generate），WorkflowState 已预留 review_result/regenerate_count
- `orchestrator.py` — 3 节点流式编排，NODE_ORDER=["retriever","analyzer","generator"]

### 缺失
- `reviewer.py` — 不存在
- `citation_parser.py` — 不存在（引用提取逻辑内嵌在 generator.py）
- graph.py 缺少 coordinator/comparer/reviewer 节点和条件边
- orchestrator.py 缺少 coordinator/comparer/reviewer
- DIFFICULTY_MAP 仅 `{beginner: 1}` 数值映射
- STYLE_MAP 仅 3 维度（tone/paragraph/structure）
- 6-Agent 个性化注入仅 generator/analyzer 部分支持

### 关键问题
1. `generator.py` 内部有一套独立的 DIFFICULTY_MAP/STYLE_MAP/EDUCATION_ADAPTATION/FIELD_EMPHASIS，与 PersonalizationService 重复
2. `prompts/reviewer.txt` 使用 `$variable` 语法，需改为 `${variable}` 以兼容 PromptManager
3. WorkflowState 已有 `regenerate_count` 字段但未使用

## 任务依赖关系

```
Task 37 (Prompt+CitationParser) ──→ Task 36 (ReviewerAgent) ──→ Task 38 (Graph+Orchestrator)
Task 40 (Mapping增强) ──→ Task 39 (Personalization完善) ──→ Task 41 (注入+测试)
```

## 实施步骤

### Step 1: Task 37 — Reviewer Prompt 增强 + Citation Parser

**文件 1**: `Veritas/ai-service/prompts/reviewer.txt`（修改）

- 重构为 7-Block 结构：Role Block / Task Block / Input Block / Review Chain / Output Schema / Constraint Block / Fallback Block
- 变量语法从 `$report_content`/`$original_papers` 改为 `${report_content}`/`${original_papers}`
- 新增 `${retry_context}` 变量（审核重试时传递上次问题列表）
- 增强引用校验规则：引用格式标准 `[作者, 年份]`、引用准确性/完整性/一致性校验
- 增加错误分类标准：factual_error / citation_error / logic_gap / info_missing
- 审核通过条件：事实准确率>90% 且 引用准确率>90%

**文件 2**: `Veritas/ai-service/app/utils/citation_parser.py`（新建）

- `extract_citations(report: str) -> list`：正则提取 `[作者, 年份]` 和 `(Author, Year)` 两种格式
- `validate_citations(extracted_citations: list, paper_list: list) -> dict`：比对引用与论文列表，返回 matched/unmatched/not_found
- `calculate_citation_accuracy(validation_result: dict) -> float`：计算准确率 0.0-1.0
- 仅依赖 `re` 和 `typing`，不依赖 Agent 框架
- 异常安全：不抛异常，返回空列表/0.0 兜底

**测试文件**: `Veritas/ai-service/tests/test_citation_parser.py`（新建）

- test_extract_author_year / test_extract_parentheses / test_empty_report / test_no_citations / test_validate_accuracy

### Step 2: Task 36 — ReviewerAgent 核心

**文件**: `Veritas/ai-service/app/agents/reviewer.py`（新建）

- `ReviewerAgent(BaseAgent)` 类，`name='reviewer'`
- 构造函数：`__init__(self, llm_service, prompt_manager)`
- `build_prompt(input_data, context)`：获取 report + original_papers，调用 `prompt_manager.get_prompt('reviewer', report_content=report, original_papers=json.dumps(papers), retry_context=retry_context)`
- `_run(prompt, input_data, context)`：
  1. 调用 `llm_service.generate(prompt)`
  2. 4 级 JSON 解析降级：标准 JSON → ```json``` 代码块 → 正则提取关键字段 → 规则兜底
  3. 计算审核通过判定：`approved = review_result=='通过' OR (fact_accuracy>90% AND citation_accuracy>90%)`
  4. 返回 `{approved, issues, suggestions, citation_accuracy, fact_accuracy, degraded}`
- `_fallback_result(input_data)`：覆盖基类，返回 `{approved: False, degraded: True, issues: [], suggestions: [], citation_accuracy: 0.0}`
- `_summarize_result(result)`：覆盖基类，返回审核状态摘要

**测试文件**: `Veritas/ai-service/tests/test_reviewer.py`（新建）

- test_creation / test_build_prompt / test_run_approved / test_run_rejected / test_json_parse_fallback / test_timeout_fallback / test_accuracy_calculation

### Step 3: Task 38 — Review Retry + Graph Integration

**文件 1**: `Veritas/ai-service/app/agents/graph.py`（修改）

- 新增 `review_node(state)` 异步函数：
  - 从 state 获取 report 和 search_results
  - 调用 ReviewerAgent.execute()
  - 更新 state 的 review_result
  - Reviewer 不存在时跳过审核，直接标记通过
- 新增 `should_review(state)` 条件函数：
  - report 非空且非退化 → True（进入审核）
  - 否则 → False（直接结束）
- 新增 `should_regenerate(state)` 条件函数：
  - `approved=False` 且 `regenerate_count < 1` → True（重新生成）
  - 否则 → False（结束）
- 修改 `generate_node`：当 `regenerate_count > 0` 时，将 review_result 中的 issues/suggestions 注入 Generator 的 input_data
- 扩展 `build_agent_graph()`：
  - 添加 generate → review 边
  - 添加 review 的条件边：should_regenerate True→generate, False→END
  - 注意：不破坏已有 3 节点工作流（向后兼容）
- 更新 WorkflowState：确认 regenerate_count 字段存在

**文件 2**: `Veritas/ai-service/app/agents/orchestrator.py`（修改）

- NODE_ORDER 增加 `'reviewer'`
- `run_workflow_stream()` 增加 Reviewer 执行段：
  - yield `agent_started` / `agent_state_update` / `agent_completed` / `agent_failed` 事件
  - 审核不通过时 yield `review_rejected` 事件，回到 Generator
  - 最多重试 1 次
- 使用 `_make_event()` 统一构造 SSE 事件（不硬编码格式）
- Reviewer 不存在时跳过审核

**测试文件**: `Veritas/ai-service/tests/test_graph_integration.py`（新建）

- test_should_review_true / test_should_review_false_empty / test_should_review_false_degraded
- test_should_regenerate_true / test_should_regenerate_false_approved / test_should_regenerate_false_max_retry
- test_full_workflow_6_agents / test_review_rejected_regenerate / test_review_agent_not_found_skip / test_review_agent_timeout_degraded

### Step 4: Task 40 — Difficulty/Style Mapping 增强

**文件**: `Veritas/ai-service/app/services/personalization_service.py`（修改）

- 增强 DIFFICULTY_MAP：从 `{beginner: 1}` 扩展为策略对象
  ```python
  DIFFICULTY_MAP = {
      "beginner": {"level": 1, "term_density": 0.05, "explanation_style": "通俗类比+日常例子+避免术语", "example_requirement": "每个概念至少1个日常类比", "abstraction_level": "具体→抽象，逐步引导", "citation_depth": "仅引用核心结论"},
      "intermediate": {"level": 2, "term_density": 0.2, ...},
      "advanced": {"level": 3, "term_density": 0.4, ...},
      "expert": {"level": 4, "term_density": 0.5, ...}
  }
  ```
- 增强 STYLE_MAP：从 3 维度扩展为 7 维度
  ```python
  STYLE_MAP = {
      "simple": {"tone": "...", "paragraph": "...", "structure": "...", "structure_example": "引言→要点→总结", "sentence_pattern": "短句为主，每句不超过25字", "transition_style": "使用首先/其次/最后", "audience_awareness": "面向非专业读者"},
      ...
  }
  ```
- 增强 EDUCATION_ADAPTATION：从文本扩展为策略对象（background_knowledge / methodology_focus / innovation_emphasis / teaching_applicability）
- 增强 FIELD_EMPHASIS：从文本扩展为策略对象（primary_keywords / secondary_keywords / methodology_bias / evaluation_focus）
- 确保所有现有方法向后兼容（get_education_adaptation / get_term_density_target / get_style_guide / get_field_emphasis）

**测试文件**: `Veritas/ai-service/tests/test_personalization_service.py`（修改，新增测试）

- test_difficulty_map_all_levels_have_5_dimensions / test_style_map_all_styles_have_7_dimensions
- test_education_adaptation_all_levels_have_4_dimensions / test_field_emphasis_all_fields_have_4_dimensions
- test_backward_compatibility_all_methods / test_difficulty_map_default_fallback

### Step 5: Task 39 — Personalization Service 完善

**文件**: `Veritas/ai-service/app/services/personalization_service.py`（修改）

- 新增 `AGENT_PERSONALIZATION_MAP`：6 个 Agent 的个性化指令模板
  - 每个 Agent 含 `knowledge_level_instructions`（4 级）和 `education_level_instructions`（4 级）
  - coordinator：任务分解策略（beginner→细化子任务+背景补充，expert→聚焦前沿+研究空白）
  - retriever：检索关键词权重 + 检索数量适配（beginner→Top5, expert→Top20）
  - analyzer：分析深度适配
  - comparer：对比维度数量（beginner→3, expert→6）+ 对比深度
  - generator：写作风格（已有，复用）
  - reviewer：审核严格度（beginner→基础准确性，expert→前沿准确性+引用完整性）
- 新增 `get_personalization_for_agent(agent_name, user_profile)` 方法
- 新增 `get_personalization_diff(profile_a, profile_b)` 方法：计算差异度 0-1
- 增强 `_build_user_profile_summary()`：包含 5 个维度信息

**测试文件**: `Veritas/ai-service/tests/test_personalization_service.py`（修改，新增测试）

- test_get_personalization_for_agent_all_six / test_agent_personalization_map_coverage
- test_get_personalization_diff / test_personalization_fallback / test_enhanced_user_profile_summary

### Step 6: Task 41 — 个性化 Prompt 注入 + 效果测试

**文件 1-6**: 6 个 Agent 的 build_prompt() 修改

- `coordinator.py`：在 build_prompt() 末尾追加 `personalization_service.get_personalization_for_agent('coordinator', user_profile)`，使用 `【个性化适配】` 标记
- `retriever.py`：同上，注入领域侧重和检索数量适配
- `analyzer.py`：从 `get_extra_instruction()` 迁移到 `get_personalization_for_agent('analyzer', user_profile)`
- `comparer.py`：注入对比深度适配
- `generator.py`：统一使用 `get_personalization_for_agent('generator', user_profile)`
- `reviewer.py`：注入审核严格度适配

所有注入使用 try-except 包裹，失败时降级为默认指令。

**文件 7**: `Veritas/ai-service/tests/test_personalization_e2e.py`（新建）

- test_personalization_diversity_e2e：两个极端画像差异度>60%
- test_four_dimension_effectiveness：4 维度画像生效验证
- test_personalization_full_pipeline：6-Agent 个性化链路完整性
- test_personalization_empty_profile_fallback：空画像降级

**文件 8**: `Veritas/ai-service/tests/test_personalization_service.py`（修改，新增测试）

- test_coordinator_build_prompt_has_personalization / test_retriever_build_prompt_has_personalization
- test_comparer_build_prompt_has_personalization / test_reviewer_build_prompt_has_personalization
- test_all_six_agents_personalization_injection / test_personalization_empty_profile_fallback

## 关键决策

1. **Prompt 变量语法**：统一使用 `${variable}` 语法，兼容 PromptManager 的 `re.sub(r'\$\{(\w+)\}', r'$\1', template)` 预处理
2. **DIFFICULTY_MAP 结构变更兼容**：新增 `level` key 保留原数值，现有方法 `get_term_density_target()` 改为从策略对象读取
3. **generator.py 重复映射处理**：Task 41 中统一 generator.py 使用 PersonalizationService，移除内部重复映射
4. **graph.py 向后兼容**：新增节点和条件边不破坏已有 3 节点线性流程，reviewer 不存在时跳过审核
5. **个性化注入方式**：通过 context 中的 personalization_service 实例调用，不直接实例化

## 验证步骤

1. `cd Veritas/ai-service && python -m pytest tests/test_citation_parser.py -v` — Task 37
2. `cd Veritas/ai-service && python -m pytest tests/test_reviewer.py -v` — Task 36
3. `cd Veritas/ai-service && python -m pytest tests/test_graph_integration.py -v` — Task 38
4. `cd Veritas/ai-service && python -m pytest tests/test_personalization_service.py -v` — Task 39+40
5. `cd Veritas/ai-service && python -m pytest tests/test_personalization_e2e.py -v` — Task 41
6. `cd Veritas/ai-service && python -m pytest tests/ -v --ignore=tests/test_graph_integration.py --ignore=tests/test_personalization_e2e.py` — 已有测试无回归
