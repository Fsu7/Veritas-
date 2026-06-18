# task53: 外接 Embedding API 备选方案

> **课题编号**：XH-202630
> **子项目**：科研文献助手 — AI 服务模块
> **里程碑**：M5 / AM5：混合检索与功能完善
> **AM5 天数**：Week 10 Day 3
> **版本**：v0.5
> **功能编号**：F5.2.1, F5.2.2
> **优先级**：P0
> **创建日期**：2026-06-17

---

## 1. 背景与上下文

### 1.1 项目背景

XH-202630 科研文献智能助手 — EmbeddingService 当前仅支持 DashScope API（text-embedding-v4，1024维），无备选 Provider。当 DashScope API 不可用时，整个检索系统瘫痪。本任务扩展为多 Provider 架构，支持 Jina/OpenAI 作为备选。

### 1.2 任务需求

扩展 EmbeddingService 支持 Jina/OpenAI 作为 DashScope 的备选 Provider。重构为多 Provider 架构（DashScopeProvider/JinaProvider/OpenAIProvider），通过 EMBEDDING_PROVIDER 环境变量选择。JinaProvider 调用 jina-embeddings-v3（1024维），OpenAIProvider 调用 text-embedding-3-small（1536维，需降维到1024或调整ChromaDB维度）。维度校验：所有 Provider 输出维度必须与 ChromaDB collection 维度一致。Provider 失败时降级到下一个 Provider（dashscope→jina→openai）。

### 1.3 参考文档

| 文档 | 用途 |
|------|------|
| [docs/ai-service/AI服务模块系统架构文档.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块系统架构文档.md) | 了解 EmbeddingService 当前单一 DashScope Provider 实现 |
| [docs/ai-service/AI服务模块项目里程碑文档.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块项目里程碑文档.md) | 确认 AM5 Week 10 Day 3 外接 Embedding API 交付物 |
| [AGENTS.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/AGENTS.md) | 确认降级约束和配置管理规范 |

---

## 2. 当前架构

### 2.1 涉及层级

- `python_ai_service`

### 2.2 相关模块

| 层级 | 模块路径 | 描述 |
|------|---------|------|
| python_ai_service | `app.services.embedding_service` | EmbeddingService 当前仅支持 DashScope API（text-embedding-v4，1024维），无备选 Provider |
| python_ai_service | `app.core.config` | Settings 配置类，需新增 EMBEDDING_PROVIDER/JINA_API_KEY/OPENAI_API_KEY |
| python_ai_service | `app.services.vector_store_service` | ChromaDB 向量存储，collection 维度 1024 |

### 2.3 现有实现

| 文件 | 描述 | 复用方式 |
|------|------|---------|
| `Veritas/ai-service/app/services/embedding_service.py` | EmbeddingService 单一 DashScope 实现，embed_query/embed_documents 方法已存在 | refactor |
| `Veritas/ai-service/app/core/config.py` | Settings 已有 DASHSCOPE_API_KEY 配置，需新增 Jina/OpenAI 配置 | extend |
| `Veritas/ai-service/.env.example` | 环境变量示例文件，需追加外接 Embedding 配置 | extend |

---

## 3. 相关模块详情

### 3.1 EmbeddingService

- **路径**：`Veritas/ai-service/app/services/embedding_service.py`
- **职责**：文本向量化服务

| 方法 | 签名 | 描述 |
|------|------|------|
| `embed_query` | `async def embed_query(self, text: str) -> List[float]` | 查询单条文本向量化 |
| `embed_documents` | `async def embed_documents(self, texts: List[str]) -> List[List[float]]` | 批量文本向量化 |

### 3.2 VectorStoreService

- **路径**：`Veritas/ai-service/app/services/vector_store_service.py`
- **职责**：ChromaDB 向量存储

| 接口 | 签名 | 描述 |
|------|------|------|
| collection | `collection.dimension = 1024` | ChromaDB collection 维度固定 1024 |

---

## 4. 待修改文件

| 操作 | 路径 | 说明 |
|------|------|------|
| modify | `Veritas/ai-service/app/services/embedding_service.py` | 重构为多 Provider 架构：1) 新增 BaseEmbeddingProvider 抽象基类（含 embed_query/embed_documents 抽象方法 + dimension 属性）；2) DashScopeProvider 封装现有 DashScope 逻辑（text-embedding-v4，1024维）；3) JinaProvider 调用 https://api.jina.ai/v1/embeddings，模型 jina-embeddings-v3，维度1024；4) OpenAIProvider 调用 https://api.openai.com/v1/embeddings，模型 text-embedding-3-small，维度1536（需降维到1024：截断或PCA，推荐截断前1024维并归一化）；5) EmbeddingService 持有 active_provider 和 fallback_providers 列表；6) embed_query/embed_documents 委托 active_provider，失败时降级到 fallback_providers；7) 维度校验：provider.dimension 必须等于 ChromaDB collection 维度（1024），否则抛 ModelNotLoadedException。 |
| modify | `Veritas/ai-service/app/core/config.py` | Settings 类新增配置项：1) EMBEDDING_PROVIDER: str = 'dashscope'（可选值 dashscope/jina/openai）；2) JINA_API_KEY: Optional[str] = None；3) OPENAI_API_KEY: Optional[str] = None；4) EMBEDDING_DIMENSION: int = 1024（ChromaDB collection 维度，用于校验）。 |
| modify | `Veritas/ai-service/.env.example` | 追加配置示例：EMBEDDING_PROVIDER=dashscope / JINA_API_KEY= / OPENAI_API_KEY= / EMBEDDING_DIMENSION=1024 |
| create | `Veritas/ai-service/tests/test_external_embedding.py` | 测试：1) test_jina_provider_activated 验证 EMBEDDING_PROVIDER=jina 时使用 JinaProvider；2) test_openai_provider_activated 验证 EMBEDDING_PROVIDER=openai 时使用 OpenAIProvider；3) test_dimension_mismatch_raises 验证维度不一致抛 ModelNotLoadedException；4) test_provider_fallback 验证 dashscope 失败降级到 jina；5) test_openai_dimension_truncation 验证 OpenAI 1536维降维到1024维。 |

---

## 5. 实现要求

### 5.1 功能需求（FR）

| ID | 优先级 | 描述 | 验收条件 |
|----|--------|------|---------|
| FR-001 | P0 | EmbeddingService 重构为 Provider 模式：1) BaseEmbeddingProvider 抽象基类：abstract async embed_query(text) -> List[float]、abstract async embed_documents(texts) -> List[List[float]]、property dimension -> int；2) DashScopeProvider 继承基类，封装现有 DashScope 逻辑，dimension=1024；3) JinaProvider 继承基类，dimension=1024；4) OpenAIProvider 继承基类，dimension=1024（1536截断）；5) EmbeddingService.__init__ 根据 settings.EMBEDDING_PROVIDER 选择 active_provider，其余加入 fallback_providers 列表。 | EmbeddingService 支持 3 个 Provider 切换 |
| FR-002 | P0 | 通过 EMBEDDING_PROVIDER 环境变量选择 Provider：1) settings.EMBEDDING_PROVIDER='dashscope' 时 active_provider=DashScopeProvider，fallback=[JinaProvider, OpenAIProvider]；2) ='jina' 时 active=JinaProvider，fallback=[DashScopeProvider, OpenAIProvider]；3) ='openai' 时 active=OpenAIProvider，fallback=[DashScopeProvider, JinaProvider]；4) 默认值 'dashscope'。 | EMBEDDING_PROVIDER 环境变量正确切换 active_provider |
| FR-003 | P0 | JinaProvider 实现：1) 调用 POST https://api.jina.ai/v1/embeddings；2) 请求头 Authorization: Bearer {JINA_API_KEY}；3) 请求体 {model: 'jina-embeddings-v3', input: [texts], dimensions: 1024}；4) 解析响应 data[].embedding；5) dimension=1024；6) 使用 httpx.AsyncClient 异步调用；7) 超时 30s，重试 1 次。 | JinaProvider 正确调用 Jina API 并返回 1024 维向量 |
| FR-004 | P0 | OpenAIProvider 实现：1) 调用 POST https://api.openai.com/v1/embeddings；2) 请求头 Authorization: Bearer {OPENAI_API_KEY}；3) 请求体 {model: 'text-embedding-3-small', input: [texts]}；4) 解析响应 data[].embedding（1536维）；5) 降维到1024：截断前1024维 + L2归一化；6) dimension=1024；7) 使用 httpx.AsyncClient 异步调用；8) 超时 30s，重试 1 次。 | OpenAIProvider 正确调用 OpenAI API 并返回降维后的 1024 维向量 |
| FR-005 | P0 | 维度校验：1) EmbeddingService.__init__ 检查 active_provider.dimension == settings.EMBEDDING_DIMENSION（1024）；2) 不一致时抛 ModelNotLoadedException(f'Provider {name} dimension {dim} != ChromaDB dimension {expected}')；3) 不静默失败，不自动降维（OpenAIProvider 内部已降维，对外 dimension=1024）。 | 维度不一致时抛 ModelNotLoadedException |
| FR-006 | P1 | Provider 失败时降级到下一个 Provider：1) embed_query/embed_documents try-except 包裹 active_provider 调用；2) 捕获 Exception，logger.warning 输出降级原因；3) 遍历 fallback_providers 依次尝试；4) 全部失败抛出最后一个异常；5) 降级顺序：active → fallback[0] → fallback[1]。 | Provider 失败时降级到下一个 Provider，日志记录降级 |
| FR-007 | P1 | /api/model/status 返回当前 Embedding Provider 信息：1) 响应新增 embedding_provider 字段，含 {name: str, dimension: int, fallbacks: List[str]}；2) name 为 active_provider 类名；3) fallbacks 为 fallback_providers 类名列表。 | /api/model/status 返回 embedding_provider 信息 |

### 5.2 降级需求

| 场景 | 策略 |
|------|------|
| Provider 失败 | active_provider 失败降级到 fallback_providers 列表 |
| 全部 Provider 失败 | 全部 Provider 失败抛出最后一个异常 |

---

## 6. 约束

### 6.1 命名规范

| 对象 | Python |
|------|--------|
| 类名 | PascalCase |
| 函数/变量 | snake_case |
| 常量 | UPPER_SNAKE_CASE |
| 文件名 | snake_case.py |

### 6.2 分层规范

- Embedding 服务在 `services/`
- 配置在 `core/`
- 测试在 `tests/`

### 6.3 错误处理

- Provider 失败降级到下一个，全部失败抛异常
- 维度不匹配：抛 ModelNotLoadedException，不静默失败

### 6.4 日志

- 日志库：Loguru
- 必需日志：Provider 降级日志
- 禁止：打印 API Key 明文

---

## 7. 禁止动作

| ID | 动作 | 原因 | 严重性 |
|----|------|------|--------|
| FA-001 | 输出伪代码或 TODO 注释 | 必须输出完整可执行代码 | critical |
| FA-002 | 删除现有 DashScope 实现逻辑 | DashScopeProvider 封装现有逻辑，不删除 | critical |
| FA-003 | 在代码中硬编码 API Key | 必须从 settings 读取 | critical |
| FA-004 | 修改 ChromaDB collection 维度为 1536 | 保持 1024 维，OpenAI 在 Provider 内部降维 | high |
| FA-005 | 使用同步 requests 库调用 API | 必须用 httpx.AsyncClient 异步 | high |
| FA-006 | 在 .env.example 中填入真实 API Key | 仅占位符，不填真实值 | critical |
| FA-007 | 跳过维度校验 | 维度不一致必须抛异常 | high |

---

## 8. 测试要求

### 8.1 单元测试

| 测试名 | 描述 | 框架 | 覆盖范围 |
|--------|------|------|---------|
| test_jina_provider_activated | EMBEDDING_PROVIDER=jina 时 EmbeddingService 使用 JinaProvider | pytest | normal_flow |
| test_openai_provider_activated | EMBEDDING_PROVIDER=openai 时 EmbeddingService 使用 OpenAIProvider | pytest | normal_flow |
| test_dashscope_provider_default | 默认 EMBEDDING_PROVIDER=dashscope 时使用 DashScopeProvider | pytest | normal_flow |
| test_dimension_mismatch_raises | 维度不一致时抛 ModelNotLoadedException | pytest | error_flow |
| test_provider_fallback | dashscope 失败降级到 jina，日志记录降级 | pytest | error_flow, degradation |
| test_openai_dimension_truncation | OpenAI 1536维降维到1024维 + L2归一化 | pytest | normal_flow |
| test_model_status_returns_provider_info | /api/model/status 返回 embedding_provider 信息 | pytest | normal_flow |

### 8.2 验证命令

```bash
cd Veritas/ai-service && python -m pytest tests/test_external_embedding.py -v
```

**预期结果**：7 个测试用例全部通过

---

## 9. 验收标准

| ID | 验收标准 | 验证方式 |
|----|---------|---------|
| AC-001 | EMBEDDING_PROVIDER=jina 时，EmbeddingService 使用 JinaProvider | automated_test |
| AC-002 | EMBEDDING_PROVIDER=openai 时，EmbeddingService 使用 OpenAIProvider | automated_test |
| AC-003 | 维度不一致时抛出 ModelNotLoadedException，不静默失败 | automated_test |
| AC-004 | Provider 失败时降级到下一个 Provider，日志记录降级 | automated_test |
| AC-005 | OpenAI 1536维正确降维到1024维 + L2归一化 | automated_test |
| AC-006 | /api/model/status 返回 embedding_provider 信息 | automated_test |
