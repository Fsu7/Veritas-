# Task41: 个性化 Prompt 注入到 6-Agent + 效果测试

## 任务概述

| 项目 | 内容 |
|------|------|
| **版本** | v0.4 |
| **里程碑** | AM4：6-Agent协同与个性化引擎（Week 8 Day 3，M4） |
| **功能编号** | F3.4.3, F3.4.4 |
| **涉及层级** | python_ai_service |
| **优先级** | P0 |

## 需求描述

实现个性化 Prompt 片段注入到 6 个 Agent 的完整链路，并编写效果测试验证个性化**差异度 > 60%**。具体包括：

1. 在 Coordinator/Retriever/Analyzer/Comparer/Generator/Reviewer 6 个 Agent 的 `build_prompt()` 中注入个性化片段
2. 编写个性化差异度测试，验证同一主题不同画像生成结果的差异度 > 60%
3. 编写端到端个性化效果测试，验证 4 维度画像全部生效

本任务是 task39/40 PersonalizationService 的端到端集成任务。

### 核心目标

1. **6 个 Agent 注入个性化片段**：每个 Agent 的 `build_prompt()` 输出含 `【个性化适配】` 标记
2. **检索数量适配**：根据 `knowledge_level` 调整 `top_k`（beginner→5, expert→20）
3. **对比维度适配**：根据 `knowledge_level` 调整对比维度数量（beginner→3, expert→6）
4. **审核严格度适配**：根据 `knowledge_level` 调整审核严格度
5. **个性化差异度测试**：极端画像生成结果差异度 > 60%
6. **4 维度画像生效测试**：education_level / knowledge_level / preferred_style / research_field 均体现
7. **6-Agent 链路完整性测试**：个性化指令不丢失
8. **空画像降级测试**：user_profile 为空时使用默认配置

### 关键约束

- 不在 Agent 中直接实例化 PersonalizationService（通过依赖注入）
- 不修改 Agent 的 `execute()` 核心逻辑（仅修改 `build_prompt()`）
- 测试使用 mock 避免调用真实 LLM API
- 个性化注入失败时使用默认配置，**不阻塞** Agent 执行

## 影响范围

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 修改 | `Veritas/ai-service/app/agents/coordinator.py` | 注入个性化指令 |
| 修改 | `Veritas/ai-service/app/agents/retriever.py` | 注入领域侧重 + top_k 适配 |
| 修改 | `Veritas/ai-service/app/agents/analyzer.py` | 迁移到统一注入接口 |
| 修改 | `Veritas/ai-service/app/agents/comparer.py` | 注入对比深度适配 |
| 修改 | `Veritas/ai-service/app/agents/generator.py` | 统一接口 |
| 修改 | `Veritas/ai-service/app/agents/reviewer.py` | 注入审核严格度适配 |
| 修改 | `Veritas/ai-service/tests/test_personalization_service.py` | 新增差异度测试 |
| 新建 | `Veritas/ai-service/tests/test_personalization_e2e.py` | 端到端效果测试 |

## 6-Agent 注入实现

### 统一注入模式

```python
def build_prompt(self, input_data: dict, context: dict) -> str:
    """统一注入模式：基 Prompt + 个性化片段"""
    # 1. 基础 Prompt
    base_prompt = self.prompt_manager.get_prompt(self.name, ...)

    # 2. 个性化片段（统一接口）
    user_profile = context.get("user_profile", {})
    try:
        personalization = self.personalization_service.get_personalization_for_agent(
            self.name, user_profile
        )
    except Exception as e:
        logger.warning(f"个性化注入失败，使用默认: {e}")
        personalization = "（使用默认个性化配置）"

    # 3. 拼接
    return base_prompt + "\n\n【个性化适配】\n" + personalization
```

### Coordinator Agent

```python
class CoordinatorAgent(BaseAgent):
    def build_prompt(self, input_data: dict, context: dict) -> str:
        base_prompt = self.prompt_manager.get_prompt('coordinator', topic=input_data.get('topic', ''))
        personalization = self.personalization_service.get_personalization_for_agent('coordinator', context.get('user_profile', {}))
        return base_prompt + "\n\n【个性化适配】\n" + personalization
```

### Retriever Agent（含 top_k 动态调整）

```python
class RetrieverAgent(BaseAgent):
    def build_prompt(self, input_data: dict, context: dict) -> str:
        user_profile = context.get("user_profile", {})
        knowledge_level = user_profile.get("knowledge_level", "intermediate")

        # 动态调整 top_k
        top_k_map = {"beginner": 5, "intermediate": 10, "advanced": 15, "expert": 20}
        input_data["top_k"] = top_k_map[knowledge_level]

        base_prompt = self.prompt_manager.get_prompt('retriever', top_k=input_data['top_k'], ...)
        personalization = self.personalization_service.get_personalization_for_agent('retriever', user_profile)
        return base_prompt + "\n\n【个性化适配】\n" + personalization
```

### Analyzer Agent

```python
class AnalyzerAgent(BaseAgent):
    def build_prompt(self, input_data: dict, context: dict) -> str:
        # 统一使用 get_personalization_for_agent 接口（不再用 get_extra_instruction）
        base_prompt = self.prompt_manager.get_prompt('analyzer', ...)
        personalization = self.personalization_service.get_personalization_for_agent('analyzer', context.get('user_profile', {}))
        return base_prompt + "\n\n【个性化适配】\n" + personalization
```

### Comparer Agent（含对比维度动态调整）

```python
class ComparerAgent(BaseAgent):
    def build_prompt(self, input_data: dict, context: dict) -> str:
        user_profile = context.get("user_profile", {})
        knowledge_level = user_profile.get("knowledge_level", "intermediate")

        # 动态调整对比维度数量
        dim_count_map = {"beginner": 3, "intermediate": 4, "advanced": 5, "expert": 6}
        input_data["dimension_count"] = dim_count_map[knowledge_level]

        base_prompt = self.prompt_manager.get_prompt('comparer', dimension_count=input_data['dimension_count'], ...)
        personalization = self.personalization_service.get_personalization_for_agent('comparer', user_profile)
        return base_prompt + "\n\n【个性化适配】\n" + personalization
```

### Generator Agent

```python
class GeneratorAgent(BaseAgent):
    def build_prompt(self, input_data: dict, context: dict) -> str:
        user_profile = context.get("user_profile", {})
        base_prompt = self.prompt_manager.get_prompt('generator', ...)
        personalization = self.personalization_service.get_personalization_for_agent('generator', user_profile)
        return base_prompt + "\n\n【个性化适配】\n" + personalization
```

### Reviewer Agent

```python
class ReviewerAgent(BaseAgent):
    def build_prompt(self, input_data: dict, context: dict) -> str:
        user_profile = context.get("user_profile", {})
        base_prompt = self.prompt_manager.get_prompt('reviewer', ...)
        personalization = self.personalization_service.get_personalization_for_agent('reviewer', user_profile)
        return base_prompt + "\n\n【个性化适配】\n" + personalization
```

## 6-Agent 注入清单

| Agent | 关注维度 | 动态调整项 | 注入标记 |
|-------|---------|----------|---------|
| Coordinator | 任务分解策略 | 无 | 【个性化适配】 |
| Retriever | 检索关键词权重 | top_k = 5/10/15/20 | 【个性化适配】 |
| Analyzer | 分析深度 + 术语使用 | 无 | 【个性化适配】 |
| Comparer | 对比维度数量 | dim_count = 3/4/5/6 | 【个性化适配】 |
| Generator | 写作风格 + 术语密度 | 无 | 【个性化适配】 |
| Reviewer | 审核严格度 | 无 | 【个性化适配】 |

## 个性化差异度算法

```python
def calculate_personalization_diversity(result_a: str, result_b: str) -> float:
    """
    计算两个生成结果的差异度
    使用 Jaccard 距离 = 1 - |A ∩ B| / |A ∪ B|
    """
    # 分词（简单按空格 + 中文按字）
    words_a = set(tokenize(result_a))
    words_b = set(tokenize(result_b))

    intersection = words_a & words_b
    union = words_a | words_b

    if not union:
        return 0.0

    jaccard_similarity = len(intersection) / len(union)
    diversity = 1.0 - jaccard_similarity

    return diversity
```

| 画像对比 | 预期差异度 |
|---------|----------|
| beginner+undergraduate+simple+ML vs expert+phd+technical+NLP | > 0.6（验收标准） |
| intermediate+master+balanced+CV vs intermediate+master+balanced+CV | 0.0（相同） |
| beginner+undergraduate+simple+CV vs intermediate+master+balanced+CV | ~0.4-0.5（中等差异） |

## 4 维度画像生效测试设计

| 维度 | 验证方法 |
|------|---------|
| `education_level` | 对比 `undergraduate` vs `professor` 的 Prompt 是否包含"补充背景知识" vs "批判性分析" |
| `knowledge_level` | 对比 `beginner` vs `expert` 的 Prompt 是否包含"通俗类比" vs "数学原理" |
| `preferred_style` | 对比 `simple` vs `technical` 的 Prompt 是否包含"短句" vs "长句从嵌套结构" |
| `research_field` | 对比 `NLP` vs `CV` 的 Prompt 是否包含"transformer" vs "CNN" |

## 6-Agent 链路完整性测试

```python
def test_six_agents_personalization_chain():
    """验证 6 个 Agent 的 build_prompt() 输出均含【个性化适配】标记"""
    profile = {"education_level": "phd", "knowledge_level": "expert", "preferred_style": "technical", "research_field": "NLP"}
    agents = [
        CoordinatorAgent(),
        RetrieverAgent(),
        AnalyzerAgent(),
        ComparerAgent(),
        GeneratorAgent(),
        ReviewerAgent()
    ]
    for agent in agents:
        prompt = agent.build_prompt({"topic": "transformer"}, {"user_profile": profile})
        assert "【个性化适配】" in prompt, f"{agent.name} 缺少个性化标记"
```

## 空画像降级测试

```python
def test_empty_user_profile_fallback():
    """验证 user_profile 为空时使用默认配置"""
    agents = [CoordinatorAgent(), RetrieverAgent(), AnalyzerAgent(), ComparerAgent(), GeneratorAgent(), ReviewerAgent()]
    for agent in agents:
        # 不传 user_profile
        prompt = agent.build_prompt({"topic": "test"}, {})
        assert "【个性化适配】" in prompt, f"{agent.name} 缺少默认个性化"
        # 不应抛异常
```

## 跨系统字段映射

| Java 字段 | Python 字段 | JSON 字段 |
|----------|------------|---------|
| `educationLevel` | `education_level` | `education_level` |
| `knowledgeLevel` | `knowledge_level` | `knowledge_level` |
| `preferredStyle` | `preferred_style` | `preferred_style` |
| `researchField` | `research_field` | `research_field` |

## 测试覆盖

### 单元测试（pytest，6 个用例）

| 测试名称 | 覆盖场景 |
|---------|---------|
| test_coordinator_build_prompt_has_personalization | 正常流程（含标记） |
| test_retriever_build_prompt_has_personalization | 正常流程（含 top_k 适配） |
| test_comparer_build_prompt_has_personalization | 正常流程（含 dim_count 适配） |
| test_reviewer_build_prompt_has_personalization | 正常流程（含严格度适配） |
| test_all_six_agents_personalization_injection | 正常流程（6 Agent 全链路） |
| test_personalization_empty_profile_fallback | 异常流程 + 降级（空画像） |

### 集成测试（pytest，3 个用例）

| 测试名称 | 覆盖场景 |
|---------|---------|
| test_personalization_diversity_e2e | 端到端（差异度 > 0.6） |
| test_four_dimension_effectiveness | 端到端（4 维度全部生效） |
| test_personalization_full_pipeline | 端到端（6-Agent 链路完整） |

## 验证命令

```bash
# 1. 6-Agent 个性化注入验证
cd /Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service
python -c "
from app.agents.coordinator import CoordinatorAgent
from app.agents.retriever import RetrieverAgent
from app.agents.analyzer import AnalyzerAgent
from app.agents.comparer import ComparerAgent
from app.agents.generator import GeneratorAgent
from app.agents.reviewer import ReviewerAgent

profile = {'education_level': 'phd', 'knowledge_level': 'expert', 'preferred_style': 'technical', 'research_field': 'NLP'}
for Agent in [CoordinatorAgent, RetrieverAgent, AnalyzerAgent, ComparerAgent, GeneratorAgent, ReviewerAgent]:
    agent = Agent()
    prompt = agent.build_prompt({'topic': 'transformer'}, {'user_profile': profile})
    assert '【个性化适配】' in prompt, f'{agent.name} 缺少个性化'
    print(f'{agent.name}: OK')
"

# 2. 差异度验证（极端画像）
python -c "
from app.services.personalization_service import PersonalizationService
ps = PersonalizationService()
diff = ps.get_personalization_diff(
    {'education_level': 'undergraduate', 'knowledge_level': 'beginner', 'preferred_style': 'simple', 'research_field': 'ML'},
    {'education_level': 'phd', 'knowledge_level': 'expert', 'preferred_style': 'technical', 'research_field': 'NLP'}
)
print(f'Diff: {diff}')  # 期望 > 0.6
"

# 3. 单元测试
python -m pytest tests/test_personalization_service.py -v

# 4. 端到端测试
python -m pytest tests/test_personalization_e2e.py -v

# 5. 差异度专项测试
python -m pytest tests/test_personalization_e2e.py::test_personalization_diversity_e2e -v
```

## 验收标准

- [x] AC-001: 6 个 Agent（Coordinator/Retriever/Analyzer/Comparer/Generator/Reviewer）的 `build_prompt()` 输出均包含个性化适配片段
- [x] AC-002: 同一主题，beginner+undergraduate+simple 画像与 expert+phd+technical 画像的生成结果差异度 > 60%
- [x] AC-003: 4 个画像维度（education_level/knowledge_level/preferred_style/research_field）在生成结果中均有可验证的体现
- [x] AC-004: 6-Agent 个性化链路完整：Coordinator→Retriever→Analyzer→Comparer→Generator→Reviewer 全链路个性化指令不丢失
- [x] AC-005: user_profile 为空或缺失时所有 Agent 使用默认配置，不抛异常，不阻塞工作流
- [x] AC-006: 个性化注入失败时记录 warning 日志，Agent 继续执行核心功能
- [x] AC-007: 所有已有测试保持通过，无回归问题
- [x] AC-008: 测试代码使用 mock 避免调用真实 LLM API

## 关键设计决策

### 1. 为什么用【个性化适配】标记？

| 不使用标记 | 使用标记 |
|----------|---------|
| 难以解析个性化片段位置 | 易识别、易提取 |
| 调试时无法快速定位 | 调试友好 |
| LLM 难以区分基础/个性化 | LLM 可识别优先级 |

`【个性化适配】` 是中文标记 + 全角符号，LLM 易于识别，且对中文用户友好。

### 2. 为什么 Retriever 动态调整 top_k？

不同知识水平用户对"信息量"的需求不同：

| 知识水平 | top_k | 理由 |
|---------|-------|------|
| beginner | 5 | 少而精，避免信息过载 |
| intermediate | 10 | 标准量 |
| advanced | 15 | 增加前沿论文 |
| expert | 20 | 关注最新研究 |

固定 top_k=10 对 beginner 太多、对 expert 太少。

### 3. 为什么 Comparer 动态调整对比维度数量？

| 知识水平 | 维度数 | 理由 |
|---------|--------|------|
| beginner | 3 | 核心维度：方法/效果/场景 |
| intermediate | 4 | + 局限 |
| advanced | 5 | + 未来方向 |
| expert | 6 | + 理论贡献 |

维度越多，LLM 输出越长、越深入。beginner 看 3 维就够，expert 需要 6 维完整图景。

### 4. 为什么差异度算法用 Jaccard 距离？

| 算法 | 适用 | 用户画像/生成结果 |
|------|------|-----------------|
| 余弦相似度 | 连续向量 | ❌ 离散文本 |
| 编辑距离 | 字符串 | ❌ 长度敏感 |
| Jaccard 距离 | 离散集合 | ✅ 词集合 |

Jaccard 距离对**长度不敏感**，且实现简单。

## 上下游关系

```
Java 后端 (AnalysisRequest)
       ↓ DTO: userProfile
Python AI 服务
       ↓ 解析 + camelCase → snake_case
6-Agent 工作流
       ↓
Coordinator.build_prompt()
       ↓ + 个性化指令【协调者】
Retriever.build_prompt()
       ↓ + 个性化指令【检索者】+ 动态 top_k
Analyzer.build_prompt()
       ↓ + 个性化指令【分析者】
Comparer.build_prompt()
       ↓ + 个性化指令【对比者】+ 动态 dim_count
Generator.build_prompt()
       ↓ + 个性化指令【生成者】
Reviewer.build_prompt()
       ↓ + 个性化指令【审核者】
       ↓
LLM 推理（每个 Agent 体现个性化）
       ↓
最终结果（差异度 > 60%）
```

## 参考文档

- [AI服务模块系统架构文档 §8 个性化引擎](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块系统架构文档.md)
- [AI服务模块项目里程碑文档 §6.3 Week 8 Day 3](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块项目里程碑文档.md)
- [AI服务模块项目里程碑文档 §6.4 验收标准](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块项目里程碑文档.md)
- [AGENTS.md §关键规则](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/AGENTS.md)
- [04-Personalization.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/agents/04-personalization.md)
- [Task39 PersonalizationService 完整实现](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/json_prompt/ai-service/task39_personalization_service_complete/prompt.md)
- [Task40 难度/风格映射表](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/json_prompt/ai-service/task40_difficulty_style_mapping/prompt.md)

## 下一步建议

1. **AM4 阶段收尾**: 跑完 6-Agent 全链路集成测试 + 个性化效果 A/B 测试
2. **M4 答辩准备**: 准备 AM4 里程碑的演示材料 + 个性化效果展示
3. **未来增强** (AM5+):
   - 个性化效果量化评估（BLEU、ROUGE、CIDEr 等）
   - 用户满意度调研（A/B 测试 + 问卷）
   - 引入强化学习（基于用户反馈自动优化个性化策略）
   - 跨设备个性化同步（手机/平板/PC 同一画像）
   - 个性化策略可解释性（向用户展示"为什么这样生成"）
   - 群体个性化（同一实验室/同一年级的用户使用相似画像）
   - 隐私保护增强（差分隐私 + 联邦学习）
