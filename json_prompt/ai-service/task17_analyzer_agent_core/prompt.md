# Task17: AnalyzerAgent 分析员Agent核心逻辑

## 任务概述

| 项目 | 内容 |
|------|------|
| **版本** | v0.2 |
| **里程碑** | M2 / AM2：RAG检索与3-Agent基础可用 |
| **功能编号** | F3.1.3 |
| **涉及层级** | python_ai_service |
| **优先级** | P0 |

## 需求描述

实现 AnalyzerAgent 分析员Agent核心逻辑，产出 `agents/analyzer.py`。

AnalyzerAgent 继承 BaseAgent，负责对检索得到的论文进行 **5维度结构化深度分析**：

| 维度 | 字段 | 内容 |
|------|------|------|
| 研究问题 | research_problem | 论文要解决的核心问题 |
| 核心方法 | core_method | 提出的方法/算法，含创新点 |
| 主要实验 | main_experiments | 实验设置、数据集、对比基线 |
| 核心结论 | core_conclusions | 主要发现和结论 |
| 局限性 | limitations | 方法局限和适用边界 |

每个维度输出 `summary`（摘要）、`confidence`（置信度0-1）、`references`（原文引用出处）。

## 影响范围

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `Veritas/ai-service/app/agents/analyzer.py` | AnalyzerAgent核心逻辑 |

## 核心实现要求

### 类结构

```python
class AnalyzerAgent(BaseAgent):
    FIVE_DIMENSIONS = [
        "research_problem", "core_method",
        "main_experiments", "core_conclusions", "limitations"
    ]

    def __init__(self, llm_service, prompt_manager, timeout=30): ...
    def build_prompt(self, input_data, context) -> str: ...
    async def _run(self, prompt, input_data, context) -> dict: ...
    def build_analysis_prompt(self, paper, user_profile=None) -> str: ...
    def _get_extra_instruction(self, user_profile) -> str: ...
    def _parse_analysis_result(self, llm_output, paper) -> dict: ...
    def _validate_dimensions(self, analysis) -> dict: ...
    def _rule_based_extraction(self, paper) -> dict: ...
```

### _run 核心流程

1. 从 `input_data['papers']` 获取论文列表
2. 遍历每篇论文：
   - 调用 `build_analysis_prompt()` → 渲染分析Prompt
   - 调用 `llm_service.generate()` → 获取LLM输出
   - 调用 `_parse_analysis_result()` → 解析JSON
   - 调用 `_validate_dimensions()` → 验证完整性
3. 每篇处理完后更新 `self.state.progress`
4. 计算 `extraction_quality = mean(各维度confidence)`
5. 返回 `{analysis_results: [...], analyzed_count: N, extraction_quality: 0.X}`

### 降级策略

- **单篇LLM失败**：该论文走 `_rule_based_extraction` 降级 (confidence=0.3, extraction_quality=0.1)，继续处理后续论文
- **全部LLM失败**：所有论文走降级路径，仍返回完整5维度结构
- **JSON解析失败**：先尝试```json```代码块 → ```代码块 → 降级为规则提取

### JSON解析支持格式

- 纯JSON: `{"research_problem": {...}}`
- ```` ```json\n{...}\n``` ````
- ```` ```\n{...}\n``` ````

## 依赖的已有模块

| 模块 | 复用方式 |
|------|---------|
| `app/agents/base.py` → BaseAgent | 直接继承 |
| `app/agents/retriever.py` → Agent实现模式 | 参考 |
| `app/services/llm_service.py` → LLMService.generate() | 直接调用 |
| `app/services/prompt_manager.py` → get_prompt('analyzer', ...) | 直接调用 |
| `prompts/analyzer.txt` → 分析Prompt模板 | 直接使用 |

## 约束

- 5维度字段统一 snake_case（research_problem 而非 researchProblem）
- 单篇论文LLM失败不中断整体分析流程
- LLM调用失败时走 _rule_based_extraction 降级路径
- 每条分析结果必须包含 ai_disclaimer
- 日志使用 Loguru，论文循环内使用 DEBUG 级别

## 禁止行为

- ❌ 输出伪代码或 TODO 注释
- ❌ 修改 base.py / retriever.py / llm_service.py 等已有文件
- ❌ 5维度字段使用 camelCase
- ❌ 单篇LLM失败时中断整体分析
- ❌ 忽略降级场景
- ❌ 修改 prompts/analyzer.txt

## 验证命令

```bash
cd Veritas/ai-service && python -m pytest tests/test_analyzer_agent.py -v
cd Veritas/ai-service && python -c "from app.agents.analyzer import AnalyzerAgent; print('Import OK')"
```

## 验收标准

- [ ] AnalyzerAgent 继承 BaseAgent，name='analyzer'
- [ ] build_prompt 正确调用 prompt_manager.get_prompt('analyzer', ...)
- [ ] _run 正常流程：N篇论文 → N条分析结果（含5维度+disclaimer）
- [ ] _parse_analysis_result 支持3种JSON格式 + 降级
- [ ] _validate_dimensions 补全缺失维度，clamp confidence
- [ ] 单篇LLM失败降级不中断整体流程
- [ ] 全部LLM失败仍返回完整5维度结构
- [ ] 5维度字段全部 snake_case
- [ ] 所有 pytest 测试通过（15+用例）