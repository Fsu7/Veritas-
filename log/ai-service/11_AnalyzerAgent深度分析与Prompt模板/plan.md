# Task17/18/19 执行计划 — AnalyzerAgent 核心逻辑 + Prompt模板 + 单元测试

## 当前状态评估

### 已有实现

| 文件 | 状态 | 说明 |
|------|------|------|
| `app/agents/analyzer.py` | ✅ 已存在 | 完整实现，含5维度提取/JSON解析/降级/个性化 |
| `prompts/analyzer.txt` | ✅ 已存在 | 已含8区块/CoT/嵌套Schema，基本完整 |
| `tests/test_analyzer_agent.py` | ✅ 已存在 | 50+测试用例，覆盖面广 |

### 关键差距分析（当前实现 vs 三个Task规格）

#### Task17 差距（analyzer.py）

| # | 差距 | 当前值 | 规格要求 | 严重度 |
|---|------|--------|---------|--------|
| G1 | `_validate_dimensions` 字段名 | `disclaimer` | `ai_disclaimer` | 高 |
| G2 | `_validate_dimensions` None维度confidence | `0.0` | `0.3` | 高 |
| G3 | `_validate_dimensions` 缺少字段 | 无 `analysis_id` | 需添加 `analysis_id` | 中 |
| G4 | `_run` 返回值 | 无 `extraction_quality` | 需计算全局 `extraction_quality` | 高 |
| G5 | `_parse_analysis_result` 失败路径 | 返回 `_empty_dimensions()` | 应调用 `_rule_based_extraction(paper)` | 高 |
| G6 | `_parse_analysis_result` 签名 | `(llm_output)` | `(llm_output, paper)` | 高 |
| G7 | `_get_extra_instruction` 缺失knowledge_level | 默认intermediate | 返回空字符串 | 中 |
| G8 | `_get_extra_instruction` 关键词 | 缺"通俗解释"/"研究空白"/"前沿洞察" | 需包含这些关键词 | 中 |
| G9 | `_rule_based_extraction` confidence | 关键词匹配变化值(0.1~0.5) | 统一 `0.3` | 高 |
| G10 | `_rule_based_extraction` extraction_quality | `"degraded_rule_based"`(字符串) | `0.1`(浮点数) | 高 |
| G11 | `_rule_based_extraction` disclaimer字段 | `disclaimer` | `ai_disclaimer` | 高 |
| G12 | `_validate_dimensions` confidence=None | 默认 `0.5` | 应设为 `0.3` | 中 |

#### Task18 差距（analyzer.txt）

| # | 差距 | 说明 |
|---|------|------|
| G13 | Output Schema缺少 `ai_disclaimer` 字段 | 需在JSON Schema示例中添加 |
| G14 | 缺少AI内容声明 | 需在Prompt底部添加声明指令 |

#### Task19 差距（test_analyzer_agent.py）

| # | 差距 | 说明 |
|---|------|------|
| G15 | 测试检查 `disclaimer` 而非 `ai_disclaimer` | 需更新断言 |
| G16 | 缺少 `extraction_quality` 正常流程测试 | 需新增 |
| G17 | 缺少 `analysis_id` 测试 | 需新增 |
| G18 | `_rule_based_extraction` 测试期望变化confidence | 需改为0.3 |
| G19 | `_parse_analysis_result` 未测试rule_based降级路径 | 需新增 |
| G20 | 缺少 `_get_extra_instruction` 无knowledge_level返回空字符串测试 | 需新增 |
| G21 | SAMPLE_PAPERS仅2篇，规格要求3篇 | 需扩展 |
| G22 | 缺少PARTIAL_ANALYSIS_JSON常量 | 需新增 |

---

## 执行计划

### Phase 0: 基线验证

```bash
cd Veritas/ai-service && python -m pytest tests/test_analyzer_agent.py -v
```

确认当前测试全部通过，建立基线。

---

### Phase 1: Task17 — 更新 analyzer.py

#### Step 1.1: 添加 uuid 导入

```python
import uuid
```

#### Step 1.2: 修改 `_parse_analysis_result` 签名和降级路径

**变更**：
- 签名从 `(self, llm_output: str)` → `(self, llm_output: str, paper: dict = None)`
- 解析失败时：若 paper 不为 None，调用 `self._rule_based_extraction(paper)`；否则返回 `self._empty_dimensions()`

```python
def _parse_analysis_result(self, llm_output: str, paper: dict = None) -> dict:
    # ... 现有解析逻辑不变 ...
    # 最后的 fallback:
    logger.error(f"All JSON parsing attempts failed for output: {cleaned[:200]}")
    if paper is not None:
        return self._rule_based_extraction(paper)
    return self._empty_dimensions()
```

#### Step 1.3: 更新 `_analyze_single_paper` 传递 paper

```python
parsed = self._parse_analysis_result(llm_output, paper)
```

#### Step 1.4: 修改 `_validate_dimensions`

**变更**：
1. `disclaimer` → `ai_disclaimer`，值为 `"⚠️ 本分析由 AI 生成，仅供参考"`
2. None维度 confidence 从 `0.0` → `0.3`
3. 添加 `analysis_id` 字段
4. confidence 解析失败默认值从 `0.5` → `0.3`

```python
def _validate_dimensions(self, parsed: dict, paper: dict) -> dict:
    result: Dict[str, Any] = {}

    for dim in DEFAULT_DIMENSIONS:
        dim_data = parsed.get(dim)

        if dim_data is None:
            result[dim] = {
                "summary": FALLBACK_NOTE,
                "confidence": 0.3,  # G2: 0.0 → 0.3
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
                confidence = 0.3  # G12: 0.5 → 0.3
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
            "confidence": 0.3,  # G2: 0.0 → 0.3
            "references": [],
        }

    paper_title = paper.get("title", "")
    result["paper_title"] = paper_title
    result["analysis_id"] = str(uuid.uuid4())  # G3: 新增
    result["ai_disclaimer"] = "⚠️ 本分析由 AI 生成，仅供参考"  # G1: disclaimer → ai_disclaimer

    return result
```

#### Step 1.5: 修改 `_run` 添加 extraction_quality

**变更**：在返回前计算全局 extraction_quality

```python
# 在 return 之前添加:
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
    "extraction_quality": round(extraction_quality, 4),  # G4: 新增
}
```

#### Step 1.6: 修改 `_get_extra_instruction`

**变更**：
1. knowledge_level 缺失时返回空字符串（G7）
2. 更新指令文本包含规格关键词（G8）

```python
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

    knowledge_level = user_profile.get("knowledge_level")  # G7: 不再默认intermediate
    if knowledge_level is None:
        return ""  # G7: 缺失时返回空字符串

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
    edu_instruction = education_instructions.get(education_level, "")
    if edu_instruction:
        instruction_parts.append(edu_instruction)

    return " ".join(instruction_parts) if instruction_parts else ""
```

#### Step 1.7: 修改 `_rule_based_extraction`

**变更**：
1. 所有维度 confidence 统一为 0.3（G9）
2. `extraction_quality` 从字符串改为浮点数 0.1（G10）
3. `disclaimer` → `ai_disclaimer`（G11）

```python
def _rule_based_extraction(self, paper: dict) -> dict:
    title = paper.get("title", "")
    abstract = paper.get("abstract", "")

    abstract_preview = abstract[:300] if abstract else ""

    return {
        "paper_title": title,
        "research_problem": {
            "summary": f"基于标题'{title}'的规则提取" if not abstract else abstract_preview,
            "confidence": 0.3,  # G9: 统一0.3
            "references": [f"标题: {title}"] if not abstract else [],
        },
        "core_method": {
            "summary": FALLBACK_NOTE,
            "confidence": 0.3,  # G9
            "references": [],
        },
        "main_experiments": {
            "summary": FALLBACK_NOTE,
            "confidence": 0.3,  # G9
            "references": [],
        },
        "core_conclusions": {
            "summary": FALLBACK_NOTE,
            "confidence": 0.3,  # G9
            "references": [],
        },
        "limitations": {
            "summary": FALLBACK_NOTE,
            "confidence": 0.3,  # G9
            "references": [],
        },
        "ai_disclaimer": "⚠️ 本分析由 AI 生成，仅供参考",  # G11
        "extraction_quality": 0.1,  # G10: 字符串→浮点数
    }
```

#### Step 1.8: 更新 `_fallback_result` 中的字段名

确保 `_fallback_result` 中的降级结果也使用 `ai_disclaimer`。

#### Step 1.9: 验证 Task17

```bash
cd Veritas/ai-service && python -c "from app.agents.analyzer import AnalyzerAgent; print('Import OK')"
```

---

### Phase 2: Task18 — 更新 analyzer.txt

#### Step 2.1: 在 Output Schema Block 添加 ai_disclaimer 字段

在 JSON Schema 示例中添加：

```json
"ai_disclaimer": "⚠️ 本分析由 AI 生成，仅供参考"
```

#### Step 2.2: 在 Prompt 底部添加 AI 内容声明

```
注意：你生成的分析内容将被标注为AI生成，确保所有意见基于原文事实。请在输出的JSON中包含ai_disclaimer字段，值为"⚠️ 本分析由 AI 生成，仅供参考"。
```

#### Step 2.3: 验证 Task18

```bash
cd Veritas/ai-service && python -c "
import string
t = open('prompts/analyzer.txt').read()
s = string.Template(t).substitute(paper_title='Test', paper_abstract='Abs', extra_instruction='')
print('Render OK, length:', len(s))
"
```

```bash
cd Veritas/ai-service && python -m pytest tests/test_prompt_manager.py -v -k "analyzer"
```

---

### Phase 3: Task19 — 重写 test_analyzer_agent.py

#### Step 3.1: 更新测试常量

1. **SAMPLE_PAPERS** — 扩展为3篇论文
2. **VALID_ANALYSIS_JSON** — 保持不变（已符合snake_case嵌套结构）
3. **新增 PARTIAL_ANALYSIS_JSON** — 缺失 limitations 维度
4. **新增 MALFORMED_OUTPUT** — 完全无效的LLM输出

#### Step 3.2: 更新 _make_mock_services

保持现有模式（llm=AsyncMock, pm=MagicMock, ps=MagicMock），确保与 test_retriever_agent.py 风格一致。

#### Step 3.3: 重写测试类

按照 task19 规格要求的测试类组织：

| 测试类 | 测试方法数 | 覆盖场景 |
|--------|-----------|---------|
| TestAnalyzerAgentInit | 3+ | 继承/名称/超时 |
| TestBuildPrompt | 2 | prompt_manager调用/个性化 |
| TestGetExtraInstruction | 6+ | 4种level + None + 缺失key |
| TestRunSuccessFlow | 3+ | 3篇论文/进度更新/结果结构 |
| TestRunDegradation | 3 | 单篇失败/全部失败/空papers |
| TestParseAnalysisResult | 5+ | 纯JSON/json代码块/普通代码块/无效输出/空字符串 |
| TestValidateDimensions | 5+ | 缺失维度/confidence clamp/None/disclaimer |
| TestRuleBasedExtraction | 3 | 5维度/confidence=0.3/extraction_quality=0.1 |
| TestExecuteIntegration | 2 | 正常流程/异常流程 |

**关键断言更新**：
- `disclaimer` → `ai_disclaimer`
- 新增 `analysis_id` 断言
- 新增 `extraction_quality` 断言
- `_rule_based_extraction` confidence 统一为 0.3
- `_parse_analysis_result` 无效输出走 `_rule_based_extraction` 降级路径

#### Step 3.4: 验证 Task19

```bash
cd Veritas/ai-service && python -m pytest tests/test_analyzer_agent.py -v
cd Veritas/ai-service && python -m pytest tests/test_analyzer_agent.py --tb=short -q
```

---

### Phase 4: 全局验证

1. 运行全部AI服务测试：`python -m pytest tests/ -v --tb=short`
2. 验证analyzer import：`python -c "from app.agents.analyzer import AnalyzerAgent; print('Import OK')"`
3. 验证prompt渲染：`python -m pytest tests/test_prompt_manager.py -v -k "analyzer"`

---

## 变更影响矩阵

| 变更项 | analyzer.py | analyzer.txt | test_analyzer_agent.py | test_prompt_manager.py |
|--------|:-----------:|:------------:|:----------------------:|:---------------------:|
| G1 disclaimer→ai_disclaimer | ✏️ | ✏️ | ✏️ | — |
| G2 None confidence 0.0→0.3 | ✏️ | — | ✏️ | — |
| G3 新增 analysis_id | ✏️ | — | ✏️ | — |
| G4 新增 extraction_quality | ✏️ | — | ✏️ | — |
| G5-6 _parse签名+降级路径 | ✏️ | — | ✏️ | — |
| G7 knowledge_level缺失→空 | ✏️ | — | ✏️ | — |
| G8 指令关键词更新 | ✏️ | — | ✏️ | — |
| G9-11 _rule_based简化 | ✏️ | — | ✏️ | — |
| G12 confidence=None→0.3 | ✏️ | — | ✏️ | — |
| G13-14 Prompt声明 | — | ✏️ | — | 可能影响 |

---

## 风险与注意事项

1. **_parse_analysis_result 签名变更**：从 `(llm_output)` → `(llm_output, paper=None)`，需确保所有调用点更新
2. **_rule_based_extraction 简化**：移除关键词匹配逻辑，降级结果不再有差异化confidence，但符合规格
3. **_get_extra_instruction 行为变更**：缺失knowledge_level时返回空字符串而非默认intermediate，可能影响无knowledge_level的用户体验
4. **test_prompt_manager.py**：analyzer相关测试可能因Prompt模板变更而受影响，需验证
5. **向后兼容**：`disclaimer` → `ai_disclaimer` 是字段名变更，下游Comparer/Generator如依赖此字段需同步更新（当前尚未实现，风险低）
