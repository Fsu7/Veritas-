# 技术教学文档

## 开发思路

### 需求分析过程
本次开发覆盖4个任务（Task 42-45），核心需求是：
1. **Task 42**：将4-Agent LangGraph工作流扩展为6-Agent（增加Coordinator和Comparer），实现条件分支
2. **Task 43**：实现二级降级机制——Agent级（单Agent失败跳过继续）和工作流级（2+Agent失败降级为最小路径）
3. **Task 44**：增强SSE事件数据结构，扩展AgentStateResponse模型，新增workflow_degraded事件
4. **Task 45**：端到端集成测试、个性化差异验证、SSE事件完整性测试

### 技术选型考虑
- **LangGraph StateGraph**：已有4节点图，扩展为6节点需新增coordinator/compare节点和条件边
- **降级策略**：采用二级降级（Agent级+工作流级），与架构文档5.7节定义一致
- **degradation_level双语义**：内部用none/agent/workflow跟踪工作流状态，对外用none/partial/severe/critical反映严重程度，两者在不同上下文使用不冲突
- **SSE事件增强**：保持向后兼容，新增字段使用Optional，旧前端可忽略未知字段

### 架构设计思路
```
6-Agent工作流：
coordinator → retriever → analyzer → [comparer] → generator → [reviewer] → END
                                    ↘ generate(跳过对比)    ↘ END(跳过审核)

降级路径：
- Agent级：单Agent失败 → degraded_agents记录 → 继续后续节点
- 工作流级：2+Agent失败 → degradation_level='workflow' → 跳过可选Agent

SSE事件流：
agent_started → agent_state_update → agent_completed/agent_failed → [workflow_degraded] → ... → analysis_completed
```

### 遇到的问题及解决方案

1. **旧测试不兼容6-Agent**：`test_sse_basic_push.py` 和 `test_integration_am3.py` 的 `_make_mock_agents()` 缺少coordinator，导致orchestrator首先运行coordinator时失败
   - 解决：在 `_make_mock_agents()` 中添加coordinator Agent

2. **agent_failed事件断言错误**：旧测试假设第一个agent_failed是analyzer，但6-Agent工作流中coordinator先运行
   - 解决：改为按agentName过滤查找analyzer的failed事件

3. **个性化测试关键词不匹配**：`test_personalization_block_contains_style_keywords` 使用英文关键词，但实际输出是中文
   - 解决：添加中文风格关键词（"日常用语"、"正式学术"、"口语化"、"学术结构"）

## 实现步骤

1. **Step 1**：修改 `orchestrator.py` 的 `_yield_final()` 方法，在 `analysis_completed` 事件中添加 `degradationLevel` 和 `degradedAgents` 字段
2. **Step 2a**：修改 `agent.py` 的 `_convert_agent_states()`，新增 error/started_at/completed_at/degraded 字段映射
3. **Step 2b**：修改 `agent.py` 的 `analyze()` 端点，根据 degraded_agents 数量计算 degradation_level
4. **Step 3**：扩展 `test_degradation.py`，追加8个测试类（Task 43降级机制）
5. **Step 4**：新建 `test_sse_agent_state_structure.py`，10个测试类（Task 44 SSE结构）
6. **Step 5**：新建 `test_6agent_e2e.py`，5个测试类（Task 45端到端）
7. **Step 6**：新建 `test_personalization_difference.py`，4个测试类（Task 45个性化）
8. **Step 7**：新建 `test_sse_6agent_completeness.py`，5个测试类（Task 45 SSE完整性）
9. **Step 8**：修复旧测试兼容性（test_sse_basic_push.py、test_integration_am3.py），运行全量测试验证

## 解决了什么问题

### 核心问题描述
1. 6-Agent工作流缺少完整的降级机制，Agent失败时无法保证返回可用结果
2. SSE事件数据结构不完整，前端无法感知Agent降级状态和错误详情
3. AgentStateResponse模型缺少关键字段（error/时间戳/降级标记），Java后端无法获取完整Agent状态
4. 缺少端到端集成测试验证6-Agent工作流和个性化差异

### 解决方案对比
| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| Agent级降级+工作流级降级 | 精细化控制，保证结果可用 | 实现复杂 | ✅ |
| 仅Agent级降级 | 实现简单 | 多Agent失败时结果质量差 | ❌ |
| 直接返回错误 | 实现最简单 | 用户体验差 | ❌ |

### 最终方案的优势
- 二级降级确保任何场景下都有可用结果
- degradation_level双语义满足内部追踪和对外展示的不同需求
- SSE事件增强保持向后兼容

## 变更内容

### 新增文件
- `tests/test_sse_agent_state_structure.py` — Task 44 SSE事件结构测试（10个测试类）
- `tests/test_6agent_e2e.py` — Task 45 6-Agent端到端测试（5个测试类）
- `tests/test_personalization_difference.py` — Task 45 个性化差异测试（4个测试类）
- `tests/test_sse_6agent_completeness.py` — Task 45 SSE完整性测试（5个测试类）

### 修改文件
- `app/agents/orchestrator.py` — `_yield_final()` 添加 degradationLevel/degradedAgents
- `app/api/endpoints/agent.py` — `_convert_agent_states()` 新增4字段；`analyze()` 计算 degradation_level
- `tests/test_degradation.py` — 追加8个测试类（不修改已有代码）
- `tests/test_sse_basic_push.py` — `_make_mock_agents()` 添加 coordinator 适配6-Agent
- `tests/test_integration_am3.py` — 同上修复

### 配置变更
- 无配置文件变更

## 关键技术点

### 使用的核心技术
1. **LangGraph StateGraph**：6节点+3条件边的工作流编排
2. **二级降级策略**：Agent级（skip-and-continue）+ 工作流级（minimal path）
3. **SSE事件流**：9种事件类型，实时推送Agent状态
4. **Pydantic模型扩展**：camelCase alias实现跨系统字段映射
5. **PersonalizationService**：4维度用户画像驱动差异化指令

### 代码实现亮点
- `_calculate_degradation_level()` 方法：基于 `self._degraded_agents` 数量动态计算降级等级
- `_convert_agent_states()` 中的 degraded 判断逻辑：`status=='failed' or state_dict.get('degraded', False)` 覆盖两种降级场景
- 测试中使用 Jaccard 距离量化个性化差异度，确保>60%

### 需要注意的细节
- `degradation_level` 在 graph.py 中使用 `'none'/'agent'/'workflow'`，在 API/SSE 中使用 `'none'/'partial'/'severe'/'critical'`，两者语义不同但共存
- `agent_completed` 事件的 `intermediateResult` 现在是完整JSON（非截断），可能较大
- 旧测试文件中 `_make_mock_agents()` 必须包含 coordinator，否则 orchestrator 会因缺少 coordinator 而产生意外行为

## 经验总结

### 开发过程中的收获
1. 6-Agent工作流的降级设计需要在每个节点函数中正确处理 `result.get('degraded')` 信号
2. SSE事件增强时保持向后兼容是关键——新字段使用Optional，不删除已有字段
3. 测试先行策略有效——先写测试再写代码，确保每个功能点都有覆盖

### 踩过的坑及如何避免
1. **旧测试兼容性**：6-Agent扩展后，所有使用 `_make_mock_agents()` 的旧测试都需要添加 coordinator。避免方法：在修改 orchestrator 工作流时，同步更新所有测试辅助函数
2. **agent_failed断言顺序**：不能假设第一个 failed 事件就是目标Agent，应按 agentName 过滤查找
3. **中文关键词匹配**：个性化指令输出为中文，测试断言应使用中文关键词

### 最佳实践建议
1. 降级机制测试应覆盖：正常流程、单Agent失败、多Agent失败、全流程超时四种场景
2. SSE事件测试应验证：事件类型完整性、字段存在性、事件顺序、ID单调递增
3. 个性化差异测试应使用极端画像（4维度全不同），确保差异度>60%
4. 修改工作流节点顺序时，务必检查所有测试文件的 mock Agent 集合
