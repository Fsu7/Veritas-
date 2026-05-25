# Embedding与VectorStore服务开发

## 功能描述
- 解决了AI服务层缺少文本向量化和向量数据库服务的问题，实现了从文本到语义检索的完整基础设施
- 实现了EmbeddingService（阿里云百炼API优先 + 本地bge-large-zh-v1.5降级）和VectorStoreService（ChromaDB PersistentClient + papers collection）
- 完成了pytest单元测试覆盖（24个测试全部通过），以及全项目文档中向量维度从768→1024的修正
- 业务价值：为后续RAG检索、多Agent协同分析提供了核心的向量化与存储能力

## 实现逻辑

### 修改的核心文件列表

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 修改 | `app/core/config.py` | 新增DASHSCOPE_API_KEY/DASHSCOPE_EMBEDDING_MODEL/DASHSCOPE_EMBEDDING_BASE_URL三个配置项 |
| 新建 | `app/services/embedding_service.py` | EmbeddingService完整实现：两级策略(API优先→本地降级) |
| 新建 | `app/services/vector_store_service.py` | VectorStoreService完整实现：PersistentClient + HNSW |
| 修改 | `app/core/events.py` | 启动时加载EmbeddingService和VectorStoreService，关闭时释放资源 |
| 修改 | `app/main.py` | /health返回真实embedding和chroma状态 |
| 修改 | `.env.example` | 新增阿里云百炼配置区域 |
| 新建 | `tests/conftest.py` | pytest共享fixture |
| 新建 | `tests/test_embedding.py` | EmbeddingService单元测试(12个) |
| 新建 | `tests/test_vector_store.py` | VectorStoreService单元测试(12个) |

### 使用的算法或设计模式

1. **两级降级策略**：EmbeddingService优先使用阿里云百炼text-embedding-v4 API，失败后降级到本地bge-large-zh-v1.5模型
2. **HNSW近似最近邻索引**：ChromaDB使用HNSW算法(cosine/M=16/construction_ef=200)实现高效向量检索
3. **score转换**：ChromaDB返回cosine距离(0-2)，转换为相似度score=1-distance(范围0-1)
4. **元数据过滤**：search()支持yearFrom($gte)/yearTo($lte)/venue($eq)条件，多条件用$and组合
5. **异步包装**：本地模型encode()使用run_in_executor避免阻塞事件循环

### 关键代码逻辑说明

**EmbeddingService.load_model()**：
- 检测DASHSCOPE_API_KEY非空→初始化AsyncOpenAI客户端→测试连接→status='loaded_api'
- API失败或Key为空→加载本地SentenceTransformer→status='loaded_local'
- 都失败→status='error', raise RuntimeError

**VectorStoreService.search()**：
- 构建where_filter：解析filters中的yearFrom/yearTo/venue
- 调用collection.query(query_embeddings, n_results, where, include)
- 格式化结果：score=1-distance，返回[{paperId,title,abstract,score,year,venue}]

## 接口变更

### Request — EmbeddingService

```python
# 加载模型
await embedding_service.load_model()

# 单条向量化
embedding = await embedding_service.encode("测试文本")  # → np.ndarray (1024,)

# 批量向量化
embeddings = await embedding_service.encode_batch(["文本1", "文本2", ...], batch_size=32)  # → np.ndarray (N, 1024)
```

### Request — VectorStoreService

```python
# 初始化
await vector_store_service.initialize()

# 添加论文
await vector_store_service.add_papers(
    paper_ids=["arxiv_2024_001"],
    embeddings=[[0.1, 0.2, ...]],  # 1024维
    metadatas=[{"paper_id": "arxiv_2024_001", "title": "...", "year": 2024, "venue": "ACL"}],
    documents=["标题+摘要文本"]
)

# 语义检索
results = await vector_store_service.search(
    embedding=[0.1, 0.2, ...],  # 1024维查询向量
    top_k=10,
    filters={"yearFrom": 2022, "yearTo": 2024, "venue": "ACL"}
)

# 删除论文
await vector_store_service.delete_papers(["arxiv_2024_001"])

# 计数
count = await vector_store_service.count()

# 关闭
await vector_store_service.close()
```

### Response — /health

```json
{
    "status": "UP",
    "timestamp": "2026-05-25T...",
    "llm": "not_loaded",
    "embedding": "loaded_api",
    "chroma": "connected"
}
```

## 测试结果

- **EmbeddingService初始化测试**：初始状态(dimension=1024, status='initializing') ✅
- **本地模型加载测试**：load_model后status='loaded_local', model非空 ✅
- **encode单条测试**：返回shape=(1024,)的float32数组 ✅
- **encode多条测试**：返回shape=(3, 1024) ✅
- **encode_batch分批测试**：10条文本batch_size=3，返回shape=(10, 1024) ✅
- **向量归一化测试**：L2范数≈1.0(容差0.01) ✅
- **阿里云百炼API测试**：DASHSCOPE_API_KEY设置后，API连接、encode、encode_batch全部通过 ✅
- **未加载模型encode异常**：抛出ModelNotLoadedException(code=503) ✅
- **无效路径load_model异常**：抛出RuntimeError，status='error' ✅
- **VectorStore初始化测试**：status='connected', collection.name='papers', count=0 ✅
- **add_papers + count测试**：添加3条→count=3 ✅
- **参数长度不一致测试**：raise ValueError ✅
- **delete_papers测试**：删除1条→count=2 ✅
- **search基本检索测试**：自身最相似score>0.9 ✅
- **search年份过滤测试**：yearFrom=2021,yearTo=2023仅返回2022年论文 ✅
- **search venue过滤测试**：venue='ACL'仅返回ACL论文 ✅
- **空collection搜索测试**：返回空列表 ✅

**总计：24 passed, 0 failed** ✅

## 相关文件

### 代码文件
- `Veritas/ai-service/app/core/config.py` — 新增3个DashScope配置项
- `Veritas/ai-service/app/services/embedding_service.py` — EmbeddingService完整实现
- `Veritas/ai-service/app/services/vector_store_service.py` — VectorStoreService完整实现
- `Veritas/ai-service/app/core/events.py` — 启动/关闭生命周期管理
- `Veritas/ai-service/app/main.py` — /health动态状态
- `Veritas/ai-service/tests/conftest.py` — pytest fixture
- `Veritas/ai-service/tests/test_embedding.py` — EmbeddingService测试
- `Veritas/ai-service/tests/test_vector_store.py` — VectorStoreService测试

### 配置文件变更
- `.env.example` — 新增阿里云百炼配置区域
- `requirements.txt` — 已含chromadb==0.5.0, sentence-transformers等依赖

### 文档修正（768维→1024维）
- `AGENTS.md` — 4处
- `AI服务模块系统架构文档.md` — 11处
- `AI服务模块项目里程碑文档.md` — 4处
- `数据库设计文档.md` — 7处
- `需求规格说明书.md` — 5处
- `信息架构文档.md` — 7处
- `项目里程碑文档.md` — 3处
- `版本里程碑功能清单.md` — 3处
- `项目模块功能与联系文档.md` — 3处
- `README.md`(项目根) — 4处
- 其他文档若干
