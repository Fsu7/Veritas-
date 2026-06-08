# AM4 CoordinatorAgent 与 Prompt 模板升级 — 执行计划

> 依据 `json_prompt/ai-service/task32_coordinator_agent_core/prompt.json` 与 `task33_coordinator_prompt_template/prompt.json` 实施

## 1. 任务背景

依次完成两个强耦合的串联任务：
- **task32**：新增 `Veritas/ai-service/app/agents/coordinator.py`（CoordinatorAgent协调者Agent核心逻辑）
- **task33**：重写 `Veritas/ai-service/prompts/coordinator.txt`（v1 → v2 标准模板）

二者强耦合 —— task32 使用旧模板运行，task33 升级后保持兼容（同一 `$query / $user_profile / $paper_ids / $analysis_type` 4 变量）。

## 2. 当前实现状态摘要

| 模块 | 状态 |
|------|------|
| `app/agents/base.py` | ✅ BaseAgent基类已实现，含 30s超时、_fallback_result、_summarize_result |
| `app/agents/analyzer.py` | ✅ 参考实现：build_prompt + _run + JSON 解析 + 规则降级 |
| `app/agents/generator.py` | ✅ 参考实现：完整三件套（_run + _fallback_result + _summarize_result） |
| `app/agents/coordinator.py` | ❌ **缺失**（task32待创建） |
| `app/services/prompt_manager.py` | ✅ string.Template.safe_substitute 渲染 |
| `app/services/llm_service.py` | ✅ LLMService.generate(prompt, max_tokens, temperature) |
| `app/services/personalization_service.py` | ✅ 4维度画像 → 个性化片段 |
| `app/models/enums.py` | ✅ AnalysisType(paper_analysis/compare/report) + EducationLevel/KnowledgeLevel/PreferredStyle |
| `prompts/coordinator.txt` | ⚠️ **v1**（57行，仅$query/$user_profile 2变量，5种子任务Schema不完整）→ task33升级 |
| `prompts/analyzer.txt` / `generator.txt` | ✅ 高质量参考模板 |

## 3. 执行步骤

### 步骤 1：task32 — 创建 CoordinatorAgent（`app/agents/coordinator.py`）

**实现要点**（严格遵循 task32 prompt.json FR-001 ~ FR-013）：

```python
class CoordinatorAgent(BaseAgent):
    """协调者Agent — 项目经理角色（任务分解器）"""

    # FR-013 类常量
    VALID_TASK_TYPES = {"retrieve", "analyze", "compare", "generate", "review"}
    MIN_SUB_TASKS = 2
    MAX_SUB_TASKS = 5
    DEFAULT_ANALYSIS_TYPE = "report"
    DEFAULT_TOP_K = 10
    DEFAULT_DIMENSIONS = [
        "research_problem", "core_method", "main_experiments",
        "core_conclusions", "limitations",
    ]
    MAX_QUERY_LENGTH = 500
```

**关键方法签名与职责**：

| 方法 | 职责 |
|------|------|
| `__init__(llm_service, prompt_manager, timeout=30, llm_temperature=0.3, llm_max_tokens=1024)` | 调 `super().__init__(name='coordinator', ...)`，存额外属性 |
| `build_prompt(input_data, context) -> str` | 提取topic/paper_ids/analysis_type/user_profile，调 `prompt_manager.get_prompt('coordinator', query=, user_profile=, paper_ids=, analysis_type=)` |
| `_run(prompt, input_data, context) -> dict` | 核心：进度 0.2→0.5→0.8→1.0，LLM调用 + 解析 + 降级兜底，返回 `{sub_tasks, reasoning, task_count, requires_compare, requires_review, analysis_type, paper_count, agent}` |
| `_parse_task_breakdown(llm_output, input_data) -> list` | 三段 JSON 解析（```json...``` / ```{...}``` / raw）；校验 task_type ∈ VALID_TASK_TYPES；强制 2-5 约束 |
| `_rule_based_decomposition(input_data) -> list` | LLM失败/JSON失败/空输出时的兜底（按 analysis_type + paper_ids 数量生成 2-5 子任务） |
| `_determine_required_tasks(input_data, sub_tasks) -> dict` | 计算 `requires_compare` (paper≥2 + report/compare)、`requires_review` (report/compare) |
| `_summarize_sub_tasks(sub_tasks) -> str` | 生成 "分解为 N 个子任务: ..." 摘要（SSE 用） |
| `_infer_style_from_profile(user_profile) -> str` | simple→通俗风格 / technical→专业风格 / 默认学术风格 |
| `_fallback_result(input_data) -> dict` | 覆盖基类，LLM 失败时返回规则分解子任务 + degraded=True |
| `_summarize_result(result) -> str` | 覆盖基类，格式 `Decomposed into N sub-tasks: [...]` |
| `_sanitize_topic(topic) -> str` | FR-013 SR-002：长度限制 500 + 控制字符清理 |

### 步骤 2：task33 — 重写协调者 Prompt 模板（`prompts/coordinator.txt`）

**模板结构（v2 五层固定结构）**：
- System Context（Agent 身份 + 5 项核心约束 + 安全约束 + 顶层 Schema）
- Task Context（4 个变量：$query / $user_profile / $paper_ids / $analysis_type）
- Execution Protocol（5 步 CoT：意图识别 → 任务映射 → 子任务排序 → 依赖检查 → JSON 输出）
- 5 种子任务 JSON Schema 详解（retrieve/analyze/compare/generate/review）
- 用户画像 → 子任务个性化映射（4 项）
- Few-shot 示例（仅 1 个，multi_paper_comparison 模式）
- Self-Check 清单（5 项）

### 步骤 3：单元测试文件（`tests/test_coordinator_agent.py`）

按 task32 prompt.json 的 20 个测试用例 + 2 个 Prompt 集成测试 + 2 个 sanitize_topic 测试 = 23 个用例。

### 步骤 4：执行验证命令

```bash
cd /Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service

# 1. 导入验证
python -c "from app.agents.coordinator import CoordinatorAgent; print('Import OK')"

# 2. PromptManager 加载验证
python -c "from app.services.prompt_manager import PromptManager; pm = PromptManager('prompts'); import asyncio; asyncio.run(pm.load_templates()); print(pm.list_templates())"

# 3. 模板渲染验证
python -c "from app.services.prompt_manager import PromptManager; pm = PromptManager('prompts'); import asyncio; asyncio.run(pm.load_templates()); prompt = pm.get_prompt('coordinator', query='test', user_profile='test', paper_ids='', analysis_type='report'); print(f'Length: {len(prompt)} chars')"

# 4. 单元测试
python -m pytest tests/test_coordinator_agent.py -v

# 5. 全量 coordinator 相关测试
python -m pytest tests/ -k coordinator -v

# 6. 安全检查
grep -E '(api[_-]?key|password|secret|token)\s*[:=]\s*["'\''][^"'\'']+["'\'']' prompts/coordinator.txt || echo 'No hardcoded secrets found'

# 7. 现有测试回归
python -m pytest tests/test_analyzer_agent.py tests/test_generator_agent.py tests/test_retriever_agent.py -v
```

## 4. 验证结果

| 验证项 | 结果 |
|--------|------|
| Import CoordinatorAgent | ✅ Import OK |
| PromptManager 加载 | ✅ 含 'coordinator' 模板 |
| 模板渲染长度 | ✅ 8516 chars / 222 行 |
| 单元测试 | ✅ 23/23 PASSED |
| Jinja2 语法检查 | ✅ 无匹配 |
| 敏感信息检查 | ✅ No hardcoded secrets found |
| 既有测试回归 | ✅ 123/123 PASSED |

## 5. 禁止动作（已严格遵守）

- ❌ 修改 base.py / retriever.py / analyzer.py / generator.py / graph.py / prompt_manager.py / llm_service.py 等已有文件
- ❌ 在 coordinator.py 中修改 prompts/coordinator.txt
- ❌ 输出 camelCase 字段（必须 snake_case）
- ❌ CoordinatorAgent 直接调用其他 Agent
- ❌ CoordinatorAgent 失败时返回 None 或空 dict
- ❌ 使用 {{variable}} Jinja2 语法
- ❌ 在模板中硬编码敏感信息
- ❌ 超过 1 个 Few-shot 示例
- ❌ 模板中包含降级逻辑代码
- ❌ 省略 Self-Check 清单
- ❌ 输出伪代码或 TODO 注释（必须完整可执行）