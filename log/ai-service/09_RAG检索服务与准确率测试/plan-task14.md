# Task14: 检索准确率测试套件与参数调优框架 — 实施计划

## 前置状态

- ✅ Task12: `SearchService` 已完成（语义检索+关键词检索+RRF融合）
- ✅ Task13: `Reranker` + 搜索API已完成（多维度重排序+hybrid/suggest路由）
- 🔄 Task14: 检索准确率测试套件 — **待实施**

## 实施步骤

### Step 1: 创建 `tests/test_data/search_queries.json`

**文件**: `Veritas/ai-service/tests/test_data/search_queries.json`

基于 `data/papers/sample_papers.json` 中的5篇样本论文，构建20+条标注查询集：

```json
[
  {
    "query_id": "q001",
    "query": "Multi-Agent",
    "query_type": "single_keyword",
    "relevant_paper_ids": ["arxiv_2401_0001", "arxiv_2401_0002", "arxiv_2401_0005"],
    "description": "单关键词查询，匹配多Agent相关论文"
  },
  ...
]
```

**查询覆盖4种类型**:
- `single_keyword`: 单关键词（如 "Transformer", "RAG"）— 5条
- `phrase`: 短语查询（如 "注意力机制", "检索增强生成"）— 5条
- `academic`: 学术查询（如 "Multi-Agent协同决策"）— 5条
- `cross_domain`: 跨领域查询（如 "强化学习在NLP中的应用"）— 5条

**相关论文标注规则**:
- 从 sample_papers.json 的5篇论文中选取
- 每条查询标注2-4篇相关论文（5篇池较小，适当放宽）
- 相关性基于标题/摘要/关键词的语义匹配

### Step 2: 创建 `tests/test_search_accuracy.py`

**文件**: `Veritas/ai-service/tests/test_search_accuracy.py`

#### 2.1 指标计算工具函数

```python
def calc_mrr(results: List[dict], relevant_ids: Set[str]) -> float
def calc_ndcg(results: List[dict], relevant_ids: Set[str], k: int = 10) -> float
def calc_precision(results: List[dict], relevant_ids: Set[str], k: int = 10) -> float
def calc_recall(results: List[dict], relevant_ids: Set[str], k: int = 10) -> float
```

**关键实现细节**:
- `calc_mrr`: 遍历results，找到第一个paper_id在relevant_ids中的位置，返回1/rank；空结果/无相关返回0.0
- `calc_ndcg`: DCG = Σ(2^rel - 1) / log2(rank+1)，rel=1 if relevant else 0；IDCG = 理想排序下的DCG；NDCG = DCG/IDCG；边界：IDCG=0时返回0.0
- `calc_precision`: top-k中相关结果数 / k
- `calc_recall`: top-k中相关结果数 / |relevant_ids|；relevant_ids为空时返回0.0

#### 2.2 测试类设计

| 测试类 | 测试内容 | 数量 |
|--------|---------|------|
| `TestMetricCalculations` | MRR/NDCG/Precision/Recall正确性+边界 | ~8 |
| `TestSemanticSearchAccuracy` | mock环境下语义检索准确率 | ~3 |
| `TestRRFFusionEffectiveness` | RRF融合≥单路，不同k值影响 | ~4 |
| `TestRerankerImprovement` | 重排序后NDCG≥重排序前 | ~4 |
| `TestSearchPerformance` | 响应时间阈值验证 | ~2 |

**Mock策略**（复用 test_search_service.py 的模式）:
- `mock_vector_store`: MagicMock + AsyncMock
- `mock_embedding`: MagicMock + AsyncMock
- 构造包含已知相关论文的检索结果，验证指标计算

**关键测试用例**:

1. `TestMetricCalculations`:
   - `test_mrr_first_position`: 相关结果在第1位 → MRR=1.0
   - `test_mrr_third_position`: 相关结果在第3位 → MRR=1/3
   - `test_mrr_no_relevant`: 无相关结果 → MRR=0.0
   - `test_mrr_empty_results`: 空结果 → MRR=0.0
   - `test_ndcg_perfect_ranking`: 完美排序 → NDCG=1.0
   - `test_ndcg_worst_ranking`: 最差排序 → NDCG接近0
   - `test_ndcg_empty_results`: 空结果 → NDCG=0.0
   - `test_precision_recall_basic`: 基本计算验证

2. `TestSemanticSearchAccuracy`:
   - `test_semantic_search_mrr_threshold`: mock返回结果中相关论文排名靠前，验证MRR≥0.6
   - `test_semantic_search_precision_threshold`: 验证Precision@10≥0.5
   - `test_semantic_search_with_test_queries`: 加载search_queries.json，批量验证

3. `TestRRFFusionEffectiveness`:
   - `test_hybrid_mrr_gte_semantic`: 构造两路结果（部分重叠+互补），验证hybrid MRR ≥ semantic MRR
   - `test_hybrid_precision_gte_semantic`: 验证hybrid Precision ≥ semantic Precision
   - `test_rrf_k_value_impact`: 测试k=30/60/120对融合效果的影响
   - `test_rrf_complementary_results`: 语义检索漏掉的论文被关键词检索补充

4. `TestRerankerImprovement`:
   - `test_reranker_ndcg_improvement`: 重排序后NDCG≥重排序前
   - `test_title_match_rerank_improvement`: 标题匹配论文排名提升
   - `test_citation_rerank_improvement`: 高引用论文排名提升
   - `test_personalization_rerank_improvement`: 个性化排序提升相关领域论文

5. `TestSearchPerformance`:
   - `test_semantic_search_latency`: mock环境下<100ms
   - `test_hybrid_search_latency`: mock环境下<200ms

### Step 3: 创建 `scripts/evaluate_search.py`

**文件**: `Veritas/ai-service/scripts/evaluate_search.py`

#### 3.1 CLI参数设计

```python
parser.add_argument("--top-k", nargs="+", type=int, default=[5, 10, 20])
parser.add_argument("--rrf-k", nargs="+", type=int, default=[30, 60, 120])
parser.add_argument("--reranker-weights", nargs="+", type=str, default=["0.5,0.3,0.2"])
parser.add_argument("--queries", type=str, default="tests/test_data/search_queries.json")
parser.add_argument("--output", type=str, default="data/search_eval_report.json")
```

#### 3.2 核心流程

```
1. 加载测试查询集
2. 初始化服务（EmbeddingService + VectorStoreService + SearchService + Reranker）
3. 参数网格遍历：
   for top_k in args.top_k:
     for rrf_k in args.rrf_k:
       for weights in args.reranker_weights:
         对每条查询执行 search/hybrid_search+rerank
         计算 MRR/NDCG/Precision/Recall
4. 输出评估报告JSON
```

#### 3.3 评估报告格式

```json
{
  "timestamp": "2026-05-29T...",
  "parameters": {
    "top_k": 10,
    "rrf_k": 60,
    "reranker_weights": [0.5, 0.3, 0.2]
  },
  "metrics": {
    "mrr": 0.85,
    "ndcg_at_10": 0.78,
    "precision_at_10": 0.72,
    "recall_at_10": 0.65
  },
  "per_query_details": [
    {
      "query": "Multi-Agent",
      "relevant_ids": ["arxiv_2401_0001", ...],
      "retrieved_ids": ["arxiv_2401_0001", ...],
      "metrics": {"mrr": 1.0, "ndcg_at_10": 0.9, ...}
    }
  ]
}
```

#### 3.4 关键实现约束

- 使用 `loguru` 日志
- 不修改业务代码或数据库（只读）
- 支持 `--help` 显示帮助
- 参数网格搜索：每个参数组合生成独立报告条目
- 脚本可通过 `python scripts/evaluate_search.py --help` 验证

### Step 4: 验证

```bash
# 1. 运行准确率测试
cd Veritas/ai-service && python3 -m pytest tests/test_search_accuracy.py -v

# 2. 验证评估脚本帮助
cd Veritas/ai-service && python3 scripts/evaluate_search.py --help

# 3. 运行完整测试套件（确保不破坏已有测试）
cd Veritas/ai-service && python3 -m pytest tests/ -v
```

## 文件清单

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| CREATE | `tests/test_data/search_queries.json` | 20+条标注查询集 |
| CREATE | `tests/test_search_accuracy.py` | 准确率测试套件（~21个测试） |
| CREATE | `scripts/evaluate_search.py` | 评估脚本+参数网格搜索 |
| 不修改 | `app/services/search_service.py` | 禁止修改业务代码 |
| 不修改 | `app/services/reranker.py` | 禁止修改业务代码 |

## 禁止事项

- ❌ 输出伪代码或TODO注释
- ❌ 修改 SearchService 或 Reranker 的实现代码
- ❌ 测试依赖真实LLM/Embedding API调用
- ❌ 硬编码API Key
- ❌ 评估脚本修改业务代码或数据库
