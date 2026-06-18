# task54: 检索参数优化（chunk_size/top_k/threshold）

> **课题编号**：XH-202630
> **子项目**：科研文献助手 — AI 服务模块
> **里程碑**：M5 / AM5：混合检索与功能完善
> **AM5 天数**：Week 10 Day 4
> **版本**：v0.5
> **功能编号**：F3.2.3, F3.2.4
> **优先级**：P1
> **创建日期**：2026-06-17

---

## 1. 背景与上下文

### 1.1 项目背景

XH-202630 科研文献智能助手 — SearchService 当前使用硬编码 top_k=10，无 similarity_threshold 过滤。检索参数未调优，无法验证 AM5 验收硬指标"检索准确率 > 85%"。

### 1.2 任务需求

调优检索参数（chunk_size/top_k/threshold），使检索准确率 > 85%（AM5 验收硬指标）。将 SEARCH_TOP_K/SEARCH_SIMILARITY_THRESHOLD/CHUNK_SIZE 改为可配置，支持环境变量覆盖。vector_store_service 支持 similarity_threshold 过滤。提供调优脚本网格搜索 top_k × threshold 组合，复用 task48 基准测试数据，输出 Top5 准确率对比表。

### 1.3 参考文档

| 文档 | 用途 |
|------|------|
| [docs/ai-service/AI服务模块系统架构文档.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块系统架构文档.md) | 了解 SearchService 和 VectorStoreService 检索参数现状 |
| [docs/ai-service/AI服务模块项目里程碑文档.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块项目里程碑文档.md) | 确认 AM5 Week 10 Day 4 检索参数优化交付物和准确率>85%硬指标 |
| [AGENTS.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/AGENTS.md) | 确认配置管理规范 |

---

## 2. 当前架构

### 2.1 涉及层级

- `python_ai_service`

### 2.2 相关模块

| 层级 | 模块路径 | 描述 |
|------|---------|------|
| python_ai_service | `app.services.search_service` | SearchService hybrid_search() 使用硬编码 top_k=10，无 similarity_threshold 过滤 |
| python_ai_service | `app.services.vector_store_service` | VectorStoreService search_by_similarity() 返回所有结果，无 threshold 过滤 |
| python_ai_service | `app.core.config` | Settings 配置类，需新增 SEARCH_TOP_K/SEARCH_SIMILARITY_THRESHOLD/CHUNK_SIZE |

### 2.3 现有实现

| 文件 | 描述 | 复用方式 |
|------|------|---------|
| `Veritas/ai-service/app/services/search_service.py` | hybrid_search() 硬编码 top_k=10，需改为从 settings 读取 | extend |
| `Veritas/ai-service/app/services/vector_store_service.py` | search_by_similarity() 无 threshold 过滤，需新增可选参数 | extend |
| `Veritas/ai-service/app/core/config.py` | Settings 已存在，需新增检索参数配置项 | extend |
| `Veritas/ai-service/tests/benchmark/search_accuracy_benchmark.py` | task48 已创建基准测试脚本，本任务调优脚本复用其测试数据 | direct_reuse |

---

## 3. 相关模块详情

### 3.1 SearchService

- **路径**：`Veritas/ai-service/app/services/search_service.py`
- **职责**：混合检索服务

| 方法 | 签名 | 描述 |
|------|------|------|
| `hybrid_search` | `async def hybrid_search(self, query: str, top_k: int = 10) -> List[Dict]` | 混合检索，top_k 需从 settings 读取 |

### 3.2 VectorStoreService

- **路径**：`Veritas/ai-service/app/services/vector_store_service.py`
- **职责**：ChromaDB 向量存储与检索

| 方法 | 签名 | 描述 |
|------|------|------|
| `search_by_similarity` | `async def search_by_similarity(self, query_embedding: List[float], top_k: int = 10) -> List[Dict]` | 相似度检索，需新增 similarity_threshold 参数 |

---

## 4. 待修改文件

| 操作 | 路径 | 说明 |
|------|------|------|
| modify | `Veritas/ai-service/app/core/config.py` | Settings 类新增配置项：1) SEARCH_TOP_K: int = 10（范围 [5, 20]，环境变量覆盖）；2) SEARCH_SIMILARITY_THRESHOLD: float = 0.0（范围 [0.0, 0.9]，0.0 表示不过滤）；3) CHUNK_SIZE: int = 512（论文摘要+标题不分块，环境变量覆盖）。 |
| modify | `Veritas/ai-service/app/services/search_service.py` | 1) hybrid_search() 的 top_k 默认值改为 settings.SEARCH_TOP_K（保留参数覆盖能力）；2) 调用 vector_store_service.search_by_similarity() 时传入 similarity_threshold=settings.SEARCH_SIMILARITY_THRESHOLD；3) keyword_search() 同步使用 settings.SEARCH_TOP_K。 |
| modify | `Veritas/ai-service/app/services/vector_store_service.py` | search_by_similarity() 新增 similarity_threshold: float = 0.0 参数：1) ChromaDB query 返回结果后，过滤 distance < (1 - similarity_threshold) 的结果（ChromaDB distance 越小越相似）；2) similarity_threshold=0.0 时不过滤；3) 过滤后若结果数 < top_k，不补充（保持过滤严格性）。 |
| create | `Veritas/ai-service/scripts/tune_retrieval_params.py` | 调优脚本：1) 网格搜索 top_k ∈ {5, 10, 15, 20} × threshold ∈ {0.0, 0.3, 0.5, 0.7}（共16组合）；2) 复用 task48 的 tests/benchmark/test_queries.json 和 expected_results.json；3) 每组合运行 20 条查询，计算 Top5 准确率；4) 输出 Markdown 报告到 scripts/reports/retrieval_params_tuning_report.md，含组合对比表和最优组合标注；5) 验证最优组合 Top5 准确率 > 85%。 |
| create | `Veritas/ai-service/tests/test_retrieval_params.py` | 测试：1) test_top_k_from_settings 验证 SEARCH_TOP_K 环境变量覆盖；2) test_similarity_threshold_filter 验证低于阈值的结果不返回；3) test_threshold_zero_no_filter 验证 threshold=0.0 不过滤；4) test_chunk_size_config 验证 CHUNK_SIZE 配置项；5) test_tune_script_output 验证调优脚本输出 Markdown 报告。 |

---

## 5. 实现要求

### 5.1 功能需求（FR）

| ID | 优先级 | 描述 | 验收条件 |
|----|--------|------|---------|
| FR-001 | P0 | SEARCH_TOP_K 默认 10，支持环境变量覆盖，范围 [5, 20]：1) Settings.SEARCH_TOP_K: int = 10；2) 环境变量 SEARCH_TOP_K=15 覆盖；3) SearchService.hybrid_search() 默认 top_k=settings.SEARCH_TOP_K；4) 保留方法参数 top_k 覆盖能力（优先级：方法参数 > settings > 默认值）。 | SEARCH_TOP_K 可通过环境变量覆盖 |
| FR-002 | P0 | SEARCH_SIMILARITY_THRESHOLD 默认 0.0（不过滤），支持环境变量覆盖，范围 [0.0, 0.9]：1) Settings.SEARCH_SIMILARITY_THRESHOLD: float = 0.0；2) 环境变量 SEARCH_SIMILARITY_THRESHOLD=0.3 覆盖；3) VectorStoreService.search_by_similarity() 新增 similarity_threshold 参数，默认 settings.SEARCH_SIMILARITY_THRESHOLD；4) 过滤逻辑：ChromaDB distance < (1 - similarity_threshold) 的结果保留（distance 越小越相似）。 | SEARCH_SIMILARITY_THRESHOLD 可通过环境变量覆盖 |
| FR-003 | P1 | CHUNK_SIZE 默认 512（论文摘要+标题不分块），支持环境变量覆盖：1) Settings.CHUNK_SIZE: int = 512；2) 环境变量 CHUNK_SIZE=256 覆盖；3) 当前论文入库策略为摘要+标题整体向量化（不分块），CHUNK_SIZE 预留给未来长论文分块场景；4) 本任务仅新增配置项，不修改入库逻辑。 | CHUNK_SIZE 配置项可从环境变量读取 |
| FR-004 | P1 | 调优脚本 scripts/tune_retrieval_params.py 网格搜索：1) top_k ∈ {5, 10, 15, 20} × threshold ∈ {0.0, 0.3, 0.5, 0.7}（16组合）；2) 复用 tests/benchmark/test_queries.json（20条查询）和 expected_results.json（期望Top10）；3) 每组合：设置环境变量 → 运行20条查询 → 计算 Top5 准确率（命中数/5）；4) 输出 Markdown 报告含组合对比表（top_k, threshold, top5_accuracy, 备注）；5) 标注最优组合（Top5准确率最高）；6) 验证最优组合 Top5 准确率 > 85%。 | 调优脚本输出最优参数组合及 Top5 准确率 |
| FR-005 | P1 | 调优脚本复用 task48 基准测试数据：1) 读取 tests/benchmark/test_queries.json；2) 读取 tests/benchmark/expected_results.json；3) 若文件不存在，输出错误提示并退出；4) 不重复创建测试数据。 | 调优脚本复用 task48 测试数据 |
| FR-006 | P0 | 验证检索准确率 > 85%（AM5 验收硬指标）：1) 调优脚本输出最优组合 Top5 准确率；2) 若 > 85% 输出 PASS；3) 若 ≤ 85% 输出 FAIL 并建议优化方向（调整 RRF k 值、重排序权重、Embedding 模型）；4) 在 Markdown 报告末尾输出验证结论。 | 最优参数下检索准确率 > 85% |

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

- 配置在 `core/`
- 检索服务在 `services/`
- 调优脚本在 `scripts/`
- 测试在 `tests/`

### 6.3 错误处理

- 调优脚本依赖 task48 测试数据，不存在时友好提示退出

### 6.4 日志

- 日志库：Loguru
- 禁止：在检索循环中打印 INFO 日志

---

## 7. 禁止动作

| ID | 动作 | 原因 | 严重性 |
|----|------|------|--------|
| FA-001 | 输出伪代码或 TODO 注释 | 必须输出完整可执行代码 | critical |
| FA-002 | 修改 task48 的基准测试数据文件 | 调优脚本仅读取，不修改 | high |
| FA-003 | 在调优脚本中硬编码测试查询 | 必须从 test_queries.json 读取 | high |
| FA-004 | 删除 SearchService.hybrid_search() 的 top_k 方法参数 | 保留参数覆盖能力，仅改默认值 | high |
| FA-005 | 修改论文入库分块逻辑 | 本任务仅新增 CHUNK_SIZE 配置，不改入库 | medium |
| FA-006 | similarity_threshold 过滤后自动补充结果 | 保持过滤严格性，不补充 | medium |

---

## 8. 测试要求

### 8.1 单元测试

| 测试名 | 描述 | 框架 | 覆盖范围 |
|--------|------|------|---------|
| test_top_k_from_settings | SEARCH_TOP_K=15 环境变量覆盖默认值10 | pytest | normal_flow |
| test_similarity_threshold_filter | threshold=0.3 时低于阈值结果不返回 | pytest | normal_flow, boundary_condition |
| test_threshold_zero_no_filter | threshold=0.0 时不过滤，返回全部 top_k 结果 | pytest | normal_flow |
| test_chunk_size_config | CHUNK_SIZE=256 环境变量覆盖默认值512 | pytest | normal_flow |
| test_tune_script_output | 调优脚本输出 Markdown 报告含16组合对比表 | pytest | normal_flow |

### 8.2 验证命令

```bash
# 单元测试
cd Veritas/ai-service && python -m pytest tests/test_retrieval_params.py -v
# 预期：5 个测试用例全部通过

# 调优脚本
cd Veritas/ai-service && python scripts/tune_retrieval_params.py
# 预期：输出 Markdown 报告，最优组合 Top5 准确率 > 85%
```

---

## 9. 验收标准

| ID | 验收标准 | 验证方式 |
|----|---------|---------|
| AC-001 | SEARCH_TOP_K / SEARCH_SIMILARITY_THRESHOLD 可通过环境变量覆盖 | automated_test |
| AC-002 | similarity_threshold 过滤生效，低于阈值的结果不返回 | automated_test |
| AC-003 | 调优脚本输出最优参数组合及 Top5 准确率 | manual_test |
| AC-004 | 最优参数下检索准确率 > 85% | automated_test |
