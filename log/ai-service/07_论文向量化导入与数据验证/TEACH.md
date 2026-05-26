# 技术教学文档

## 开发思路

### 需求分析过程
本次开发对应M2里程碑的两个任务：
- **Task10（论文向量化导入）**：需要将论文数据从arXiv API采集，经过清洗、分块、向量化后批量写入ChromaDB
- **Task11（论文数据验证）**：需要对已入库的数据进行完整性验证，并提供向量库构建脚本

核心挑战在于：
1. arXiv API可能限流或超时，需要重试机制
2. 大批量数据（200+篇）需要分批处理避免OOM
3. 文本分块质量直接影响RAG检索效果
4. DashScope API向量化有调用频率限制

### 技术选型考虑
| 选型点 | 方案 | 理由 |
|--------|------|------|
| arXiv数据源 | `arxiv` Python库 | 官方推荐，支持分类搜索和排序 |
| 向量化 | DashScope API (text-embedding-v4) | 1024维，与bge-m3兼容，无需本地GPU |
| 文本分块 | 滑动窗口（800字/100字重叠） | 平衡检索精度和上下文完整性 |
| 批量写入 | 分批50条+sleep限流 | 避免ChromaDB写入OOM和API限流 |
| 验证方式 | 4项独立验证+汇总报告 | 单项失败不阻塞后续验证 |

### 架构设计思路
```
arXiv API / JSON文件
       ↓
  fetch_papers (含重试3次)
       ↓
  clean_papers (去重/格式统一)
       ↓
  chunk_text (800字分块/100字重叠)
       ↓
  encode_batch (DashScope API向量化)
       ↓
  add_papers_batch (分批50条写入ChromaDB)
```

### 遇到的问题及解决方案

#### 问题1：clean_text误删换行符
- **现象**：`re.sub(r"[\x00-\x1f\x7f]", " ", text)` 把 `\n`（0x0a）也替换成了空格
- **解决**：改为 `[\x00-\x09\x0b-\x1f\x7f]`，跳过0x0a（\n）
- **教训**：控制字符范围要精确，不能贪方便用宽范围

#### 问题2：truncate_text截断位置不含句号
- **现象**：`text[:cut_pos]` 在句号位置截断时，句号本身被排除
- **解决**：`cut_pos = cut_pos + 1`，包含截断标点
- **教训**：字符串切片是左闭右开，注意边界

#### 问题3：pytest async测试缺少装饰器
- **现象**：3个async测试报错 "async def functions are not natively supported"
- **解决**：添加 `@pytest.mark.asyncio` 装饰器
- **教训**：pytest-asyncio strict模式下，每个async测试必须显式标记

#### 问题4：200篇论文导入时间过长
- **现象**：DashScope API逐篇调用，200篇预计需要10+分钟
- **解决**：当前脚本逐篇调用encode_batch，可优化为收集所有文本后批量调用
- **状态**：已知限制，后续优化

## 实现步骤

1. **创建text_processing.py**：实现chunk_text/clean_text/truncate_text三个工具函数
2. **扩展VectorStoreService**：新增add_papers_batch/get_paper_by_id/update_paper_metadata三个方法
3. **创建import_papers.py**：实现arXiv API采集+JSON源+CLI参数+重试+dry-run
4. **创建validate_papers.py**：实现4项验证+汇总报告+exit(1)失败
5. **创建build_vector_db.py**：实现rebuild/incremental两种构建模式
6. **创建sample_papers.json**：5篇AI/Agent领域样本数据
7. **编写测试**：test_text_processing(24) + test_import_papers(12) + test_validate_papers(12)
8. **补全VectorStoreService测试**：test_vector_store新增8个测试
9. **修复bug**：clean_text换行/truncate_text句号/pytest async装饰器
10. **全量测试验证**：68个测试全部通过

## 解决了什么问题

### 核心问题描述
M2里程碑需要200+篇论文入库ChromaDB，为RAG语义检索提供数据基础。但此前只有VectorStoreService的基础CRUD，缺少：
- 论文数据采集和清洗能力
- 文本分块和向量化流水线
- 大批量数据分批写入能力
- 数据完整性验证手段

### 解决方案对比

| 方案 | 优点 | 缺点 | 最终选择 |
|------|------|------|---------|
| 单次全量add_papers | 简单 | 大数据量OOM | ❌ |
| 分批add_papers_batch | 内存可控 | 需要限流 | ✅ |
| 逐条add | 最安全 | 极慢 | ❌ |
| EphemeralClient内存模式 | 快 | 数据不持久 | ❌（违反FA-008） |

### 最终方案的优势
1. **分批写入**：batch_size=50，每批间sleep 0.5s，兼顾性能和稳定性
2. **容错机制**：单篇论文失败不阻塞后续，记录failed计数和错误详情
3. **dry-run模式**：调试时不调用embedding和vector_store，节省API费用
4. **双数据源**：arXiv API + 本地JSON，灵活切换
5. **完整验证**：4项验证覆盖向量维度/元数据/去重/检索质量

## 变更内容

### 新增文件
- `app/utils/text_processing.py` — 文本处理工具（分块/清洗/截断）
- `scripts/import_papers.py` — 论文导入脚本（arXiv+JSON+CLI）
- `scripts/validate_papers.py` — 数据验证脚本（4项验证+报告）
- `scripts/build_vector_db.py` — 向量库构建脚本（rebuild/incremental）
- `data/papers/sample_papers.json` — 5篇样本论文
- `tests/test_text_processing.py` — 24个测试
- `tests/test_import_papers.py` — 12个测试
- `tests/test_validate_papers.py` — 12个测试

### 修改文件
- `app/services/vector_store_service.py` — 新增3个方法（add_papers_batch/get_paper_by_id/update_paper_metadata），新增import asyncio
- `tests/test_vector_store.py` — 新增TestVectorStoreBatchAndQuery类（8个测试）
- `tests/test_import_papers.py` — 3个async测试添加@pytest.mark.asyncio装饰器

### 配置变更
- 无新增配置项，复用现有CHROMA_PATH和DASHSCOPE_API_KEY

## 关键技术点

### 1. 文本分块（RAG Chunking）
- **滑动窗口算法**：固定窗口大小(800) + 重叠区域(100)
- **chunk_type标记**：首块`title_abstract`，后续`continuation`，与ChromaDB元数据Schema一致
- **小块合并**：最后一块不足chunk_size的20%时合并到前一块，避免碎片化
- **为什么需要overlap**：防止关键语义在分块边界断裂，100字符重叠确保跨块语义连续

### 2. DashScope API向量化
- **模型**：text-embedding-v4，输出1024维向量，与bge-m3维度一致
- **调用方式**：通过OpenAI兼容接口（AsyncOpenAI），base_url为DashScope端点
- **降级策略**：API失败→本地bge-m3模型兜底
- **限流注意**：DashScope有QPS限制，大批量调用需控制频率

### 3. ChromaDB批量写入
- **HNSW参数**：space=cosine, M=16, construction_ef=200（在initialize时设置）
- **分批策略**：batch_size=50，每批间sleep 0.5s
- **ID格式**：`{paper_id}_chunk_{chunk_index}`，如`arxiv_2401.0001_chunk_0`
- **锁冲突**：PersistentClient和chroma run Server不能同时写入同一目录

### 4. 数据验证4项检查
- **向量维度**：遍历所有embedding验证1024维
- **元数据完整性**：paper_id/title/year非空
- **去重**：从metadata提取paper_id，Counter统计重复
- **检索质量**：预定义3个测试查询，验证Top1相似度>0.5

## 经验总结

### 开发过程中的收获
1. **分块是RAG的核心**：chunk_size和overlap的选择直接影响检索质量，需要根据实际数据调整
2. **批量操作必须限流**：无论是API调用还是DB写入，分批+sleep是基本操作
3. **容错比完美更重要**：单篇失败不阻塞，记录错误继续执行，保证整体可用

### 踩过的坑及如何避免
1. **控制字符正则范围**：`[\x00-\x1f]` 包含了 `\n`(0x0a)，需要精确排除 → 用`[\x00-\x09\x0b-\x1f]`
2. **字符串切片边界**：`text[:cut_pos]` 不包含cut_pos位置的字符 → 需要时+1
3. **pytest-asyncio strict模式**：必须显式标记`@pytest.mark.asyncio` → 全局pytestmark不适用于混合sync/async的测试文件
4. **ChromaDB锁冲突**：PersistentClient和Server不能同时操作同一目录 → 导入时停掉Server

### 最佳实践建议
1. **先dry-run再实际导入**：`--dry-run`模式验证数据质量，再正式导入
2. **导入后立即验证**：运行validate_papers.py确认数据完整性
3. **小批量试跑**：先用`--count 5`验证流程，再扩大到200+
4. **向量库定期重建**：数据量大时用build_vector_db.py --mode rebuild重建索引
5. **监控API费用**：DashScope按调用次数计费，200篇论文约200次API调用
