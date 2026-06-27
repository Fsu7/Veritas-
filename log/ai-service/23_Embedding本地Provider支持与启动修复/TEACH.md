# 技术教学文档

## 开发思路

### 需求分析过程
项目启动时发现 AI 服务 EmbeddingService 仅支持三种 API Provider（DashScope/Jina/OpenAI），没有本地 SentenceTransformer 模型的支持路径。启动时因无 API Key 配置导致 Embedding 服务不可用，系统处于 DEGRADED 模式。同时缺少 `sse-starlette` 依赖导致服务无法启动。

### 技术选型考虑
- 本地 Embedding 模型选择 `BAAI/bge-m3`（1024维），与现有 ChromaDB 中的预存向量维度对齐
- 采用 Provider 架构模式，新增 `LocalSentenceTransformerProvider` 与现有 API Provider 并列，不破坏原有架构
- 懒加载策略：仅在 `EMBEDDING_PROVIDER=local` 时才触发模型下载和加载，避免服务启动阻塞

### 架构设计思路
```
BaseEmbeddingProvider (抽象基类)
    ├── DashScopeProvider  (阿里云百炼 API)
    ├── JinaProvider       (Jina AI API)
    ├── OpenAIProvider     (OpenAI API)
    └── LocalSentenceTransformerProvider  ← 新增
```

Provider 注册表 `PROVIDER_CLASSES` 中添加 `"local"` 映射，`load_model()` 方法统一遍历所有 Provider 的 `is_available()` 判断可用性。

### 遇到的问题及解决方案

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `ModuleNotFoundError: sse_starlette` | 依赖未安装 | `pip install sse-starlette` |
| bge-m3 模型下载阻塞启动（2.27GB） | `SentenceTransformer.__init__()` 同步下载 | 实现 `_should_load` 标志 + 懒加载 `is_available()` |
| `_load_local_model` 返回类型注解报错 | `"SentenceTransformer"` 在模块顶部未导入 | 移除返回类型注解 |
| Embedding provider 配置不匹配 | `.env` 中 `EMBEDDING_PROVIDER=local` 但代码无此分支 | 新增 LocalSentenceTransformerProvider 并注册 |

## 实现步骤

1. **安装缺失依赖**：`pip install sse-starlette sentence-transformers`
2. **新增 LocalSentenceTransformerProvider 类**：继承 `BaseEmbeddingProvider`，实现 `embed_query` / `embed_documents`，使用 `asyncio.get_running_loop().run_in_executor()` 异步执行模型推理
3. **实现懒加载机制**：`_should_load` 标志仅在 `EMBEDDING_PROVIDER=local` 时为 True，`is_available()` 首次调用时触发模型加载
4. **注册到 PROVIDER_CLASSES**：添加 `"local": LocalSentenceTransformerProvider` 映射
5. **更新状态日志**：`loaded_local` 状态区分本地模型与 API 模型，masked_key 显示模型路径
6. **修复类型注解**：移除 `_load_local_model` 的 `"SentenceTransformer"` 返回类型注解
7. **配置 .env**：设置 DeepSeek API Key、LLM 超时参数、Agent 超时参数

## 解决了什么问题

### 核心问题
AI 服务无法启动或启动后 Embedding 不可用，导致语义检索功能完全丧失。

### 解决方案对比
| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| 配置 DashScope API Key | 快速、无需下载 | 需付费、外部依赖 | ✗ |
| 安装本地 bge-m3 模型 | 免费、离线可用 | 2.27GB下载、启动慢 | ✓ |
| 禁用 Embedding 降级运行 | 即时可用 | 语义检索不可用 | 临时方案 |

### 最终方案的优势
- Provider 架构保持一致，本地模型与 API 模型统一接口
- 懒加载避免服务启动阻塞，模型在首次实际使用时才加载
- 降级链完整：local → dashscope → jina → openai

## 变更内容

### 新增文件
- `ai-service/.env` — AI 服务环境变量配置（DeepSeek API Key、LLM/Agent 超时参数）

### 修改文件
- `ai-service/app/services/embedding_service.py`
  - 新增 `LocalSentenceTransformerProvider` 类（约 40 行）
  - `PROVIDER_CLASSES` 添加 `"local"` 映射
  - `load_model()` 状态日志添加 `loaded_local` 分支和 `masked_key` 本地模型路径显示
  - `_load_local_model` 移除返回类型注解

## 关键技术点

### 懒加载 Provider 模式
```python
def __init__(self, settings):
    self._should_load = getattr(settings, "EMBEDDING_PROVIDER", "") == "local"
    if self._should_load:
        self._try_load_model()  # 仅在配置为 local 时才加载

def is_available(self) -> bool:
    if not self._should_load:
        return False  # 非 local 配置直接返回 False，不触发加载
    if not self._loaded:
        self._try_load_model()  # 首次调用时懒加载
    return self._model is not None
```

### 异步推理
SentenceTransformer 的 `encode()` 是同步阻塞操作，通过 `run_in_executor` 放到线程池执行，不阻塞事件循环：
```python
async def embed_query(self, text: str) -> np.ndarray:
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: self._model.encode(text, normalize_embeddings=True),
    )
    return np.array(result, dtype=np.float32)
```

## 经验总结

### 开发过程中的收获
- Provider 架构的扩展性优势：新增 Provider 只需实现接口 + 注册，不修改现有代码
- 懒加载模式有效解决了大模型下载阻塞服务启动的问题

### 踩过的坑及如何避免
- `SentenceTransformer.__init__()` 会同步从 HuggingFace 下载模型（2.27GB），如果在 `load_model()` 中直接调用会导致服务启动超时。通过 `_should_load` 标志控制加载时机
- Python 类型注解中的字符串引用（如 `"SentenceTransformer"`）需要对应类型在模块顶部导入，否则类型检查器报 Undefined name

### 最佳实践建议
- 新增 Provider 时始终实现懒加载标志，避免不必要的资源初始化
- `.env` 文件不应提交到版本控制，仅提交 `.env.example` 模板
