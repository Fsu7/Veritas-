# 技术教学文档 — AM4 CoordinatorAgent 与 Prompt 模板升级

## 开发思路

### 需求分析过程
1. **M4 里程碑目标**：从 3-Agent 线性工作流（task22）扩展为 6-Agent 含条件分支的完整工作流
2. **缺失入口分析**：6-Agent 工作流缺少"任务分解"环节，LangGraph 入口节点需要根据用户 query 决定启用哪些下游 Agent
3. **职责边界确认**：依据 ADR-002 单向数据流，Coordinator 仅做任务分解，不直接调用其他 Agent（避免反模式 AP-09 Planner-Executor Hybrid）
4. **降级策略必要性**：依据 ADR-002 可用性约束，Coordinator 失败会阻塞整个工作流启动，必须有降级路径不受 LLM 失败影响

### 技术选型考虑
| 候选方案 | 优势 | 劣势 | 决策 |
|---------|------|------|------|
| LLM 强制任务分解 | 输出更智能 | 失败率高、不可预测 | ❌ 不可单独使用 |
| 固定模板分解 | 100% 可用 | 缺乏灵活性 | ❌ 用户体验差 |
| LLM 优先 + 规则降级 | 智能 + 可用 | 实现复杂 | ✅ 选用（task32 实现） |
| Jinja2 Prompt 模板 | 语法强大 | 引入新依赖、违反分层约束 | ❌ |
| string.Template 兼容 | 与现有 PromptManager 兼容 | 语法简单 | ✅ 选用（task33） |

### 架构设计思路
1. **Coordinator-Worker 模式**：Coordinator 是任务分解器，Worker 是 LangGraph 编排的下游 Agent
2. **三层降级保护**：LLM 调用失败 → JSON 解析失败 → 子任务数 < 2 → 补全规则分解子任务
3. **进度可视化**：通过 `state.update_progress(0.2/0.5/0.8/1.0, ...)` 渐变，SSE 推送前端可视化
4. **Prompt 工程五层结构**：System Context / Task Context / Execution Protocol / Few-shot / Self-Check

### 遇到的问题及解决方案
| 问题 | 解决方案 |
|------|---------|
| MagicMock `call_args` 返回 None 无法 unpack | 改用 `call_args[0]` 和 `call_args[1]` 分别获取 args 和 kwargs |
| LLM 输出非 JSON 格式 | 三段解析策略：` ```json ... ``` ` / ` ``` ... ``` ` / 整体文本 |
| 子任务数 < 2 强制约束 | 强制降级到 `_rule_based_decomposition` 补全 |
| 模板 4 个变量必须与 build_prompt 一致 | 在 `task32 build_prompt` 和 `task33 模板`双重约定 `$query / $user_profile / $paper_ids / $analysis_type` |
| Prompt 注入风险 | `_sanitize_topic` 实现 500 字符长度限制 + 控制字符清理 |
| 用户画像字段可能是 camelCase | `_normalize_profile` 兼容 `educationLevel` ↔ `education_level` |

## 实现步骤

1. **第一步**：创建 `app/agents/coordinator.py`，继承 `BaseAgent`，实现 `__init__` + 6 个类常量
2. **第二步**：实现 `build_prompt`，调用 `prompt_manager.get_prompt('coordinator', query=, user_profile=, paper_ids=, analysis_type=)`
3. **第三步**：实现 `_run` 核心逻辑（进度渐变 + LLM 调用 + 解析 + 降级兜底）
4. **第四步**：实现 `_parse_task_breakdown` 三段 JSON 解析 + 2-5 子任务约束
5. **第五步**：实现 `_rule_based_decomposition` 规则分解（5 种 analysis_type × paper_ids 数量 → 2-5 子任务）
6. **第六步**：实现 `_determine_required_tasks` 计算 `requires_compare` / `requires_review` 标记
7. **第七步**：实现 `_fallback_result`（覆盖 BaseAgent）和 `_summarize_result`（覆盖 BaseAgent）
8. **第八步**：实现 `_sanitize_topic`（Prompt 注入防护：500 字符限制 + 控制字符清理）
9. **第九步**：编写 `tests/test_coordinator_agent.py`（23 个测试用例）
10. **第十步**：运行单元测试 + 6 个 verification_commands 验证
11. **第十一步**：重写 `prompts/coordinator.txt`（v1 57 行 → v2 222 行五层结构）
12. **第十二步**：模板验证（PromptManager 加载 + 渲染 + 安全 grep + Token 预算）
13. **第十三步**：回归测试确保未破坏既有 123 个测试

## 解决了什么问题

### 核心问题描述
1. **6-Agent 工作流缺少入口节点**：M2 阶段 task22 完成了 3-Agent 线性工作流，但 M4 阶段 6-Agent 含条件分支工作流缺少任务分解入口
2. **LLM 失败导致整个工作流中断**：如果不设计降级路径，Coordinator 失败会导致 LangGraph 流程完全阻塞
3. **v1 Prompt 模板过于简单**：仅 57 行，无法支持复杂的多论文对比场景
4. **用户画像未显式影响子任务分解**：v1 模板未说明画像如何影响具体子任务参数

### 解决方案对比
| 方案 | 优势 | 劣势 |
|------|------|------|
| 仅 LLM 分解 | 灵活 | 失败率高 |
| 仅规则分解 | 100% 可用 | 缺乏灵活性 |
| **LLM + 规则降级** | 智能 + 可用 | 实现复杂 |

### 最终方案的优势
1. **三段 JSON 解析 + 规则降级**：保证 LLM 输出格式异常时也能继续
2. **2-5 子任务强制约束**：避免 LLM 产生过多/过少子任务导致 LangGraph 失败
3. **5 步 CoT + 5 项 Self-Check**：Prompt 模板显式引导 LLM 推理并自检
4. **Few-shot 单示例**：避免 Prompt Monster 反模式，控制 Token 预算在 2000-3000

## 变更内容

### 新增文件
- `Veritas/ai-service/app/agents/coordinator.py`（365 行）
  - CoordinatorAgent 类（继承 BaseAgent）
  - 11 个方法 + 6 个类常量 + 1 个 camelCase → snake_case 映射
  - 完整的 30s 超时 + LLM 失败/JSON 失败/空输出/超时 降级保护
- `Veritas/ai-service/tests/test_coordinator_agent.py`（370 行）
  - 23 个单元测试用例
  - 覆盖 normal_flow / boundary_condition / error_flow / degradation

### 重写文件
- `Veritas/ai-service/prompts/coordinator.txt`（v1 57 行 → v2 222 行）
  - 五层固定结构：System Context / Task Context / Execution Protocol / Few-shot / Self-Check
  - 4 个变量契约：$query / $user_profile / $paper_ids / $analysis_type
  - 5 步 CoT + 5 项 Self-Check
  - 1 个 multi_paper_comparison Few-shot 示例
  - 4 项用户画像 → 子任务个性化映射
  - 8516 字符（Token 预算 2000-3000）

### 配置变更
- 无（保持 `settings.AGENT_TIMEOUT = 30` 不变）

## 关键技术点

### 使用的核心技术
1. **LangGraph StateGraph 入口节点模式**：Coordinator 作为第一个节点
2. **Coordinator-Worker 模式**：任务分解 + 委派
3. **三级降级策略**：LLM 失败 → JSON 失败 → 子任务数 < 2 补全
4. **Chain-of-Thought 推理**：5 步显式推理过程
5. **Self-Check 清单**：5 项强制自检
6. **Few-shot Learning**：1 个示例引导
7. **Prompt 工程规范**：string.Template 兼容
8. **Prompt 注入防护**：500 字符限制 + 控制字符清理

### 代码实现亮点
1. **`_extract_json` 三段解析**：覆盖 LLM 输出常见格式
2. **`_rule_based_decomposition` 规则分解**：覆盖 5 种 analysis_type × 多种 paper_ids 数量
3. **`_determine_required_tasks` 条件标记**：LangGraph 条件边驱动
4. **`_sanitize_topic` Prompt 注入防护**：长度限制 + 控制字符清理
5. **`_normalize_profile` 跨系统字段兼容**：camelCase ↔ snake_case

### 需要注意的细节
1. **不要在 coordinator.py 中修改 prompts/coordinator.txt**：违反 FA-008
2. **不要使用 camelCase 字段命名**：违反跨系统一致性（snake_case 是硬约束）
3. **不要让 CoordinatorAgent 失败时返回 None/空 dict**：违反可用性约束 ADR-002
4. **不要在 Prompt 模板中使用 {{variable}} Jinja2 语法**：违反 FA-001（保持 string.Template 兼容）
5. **不要超过 1 个 Few-shot 示例**：违反 FA-004（避免 Prompt Monster）
6. **不要在 Prompt 模板中包含降级逻辑代码**：违反 FA-003（职责分离）

## 经验总结

### 开发过程中的收获
1. **任务分解器是 6-Agent 工作流的关键入口**：缺失会导致整个工作流无法启动
2. **降级策略是 LLM 应用的核心要求**：必须设计三级保护
3. **Prompt 模板的五层结构是高效工程的产物**：System/Task/Execution/Few-shot/Self-Check 缺一不可
4. **string.Template 兼容性是关键约束**：避免引入 Jinja2 依赖可减少 90% 的实施风险
5. **Few-shot 单示例优于多示例**：1 个高质量示例比 3 个中等示例更有效

### 踩过的坑及如何避免
1. **坑1：MagicMock `call_args` 返回 None 无法 unpack**
   - 解决：使用 `call_args[0]` 和 `call_args[1]` 分别获取 args 和 kwargs
2. **坑2：忘记在 _fallback_result 中调用 _rule_based_decomposition**
   - 解决：测试 `test_fallback_result_preserves_langgraph_flow` 强制要求降级结果包含 >= 2 子任务
3. **坑3：模板变量拼写不一致（$userProfile vs $user_profile）**
   - 解决：在 build_prompt 和 模板双重约定 snake_case
4. **坑4：LLM 输出非 JSON 格式导致解析失败**
   - 解决：三段解析策略（` ```json ... ``` ` / 整体 `{ ... }` / raw）

### 最佳实践建议
1. **任务分解器设计原则**：仅做分解，不做执行；LLM 优先 + 规则降级；2-5 子任务强制约束
2. **Prompt 模板设计原则**：五层结构；Few-shot 单示例；Self-Check 清单；string.Template 兼容
3. **降级策略设计原则**：LLM 失败 → JSON 失败 → 子任务数 < 2 补全；degraded=True 标识
4. **测试设计原则**：覆盖 normal_flow / boundary_condition / error_flow / degradation 四种场景
5. **日志规范**：仅记录摘要（子任务数、关键决策），不输出完整 LLM Prompt/输出

### 后续优化方向
1. **任务34 Comparer Agent**：参考 CoordinatorAgent 模式实现对比节点
2. **task22-25 SSE 集成**：Coordinator 完成时通过 SSE 推送 `sub_tasks` 给前端可视化
3. **集成测试**：Coordinator + Retriever + Analyzer + Generator + Reviewer 端到端流程
4. **Prompt v2 模板升级**：analyzer.txt / generator.txt / retriever.txt 也升级到 v2 标准模板
5. **性能测试**：Coordinator 30s 超时边界场景 + 降级路径耗时分析