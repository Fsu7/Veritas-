# M1阶段审阅修复与验证

## 功能描述
- 解决了AI服务模块M1阶段审阅中发现的8项风险问题（2个P0、3个P1、3个P2）
- 核心修复：Embedding维度不一致（768维→1024维）、软件方模型URL空值保护、Pydantic camelCase alias、/health组件级健康判断、LLM超时控制、AppState重构等
- 业务价值：确保M1里程碑验收通过，为AM2多Agent开发奠定稳定基础，消除Java后端联调时的字段映射隐患

## 实现逻辑

### 修改的核心文件列表

| 文件 | 修改类型 | 修复项 |
|------|---------|--------|
| `app/core/config.py` | 修改 | P0-1(bge-m3), P0-2(URL清空), 新增EMBEDDING_EXPECTED_DIMENSION |
| `app/services/embedding_service.py` | 修改 | P0-1(bge-m3+维度校验+启动告警) |
| `app/services/vector_store_service.py` | 修改 | P0-1(维度校验EXPECTED_DIMENSION) |
| `app/services/llm_service.py` | 修改 | P0-2(URL空值保护+10s超时), P1-3(asyncio.wait_for超时+降级) |
| `app/models/schemas.py` | 重写 | P1-1(camelCase alias), P2-1(analysis_type/analysis_id) |
| `app/api/endpoints/agent.py` | 修改 | P1-1(response_model_by_alias), P2-1(analysis_id) |
| `app/api/endpoints/search.py` | 修改 | P1-1(response_model_by_alias) |
| `app/api/endpoints/model.py` | 修改 | P1-1(response_model_by_alias) |
| `app/main.py` | 修改 | P1-2(/health 503), P2-3(app_state引用) |
| `app/core/events.py` | 重写 | P2-3(AppState类替代全局变量) |
| `.env.example` | 修改 | P0-1(bge-m3), P0-2(URL注释更新) |
| `.dockerignore` | 新建 | P2-2 |

### 使用的设计模式

1. **策略模式（维度校验）**: `EXPECTED_DIMENSION` 类常量 + 运行时校验，确保向量维度与ChromaDB collection一致
2. **空对象模式（URL空值保护）**: `LLM_BUILTIN_URL` 为空时跳过BuiltinLLMProvider，避免无意义超时
3. **别名模式（camelCase兼容）**: Pydantic `Field(alias=...)` + `populate_by_name=True`，同一模型同时支持snake_case和camelCase
4. **状态对象模式（AppState）**: 将4个全局变量封装为 `AppState` 类，提高可测试性和可维护性

### 关键代码逻辑说明

1. **维度校验链**: `EmbeddingService.load_model()` 加载后检查 `dimension == EXPECTED_DIMENSION` → 不匹配时 `logger.warning` → `VectorStoreService.add_papers()` 写入时再次校验，不匹配则抛 `VectorStoreException`
2. **URL空值保护**: `LLMService.initialize()` 检查 `settings.LLM_BUILTIN_URL` 非空才创建BuiltinLLMProvider → 空值时直接日志跳过 → 避免连接占位URL的10s超时
3. **超时控制双保险**: `test_connection()` 使用 `asyncio.wait_for(timeout=10)` + `generate()` 使用 `asyncio.wait_for(timeout=LLM_TIMEOUT)` → 超时后自动触发 `_fallback()` 降级
4. **/health组件级判断**: 4个组件状态检查 → `llm=="loaded" AND embedding in ("loaded_api","loaded_local") AND chroma=="connected"` → 全部满足→200/UP，否则→503/DEGRADED

## 接口变更

### Request — POST /api/agent/analyze（新增字段）

```json
{
    "topic": "Multi-Agent协同决策",
    "paperIds": ["arxiv_2024_001"],
    "userId": "usr_001",
    "userProfile": {
        "educationLevel": "master",
        "researchField": "NLP",
        "knowledgeLevel": "intermediate",
        "preferredStyle": "balanced"
    },
    "analysisType": "report",
    "analysisId": "anl_20240523_001"
}
```

**变更说明**: 新增 `analysisType`（分析类型）和 `analysisId`（任务ID，支持Java端传入或自动生成）

### Response — POST /api/agent/analyze（camelCase输出）

```json
{
    "analysisId": "anl_test_001",
    "status": "processing"
}
```

**变更说明**: 响应字段从 `analysis_id` → `analysisId`（by_alias=True）

### Response — GET /health（新增503状态码）

```json
// 组件健康时
{
    "status": "UP",
    "timestamp": "2026-05-25T13:54:18.514874+00:00",
    "llm": "loaded",
    "embedding": "loaded_api",
    "chroma": "connected",
    "prompts": "loaded"
}

// 组件不健康时（HTTP 503）
{
    "status": "DEGRADED",
    "timestamp": "2026-05-25T13:54:18.514874+00:00",
    "llm": "error",
    "embedding": "not_loaded",
    "chroma": "disconnected",
    "prompts": "not_loaded"
}
```

### Response — GET /api/model/status（新增字段）

```json
{
    "llm": "loaded",
    "embedding": "loaded_api",
    "chroma": "connected",
    "prompts": "loaded",
    "embeddingDimension": 1024,
    "activeLlmProvider": "api"
}
```

**变更说明**: 新增 `embeddingDimension` 和 `activeLlmProvider` 字段

## 测试结果

### 单元级验证（10项全部通过）

| # | 验证项 | 结果 |
|---|--------|------|
| 1 | Pydantic camelCase alias输入解析 | ✅ `topic=Multi-Agent, userId=u1` |
| 2 | Pydantic camelCase输出序列化 | ✅ `{"analysisId":"ana_123","status":"processing"}` |
| 3 | 空topic→422校验 | ✅ `ValidationError` |
| 4 | 异常体系统一JSON | ✅ `LLMException(503), AgentTimeoutException(408)` |
| 5 | Prompt模板6个加载+变量替换 | ✅ `"Test Paper" in prompt = True` |
| 6 | Config bge-m3 + EXPECTED_DIMENSION | ✅ `EMBEDDING_MODEL_PATH=BAAI/bge-m3` |
| 7 | AppState类 | ✅ `type: AppState` |
| 8 | ChromaDB初始化 | ✅ `connected, count=0` |
| 9 | DashScope API Embedding | ✅ `dimension=1024, encode("测试")=(1024,)` |
| 10 | LLM降级初始化 | ✅ `Builtin skipped → Using API provider` |

### API端点验证（6项全部通过）

| # | 验证项 | 结果 |
|---|--------|------|
| 1 | GET /health 组件就绪→200 | ✅ `UP, llm=loaded, embedding=loaded_api` |
| 2 | GET /api/model/status camelCase响应 | ✅ `embeddingDimension=1024` |
| 3 | POST /api/search camelCase请求体 | ✅ `topK=5` 正确解析 |
| 4 | POST /api/agent/analyze camelCase双向 | ✅ 输入解析+输出序列化 |
| 5 | 空topic→422 | ✅ `status_code=422` |
| 6 | 空query→422 | ✅ `status_code=422` |

**是否通过**: 是 ✅

## 相关文件

### 代码文件
- `Veritas/ai-service/app/core/config.py` — 配置默认值修改
- `Veritas/ai-service/app/core/events.py` — AppState类重构
- `Veritas/ai-service/app/services/embedding_service.py` — bge-m3+维度校验
- `Veritas/ai-service/app/services/vector_store_service.py` — 维度校验
- `Veritas/ai-service/app/services/llm_service.py` — URL空值保护+超时控制
- `Veritas/ai-service/app/models/schemas.py` — camelCase alias重写
- `Veritas/ai-service/app/main.py` — /health 503
- `Veritas/ai-service/app/api/endpoints/agent.py` — by_alias
- `Veritas/ai-service/app/api/endpoints/search.py` — by_alias
- `Veritas/ai-service/app/api/endpoints/model.py` — by_alias
- `Veritas/ai-service/.dockerignore` — 新建
- `Veritas/ai-service/.env` — 新建（本地开发配置）
- `Veritas/ai-service/.env.example` — 更新

### 配置文件变更
- `EMBEDDING_MODEL_PATH`: `BAAI/bge-large-zh-v1.5` → `BAAI/bge-m3`
- `EMBEDDING_EXPECTED_DIMENSION`: 新增，默认1024
- `LLM_BUILTIN_URL`: `https://llm.literature-assistant.com/v1` → `""` (空值)
- `LLM_BUILTIN_API_KEY`: `builtin` → `""` (空值)
- `LLM_BUILTIN_MODEL`: `literature-assistant-pro` → `""` (空值)

### 文档更新
- `docs/ai-service/AI服务模块系统架构文档.md` — v1.0→v1.1，12项修改
- `log/阶段审阅报告/ai-service/M1-阶段审阅报告.md` — 全面重写
