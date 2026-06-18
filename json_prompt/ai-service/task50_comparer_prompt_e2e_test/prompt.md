# task50: 矛盾发现 Prompt + 端到端测试

> **课题编号**：XH-202630
> **子项目**：科研文献助手 — AI 服务模块
> **里程碑**：M5 / AM5：混合检索与功能完善
> **AM5 天数**：Week 9 Day 5
> **版本**：v0.5
> **功能编号**：F3.1.4, F3.1.5
> **优先级**：P0
> **创建日期**：2026-06-17

---

## 1. 背景与上下文

### 1.1 项目背景

XH-202630 科研文献智能助手 — 6-Agent LangGraph 工作流中，ComparerAgent 负责多论文对比与矛盾发现。task49 已增强矛盾检测逻辑和 Prompt 8 字段输出要求，本任务在此基础上进行端到端验证并增加 few-shot 示例。

### 1.2 任务需求

端到端验证 6-Agent 工作流中 ComparerAgent 的矛盾发现能力。优化矛盾发现 Prompt，增加 few-shot 示例。测试 3 篇含矛盾观点的论文输入，验证 contradictions 数组非空且结构完整。验证 ComparerAgent 降级路径：LLM 超时 → 规则矛盾检测 → 输出降级标记。

### 1.3 参考文档

| 文档 | 用途 |
|------|------|
| [docs/ai-service/AI服务模块系统架构文档.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块系统架构文档.md) | 了解 ComparerAgent 端到端调用链路 |
| [docs/ai-service/AI服务模块项目里程碑文档.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块项目里程碑文档.md) | 确认 AM5 Week 9 Day 5 矛盾发现端到端测试交付物 |
| [AGENTS.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/AGENTS.md) | 确认 Agent 降级约束和 Prompt few-shot 规范 |

---

## 2. 当前架构

### 2.1 涉及层级

- `python_ai_service`

### 2.2 相关模块

| 层级 | 模块路径 | 描述 |
|------|---------|------|
| python_ai_service | `app.agents.comparer` | ComparerAgent 已实现 5 类根因检测和规则降级 |
| python_ai_service | `prompts.comparer` | comparer.txt Prompt 模板，需增加 few-shot 示例 |
| python_ai_service | `app.agents.graph` | 6-Agent LangGraph 工作流，compare_node 调用 ComparerAgent |

### 2.3 现有实现

| 文件 | 描述 | 复用方式 |
|------|------|---------|
| `Veritas/ai-service/app/agents/comparer.py` | ComparerAgent 已实现 _run/_parse_comparison/_rule_based_comparison/_detect_conflicts | direct_reuse |
| `Veritas/ai-service/prompts/comparer.txt` | 对比 Prompt 模板已存在（task49 已优化 8 字段输出），需增加 few-shot 示例 | extend |
| `Veritas/ai-service/app/agents/graph.py` | 6-Agent 工作流已实现，端到端测试复用 | direct_reuse |

---

## 3. 相关模块详情

### 3.1 ComparerAgent

- **路径**：`Veritas/ai-service/app/agents/comparer.py`
- **职责**：多论文对比与矛盾发现

| 方法 | 签名 | 描述 |
|------|------|------|
| `_run` | `async def _run(self, prompt: str, input_data: dict, context: dict) -> dict` | 核心执行：调 LLM 解析对比结果，失败降级到 _rule_based_comparison |
| `_parse_comparison` | `def _parse_comparison(self, llm_output: str, input_data: dict) -> dict` | 解析 LLM 输出，校验矛盾根因和 8 字段结构 |
| `_rule_based_comparison` | `def _rule_based_comparison(self, input_data: dict) -> dict` | 规则降级对比，C(N,2) 两两对比 + 矛盾检测 |

### 3.2 ComparerPrompt

- **路径**：`Veritas/ai-service/prompts/comparer.txt`
- **职责**：矛盾发现 Prompt 模板

| 接口 | 签名 | 描述 |
|------|------|------|
| template_variables | `papers: List[Dict], compare_dimensions: List[str]` | Prompt 模板变量 |

---

## 4. 待修改文件

| 操作 | 路径 | 说明 |
|------|------|------|
| modify | `Veritas/ai-service/prompts/comparer.txt` | 增加 1-2 个 few-shot 示例，展示矛盾标注格式（含 8 字段完整输出）。示例应覆盖 dataset_bias 和 methodological_conflict 两类典型矛盾。 |
| create | `Veritas/ai-service/tests/e2e/test_comparer_e2e.py` | 端到端测试：3 篇含矛盾观点的论文 → ComparerAgent 输出 contradictions 数组。验证数组非空、每项含 papers/topic/claim_a/claim_b/root_cause。验证降级路径：mock LLM 超时 → 规则矛盾检测 → degraded=True。 |
| create | `Veritas/ai-service/tests/e2e/test_data/conflict_papers.json` | 3 篇含矛盾观点的论文测试数据：论文A（方法X在数据集D1上提升20%）、论文B（方法X在数据集D2上下降15%）、论文C（方法Y与方法X方法论冲突）。每篇含 title/abstract/method/experiment/conclusion 字段。 |

---

## 5. 实现要求

### 5.1 功能需求（FR）

| ID | 优先级 | 描述 | 验收条件 |
|----|--------|------|---------|
| FR-001 | P0 | 端到端测试覆盖：加载 conflict_papers.json 中 3 篇含矛盾观点的论文，调用 ComparerAgent._run()，验证输出 contradictions 数组非空。测试通过 mock LLM 返回预设矛盾 JSON，确保结果可复现。 | 端到端测试 3 篇论文输入，输出 contradictions 数组非空 |
| FR-002 | P0 | 验证 contradictions 数组结构完整性：每项必含 papers（涉及论文ID列表）/topic（矛盾主题）/claim_a（论文A主张）/claim_b（论文B主张）/root_cause（5类根因之一）。AM5 验收硬指标。 | contradictions 数组每项包含 papers/topic/claim_a/claim_b/root_cause |
| FR-003 | P1 | 优化 prompts/comparer.txt 增加 few-shot 示例：1) 示例1展示 dataset_bias 类矛盾（两论文使用不同数据集导致结论矛盾），完整输出 8 字段；2) 示例2展示 methodological_conflict 类矛盾（方法论根本冲突），完整输出 8 字段。示例使用占位符论文ID，不硬编码真实数据。 | Prompt 模板含 2 个 few-shot 示例，每个展示 8 字段完整输出 |
| FR-004 | P0 | 降级路径端到端验证：mock LLM 抛出 TimeoutError，调用 ComparerAgent._run()，验证：1) 降级到 _rule_based_comparison；2) 返回 degraded=True；3) contradictions 数组仍可能非空（当规则检测到矛盾时）；4) 不抛出异常。 | LLM 超时降级路径正确触发，输出 degraded=True |

### 5.2 降级需求

| 场景 | 策略 |
|------|------|
| 单 Agent 失败 | ComparerAgent LLM 超时降级为 _rule_based_comparison，返回 degraded=True |
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

- 端到端测试在 `tests/e2e/`
- 测试数据在 `tests/e2e/test_data/`
- Prompt 在 `prompts/`

### 6.3 错误处理

- LLM 超时降级为规则对比，不抛出异常
- Agent 错误处理：`logger.warning` + `_fallback_result`

### 6.4 日志

- 日志库：Loguru
- 禁止：在端到端测试中打印 INFO 日志干扰断言

---

## 7. 禁止动作

| ID | 动作 | 原因 | 严重性 |
|----|------|------|--------|
| FA-001 | 输出伪代码或 TODO 注释 | 必须输出完整可执行代码 | critical |
| FA-002 | 在端到端测试中调用真实 LLM API | 必须 mock LLM 确保测试可复现 | critical |
| FA-003 | 修改 ComparerAgent 核心逻辑 | 本任务仅测试和优化 Prompt，不改 Agent 代码 | high |
| FA-004 | 在 few-shot 示例中硬编码真实论文数据 | 使用占位符 paper_id_1/paper_id_2 | medium |
| FA-005 | 删除 task49 已添加的 8 字段输出要求 | 在 task49 基础上增加 few-shot，不删除已有内容 | high |
| FA-006 | 修改 graph.py 工作流逻辑 | 本任务仅测试 ComparerAgent，不改工作流 | high |

---

## 8. 测试要求

### 8.1 单元测试

| 测试名 | 描述 | 框架 | 覆盖范围 |
|--------|------|------|---------|
| test_comparer_e2e_three_papers_conflict | 端到端测试：3 篇含矛盾论文 → contradictions 非空 | pytest | normal_flow, integration |
| test_comparer_e2e_contradictions_schema | 验证 contradictions 数组每项含 papers/topic/claim_a/claim_b/root_cause | pytest | normal_flow, boundary_condition |
| test_comparer_e2e_degradation_timeout | 降级路径：mock LLM 超时 → 规则矛盾检测 → degraded=True | pytest | error_flow, degradation |
| test_comparer_prompt_has_few_shot | 验证 comparer.txt 含 2 个 few-shot 示例 | pytest | normal_flow |

### 8.2 验证命令

```bash
cd Veritas/ai-service && python -m pytest tests/e2e/test_comparer_e2e.py -v
```

**预期结果**：4 个测试用例全部通过

---

## 9. 验收标准

| ID | 验收标准 | 验证方式 |
|----|---------|---------|
| AC-001 | 端到端测试 3 篇论文输入，输出 contradictions 数组非空 | automated_test |
| AC-002 | contradictions 数组每项包含 papers/topic/claim_a/claim_b/root_cause | automated_test |
| AC-003 | LLM 超时降级路径正确触发，输出 degraded=True | automated_test |
| AC-004 | comparer.txt 含 2 个 few-shot 示例，每个展示 8 字段完整输出 | code_review |
