# P2 常规修复 — AI 服务（算法优化与异常处理与防御性编程）

## 功能描述
- **解决的问题**：修复了 P2 级别的 10 项 Python AI 服务代码质量问题，包括算法复杂度优化、线程泄漏、异常处理缺陷、类型假设、防御性校验缺失
- **实现的功能**：
  - `_tokenize_query` 去重从 List O(n) 改为 Set O(1)，整体复杂度 O(T²)→O(T)
  - 删除旧关键词检索路径（逐关键词 N+1 查询），统一走 `$or` 单次查询
  - LocalLLMProvider 线程改 daemon + finally join，修复 SSE 断开时线程泄漏
  - asyncio.gather 添加 `return_exceptions=True` 兜底防护（search_service + analyzer）
  - 搜索降级增加计数器 + 双空警告日志，不再双重静默失败
  - `update_paper_metadata` 移除 try/catch，让异常自然传播
  - embedding fallback 保留 `last_error`，异常消息不再用错
  - reranker year/citation_count 添加类型转换守卫，防止 TypeError
  - reviewer fact_check 添加 `isinstance(item, dict)` 守卫 + 统一默认值
  - ChromaDB 返回数组添加防御性校验，防 KeyError/IndexError
- **业务价值**：提升 AI 服务稳定性、可观测性和类型安全性，减少因边界数据导致的静默降级和崩溃

## 实现逻辑
- **修改的核心文件**：
  - `app/services/search_service.py` — 去重优化 + gather 兜底 + 降级日志
  - `app/services/vector_store_service.py` — 旧路径删除 + re-raise + 防御性校验
  - `app/services/llm_service.py` — 线程泄漏修复
  - `app/services/embedding_service.py` — fallback last_error
  - `app/services/reranker.py` — 类型转换守卫
  - `app/agents/reviewer.py` — isinstance 守卫 + 默认值统一
  - `app/agents/analyzer.py` — gather return_exceptions
- **设计模式**：
  - 防御性编程（isinstance 守卫、类型转换 try/except、数组长度校验）
  - 降级计数器模式（不改签名，用日志+计数器记录降级事件）
  - daemon 线程 + finally join 模式（资源释放保证）

## 测试结果
- Python 语法检查：7 个文件全部通过 `ast.parse`
- 代码模式验证：Grep 确认所有修复点存在（seen_tokens 9 处、daemon=True 2 处、return_exceptions 3 处等）
- 是否通过：是

## 相关文件
- `ai-service/app/services/search_service.py`
- `ai-service/app/services/vector_store_service.py`
- `ai-service/app/services/llm_service.py`
- `ai-service/app/services/embedding_service.py`
- `ai-service/app/services/reranker.py`
- `ai-service/app/agents/reviewer.py`
- `ai-service/app/agents/analyzer.py`
- `ai-service/requirements.txt`（numpy 固定 + redis 添加）
