# Task12: SearchService 语义检索服务

## 任务概述

| 项目 | 内容 |
|------|------|
| **版本** | v0.2 |
| **里程碑** | M2：单Agent可用 / AM2：RAG检索与3-Agent基础可用 |
| **功能编号** | F3.2.3, F3.2.1, F3.2.2 |
| **涉及层级** | Python AI服务 |
| **优先级** | P0 |

## 需求描述

实现 `SearchService` 语义检索服务，作为 RAG 检索模块（F3.2）的核心服务层。当前 `search.py` 端点直接调用 `EmbeddingService` + `VectorStoreService`，缺少服务层抽象。需要新建 `services/search_service.py`，封装语义检索全流程（查询向量化 → ChromaDB检索 → 结果格式化），并为后续混合检索（RRF融合）和重排序预留扩展点。

## 影响范围

### 新增文件
| 文件 | 说明 |
|------|------|
| `Veritas/ai-service/app/services/search_service.py` | SearchService类，语义检索+关键词检索+RRF融合 |

### 修改文件
| 文件 | 说明 |
|------|------|
| `Veritas/ai-service/app/core/events.py` | AppState新增search_service，on_startup初始化 |
| `Veritas/ai-service/app/api/endpoints/search.py` | 重构为调用SearchService |

## 实现要求

### 核心方法

| 方法 | 优先级 | 说明 |
|------|--------|------|
| `search(query, top_k, filters)` | P0 | 语义检索：encode → vector_search → format |
| `keyword_search(query, top_k, filters)` | P1 | 关键词检索：ChromaDB where_document过滤 |
| `_reciprocal_rank_fusion(list1, list2, k=60)` | P1 | RRF融合算法 |
| `hybrid_search(query, top_k, filters)` | P1 | 双路并行检索 + RRF融合 |

### 扩展点
- 构造函数可选接收 `reranker` 参数
- `search()` / `hybrid_search()` 返回前若 reranker 存在则调用重排序

### 降级策略
- 检索异常时返回空结果 + 日志 WARNING，不抛出异常

## 跨系统一致性

- Python内部：snake_case
- API输出：通过Pydantic alias转camelCase
- 关键映射：paperId ↔ paper_id, topK ↔ top_k

## 验收标准

- [ ] SearchService 四个核心方法均可调用
- [ ] AppState正确注册SearchService
- [ ] search.py端点重构后API行为一致
- [ ] RRF融合算法正确（k=60，去重合并）
- [ ] reranker扩展点预留且None时正常工作
- [ ] 检索异常返回空结果而非抛出异常
- [ ] 日志规范（不输出完整向量/敏感信息）

## 验证命令

```bash
cd Veritas/ai-service && python -m pytest tests/test_search_service.py -v
cd Veritas/ai-service && python -c "from app.services.search_service import SearchService; print('Import OK')"
```