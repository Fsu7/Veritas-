# task04 — ChromaDB初始化 + VectorStoreService

## 项目
XH-202630 科研文献智能助手 — v0.1 M1：基础设施就绪 / AM1：项目骨架与模型层就绪

## 需求概述
实现 ChromaDB 向量数据库初始化与 VectorStoreService 向量存储服务。

核心交付：
1. `services/vector_store_service.py` — VectorStoreService（PersistentClient 连接、papers collection 管理、向量增删查）
2. `events.py` 启动时初始化 VectorStoreService，关闭时清理
3. `main.py` /health 返回真实 chroma 状态

## 影响范围

| 层级 | 涉及模块 |
|------|---------|
| python_ai_service | app/services/vector_store_service.py（新增） |
| python_ai_service | app/core/events.py（修改：初始化 + 关闭） |
| python_ai_service | app/main.py（修改：health 状态） |

## 核心实现要求

### VectorStoreService
- **存储引擎**：`chromadb.PersistentClient(path=CHROMA_PATH)`，禁止 EphemeralClient
- **HNSW 索引参数**：`cosine` 相似度、`M=16`、`construction_ef=200`
- **Collection**：`papers`（自动创建）

关键方法：`initialize()` / `add_papers()` / `search()` / `delete_papers()` / `count()` / `close()`

### search() 关键细节
- `score = 1 - distance`（cosine 距离 → 相似度，范围 0-1，越大越相似）
- 支持 `filters` 元数据过滤（yearFrom / yearTo / venue）
- ChromaDB `where` 条件：`$gte` / `$lte` / `$eq`，多条件用 `$and` 组合

### 关键约束
- 必须使用 `PersistentClient`（持久化），禁止 `EphemeralClient`（内存模式）
- `add_papers()` 参数长度必须一致，不一致抛 `ValueError`
- `initialize()` 失败时设置 `status='error'` 并抛 `VectorStoreException`

## 文件清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | `Veritas/ai-service/app/services/vector_store_service.py` | VectorStoreService 实现 |
| 修改 | `Veritas/ai-service/app/core/events.py` | 启动初始化 + 关闭清理 |
| 修改 | `Veritas/ai-service/app/main.py` | /health 返回真实 chroma 状态 |

## 验收标准
- [ ] 使用 `chromadb.PersistentClient`，路径读取 `settings.CHROMA_PATH`
- [ ] papers collection：`cosine` / `M=16` / `construction_ef=200`
- [ ] `add_papers()` 批量写入，参数长度校验
- [ ] `search()` 返回 `[{paperId,title,abstract,score,year,venue},...]`，score 范围 0-1
- [ ] `search()` 支持 `filters`（yearFrom / yearTo / venue）
- [ ] `delete_papers()` 后 count 减少，search 不再返回
- [ ] `count()` 空 collection 返回 0
- [ ] `/health` chroma 字段动态返回真实状态
- [ ] `initialize` 失败时 status='error' 并抛出异常