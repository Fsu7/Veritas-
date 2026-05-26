# Task10 & Task11 收尾计划：VectorStoreService 新方法测试补全

## 当前状态

Task10（论文向量化导入）和 Task11（论文数据验证）的所有核心文件已创建完成：

| 文件 | 状态 | 测试 |
|------|------|------|
| `app/utils/text_processing.py` | ✅ 已创建 | 24/24 通过 |
| `app/services/vector_store_service.py` | ✅ 已扩展3个新方法 | ❌ 缺少新方法测试 |
| `scripts/import_papers.py` | ✅ 已创建 | 12/12 通过 |
| `scripts/validate_papers.py` | ✅ 已创建 | 12/12 通过 |
| `scripts/build_vector_db.py` | ✅ 已创建 | — (脚本无单测要求) |
| `data/papers/sample_papers.json` | ✅ 已创建 | — |
| `tests/test_text_processing.py` | ✅ 24测试通过 | — |
| `tests/test_import_papers.py` | ✅ 12测试通过 | — |
| `tests/test_validate_papers.py` | ✅ 12测试通过 | — |

## 待完成工作

### Step 1: 为 VectorStoreService 3个新方法添加测试

在 `tests/test_vector_store.py` 中新增 `TestVectorStoreBatchAndQuery` 测试类，覆盖：

#### 1.1 `add_papers_batch` 测试
- **test_add_papers_batch_basic**: 120条数据 batch_size=50 分3批写入，验证 count=120
- **test_add_papers_batch_invalid_lengths**: 参数长度不一致抛 ValueError
- **test_add_papers_batch_invalid_dimension**: 非1024维向量抛 VectorStoreException
- **test_add_papers_batch_single_batch**: 数据量≤batch_size 时不分批

#### 1.2 `get_paper_by_id` 测试
- **test_get_paper_by_id_exists**: 添加论文后查询返回详情 dict
- **test_get_paper_by_id_not_exists**: 查询不存在的 paper_id 返回 None

#### 1.3 `update_paper_metadata` 测试
- **test_update_paper_metadata_success**: 更新后查询返回新值
- **test_update_paper_metadata_not_exists**: 更新不存在的 paper_id 不抛异常（仅 warning）

### Step 2: 运行全部测试验证

```bash
cd Veritas/ai-service && .venv/bin/python -m pytest tests/test_vector_store.py -v
cd Veritas/ai-service && .venv/bin/python -m pytest tests/ -v --tb=short
```

### Step 3: 确认已有测试未被破坏

验证 test_vector_store.py 中原有12个测试 + 新增8个测试全部通过。

## 实现细节

### 测试代码风格

- 遵循现有 `test_vector_store.py` 的风格：使用 `pytestmark = pytest.mark.asyncio`，使用 `_random_unit_vector()` 和 `_make_metadata()` 辅助函数
- 新增测试类 `TestVectorStoreBatchAndQuery`，不修改已有测试类
- 使用 `vector_store_service` fixture（来自 conftest.py，基于 tmp_path 的临时 ChromaDB）

### 关键注意点

1. `add_papers_batch` 内部有 `asyncio.sleep(0.5)`，测试时 batch 间会有实际延迟，小数据量影响不大
2. `update_paper_metadata` 对不存在的 paper_id 会触发 ChromaDB 异常，方法内部 catch 后仅 warning，测试验证不抛异常
3. `get_paper_by_id` 返回的 dict 包含 `chunk_index` 和 `chunk_type` 字段，需验证
