# Task18: 分析Prompt模板升级 + LLM推理集成

## 任务概述

| 项目 | 内容 |
|------|------|
| **版本** | v0.2 |
| **里程碑** | M2 / AM2：RAG检索与3-Agent基础可用 |
| **功能编号** | F3.1.3, F3.3.4 |
| **涉及层级** | python_ai_service |
| **优先级** | P0 |

## 需求描述

增强 `prompts/analyzer.txt` Prompt 模板，将当前初稿版本升级为包含完整5维度结构化JSON Schema、CoT推理链、个性化变量注入、降级兼容说明的生产级 Prompt。

## 影响范围

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 修改 | `Veritas/ai-service/prompts/analyzer.txt` | Prompt模板全面升级 |

## 核心实现要求

### Prompt 8区块结构

```
1. Role Block       — "你是一位资深学术论文审稿人..."
2. Task Block       — 当前分析任务说明
3. Input Block      — $paper_title / $paper_abstract
4. Personalization  — $extra_instruction（可空）
5. CoT Block        — 6步推理链
6. Output Schema    — 严格JSON Schema（嵌套含confidence/references）
7. Constraint Block — 行为边界（禁止臆造/100-200字/confidence标准）
8. Fallback Block   — 信息不足时的降级输出
```

### 5维度JSON Schema升级（snake_case）

```json
{
  "research_problem": {"summary": "...", "confidence": 0.85, "references": ["原文: ..."]},
  "core_method":      {"summary": "...", "confidence": 0.90, "references": ["原文: ..."]},
  "main_experiments": {"summary": "...", "confidence": 0.80, "references": ["原文: ..."]},
  "core_conclusions": {"summary": "...", "confidence": 0.88, "references": ["原文: ..."]},
  "limitations":      {"summary": "...", "confidence": 0.75, "references": ["原文: ..."]}
}
```

### 6步 CoT 推理链

| Step | 名称 | 内容 |
|------|------|------|
| 1 | Skim | 快速浏览摘要，识别论文领域和类型 |
| 2 | Extract_Problem | 提取研究问题，找"本文旨在/针对/解决" |
| 3 | Extract_Method | 提取核心方法（名称+创新点+适用条件） |
| 4 | Extract_Experiments | 提取实验设置（数据集+指标+基线） |
| 5 | Extract_Conclusions | 提取核心结论（区分客观发现与主观推测） |
| 6 | Identify_Limitations | 识别局限性（作者自述+合理推断） |

### 模板变量（string.Template语法）

| 变量 | 来源 | 说明 |
|------|------|------|
| `$paper_title` | AnalyzerAgent.build_analysis_prompt() | 论文标题 |
| `$paper_abstract` | AnalyzerAgent.build_analysis_prompt() | 论文摘要 |
| `$extra_instruction` | AnalyzerAgent._get_extra_instruction() | 个性化指令（可空） |

## 关键对比

| 项目 | 当前版本（v1） | 升级后版本（v2） |
|------|--------------|-----------------|
| 字段命名 | camelCase (researchQuestion) | snake_case (research_problem) |
| 维度结构 | 简单字符串 | 嵌套对象{summary,confidence,references} |
| 推理链 | 无 | 6步CoT |
| 个性化 | 无 | $extra_instruction注入 |
| 降级说明 | 无 | Fallback Block |
| 约束 | 简单3条 | 细化7条含confidence标准 |

## 约束

- 必须使用 string.Template 语法（`$variable`），不用 Jinja2（`{{variable}}`）
- 变量名必须与 AnalyzerAgent 传入参数严格一致
- JSON Schema 字段全 snake_case
- 不修改 prompt_manager.py 或其他文件
- Prompt 中不含硬编码密钥

## 禁止行为

- ❌ 使用 camelCase 字段名
- ❌ 使用 Jinja2 语法替代 string.Template
- ❌ 修改变 prompt_manager.py
- ❌ Prompt 中硬编码密钥
- ❌ 变量名与 AnalyzerAgent 传入参数不一致

## 验证命令

```bash
cd Veritas/ai-service && python -m pytest tests/test_prompt_manager.py -v -k "analyzer"
cd Veritas/ai-service && python -c "
import string
t=open('prompts/analyzer.txt').read()
s=string.Template(t).substitute(paper_title='Test',paper_abstract='Abs',extra_instruction='')
print('Render OK, length:', len(s))
"
```

## 验收标准

- [ ] 8区块结构完整（Role/Task/Input/Personalization/CoT/Output/Constraint/Fallback）
- [ ] 5维度嵌套JSON Schema含summary/confidence/references，全部snake_case
- [ ] 6步CoT推理链完整
- [ ] 变量使用string.Template语法，与AnalyzerAgent参数对齐
- [ ] $extra_instruction为空时正确渲染不产生多余内容
- [ ] 无camelCase字段名，无硬编码密钥
- [ ] 所有测试通过