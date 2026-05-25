# task05 — 批量向量化测试 + 连接验证

## 项目
XH-202630 科研文献智能助手 — v0.1 M1：基础设施就绪 / AM1：项目骨架与模型层就绪

## 需求概述
编写 EmbeddingService 和 VectorStoreService 的完整单元测试代码。

核心交付：
1. `tests/conftest.py` — pytest 共享 fixture（embedding_service / vector_store_service 实例）
2. `tests/test_embedding.py` — EmbeddingService 测试（本地模型、API 连接、异常处理）
3. `tests/test_vector_store.py` — VectorStoreService 测试（CRUD、检索、过滤）

## 影响范围

| 层级 | 涉及模块 |
|------|---------|
| python_ai_service | tests/conftest.py（新增：共享 fixture） |
| python_ai_service | tests/test_embedding.py（新增：17+ 测试用例） |
| python_ai_service | tests/test_vector_store.py（新增：10+ 测试用例） |

## 核心测试要求

### conftest.py Fixture 设计
- `embedding_service` fixture：function 级别，加载本地 `bge-large-zh-v1.5`（无 API 依赖），CPU 模式
- `vector_store_service` fixture：function 级别，使用 `tmp_path` 临时目录，teardown 调用 `close()`

### TestEmbeddingService (test_embedding.py)
| 测试类 | 测试用例 | 覆盖场景 |
|--------|---------|---------|
| `TestEmbeddingServiceInit` | 初始状态（dimension=768 / initializing / model=None）、加载本地模型 | normal_flow |
| `TestEmbeddingServiceLocal` | encode 单条/列表、encode_batch 分批、维度 768、L2 范数 ≈ 1.0 | normal / boundary |
| `TestEmbeddingServiceAPI` | API 连接、encode、批量性能（条件 skip） | normal / degradation|
| `TestEmbeddingServiceError` | 未加载 encode 抛异常、无效路径异常 | error_flow |

### TestVectorStoreService (test_vector_store.py)
| 测试类 | 测试用例 | 覆盖场景 |
|--------|---------|---------|
| `TestVectorStoreInit` | initialize 连接、collection name、空 count | normal_flow |
| `TestVectorStoreCRUD` | add/count/delete/add_after_delete、参数长度不一致异常 | normal / error |
| `TestVectorStoreSearch` | search basic、score 范围、year 过滤、venue 过滤、空结果 | normal / boundary |

### 关键约束
- 测试 VectorStore 必须使用 `tmp_path` 临时目录，**禁止污染** `data/vector_db/`
- 禁止硬编码 `DASHSCOPE_API_KEY`；API 测试使用 `pytest.mark.skipif` 优雅跳过
- fixture 使用 `function` 级别确保测试隔离
- 所有 async 测试函数加 `@pytest.mark.asyncio`

## 文件清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | `Veritas/ai-service/tests/conftest.py` | pytest fixture 配置 |
| 新增 | `Veritas/ai-service/tests/test_embedding.py` | EmbeddingService 单元测试 |
| 新增 | `Veritas/ai-service/tests/test_vector_store.py` | VectorStoreService 单元测试 |

## 验收标准
- [ ] `conftest.py` 提供 `embedding_service` 和 `vector_store_service` 两个独立 fixture
- [ ] `test_embedding.py` 覆盖：初始化 / 本地模型 encode / API 连接(条件) / 异常处理
- [ ] `test_vector_store.py` 覆盖：初始化 / CRUD / 检索过滤 / 空边界
- [ ] `pytest tests/test_embedding.py -v` 全部通过或 skip（无 FAILED）
- [ ] `pytest tests/test_vector_store.py -v` 全部通过
- [ ] 测试间互不干扰，临时目录自动清理
- [ ] 无硬编码 API Key / 密码等敏感信息