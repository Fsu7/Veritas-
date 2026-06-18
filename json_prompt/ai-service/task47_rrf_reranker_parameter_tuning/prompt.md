# Task 47: RRF k 值 + 重排序权重调优（rrf_reranker_parameter_tuning）

> **里程碑**：AM5 Week 9 Day 2 — 混合检索优化
> **优先级**：P0
> **版本**：v0.5

---

## 任务概述

将 SearchService 的 RRF_K 常量和 Reranker 的权重常量改为从 settings 读取，支持环境变量覆盖。提供参数调优脚本，网格搜索 k 值和权重组合，输出 Top5 准确率对比表。依赖 task46 关键词检索优化完成。

---

## 影响范围

### 涉及层级
- python_ai_service

### 相关模块
- `app.services.search_service` — SearchService（RRF_K 常量）
- `app.services.reranker` — Reranker（权重常量）
- `app.core.config` — Settings 配置类
- `app.core.events` — Reranker 初始化

### 已有实现
- [search_service.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/app/services/search_service.py) `RRF_K = 60` 类级常量
- [reranker.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/app/services/reranker.py) `WEIGHT_RRF=0.5/WEIGHT_FIELD=0.3/WEIGHT_POPULARITY=0.2` 类级常量
- [config.py](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service/app/core/config.py) Settings 类可参考新增配置

---

## 文件变更

| 操作 | 文件路径 | 说明 |
|-----|---------|------|
| 修改 | `app/core/config.py` | 新增 RRF_K/RERANKER_WEIGHT_* 配置项 |
| 修改 | `app/services/search_service.py` | RRF_K 改为从 settings 读取 |
| 修改 | `app/services/reranker.py` | 权重改为从 settings 读取 |
| 修改 | `app/core/events.py` | Reranker 初始化传入 settings |
| 新增 | `scripts/tune_rrf_reranker.py` | 参数调优脚本 |
| 新增 | `tests/test_rrf_reranker_tuning.py` | 调优测试 |
| 修改 | `.env.example` | 新增配置示例 |

---

## 实现要求

### 功能要求

| ID | 描述 | 优先级 |
|----|------|--------|
| FR-001 | Settings 新增 RRF_K=60/RERANKER_WEIGHT_RRF=0.5/RERANKER_WEIGHT_FIELD=0.3/RERANKER_WEIGHT_POPULARITY=0.2 | P0 |
| FR-002 | SearchService 删除 RRF_K 类常量，__init__ 从 settings 读取 self.rrf_k | P0 |
| FR-003 | Reranker 删除权重类常量，__init__ 从 settings 读取，rerank 使用实例属性 | P0 |
| FR-004 | 调优脚本网格搜索 k ∈ {30,60,90,120} × 权重组合，输出 Top5 准确率 Markdown 表 | P1 |
| FR-005 | 权重归一化校验：和 ≈ 1.0（±0.01），否则 logger.warning 不阻止初始化 | P1 |

### 降级要求
- N/A（本任务不涉及 Agent 降级）

---

## 约束

### 命名规范
- Python: 类名 PascalCase，函数/变量 snake_case，配置键 UPPER_SNAKE_CASE

### 分层规范
- 配置在 core/config.py，业务逻辑在 services/，调优脚本在 scripts/

### 错误处理
- 权重归一化失败 logger.warning 不阻止初始化
- 调优脚本单组参数失败 continue 下一组

### 日志规范
- 调优循环中用 DEBUG 不用 INFO

---

## 禁止行为

- ❌ 修改 _reciprocal_rank_fusion 核心算法（score = 1/(k + rank + 1)）
- ❌ 修改 Reranker.rerank 复合评分公式结构
- ❌ 修改 YEAR_DECAY_RATE/TITLE_MATCH_BOOST 等次要常量
- ❌ 删除 Reranker 现有 personalization_boost 逻辑（task55 处理）
- ❌ 硬编码 k 值或权重到业务代码
- ❌ 调优脚本依赖外部数据文件（需内置 fallback 查询）

---

## 测试要求

### 单元测试（pytest）

| 测试名 | 描述 |
|-------|------|
| test_rrf_k_from_settings | RRF_K 默认 60，环境变量 RRF_K=90 时为 90 |
| test_reranker_weights_from_settings | 权重默认 0.5/0.3/0.2，环境变量覆盖生效 |
| test_weight_normalization_warning | 权重和 0.8 时 logger.warning 不抛异常 |
| test_tune_script_executable | 调优脚本可执行，输出 Markdown 表格 |
| test_rrf_fusion_uses_configured_k | _reciprocal_rank_fusion 使用配置的 k 值 |

### 验证命令

```bash
cd Veritas/ai-service && RRF_K=90 RERANKER_WEIGHT_RRF=0.7 python -m pytest tests/test_rrf_reranker_tuning.py -v
cd Veritas/ai-service && python scripts/tune_rrf_reranker.py
```

---

## 验收标准

- [ ] AC-001: RRF_K 可通过环境变量 RRF_K=90 覆盖（automated_test）
- [ ] AC-002: Reranker 权重可通过环境变量覆盖（automated_test）
- [ ] AC-003: 调优脚本输出 k=60 vs k=90 的 Top5 准确率对比（manual_test）
- [ ] AC-004: 权重归一化校验：权重和 ≠ 1.0 时 logger.warning（automated_test）
- [ ] AC-005: 未修改 _reciprocal_rank_fusion 核心算法（code_review）
- [ ] AC-006: 未修改 Reranker.rerank 复合评分公式结构（code_review）
