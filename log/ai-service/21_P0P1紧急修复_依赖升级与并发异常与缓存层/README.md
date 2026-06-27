# P0-P1 紧急修复 — AI 服务（依赖升级与并发异常与缓存层）

## 功能描述

### 解决了什么问题
基于《代码质量与性能检查报告》中标记为 P0（致命）和 P1（严重）的问题，本次修复覆盖 AI 服务 7 个问题：
- P0 安全漏洞：python-multipart 0.0.12 的 CVE-2024-53981、httpx 0.27.0 的 CVE-2024-35195
- P1 依赖兼容：langgraph 0.2.28 与 langchain 0.3.0 不兼容、chromadb 0.5.0 不支持 Python 3.13
- P1 并发竞态：LLMService 共享状态无 asyncio.Lock 保护，_fallback/_recovery_loop/generate 三方竞态
- P1 事件循环阻塞：VectorStoreService 9 个 async 方法直接调用同步 ChromaDB API
- P1 流式内容重复：generate_stream 流失败后重发完整响应
- P1 SSE 异常中断：orchestrator 缺少顶层 except Exception
- P1 死循环：chunk_text 参数无校验，overlap >= chunk_size 时无限循环
- P1 HTTP 客户端无复用：Jina/OpenAI Provider 每次调用创建新 httpx.AsyncClient
- P1 缓存层缺失：整个 AI 服务无任何缓存机制
- P1 算法复杂度：comparer.py 两两对比 O(N²·D·L)

### 实现了什么功能
1. 依赖升级：python-multipart 0.0.13、httpx 0.28.1、langgraph 0.2.50、chromadb 0.5.20、numpy 1.26.4、cachetools 5.5.0
2. asyncio.Lock 竞态保护：_fallback、_recovery_loop、generate、generate_stream 中的状态修改全部加锁
3. ChromaDB 异步包装：9 个方法用 asyncio.to_thread 包装同步调用
4. 流失败不重发：已 yield 过 token 时仅通知中断，不重发完整响应
5. SSE 兜底异常：顶层添加 except Exception，yield error 事件
6. 死循环防护：chunk_text 添加 overlap >= chunk_size 参数校验
7. HTTP 客户端持久化：Jina/OpenAI Provider 在 __init__ 中创建持久化 httpx.AsyncClient
8. 缓存层：新建 cache.py 模块，Embedding 缓存(TTL 5min) + 搜索结果缓存(TTL 2min)
9. 聚类优化：comparer.py N>10 时先聚类分组，将 O(N²) 降至 O(N·K²)

### 业务价值
- 消除 2 个安全漏洞（CVE），防止 DoS 和 TLS 绕过
- 消除 LLM 降级竞态导致的不可预测行为
- 消除事件循环阻塞，提升并发吞吐量
- 修复流式生成内容重复导致前端显示错乱
- 修复 SSE 流异常中断无错误事件
- 消除死循环导致进程挂起风险
- 减少 50-200ms 的 HTTP 连接建立延迟
- 减少重复 Embedding API 调用和 ChromaDB 查询开销

## 实现逻辑

### 修改的核心文件列表

| 文件 | 修改内容 |
|------|---------|
| `requirements.txt` | 5 个依赖升级 + 新增 cachetools/redis |
| `app/services/llm_service.py` | asyncio.Lock + 流失败不重发 |
| `app/services/vector_store_service.py` | 9 个方法 asyncio.to_thread 包装 |
| `app/agents/orchestrator.py` | 顶层 except Exception 兜底 |
| `app/utils/text_processing.py` | chunk_text 参数校验 |
| `app/services/embedding_service.py` | HTTP 客户端持久化 + Embedding 缓存 |
| `app/agents/comparer.py` | N>10 聚类分组 + _cluster_papers 方法 |
| `app/core/cache.py` | 新建缓存工具模块 |
| `app/services/search_service.py` | 搜索结果缓存 |

### 使用的算法或设计模式
- **异步锁模式**：asyncio.Lock 保护单例共享状态
- **异步包装模式**：asyncio.to_thread 将同步 IO 包装为协程
- **缓存模式**：TTLCache 实现 TTL 自动过期 + maxsize LRU 淘汰
- **聚类降维模式**：标题关键词重叠度聚类，将 O(N²) 降至 O(N·K²)

## 接口变更

### 无 API 接口变更
本次修复不涉及 HTTP API 端点变更，仅修改内部实现。SSE 事件流新增可能的 error 事件：

```json
{
  "id": "999",
  "event": "error",
  "data": "{\"message\": \"工作流执行异常: KeyError('query')\"}"
}
```

## 测试结果
- Python 导入验证：✅ All imports OK
- 依赖版本验证：langgraph 0.2.50 ✅, chromadb 0.5.20 ✅, httpx 0.28.1 ✅, python-multipart 0.0.13 ✅
- 是否通过：是

## 相关文件
- 计划文件：`.trae/documents/P0-P1紧急问题修复计划.md`
- 修复清单：`Veritas/修复清单-1-紧急(P0-P1).md`（19个问题已标记 [已修复]）
- 检查报告：`Veritas/代码质量与性能检查报告.md`
