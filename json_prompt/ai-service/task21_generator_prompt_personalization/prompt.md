# Task 21: Generator Prompt模板升级 + PersonalizationService个性化注入

## 项目上下文

| 项目 | 内容 |
|------|------|
| **课题编号** | XH-202630 |
| **课题名称** | 领域知识个性化生成与多智能体协同决策系统研究 |
| **版本** | v0.2 |
| **里程碑** | M2 / AM2：RAG检索与3-Agent基础可用 |
| **任务编号** | 21 |
| **前置任务** | task20_generator_agent_core |
| **需求编号** | F3.4.1, F3.4.2, F3.4.3, F3.4.4 |

## 需求概述

升级 Generator Agent Prompt模板（`prompts/generator.txt`），实现4维度用户画像→个性化Prompt片段注入的PersonalizationService（`app/services/personalization_service.py`）。当前generator.txt为初稿版本，缺少CoT推理链、个性化适配变量注入、严格JSON输出Schema。需升级为生产级Prompt模板，并创建PersonalizationService为Analyzer/Generator等Agent提供个性化指令生成能力。

## 当前架构

### 涉及层级

- Python AI服务层

### 相关模块

| 模块路径 | 说明 |
|---------|------|
| `prompts/generator.txt` | 生成Agent Prompt模板（初稿），需升级 |
| `app/services/personalization_service.py` | 个性化服务（待创建） |
| `app/agents/analyzer.py` | AnalyzerAgent，已预留personalization_service集成接口 |
| `app/services/prompt_manager.py` | PromptManager，使用string.Template渲染 |
| `app/models/schemas.py` | UserProfile模型，4维度字段定义 |

### 现有实现

| 文件 | 说明 | 复用类型 |
|------|------|---------|
| `prompts/generator.txt` | 当前初稿：基本综述结构，$personalization/$analysis_data/$comparison_data变量 | **修改** |
| `prompts/analyzer.txt` | 已升级的8区块结构模板 | 参考 |
| `app/agents/analyzer.py` | `_get_extra_instruction()`已预留personalization_service接口 | 参考 |
| `app/services/prompt_manager.py` | `get_prompt()`使用string.Template.safe_substitute() | 参考 |
| `app/models/schemas.py` | UserProfile：education_level/research_field/knowledge_level/preferred_style | 参考 |

## 交付文件

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| **MODIFY** | `Veritas/ai-service/prompts/generator.txt` | 升级Generator Prompt模板：8区块结构+CoT+个性化注入+JSON Schema |
| **CREATE** | `Veritas/ai-service/app/services/personalization_service.py` | 创建PersonalizationService：4维度画像→个性化Prompt片段 |

---

## 一、prompts/generator.txt 升级要求

### 1.1 八区块结构

模板必须包含以下8个区块：

```
(1) Role Block — 科研综述写作专家身份定义
(2) Task Block — 综述生成任务说明
(3) Input Block — 分析数据/对比数据/用户画像摘要
(4) Personalization Block — 4维度个性化适配指令注入
(5) CoT Block — 4步推理链
(6) Output Schema Block — 严格JSON Schema定义
(7) Constraint Block — 行为边界
(8) Fallback Block — 降级兼容说明
```

### 1.2 模板变量（$variable语法，string.Template兼容）

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `$personalization` | string | 个性化适配指令块，由PersonalizationService.get_personalization_block()生成 |
| `$analysis_data` | string (JSON) | 论文分析结果JSON字符串，由AnalyzerAgent产出 |
| `$comparison_data` | string (JSON) | 对比分析结果JSON字符串，可为空字符串 |
| `$user_profile_summary` | string | 用户画像简要描述 |

### 1.3 CoT推理链（4步）

| 步骤 | 名称 | 说明 |
|------|------|------|
| Step 1 | **Outline** | 根据分析数据生成综述大纲：引言/方法综述/方法对比/矛盾分析/结论与展望 |
| Step 2 | **Draft** | 按大纲逐节撰写，每个观点标注引用[N] Author et al., Year |
| Step 3 | **Personalize** | 检查术语密度、写作风格、解释深度是否匹配用户画像 |
| Step 4 | **Self-Check** | 验证：所有论文覆盖？引用完整？术语密度达标？风格匹配？AI声明包含？ |

### 1.4 Output JSON Schema

```json
{
    "report": "Markdown格式综述全文（2000-3000字，末尾含'AI生成，仅供参考'）",
    "citation_list": [
        {
            "id": 1,
            "authors": "Author et al.",
            "year": 2024,
            "title": "论文标题",
            "venue": "发表会议/期刊"
        }
    ],
    "term_density_actual": 0.22,
    "personalization_applied": {
        "education_level": "master",
        "knowledge_level": "intermediate",
        "preferred_style": "balanced",
        "research_field": "NLP"
    }
}
```

### 1.5 引用格式

- 正文引用格式：`[N]`（数字编号）
- citation_list每条包含：id / authors / year / title / venue
- 多作者格式：`Author et al.`
- 每个观点必须标注引用来源

### 1.6 Constraint Block

1. 每个观点必须引用具体论文 `[N]`
2. 内容基于提供数据不可编造
3. 矛盾观点客观呈现不偏袒
4. 术语密度匹配用户画像目标
5. 写作风格匹配 preferred_style
6. 字数 2000-3000 字
7. 综述末尾标注"AI生成，仅供参考"
8. report 为 Markdown 格式

### 1.7 Fallback Block

- analysis_data 为空时：输出提示"暂无论文分析数据，无法生成综述"
- comparison_data 为空时：跳过对比/矛盾分析章节
- 始终输出完整 JSON 结构，不因数据不足而拒绝输出

---

## 二、PersonalizationService 实现要求

### 2.1 类定义

```python
class PersonalizationService:
    def __init__(self, prompt_manager=None):
        ...
```

### 2.2 映射表定义

#### DIFFICULTY_MAP（4级）

| knowledge_level | term_density | strategy | example_type | avoid |
|----------------|-------------|----------|-------------|-------|
| beginner | <5% | 通俗解释+类比+入门路线 | 生活化类比、图示说明 | 专业术语堆砌、数学公式 |
| intermediate | ~20% | 标准描述+示例+方法对比 | 代码片段、流程图 | 过度简化、缺少细节 |
| advanced | ~40% | 专业术语+深入分析+研究空白 | 算法伪代码、实验对比 | 基础概念解释过多 |
| expert | >50% | 前沿洞察+创新建议+技术细节 | 最新论文引用、理论推导 | 入门级解释 |

#### STYLE_MAP（3级）

| preferred_style | tone | paragraph | structure |
|----------------|------|-----------|-----------|
| simple | 日常用语+比喻 | 简短段落(3-5句) | 要点式 |
| balanced | 标准学术表达 | 适度展开 | 总分总 |
| technical | 正式学术+引用 | 深入论证 | IMRAD |

#### EDUCATION_ADAPTATION（4级）

| education_level | Prompt片段 |
|----------------|-----------|
| undergraduate | 请使用通俗易懂的语言，配合生活化类比解释复杂概念。适当补充背景知识，帮助建立知识体系。 |
| master | 请对比不同方法的优劣，提供代码实现参考和伪代码。侧重方法论对比和实验设计分析。 |
| phd | 请聚焦前沿研究，分析创新点和改进方向。关注研究创新点和前沿贡献，分析可扩展的研究方向。 |
| faculty | 请构建知识体系框架，提供教学案例和课程设计建议。关注教学适用性和学科知识体系构建。 |

#### FIELD_EMPHASIS

| research_field | 侧重文本 |
|---------------|---------|
| NLP | 重点关注自然语言处理相关的技术方案和应用场景 |
| CV | 重点关注计算机视觉相关的视觉特征提取和图像处理技术 |
| RL | 重点关注强化学习相关的策略优化和奖励机制设计 |
| 多模态 | 重点关注多模态融合与跨模态对齐技术 |
| 知识图谱 | 重点关注知识表示与推理相关技术 |
| 推荐系统 | 重点关注个性化推荐与协同过滤技术 |
| 默认(空/未知) | 均衡关注各研究方向 |

#### TERM_DENSITY_TARGET

| knowledge_level | 目标值 |
|----------------|-------|
| beginner | 0.05 |
| intermediate | 0.20 |
| advanced | 0.40 |
| expert | 0.55 |

### 2.3 公共方法

#### `get_personalization_block(user_profile: dict) -> str`

根据用户画像4维度生成结构化个性化Prompt片段，格式：

```
【个性化适配要求】
- 学历适配：{education_adaptation}
- 术语密度目标：{term_density_target}%（{knowledge_label}水平）
- 写作风格：{style_guide}（{style_label}风格）
- 领域侧重：{field_emphasis}
```

未知枚举值使用默认值：education_level→master, knowledge_level→intermediate, preferred_style→balanced, research_field→空字符串。

#### `get_extra_instruction(user_profile: dict, agent_name: str = "") -> str`

为Agent生成额外个性化指令：
- agent_name="analyzer"：侧重分析深度和术语使用
- agent_name="generator"或其他：侧重写作风格和解释方式
- 返回简洁指令字符串

与 `AnalyzerAgent._get_extra_instruction()` 调用接口对齐：
```python
personalization_service.get_extra_instruction(user_profile, agent_name="analyzer")
```

#### `build_generation_prompt(analysis_results: list, comparison_result: dict, user_profile: dict) -> str`

完整Prompt组装流程：
1. 调用 `get_personalization_block()` 生成个性化片段
2. 将 `analysis_results` 序列化为JSON字符串
3. 将 `comparison_result` 序列化为JSON字符串
4. 生成用户画像摘要（如"硕士研究生/NLP方向/中级知识水平/标准学术风格"）
5. 通过 `prompt_manager.get_prompt("generator", ...)` 渲染模板
6. prompt_manager 为 None 时降级为直接读取 `prompts/generator.txt` 文件

#### 辅助方法

| 方法 | 返回类型 | 说明 |
|------|---------|------|
| `get_education_adaptation(education_level)` | str | 学历适配Prompt片段 |
| `get_term_density_target(knowledge_level)` | float | 术语密度目标值 |
| `get_style_guide(preferred_style)` | str | 写作风格指南 |
| `get_field_emphasis(research_field)` | str | 领域侧重文本 |

#### 内部标签方法

| 方法 | 返回类型 | 映射 |
|------|---------|------|
| `_education_label(level)` | str | undergraduate→本科, master→硕士, phd→博士, faculty→教师 |
| `_knowledge_label(level)` | str | beginner→入门, intermediate→中级, advanced→进阶, expert→专家 |
| `_style_label(style)` | str | simple→通俗, balanced→均衡, technical→专业 |

未知值返回"未知"。

### 2.4 camelCase兼容

user_profile参数支持snake_case和camelCase两种键名。内部通过 `_normalize_profile()` 方法统一转换为snake_case：

| camelCase | snake_case |
|-----------|-----------|
| educationLevel | education_level |
| researchField | research_field |
| knowledgeLevel | knowledge_level |
| preferredStyle | preferred_style |

### 2.5 降级策略

| 场景 | 触发条件 | 降级行为 |
|------|---------|---------|
| PersonalizationService异常 | `get_personalization_block()`抛出异常 | $personalization注入空字符串，使用默认配置 |
| prompt_manager不可用 | 构造时prompt_manager=None | `build_generation_prompt()`降级为文件读取 |
| 未知枚举值 | 如education_level='postdoc' | 使用默认值，不抛出异常 |

---

## 三、安全要求

| 编号 | 要求 | 优先级 |
|------|------|-------|
| SR-001 | PersonalizationService不记录user_profile完整内容到日志 | P1 |
| SR-002 | Prompt模板和代码中不硬编码API Key或密码 | P0 |

---

## 四、禁止操作

| ID | 禁止操作 | 原因 | 严重度 |
|----|---------|------|-------|
| FA-001 | 在generator.txt中使用Jinja2语法（{{variable}}） | PromptManager使用string.Template | critical |
| FA-002 | 修改prompt_manager.py | 本任务不修改PromptManager | high |
| FA-003 | 修改analyzer.py或其他Agent文件 | Agent集成在后续任务完成 | high |
| FA-004 | 硬编码API Key或密码 | 安全约束 | critical |
| FA-005 | PersonalizationService公共方法抛出异常 | 必须优雅降级 | high |
| FA-006 | 日志中记录user_profile完整内容 | 隐私保护 | high |
| FA-007 | 模板变量名与PromptManager.get_prompt() kwargs不一致 | 运行时渲染失败 | critical |
| FA-008 | PersonalizationService直接导入Agent层代码 | 分层约束 | high |

---

## 五、测试要求

### 单元测试

| 测试名 | 覆盖场景 |
|--------|---------|
| test_generator_prompt_structure | 8区块完整性 |
| test_generator_prompt_variable_rendering | 4个变量正确替换 |
| test_generator_prompt_empty_personalization | $personalization为空时渲染 |
| test_generator_prompt_json_schema | JSON Schema 4字段 |
| test_generator_prompt_cot_steps | 4步CoT推理链 |
| test_personalization_service_get_personalization_block | 个性化片段生成 |
| test_personalization_service_get_extra_instruction | Agent额外指令 |
| test_personalization_service_build_generation_prompt | 完整Prompt组装 |
| test_personalization_service_unknown_enum_defaults | 未知枚举值默认 |
| test_personalization_service_camelcase_input | camelCase兼容 |
| test_personalization_service_no_prompt_manager | prompt_manager=None降级 |
| test_personalization_service_helper_methods | 辅助方法正确性 |
| test_personalization_service_label_methods | 标签方法正确性 |
| test_generator_prompt_manager_integration | PromptManager集成 |

### 验证命令

```bash
# PersonalizationService测试
cd Veritas/ai-service && python -m pytest tests/test_personalization_service.py -v

# 模板渲染验证
cd Veritas/ai-service && python -c "import string; t=open('prompts/generator.txt').read(); s=string.Template(t).substitute(personalization='test',analysis_data='[]',comparison_data='',user_profile_summary='test'); print('Render OK, length:', len(s))"

# PromptManager集成测试
cd Veritas/ai-service && python -m pytest tests/test_prompt_manager.py -v -k "generator"
```

---

## 六、验收标准

| ID | 验收条件 | 验证方式 |
|----|---------|---------|
| AC-001 | generator.txt包含8个完整区块 | 自动测试 |
| AC-002 | generator.txt包含4步CoT推理链 | 自动测试 |
| AC-003 | JSON Schema包含report/citation_list/term_density_actual/personalization_applied | 自动测试 |
| AC-004 | 4个模板变量与PromptManager调用参数对齐 | 自动测试 |
| AC-005 | 使用string.Template语法（$variable） | 自动测试 |
| AC-006 | $personalization为空时正确渲染 | 自动测试 |
| AC-007 | PersonalizationService包含5个完整映射表 | 自动测试 |
| AC-008 | get_personalization_block()生成结构化个性化片段 | 自动测试 |
| AC-009 | get_extra_instruction()与AnalyzerAgent接口对齐 | 自动测试 |
| AC-010 | build_generation_prompt()正确组装，prompt_manager=None时降级 | 自动测试 |
| AC-011 | 所有公共方法对未知枚举值使用默认值 | 自动测试 |
| AC-012 | 兼容camelCase键名输入 | 自动测试 |
| AC-013 | 无硬编码密钥/密码 | 代码审查 |
| AC-014 | 所有pytest测试通过 | 自动测试 |

---

## 七、参考文档

| 文档 | 用途 |
|------|------|
| [AI服务模块系统架构文档](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块系统架构文档.md) | GeneratorAgent/PersonalizationService设计 |
| [架构决策记录(ADR)](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/架构决策记录(ADR).md) | ADR-006 个性化引擎 |
| [AGENTS.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/AGENTS.md) | Agent角色定义、个性化4维度策略表 |
| [analyzer.txt](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/prompts/analyzer.txt) | 已升级的8区块Prompt模板参考 |
| [analyzer.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/app/agents/analyzer.py) | _get_extra_instruction()集成接口 |
| [prompt_manager.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/app/services/prompt_manager.py) | string.Template渲染机制 |
| [schemas.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/app/models/schemas.py) | UserProfile模型定义 |
