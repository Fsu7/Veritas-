# Task13: 检索API增强 + 规则重排序器

## 任务概述

| 项目 | 内容 |
|------|------|
| **版本** | v0.2 |
| **里程碑** | M2：单Agent可用 / AM2：RAG检索与3-Agent基础可用 |
| **功能编号** | F3.2.4, F3.2.5, F3.5.2 |
| **涉及层级** | Python AI服务 |
| **优先级** | P0/P1 |

## 需求描述

实现检索API增强和规则重排序器（Reranker）。1) 重构 search.py 端点，新增混合检索路由和检索建议路由。2) 新建 Reranker，实现基于规则的多维度重排序，按架构文档公式 `score_rrf×0.5 + field×0.3 + popularity×0.2` 排序。

## 影响范围

### 新增文件
| 文件 | 说明 |
|------|------|
| `Veritas/ai-service/app/services/reranker.py` | Reranker类，规则重排序 |

### 修改文件
| 文件 | 说明 |
|------|------|
| `Veritas/ai-service/app/api/endpoints/search.py` | 新增hybrid和suggest路由 |
| `Veritas/ai-service/app/models/schemas.py` | 新增HybridSearchRequest等模型 |
| `Veritas/ai-service/app/core/events.py` | 注册Reranker并注入SearchService |

## 实现要求

### Reranker 多维度评分

| 维度 | 权重 | 计算方式 |
|------|------|---------|
| RRF分数 | 0.5 | 直接使用检索返回的score |
| 领域相关性 | 0.3 | 标题匹配+0.1, 关键词密度×0.05, 研究方向匹配+0.05 |
| 流行度 | 0.2 | min(citation/100,1)×0.1 + 年份衰减exp(-0.05×Δyear) |

### 新增API路由

| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/search/hybrid` | POST | 混合检索+重排序 |
| `/api/search/suggest` | GET | 搜索建议（标题前缀匹配） |

### 降级策略
- Reranker异常时返回原始未排序结果 + 日志 WARNING

## 验收标准

- [ ] Reranker多维度评分+个性化排序实现完整
- [ ] 综合分数公式正确（0.5/0.3/0.2权重）
- [ ] POST /api/search/hybrid 可用
- [ ] GET /api/search/suggest 可用
- [ ] Reranker异常时返回原始结果不阻断
- [ ] AppState正确注册Reranker并注入SearchService

## 验证命令

```bash
cd Veritas/ai-service && python -m pytest tests/test_reranker.py tests/test_search_endpoint.py -v
cd Veritas/ai-service && python -c "from app.services.reranker import Reranker; print('Import OK')"
```