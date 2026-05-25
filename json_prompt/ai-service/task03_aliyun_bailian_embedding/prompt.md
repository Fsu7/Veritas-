# task03 — 阿里云百炼API配置 + EmbeddingService

## 项目
XH-202630 科研文献智能助手 — v0.1 M1：基础设施就绪 / AM1：项目骨架与模型层就绪

## 需求概述
实现阿里云百炼 DashScope text-embedding-v4 API 配置与 EmbeddingService 文本向量化服务。

核心交付：
1. `config.py` 新增阿里云百炼 DashScope Embedding 配置项（DASHSCOPE_API_KEY / DASHSCOPE_EMBEDDING_MODEL / DASHSCOPE_EMBEDDING_BASE_URL）
2. `services/embedding_service.py` — 实现 EmbeddingService（API优先 + 本地降级的双向策略）
3. `events.py` 启动时加载 EmbeddingService
4. `.env.example` 添加配置说明
5. `main.py` /health 返回真实 embedding 状态

## 影响范围

| 层级 | 涉及模块 |
|------|---------|
| python_ai_service | app/services/embedding_service.py（新增） |
| python_ai_service | app/core/config.py（修改：新增3个配置项） |
| python_ai_service | app/core/events.py（修改：加载 service） |
| python_ai_service | app/main.py（修改：health 状态） |
| python_ai_service | .env.example（修改：添加配置区域） |

## 核心实现要求

### EmbeddingService 双向策略
1. **第一优先级（API模式）**：配置 `DASHSCOPE_API_KEY` 后，通过 OpenAI 兼容接口调用阿里云百炼 `text-embedding-v4`（768 维），base_url = `https://dashscope.aliyuncs.com/compatible-mode/v1`
2. **第二优先级（本地降级）**：API 不可用时加载本地 `bge-large-zh-v1.5`（768 维）

关键方法：`load_model()` / `encode()` / `encode_batch()` / `_encode_via_api()` / `_init_dashscope_client()`

### 关键约束
- API Key 通过环境变量注入，禁止硬编码
- DashScope OpenAI 兼容端点必须是 `/compatible-mode/v1`
- `encode()` 返回 float32 numpy 数组，`normalize_embeddings=True`
- 日志中禁止输出完整 API Key

## 文件清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | `Veritas/ai-service/app/services/embedding_service.py` | EmbeddingService 实现 |
| 修改 | `Veritas/ai-service/app/core/config.py` | 新增 DASHSCOPE_API_KEY 等 3 个配置项 |
| 修改 | `Veritas/ai-service/app/core/events.py` | 启动时加载 EmbeddingService |
| 修改 | `Veritas/ai-service/app/main.py` | /health 返回真实状态 |
| 修改 | `Veritas/ai-service/.env.example` | 新增阿里云百炼配置区域 |

## 验收标准
- [ ] `DASHSCOPE_EMBEDDING_BASE_URL` 默认值为 `https://dashscope.aliyuncs.com/compatible-mode/v1`
- [ ] `load_model()` 实现 API 优先 → 本地降级的策略
- [ ] `encode('单条文本')` 返回 `shape(768,)` 的 float32 向量
- [ ] `encode(['a','b'])` 返回 `shape(2,768)` 矩阵
- [ ] `encode_batch(100条)` 分 batch 处理，返回 `(100,768)`
- [ ] 不配置 API Key 时降级加载本地模型（status='loaded_local'）
- [ ] `/health` 返回真实 embedding 状态而非 `'not_loaded'`
- [ ] 日志中不输出完整 API Key