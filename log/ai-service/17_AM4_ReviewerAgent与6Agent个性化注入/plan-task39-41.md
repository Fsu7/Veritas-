# Task 39-41 实施计划：PersonalizationService 完善 + 6-Agent 个性化 Prompt 注入

## 摘要

基于上下文恢复，Task 36-38（ReviewerAgent核心、Citation Parser、Review Retry Graph）已完成，Task 39-40 的代码变更已写入 `personalization_service.py`（DIFFICULTY_MAP/STYLE_MAP/EDUCATION_ADAPTATION/FIELD_EMPHASIS 增强 + AGENT_PERSONALIZATION_MAP + get_personalization_for_agent/get_personalization_diff），但**测试尚未运行验证**。Task 41（6-Agent 个性化 Prompt 注入 + e2e 测试）尚未开始。

本计划覆盖：
1. 验证 Task 39-40 已完成的代码变更（运行现有测试 + 新增测试）
2. 执行 Task 41（6-Agent 个性化注入 + e2e 测试）
3. 最终全量回归验证

---

## 当前状态分析

### 已完成（代码已写入，待测试验证）

| 文件 | 变更内容 | 状态 |
|------|---------|------|
| `personalization_service.py` | DIFFICULTY_MAP 6-key策略对象、STYLE_MAP 7维度、EDUCATION_ADAPTATION dict、FIELD_EMPHASIS dict、AGENT_PERSONALIZATION_MAP、get_personalization_for_agent()、get_personalization_diff()、增强_build_user_profile_summary() | 代码已写入，**未测试** |
| `reviewer.py` | ReviewerAgent 核心逻辑 | 已测试通过 |
| `citation_parser.py` | 引用解析工具 | 已测试通过 |
| `graph.py` | review_node + should_review/should_regenerate 条件边 | 已测试通过 |
| `orchestrator.py` | reviewer 重试循环 | 已测试通过 |

### 待完成

| 任务 | 文件 | 描述 |
|------|------|------|
| Task 39-40 测试 | `test_personalization_service.py` | 新增映射表结构验证 + 向后兼容测试 |
| Task 41 Step 1 | `coordinator.py` | build_prompt() 注入个性化指令 |
| Task 41 Step 2 | `retriever.py` | build_prompt() 注入个性化指令 + top_k 适配 |
| Task 41 Step 3 | `analyzer.py` | 从 get_extra_instruction() 迁移到 get_personalization_for_agent() |
| Task 41 Step 4 | `comparer.py` | build_prompt() 注入个性化指令 |
| Task 41 Step 5 | `generator.py` | 统一使用 get_personalization_for_agent() |
| Task 41 Step 6 | `reviewer.py` | build_prompt() 注入个性化指令 |
| Task 41 Step 7 | `test_personalization_e2e.py` | 端到端个性化效果测试 |

---

## 实施步骤

### Step 1: 验证 Task 39-40 — 运行现有 personalization 测试

**目标**：确认 personalization_service.py 增强后所有已有测试仍通过

**操作**：
```bash
cd Veritas/ai-service && python -m pytest tests/test_personalization_service.py -v
```

**预期**：16 个已有测试全部通过（向后兼容验证）

### Step 2: 新增 Task 39-40 测试用例

**文件**：`tests/test_personalization_service.py`（追加，不修改已有测试）

**新增测试**：

1. `test_difficulty_map_all_levels_have_6_keys` — 验证 DIFFICULTY_MAP 4个级别均包含 level/term_density/explanation_style/example_requirement/abstraction_level/citation_depth
2. `test_style_map_all_styles_have_7_keys` — 验证 STYLE_MAP 3个风格均包含 tone/paragraph/structure/structure_example/sentence_pattern/transition_style/audience_awareness
3. `test_education_adaptation_all_levels_have_strategy_dimensions` — 验证 EDUCATION_ADAPTATION 4个层次均包含 text/background_knowledge/methodology_focus/innovation_emphasis/teaching_applicability
4. `test_field_emphasis_all_fields_have_strategy_dimensions` — 验证 FIELD_EMPHASIS 7个领域均包含 text/primary_keywords/secondary_keywords/methodology_bias/evaluation_focus
5. `test_get_personalization_for_agent_all_six` — 验证 6 个 Agent 返回不同且非空的个性化指令
6. `test_agent_personalization_map_coverage` — 验证 AGENT_PERSONALIZATION_MAP 覆盖 6 Agent × 4 知识水平 × 4 学历层次
7. `test_get_personalization_diff` — 验证极端画像差异度 > 0.6
8. `test_get_personalization_diff_same_profile` — 验证相同画像差异度 = 0
9. `test_get_personalization_for_agent_unknown_agent` — 验证未知 Agent 返回空字符串
10. `test_backward_compatibility_after_enhancement` — 验证增强后 get_education_adaptation/get_term_density_target/get_style_guide/get_field_emphasis 仍正常工作

**验证命令**：
```bash
cd Veritas/ai-service && python -m pytest tests/test_personalization_service.py -v
```

### Step 3: Task 41 — CoordinatorAgent 个性化注入

**文件**：`app/agents/coordinator.py`

**变更**：
- 在 `__init__()` 中添加 `personalization_service` 参数（可选，默认 None）
- 在 `build_prompt()` 中，调用 `personalization_service.get_personalization_for_agent('coordinator', user_profile)` 获取个性化指令
- 将个性化指令追加到 prompt 末尾，使用 `【个性化适配】` 标记
- 降级处理：personalization_service 为 None 或调用失败时，不注入个性化指令，不抛异常

**关键代码逻辑**：
```python
def build_prompt(self, input_data: dict, context: dict) -> str:
    # ... 现有逻辑 ...
    base_prompt = self.prompt_manager.get_prompt(...)

    # 注入个性化指令
    personalization = self._get_personalization_instruction(context)
    if personalization:
        base_prompt += f"\n\n【个性化适配】{personalization}"

    return base_prompt

def _get_personalization_instruction(self, context: dict) -> str:
    if self.personalization_service is None:
        return ""
    user_profile = context.get("user_profile")
    if not user_profile:
        return ""
    try:
        return self.personalization_service.get_personalization_for_agent(
            "coordinator", user_profile
        )
    except Exception as e:
        logger.warning(f"Personalization injection failed for coordinator: {e}")
        return ""
```

### Step 4: Task 41 — RetrieverAgent 个性化注入

**文件**：`app/agents/retriever.py`

**变更**：
- 在 `__init__()` 中添加 `personalization_service` 参数（可选，默认 None）
- 在 `build_prompt()` 中注入个性化指令
- 根据 knowledge_level 调整 top_k（beginner→5, intermediate→10, advanced→15, expert→20）
- 降级处理同上

**关键代码逻辑**：
```python
def build_prompt(self, input_data: dict, context: dict) -> str:
    # 根据 knowledge_level 调整 top_k
    top_k = input_data.get("top_k", 10)
    adjusted_top_k = self._adjust_top_k(top_k, context)

    base_prompt = self.prompt_manager.get_prompt(
        "retriever",
        topic=input_data.get("topic", ""),
        top_k=str(adjusted_top_k),
    )

    # 注入个性化指令
    personalization = self._get_personalization_instruction(context)
    if personalization:
        base_prompt += f"\n\n【个性化适配】{personalization}"

    return base_prompt

def _adjust_top_k(self, default_top_k: int, context: dict) -> int:
    """根据 knowledge_level 调整检索数量"""
    if self.personalization_service is None:
        return default_top_k
    user_profile = context.get("user_profile")
    if not user_profile:
        return default_top_k
    try:
        profile = self.personalization_service._normalize_profile(user_profile)
        knowledge_level = profile.get("knowledge_level", "intermediate")
        top_k_map = {"beginner": 5, "intermediate": 10, "advanced": 15, "expert": 20}
        return top_k_map.get(knowledge_level, default_top_k)
    except Exception:
        return default_top_k
```

### Step 5: Task 41 — AnalyzerAgent 个性化迁移

**文件**：`app/agents/analyzer.py`

**变更**：
- 在 `build_prompt()` 中，将 `_get_extra_instruction()` 替换为 `personalization_service.get_personalization_for_agent('analyzer', user_profile)`
- 保留 `_get_extra_instruction()` 作为降级路径（personalization_service 为 None 时使用）
- 降级处理：personalization_service 为 None 或调用失败时，回退到 `_get_extra_instruction()`

**关键代码逻辑**：
```python
def build_prompt(self, input_data: dict, context: dict) -> str:
    extra_instruction = self._get_personalized_instruction(context)

    return self.prompt_manager.get_prompt(
        "analyzer",
        paper_title=input_data.get("paper_title", ""),
        paper_abstract=input_data.get("paper_abstract", ""),
        extra_instruction=extra_instruction,
    )

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
```

### Step 6: Task 41 — ComparerAgent 个性化注入

**文件**：`app/agents/comparer.py`

**变更**：
- 在 `__init__()` 中添加 `personalization_service` 参数（可选，默认 None）
- 在 `build_prompt()` 中注入个性化指令
- 降级处理同上

**关键代码逻辑**：与 CoordinatorAgent 类似，在 build_prompt() 返回的 prompt 末尾追加 `【个性化适配】` 标记的个性化指令。

### Step 7: Task 41 — GeneratorAgent 统一接口

**文件**：`app/agents/generator.py`

**变更**：
- 在 `_build_personalization_block()` 中，优先使用 `personalization_service.get_personalization_for_agent('generator', user_profile)` 获取个性化指令
- 保留现有 `get_personalization_block()` 调用作为兼容路径
- 在 `_build_user_profile_summary()` 中统一使用 `personalization_service._build_user_profile_summary()`
- 移除 generator.py 中的内部 DIFFICULTY_MAP/STYLE_MAP/EDUCATION_ADAPTATION/FIELD_EMPHASIS 常量（已由 personalization_service.py 统一管理）

**注意**：generator.py 内部仍有旧版 DIFFICULTY_MAP/STYLE_MAP/EDUCATION_ADAPTATION/FIELD_EMPHASIS 常量（简单值），这些与 personalization_service.py 中的增强版重复。Task 41 要求统一使用 PersonalizationService 接口，但根据 FA-014 约束（不修改返回类型签名），需谨慎处理。

**决策**：保留 generator.py 内部常量作为 personalization_service 不可用时的降级路径，但在 personalization_service 可用时优先使用增强版。

### Step 8: Task 41 — ReviewerAgent 个性化注入

**文件**：`app/agents/reviewer.py`

**变更**：
- ReviewerAgent 已有 `personalization_service` 参数
- 在 `build_prompt()` 中注入个性化指令
- 降级处理同上

**关键代码逻辑**：
```python
def build_prompt(self, input_data: dict, context: dict) -> str:
    # ... 现有逻辑 ...
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
```

### Step 9: Task 41 — 创建 test_personalization_e2e.py

**文件**：`tests/test_personalization_e2e.py`（新建）

**测试用例**：

1. `test_coordinator_build_prompt_has_personalization` — 验证 CoordinatorAgent.build_prompt() 输出包含【个性化适配】
2. `test_retriever_build_prompt_has_personalization` — 验证 RetrieverAgent.build_prompt() 含个性化指令
3. `test_retriever_top_k_adjustment` — 验证 top_k 随 knowledge_level 变化
4. `test_analyzer_build_prompt_uses_get_personalization_for_agent` — 验证 AnalyzerAgent 使用新接口
5. `test_comparer_build_prompt_has_personalization` — 验证 ComparerAgent.build_prompt() 含【个性化适配】
6. `test_generator_build_prompt_uses_personalization_service` — 验证 GeneratorAgent 使用 PersonalizationService
7. `test_reviewer_build_prompt_has_personalization` — 验证 ReviewerAgent.build_prompt() 含【个性化适配】
8. `test_all_six_agents_personalization_injection` — 验证 6 个 Agent 的 build_prompt() 输出均包含个性化片段
9. `test_personalization_empty_profile_fallback` — 验证空画像降级不抛异常
10. `test_personalization_diff_extreme_profiles` — 验证极端画像差异度 > 0.6
11. `test_four_dimension_effectiveness` — 验证 4 维度画像在个性化指令中体现
12. `test_personalization_service_failure_graceful` — 验证 PersonalizationService 异常时 Agent 不阻塞

**所有测试使用 mock，不调用真实 LLM API**（FA-018 约束）

### Step 10: 最终验证

**操作**：
```bash
cd Veritas/ai-service && python -m pytest tests/ -v --tb=short
```

**预期**：所有测试通过，包括：
- test_personalization_service.py（16 已有 + 10 新增）
- test_personalization_e2e.py（12 新增）
- test_reviewer.py（21 已有）
- test_citation_parser.py（18 已有）
- test_graph_integration.py（19 已有）
- test_graph.py（16 已有）

---

## 关键决策

1. **个性化注入方式**：在 build_prompt() 返回的 prompt 末尾追加 `【个性化适配】` 标记的指令片段，而非修改 prompt 模板。这样避免修改所有 prompt 模板文件，且降级更简单。

2. **AnalyzerAgent 迁移策略**：保留 `_get_extra_instruction()` 作为降级路径，优先使用 `get_personalization_for_agent('analyzer', user_profile)`。不删除旧方法，保持向后兼容。

3. **GeneratorAgent 内部常量**：保留 generator.py 中的旧版常量作为降级路径，不删除（FA-014 约束）。当 personalization_service 可用时优先使用增强版。

4. **RetrieverAgent top_k 调整**：在 build_prompt() 中调整 top_k 参数，而非在 _run() 中。这样 prompt 模板中的 top_k 变量已经是调整后的值。

5. **测试策略**：所有 e2e 测试使用 mock LLM，不调用真实 API。个性化差异度通过 `get_personalization_diff()` 方法验证，而非实际生成文本的 Jaccard 相似度。

---

## 文件变更清单

| 文件 | 操作 | 描述 |
|------|------|------|
| `tests/test_personalization_service.py` | 修改（追加） | 新增 10 个测试用例 |
| `app/agents/coordinator.py` | 修改 | 添加 personalization_service + 个性化注入 |
| `app/agents/retriever.py` | 修改 | 添加 personalization_service + 个性化注入 + top_k 调整 |
| `app/agents/analyzer.py` | 修改 | 迁移到 get_personalization_for_agent() |
| `app/agents/comparer.py` | 修改 | 添加 personalization_service + 个性化注入 |
| `app/agents/generator.py` | 修改 | 统一使用 get_personalization_for_agent() |
| `app/agents/reviewer.py` | 修改 | 添加个性化注入到 build_prompt() |
| `tests/test_personalization_e2e.py` | 新建 | 12 个端到端个性化效果测试 |

---

## 验证步骤

1. Step 1: `cd Veritas/ai-service && python -m pytest tests/test_personalization_service.py -v` — 向后兼容验证
2. Step 2: 同上 — 新增测试验证
3. Step 3-8: 逐个 Agent 修改后运行对应测试
4. Step 9: `cd Veritas/ai-service && python -m pytest tests/test_personalization_e2e.py -v` — e2e 测试
5. Step 10: `cd Veritas/ai-service && python -m pytest tests/ -v` — 全量回归
