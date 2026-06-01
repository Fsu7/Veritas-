# GeneratorAgent 与个性化引擎

## 功能描述
- 解决了科研文献综述自动生成问题：基于 AnalyzerAgent 的5维度分析结果和 ComparerAgent 的对比数据，自动生成结构化的个性化文献综述
- 实现了4维度用户画像驱动的个性化Prompt注入：学历层次/知识水平/偏好风格/研究方向 → Prompt个性化片段
- 创建了 PersonalizationService 通用个性化服务：为 Analyzer/Generator 等多个Agent提供个性化指令生成能力
- 业务价值：综述生成是系统核心输出，个性化引擎确保不同用户（本科生→教授）获得适配其水平的综述内容，是项目四大创新点之一

## 实现逻辑

### 修改的核心文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/agents/generator.py` | 创建 | GeneratorAgent 核心逻辑，~620行 |
| `app/services/personalization_service.py` | 创建 | PersonalizationService 个性化引擎，~260行 |
| `prompts/generator.txt` | 升级 | 8区块结构+4步CoT+JSON Schema |
| `app/agents/__init__.py` | 修改 | 导出 GeneratorAgent |
| `app/services/__init__.py` | 修改 | 导出 PersonalizationService |
| `tests/test_generator_agent.py` | 创建 | 19个测试用例 |
| `tests/test_personalization_service.py` | 创建 | 14个测试用例 |

### 使用的算法或设计模式

1. **BaseAgent继承模式**：GeneratorAgent extends BaseAgent，实现 `execute()` → `_run()` → `build_prompt()` 标准流程
2. **三级降级策略**：LLM失败→fallback报告 / PersonalizationService异常→内置映射 / citation提取失败→空列表
3. **4维度画像映射**：education_level/knowledge_level/preferred_style/research_field → 结构化Prompt片段
4. **Cache-Aside个性化**：优先使用PersonalizationService，异常时回退到Agent内置映射表
5. **camelCase/snake_case兼容**：`_normalize_profile()` 统一处理JSON camelCase输入

### 关键代码逻辑说明

**GeneratorAgent._run() 流程**：
```
progress 0.2 → build_prompt（个性化+数据注入）
progress 0.4 → LLM生成综述
progress 0.7 → 引用提取 + 报告验证 + 术语密度计算
progress 1.0 → 返回完整结果（report/citation_list/term_density_actual/personalization_applied）
```

**PersonalizationService 核心方法**：
- `get_personalization_block()` → 4维度→结构化Prompt片段（【学历适配】【术语密度目标】【写作风格】【领域侧重】）
- `get_extra_instruction()` → Agent特定额外指令（analyzer侧重分析深度/generator侧重写作风格）
- `build_generation_prompt()` → 完整Prompt组装（模板+数据+个性化+画像摘要）

**generator.txt 8区块结构**：
1. Role Block — 科研综述撰写专家身份
2. Task Block — 综述生成任务说明
3. Input Block — $user_profile_summary / $analysis_data / $comparison_data
4. Personalization Block — $personalization 4维度适配
5. CoT Block — Outline→Draft→Personalize→Self-Check 4步推理链
6. Output Schema Block — 严格JSON（report/citation_list/term_density_actual/personalization_applied）
7. Constraint Block — 引用格式/信息源/矛盾呈现/术语密度/风格/字数/AI声明/格式
8. Fallback Block — 降级兼容说明

## 接口变更

### Request（GeneratorAgent 输入）

```json
{
  "analysis_results": [
    {
      "paper_id": "paper_1",
      "paper_title": "Attention Is All You Need",
      "research_problem": {"summary": "序列建模问题", "confidence": 0.9},
      "core_method": {"summary": "Transformer架构", "confidence": 0.95},
      "main_experiments": {"summary": "WMT翻译任务", "confidence": 0.85},
      "core_conclusions": {"summary": "自注意力机制有效", "confidence": 0.9},
      "limitations": {"summary": "计算复杂度高", "confidence": 0.7}
    }
  ],
  "compare_result": {
    "summary": "Transformer与RNN的方法对比",
    "contradictions": []
  }
}
```

### Context（用户画像）

```json
{
  "user_profile": {
    "education_level": "master",
    "knowledge_level": "intermediate",
    "preferred_style": "balanced",
    "research_field": "NLP"
  }
}
```

### Response（GeneratorAgent 输出）

```json
{
  "report": "## 1 引言\n\n综述内容...\n\n⚠️ 本内容由 AI 生成，仅供参考",
  "citation_list": [
    {"id": 1, "authors": "Vaswani et al.", "year": 2017, "title": "Attention Is All You Need", "venue": "NeurIPS"}
  ],
  "term_density_actual": 0.22,
  "personalization_applied": {
    "education_adaptation": "侧重方法论对比和实验设计分析，关注技术细节",
    "term_density_target": 0.20,
    "style_guide": "standard"
  }
}
```

### PersonalizationService 接口

```python
service = PersonalizationService(prompt_manager=pm)

# 生成个性化Prompt片段
block = service.get_personalization_block(user_profile)
# → "【学历适配】侧重方法论对比...\n【术语密度目标】20%\n【写作风格】标准学术...\n【领域侧重】侧重自然语言处理..."

# Agent特定额外指令
instruction = service.get_extra_instruction(user_profile, agent_name="analyzer")
# → "请使用标准学术语言，适当引入术语定义...侧重方法论对比和实验设计分析。"

# 完整Prompt组装
prompt = service.build_generation_prompt(analysis_results, comparison_result, user_profile)
# → 完整渲染后的Prompt字符串
```

## 测试结果

- **test_generator_agent.py**：19/19 ✅ 通过
  - 继承验证、Prompt渲染、个性化块构建（有/无画像/服务异常）
  - _run完整流程（成功/LLM失败/空数据）
  - 引用提取（Author-Year/数字编号/无匹配）
  - 报告验证（完整/缺失章节）
  - 术语密度计算、fallback报告、AI声明、结果摘要
- **test_personalization_service.py**：14/14 ✅ 通过
  - generator.txt 8区块结构验证
  - 模板变量渲染（4变量正确替换/空personalization）
  - JSON Schema 4字段验证
  - CoT 4步推理链验证
  - get_personalization_block 多画像测试
  - get_extra_instruction analyzer/generator区分
  - build_generation_prompt 完整组装
  - 未知枚举值默认值
  - camelCase输入兼容
  - prompt_manager=None降级
  - 4个辅助方法返回值
  - 3个标签方法中文标签
  - PromptManager集成渲染
- **模板渲染验证**：`string.Template.substitute()` 4变量正确替换，输出长度3558字符
- **是否通过**：是

## 相关文件

### 代码文件
- `Veritas/ai-service/app/agents/generator.py` — GeneratorAgent核心实现
- `Veritas/ai-service/app/services/personalization_service.py` — PersonalizationService个性化引擎
- `Veritas/ai-service/prompts/generator.txt` — Generator Prompt模板（8区块）
- `Veritas/ai-service/app/agents/__init__.py` — Agent模块导出
- `Veritas/ai-service/app/services/__init__.py` — Service模块导出

### 测试文件
- `Veritas/ai-service/tests/test_generator_agent.py` — 19个GeneratorAgent测试
- `Veritas/ai-service/tests/test_personalization_service.py` — 14个PersonalizationService测试

### 任务定义
- `json_prompt/ai-service/task20_generator_agent_core/prompt.json` — Task20任务定义
- `json_prompt/ai-service/task21_generator_prompt_personalization/prompt.json` — Task21任务定义
