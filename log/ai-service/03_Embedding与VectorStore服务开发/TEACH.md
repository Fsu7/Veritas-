# 技术教学文档

## 开发思路

### 需求分析过程

本次开发涉及三个连续任务（Task03/04/05），核心目标是搭建AI服务的向量化基础设施：

1. **Task03**：需要一个EmbeddingService，能将文本转为向量。要求优先使用阿里云百炼API（成本低、无需本地GPU），备选本地模型（离线可用）
2. **Task04**：需要一个VectorStoreService，能将向量存入ChromaDB并支持语义检索。要求使用PersistentClient持久化、HNSW索引参数精确匹配架构文档
3. **Task05**：需要完整的pytest测试覆盖，确保两个Service在各种场景下行为正确

### 技术选型考虑

| 选型点 | 方案A | 方案B | 最终选择 | 理由 |
|--------|-------|-------|---------|------|
| Embedding API | 阿里云百炼DashScope原生SDK | OpenAI兼容接口 | **OpenAI兼容接口** | 使用openai.AsyncOpenAI客户端，代码更简洁，且与LangChain生态兼容 |
| 本地模型加载 | 直接用transformers | SentenceTransformer | **SentenceTransformer** | 封装了encode+normalize，API更简洁，一行代码完成向量化 |
| ChromaDB客户端 | EphemeralClient(内存) | PersistentClient(磁盘) | **PersistentClient** | 数据持久化，服务重启后数据不丢失 |
| 异步策略 | 全async | CPU密集用run_in_executor | **混合策略** | I/O操作用async/await，CPU密集的encode用executor包装 |

### 架构设计思路

```
EmbeddingService (两级降级)
├── API模式: openai.AsyncOpenAI → text-embedding-v4 → 1024维
└── 本地模式: SentenceTransformer → bge-large-zh-v1.5 → 1024维

VectorStoreService (ChromaDB封装)
├── initialize(): PersistentClient + get_or_create_collection
├── add_papers(): 批量写入 + 参数长度校验
├── search(): where过滤 + score=1-distance转换
├── delete_papers(): 幂等删除
├── count(): 向量计数
└── close(): 资源释放
```

### 遇到的问题及解决方案

**问题1：向量维度文档与实际不符**
- 文档声明768维，但bge-large-zh-v1.5实际输出1024维，text-embedding-v4也是1024维
- 解决：将全项目文档中的768维统一修正为1024维（涉及14+个文件、62+处修改）
- 教训：技术文档中的模型参数必须以实际测试为准，不能盲目引用

**问题2：pytest-asyncio版本兼容性**
- requirements.txt声明pytest-asyncio==0.23.0，但实际安装的是1.3.0
- 1.3.0要求异步fixture使用`@pytest_asyncio.fixture`而非`@pytest.fixture`
- 解决：conftest.py中使用`pytest_asyncio.fixture`装饰器

**问题3：ChromaDB cosine距离转相似度**
- ChromaDB返回的是cosine距离(0-2)，不是相似度
- 随机单位向量间的cosine距离可能>1，导致score=1-distance为负值
- 解决：测试中用自身向量查询自身（距离≈0，score≈1.0），避免随机向量导致的边界问题

**问题4：API模式encode单条返回shape不一致**
- 本地模型encode("文本")返回(1024,)，API模式返回(1,1024)
- 解决：_encode_via_api中检测is_single输入，单条时squeeze到1维

## 实现步骤

1. **Step 03-1**：修改config.py，新增DASHSCOPE_API_KEY/DASHSCOPE_EMBEDDING_MODEL/DASHSCOPE_EMBEDDING_BASE_URL三个配置项
2. **Step 03-2**：创建embedding_service.py，实现EmbeddingService（两级降级策略、encode/encode_batch/_encode_via_api）
3. **Step 03-3**：修改events.py，启动时加载EmbeddingService
4. **Step 03-4**：修改main.py，/health返回真实embedding状态
5. **Step 03-5**：修改.env.example，新增阿里云百炼配置区域
6. **Step 04-1**：创建vector_store_service.py，实现VectorStoreService（PersistentClient、HNSW、add/search/delete/count/close）
7. **Step 04-2**：修改events.py，启动时初始化VectorStoreService
8. **Step 04-3**：修改main.py，/health返回真实chroma状态
9. **Step 05-1**：创建conftest.py，定义embedding_service和vector_store_service fixture
10. **Step 05-2**：创建test_embedding.py，12个EmbeddingService测试
11. **Step 05-3**：创建test_vector_store.py，12个VectorStoreService测试
12. **维度修正**：将全项目文档中768维→1024维（14+文件，62+处）

## 解决了什么问题

### 核心问题描述

AI服务层缺少文本向量化和向量存储能力，无法支持后续的RAG检索和多Agent协同分析。具体问题：
1. 没有Embedding服务，无法将用户查询和论文文本转为语义向量
2. 没有向量数据库服务，无法存储和检索论文向量
3. /health接口返回硬编码状态，无法反映真实服务状态
4. 项目文档中向量维度信息错误（768维 vs 实际1024维）

### 解决方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| 仅API模式 | 速度快、无需本地资源 | 依赖网络、有API成本 |
| 仅本地模型 | 离线可用、无API成本 | 需要下载模型(~1.3GB)、CPU推理慢 |
| **API优先+本地降级** | 兼顾速度和可用性 | 代码复杂度略高 |

### 最终方案的优势

1. **高可用**：API不可用时自动降级到本地模型，服务不中断
2. **成本优化**：优先使用API（按量计费），避免本地模型推理的CPU开销
3. **数据持久化**：PersistentClient确保向量数据落盘，重启不丢失
4. **精确检索**：HNSW参数(cosine/M=16/ef=200)与架构文档严格一致

## 变更内容

### 新增文件
- `app/services/embedding_service.py` — EmbeddingService文本向量化服务（两级降级策略）
- `app/services/vector_store_service.py` — VectorStoreService向量数据库服务（ChromaDB封装）
- `tests/conftest.py` — pytest全局fixture配置
- `tests/test_embedding.py` — EmbeddingService单元测试（12个测试用例）
- `tests/test_vector_store.py` — VectorStoreService单元测试（12个测试用例）

### 修改文件
- `app/core/config.py` — 新增3个DashScope配置项
- `app/core/events.py` — 启动时加载EmbeddingService和VectorStoreService，关闭时释放资源
- `app/main.py` — /health动态返回embedding和chroma状态
- `.env.example` — 新增阿里云百炼配置区域

### 配置变更
| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| DASHSCOPE_API_KEY | str | "" | 阿里云百炼API Key |
| DASHSCOPE_EMBEDDING_MODEL | str | "text-embedding-v4" | 百炼Embedding模型名 |
| DASHSCOPE_EMBEDDING_BASE_URL | str | "https://dashscope.aliyuncs.com/compatible-mode/v1" | API端点 |

## 关键技术点

### 1. OpenAI兼容接口调用阿里云百炼

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key="sk-xxx",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
response = await client.embeddings.create(model="text-embedding-v4", input=["文本"])
embedding = response.data[0].embedding  # 1024维list
```

阿里云百炼提供OpenAI兼容接口，无需使用DashScope原生SDK，直接用openai库即可调用。

### 2. SentenceTransformer本地模型加载与归一化

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-large-zh-v1.5", device="cpu")
embedding = model.encode("文本", normalize_embeddings=True)  # L2归一化
```

`normalize_embeddings=True`使输出向量的L2范数为1，与cosine相似度计算兼容。

### 3. ChromaDB HNSW参数配置

```python
collection = client.get_or_create_collection(
    name="papers",
    metadata={
        "hnsw:space": "cosine",        # 余弦相似度
        "hnsw:M": 16,                   # HNSW图连接数
        "hnsw:construction_ef": 200,    # 构建时搜索宽度
    },
)
```

M=16平衡了检索精度和内存占用，construction_ef=200确保构建质量。

### 4. 元数据过滤构建

```python
# 单条件: {"year": {"$gte": 2022}}
# 多条件: {"$and": [{"year": {"$gte": 2022}}, {"year": {"$lte": 2024}}, {"venue": {"$eq": "ACL"}}]}
```

ChromaDB的where过滤支持$gte/$lte/$eq等操作符，多条件用$and组合。

### 5. 异步fixture与临时目录隔离

```python
@pytest_asyncio.fixture(scope="function")
async def vector_store_service(tmp_path):
    chroma_dir = str(tmp_path / "chroma_test")
    test_settings = Settings(CHROMA_PATH=chroma_dir)
    svc = VectorStoreService(test_settings)
    await svc.initialize()
    yield svc
    await svc.close()
```

- `scope="function"`确保每个测试独立的数据库实例
- `tmp_path`自动创建临时目录，测试结束自动清理
- 不污染真实data/vector_db/目录

## 经验总结

### 开发过程中的收获

1. **先验证再编码**：在写代码前先确认模型的实际输出维度（bge-large-zh-v1.5=1024维），避免后续大规模修正
2. **两级降级是刚需**：API服务不稳定时本地模型是关键保障，但本地模型首次加载需下载~1.3GB
3. **测试即文档**：精心设计的测试用例（如自身向量查询自身score>0.9）本身就是服务行为的最佳文档

### 踩过的坑及如何避免

1. **坑：文档中的维度信息不可信**
   - 踩坑：项目文档统一写768维，但实际模型输出1024维
   - 避免：开发前先用Python一行代码验证实际维度：`python -c "from sentence_transformers import SentenceTransformer; m=SentenceTransformer('BAAI/bge-large-zh-v1.5'); print(m.get_sentence_embedding_dimension())"`

2. **坑：pytest-asyncio版本差异**
   - 踩坑：requirements.txt声明0.23.0但实际安装1.3.0，API不兼容
   - 避免：在conftest.py中同时导入pytest和pytest_asyncio，使用pytest_asyncio.fixture

3. **坑：ChromaDB cosine距离不是相似度**
   - 踩坑：随机向量间的cosine距离可能>1，score=1-distance可能为负
   - 避免：测试中用自身向量查询自身，或对score范围使用容差断言

4. **坑：API模式encode单条返回2D数组**
   - 踩坑：openai.embeddings.create返回的data是列表，单条输入也返回(1, dim)
   - 避免：在_encode_via_api中检测is_single，单条时squeeze到1维

### 最佳实践建议

1. **Embedding维度动态获取**：不要硬编码维度，使用`model.get_sentence_embedding_dimension()`动态获取
2. **API Key脱敏日志**：日志中只输出Key前4位+****，如`sk-6577****`
3. **测试使用tmp_path**：永远不要在测试中操作真实数据目录
4. **API测试条件执行**：使用`pytest.mark.skipif`，无API Key时优雅跳过
5. **events.py延迟导入**：Service在on_startup中导入和初始化，避免模块级导入时的循环依赖
