# task10 — 论文向量化脚本 + 批量入库

## 项目
XH-202630 科研文献智能助手 — v0.2 M2：单Agent可用 / AM2：RAG检索与3-Agent基础可用

## 需求概述
实现论文向量化脚本与批量入库功能，为 RAG 检索提供向量数据基础。

核心交付：
1. `scripts/import_papers.py` — 论文数据导入脚本（arXiv API 下载 + 清洗 + 分块 + 向量化 + 入库）
2. `app/services/vector_store_service.py` 扩展 — 新增 `add_papers_batch` / `get_paper_by_id` / `update_paper_metadata`
3. `app/utils/text_processing.py` — 文本处理工具（分块、清洗、截断）
4. `tests/test_import_papers.py` + `tests/test_text_processing.py` — 单元测试

## 影响范围

| 层级 | 涉及模块 |
|------|---------|
| python_ai_service | scripts/import_papers.py（新增） |
| python_ai_service | app/services/vector_store_service.py（修改：新增3个方法） |
| python_ai_service | app/utils/text_processing.py（新增） |
| python_ai_service | tests/test_import_papers.py（新增） |
| python_ai_service | tests/test_text_processing.py（新增） |
| data_layer | ChromaDB papers collection（数据填充） |

## Current Architecture

### 已有实现（可直接复用）
- **VectorStoreService** — 已有 `initialize` / `add_papers` / `search` / `delete_papers` / `count` / `close`，本任务仅扩展
- **EmbeddingService** — 已有 `encode` / `encode_batch`，import 脚本直接调用
- **Settings** — 已有 `CHROMA_PATH` / `DASHSCOPE_*` 配置项，无需新增
- **requirements.txt** — 已含 `arxiv==2.1.0`，无需新增依赖

### 参考实现
- 架构文档 §11.1 — `import_papers.py` 参考代码（`fetch_papers` / `clean_papers` / `import_to_vector_db`），需按本任务 FR 要求增强

## Relevant Modules

### import_papers 脚本
- 路径：`Veritas/ai-service/scripts/import_papers.py`
- 职责：论文数据导入 — arXiv API / 本地 JSON → 清洗 → 分块 → 向量化 → 批量入库
- 关键接口：
  - `main()` — CLI 入口，argparse 解析 `--count/--category/--source/--dry-run/--batch-size`
  - `fetch_papers_from_arxiv(category, count)` — arXiv API 搜索，含重试(3次/5s间隔)
  - `fetch_papers_from_json(data_dir)` — 本地 JSON 文件导入
  - `clean_papers(papers)` — 按 title 去重、strip 空白、统一 paper_id 格式
  - `import_to_vector_db(papers, embedding_svc, vector_store_svc, batch_size)` — 分块+向量化+入库

### VectorStoreService 扩展
- 路径：`Veritas/ai-service/app/services/vector_store_service.py`
- 新增方法：
  - `add_papers_batch(ids, embeddings, metadatas, documents, batch_size=50)` — 分批写入，sleep 0.5s 限流
  - `get_paper_by_id(paper_id)` → `Optional[dict]` — 按 ID 查询单篇
  - `update_paper_metadata(paper_id, metadata)` — 更新元数据

### text_processing 工具
- 路径：`Veritas/ai-service/app/utils/text_processing.py`
- 关键接口：
  - `chunk_text(text, chunk_size=800, overlap=100)` → `[{chunk_index, chunk_type, content}]`
  - `clean_text(text)` → 去除多余空白/控制字符，保留中英文和基本标点
  - `truncate_text(text, max_length)` → 优先在句号/换行处截断

## Files To Modify

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `Veritas/ai-service/scripts/import_papers.py` | 论文导入脚本：arXiv+JSON源、清洗、分块、向量化、入库、CLI参数、dry-run |
| 修改 | `Veritas/ai-service/app/services/vector_store_service.py` | 新增 add_papers_batch / get_paper_by_id / update_paper_metadata |
| 新增 | `Veritas/ai-service/app/utils/text_processing.py` | 文本处理：chunk_text / clean_text / truncate_text |
| 新增 | `Veritas/ai-service/tests/test_import_papers.py` | import_papers 脚本测试 |
| 新增 | `Veritas/ai-service/tests/test_text_processing.py` | text_processing 工具测试 |

## Implementation Requirements

### 功能要求

| ID | 功能 | 优先级 | 验收条件 |
|----|------|--------|---------|
| FR-001 | CLI 入口：`--count(200)` / `--category(cs.AI)` / `--source(arxiv\|json)` / `--dry-run` / `--batch-size(50)` | P0 | `--dry-run --count 5` 正常执行 |
| FR-002 | `fetch_papers_from_arxiv(category, count)` — arXiv API 搜索，含重试(3次/5s) | P0 | 返回论文元数据列表 |
| FR-003 | `clean_papers(papers)` — 按 title 去重、strip、统一 paper_id 格式 `arxiv_XXX` | P0 | 重复 title 去重，id 格式统一 |
| FR-004 | `chunk_text(text, 800, 100)` — 分块+重叠，返回 `[{chunk_index, chunk_type, content}]` | P0 | 2000 字文本分 3 块，块间 100 字重叠 |
| FR-005 | `import_to_vector_db()` — 分块+向量化+批量入库，单篇失败不阻塞 | P0 | 3 篇论文入库成功 |
| FR-006 | `add_papers_batch(batch_size=50)` — 分批写入+sleep 0.5s+进度日志 | P0 | 120 条分 3 批写入 |
| FR-007 | `get_paper_by_id(paper_id)` — 按 ID 查询返回 dict 或 None | P1 | 存在返回详情，不存在返回 None |
| FR-008 | `update_paper_metadata(paper_id, metadata)` — 更新元数据 | P1 | 更新后查询返回新值 |
| FR-009 | `clean_text(text)` — 去除空白/控制字符，保留中英文和基本标点 | P0 | 清洗结果正确 |
| FR-010 | `truncate_text(text, max_length)` — 优先句号/换行处截断 | P1 | 在句号处截断 |
| FR-011 | `--source json` 模式 — 从 `data/papers/` 读取本地 JSON | P1 | JSON 文件正确解析 |
| FR-012 | `--dry-run` 模式 — 仅下载清洗不入库，输出统计和示例 | P0 | 不调用 embedding/vector_store |

### 安全要求
- arXiv API 无需 API Key，但若扩展其他数据源需通过环境变量注入凭证
- 日志中禁止输出完整 API Key
- 日志中禁止输出 embedding 向量原始数据

## Constraints

### 命名规范
- Python: 类名 PascalCase, 函数/变量 snake_case, 常量 UPPER_SNAKE_CASE, 文件 snake_case.py
- JSON: 字段名 snake_case
- 跨系统映射: paperId↔paper_id, citationCount↔citation_count, chunkIndex↔chunk_index, chunkType↔chunk_type

### 分层规范
- import_papers.py 是独立脚本，直接调用 Service 层
- text_processing.py 是 utils 工具层，不依赖 Service 层

### 错误处理
- try-except，单篇论文导入失败不阻塞后续论文
- 记录 failed 计数和错误信息

### 日志规范
- 使用 Loguru
- 禁止在日志中输出敏感信息（API Key）
- 禁止在日志中输出 embedding 向量原始数据

## Forbidden Actions

- ❌ 输出伪代码或 TODO 注释（critical）
- ❌ 修改需求范围外的模块（high）
- ❌ 在代码中硬编码 API Key（critical）
- ❌ 分块时不设置 overlap 导致上下文断裂（high）
- ❌ 批量入库时不分批导致内存溢出（high）
- ❌ arXiv API 调用无重试机制（medium）
- ❌ import 脚本不支持 --dry-run 模式（medium）
- ❌ 修改 VectorStoreService 已有方法的签名或行为（high）
- ❌ chunk_text 返回的 chunk_type 使用非规范值（medium）

## Test Requirements

### 单元测试（pytest）

| 测试名 | 覆盖场景 |
|--------|---------|
| chunk_text 正常分块 | 2000 字分 3 块，重叠验证，chunk_type 验证 |
| chunk_text 边界条件 | 空文本、短文本、恰好等于 chunk_size、末尾块合并 |
| chunk_text 重叠验证 | 第 N 块开头与第 N-1 块结尾 overlap 字符相同 |
| clean_text | 空白替换、控制字符去除、保留中英文标点、strip |
| truncate_text | 短文本不截断、句号截断、换行截断、硬截断 |
| add_papers_batch | mock ChromaDB，120 条分 3 批，sleep 验证 |
| get_paper_by_id | 存在返回 dict、不存在返回 None |
| update_paper_metadata | 存在更新成功、不存在 warning 不抛异常 |
| clean_papers 去重 | 重复 title 去重、paper_id 格式统一 |
| import_to_vector_db 单篇失败 | mock 第 2 篇异常，验证第 1/3 篇正常 |

### 验证命令

```bash
# text_processing 单元测试
cd Veritas/ai-service && python -m pytest tests/test_text_processing.py -v

# import_papers 单元测试
cd Veritas/ai-service && python -m pytest tests/test_import_papers.py -v

# VectorStoreService 新增方法测试
cd Veritas/ai-service && python -m pytest tests/test_vector_store.py -v -k "batch or get_paper or update"

# dry-run 端到端验证
cd Veritas/ai-service && python scripts/import_papers.py --dry-run --count 5
```

## Acceptance Criteria

- [ ] import_papers.py 支持 CLI 参数 --count/--category/--source/--dry-run/--batch-size
- [ ] fetch_papers_from_arxiv() 成功从 arXiv 下载论文元数据，含重试机制
- [ ] clean_papers() 按 title 去重并统一 paper_id 格式
- [ ] chunk_text() 按 800 字分块，100 字重叠，返回 [{chunk_index, chunk_type, content}]
- [ ] import_to_vector_db() 分批写入 ChromaDB，单篇失败不阻塞
- [ ] add_papers_batch() 分批 50 条写入，每批间 sleep 0.5s，有进度日志
- [ ] get_paper_by_id() 按 ID 查询返回论文详情 dict 或 None
- [ ] update_paper_metadata() 更新元数据成功，不存在时 warning 不抛异常
- [ ] --dry-run 模式仅下载清洗不入库，输出论文数量和示例数据
- [ ] clean_text() 正确清洗空白、控制字符
- [ ] truncate_text() 优先在句号/换行处截断
- [ ] --source json 模式从 data/papers/ 读取本地 JSON 文件
- [ ] VectorStoreService 已有方法签名和行为未被修改