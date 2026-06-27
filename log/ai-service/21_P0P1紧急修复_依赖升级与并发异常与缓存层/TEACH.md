# 技术教学文档 — AI 服务 P0-P1 紧急修复

## 开发思路

### 需求分析过程
代码质量检查报告识别出 AI 服务 7 个 P1 问题，涵盖并发竞态、事件循环阻塞、流式内容重复、SSE 异常中断、死循环、HTTP 连接浪费、缓存缺失和算法复杂度。这些问题相互独立但都影响系统稳定性和性能。

### 技术选型考虑

#### asyncio.Lock vs threading.Lock
选择 `asyncio.Lock`：
- LLMService 在单进程 asyncio 事件循环中运行，不需要跨进程锁
- `asyncio.Lock` 是协程级锁，不阻塞事件循环，比 `threading.Lock` 更适合异步场景
- 锁的粒度仅覆盖状态修改（`active_provider` 和 `_degradation_state`），不覆盖网络 IO（`test_connection`），避免不必要的阻塞

#### asyncio.to_thread vs run_in_executor
选择 `asyncio.to_thread`：
- Python 3.9+ 原生支持，API 更简洁
- 不需要获取事件循环引用（`get_event_loop()` 在 3.10+ 已废弃）
- 对于含关键字参数的调用，用 `lambda` 包装

#### TTLCache vs Redis 缓存
选择 `TTLCache`（内存缓存）：
- AI 服务当前无 Redis 依赖（画像 JSON 由 Java 后端写入，Python 只读）
- 缓存需求是短期热点缓存（2-5 分钟），内存方案足够
- 避免引入 Redis 依赖增加部署复杂度

### 遇到的问题及解决方案

#### 问题1：asyncio.to_thread 不支持关键字参数
`asyncio.to_thread(func, *args, **kwargs)` 在 Python 3.9+ 实际上支持 kwargs，但 ChromaDB 的 `collection.query()` 使用了大量关键字参数（`query_embeddings=`, `n_results=`, `where=`, `include=`），直接传递可能导致参数映射问题。
**解决方案**：使用 `lambda` 包装，在 lambda 内部调用：
```python
results = await asyncio.to_thread(
    lambda: self.collection.query(query_embeddings=[embedding], n_results=top_k, ...)
)
```

#### 问题2：LLMService _fallback 中的 test_connection 不应在锁内
`_fallback` 方法需要遍历 provider 列表调用 `test_connection()`（网络 IO），如果放在锁内会阻塞其他协程。
**解决方案**：只在修改 `active_provider` 和 `_degradation_state` 时加锁，`test_connection` 在锁外执行。

#### 问题3：generate_stream 流失败后的降级策略
流失败后如果已 yield 过 token，客户端已收到部分内容。直接重发完整响应会导致"部分 + 完整 = 重复"。
**解决方案**：检查 `first_token_yielded` 标志，如果已 yield 则仅发送中断提示并 return；未 yield 则降级为非流式。

## 实现步骤

1. **批次5 依赖升级**：修改 requirements.txt 5 个版本 + 新增 cachetools
2. **批次6 并发/异常/边界修复**：
   - llm_service.py：__init__ 添加 _state_lock，_fallback/_recovery_loop/generate/generate_stream 加锁，流失败不重发
   - vector_store_service.py：9 个方法添加 asyncio.to_thread
   - orchestrator.py：添加 except Exception 兜底
   - text_processing.py：添加 overlap >= chunk_size 校验
   - embedding_service.py：Jina/OpenAI Provider 持久化 httpx.AsyncClient + close 方法
   - comparer.py：N>10 聚类分组 + _cluster_papers 方法
3. **批次7 缓存层**：
   - 新建 cache.py 模块
   - embedding_service.py encode 方法添加缓存
   - search_service.py search 方法添加缓存

## 解决了什么问题

### 核心问题
1. **LLM 降级竞态**：三个并发路径（请求超时降级、另一个请求超时降级、后台恢复任务）同时修改 `active_provider`，导致降级逻辑互相覆盖
2. **事件循环阻塞**：ChromaDB 的同步 API（C 扩展 + SQLite IO）在 async 函数中直接调用，阻塞整个事件循环
3. **流式内容重复**：`yield full_response` 在已 yield 部分 token 后重发完整内容
4. **SSE 异常静默**：编排代码异常直接冒泡，客户端收到 500 而非 error 事件
5. **死循环**：`overlap >= chunk_size` 时步进为零或负数
6. **HTTP 连接浪费**：每次 embedding 调用创建+销毁 httpx.AsyncClient，浪费 50-200ms
7. **无缓存**：相同查询重复调用 Embedding API 和 ChromaDB 查询

### 解决方案对比
| 问题 | 方案A（未采用） | 方案B（已采用） | 优势 |
|------|----------------|----------------|------|
| 事件循环阻塞 | 改用异步 ChromaDB 客户端 | asyncio.to_thread 包装 | 无需替换 ChromaDB，改动最小 |
| 流失败重发 | 清空已发送内容 | 检查 first_token_yielded 标志 | 不可能"撤回"已发送的 SSE |
| 缓存缺失 | Redis 缓存 | TTLCache 内存缓存 | 无新依赖，部署简单 |
| N² 复杂度 | ML 聚类算法 | 标题关键词重叠聚类 | 无需额外依赖，O(N²)→O(N·K²) |

## 变更内容

### 新增文件
- `app/core/cache.py` — TTLCache 缓存工具模块

### 修改文件
- `requirements.txt` — 5 个依赖升级 + 新增 cachetools/redis
- `app/services/llm_service.py` — asyncio.Lock + 流失败不重发
- `app/services/vector_store_service.py` — 9 个方法 asyncio.to_thread
- `app/agents/orchestrator.py` — except Exception 兜底
- `app/utils/text_processing.py` — 参数校验
- `app/services/embedding_service.py` — HTTP 客户端持久化 + Embedding 缓存
- `app/agents/comparer.py` — 聚类分组
- `app/services/search_service.py` — 搜索结果缓存

### 配置变更
- requirements.txt 依赖版本升级

## 关键技术点

### asyncio.Lock 的正确使用
```python
# 错误：整个方法都加锁，test_connection 网络IO阻塞其他协程
async def _fallback(self):
    async with self._state_lock:
        # test_connection 在锁内 - 错误！
        await provider.test_connection()
        self.active_provider = provider

# 正确：只在状态修改时加锁
async def _fallback(self):
    # test_connection 在锁外
    await provider.test_connection()
    async with self._state_lock:
        self.active_provider = provider
        self._degradation_state["current_provider"] = provider_name
```

### asyncio.to_thread 包装模式
```python
# ChromaDB 的 query 方法有多个关键字参数
results = await asyncio.to_thread(
    lambda: self.collection.query(
        query_embeddings=[embedding],
        n_results=top_k,
        where=where,
        include=["metadatas", "distances", "documents"]
    )
)
```

### TTLCache 缓存模式
```python
from cachetools import TTLCache

# TTL=300秒(5分钟)，maxsize=2000条
_embedding_cache = TTLCache(maxsize=2000, ttl=300)

# 使用
cache_key = hashlib.md5(json.dumps(args).encode()).hexdigest()
cached = _embedding_cache.get(cache_key)
if cached is not None:
    return cached
# ... 计算 embedding ...
_embedding_cache[cache_key] = result
```

### 流失败降级策略
```python
except Exception as e:
    if first_token_yielded:
        # 已发送部分内容，不能重发完整响应
        yield "\n\n[生成中断，已显示部分内容]"
        return
    # 未发送任何内容，可以安全降级为非流式
    await self._fallback()
    full_response = await self.active_provider.generate(prompt, ...)
    yield full_response
```

## 经验总结

### 开发过程中的收获
1. **asyncio.Lock 的粒度**：锁应仅覆盖共享状态修改，不覆盖网络 IO。`test_connection` 在锁外执行，只有 `self.active_provider = provider` 在锁内。
2. **asyncio.to_thread vs run_in_executor**：`to_thread` 是 Python 3.9+ 的现代 API，更简洁。但对于含关键字参数的调用，需要用 lambda 包装。
3. **流式降级的不可逆性**：已 yield 的 token 无法"撤回"，所以流失败后只能通知中断，不能重发完整内容。这是一个容易忽略的边界条件。
4. **TTLCache 的线程安全性**：`cachetools.TTLCache` 不是线程安全的，但在 asyncio 单线程事件循环中是安全的。如果未来引入多线程，需要加锁。

### 踩过的坑及如何避免
1. **chromadb 0.5.0 与 Python 3.13 不兼容**：chromadb 0.5.0 发布早于 Python 3.13，无预编译 wheel。升级到 0.5.20 解决。
2. **langgraph 0.2.28 与 langchain 0.3.0 的隐式不兼容**：langgraph 0.2.28 声明兼容 langchain-core >= 0.2.43，但 0.3.x 的 API 变更未充分测试。升级到 0.2.50 正式声明兼容。
3. **numpy 版本范围约束**：`numpy>=1.26.0,<2.0.0` 导致 pip 可能安装不同版本，无法保证可复现构建。固定为 `numpy==1.26.4`。

### 最佳实践建议
1. 所有单例共享状态必须用 `asyncio.Lock` 保护，锁粒度仅覆盖状态修改
2. 所有同步 IO 在 async 函数中必须用 `asyncio.to_thread` 包装
3. 流式生成器必须有"已发送"标志，失败后不能重发完整内容
4. 顶层异步生成器必须有 `except Exception` 兜底
5. 对外部 API 调用结果实现短期缓存，减少重复调用开销
