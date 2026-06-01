# 技术教学文档

## 开发思路

### 需求分析过程
AnalyzerAgent是6-Agent工作流中的第三环，承接RetrieverAgent的检索结果，为ComparerAgent和GeneratorAgent提供结构化输入。核心需求：
1. 从论文标题+摘要中提取5个维度：research_problem / core_method / main_experiments / core_conclusions / limitations
2. 每个维度需包含嵌套结构：summary（中文摘要）+ confidence（0.0-1.0置信度）+ references（原文引用列表）
3. LLM输出不可靠时需降级到规则提取
4. 根据用户画像（knowledge_level + education_level）个性化分析指令
5. 所有AI生成内容必须标注声明

### 技术选型考虑
- **JSON解析多策略**：LLM输出格式不稳定（可能包裹在代码块、混合文本中），需要4级解析策略逐级降级
- **规则提取兜底**：当LLM完全失败时，基于论文标题和摘要前300字的简单规则提取，保证下游Agent总能获得结构化数据
- **confidence统一默认值0.3**：缺失维度和非数字confidence统一为0.3（而非0.0或0.5），因为0.0暗示完全不可信（过于悲观），0.5暗示一半可信（过于乐观），0.3表示"信息不足但非零"
- **extraction_quality双轨计算**：LLM成功时=所有维度confidence均值；规则提取时单论文=0.1，全局=均值

### 架构设计思路
```
AnalyzerAgent
├── execute() [BaseAgent] — 超时控制 + 异常兜底
│   └── _run() — 遍历papers，逐篇分析
│       └── _analyze_single_paper() — 单篇分析流程
│           ├── build_prompt() — 构建个性化Prompt
│           ├── llm.generate() — 调用LLM
│           ├── _parse_analysis_result() — 4策略JSON解析
│           └── _validate_dimensions() — 维度校验+补全
├── _rule_based_extraction() — 规则提取兜底
├── _get_extra_instruction() — 个性化指令映射
└── _fallback_result() — Agent级降级结果
```

### 遇到的问题及解决方案

**问题1：LLM输出JSON格式不稳定**
- 现象：LLM可能返回纯JSON、```json```代码块、```plain```代码块、或文本包裹的JSON
- 解决：4策略逐级解析（纯JSON → json代码块 → plain代码块 → 花括号提取），全部失败时降级到规则提取

**问题2：extraction_quality语义冲突**
- 现象：规则提取中extraction_quality=0.1（表示低质量），但_run()计算全局extraction_quality为confidence均值（0.3），两者语义不同
- 解决：单论文规则提取结果中extraction_quality=0.1作为元数据标记；全局extraction_quality始终为均值计算，保持语义一致

**问题3：_parse_analysis_result签名兼容性**
- 现象：原签名`(self, llm_output)`无法在解析失败时触发规则提取（缺少paper信息）
- 解决：增加可选参数`paper: dict = None`，解析失败时若有paper则调用`_rule_based_extraction(paper)`，否则返回`_empty_dimensions()`

## 实现步骤

1. **Gap分析**：对照Task17/18/19三个prompt.json，逐项比对现有代码，识别22个差距（G1-G22）
2. **Task17核心逻辑**：修改analyzer.py，修复12个核心差距（ai_disclaimer、analysis_id、extraction_quality、confidence默认值、规则提取统一confidence等）
3. **Task18 Prompt模板**：增强analyzer.txt，添加ai_disclaimer字段到JSON Schema示例，添加第9块AI内容声明
4. **Task19单元测试**：重写test_analyzer_agent.py，扩展SAMPLE_PAPERS到3篇，新增PARTIAL_ANALYSIS_JSON和MALFORMED_OUTPUT常量，42个测试方法覆盖12个测试类
5. **Phase4全局验证**：运行测试发现1个断言错误（extraction_quality期望0.1实际0.3），修正后全部通过

## 解决了什么问题

### 核心问题描述
论文深度分析需要从非结构化的标题+摘要中提取5个维度的结构化信息，同时应对LLM输出不稳定、用户画像个性化、降级兜底等挑战。

### 解决方案对比
| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| 单策略JSON解析 | 简单 | LLM输出格式不稳定时大量失败 | ❌ |
| 4策略JSON解析+规则兜底 | 鲁棒性高 | 代码复杂度增加 | ✅ |
| 固定confidence默认值 | 一致 | 不够灵活 | ✅（0.3） |
| 动态confidence评估 | 精确 | 实现复杂，可能不准确 | ❌ |

### 最终方案的优势
1. **鲁棒性**：4策略JSON解析+规则兜底，确保任何情况下都能返回结构化数据
2. **一致性**：confidence默认值统一0.3，extraction_quality全局均值计算
3. **可追溯**：每个分析结果包含analysis_id和ai_disclaimer
4. **个性化**：根据knowledge_level和education_level动态调整分析指令

## 变更内容

### 新增文件
- 无新增文件（analyzer.py和analyzer.txt为已有文件修改）

### 修改文件
- `app/agents/analyzer.py`
  - 新增 `import uuid`
  - `_validate_dimensions()`: None维度confidence 0.0→0.3；非数字confidence 0.5→0.3；新增analysis_id=uuid4()；disclaimer→ai_disclaimer
  - `_parse_analysis_result()`: 签名增加`paper: dict = None`；解析失败时若有paper则调用_rule_based_extraction(paper)
  - `_run()`: 新增extraction_quality全局计算（所有维度confidence均值）
  - `_rule_based_extraction()`: 所有维度confidence统一0.3；extraction_quality改为float 0.1；disclaimer→ai_disclaimer
  - `_get_extra_instruction()`: knowledge_level为None时返回""；更新指令关键词（beginner→通俗解释、intermediate→方法对比、advanced→研究空白、expert→前沿洞察）
  - `_fallback_result()`: 新增extraction_quality=0.1

- `prompts/analyzer.txt`
  - Output Schema Block: 新增`"ai_disclaimer": "⚠️ 本分析由 AI 生成，仅供参考"`字段
  - 新增Section (9) AI Content Declaration块

- `tests/test_analyzer_agent.py`
  - 完全重写：SAMPLE_PAPERS扩展到3篇；新增PARTIAL_ANALYSIS_JSON和MALFORMED_OUTPUT常量
  - 所有disclaimer断言→ai_disclaimer；新增extraction_quality和analysis_id断言
  - 12个测试类42个测试方法

### 配置变更
- 无配置变更

## 关键技术点

### 1. JSON解析4策略
```python
# 策略1: 纯JSON
json.loads(cleaned)
# 策略2: ```json``` 代码块
re.search(r"```json\s*(.*?)\s*```", cleaned, re.DOTALL)
# 策略3: ```plain``` 代码块
re.search(r"```\s*(.*?)\s*```", cleaned, re.DOTALL)
# 策略4: 花括号提取
cleaned.find("{") / cleaned.rfind("}")
```

### 2. 维度校验三重防御
- None维度 → `{summary: FALLBACK_NOTE, confidence: 0.3, references: []}`
- 字符串维度 → `{summary: 原文, confidence: 0.5, references: []}`
- 字典维度 → 校验summary非空、confidence数值clamp、references列表化

### 3. Prompt模板9块结构
1. Role Block — 身份定义
2. Task Block — 任务说明
3. Input Block — $paper_title + $paper_abstract
4. Personalization Block — $extra_instruction
5. Chain-of-Thought Block — 6步推理链（Skim→Extract Problem→Extract Method→Extract Experiments→Extract Conclusions→Identify Limitations）
6. Output Schema Block — 嵌套JSON Schema + ai_disclaimer
7. Constraint Block — 7条行为约束
8. Fallback Block — 降级兼容规则
9. AI Content Declaration — AI内容声明

### 4. 个性化指令映射
```
knowledge_level:
  beginner   → 通俗解释和类比说明，避免过多专业术语
  intermediate → 标准学术语言，方法对比和实现细节
  advanced    → 专业学术语言，研究空白和技术细节
  expert      → 高度专业学术语言，前沿洞察和创新建议

education_level:
  undergraduate → 补充背景知识
  master        → 方法论对比和实验设计分析
  phd           → 研究创新点和前沿贡献
  faculty       → 教学适用性和学科知识体系构建
```

## 经验总结

### 开发过程中的收获
1. **Gap分析先行**：在编码前先做22项Gap分析（G1-G22），确保不遗漏任何需求点，避免反复修改
2. **签名兼容性设计**：`_parse_analysis_result(llm_output, paper=None)`通过可选参数保持向后兼容，同时启用规则提取兜底
3. **测试驱动修复**：Phase4验证发现extraction_quality断言错误，说明对"全局均值 vs 单论文标记"的语义理解需要更精确

### 踩过的坑及如何避免
1. **extraction_quality语义混淆**：规则提取中单论文extraction_quality=0.1是元数据标记，而_run()计算的全局extraction_quality是confidence均值。测试中期望全局值=0.1实际=0.3。**避免方法**：区分"单论文元数据"和"全局聚合指标"的语义
2. **f-string花括号错误**：`f"Analyzed {total} papers ({degraded degraded to rule-based)"`缺少闭合花括号。**避免方法**：f-string中变量后紧跟文字时注意花括号闭合
3. **python vs python3**：sandbox环境中`python`命令不存在，必须用`python3`。**避免方法**：始终使用`python3 -m pytest`

### 最佳实践建议
1. **LLM输出解析**：永远不要假设LLM输出格式稳定，至少实现3级解析策略+1级规则兜底
2. **confidence默认值**：缺失/无效confidence统一为0.3（非0.0非0.5），平衡悲观与乐观
3. **AI声明字段**：所有AI生成内容必须包含`ai_disclaimer`字段，且字段名统一（不用`disclaimer`）
4. **UUID生成**：每个分析结果生成唯一analysis_id，便于下游溯源和去重
5. **测试覆盖降级路径**：不仅要测试正常流程，更要覆盖LLM失败、JSON解析失败、空输入等降级场景
