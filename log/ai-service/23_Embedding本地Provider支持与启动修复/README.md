# Embedding 本地 Provider 支持与 AI 服务启动修复

## 功能描述
- 解决了 AI 服务启动时因缺少 Embedding API Key 导致 EmbeddingService 不可用的问题
- 新增 `LocalSentenceTransformerProvider` 本地模型 Provider，支持 bge-m3 等 SentenceTransformer 模型
- 配置懒加载机制，避免非 local 模式下不必要的模型加载
- 修复 `_load_local_model` 类型注解 `SentenceTransformer` 未定义的 lint 错误
- 创建 `.env` 配置文件，配置 DeepSeek API 作为 LLM Provider

## 实现逻辑
- 修改的核心文件列表：
  - `app/services/embedding_service.py` — 新增 LocalSentenceTransformerProvider 类 + 注册到 PROVIDER_CLASSES
  - `ai-service/.env` — 新建环境配置文件

- 使用的算法或设计模式：
  - **多 Provider 架构**：BaseEmbeddingProvider 抽象基类 + 多个具体 Provider（DashScope/Jina/OpenAI/Local），支持主 Provider + 降级链
  - **懒加载模式**：LocalSentenceTransformerProvider 仅在 `EMBEDDING_PROVIDER=local` 时才加载模型，避免启动阻塞
  - **is_available() 双重检查**：先检查 `_should_load` 标志，再触发懒加载

- 关键代码逻辑说明：
  - `LocalSentenceTransformerProvider.__init__`：读取 `settings.EMBEDDING_PROVIDER`，仅当值为 `"local"` 时调用 `_try_load_model()`
  - `_try_load_model()`：从 HuggingFace 下载并加载 SentenceTransformer 模型（bge-m3，1024维）
  - `is_available()`：先检查 `_should_load`，若为 False 直接返回 False；若为 True 且未加载则触发懒加载
  - `embed_query/embed_documents`：通过 `asyncio.get_running_loop().run_in_executor()` 在线程池中执行模型推理，避免阻塞事件循环

## 接口变更
本次修改不涉及 API 接口变更，仅影响 EmbeddingService 内部初始化逻辑。

### 请求示例（健康检查）
```
GET /health
```

### 响应示例
```json
{
  "code": 200,
  "message": "DEGRADED",
  "data": {
    "llm": "loaded",
    "embedding": "disabled",
    "chroma": "connected",
    "prompts": "loaded",
    "searchService": "ready",
    "reranker": "ready",
    "status": "DEGRADED"
  }
}
```

## 测试结果
- 测试场景1：AI 服务启动（EMBEDDING_PROVIDER=dashscope，无 API Key）→ DEGRADED 模式启动成功，LLM 可用，ChromaDB 30 篇论文已加载
- 测试场景2：AI 服务启动（EMBEDDING_PROVIDER=local）→ 触发 bge-m3 模型下载（2.27GB），加载完成后 embedding 可用
- 测试场景3：`_load_local_model` 类型注解移除后 lint 错误消除
- 是否通过：是

## 相关文件
- `Veritas/ai-service/app/services/embedding_service.py` — 新增 LocalSentenceTransformerProvider 类（约40行），更新 PROVIDER_CLASSES 注册表，更新 masked_key 日志
- `Veritas/ai-service/.env` — 新建配置文件，配置 DeepSeek API + LLM/Agent 超时参数
