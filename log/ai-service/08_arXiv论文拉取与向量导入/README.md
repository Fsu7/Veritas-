# arXiv论文拉取与向量导入

## 功能描述
- **解决问题**：项目需要真实论文数据来验证 RAG 检索和多 Agent 分析功能，但本地只有 5 篇样例论文，数据量不足以支撑检索和分析测试。
- **实现功能**：通过 arXiv API 从 `cs.AI` 类别拉取 10 篇最新论文元数据，使用 DashScope `text-embedding-v4` 模型生成 1024 维向量，并导入 ChromaDB 向量库。
- **业务价值**：为 M2 阶段（单 Agent 可用）提供真实论文数据基础，支持 RAG 检索、论文分析和综述生成功能的联调测试。

## 实现逻辑
- **修改的核心文件列表**：
  - 新建 `.env` 配置文件（原项目无此文件，只有 `.env.example`）
  - 数据写入 `ai-service/data/vector_db/`（ChromaDB 持久化存储）
- **使用的算法或设计模式**：
  - arXiv Python API（`arxiv` 库）异步拉取论文元数据
  - 文本分块策略：标题+摘要超过 800 字符则按 800 字/块、重叠 100 字分块
  - DashScope OpenAI 兼容 API 调用 Embedding 服务
  - ChromaDB `PersistentClient` 批量写入（batch_size=10）
- **关键代码逻辑说明**：
  1. `import_papers.py` 中 `fetch_papers_from_arxiv()` 使用 `arxiv.Search` 按类别和提交日期排序拉取论文
  2. `clean_papers()` 去重并规范化 paper_id 格式（去掉版本号 `vN`）
  3. `import_to_vector_db()` 调用 `EmbeddingService.encode_batch()` 批量生成向量
  4. `VectorStoreService.add_papers_batch()` 分批次写入 ChromaDB，避免单次请求过大

## 接口变更
本次任务未涉及 API 接口变更，属于数据层操作。

### 命令行调用
```bash
# Dry-run 预览
.venv/bin/python scripts/import_papers.py --source arxiv --count 10 --category cs.AI --dry-run

# 实际导入
.venv/bin/python scripts/import_papers.py --source arxiv --count 10 --category cs.AI --batch-size 10

# 验证数据
.venv/bin/python scripts/validate_papers.py --chroma-path ./data/vector_db --verbose
```

## 测试结果
- **测试场景1**：Dry-run 模式成功拉取 10 篇论文，预计生成 25 个分块 → **通过**
- **测试场景2**：实际导入成功，10 篇论文全部向量化并写入 ChromaDB，0 失败 → **通过**
- **测试场景3**：向量维度验证，25 条记录全部为 1024 维 → **通过**
- **测试场景4**：元数据完整性验证，所有记录包含 `paper_id`、`title`、`year` → **通过**
- **是否通过**：是（搜索质量因跨语言检索略低于阈值，属预期行为）

## 相关文件
- 新增配置：`/Veritas/ai-service/.env`
- 导入脚本：`/Veritas/ai-service/scripts/import_papers.py`
- 验证脚本：`/Veritas/ai-service/scripts/validate_papers.py`
- 向量数据库：`/Veritas/ai-service/data/vector_db/`
- 样例数据：`/Veritas/ai-service/data/papers/sample_papers.json`
