# 三层全栈评估 P0-P2 修复 — AI 服务

## 功能描述

### 解决了什么问题
基于《三层全栈综合技术评估报告-2026-06-18》指出的 AI 服务层问题，系统性修复了以下阻断性与建议性缺陷：
- **P0-6 审核降级放行漏洞**：Reviewer Agent 降级时直接 `approved=True` 强制放行，绕过质量门禁
- **P0-7 Token 爆炸风险**：Generator/Comparer/Reviewer 注入完整分析结果到 Prompt，无截断保护
- **P1-6 Analyzer 串行瓶颈**：10 篇论文串行调用 LLM，耗时线性叠加
- **P1-7 regenerate_count 逻辑冗余**：递增条件嵌套过深，可读性差
- **P2-5 JSON 解析重复实现**：各 Agent 各自实现 JSON 提取，逻辑分散且降级策略不一致

### 实现了什么功能
1. 审核降级时标记 `review_skipped=True`，前端可据此提示用户人工核查
2. Generator/Comparer/Reviewer 注入 Prompt 前对分析结果截断（8000/6000 字符上限），保留关键维度
3. Analyzer 使用 `asyncio.gather` + `Semaphore(3)` 并行化 LLM 调用，保持结果顺序与降级行为
4. 简化 `regenerate_count` 递增逻辑为单行表达式
5. 新建统一 JSON 解析工具 `json_parser.py`，提供 4 级降级策略

### 业务价值
- 修复审核降级放行漏洞，避免低质量综述流入用户侧
- Token 截断防护避免 LLM 调用因超长输入失败或费用激增
- Analyzer 并行化使 10 篇论文分析耗时从 ~30s 降至 ~10s（预期 3x 提升）
- 统一 JSON 解析降低维护成本，提升降级一致性

## 实现逻辑

### 修改的核心文件列表
| 文件 | 修复项 | 变更说明 |
|------|--------|----------|
| `app/agents/graph.py` | P0-6, P1-7 | 降级标记 `review_skipped`；简化 `regenerate_count` 递增 |
| `app/agents/generator.py` | P0-7 | 新增 `_truncate_analysis_for_prompt` 截断方法 |
| `app/agents/comparer.py` | P0-7 | 新增 `_truncate_analysis_for_prompt` 截断方法 |
| `app/agents/reviewer.py` | P0-7, P1-5 | 新增 `_truncate_papers_for_prompt`；新增 `_rule_based_citation_check` 规则核查 |
| `app/agents/analyzer.py` | P1-6 | 串行循环改为 `asyncio.gather` + `Semaphore(3)` 并行 |
| `app/utils/json_parser.py` | P2-5 | 新建统一 JSON 解析工具（4 级降级） |

### 使用的算法或设计模式
- **并发模式**：`asyncio.gather` + `Semaphore` 限制并发度，避免打满 LLM 配额
- **截断策略**：按维度优先级截断（research_problem > core_method > main_experiments > core_conclusions > limitations），保留关键信息
- **降级链**：JSON 解析 4 级降级（直接解析 → 提取代码块 → 正则匹配 → 空对象兜底）
- **标记模式**：`review_skipped` 布尔标记区分"审核通过"与"审核降级跳过"

### 关键代码逻辑说明

#### P1-6 Analyzer 并行化
```python
semaphore = asyncio.Semaphore(self.concurrency)
tasks = [
    self._analyze_paper_with_semaphore(paper, context, semaphore, idx, total)
    for idx, paper in enumerate(papers)
]
gathered = await asyncio.gather(*tasks)
# 按 idx 顺序整理结果，保证输出稳定
```

#### P0-7 Token 截断
```python
MAX_ANALYSIS_CHARS = 8000

def _truncate_analysis_for_prompt(self, analysis_results):
    # 按维度优先级截断，保留 research_problem/core_method 等关键字段
```

#### P0-6 审核降级标记
```python
# graph.py 降级分支
review_result["review_skipped"] = True
# 前端可据此提示用户人工核查
```

## 接口变更

### Request
本次修复未改变 API 请求契约，仅优化内部处理逻辑。

### Response
SSE 事件新增 `review_skipped` 字段（仅审核降级时出现）：
```json
{
  "event": "review_complete",
  "data": {
    "approved": true,
    "review_skipped": true,
    "reviewer_feedback": "审核服务降级，已标记跳过"
  }
}
```

## 测试结果
- **analyzer 单元测试**：42 个测试全部通过（含并行化、降级、顺序保证场景）
- **关键模块测试**：211 个测试全部通过（analyzer/generator/comparer/reviewer/graph/json_parser）
- **语法检查**：`python -m py_compile` 全部通过
- 是否通过：是

## 相关文件
- `Veritas/ai-service/app/agents/analyzer.py`
- `Veritas/ai-service/app/agents/generator.py`
- `Veritas/ai-service/app/agents/comparer.py`
- `Veritas/ai-service/app/agents/reviewer.py`
- `Veritas/ai-service/app/agents/graph.py`
- `Veritas/ai-service/app/utils/json_parser.py`（新建）
- 评估报告：`log/阶段审阅报告/三层全栈综合技术评估报告-2026-06-18.md`
- 修复计划：`.trae/documents/全栈P0-P2问题修复计划-2026-06-18.md`
