# 论文向量化导入与数据验证

## 功能描述
- 解决了论文数据从采集到入库ChromaDB的全链路问题，实现了arXiv API论文元数据采集、文本分块、向量化、批量入库的完整流程
- 实现了ChromaDB数据完整性验证（向量维度、元数据完整性、去重、检索质量），以及向量库构建脚本（全量重建/增量更新）
- 业务价值：为RAG语义检索提供数据基础，是M2里程碑"单Agent可用"的核心前置条件

## 实现逻辑

### 修改的核心文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/utils/text_processing.py` | 新建 | 文本处理工具（chunk_text/clean_text/truncate_text） |
| `app/services/vector_store_service.py` | 扩展 | +3方法：add_papers_batch/get_paper_by_id/update_paper_metadata |
| `scripts/import_papers.py` | 新建 | 论文导入脚本（arXiv API + JSON源 + CLI） |
| `scripts/validate_papers.py` | 新建 | 数据验证脚本（向量维度/元数据/去重/检索质量） |
| `scripts/build_vector_db.py` | 新建 | 向量库构建脚本（rebuild/incremental模式） |
| `data/papers/sample_papers.json` | 新建 | 5篇AI/Agent领域样本论文 |
| `tests/test_text_processing.py` | 新建 | 24个测试 |
| `tests/test_import_papers.py` | 新建 | 12个测试 |
| `tests/test_validate_papers.py` | 新建 | 12个测试 |
| `tests/test_vector_store.py` | 修改 | +8个测试（VectorStoreService新方法） |

### 使用的算法或设计模式

1. **文本分块算法**：滑动窗口分块，chunk_size=800字符，overlap=100字符，最后一块不足20%时合并到前一块
2. **批量入库模式**：分批写入（batch_size=50），每批间sleep 0.5s避免API限流
3. **重试机制**：arXiv API调用失败时最多重试3次，间隔5秒
4. **Cache-Aside缓存**：写ChromaDB后删除Redis缓存（由Java后端负责）
5. **降级容错**：单篇论文导入失败不阻塞后续论文，记录failed计数

### 关键代码逻辑说明

#### 文本分块（chunk_text）
```python
# 从位置0开始，每次取chunk_size字符，下次起始位置前移overlap字符
# 首块chunk_type='title_abstract'，后续'continuation'
# 最后一块不足chunk_size的20%时合并到前一块
```

#### 批量入库（add_papers_batch）
```python
# 校验参数长度一致性 + embedding维度1024
# 按batch_size分批调用collection.add()
# 每批之间await asyncio.sleep(0.5)限流
# 记录每批进度日志
```

#### 数据验证（validate_papers）
```python
# 4项验证：向量维度/元数据完整性/去重/检索质量
# 使用collection.get()分批获取(limit/offset)避免OOM
# 验证失败时sys.exit(1)，CI/CD可依赖退出码
```

## 接口变更

### Request（import_papers CLI）
```bash
python scripts/import_papers.py \
  --count 200 \
  --category cs.AI \
  --source arxiv \
  --batch-size 50 \
  --dry-run
```

### Response（import结果）
```json
{
  "total": 200,
  "success": 198,
  "failed": 2,
  "errors": [
    {"paper_id": "arxiv_2401.0001", "error": "Embedding failed"}
  ]
}
```

### Request（validate_papers CLI）
```bash
python scripts/validate_papers.py \
  --chroma-path ./data/vector_db \
  --verbose \
  --fix
```

### Response（验证报告）
```json
{
  "total_papers": 200,
  "dimension_check": {"passed": true, "total": 250, "abnormal_count": 0},
  "metadata_check": {"passed": true, "total": 250, "incomplete_count": 0},
  "duplicate_check": {"passed": true, "total": 250, "duplicate_count": 0},
  "search_quality_check": {"passed": true, "query_results": [...]},
  "passed": true,
  "issues": []
}
```

### Request（build_vector_db CLI）
```bash
python scripts/build_vector_db.py \
  --mode rebuild \
  --count 200 \
  --category cs.AI \
  --dry-run
```

## 测试结果

| 测试文件 | 测试数 | 结果 |
|----------|--------|------|
| test_text_processing.py | 24 | ✅ 全部通过 |
| test_import_papers.py | 12 | ✅ 全部通过 |
| test_validate_papers.py | 12 | ✅ 全部通过 |
| test_vector_store.py（新增部分） | 8 | ✅ 全部通过 |
| **合计** | **56** | **✅ 全部通过** |

### 关键测试场景
- chunk_text：正常分块/边界条件/重叠验证/最后小块合并
- clean_text：空白处理/控制字符清除/中文保留
- truncate_text：句号截断/换行截断/硬截断
- add_papers_batch：120条分3批/参数校验/维度校验
- get_paper_by_id：存在/不存在
- update_paper_metadata：成功/不存在不抛异常
- import_to_vector_db：单篇失败不阻塞
- validate：向量维度/元数据完整性/去重/报告生成

### 实际导入验证
- `--count 2 --source arxiv` 成功导入2篇论文（5个chunk），耗时约1.5秒
- DashScope API（text-embedding-v4）向量化正常，维度1024
- ChromaDB papers collection HNSW配置正确（cosine/M=16/ef=200）

## 相关文件

### 代码文件
- `Veritas/ai-service/app/utils/text_processing.py`
- `Veritas/ai-service/app/services/vector_store_service.py`
- `Veritas/ai-service/scripts/import_papers.py`
- `Veritas/ai-service/scripts/validate_papers.py`
- `Veritas/ai-service/scripts/build_vector_db.py`
- `Veritas/ai-service/data/papers/sample_papers.json`
- `Veritas/ai-service/tests/test_text_processing.py`
- `Veritas/ai-service/tests/test_import_papers.py`
- `Veritas/ai-service/tests/test_validate_papers.py`
- `Veritas/ai-service/tests/test_vector_store.py`

### 配置文件变更
- 无新增配置项，复用现有 `CHROMA_PATH` / `DASHSCOPE_API_KEY` 配置

### 任务Prompt
- `json_prompt/ai-service/task10_paper_vectorization_import/prompt.json`
- `json_prompt/ai-service/task11_paper_data_validation/prompt.json`
