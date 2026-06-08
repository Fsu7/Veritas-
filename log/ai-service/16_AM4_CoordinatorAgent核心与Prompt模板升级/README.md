# AM4 CoordinatorAgent 协调者 Agent 核心与 Prompt 模板升级

## 功能描述

- **实现了 CoordinatorAgent（协调者 Agent）核心逻辑**：作为 6-Agent 协同工作流的入口节点，将用户研究问题分解为 2-5 个结构化子任务（retrieve/analyze/compare/generate/review），由 LangGraph 工作流按依赖顺序委派给下游 Agent 执行
- **建立了三级降级保护机制**：LLM 调用失败 / 超时 / JSON 解析失败 / 空输出时，自动降级为基于规则的启发式分解（`_rule_based_decomposition`），确保 LangGraph 流程不中断（满足 ADR-002 可用性约束）
- **升级了协调者 Prompt 模板（v1 → v2）**：从 57 行简单模板升级为 222 行标准结构化模板，包含五层固定结构（System Context / Task Context / Execution Protocol / Few-shot / Self-Check）
- **实现了用户画像 → 子任务个性化映射**：4 项画像字段（education_level / research_field / knowledge_level / preferred_style）显式影响对应子任务的参数（analyze 深度 / retrieve 关键词权重 / generate style）
- **解决了 6-Agent 协同工作流的入口缺失问题**：task22 完成了 3-Agent 线性工作流，但 M4 阶段 6-Agent 含条件分支工作流缺少任务分解入口
- **业务价值**：完成 AM4 里程碑核心交付——Coordinator Agent + 升级 Prompt 模板，为后续 task34（Comparer Agent）和 6-Agent 完整工作流奠定基础

## 实现逻辑

### 修改/新增的核心文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `Veritas/ai-service/app/agents/coordinator.py` | 新增 | CoordinatorAgent 协调者 Agent 核心逻辑（11 个方法 + 6 个类常量） |
| `Veritas/ai-service/prompts/coordinator.txt` | 重写 | v1（57 行）→ v2（222 行）标准模板（五层结构） |
| `Veritas/ai-service/tests/test_coordinator_agent.py` | 新增 | 23 个单元测试用例 |

### 使用的算法或设计模式

1. **Coordinator-Worker 模式（任务分解器模式）**：Coordinator 仅做任务分解，子任务执行由 LangGraph 编排，避免反模式 AP-09 Planner-Executor Hybrid
2. **三级降级策略**：Level 1 - LLM 调用失败 → `_fallback_result`；Level 2 - JSON 解析失败 → `_rule_based_decomposition`；Level 3 - 子任务数 < 2 → 补全规则分解子任务
3. **CoT（Chain-of-Thought）推理 + Self-Check 清单**：Prompt 模板内嵌 5 步 CoT（意图识别 → 任务映射 → 子任务排序 → 依赖检查 → JSON 输出）+ 5 项 Self-Check
4. **Few-shot Learning（单示例）**：1 个 multi_paper_comparison 模式示例，避免 Prompt Monster 反模式
5. **Prompt 注入防护**：`_sanitize_topic` 实现 500 字符长度限制 + 控制字符清理
6. **string.Template 兼容**：仅用 `$variable` 语法（不引入 Jinja2 依赖）

### 关键代码逻辑说明

#### 1. CoordinatorAgent 类结构
- **继承 `BaseAgent`**：`name='coordinator'`、`timeout=30`（默认 `settings.AGENT_TIMEOUT`）
- **类常量（FR-013）**：
  - `VALID_TASK_TYPES = {"retrieve", "analyze", "compare", "generate", "review"}`
  - `MIN_SUB_TASKS = 2` / `MAX_SUB_TASKS = 5`
  - `DEFAULT_ANALYSIS_TYPE = "report"` / `DEFAULT_TOP_K = 10`
  - `DEFAULT_DIMENSIONS = ["research_problem", "core_method", "main_experiments", "core_conclusions", "limitations"]`
  - `MAX_QUERY_LENGTH = 500`（SR-002 Prompt 注入防护）

#### 2. `_run` 核心流程（进度渐变 0.2→0.5→0.8→1.0）
```
Step 1 (0.2): Decomposing task via LLM
Step 2 (0.5): Calling LLM for task breakdown
Step 3 (0.8): Parsing task breakdown
Step 4 (1.0): 分解为 N 个子任务
```
异常时调用 `_fallback_result(input_data)` 返回规则分解结果。

#### 3. `_parse_task_breakdown` 三段 JSON 解析
1. 提取 ` ```json ... ``` ` 代码块
2. 提取首个 `{ ... }` 块
3. 整体文本解析
4. 失败时降级到 `_rule_based_decomposition`
强制 2-5 子任务约束：< 2 补全；> 5 截断。

#### 4. `_rule_based_decomposition` 规则分解
- 总是包含：retrieve + analyze
- 条件启用 compare（paper_ids >= 2 且 analysis_type ∈ {compare, report}）
- 条件启用 generate（analysis_type ≠ paper_analysis）
- 条件启用 review（analysis_type ∈ {report, compare}）

#### 5. v2 Prompt 模板五层结构
- **System Context**：Agent 身份 + 5 项核心约束 + 安全约束 + 顶层 Schema
- **Task Context**：4 个变量注入（$query / $user_profile / $paper_ids / $analysis_type）
- **Execution Protocol**：5 步 CoT + 决策表
- **5 种子任务 JSON Schema 详解**：retrieve / analyze / compare / generate / review
- **用户画像个性化映射**：4 项画像 → 4 类子任务影响规则
- **Few-shot 示例**：1 个 multi_paper_comparison 模式示例
- **Self-Check 清单**：5 项强制检查（子任务数、动词开头、依赖排序、画像影响、JSON Schema）

## 接口变更

### LangGraph StateGraph 入口（Coordinator Agent 产出）
```python
# Coordinator Agent 产出格式（消费方：LangGraph graph.py）
{
    "sub_tasks": [
        {"task_type": "retrieve", "description": "检索关于...", "keywords": [...], "top_k": 10},
        {"task_type": "analyze", "description": "分析...", "dimensions": [...]},
        {"task_type": "compare", "description": "对比...", "required": true},
        {"task_type": "generate", "description": "生成...", "style": "专业风格"},
        {"task_type": "review", "description": "审核...", "focus": ["事实核查", "引用核查"]}
    ],
    "reasoning": "Chain-of-Thought 任务分解推理说明（50-200字）",
    "task_count": 5,
    "requires_compare": true,
    "requires_review": true,
    "analysis_type": "compare",
    "paper_count": 2,
    "agent": "coordinator"
}
```

### Prompt 模板变量契约（消费方：PromptManager.get_prompt）
```python
# 调用方式（CoordinatorAgent.build_prompt）
prompt = self.prompt_manager.get_prompt(
    "coordinator",
    query="Multi-Agent协同决策",                              # str (必填)
    user_profile="education_level=master / research_field=NLP / knowledge_level=intermediate / preferred_style=balanced",  # str (key=value 格式)
    paper_ids="arxiv_2024_001, arxiv_2024_002",                # str (逗号分隔，空时显示"（用户未指定）")
    analysis_type="report"                                      # str (paper_analysis/compare/report)
)
```

### 降级响应（LLM 失败时）
```python
# _fallback_result 返回
{
    "degraded": True,
    "agent": "coordinator",
    "sub_tasks": [<2-5 个规则分解子任务>],
    "reasoning": "LLM unavailable, using rule-based decomposition",
    "task_count": 4,
    "requires_compare": False,
    "requires_review": True,
    "analysis_type": "report",
    "paper_count": 1,
    "error": "Agent coordinator timed out after 30s"  # 或具体异常信息
}
```

## 测试结果

| 测试场景 | 期望 | 实际结果 |
|---------|------|---------|
| `test_coordinator_inherits_base_agent` | 继承 BaseAgent + name='coordinator' | ✅ PASSED |
| `test_build_prompt_renders_template` | prompt_manager.get_prompt 被正确调用 | ✅ PASSED |
| `test_build_prompt_with_empty_paper_ids` | 空 paper_ids 渲染不报错 | ✅ PASSED |
| `test_parse_task_breakdown_valid_json` | 合法 JSON 块解析为子任务列表 | ✅ PASSED |
| `test_parse_task_breakdown_invalid_json` | 非法 JSON 降级到规则分解 | ✅ PASSED |
| `test_parse_task_breakdown_filter_invalid_task_types` | 过滤非法 task_type | ✅ PASSED |
| `test_parse_task_breakdown_subtask_count_constraint` | 强制 2-5 约束 | ✅ PASSED |
| `test_rule_based_decomposition_paper_analysis` | paper_analysis + paper_ids=[] → 2 子任务 | ✅ PASSED |
| `test_rule_based_decomposition_compare_with_multi_papers` | compare + 2 papers → 5 子任务 | ✅ PASSED |
| `test_rule_based_decomposition_report_with_single_paper` | report + 1 paper → 4 子任务（无 compare） | ✅ PASSED |
| `test_rule_based_decomposition_report_with_multi_papers` | report + 2 papers → 5 子任务（含 compare） | ✅ PASSED |
| `test_determine_required_tasks_compare` | paper_ids=[id1,id2]+compare → requires_compare=True | ✅ PASSED |
| `test_determine_required_tasks_no_compare` | paper_ids=[]+report → requires_compare=False, requires_review=True | ✅ PASSED |
| `test_summarize_sub_tasks` | "分解为 N 个子任务: ..." 摘要 | ✅ PASSED |
| `test_run_success_flow` | 3 篇论文 + report → 完整结构返回 | ✅ PASSED |
| `test_run_llm_failure_fallback` | LLM 失败 → 规则分解降级 | ✅ PASSED |
| `test_run_llm_empty_output_fallback` | LLM 空输出 → 规则分解降级 | ✅ PASSED |
| `test_fallback_result_preserves_langgraph_flow` | 降级结果包含 >= 2 子任务 | ✅ PASSED |
| `test_infer_style_from_profile` | preferred_style → 中文风格描述 | ✅ PASSED |
| `test_summarize_result` | "Decomposed into N sub-tasks: [...]" 格式 | ✅ PASSED |
| `test_sanitize_topic_length_limit` | 长度限制 500 字符 | ✅ PASSED |
| `test_sanitize_topic_strip_control_chars` | 移除控制字符 | ✅ PASSED |
| `test_coordinator_with_prompt_manager` | 与真实 PromptManager 集成 | ✅ PASSED |

### 测试统计
- CoordinatorAgent 新增测试：**23 个**
- 既有测试（analyzer/generator/retriever/base_agent/prompt_manager）：**123 个全 PASSED**
- 总计：**146/146 PASSED** ✅百分百

### 验证命令结果
| 验证命令 | 期望结果 | 实际结果 |
|---------|---------|---------|
| `python -c "from app.agents.coordinator import CoordinatorAgent"` | Import OK | ✅ Import OK |
| `pm.list_templates()` | 含 'coordinator' | ✅ ['analyzer', 'comparer', 'coordinator', 'generator', 'retriever', 'reviewer'] |
| `pm.get_prompt('coordinator', ...)` 长度 | 5000-10000 chars | ✅ 8516 chars / 222 行 |
| `grep -E '\{\{[a-zA-Z_]+\}\}'` | 无匹配（无 Jinja2） | ✅ 无匹配 |
| 敏感信息 grep | No hardcoded secrets found | ✅ No hardcoded secrets found |
| 既有回归测试 | 不破坏 | ✅ 123/123 PASSED |

## 相关文件

### 新增文件
- `/Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/app/agents/coordinator.py`（365 行）
- `/Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/tests/test_coordinator_agent.py`（370 行）

### 重写文件
- `/Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/prompts/coordinator.txt`（v1 57 行 → v2 222 行）

### 参考文件（未修改）
- `Veritas/ai-service/app/agents/base.py` — BaseAgent 基类
- `Veritas/ai-service/app/agents/analyzer.py` — 参考实现模板
- `Veritas/ai-service/app/agents/generator.py` — 参考实现模板
- `Veritas/ai-service/app/services/prompt_manager.py` — string.Template 渲染
- `Veritas/ai-service/app/services/llm_service.py` — LLMService.generate()
- `Veritas/ai-service/app/models/enums.py` — AnalysisType 等枚举
- `docs/开发规范文档.md` — Section 8/9 Python AI 服务与 Agent 开发规范
- `docs/ai-service/AI服务模块系统架构文档.md` — Section 5.4.1 Coordinator Agent 详细设计
- `json_prompt/ai-service/task32_coordinator_agent_core/prompt.json` — task32 任务定义
- `json_prompt/ai-service/task33_coordinator_prompt_template/prompt.json` — task33 任务定义

### 配置/计划文件
- `/Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/.trae/documents/plan_task32_task33_coordinator.md` — 本次实施计划