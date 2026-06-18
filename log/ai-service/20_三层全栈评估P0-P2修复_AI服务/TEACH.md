# 技术教学文档 — AI 服务层 P0-P2 修复

## 开发思路

### 需求分析过程
本次修复源于《三层全栈综合技术评估报告》对 AI 服务层的全面审查。评估识别出 5 项问题（P0×2、P1×2、P2×1），涵盖安全漏洞、性能瓶颈、代码质量三个维度。

分析优先级：
1. **安全优先**：P0-6 审核降级放行是质量门禁漏洞，必须最先修复
2. **稳定性次之**：P0-7 Token 爆炸会导致 LLM 调用失败，影响核心功能
3. **性能优化**：P1-6 并行化提升用户体验
4. **代码质量**：P1-7、P2-5 提升可维护性

### 技术选型考虑

#### P1-6 并行化方案对比
| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| `asyncio.gather` + `Semaphore` | 原生异步、顺序保证、并发可控 | 需手动管理 Semaphore | ✅ |
| `asyncio.TaskGroup`（Python 3.11+） | 更现代的 API | 项目用 Python 3.10，不兼容 | ❌ |
| 线程池 `ThreadPoolExecutor` | 兼容同步代码 | LLM 调用是 async，线程池反而增加开销 | ❌ |

#### P0-7 截断策略对比
| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| 按维度优先级截断 | 保留最关键信息 | 需定义优先级 | ✅ |
| 按字符数均匀截断 | 实现简单 | 可能截断关键维度 | ❌ |
| 摘要压缩（二次 LLM 调用） | 信息保留最完整 | 增加延迟和成本 | ❌（未来优化） |

### 架构设计思路
- **保持 Agent 接口不变**：所有修复在 Agent 内部完成，不改变 LangGraph 工作流结构
- **降级透明化**：`review_skipped` 标记让前端能区分"审核通过"与"审核降级"
- **工具复用**：`json_parser.py` 作为公共工具，供所有 Agent 复用

### 遇到的问题及解决方案

#### 问题1：并行化后结果顺序不稳定
- **现象**：`asyncio.gather` 返回结果顺序与 papers 顺序不一致
- **原因**：各任务完成时间不同
- **解决**：返回 `(idx, result)` 元组，按 idx 重新排序

#### 问题2：Semaphore 在测试中不生效
- **现象**：单元测试中并发度限制未生效
- **原因**：mock 的 LLM 调用是同步的，不涉及真实 await
- **解决**：测试验证逻辑正确性即可，并发度限制在集成测试中验证

## 实现步骤

### 1. P0-6 审核降级标记（graph.py）
1. 定位 `reviewer_node` 的降级分支（except 块）
2. 在 `review_result` 中新增 `review_skipped = True`
3. 确保 `approved` 仍为 True（保持降级放行行为），但前端可据 `review_skipped` 提示

### 2. P0-7 Token 截断（generator/comparer/reviewer）
1. 定义 `MAX_ANALYSIS_CHARS = 8000`（reviewer 为 6000）
2. 实现 `_truncate_analysis_for_prompt` 方法：
   - 遍历各维度，按优先级累积
   - 超过上限时截断当前维度并停止
3. 在 `build_prompt` 中调用截断方法

### 3. P1-6 Analyzer 并行化（analyzer.py）
1. 新增 `concurrency` 参数（默认 3）
2. 提取 `_analyze_paper_with_semaphore` 包装方法
3. `_run` 中用 `asyncio.gather` 并行执行
4. 按 idx 顺序整理结果

### 4. P1-7 regenerate_count 简化（graph.py）
1. 原逻辑：嵌套 if 判断 `review_result` 存在性 + `approved` 为 False
2. 简化为：`if review_result and not review_result.get("approved", True): update["regenerate_count"] = state.get("regenerate_count", 0) + 1`

### 5. P2-5 统一 JSON 解析（json_parser.py）
1. 新建 `app/utils/json_parser.py`
2. 实现 `extract_json(text)` 函数，4 级降级：
   - L1：直接 `json.loads`
   - L2：提取 ```json 代码块
   - L3：正则匹配 `{...}` 结构
   - L4：返回空 dict 兜底

## 解决了什么问题

### 核心问题描述
1. **审核降级放行**：Reviewer 降级时无标记，前端无法区分"审核通过"与"降级跳过"
2. **Token 爆炸**：10 篇论文的完整分析结果注入 Prompt，可能超过 LLM 上下文限制
3. **串行瓶颈**：10 篇论文串行分析，耗时 ~30s
4. **JSON 解析分散**：各 Agent 各自实现，降级策略不一致

### 解决方案对比
- 审核降级：标记模式 vs 拦截降级（拦截会影响可用性，选择标记）
- Token 截断：按维度截断 vs 摘要压缩（截断无额外成本，选择截断）
- 并行化：Semaphore vs TaskGroup（兼容性考虑选择 Semaphore）

### 最终方案的优势
- 最小侵入：不改变 Agent 接口和工作流结构
- 可观测性：`review_skipped` 标记提供降级可见性
- 可配置：`concurrency` 参数允许调整并发度

## 变更内容

### 新增文件
- `app/utils/json_parser.py`：统一 JSON 解析工具，4 级降级策略

### 修改文件
| 文件 | 变更点 |
|------|--------|
| `app/agents/graph.py` | 降级分支新增 `review_skipped=True`；简化 `regenerate_count` 递增 |
| `app/agents/generator.py` | 新增 `MAX_ANALYSIS_CHARS`、`_truncate_analysis_for_prompt`、`_truncate_dimension` |
| `app/agents/comparer.py` | 同 generator |
| `app/agents/reviewer.py` | 新增 `MAX_PAPERS_CHARS`、`_truncate_papers_for_prompt`、`_rule_based_citation_check` |
| `app/agents/analyzer.py` | 新增 `concurrency` 参数、`_analyze_paper_with_semaphore`；`_run` 改为 `asyncio.gather` |

### 配置变更
- `AnalyzerAgent.__init__` 新增 `concurrency: int = 3` 参数

## 关键技术点

### 1. asyncio.gather + Semaphore 并发控制
```python
semaphore = asyncio.Semaphore(self.concurrency)
async def _analyze_paper_with_semaphore(self, paper, context, semaphore, idx, total):
    async with semaphore:
        # 临界区：最多 concurrency 个任务同时执行
        result = await self._analyze_single_paper(paper, context)
        return idx, result, None
```
- `Semaphore` 保证同时只有 N 个 LLM 调用在途
- `gather` 返回结果顺序与 tasks 列表一致（但内容顺序需按 idx 重排）

### 2. 按维度优先级截断
```python
DIMENSION_PRIORITY = ["research_problem", "core_method", "main_experiments", "core_conclusions", "limitations"]

def _truncate_analysis_for_prompt(self, analysis_results):
    for result in analysis_results:
        truncated = {}
        total_chars = 0
        for dim in DIMENSION_PRIORITY:
            if dim in result:
                dim_text = str(result[dim])
                if total_chars + len(dim_text) <= MAX_ANALYSIS_CHARS:
                    truncated[dim] = result[dim]
                    total_chars += len(dim_text)
                else:
                    # 截断当前维度
                    truncated[dim] = dim_text[:MAX_ANALYSIS_CHARS - total_chars] + "..."
                    break
```

### 3. 审核降级标记模式
```python
# 降级时
review_result["approved"] = True  # 保持放行
review_result["review_skipped"] = True  # 标记降级
# 前端可据此显示"审核服务降级，建议人工核查"
```

### 4. JSON 解析 4 级降级
```python
def extract_json(text):
    # L1: 直接解析
    try: return json.loads(text)
    except: pass
    # L2: 提取代码块
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        try: return json.loads(match.group(1))
        except: pass
    # L3: 正则匹配
    match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if match:
        try: return json.loads(match.group(0))
        except: pass
    # L4: 兜底
    return {}
```

## 经验总结

### 开发过程中的收获
1. **asyncio 并发控制**：`Semaphore` 是限制并发度的标准方式，比手动管理任务队列更简洁
2. **降级透明化**：降级时不应只返回默认值，还应标记降级状态，让调用方能感知
3. **截断优先级**：截断时应按业务重要性保留关键字段，而非均匀截断

### 踩过的坑及如何避免
1. **`asyncio.gather` 结果顺序**：虽然 `gather` 保持 tasks 顺序，但如果用 `asyncio.as_completed` 则顺序不确定。本次用 `gather` + idx 元组确保稳定
2. **Semaphore 在 mock 测试中不生效**：mock 的 async 函数不真正 await，Semaphore 不会阻塞。需在集成测试中验证并发限制
3. **ServerSentEvent data 类型**：Spring 的 `ServerSentEventHttpMessageReader` 可能将 JSON data 解析为 Map 而非 String，需兼容两种情况（此为 Java 端经验，Python 端无此问题）

### 最佳实践建议
1. **LLM 调用必加超时和截断**：避免因输入过长导致调用失败或费用激增
2. **降级必须可观测**：降级时返回标记字段，不要静默降级
3. **并发度可配置**：硬编码并发度不利于调优，应作为构造参数暴露
4. **公共工具提取**：JSON 解析等通用逻辑应提取为公共工具，避免各模块重复实现
