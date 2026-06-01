# AnalyzerAgent深度分析与Prompt模板

## 功能描述
- 解决了论文深度分析的核心问题：如何从论文标题和摘要中结构化提取5个关键维度信息（研究问题、核心方法、主要实验、核心结论、局限性）
- 实现了AnalyzerAgent完整功能：5维度嵌套结构提取、JSON解析4策略、LLM降级到规则提取、个性化指令适配、AI内容声明
- 增强了analyzer Prompt模板：9块结构化模板（含CoT推理链、嵌套JSON Schema、AI声明块）
- 编写了42个单元测试，覆盖正常/错误/边界/降级全流程
- 业务价值：AnalyzerAgent是6-Agent工作流中的第三环，为ComparerAgent（对比）和GeneratorAgent（综述生成）提供结构化输入

## 实现逻辑
- 修改的核心文件列表：
  - `app/agents/analyzer.py` — AnalyzerAgent核心逻辑
  - `prompts/analyzer.txt` — Prompt模板增强
  - `tests/test_analyzer_agent.py` — 42个单元测试

- 使用的算法或设计模式：
  - **策略模式**：JSON解析4策略（纯JSON → ```json```块 → ```plain```块 → 花括号提取），逐级降级
  - **模板方法模式**：继承BaseAgent，实现`_run()`和`build_prompt()`抽象方法
  - **降级模式**：LLM失败 → `_rule_based_extraction()`规则提取兜底，confidence统一0.3
  - **个性化适配**：`_get_extra_instruction()`根据knowledge_level和education_level映射不同指令

- 关键代码逻辑说明：
  - `_run()`：遍历papers列表，逐篇调用`_analyze_single_paper()`，计算全局`extraction_quality`（所有维度confidence均值）
  - `_parse_analysis_result()`：4策略JSON解析，失败时传入paper参数触发规则提取兜底
  - `_validate_dimensions()`：补全缺失维度（confidence=0.3），clamp到[0.0,1.0]，注入analysis_id和ai_disclaimer
  - `_rule_based_extraction()`：所有维度confidence=0.3，extraction_quality=0.1，含ai_disclaimer
  - `_get_extra_instruction()`：knowledge_level映射（beginner→通俗解释、intermediate→方法对比、advanced→研究空白、expert→前沿洞察）

## 接口变更

### Request（_run / execute 输入）
```json
{
  "papers": [
    {
      "paper_id": "arxiv_2024_001",
      "title": "Attention Is All You Need",
      "abstract": "The dominant sequence transduction models..."
    }
  ]
}
```

### Response（_run / execute 输出）
```json
{
  "analysis_results": [
    {
      "paper_id": "arxiv_2024_001",
      "degraded": false,
      "paper_title": "Attention Is All You Need",
      "analysis_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "ai_disclaimer": "⚠️ 本分析由 AI 生成，仅供参考",
      "research_problem": {
        "summary": "论文要解决序列转导模型中循环/卷积网络计算效率低的问题...",
        "confidence": 0.92,
        "references": ["The dominant sequence transduction models..."]
      },
      "core_method": {
        "summary": "提出Transformer架构，完全基于注意力机制...",
        "confidence": 0.95,
        "references": ["We propose a new simple network architecture..."]
      },
      "main_experiments": {
        "summary": "在WMT 2014英德翻译任务上验证...",
        "confidence": 0.88,
        "references": ["Experiments on two machine translation tasks..."]
      },
      "core_conclusions": {
        "summary": "Transformer在翻译质量上超越已有模型...",
        "confidence": 0.90,
        "references": ["Our model achieves 28.4 BLEU..."]
      },
      "limitations": {
        "summary": "长序列上的计算成本较高...",
        "confidence": 0.80,
        "references": ["The paper discusses the limitations..."]
      }
    }
  ],
  "degraded_papers": [],
  "total_analyzed": 1,
  "extraction_quality": 0.89
}
```

### 降级Response（LLM失败时）
```json
{
  "analysis_results": [
    {
      "paper_id": "arxiv_2024_001",
      "degraded": true,
      "degraded_reason": "LLM error on second paper",
      "paper_title": "Attention Is All You Need",
      "research_problem": {
        "summary": "The dominant sequence transduction models...",
        "confidence": 0.3,
        "references": []
      },
      "core_method": {
        "summary": "论文未明确提及",
        "confidence": 0.3,
        "references": []
      },
      "main_experiments": { "summary": "论文未明确提及", "confidence": 0.3, "references": [] },
      "core_conclusions": { "summary": "论文未明确提及", "confidence": 0.3, "references": [] },
      "limitations": { "summary": "论文未明确提及", "confidence": 0.3, "references": [] },
      "ai_disclaimer": "⚠️ 本分析由 AI 生成，仅供参考",
      "extraction_quality": 0.1
    }
  ],
  "degraded_papers": ["arxiv_2024_001"],
  "total_analyzed": 1,
  "extraction_quality": 0.3
}
```

## 测试结果
- 测试场景1：42个AnalyzerAgent单元测试 — 全部通过
- 测试场景2：12个PromptManager测试（含analyzer模板渲染）— 全部通过
- 测试场景3：80个Agent相关测试（analyzer+prompt_manager+retriever）— 全部通过
- 测试场景4：294个全量测试（排除7个预存LLM配置失败）— 全部通过
- 是否通过：是

### 测试覆盖详情（12个测试类42个方法）
| 测试类 | 方法数 | 覆盖内容 |
|--------|--------|---------|
| TestAnalyzerAgentInit | 3 | 继承BaseAgent、name=analyzer、timeout |
| TestBuildPrompt | 2 | prompt_manager调用、user_profile适配 |
| TestGetExtraInstruction | 6 | beginner/intermediate/advanced/expert/None/无knowledge_level |
| TestRunSuccessFlow | 3 | 3篇论文、进度更新、结果结构 |
| TestRunDegradation | 3 | 单篇LLM失败、全失败、空papers |
| TestParseAnalysisResult | 7 | 纯JSON/json块/plain块/畸形/空串/文本包裹/无paper兜底 |
| TestValidateDimensions | 8 | 缺失维度/confidence clamp/None/非数字/ai_disclaimer/analysis_id |
| TestRuleBasedExtraction | 3 | 5维度/confidence=0.3/extraction_quality=0.1 |
| TestExecuteIntegration | 2 | 正常流程/错误流程 |
| TestSummarizeResult | 2 | 成功摘要/降级摘要 |
| TestEmptyDimensions | 1 | 空维度结构 |
| TestFallbackResult | 2 | 多论文降级/空论文降级 |

## 相关文件
- `app/agents/analyzer.py` — AnalyzerAgent核心实现
- `prompts/analyzer.txt` — 9块Prompt模板
- `tests/test_analyzer_agent.py` — 42个单元测试
- `app/agents/base.py` — BaseAgent基类（依赖）
- `app/services/prompt_manager.py` — PromptManager（依赖）
- `app/services/llm_service.py` — LLMService（依赖）
