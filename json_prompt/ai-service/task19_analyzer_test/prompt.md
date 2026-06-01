# Task19: AnalyzerAgent 单元测试 + JSON解析优化

## 任务概述

| 项目 | 内容 |
|------|------|
| **版本** | v0.2 |
| **里程碑** | M2 / AM2：RAG检索与3-Agent基础可用 |
| **功能编号** | F3.1.3 |
| **涉及层级** | python_ai_service |
| **优先级** | P0 |

## 需求描述

编写 AnalyzerAgent 的完整单元测试套件，产出 `tests/test_analyzer_agent.py`。测试覆盖正常分析流程、JSON解析鲁棒性、LLM降级路径、维度验证逻辑和confidence计算正确性。

## 影响范围

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `Veritas/ai-service/tests/test_analyzer_agent.py` | 15+个测试用例的完整测试套件 |

## 核心测试覆盖

### 测试分类与用例数

| 测试类 | 用例数 | 覆盖场景 |
|--------|--------|---------|
| TestAnalyzerAgentInit | 3 | 继承/名称/超时 |
| TestBuildPrompt | 2 | Prompt构建/个性化注入 |
| TestGetExtraInstruction | 6 | 4种knowledge_level + None + 缺失 |
| TestRunSuccessFlow | 3 | 正常3论文/进度更新/结果结构 |
| TestRunDegradation | 3 | 单篇失败/全部失败/空输入 |
| TestParseAnalysisResult | 5 | 纯JSON/code block/plain block/无效/空 |
| TestValidateDimensions | 5 | 缺失补全/clamp上限/clamp下限/None/免责声明 |
| TestRuleBasedExtraction | 3 | 完整5维度/confidence值/extraction_quality |
| TestExecuteIntegration | 2 | BaseAgent.execute正常/异常 |

### JSON解析鲁棒性测试

验证 `_parse_analysis_result` 正确处理以下输入：

```
✅ 纯JSON: {"research_problem": {"summary": "...", ...}}
✅ Markdown代码块: ```json\n{...}\n```
✅ 普通代码块: ```\n{...}\n```
✅ 无效输出: "这是一篇关于AI的论文..."
✅ 空字符串: ""
```

### 降级路径测试

```
论文1(成功) → 论文2(LLM异常) → 论文3(成功)
                     ↓
              降级为rule_based_extraction
              confidence=0.3, extraction_quality=0.1
```

### 测试常量定义

```python
SAMPLE_PAPERS = [
    {"paper_id": "arxiv_001", "title": "Multi-Agent Systems", "abstract": "A survey..."},
    {"paper_id": "arxiv_002", "title": "LangGraph Framework", "abstract": "We propose..."},
    {"paper_id": "arxiv_003", "title": "RL for Agents", "abstract": "Reinforcement..."},
]

VALID_ANALYSIS_JSON = json.dumps({...})  # 标准5维度
PARTIAL_ANALYSIS_JSON = json.dumps({...})  # 缺limitations
MALFORMED_OUTPUT = "This is a paper about AI agents..."
```

## 参考模式

参考 `tests/test_retriever_agent.py` 的代码风格：
- `_make_mock_services()` 辅助函数
- `AsyncMock` 模拟异步LLM调用
- `MagicMock` 模拟prompt_manager
- 测试类按功能分组
- 每个测试方法名格式：`test_xxx_your_description`

## 约束

- 所有测试不依赖真实I/O（无LLM调用/ChromaDB连接）
- 测试风格与 test_retriever_agent.py 一致
- JSON字段全部snake_case
- 不修改analyzer.py等源代码（发现bug报告而非直接修改）
- 每个测试函数必须有明确的assert断言

## 禁止行为

- ❌ 修改源代码文件
- ❌ 使用 time.sleep 等待
- ❌ 导入真实LLM模型或数据库连接
- ❌ 跳过降级/异常场景测试
- ❌ JSON字段使用camelCase

## 验证命令

```bash
cd Veritas/ai-service && python -m pytest tests/test_analyzer_agent.py -v
cd Veritas/ai-service && python -m pytest tests/test_analyzer_agent.py --tb=short -q
```

## 验收标准

- [ ] 15+个测试用例覆盖正常/异常/边界/降级4类场景
- [ ] JSON解析测试覆盖4种格式（纯JSON/code block/plain block/无效）
- [ ] 降级测试覆盖3种场景（单篇失败继续/全部失败/空输入）
- [ ] 维度验证覆盖缺失补全+confidence clamp(None/>1/<0)+disclaimer
- [ ] 风格与 test_retriever_agent.py 一致
- [ ] 所有测试不使用实际I/O
- [ ] 所有15+个pytest测试通过