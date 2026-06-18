# Task 48: 混合检索准确率对比测试（hybrid_search_accuracy_benchmark）

> **里程碑**：AM5 Week 9 Day 3 — 混合检索优化
> **优先级**：P0
> **版本**：v0.5

---

## 任务概述

创建混合检索准确率基准测试，对比纯语义检索 vs 关键词检索 vs 混合检索的 Top5/Top10 准确率，输出含 MRR/nDCG@10/Recall@10 指标的 Markdown 报告。验证 AM5 验收硬指标：混合检索准确率 > 纯语义检索，混合检索 Top5 准确率 > 85%。依赖 task46 和 task47 完成。

---

## 影响范围

### 涉及层级
- python_ai_service

### 相关模块
- `app.services.search_service` — SearchService（直接调用，不修改）

---

## 文件变更

| 操作 | 文件路径 | 说明 |
|-----|---------|------|
| 新增 | `tests/benchmark/search_accuracy_benchmark.py` | 基准测试脚本 |
| 新增 | `tests/benchmark/test_queries.json` | 20 条标注测试查询 |
| 新增 | `tests/benchmark/expected_results.json` | 期望 Top10 结果 |
| 新增 | `tests/benchmark/__init__.py` | 包初始化文件 |

---

## 实现要求

### 功能要求

| ID | 描述 | 优先级 |
|----|------|--------|
| FR-001 | 创建 20 条测试查询（中文 10 + 英文 10），每条含 query/expected_top10/relevance_scores | P0 |
| FR-002 | 基准测试脚本对每条查询运行三种检索方法，计算 Top5/Top10 准确率、MRR、nDCG@10、Recall@10 | P0 |
| FR-003 | MRR 计算：第一个相关论文（relevance_score >= 2）的倒数排名平均值 | P0 |
| FR-004 | nDCG@10 计算：DCG = Σ rel_i/log2(i+1)，nDCG = DCG/IDCG | P0 |
| FR-005 | Recall@10 计算：Top10 中相关论文数 / 期望相关论文总数 | P0 |
| FR-006 | 验证 AM5 硬指标：混合检索 Top10 > 纯语义检索 Top10，混合检索 Top5 > 85% | P0 |

---

## 禁止行为

- ❌ 修改 SearchService 业务代码
- ❌ 使用少于 20 条测试查询
- ❌ 在基准测试中 mock 检索结果（必须真实调用）
- ❌ 硬编码期望结果到测试脚本

---

## 测试要求

### 单元测试（pytest）

| 测试名 | 描述 |
|-------|------|
| test_benchmark_script_executable | 基准测试脚本可执行 |
| test_mrr_calculation | MRR 计算正确性 |
| test_ndcg_calculation | nDCG@10 计算正确性 |
| test_recall_calculation | Recall@10 计算正确性 |
| test_test_queries_json_valid | test_queries.json 格式正确 |

### 验证命令

```bash
cd Veritas/ai-service && python -m pytest tests/test_search_accuracy_benchmark.py -v
cd Veritas/ai-service && python tests/benchmark/search_accuracy_benchmark.py
```

---

## 验收标准

- [ ] AC-001: 基准测试脚本可执行，输出 Markdown 报告（manual_test）
- [ ] AC-002: 混合检索 Top10 准确率 > 纯语义检索 Top10 准确率（automated_test）
- [ ] AC-003: 混合检索 Top5 准确率 > 85%（AM5 验收硬指标）（automated_test）
- [ ] AC-004: test_queries.json 含 20 条查询，格式正确（automated_test）
- [ ] AC-005: MRR/nDCG@10/Recall@10 指标计算正确，范围 [0, 1]（automated_test）
