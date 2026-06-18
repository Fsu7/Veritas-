# Task 46: 关键词检索优化（hybrid_search_keyword_optimization）

> **里程碑**：AM5 Week 9 Day 1 — 混合检索优化
> **优先级**：P0
> **版本**：v0.5

---

## 任务概述

优化 `SearchService.keyword_search()` 的关键词分词与召回质量，支持中文 bigram + 英文 token 混合检索，支持短语查询精确匹配，关键词检索失败时降级为语义检索。本任务是 AM5 混合检索优化的第一步，为后续 RRF 调优（task47）和准确率基准测试（task48）奠定基础。

---

## 影响范围

### 涉及层级
- python_ai_service

### 相关模块
- `app.services.search_service` — SearchService 检索服务
- `app.services.vector_store_service` — ChromaDB 向量存储操作

### 已有实现（可复用）
- [search_service.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/app/services/search_service.py) `keyword_search()` 已实现，需扩展分词逻辑
- [vector_store_service.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/app/services/vector_store_service.py) `search_by_keywords()` 使用 where_document 过滤，需优化为多 token OR 查询
- `SearchService.search()` 语义检索方法已稳定，可作为降级目标

---

## 文件变更

| 操作 | 文件路径 | 说明 |
|-----|---------|------|
| 修改 | `Veritas/ai-service/app/services/search_service.py` | 新增 `_tokenize_query` 方法，优化 `keyword_search` 分词与降级 |
| 修改 | `Veritas/ai-service/app/services/vector_store_service.py` | 优化 `search_by_keywords` 支持多 token OR 查询和短语精确匹配 |
| 新增 | `Veritas/ai-service/tests/test_keyword_search_optimization.py` | 关键词检索优化测试 |

---

## 实现要求

### 功能要求

| ID | 描述 | 优先级 |
|----|------|--------|
| FR-001 | 新增 `_tokenize_query(query) -> Tuple[List[str], List[str]]` 方法，返回 (tokens, phrases)。双引号包裹作为 phrase；英文按空格分词转小写过滤停用词；中文按 bigram 切分 | P0 |
| FR-002 | 修改 `keyword_search`：调用 `_tokenize_query` → 调用 `search_by_keywords(tokens, phrases)` → 按命中 token 数加权排序。召回率 > 70% | P0 |
| FR-003 | 修改 `search_by_keywords` 签名新增 `tokens`/`phrases` 参数，构建 `$or`/`$and` 组合 where_document 查询 | P0 |
| FR-004 | `keyword_search` 异常时降级调用 `self.search()` 语义检索，不抛出异常 | P0 |
| FR-005 | 短语查询支持：双引号包裹部分作为 phrase 精确匹配，phrase 匹配排名高于 token 匹配 | P1 |

### 降级要求
- keyword_search 失败时降级为语义检索 `self.search()`，不阻塞 hybrid_search 流程

### 安全要求
- ChromaDB where_document 查询使用 SDK 参数化构建，禁止字符串拼接

---

## 约束

### 命名规范
- Python: 类名 PascalCase，函数/变量 snake_case，常量 UPPER_SNAKE_CASE
- 跨系统字段映射: paperId ↔ paper_id, analysisId ↔ analysis_id

### 分层规范
- Router → Service → Agent，keyword_search 逻辑在 SearchService 中

### 错误处理
- try-except，keyword_search 异常降级为语义检索
- 降级日志: `logger.warning(f'Keyword search failed, degrading to semantic search: {e}')`

### 日志规范
- 使用 Loguru
- 禁止在分词循环中打印 INFO 及以上级别日志

---

## 禁止行为

- ❌ 输出伪代码或 TODO 注释
- ❌ 修改 SearchService.search() 语义检索方法核心逻辑
- ❌ 修改 hybrid_search 或 _reciprocal_rank_fusion 方法（RRF 调优在 task47）
- ❌ 引入 jieba 等外部中文分词库（保持依赖最小化，用 bigram）
- ❌ 硬编码停用词到业务代码（应作为模块级常量 STOP_WORDS）
- ❌ keyword_search 失败时抛出异常中断 hybrid_search
- ❌ 修改 _format_results 返回格式
- ❌ 在分词循环中打印 INFO 日志

---

## 测试要求

### 单元测试（pytest）

| 测试名 | 描述 | 覆盖场景 |
|-------|------|---------|
| test_tokenize_query_chinese | 中文查询分词：'多智能体协同决策' → bigram tokens | normal_flow, boundary_condition |
| test_tokenize_query_english | 英文查询分词：'multi agent system' → tokens（停用词过滤） | normal_flow |
| test_tokenize_query_mixed | 中英文混合：'Multi-Agent 协同决策' → 英文+中文 bigram | normal_flow, boundary_condition |
| test_tokenize_query_phrase | 短语查询：'"graph neural network" 综述' → phrases+tokens | normal_flow |
| test_keyword_search_degradation | 降级路径：mock 异常 → 语义检索降级 | error_flow, degradation |
| test_keyword_search_recall | 召回率：20 条查询 Top10 召回率 > 70% | normal_flow |

### 验证命令

```bash
cd Veritas/ai-service && python -m pytest tests/test_keyword_search_optimization.py -v
```

---

## 验收标准

- [ ] AC-001: keyword_search 对中文查询返回相关论文，Top10 召回率 > 70%（automated_test）
- [ ] AC-002: 中英文混合查询正确分词，tokens 同时包含英文 token 和中文 bigram（automated_test）
- [ ] AC-003: keyword_search 异常时降级为语义检索，不抛出异常（automated_test）
- [ ] AC-004: 短语查询正确识别为 phrase，精确匹配（automated_test）
- [ ] AC-005: 未修改 SearchService.search() 语义检索方法核心逻辑（code_review）
- [ ] AC-006: 未修改 hybrid_search / _reciprocal_rank_fusion 方法（code_review）
