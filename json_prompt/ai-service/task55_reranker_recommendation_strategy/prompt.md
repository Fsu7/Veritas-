# task55: 重排序完善 + F3.4.6 推荐策略

> **课题编号**：XH-202630
> **子项目**：科研文献助手 — AI 服务模块
> **里程碑**：M5 / AM5：混合检索与功能完善
> **AM5 天数**：Week 10 Day 5
> **版本**：v0.5
> **功能编号**：F3.2.5, F3.4.6
> **优先级**：P1
> **创建日期**：2026-06-17

---

## 1. 背景与上下文

### 1.1 项目背景

XH-202630 科研文献智能助手 — Reranker 已实现复合评分（RRF×0.5+field×0.3+popularity×0.2+personalization_boost），但 personalization_boost 为简单加权，未实现 F3.4.6 推荐策略。PersonalizationService 已实现 4 维度画像，但推荐策略未实现。

### 1.2 任务需求

完善重排序逻辑，实现 F3.4.6 推荐策略。Reranker.rerank() 支持用户画像注入，不同研究方向用户获得不同排序。新增 Reranker.recommend() 方法基于用户历史分析记录推荐相关论文。F3.4.6 推荐策略：基于用户画像 4 维度（education/research/knowledge/style）计算论文推荐分。推荐分 = rerank_score × 0.7 + recommendation_score × 0.3。RecommendationService 提供 get_recommended_papers(user_id, top_k=10) 接口。验证不同研究方向用户获得不同排序结果（AM5 验收硬指标）。

### 1.3 参考文档

| 文档 | 用途 |
|------|------|
| [docs/ai-service/AI服务模块系统架构文档.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块系统架构文档.md) | 了解 Reranker 复合评分和 PersonalizationService 4 维度画像 |
| [docs/ai-service/AI服务模块项目里程碑文档.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块项目里程碑文档.md) | 确认 AM5 Week 10 Day 5 推荐策略交付物和 F3.4.6 验收 |
| [AGENTS.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/AGENTS.md) | 确认个性化引擎和推荐策略规范 |

---

## 2. 当前架构

### 2.1 涉及层级

- `python_ai_service`

### 2.2 相关模块

| 层级 | 模块路径 | 描述 |
|------|---------|------|
| python_ai_service | `app.services.reranker` | Reranker 已实现复合评分（RRF×0.5+field×0.3+popularity×0.2+personalization_boost），但 personalization_boost 为简单加权，未实现 F3.4.6 推荐策略 |
| python_ai_service | `app.services.personalization_service` | PersonalizationService 已实现 4 维度画像（education_level/knowledge_level/preferred_style/research_field），F3.4.6 推荐策略未实现 |
| python_ai_service | `app.services.search_service` | SearchService 调用 Reranker.rerank()，需支持传入 user_profile |

### 2.3 现有实现

| 文件 | 描述 | 复用方式 |
|------|------|---------|
| `Veritas/ai-service/app/services/reranker.py` | Reranker.rerank() 已实现复合评分，含 personalization_boost 但未独立为推荐分 | extend |
| `Veritas/ai-service/app/services/personalization_service.py` | PersonalizationService 已实现 get_user_profile()，需新增 get_recommendation_strategy() | extend |

---

## 3. 相关模块详情

### 3.1 Reranker

- **路径**：`Veritas/ai-service/app/services/reranker.py`
- **职责**：复合重排序

| 方法 | 签名 | 描述 |
|------|------|------|
| `rerank` | `def rerank(self, papers: List[Dict], query: str, user_profile: Optional[Dict] = None) -> List[Dict]` | 复合评分重排序，需增强 user_profile 注入 |
| `recommend` | `def recommend(self, papers: List[Dict], user_profile: Dict, user_history: List[Dict]) -> List[Dict]` | 新增：基于用户画像和历史的推荐 |

### 3.2 PersonalizationService

- **路径**：`Veritas/ai-service/app/services/personalization_service.py`
- **职责**：用户画像 4 维度

| 方法 | 签名 | 描述 |
|------|------|------|
| `get_user_profile` | `async def get_user_profile(self, user_id: str) -> Dict` | 获取用户画像 4 维度 |
| `get_recommendation_strategy` | `def get_recommendation_strategy(self, user_profile: Dict, paper: Dict) -> float` | 新增：计算论文推荐分 [0, 1] |

---

## 4. 待修改文件

| 操作 | 路径 | 说明 |
|------|------|------|
| modify | `Veritas/ai-service/app/services/reranker.py` | 1) rerank() 增强 user_profile 注入：当 user_profile 非空时，调用 personalization_service.get_recommendation_strategy() 计算推荐分，最终分 = rerank_score × 0.7 + recommendation_score × 0.3；2) 新增 recommend() 方法：基于用户画像和历史分析记录推荐相关论文，返回按推荐分排序的论文列表；3) 保持原有 personalization_boost 逻辑兼容（user_profile 为空时退化为原逻辑）。 |
| modify | `Veritas/ai-service/app/services/personalization_service.py` | 新增 get_recommendation_strategy(user_profile, paper) -> float 方法：1) 基于 4 维度计算推荐分 [0, 1]；2) research_field 匹配权重 0.4（论文研究方向与用户 research_field 一致加分）；3) education_level 匹配权重 0.2（论文难度与用户教育水平匹配加分）；4) knowledge_level 匹配权重 0.2；5) preferred_style 匹配权重 0.2；6) 各维度匹配返回 [0, 1] 分数，加权求和。 |
| create | `Veritas/ai-service/app/services/recommendation_service.py` | RecommendationService：1) get_recommended_papers(user_id: str, top_k: int = 10) -> List[Dict]；2) 调用 personalization_service.get_user_profile() 获取画像；3) 获取用户历史分析记录（从 Java 后端 API 或本地缓存）；4) 候选论文池 = 历史分析论文的相似论文（通过 ChromaDB 相似检索）；5) 调用 reranker.recommend(candidates, user_profile, user_history) 排序；6) 返回 top_k 推荐论文。 |
| create | `Veritas/ai-service/tests/test_reranker_recommendation.py` | 测试：1) test_rerank_with_user_profile 验证 rerank() 接受 user_profile 参数输出个性化排序；2) test_different_research_field_different_order 验证 NLP vs CV 用户 Top5 排序差异度 > 30%；3) test_recommend_method 验证 recommend() 返回推荐论文列表；4) test_recommendation_score_range 验证推荐分范围 [0, 1]；5) test_get_recommendation_strategy 验证 4 维度加权计算；6) test_recommendation_service 验证 get_recommended_papers() 接口。 |

---

## 5. 实现要求

### 5.1 功能需求（FR）

| ID | 优先级 | 描述 | 验收条件 |
|----|--------|------|---------|
| FR-001 | P0 | Reranker.rerank() 支持用户画像注入：1) rerank(papers, query, user_profile=None) 签名保持兼容；2) 当 user_profile 非空时：a) 对每篇论文调用 personalization_service.get_recommendation_strategy(user_profile, paper) 得 recommendation_score [0,1]；b) 最终分 = rerank_score × 0.7 + recommendation_score × 0.3；c) 按最终分降序排序；3) 当 user_profile 为空时：退化为原有 personalization_boost 逻辑（兼容）。 | Reranker.rerank() 接受 user_profile 参数，输出个性化排序 |
| FR-002 | P1 | 新增 Reranker.recommend() 方法：1) 签名 recommend(papers: List[Dict], user_profile: Dict, user_history: List[Dict]) -> List[Dict]；2) 对每篇论文计算推荐分 = research_field_match × 0.4 + education_match × 0.2 + knowledge_match × 0.2 + style_match × 0.2；3) 叠加历史相似度加分（论文与用户历史分析论文的相似度）；4) 按推荐分降序排序；5) 返回排序后论文列表（含 recommendation_score 字段）。 | Reranker.recommend() 返回推荐论文列表 |
| FR-003 | P0 | F3.4.6 推荐策略：基于用户画像 4 维度计算论文推荐分：1) research_field 匹配权重 0.4：论文 keywords/research_field 与用户 research_field 一致得 1.0，部分一致得 0.5，不一致得 0.0；2) education_level 匹配权重 0.2：论文难度（由 abstract 长度/术语密度估算）与用户教育水平匹配得 1.0，不匹配得 0.0；3) knowledge_level 匹配权重 0.2：论文技术深度与用户知识水平匹配；4) preferred_style 匹配权重 0.2：论文写作风格（理论/实验/综述）与用户偏好匹配；5) 加权求和得 recommendation_score [0, 1]。 | F3.4.6 推荐策略基于 4 维度计算推荐分 |
| FR-004 | P1 | 推荐分 = rerank_score × 0.7 + recommendation_score × 0.3：1) rerank_score 为 Reranker 复合评分（归一化到 [0, 1]）；2) recommendation_score 为 F3.4.6 推荐分 [0, 1]；3) 加权求和得最终分；4) 权重可通过 settings 配置（RERANK_WEIGHT=0.7, RECOMMENDATION_WEIGHT=0.3）。 | 推荐分计算正确，recommendation_score 范围 [0, 1] |
| FR-005 | P1 | RecommendationService 提供 get_recommended_papers(user_id, top_k=10) 接口：1) 调用 personalization_service.get_user_profile(user_id) 获取画像；2) 获取用户历史分析记录（调用 Java 后端 /api/analysis/history 或本地缓存，本任务可 mock）；3) 候选论文池 = 历史分析论文的相似论文（ChromaDB 相似检索 top 50）；4) 调用 reranker.recommend(candidates, user_profile, user_history) 排序；5) 返回 top_k 推荐论文（含 recommendation_score 字段）。 | RecommendationService.get_recommended_papers() 返回推荐论文列表 |
| FR-006 | P0 | 验证不同研究方向用户获得不同排序结果（AM5 验收硬指标）：1) 测试用例：同一查询 + 10 篇候选论文；2) 用户A：research_field='NLP'；3) 用户B：research_field='CV'；4) 分别调用 rerank(papers, query, user_profile_A) 和 rerank(papers, query, user_profile_B)；5) 计算 Top5 排序差异度 = (Top5 中不同论文数 / 5)；6) 验证差异度 > 30%（即 Top5 中至少 2 篇不同）。 | 同一查询 NLP vs CV 用户 Top5 排序差异度 > 30% |

---

## 6. 约束

### 6.1 命名规范

| 对象 | Python |
|------|--------|
| 类名 | PascalCase |
| 函数/变量 | snake_case |
| 常量 | UPPER_SNAKE_CASE |
| 文件名 | snake_case.py |

### 6.2 分层规范

- 重排序在 `services/reranker.py`
- 推荐在 `services/recommendation_service.py`
- 画像在 `services/personalization_service.py`

### 6.3 错误处理

- user_profile 为空时退化为原逻辑，不抛异常
- 历史记录获取失败时候选池为空，返回空列表

### 6.4 日志

- 日志库：Loguru
- 禁止：在推荐分计算循环中打印 INFO 日志

---

## 7. 禁止动作

| ID | 动作 | 原因 | 严重性 |
|----|------|------|--------|
| FA-001 | 输出伪代码或 TODO 注释 | 必须输出完整可执行代码 | critical |
| FA-002 | 删除 Reranker 原有 personalization_boost 逻辑 | user_profile 为空时需退化为原逻辑 | high |
| FA-003 | 修改 PersonalizationService 4 维度枚举值 | 4 维度已定义，仅新增计算方法 | high |
| FA-004 | 在推荐分计算中调用 LLM | 推荐分基于规则计算，不调 LLM | high |
| FA-005 | 硬编码推荐权重 0.7/0.3 | 应从 settings 读取，支持环境变量覆盖 | medium |
| FA-006 | RecommendationService 直接查 MySQL | 历史记录通过 Java 后端 API 获取，不直连 DB | high |

---

## 8. 测试要求

### 8.1 单元测试

| 测试名 | 描述 | 框架 | 覆盖范围 |
|--------|------|------|---------|
| test_rerank_with_user_profile | rerank() 接受 user_profile 参数输出个性化排序 | pytest | normal_flow |
| test_different_research_field_different_order | NLP vs CV 用户 Top5 排序差异度 > 30% | pytest | normal_flow, boundary_condition |
| test_recommend_method | recommend() 返回推荐论文列表含 recommendation_score | pytest | normal_flow |
| test_recommendation_score_range | 推荐分范围 [0, 1] | pytest | normal_flow, boundary_condition |
| test_get_recommendation_strategy | 4 维度加权计算推荐分 | pytest | normal_flow |
| test_recommendation_service | get_recommended_papers() 返回推荐论文列表 | pytest | normal_flow, integration |
| test_rerank_without_user_profile_backward_compat | user_profile 为空时退化为原逻辑 | pytest | regression |

### 8.2 验证命令

```bash
cd Veritas/ai-service && python -m pytest tests/test_reranker_recommendation.py -v
```

**预期结果**：7 个测试用例全部通过

---

## 9. 验收标准

| ID | 验收标准 | 验证方式 |
|----|---------|---------|
| AC-001 | Reranker.rerank() 接受 user_profile 参数，输出个性化排序 | automated_test |
| AC-002 | 同一查询，NLP 方向用户 vs CV 方向用户，Top5 排序差异度 > 30% | automated_test |
| AC-003 | RecommendationService.get_recommended_papers() 返回推荐论文列表 | automated_test |
| AC-004 | 推荐分计算正确，recommendation_score 范围 [0, 1] | automated_test |
| AC-005 | user_profile 为空时退化为原逻辑（向后兼容） | automated_test |
