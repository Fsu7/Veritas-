# Context

## 项目
XH-202630 科研文献智能助手 — 领域知识个性化生成与多智能体协同决策系统研究

## 当前版本
v0.2 — M2：单Agent可用 / AM2：RAG检索与3-Agent基础可用

## 需求描述
实现200+篇论文导入ChromaDB并完成数据验证：
1. 使用task10创建的import_papers.py脚本执行实际论文导入，目标200+篇AI/Agent领域论文
2. 创建 `scripts/validate_papers.py` — 数据验证脚本，验证ChromaDB中论文数据完整性（向量维度、元数据字段、去重、检索可用性）
3. 创建 `scripts/build_vector_db.py` — 向量数据库构建脚本（全量重建/增量更新）
4. 验证语义检索质量（输入"Multi-Agent"返回Top10论文，相关性>80%）

## 需求编号
F4.4, F4.4.1, F4.4.4, F3.2.1, F3.2.2, F3.2.3, F4.3.1, F4.3.2, F4.3.4

## 参考文档
- `docs/ai-service/AI服务模块系统架构文档.md` — §10 VectorStoreService(已有add_papers/search/count方法)、§11 论文数据采集模块(F4.4)、§6 RAG检索模块(语义检索验收标准)
- `docs/ai-service/AI服务模块项目里程碑文档.md` — §4.2 AM2交付物清单(200+篇论文向量入库、数据验证)、§4.3 Week3 Day2任务、§4.4验收检查点(Chroma collection.count()≥200、语义检索相关性>80%)
- `docs/开发规范文档.md` — §8 Python AI服务开发规范
- `AGENTS.md` — §7.3 ChromaDB配置、§18验收标准(智能检索Top10相关性>80%)

---

# Current Architecture

## 涉及层级
- Python AI服务层 (`python_ai_service`)
- 数据层 (`data_layer`)

## 相关模块
| 模块 | 路径 | 说明 |
|------|------|------|
| VectorStoreService | `app/services/vector_store_service.py` | 已有add_papers/search/count/delete_papers方法，PersistentClient，HNSW cosine/M=16/ef=200 |
| EmbeddingService | `app/services/embedding_service.py` | 已有encode/encode_batch方法，1024维向量输出 |
| import_papers | `scripts/import_papers.py` | task10创建的论文导入脚本，含fetch_papers/clean_papers/import_to_vector_db |
| text_processing | `app/utils/text_processing.py` | task10创建的文本处理工具 |
| ChromaDB存储 | `data/vector_db` | 持久化存储目录 |

## 已有实现（可直接复用）
| 文件 | 内容 | 复用方式 |
|------|------|---------|
| `scripts/import_papers.py` | 论文导入脚本(fetch_papers/clean_papers/import_to_vector_db) | 直接复用 |
| `app/services/vector_store_service.py` | VectorStoreService(add_papers/search/count/delete_papers，EXPECTED_DIMENSION=1024) | 直接复用 |
| `app/services/embedding_service.py` | EmbeddingService(encode/encode_batch，1024维) | 直接复用 |
| `app/utils/text_processing.py` | 文本处理工具(clean_text/chunk_text/normalize_metadata) | 直接复用 |

---

# Relevant Modules

## VectorStoreService
- **路径**: `Veritas/ai-service/app/services/vector_store_service.py`
- **职责**: ChromaDB向量数据库服务 — 初始化连接、papers collection管理、向量存储/检索/删除
- **关键接口**:
  - `add_papers(paper_ids, embeddings, metadatas, documents)` — 批量添加论文向量，校验维度1024
  - `search(embedding, top_k=10, filters=None)` — 语义检索，返回[{paperId, title, abstract, score, year, venue}]
  - `count()` — 返回collection中向量总数
  - `delete_papers(paper_ids)` — 批量删除论文向量

## EmbeddingService
- **路径**: `Veritas/ai-service/app/services/embedding_service.py`
- **职责**: 文本向量化服务 — 1024维向量输出
- **关键接口**:
  - `encode(text)` — 单条/批量文本编码
  - `encode_batch(texts, batch_size=32)` — 大批量文本编码

## import_papers
- **路径**: `Veritas/ai-service/scripts/import_papers.py`
- **职责**: 论文数据采集与导入脚本
- **关键接口**:
  - `fetch_papers(count, category)` — 从arXiv API采集论文
  - `clean_papers(raw_papers)` — 清洗论文数据
  - `import_to_vector_db(papers, chroma_path)` — 导入ChromaDB

---

# Files To Modify

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `Veritas/ai-service/scripts/validate_papers.py` | 数据验证脚本：CLI入口(--chroma-path/--verbose/--fix)，验证向量维度/元数据完整性/去重/检索可用性，输出JSON报告，失败exit(1) |
| 新增 | `Veritas/ai-service/scripts/build_vector_db.py` | 向量数据库构建脚本：CLI入口(--mode rebuild/incremental/--count/--category/--dry-run) |
| 新增 | `Veritas/ai-service/tests/test_validate_papers.py` | 验证脚本单元测试 |
| 新增 | `Veritas/ai-service/data/papers/sample_papers.json` | 5篇AI/Agent领域论文样本数据 |

---

# Implementation Requirements

## 功能要求

### FR-001: validate_papers.py CLI入口
- argparse定义：`--chroma-path`(默认`./data/vector_db`)、`--verbose`(默认False)、`--fix`(默认False)
- main()流程：解析参数 → PersistentClient连接 → 获取papers collection → 依次执行4项验证 → 生成报告 → 输出到stdout和`validation_report.json` → 不通过时`sys.exit(1)`

### FR-002: validate_vector_dimensions(collection)
- `collection.get(include=['embeddings'])`获取所有向量（分批处理，limit/offset）
- 验证每条向量维度为1024
- 返回：`{passed, total, abnormal_count, abnormal_ids}`

### FR-003: validate_metadata_integrity(collection)
- `collection.get(include=['metadatas'])`获取所有元数据（分批处理）
- 验证必填字段：paper_id(非空字符串)、title(非空字符串)、year(非空且为有效年份)
- 返回：`{passed, total, incomplete_count, incomplete_records}`

### FR-004: validate_no_duplicates(collection)
- 从metadata提取所有paper_id
- 检查论文级别去重（ChromaDB id是chunk级别如`paper_id_chunk_0`，需从metadata.paper_id提取）
- 返回：`{passed, total, duplicate_count, duplicate_ids}`

### FR-005: validate_search_quality(embedding_service, vector_store_service, test_queries)
- 预定义测试查询：`"Multi-Agent协同决策"` / `"大语言模型"` / `"检索增强生成"`
- 对每个查询：encode → search(top_k=10) → 验证Top1 score>0.5，Top10非空
- 返回：`{passed, query_results: [{query, top1_score, top10_count, passed}]}`

### FR-006: generate_validation_report(results)
- 汇总4项验证结果
- 输出：`{total_papers, dimension_check, metadata_check, duplicate_check, search_quality_check, passed, issues}`
- JSON格式写入`validation_report.json`

### FR-007: build_vector_db.py CLI入口
- argparse定义：`--mode`(rebuild/incremental，必填)、`--count`(默认200)、`--category`(默认cs.AI)、`--chroma-path`(默认`./data/vector_db`)、`--dry-run`(默认False)

### FR-008: rebuild模式
1. PersistentClient连接
2. `client.delete_collection('papers')` 删除旧collection
3. 重新创建collection（HNSW cosine/M=16/ef=200）
4. 调用`import_papers.import_to_vector_db`全量导入
5. dry-run模式仅输出操作日志不实际执行

### FR-009: incremental模式
1. PersistentClient连接
2. 获取现有paper_id集合
3. `fetch_papers`下载 → `clean_papers`清洗 → 过滤已存在paper_id → 仅导入新论文
4. dry-run模式仅输出新论文数量不实际导入

### FR-010: sample_papers.json
- 5篇AI/Agent领域论文样本数据
- 字段：paper_id(arxiv_YYYY_NNN格式)/title/authors/abstract(100-300字)/year(2023-2024)/venue/keywords(3-5个)
- 主题覆盖：Multi-Agent系统、大语言模型Agent、检索增强生成、知识图谱推理、人机协作

## 安全要求
- sample_papers.json禁止包含硬编码API Key
- 脚本中API Key必须从环境变量或settings读取

---

# Constraints

## 命名规范
- Python: 类名PascalCase, 函数/变量snake_case, 常量UPPER_SNAKE_CASE, 文件snake_case.py
- JSON: 字段名snake_case
- 跨系统映射: paperId ↔ paper_id, analysisId ↔ analysis_id

## 分层规范
- 脚本属于scripts/目录，可导入app/services和app/utils模块，但不修改它们
- 验证逻辑封装为独立函数，CLI入口调用验证函数

## 错误处理
- try-except包裹每项验证，单项验证失败不阻塞后续验证
- 错误信息记录到验证报告issues列表

## ChromaDB规范
- 客户端：`chromadb.PersistentClient(path=CHROMA_PATH)`
- Collection名：`papers`
- HNSW配置：space=cosine, M=16, construction_ef=200
- 向量维度：1024
- 必填元数据字段：paper_id, title, year
- ID格式：`paper_id_chunk_index`

## 日志规范
- 使用Loguru
- 禁止在循环中打印INFO及以上级别日志
- 禁止在日志中输出敏感信息

---

# Forbidden Actions

| 编号 | 禁止行为 | 原因 | 严重程度 |
|------|---------|------|---------|
| FA-001 | 输出伪代码或TODO注释 | 必须输出完整可执行代码 | critical |
| FA-002 | 修改需求范围外的模块(如vector_store_service.py/embedding_service.py/import_papers.py) | 避免引入无关变更 | high |
| FA-003 | validate脚本在非--fix模式下修改ChromaDB数据 | 验证脚本默认只读 | high |
| FA-004 | rebuild模式不删除旧collection直接覆盖导入 | 直接覆盖导致旧数据残留 | high |
| FA-005 | 验证脚本无退出码(验证失败应exit(1)) | CI/CD流程依赖退出码 | medium |
| FA-006 | sample_papers.json包含硬编码API Key | 安全约束 | critical |
| FA-007 | collection.get()不分批处理(数据量大时可能OOM) | ChromaDB默认limit=100 | high |
| FA-008 | 使用chromadb.EphemeralClient(内存模式) | 必须使用PersistentClient持久化 | critical |

---

# Test Requirements

## 单元测试
- **框架**: pytest
- **测试文件**: `tests/test_validate_papers.py`

| 测试名 | 内容 | 覆盖场景 |
|--------|------|---------|
| validate_vector_dimensions测试 | mock collection返回1024维/非1024维/空向量 | 正常/异常/边界 |
| validate_metadata_integrity测试 | mock collection返回完整/缺失/空metadata | 正常/异常/边界 |
| validate_no_duplicates测试 | mock collection返回无重复/有重复/空paper_id | 正常/异常/边界 |
| generate_validation_report测试 | 全部通过/部分失败，验证JSON格式 | 正常/异常 |

## 验证命令

```bash
# 数据验证
cd Veritas/ai-service && python scripts/validate_papers.py --chroma-path ./data/vector_db

# 详细验证
cd Veritas/ai-service && python scripts/validate_papers.py --chroma-path ./data/vector_db --verbose

# 构建脚本dry-run
cd Veritas/ai-service && python scripts/build_vector_db.py --mode rebuild --count 5 --dry-run
cd Veritas/ai-service && python scripts/build_vector_db.py --mode incremental --count 10 --dry-run

# 单元测试
cd Veritas/ai-service && pytest tests/test_validate_papers.py -v
```

---

# Acceptance Criteria

| 编号 | 验收标准 | 验证方式 |
|------|---------|---------|
| AC-001 | validate_papers.py支持--chroma-path/--verbose/--fix参数 | 自动测试 |
| AC-002 | 验证向量维度1024，异常时输出具体paper_id | 自动测试 |
| AC-003 | 验证元数据完整性(paper_id/title/year非空) | 自动测试 |
| AC-004 | 验证无重复paper_id | 自动测试 |
| AC-005 | 验证检索质量(Top1相似度>0.5) | 自动测试 |
| AC-006 | 生成JSON格式验证报告 | 自动测试 |
| AC-007 | build_vector_db.py支持rebuild/incremental模式 | 自动测试 |
| AC-008 | rebuild模式先delete_collection再重建，HNSW参数正确 | 代码审查 |
| AC-009 | incremental模式仅导入新论文 | 代码审查 |
| AC-010 | sample_papers.json包含5篇样本论文 | 代码审查 |
| AC-011 | 验证失败时exit(1)，通过时exit(0) | 自动测试 |
| AC-012 | test_validate_papers.py单元测试全部通过 | 自动测试 |
