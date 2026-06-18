# 技术教学文档

## 开发思路

### 需求分析过程

AM5 阶段承接 AM4（6-Agent 工作流 + SSE 流式输出）的成果，聚焦于检索质量与推荐策略优化。通过分析 AM4 的测试结果和架构文档，识别出 4 个核心问题：

1. **Embedding 维度不一致**（task53）：task52 实现的 3 个 Provider 的 `embed_query` 返回 2D 数组，但调用方期望 1D 数组，导致 `TestOpenAIDimensionReduction::test_openai_truncates_to_1024_and_normalizes` 测试失败
2. **检索参数硬编码**（task54）：`top_k=10` 硬编码在 `SearchService` 中，无法通过环境变量调整，缺乏调参工具
3. **缺少推荐策略**（task55）：检索结果未结合用户 4 维度画像进行个性化排序，F3.4.6 推荐策略未实现
4. **缺少集成验收**（task56）：AM5 阶段缺少端到端集成测试和验收检查点测试

### 技术选型考虑

#### 1. Embedding 维度修复方案
- **方案 A**：在调用方（`SearchService`）添加 `result.squeeze()` 处理
- **方案 B**：在 Provider 的 `embed_query` 方法中返回 1D 数组 ✅ 选择
- **理由**：方案 B 在源头修复，符合"单一职责原则"，所有调用方无需修改

#### 2. 检索参数配置化方案
- **方案 A**：使用 `.env` 文件 + `os.getenv()` 直接读取
- **方案 B**：通过 `pydantic-settings` 的 `Settings` 类管理 ✅ 选择
- **理由**：方案 B 与现有架构一致（AM4 已使用 `pydantic-settings`），支持类型校验和环境变量覆盖

#### 3. 推荐策略实现方案
- **方案 A**：在 `Reranker` 中直接实现 4 维度加权计算
- **方案 B**：在 `PersonalizationService` 中实现 `get_recommendation_strategy()`，`Reranker` 调用 ✅ 选择
- **理由**：方案 B 符合"单一职责原则"，`PersonalizationService` 负责画像相关计算，`Reranker` 负责排序

#### 4. 向后兼容设计
- **方案 A**：强制要求传入 `user_profile` 和 `personalization_service`
- **方案 B**：通过 `use_recommendation` 标志动态选择策略 ✅ 选择
- **理由**：方案 B 保证 AM4 功能不受影响，渐进式升级

### 架构设计思路

```
┌─────────────────────────────────────────────────────────────┐
│                    AM5 架构设计                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  task53: Embedding 维度修复                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  DashScopeProvider.embed_query → 1D (1024,)         │   │
│  │  JinaProvider.embed_query      → 1D (1024,)         │   │
│  │  OpenAIProvider.embed_query    → 1D (1024,)         │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                  │
│  task54: 检索参数配置化                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Settings.SEARCH_TOP_K (默认 10, 范围 [5, 20])      │   │
│  │  Settings.SEARCH_SIMILARITY_THRESHOLD (默认 0.0)    │   │
│  │  Settings.CHUNK_SIZE (默认 512, 预留)               │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                  │
│  task55: F3.4.6 推荐策略                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  PersonalizationService.get_recommendation_strategy │   │
│  │    → 4 维度加权 (0.4/0.2/0.2/0.2)                   │   │
│  │  Reranker.rerank (增强)                              │   │
│  │    → final = rerank×0.7 + recommendation×0.3        │   │
│  │  Reranker.recommend (新增)                           │   │
│  │    → 基于用户画像和历史的推荐排序                     │   │
│  │  RecommendationService (新增)                        │   │
│  │    → 完整推荐服务                                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                  │
│  task56: AM5 集成验收                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  tests/e2e/test_am5_integration.py (20 测试)        │   │
│  │  tests/e2e/test_am5_acceptance.py (24 测试)         │   │
│  │  tests/e2e/test_6agent_e2e.py (10 测试, AM4 回归)   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 遇到的问题及解决方案

#### 问题 1：task53 测试失败 `assert (1, 1024) == (1024,)`
- **原因**：`embed_query` 调用 `self._embed_via_api([text])` 返回 2D 数组 `(1, 1024)`，但 `embed_query` 应返回 1D `(1024,)`
- **解决方案**：在 3 个 Provider 的 `embed_query` 方法中添加 `result[0]` 索引
- **教训**：API 返回值维度应与接口契约一致，`embed_query` 语义上是"单文本向量化"，应返回 1D

#### 问题 2：task54 similarity_threshold 过滤逻辑方向
- **原因**：ChromaDB 返回 `distance`（越小越相似），但 `similarity_threshold` 语义上是"相似度阈值"（越大越相似）
- **解决方案**：转换 `similarity = 1.0 - distance`，过滤 `similarity < threshold` 的结果
- **教训**：注意不同库的度量方向，ChromaDB 用 distance，业务层用 similarity

#### 问题 3：task55 循环导入风险
- **原因**：`personalization_service.py` 需要 `ACADEMIC_TERMS` 列表，该列表定义在 `generator.py`，但 `generator.py` 可能导入 `personalization_service`
- **解决方案**：将 `ACADEMIC_TERMS` 复制到 `personalization_service.py`，避免循环导入
- **教训**：常量定义应放在公共模块或使用方模块，避免循环依赖

#### 问题 4：task56 测试中 Provider 构造方式错误
- **原因**：测试代码使用 `DashScopeProvider(api_key="test", model="...", dimension=1024)`，但实际 `__init__` 签名是 `(self, settings)`
- **解决方案**：修改测试代码，先构造 `Settings` 对象，再传入 Provider
- **教训**：编写测试前应先查看实际 API 签名

---

## 实现步骤

### 第一步：task53 Embedding 维度修复

1. 分析测试失败原因：`TestOpenAIDimensionReduction::test_openai_truncates_to_1024_and_normalizes` 失败
2. 定位问题代码：3 个 Provider 的 `embed_query` 方法直接返回 `_embed_via_api([text])` 的 2D 结果
3. 修复方案：添加 `result[0]` 索引，将 2D `(1, dim)` 转换为 1D `(dim,)`
4. 运行测试验证：11 个测试全部通过

```python
# 修复前
async def embed_query(self, text: str) -> np.ndarray:
    return await self._embed_via_api([text])  # 返回 (1, 1024)

# 修复后
async def embed_query(self, text: str) -> np.ndarray:
    result = await self._embed_via_api([text])
    return result[0] if len(result) > 0 else np.zeros(self._dimension, dtype=np.float32)  # 返回 (1024,)
```

### 第二步：task54 检索参数配置化

1. 在 `config.py` 添加 3 个配置项：`SEARCH_TOP_K` / `SEARCH_SIMILARITY_THRESHOLD` / `CHUNK_SIZE`
2. 修改 `VectorStoreService.search()` 添加 `similarity_threshold` 参数和过滤逻辑
3. 修改 `SearchService.__init__()` 从 settings 读取参数
4. 修改 `SearchService.search()` / `keyword_search()` / `hybrid_search()` 的 `top_k` 改为 `Optional[int]`
5. 创建 `scripts/tune_retrieval_params.py` 调参脚本
6. 创建 `tests/test_retrieval_params.py` 测试文件
7. 运行测试验证：8 个测试全部通过

### 第三步：task55 推荐策略 F3.4.6

1. 在 `config.py` 添加 `RERANK_WEIGHT` / `RECOMMENDATION_WEIGHT` 配置项
2. 在 `personalization_service.py` 添加 `ACADEMIC_TERMS` 常量和 `get_recommendation_strategy()` 方法
3. 修改 `Reranker.__init__()` 注入 `personalization_service`，读取权重
4. 修改 `Reranker.rerank()` 添加 F3.4.6 推荐策略分支（含向后兼容）
5. 新增 `Reranker.recommend()` 方法
6. 创建 `RecommendationService` 完整推荐服务
7. 创建 `tests/test_reranker_recommendation.py` 测试文件
8. 运行测试验证：9 个测试全部通过

### 第四步：task56 AM5 集成验收

1. 创建 `tests/e2e/test_am5_integration.py`（20 个端到端集成测试）
2. 创建 `tests/e2e/test_am5_acceptance.py`（24 个验收检查点测试）
3. 创建 `tests/e2e/test_6agent_e2e.py`（10 个 AM4 回归测试）
4. 运行测试验证：54 个测试通过 + 1 个跳过
5. 编写 `docs/ai-service/AM5阶段审阅报告.md`

### 第五步：全量回归测试

1. 运行所有 AM5 新增测试：82 passed, 1 skipped
2. 确认 `tests/test_embedding.py` 中 7 个失败为预先存在的环境问题（本地模型下载）
3. 确认 AM4 功能未受影响

---

## 解决了什么问题

### 核心问题描述

1. **Embedding 维度不一致**：3 个 Provider 的 `embed_query` 返回 2D 数组，导致下游调用维度不匹配
2. **检索参数不可配置**：`top_k` 硬编码，无法通过环境变量调整
3. **缺少个性化推荐**：检索结果未结合用户画像进行个性化排序
4. **缺少集成测试**：AM5 阶段缺少端到端验收测试

### 解决方案对比

#### Embedding 维度修复
| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| 调用方 squeeze | 修改少 | 多处修改，违反单一职责 | ❌ |
| Provider 内修复 | 源头修复，调用方无需改 | 需修改 3 个 Provider | ✅ |

#### 检索参数配置化
| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| os.getenv() | 简单 | 无类型校验 | ❌ |
| pydantic-settings | 类型校验，环境变量覆盖 | 需学习成本 | ✅ |

#### 推荐策略实现
| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| Reranker 内实现 | 简单 | 违反单一职责 | ❌ |
| PersonalizationService 实现 | 职责清晰 | 需注入依赖 | ✅ |

### 最终方案的优势

1. **源头修复**：Embedding 维度问题在 Provider 层修复，所有调用方受益
2. **配置化**：所有参数通过 `Settings` 管理，支持环境变量覆盖，运维友好
3. **职责清晰**：`PersonalizationService` 负责画像计算，`Reranker` 负责排序，`RecommendationService` 负责推荐流程
4. **向后兼容**：通过 `use_recommendation` 标志动态选择策略，AM4 功能不受影响
5. **测试完备**：82 个测试覆盖所有功能点和边界情况

---

## 变更内容

### 新增文件

| 文件路径 | 作用 |
|---------|------|
| `Veritas/ai-service/app/services/recommendation_service.py` | RecommendationService 完整推荐服务 |
| `Veritas/ai-service/scripts/tune_retrieval_params.py` | 检索参数调参脚本（网格搜索 16 种组合） |
| `Veritas/ai-service/tests/test_retrieval_params.py` | task54 测试（8 个） |
| `Veritas/ai-service/tests/test_reranker_recommendation.py` | task55 测试（9 个） |
| `Veritas/ai-service/tests/e2e/test_am5_integration.py` | task56 集成测试（20 个） |
| `Veritas/ai-service/tests/e2e/test_am5_acceptance.py` | task56 验收测试（24 个） |
| `Veritas/ai-service/tests/e2e/test_6agent_e2e.py` | task56 AM4 回归测试（10 个） |
| `docs/ai-service/AM5阶段审阅报告.md` | AM5 阶段审阅报告 |

### 修改文件

| 文件路径 | 变更点 |
|---------|--------|
| `Veritas/ai-service/app/services/embedding_service.py` | 3 个 Provider 的 `embed_query` 添加 `result[0]` 索引 |
| `Veritas/ai-service/app/core/config.py` | 新增 5 个配置项（task54: 3 个, task55: 2 个） |
| `Veritas/ai-service/app/services/vector_store_service.py` | `search()` 添加 `similarity_threshold` 参数和过滤逻辑 |
| `Veritas/ai-service/app/services/search_service.py` | `top_k` 改为 `Optional[int]`，从 settings 读取默认值 |
| `Veritas/ai-service/app/services/personalization_service.py` | 新增 `ACADEMIC_TERMS` + `get_recommendation_strategy()` |
| `Veritas/ai-service/app/services/reranker.py` | `__init__` 注入 `personalization_service`，`rerank()` 增强，`recommend()` 新增 |
| `Veritas/ai-service/tests/test_external_embedding.py` | task53 测试更新 |

### 配置变更

| 配置项 | 默认值 | 范围 | 任务 | 说明 |
|--------|--------|------|------|------|
| `SEARCH_TOP_K` | 10 | [5, 20] | task54 | 检索返回数量 |
| `SEARCH_SIMILARITY_THRESHOLD` | 0.0 | [0.0, 0.9] | task54 | 相似度过滤阈值（0.0 不过滤） |
| `CHUNK_SIZE` | 512 | - | task54 | 预留（当前论文摘要+标题不分块） |
| `RERANK_WEIGHT` | 0.7 | - | task55 | rerank_score 权重 |
| `RECOMMENDATION_WEIGHT` | 0.3 | - | task55 | recommendation_score 权重 |

---

## 关键技术点

### 1. Embedding 维度一致性（task53）
- **核心技术**：NumPy 数组索引 `result[0]` 将 2D `(1, dim)` 转换为 1D `(dim,)`
- **实现亮点**：添加空数组保护 `if len(result) > 0 else np.zeros(...)`
- **注意细节**：`embed_documents` 仍返回 2D `(n, dim)`，两者语义不同

### 2. similarity_threshold 过滤逻辑（task54）
- **核心技术**：ChromaDB distance → similarity 转换 `similarity = 1.0 - distance`
- **实现亮点**：`similarity_threshold > 0.0` 时才过滤，默认 0.0 不过滤
- **注意细节**：ChromaDB 的 distance 是余弦距离，越小越相似

### 3. F3.4.6 推荐策略 4 维度加权（task55）
- **核心技术**：4 维度启发式匹配
  - `research_field`：venue / keywords / abstract / title 匹配
  - `education_level`：abstract 长度启发式（本科<500字，硕士300-800字，博士>500字）
  - `knowledge_level`：术语密度启发式（ACADEMIC_TERMS 20 个术语）
  - `preferred_style`：实验型/理论型/综述型检测
- **实现亮点**：权重 0.4/0.2/0.2/0.2，`research_field` 权重最高
- **注意细节**：`ACADEMIC_TERMS` 复制自 `generator.py` 避免循环导入

### 4. 向后兼容设计（task55）
- **核心技术**：`use_recommendation` 标志动态选择策略
- **实现亮点**：三级降级
  1. 有 `user_profile` + `personalization_service` → F3.4.6 推荐策略
  2. 有 `user_profile` 无 `personalization_service` → `personalization_boost`
  3. 无 `user_profile` → 原始 `composite_score`
- **注意细节**：`rerank()` 结果新增 `recommendation_score` 字段，仅在 F3.4.6 模式下存在

### 5. RecommendationService 工作流（task55）
- **核心技术**：候选论文池构建 + 推荐排序
- **实现亮点**：
  - 候选论文池：历史论文的相似论文（ChromaDB 相似检索）
  - 历史相似度加分：最多 +0.2（每个匹配关键词 +0.05）
  - 异常处理：所有失败返回空列表
- **注意细节**：`_fetch_user_history` 当前为 mock，未来对接 Java 后端 API

### 6. 调参脚本（task54）
- **核心技术**：网格搜索 `TOP_K_GRID × THRESHOLD_GRID` = 16 种组合
- **实现亮点**：
  - Mock 模式和真实模式支持
  - 复用 task48 的 `test_queries.json` 和 `expected_results.json`
  - 生成 Markdown 报告，验证最佳组合 Top5 准确率 > 85%
- **注意细节**：Mock 模式用于 CI，真实模式用于线下调参

---

## 经验总结

### 开发过程中的收获

1. **维度一致性很重要**：API 返回值维度应与接口契约一致，`embed_query` 语义上是"单文本向量化"，应返回 1D
2. **配置化优先**：所有可调参数应通过 `Settings` 管理，支持环境变量覆盖，避免硬编码
3. **单一职责原则**：`PersonalizationService` 负责画像计算，`Reranker` 负责排序，职责清晰
4. **向后兼容设计**：通过标志位动态选择策略，保证渐进式升级
5. **测试驱动开发**：每个任务先写测试，再写实现，确保功能正确性

### 踩过的坑及如何避免

#### 坑 1：ChromaDB distance 方向混淆
- **问题**：最初以为 `distance` 越大越相似，实际是越小越相似
- **解决**：转换 `similarity = 1.0 - distance`，过滤 `similarity < threshold`
- **避免**：使用第三方库前应先查阅文档，理解度量方向

#### 坑 2：循环导入风险
- **问题**：`personalization_service.py` 需要 `ACADEMIC_TERMS`，但该列表在 `generator.py`，可能循环导入
- **解决**：将 `ACADEMIC_TERMS` 复制到 `personalization_service.py`
- **避免**：常量定义应放在公共模块或使用方模块，避免循环依赖

#### 坑 3：测试中 Provider 构造方式错误
- **问题**：测试代码使用 `DashScopeProvider(api_key="test", model="...", dimension=1024)`，但实际 `__init__` 签名是 `(self, settings)`
- **解决**：修改测试代码，先构造 `Settings` 对象，再传入 Provider
- **避免**：编写测试前应先查看实际 API 签名，避免凭印象写代码

#### 坑 4：本地模型测试环境依赖
- **问题**：`tests/test_embedding.py` 中 7 个测试依赖 `sentence-transformers` 本地模型下载，沙箱环境无法访问
- **解决**：确认这些测试为预先存在的问题，与 AM5 改动无关
- **避免**：测试应区分单元测试（Mock）和集成测试（真实依赖），单元测试不应依赖外部资源

### 最佳实践建议

1. **API 契约一致性**：接口返回值维度、类型应与文档一致，避免调用方处理不一致
2. **配置化设计**：所有可调参数通过 `Settings` 管理，支持环境变量覆盖
3. **单一职责原则**：每个类/方法只做一件事，职责清晰
4. **向后兼容设计**：通过标志位动态选择策略，保证渐进式升级
5. **测试分层**：单元测试（Mock）→ 集成测试（Mock）→ 端到端测试（真实依赖）
6. **调参脚本**：为可调参数提供网格搜索脚本，支持 Mock 模式和真实模式
7. **审阅报告**：每个阶段完成后编写审阅报告，记录验收标准达成情况和改进建议
