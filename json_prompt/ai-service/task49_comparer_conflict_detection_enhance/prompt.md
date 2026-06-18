# task49: ComparerAgent 矛盾检测增强

> **课题编号**：XH-202630
> **子项目**：科研文献助手 — AI 服务模块
> **里程碑**：M5 / AM5：混合检索与功能完善
> **AM5 天数**：Week 9 Day 4
> **版本**：v0.5
> **功能编号**：F3.1.4, F3.1.5
> **优先级**：P0
> **创建日期**：2026-06-17

---

## 1. 背景与上下文

### 1.1 项目背景

XH-202630 科研文献智能助手 — 领域知识个性化生成与多智能体协同决策系统研究。6-Agent LangGraph 工作流中，ComparerAgent 负责多论文对比与矛盾发现。

### 1.2 任务需求

增强 ComparerAgent 矛盾检测逻辑，覆盖 5 类根因（dataset_bias / metric_difference / condition_difference / assumption_difference / methodological_conflict）的端到端验证。优化矛盾发现 Prompt，明确 5 类根因输出格式。验证 AM4 遗留：ComparerAgent 在 graph.py 条件分支中正确激活。

### 1.3 参考文档

| 文档 | 用途 |
|------|------|
| [docs/ai-service/AI服务模块系统架构文档.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块系统架构文档.md) | 了解 ComparerAgent 6-Agent 工作流位置和矛盾检测职责 |
| [docs/ai-service/AI服务模块项目里程碑文档.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块项目里程碑文档.md) | 确认 AM5 Week 9 Day 4 矛盾发现交付物和 AM4 遗留验证项 |
| [AGENTS.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/AGENTS.md) | 确认 Agent 降级约束和 Prompt 管理规范 |

---

## 2. 当前架构

### 2.1 涉及层级

- `python_ai_service`

### 2.2 相关模块

| 层级 | 模块路径 | 描述 |
|------|---------|------|
| python_ai_service | `app.agents.comparer` | ComparerAgent 已实现 4 维度对比 + 5 类矛盾根因枚举 + 规则降级 |
| python_ai_service | `app.agents.graph` | graph.py should_compare 条件分支：requires_compare=True 且 papers>=2 时激活 comparer |
| python_ai_service | `prompts.comparer` | comparer.txt Prompt 模板，需优化矛盾发现输出格式 |

### 2.3 现有实现

| 文件 | 描述 | 复用方式 |
|------|------|---------|
| `Veritas/ai-service/app/agents/comparer.py` | ComparerAgent 已实现 VALID_ROOT_CAUSES 5 类枚举、_rule_based_comparison 降级、_detect_conflict_keywords 关键词检测 | extend |
| `Veritas/ai-service/app/agents/graph.py` | should_compare 条件分支已实现，compare_node 调用 ComparerAgent | direct_reuse |
| `Veritas/ai-service/prompts/comparer.txt` | 对比 Prompt 模板已存在，需优化矛盾标注格式 | extend |

---

## 3. 相关模块详情

### 3.1 ComparerAgent

- **路径**：`Veritas/ai-service/app/agents/comparer.py`
- **职责**：多论文对比与矛盾发现

**关键接口**：

| 方法 | 签名 | 描述 |
|------|------|------|
| `_run` | `async def _run(self, prompt: str, input_data: dict, context: dict) -> dict` | 核心执行：调 LLM 解析对比结果，失败降级到 _rule_based_comparison |
| `_parse_comparison` | `def _parse_comparison(self, llm_output: str, input_data: dict) -> dict` | 解析 LLM 输出，校验矛盾根因 ∈ VALID_ROOT_CAUSES |
| `_rule_based_comparison` | `def _rule_based_comparison(self, input_data: dict) -> dict` | 规则降级对比，C(N,2) 两两对比 + 关键词矛盾检测 |
| `_detect_conflict_keywords` | `def _detect_conflict_keywords(self, text1: str, text2: str) -> List[str]` | 检测矛盾关键词，需增强为语义矛盾检测 |

---

## 4. 待修改文件

| 操作 | 路径 | 说明 |
|------|------|------|
| modify | `Veritas/ai-service/app/agents/comparer.py` | 增强 _detect_conflict_keywords：除关键词匹配外，增加基于数值/方向/结论的简单语义矛盾检测（如论文A说"提升20%"，论文B说"下降15%"） |
| modify | `Veritas/ai-service/prompts/comparer.txt` | 优化矛盾发现 Prompt：1) 明确要求输出 contradictions 数组；2) 每项含 papers/topic/claim_a/claim_b/evidence_a/evidence_b/root_cause/resolution_suggestion；3) root_cause 必须 ∈ 5 类枚举；4) 增加 1-2 个 few-shot 示例 |
| create | `Veritas/ai-service/tests/test_comparer_conflict_detection.py` | 矛盾检测测试：5 类根因各 1 个用例 + 条件分支激活测试 + 降级路径测试 |

---

## 5. 实现要求

### 5.1 功能需求（FR）

| ID | 优先级 | 描述 | 验收条件 |
|----|--------|------|---------|
| FR-001 | P0 | 增强 _detect_conflict_keywords 方法为 _detect_conflicts（保留原方法兼容）：1) 保留原关键词检测；2) 新增数值矛盾检测（正则匹配数值+方向词，如"提升20%" vs "下降15%"）；3) 新增结论方向矛盾检测（"优于" vs "劣于"，"有效" vs "无效"）。返回 List[Dict] 而非 List[str]，每项含 {type, keywords, claim_a, claim_b}。 | _detect_conflicts 对含数值矛盾的论文对返回非空列表 |
| FR-002 | P0 | 优化 prompts/comparer.txt：1) 明确 contradictions 数组输出格式；2) 每项必含 papers/topic/claim_a/claim_b/evidence_a/evidence_b/root_cause/resolution_suggestion 8 个字段；3) root_cause 必须 ∈ {dataset_bias, metric_difference, condition_difference, assumption_difference, methodological_conflict}；4) 增加 1 个 few-shot 示例展示 dataset_bias 类矛盾的标注格式。 | Prompt 模板含 8 字段输出要求和 few-shot 示例 |
| FR-003 | P0 | 创建 5 类根因测试用例（test_comparer_conflict_detection.py）：1) dataset_bias：两论文使用不同数据集导致结论矛盾；2) metric_difference：使用不同评估指标；3) condition_difference：实验条件不同；4) assumption_difference：假设前提不同；5) methodological_conflict：方法论根本冲突。每用例 mock LLM 返回对应根因的 contradictions，验证 _parse_comparison 正确解析。 | 5 类根因测试用例全部通过，contradictions 数组结构符合 schema |
| FR-004 | P0 | AM4 遗留验证：测试 ComparerAgent 在 graph.py 条件分支中正确激活。1) requires_compare=True 且 papers>=2 时 should_compare 返回 "compare"；2) requires_compare=False 时返回 "generate"；3) papers<2 时返回 "generate"。 | should_compare 条件分支测试 3 个场景全部通过 |
| FR-005 | P1 | 降级路径测试：mock LLM 超时/异常，验证 _fallback_result 调用 _rule_based_comparison，返回 degraded=True 的结果，contradictions 数组不为空（当存在矛盾时）。 | LLM 失败时降级为规则矛盾检测，输出 degraded=True |

### 5.2 降级需求

| 场景 | 策略 |
|------|------|
| 单 Agent 失败 | ComparerAgent LLM 失败时降级为 _rule_based_comparison，返回 degraded=True |
| 多 Agent 失败 | N/A |
| Review 重试上限 | 0 |

---

## 6. 约束

### 6.1 命名规范

| 对象 | Python |
|------|--------|
| 类名 | PascalCase |
| 函数/变量 | snake_case |
| 常量 | UPPER_SNAKE_CASE |
| 文件名 | snake_case.py |

### 6.2 分层规范

- Agent 逻辑在 `agents/`
- Prompt 在 `prompts/`
- 测试在 `tests/`

### 6.3 错误处理

- LLM 失败降级为规则对比，不抛出异常
- Agent 错误处理：`logger.warning` + `_fallback_result`

### 6.4 日志

- 日志库：Loguru
- 禁止：在对比循环中打印 INFO 日志

---

## 7. 禁止动作

| ID | 动作 | 原因 | 严重性 |
|----|------|------|--------|
| FA-001 | 输出伪代码或 TODO 注释 | 必须输出完整可执行代码 | critical |
| FA-002 | 修改 VALID_ROOT_CAUSES 枚举值 | 5 类根因已定义，仅增强检测逻辑 | high |
| FA-003 | 修改 COMPARE_DIMENSIONS 4 维度 | 对比维度保持不变 | high |
| FA-004 | 删除 _rule_based_comparison 降级方法 | 降级路径必须保留 | critical |
| FA-005 | 修改 graph.py should_compare 条件分支逻辑 | 仅测试不修改，逻辑已正确 | high |
| FA-006 | 在 Prompt 中硬编码论文数据 | Prompt 应使用模板变量 | medium |
| FA-007 | 引入外部 NLP 库做语义矛盾检测 | 保持依赖最小化，用规则+正则 | medium |

---

## 8. 测试要求

### 8.1 单元测试

| 测试名 | 描述 | 框架 | 覆盖范围 |
|--------|------|------|---------|
| test_conflict_detection_dataset_bias | dataset_bias 根因测试：mock LLM 返回 dataset_bias 类矛盾，验证解析 | pytest | normal_flow |
| test_conflict_detection_metric_difference | metric_difference 根因测试 | pytest | normal_flow |
| test_conflict_detection_condition_difference | condition_difference 根因测试 | pytest | normal_flow |
| test_conflict_detection_assumption_difference | assumption_difference 根因测试 | pytest | normal_flow |
| test_conflict_detection_methodological_conflict | methodological_conflict 根因测试 | pytest | normal_flow |
| test_should_compare_conditional_branch | AM4 遗留：should_compare 条件分支 3 场景测试 | pytest | normal_flow, boundary_condition |
| test_comparer_degradation_path | 降级路径：LLM 超时 → 规则矛盾检测 → degraded=True | pytest | error_flow, degradation |
| test_detect_conflicts_numeric | 数值矛盾检测："提升20%" vs "下降15%" 返回非空 | pytest | normal_flow |

### 8.2 验证命令

```bash
cd Veritas/ai-service && python -m pytest tests/test_comparer_conflict_detection.py -v
```

**预期结果**：8 个测试用例全部通过

---

## 9. 验收标准

| ID | 验收标准 | 验证方式 |
|----|---------|---------|
| AC-001 | 5 类根因测试用例全部通过，contradictions 数组结构符合 schema（含 8 字段） | automated_test |
| AC-002 | ComparerAgent 在 graph.py 中条件激活正确（3 场景测试） | automated_test |
| AC-003 | LLM 失败时降级为规则矛盾检测，输出 degraded=True | automated_test |
| AC-004 | 数值矛盾检测生效（"提升20%" vs "下降15%" 返回非空） | automated_test |
| AC-005 | Prompt 模板含 8 字段输出要求和 few-shot 示例 | code_review |
