# 技术教学文档 — P2 常规修复（AI 服务）

## 开发思路
- **需求分析**：根据 P2 修复清单，10 项 Python 代码质量问题分布在 7 个文件中，无跨文件依赖
- **技术选型**：
  - 去重优化用 `set` 而非 `dict.fromkeys()`，保持最小改动
  - 线程泄漏用 `daemon=True` + `finally join(timeout=5)` 而非取消机制
  - 降级静默用计数器而非改签名，避免影响所有调用方
  - gather 兜底用 `return_exceptions=True` + isinstance 过滤
- **架构设计**：所有修复保持原有接口签名不变，仅增强内部实现
- **遇到的问题**：
  - `asyncio.get_event_loop()` 在 Python 3.10+ 已废弃，改用 `get_running_loop()`
  - reviewer 的 `accurate` 默认值在两个方法中矛盾（False vs True），统一为 False（安全侧）

## 实现步骤
1. search_service `_tokenize_query` 增加共享 `seen_tokens: set`，3 处去重改为 set 查找
2. vector_store_service 删除旧关键词路径（行 375-414），入口统一走 `$or` 查询
3. llm_service 线程改 daemon + try/finally 包裹消费循环 + `get_running_loop()`
4. search_service 和 analyzer 的 gather 添加 `return_exceptions=True` + 结果过滤
5. search_service 增加 `_degradation_count` 属性，降级时计数 + 双空警告
6. vector_store `update_paper_metadata` 移除 try/catch，添加 None 检查
7. embedding_service 保留 `last_error = fb_err`，最终异常消息用 last_error
8. reranker 添加 `int(raw_citation)` / `int(raw_year)` + try/except 守卫
9. reviewer 两处添加 `isinstance(item, dict)` 守卫 + 统一默认值 False
10. vector_store search 和 search_by_keywords 添加 `.get()` + 长度校验

## 解决了什么问题
- **O(T²) 去重**：List 线性查找 → Set O(1) 查找
- **线程泄漏**：非 daemon 线程 + join 不在 finally → daemon + finally join
- **异常吞噬**：update_paper_metadata 静默吞异常 → re-raise
- **类型假设**：ChromaDB metadata 字符串值导致 TypeError → int() 守卫
- **默认值矛盾**：reviewer accurate 默认值 False vs True → 统一 False
- **级联静默**：双重 except 返回 [] 无日志 → 降级计数器 + 双空警告

## 变更内容
### 修改文件
- `app/services/search_service.py` — seen_tokens set + gather return_exceptions + 降级计数器
- `app/services/vector_store_service.py` — 旧路径删除 + re-raise + 防御性校验
- `app/services/llm_service.py` — daemon 线程 + finally join + get_running_loop
- `app/services/embedding_service.py` — last_error 保留
- `app/services/reranker.py` — int() 类型转换守卫
- `app/agents/reviewer.py` — isinstance 守卫 + 默认值统一
- `app/agents/analyzer.py` — gather return_exceptions
- `requirements.txt` — numpy==1.26.4 + redis==5.0.0

## 关键技术点
- **Set 去重 vs List 去重**：`not in list` 是 O(n)，`not in set` 是 O(1)，在循环中差异被放大为 O(n²) vs O(n)
- **daemon 线程**：Python 非 daemon 线程会阻止进程退出，SSE 断开时若 join 不在 finally 中会导致线程泄漏
- **return_exceptions=True**：asyncio.gather 默认一个任务失败会取消其他任务，添加此参数后异常作为返回值而非抛出
- **isinstance 守卫**：LLM 返回的 JSON 可能包含非预期类型（字符串、null），对 dict 方法调用前必须做类型检查

## 经验总结
- **防御性编程的边界**：外部输入（LLM JSON、ChromaDB metadata、ChromaDB 返回结构）必须做类型校验，内部代码可信任
- **降级日志 vs 改签名**：当降级路径返回空列表是合理行为时，不改签名、用日志+计数器记录是更好的选择
- **线程资源管理**：异步生成器中的线程资源必须在 finally 中释放，否则客户端断开时泄漏
