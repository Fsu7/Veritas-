# RAG检索服务与准确率测试

## 功能描述
- 解决了RAG检索管道中语义检索、关键词检索、RRF融合、多维度重排序的完整实现问题
- 实现了SearchService语义检索服务（Task12）、Reranker规则重排序+搜索API增强（Task13）、检索准确率测试套件与参数调优框架（Task14）
- 业务价值：为6-Agent工作流中的Retriever Agent提供底层检索能力，实现ADR-005定义的混合RAG检索架构，并通过量化指标验证检索质量

## 实现逻辑

### 修改的核心文件列表

| 操作 | 文件 | 说明 |
|------|------|------|
| CREATE | `app/services/search_service.py` | SearchService：语义检索+关键词检索+RRF融合 |
| CREATE | `app/services/reranker.py` | Reranker：多维度规则重排序 |
| MODIFY | `app/services/vector_store_service.py` | 新增search_by_keywords、suggest_titles、citation_count返回 |
| MODIFY | `app/core/events.py` | AppState新增search_service/reranker，启动时初始化 |
| REWRITE | `app/api/endpoints/search.py` | 三路由：语义检索/hybrid+suggest |
| MODIFY | `app/models/schemas.py` | 新增HybridSearchRequest、SearchSuggestResponse |
| MODIFY | `app/main.py` | Health端点新增search_service/reranker状态 |
| CREATE | `tests/test_search_service.py` | SearchService 27个单元测试 |
| CREATE | `tests/test_reranker.py` | Reranker 22个单元测试 |
| CREATE | `tests/test_data/search_queries.json` | 20条标注查询集 |
| CREATE | `tests/test_search_accuracy.py` | 准确率测试套件 27个测试 |
| CREATE | `scripts/evaluate_search.py` | 评估脚本+参数网格搜索 |

### 使用的算法或设计模式

1. **RRF（Reciprocal Rank Fusion）**：`RRF_score(d) = Σ 1/(k + rank_i(d))`，k=60，将语义检索和关键词检索两路结果融合
2. **多维度重排序**：`composite = score_rrf×0.5 + field_score×0.3 + popularity_score×0.2`，field_score包含标题匹配、关键词密度、引用加成、年份衰减
3. **降级模式**：检索失败返回空列表+WARNING日志，不抛异常；Reranker失败返回原始结果
4. **Cache-Aside**：SearchService不直接缓存，由Java后端Redis层负责
5. **参数网格搜索**：evaluate_search.py支持top_k/rrf_k/reranker_weights多维度组合评估

### 关键代码逻辑说明

- **SearchService.search()**：query→EmbeddingService.encode()→VectorStoreService.search()→_format_results()→Reranker.rerank()
- **SearchService.hybrid_search()**：asyncio.gather并行执行语义+关键词检索→_reciprocal_rank_fusion()→Reranker.rerank()→截断top_k
- **Reranker.rerank()**：遍历结果计算title_match_boost、keyword_density_boost、citation_boost、year_decay→field_score→composite_score→personalization_boost→排序
- **准确率指标**：calc_mrr/calc_ndcg/calc_precision/calc_recall，边界条件（空结果、无相关）返回0.0

## 接口变更

### Request — 语义检索
```json
POST /api/search/
{
  "query": "Multi-Agent协同决策",
  "topK": 10,
  "filters": {"year": 2024}
}
```

### Request — 混合检索+重排序
```json
POST /api/search/hybrid
{
  "query": "Multi-Agent协同决策",
  "topK": 10,
  "filters": null,
  "userProfile": {
    "education_level": "master",
    "research_field": "NLP",
    "knowledge_level": "intermediate",
    "preferred_style": "balanced"
  }
}
```

### Request — 标题建议
```
GET /api/search/suggest?query=multi&topK=5
```

### Response — 混合检索
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "results": [
      {
        "paper_id": "arxiv_2401_0001",
        "title": "Multi-Agent Collaborative Decision Making...",
        "abstract": "...",
        "score": 0.95,
        "year": 2024,
        "venue": "NeurIPS",
        "citation_count": 85,
        "rerank_score": 0.6234
      }
    ],
    "total": 1
  },
  "timestamp": "2026-05-29T..."
}
```

### Response — 标题建议
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "suggestions": ["Multi-Agent Collaborative Decision Making...", "Multi-Task Learning..."],
    "total": 2
  },
  "timestamp": "2026-05-29T..."
}
```

## 测试结果

| 测试文件 | 测试数 | 结果 |
|---------|--------|------|
| test_search_service.py | 27 | ✅ 全部通过 |
| test_reranker.py | 22 | ✅ 全部通过 |
| test_search_accuracy.py | 27 | ✅ 全部通过 |
| **合计** | **76** | **✅ 全部通过 (0.14s)** |

### 关键测试场景
- 语义检索：mock EmbeddingService+VectorStoreService，验证调用链和结果格式
- RRF融合：验证重叠论文去重、互补论文补充、k值影响
- 重排序：验证标题匹配提升、引用加成、年份衰减、个性化排序
- 准确率指标：MRR/NDCG/Precision/Recall正确性+边界条件
- RRF融合效果：hybrid MRR ≥ semantic MRR
- 重排序效果：reranked NDCG ≥ original NDCG
- 性能：语义检索<100ms，混合检索<200ms（mock环境）

### 是否通过：是

## 相关文件

### 新增文件
- `Veritas/ai-service/app/services/search_service.py` — SearchService核心检索服务
- `Veritas/ai-service/app/services/reranker.py` — Reranker多维度重排序
- `Veritas/ai-service/app/api/endpoints/search.py` — 检索API端点
- `Veritas/ai-service/tests/test_search_service.py` — SearchService单元测试
- `Veritas/ai-service/tests/test_reranker.py` — Reranker单元测试
- `Veritas/ai-service/tests/test_data/search_queries.json` — 20条标注查询集
- `Veritas/ai-service/tests/test_search_accuracy.py` — 准确率测试套件
- `Veritas/ai-service/scripts/evaluate_search.py` — 评估脚本

### 修改文件
- `Veritas/ai-service/app/services/vector_store_service.py` — 新增search_by_keywords、suggest_titles、citation_count
- `Veritas/ai-service/app/core/events.py` — AppState新增search_service/reranker初始化
- `Veritas/ai-service/app/models/schemas.py` — 新增HybridSearchRequest、SearchSuggestResponse
- `Veritas/ai-service/app/main.py` — Health端点新增状态

### 配置变更
- 无新增配置项，SearchService和Reranker通过AppState生命周期管理
