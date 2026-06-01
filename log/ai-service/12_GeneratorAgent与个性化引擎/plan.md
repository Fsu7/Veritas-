# Task21 实施计划：PersonalizationService 创建 + generator.py 更新

## 当前状态

- ✅ Task20 已完成：`agents/generator.py` 创建、`__init__.py` 更新、19个测试通过
- ✅ Task21 Step4 已完成：`prompts/generator.txt` 升级为8区块结构
- ⬜ Task21 Step5：创建 `services/personalization_service.py`
- ⬜ Task21 Step6：创建 `tests/test_personalization_service.py`
- ⬜ 更新 `generator.py` 的 `build_prompt()` 传递 `$user_profile_summary`
- ⬜ 更新 `services/__init__.py` 导出 PersonalizationService
- ⬜ 运行 pytest 验证所有测试通过

---

## Step 1：创建 `services/personalization_service.py`

### 1.1 类结构与映射表

```python
class PersonalizationService:
    DIFFICULTY_MAP  # 4级: beginner→1, intermediate→2, advanced→3, expert→4
    STYLE_MAP      # 3级: simple→casual, balanced→standard, technical→formal
    EDUCATION_ADAPTATION  # 4级: undergraduate/master/phd/faculty → Prompt片段
    FIELD_EMPHASIS  # 研究方向→侧重文本
    TERM_DENSITY_TARGET  # knowledge_level→float目标值
```

**5个映射表详细定义**（对齐 AGENTS.md Section 4 + generator.py 已有常量）：

| 映射表 | 键 | 值 |
|--------|-----|-----|
| `DIFFICULTY_MAP` | beginner/intermediate/advanced/expert | 1/2/3/4 |
| `STYLE_MAP` | simple/balanced/technical | {tone, paragraph, structure} dict |
| `EDUCATION_ADAPTATION` | undergraduate/master/phd/faculty | Prompt片段字符串 |
| `FIELD_EMPHASIS` | NLP/CV/RL/多模态/... | 侧重文本字符串 |
| `TERM_DENSITY_TARGET` | beginner/intermediate/advanced/expert | 0.05/0.20/0.40/0.50 |

**注意**：`STYLE_MAP` 在 generator.py 中是简单映射 `simple→casual`，但 task21 FR-007 要求每级含 `tone/paragraph/structure`。PersonalizationService 的 STYLE_MAP 需要更丰富的结构，同时保持与 generator.py 的兼容。

### 1.2 公共方法

| 方法 | 签名 | 返回 | 说明 |
|------|------|------|------|
| `__init__` | `(prompt_manager=None)` | — | 可选注入 PromptManager |
| `get_personalization_block` | `(user_profile: dict) -> str` | 结构化Prompt片段 | 4维度→个性化指令 |
| `get_extra_instruction` | `(user_profile: dict, agent_name: str='') -> str` | 简洁指令字符串 | Agent特定额外指令 |
| `build_generation_prompt` | `(analysis_results, comparison_result, user_profile) -> str` | 完整Prompt | 组装模板+数据+个性化 |
| `get_education_adaptation` | `(education_level: str) -> str` | Prompt片段 | 学历适配 |
| `get_term_density_target` | `(knowledge_level: str) -> float` | float | 术语密度目标 |
| `get_style_guide` | `(preferred_style: str) -> str` | 风格指南字符串 | 写作风格 |
| `get_field_emphasis` | `(research_field: str) -> str` | 侧重字符串 | 领域侧重 |

### 1.3 内部方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `_normalize_profile` | `(user_profile: dict) -> dict` | camelCase→snake_case |
| `_education_label` | `(level: str) -> str` | undergraduate→本科 等 |
| `_knowledge_label` | `(level: str) -> str` | beginner→入门 等 |
| `_style_label` | `(style: str) -> str` | simple→通俗 等 |
| `_build_user_profile_summary` | `(user_profile: dict) -> str` | 生成画像摘要字符串 |

### 1.4 关键设计决策

1. **所有公共方法不抛异常**：未知枚举值使用默认值
2. **默认值**：education_level→master, knowledge_level→intermediate, preferred_style→balanced, research_field→""
3. **camelCase兼容**：`_normalize_profile()` 转换 camelCase 键名
4. **build_generation_prompt 降级**：prompt_manager=None 时直接读文件 + string.Template
5. **日志安全**：仅记录方法调用和异常，不记录 user_profile 内容
6. **分层约束**：services 层不导入 agents 层

### 1.5 `get_personalization_block()` 输出格式

```
【学历适配】{education_adaptation}
【术语密度目标】{term_density_target_percentage}%
【写作风格】{style_tone}；段落风格：{style_paragraph}；结构要求：{style_structure}
【领域侧重】{field_emphasis}
```

### 1.6 `get_extra_instruction()` 输出逻辑

- `agent_name='analyzer'`：侧重分析深度和术语使用
- `agent_name='generator'`：侧重写作风格和解释方式
- 其他/空：通用个性化指令

### 1.7 `build_generation_prompt()` 流程

```
1. 调用 get_personalization_block(user_profile) → personalization
2. json.dumps(analysis_results) → analysis_data
3. json.dumps(comparison_result) or "无" → comparison_data
4. 调用 _build_user_profile_summary(user_profile) → user_profile_summary
5. prompt_manager.get_prompt('generator', personalization=..., analysis_data=..., comparison_data=..., user_profile_summary=...)
   或 降级: Template(file_content).safe_substitute(...)
6. 返回完整 Prompt 字符串
```

---

## Step 2：更新 `agents/generator.py` 的 `build_prompt()`

当前 `build_prompt()` 只传递3个变量（personalization, analysis_data, comparison_data），需要增加第4个变量 `user_profile_summary`。

**修改点**：
- `build_prompt()` 方法中，生成 `user_profile_summary` 并传递给 `prompt_manager.get_prompt()`
- 如果 `personalization_service` 可用，调用 `personalization_service._build_user_profile_summary()` 或自行生成摘要
- 如果 `personalization_service` 不可用，使用内置逻辑生成摘要

**摘要格式**：`{education_label}/{research_field}方向/{knowledge_label}知识水平/{style_label}风格`
示例：`硕士/NLP方向/中级知识水平/均衡风格`

---

## Step 3：更新 `services/__init__.py`

当前为空文件，添加 PersonalizationService 导出。

---

## Step 4：创建 `tests/test_personalization_service.py`

14个测试用例（对齐 task21 prompt.json test_requirements）：

| # | 测试名 | 覆盖 |
|---|--------|------|
| 1 | `test_generator_prompt_structure` | generator.txt 包含8区块 |
| 2 | `test_generator_prompt_variable_rendering` | 4变量正确替换 |
| 3 | `test_generator_prompt_empty_personalization` | $personalization为空时正常渲染 |
| 4 | `test_generator_prompt_json_schema` | JSON Schema含4字段 |
| 5 | `test_generator_prompt_cot_steps` | 4步CoT推理链 |
| 6 | `test_get_personalization_block` | 不同profile→正确片段 |
| 7 | `test_get_extra_instruction` | analyzer/generator不同指令 |
| 8 | `test_build_generation_prompt` | 完整Prompt组装 |
| 9 | `test_unknown_enum_defaults` | 未知枚举值→默认值 |
| 10 | `test_camelcase_input` | camelCase键名兼容 |
| 11 | `test_no_prompt_manager` | prompt_manager=None降级 |
| 12 | `test_helper_methods` | 4个辅助方法返回值 |
| 13 | `test_label_methods` | 3个标签方法中文标签 |
| 14 | `test_prompt_manager_integration` | PromptManager集成渲染 |

---

## Step 5：运行 pytest 验证

```bash
cd Veritas/ai-service && python3 -m pytest tests/test_personalization_service.py tests/test_generator_agent.py -v
```

同时验证模板渲染：
```bash
cd Veritas/ai-service && python3 -c "import string; t=open('prompts/generator.txt').read(); s=string.Template(t).substitute(personalization='test',analysis_data='[]',comparison_data='',user_profile_summary='test'); print('Render OK, length:', len(s))"
```

---

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| **创建** | `app/services/personalization_service.py` | PersonalizationService 完整实现 |
| **修改** | `app/agents/generator.py` | `build_prompt()` 增加 `user_profile_summary` |
| **修改** | `app/services/__init__.py` | 导出 PersonalizationService |
| **创建** | `tests/test_personalization_service.py` | 14个测试用例 |

---

## 禁止事项（对齐 task21 forbidden_actions）

- ❌ 不使用 Jinja2 语法（`{{variable}}`），只用 `$variable`
- ❌ 不修改 `prompt_manager.py`
- ❌ 不修改 `analyzer.py` 或其他 Agent 文件
- ❌ 不硬编码 API Key/密码
- ❌ PersonalizationService 公共方法不抛异常
- ❌ 不在日志中记录 user_profile 完整内容
- ❌ 模板变量名必须与 PromptManager kwargs 一致
- ❌ services 层不导入 agents 层
