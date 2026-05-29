# Task14: 检索准确率测试 + 参数调优

## 任务概述

| 项目 | 内容 |
|------|------|
| **版本** | v0.2 |
| **里程碑** | M2：单Agent可用 / AM2：RAG检索与3-Agent基础可用 |
| **功能编号** | F3.2.6, F3.2.3, F3.2.5 |
| **涉及层级** | Python AI服务 |
| **优先级** | P0/P1 |

## 需求描述

实现检索准确率测试套件和参数调优框架。包含检索准确率指标测试（MRR/NDCG@10/Precision@10/Recall@10）、RRF融合效果测试、重排序效果对比测试。新建评估脚本支持批量查询评估和参数网格搜索。目标：Top10相关性>80%。

## 影响范围

### 新增文件
| 文件 | 说明 |
|------|------|
| `Veritas/ai-service/tests/test_search_accuracy.py` | 检索准确率测试套件 |
| `Veritas/ai-service/scripts/evaluate_search.py` | 评估脚本（参数网格搜索） |
| `Veritas/ai-service/tests/test_data/search_queries.json` | 测试查询集（20+条标注查询） |

### 不修改任何业务代码

## 实现要求

### 检索准确率指标

| 指标 | 说明 | 目标 |
|------|------|------|
| MRR | 第一个相关结果的排名倒数均值 | ≥0.6 |
| NDCG@10 | 考虑位置权重的排序质量 | ≥0.5 |
| Precision@10 | Top10中相关结果比例 | ≥0.5 |
| Recall@10 | Top10中相关结果占全部相关比例 | ≥0.4 |

### 测试覆盖

| 测试 | 说明 |
|------|------|
| 语义检索准确率 | mock环境下验证指标计算 |
| RRF融合效果 | 融合≥单路语义检索 |
| 重排序效果 | 重排序后NDCG≥重排序前 |
| 性能测试 | 语义检索≤3s，混合检索≤5s |

### 评估脚本参数网格

| 参数 | 候选值 |
|------|--------|
| top_k | 5, 10, 20 |
| rrf_k | 30, 60, 120 |
| reranker_weights | (0.5,0.3,0.2), (0.6,0.2,0.2), (0.4,0.4,0.2) |

## 验收标准

- [ ] 四个指标计算函数实现正确
- [ ] 测试查询集≥20条，每条标注3-5篇相关论文
- [ ] RRF融合效果≥单路语义检索
- [ ] 重排序后NDCG@10≥重排序前
- [ ] 评估脚本可执行，支持参数网格搜索
- [ ] 测试代码使用mock，不依赖真实API

## 验证命令

```bash
cd Veritas/ai-service && python -m pytest tests/test_search_accuracy.py -v
cd Veritas/ai-service && python scripts/evaluate_search.py --help
cd Veritas/ai-service && python scripts/evaluate_search.py --top-k 10 --rrf-k 60 --output data/search_eval_report.json
```