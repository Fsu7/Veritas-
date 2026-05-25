# 技术教学文档 — M1阶段审阅修复与验证

## 开发思路

### 需求分析过程

本次任务不是常规的功能开发，而是对AI服务模块M1阶段进行**系统性审阅和修复**。分析过程如下：

1. **读取架构文档** — 先理解设计意图（AGENTS.md + AI服务架构文档 + 里程碑文档）
2. **读取prompt任务定义** — 对照task00~task09的10个prompt，确认每个任务的预期交付物
3. **逐文件审阅实际代码** — 按架构层级（main→config→services→models→endpoints）阅读所有源码
4. **逐项验证M1检查点** — 对照15项验收标准，代码层面验证每项是否满足
5. **识别风险分级** — 按P0/P1/P2分级，P0为阻断AM2的必须修复项

### 技术选型考虑

| 修复项 | 方案A | 方案B | 方案C | 最终选择 |
|--------|-------|-------|-------|---------|
| Embedding维度 | bge-m3替换(1024维) | 动态维度适配 | 维度padding | **方案A** — 最简单，与API对齐 |
| camelCase兼容 | Pydantic alias | 手动json.dumps | 中间件转换 | **方案A** — Pydantic原生支持 |
| 全局变量 | AppState类 | FastAPI app.state | 依赖注入 | **方案A** — 改动最小，向后兼容 |

### 架构设计思路

修复遵循**最小侵入原则** — 每项修复只改动必要的代码，不重构整体架构。核心思路：

1. **防御性编程** — 维度校验、URL空值检查、超时控制，都是在入口处加防护
2. **数据契约对齐** — camelCase alias确保Java↔Python通信时字段名一致
3. **语义化健康检查** — /health返回503而非永远200，让运维能及时发现组件故障

### 遇到的问题及解决方案

| 问题 | 解决方案 |
|------|---------|
| bge-large-zh-v1.5只有768维，与架构文档1024维不符 | 改用bge-m3(1024维)，同时增加维度校验防止未来再出现不一致 |
| 软件方URL不可达时test_connection()阻塞30秒 | URL为空时直接跳过，test_connection加10s超时 |
| Java后端使用camelCase，Python使用snake_case | Pydantic alias + populate_by_name=True，同时支持两种命名 |
| /health永远返回200，组件全挂也无法感知 | 根据核心组件状态判断返回200或503 |

## 实现步骤

### 第一步：P0修复 — Embedding维度对齐

1. `config.py` 默认 `EMBEDDING_MODEL_PATH` 从 `bge-large-zh-v1.5` 改为 `bge-m3`
2. `config.py` 新增 `EMBEDDING_EXPECTED_DIMENSION: int = 1024` 配置项
3. `embedding_service.py` 加载后检查 `dimension == EXPECTED_DIMENSION`，不匹配时warning
4. `vector_store_service.py` 的 `add_papers()` 增加维度校验，不匹配时抛异常
5. `.env.example` 更新模型名和维度配置

### 第二步：P0修复 — 软件方模型URL空值保护

1. `config.py` 将 `LLM_BUILTIN_URL/API_KEY/MODEL` 默认值清空
2. `llm_service.py` 的 `initialize()` 检查URL非空才创建Provider
3. `BuiltinLLMProvider.test_connection()` 和 `APILLMProvider.test_connection()` 增加10s超时
4. `.env.example` 标注软件方URL为"待发榜单位提供"

### 第三步：P1修复 — Pydantic camelCase alias

1. `schemas.py` 所有模型字段增加 `alias="camelCase"` 和 `populate_by_name=True`
2. 3个API端点增加 `response_model_by_alias=True`
3. `AnalyzeRequest` 增加 `analysis_type` 和 `analysis_id` 字段
4. `ModelStatusResponse` 增加 `embedding_dimension` 和 `active_llm_provider` 字段

### 第四步：P1修复 — /health组件级健康判断

1. `main.py` 的 `/health` 增加组件状态逻辑判断
2. 核心组件健康→200/UP，否则→503/DEGRADED
3. 使用 `JSONResponse(status_code=...)` 替代默认dict返回

### 第五步：P1修复 — LLM超时控制

1. `llm_service.py` 的 `generate()` 用 `asyncio.wait_for(timeout=LLM_TIMEOUT)` 包裹
2. 超时后记录降级状态并自动 `_fallback()`
3. `test_connection()` 同样加10s超时

### 第六步：P2修复 — .dockerignore + AppState + analysis_type

1. 创建 `.dockerignore` 排除不必要文件
2. `events.py` 将4个全局变量封装为 `AppState` 类
3. 更新所有 `events.xxx` → `events.app_state.xxx` 的引用

### 第七步：自动化验证

1. 编写Python验证脚本（单元级10项 + API级6项）
2. 使用 `fastapi.testclient.TestClient` 在内存中启动服务
3. 验证camelCase输入/输出、422校验、/health状态码、Embedding维度、LLM降级

## 解决了什么问题

### 核心问题描述

| 问题 | 严重性 | 影响 |
|------|--------|------|
| Embedding维度不一致 | P0 | 本地模型768维无法写入ChromaDB(1024维)，降级后RAG检索崩溃 |
| 软件方URL占位 | P0 | 启动时test_connection()阻塞，浪费10-30秒 |
| 字段命名不一致 | P1 | Java后端传camelCase，Python只接受snake_case，AM3联调必然出错 |
| /health永远200 | P1 | 组件全挂也无法感知，运维盲区 |
| LLM无超时 | P1 | 请求可能无限挂起，拖垮整个服务 |

### 解决方案对比

**Embedding维度问题**:

| 方案 | 优点 | 缺点 | 最终 |
|------|------|------|------|
| bge-m3替换(1024维) | 简单直接，与API对齐 | 模型更大(~2GB) | ✅ 选择 |
| 动态维度适配 | 灵活，支持任意维度 | 复杂，需多个collection | ❌ |
| 维度padding(补零) | 不换模型 | 牺牲检索质量 | ❌ |

**camelCase兼容**:

| 方案 | 优点 | 缺点 | 最终 |
|------|------|------|------|
| Pydantic alias | 原生支持，零运行时开销 | 需每个字段写alias | ✅ 选择 |
| 中间件转换 | 一处配置全局生效 | 影响所有请求响应 | ❌ |
| 手动序列化 | 灵活 | 代码冗余，易遗漏 | ❌ |

## 变更内容

### 新增文件
- `Veritas/ai-service/.dockerignore` — Docker构建排除规则
- `Veritas/ai-service/.env` — 本地开发环境变量（不入Git）

### 修改文件
- `app/core/config.py` — EMBEDDING_MODEL_PATH改bge-m3, 新增EMBEDDING_EXPECTED_DIMENSION, LLM_BUILTIN_*默认值清空
- `app/core/events.py` — 全局变量→AppState类
- `app/services/embedding_service.py` — bge-m3默认+维度校验+告警日志
- `app/services/vector_store_service.py` — add_papers维度校验
- `app/services/llm_service.py` — URL空值保护+test_connection超时+generate超时+降级
- `app/models/schemas.py` — 全部alias+populate_by_name+analysis_type/analysis_id+embeddingDimension/activeLlmProvider
- `app/main.py` — /health 503判断+app_state引用
- `app/api/endpoints/agent.py` — response_model_by_alias+analysis_id
- `app/api/endpoints/search.py` — response_model_by_alias+app_state引用
- `app/api/endpoints/model.py` — response_model_by_alias+app_state引用
- `.env.example` — bge-m3+EMBEDDING_EXPECTED_DIMENSION+LLM_BUILTIN_URL注释

### 配置变更
- `EMBEDDING_MODEL_PATH`: `BAAI/bge-large-zh-v1.5` → `BAAI/bge-m3`
- `EMBEDDING_EXPECTED_DIMENSION`: 新增，默认1024
- `LLM_BUILTIN_URL`: 占位URL → `""` (空值跳过)
- `LLM_BUILTIN_API_KEY`: `"builtin"` → `""`
- `LLM_BUILTIN_MODEL`: `"literature-assistant-pro"` → `""`

## 关键技术点

### 1. Pydantic alias双向兼容

```python
class AnalyzeRequest(BaseModel):
    paper_ids: List[str] = Field(default_factory=list, alias="paperIds")
    user_id: str = Field(..., min_length=1, alias="userId")

    model_config = ConfigDict(populate_by_name=True)
```

- `populate_by_name=True` 允许同时接受 `paper_ids` 和 `paperIds`
- `response_model_by_alias=True` 让API响应输出 `paperIds`
- Java端发camelCase，Python内部用snake_case，两全其美

### 2. asyncio.wait_for 超时控制

```python
async def generate(self, prompt, max_tokens=2048, temperature=0.7):
    timeout = self.settings.LLM_TIMEOUT
    try:
        return await asyncio.wait_for(
            self.active_provider.generate(prompt, max_tokens, temperature),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        await self._fallback()
        return await asyncio.wait_for(
            self.active_provider.generate(prompt, max_tokens, temperature),
            timeout=timeout,
        )
```

- 超时后自动降级到下一个Provider
- 降级后再次尝试，仍有超时保护

### 3. Embedding维度校验链

```python
# 加载时校验（warning不阻断）
if self._dimension != expected:
    logger.warning(f"dimension={self._dimension} != expected={expected}")

# 写入时校验（hard fail）
if len(embeddings[0]) != self.EXPECTED_DIMENSION:
    raise VectorStoreException(f"dimension mismatch: {actual_dim} != {expected_dim}")
```

- 加载时仅告警（可能是有意换模型）
- 写入时强校验（维度不匹配会破坏ChromaDB索引）

### 4. FastAPI TestClient内存验证

```python
from fastapi.testclient import TestClient
from app.main import app

with TestClient(app) as client:
    resp = client.get('/health')
    assert resp.status_code in (200, 503)
```

- 无需启动uvicorn，直接在内存中测试API
- 适合CI/CD环境，不依赖外部服务

## 经验总结

### 开发过程中的收获

1. **架构文档≠实际代码** — 文档标注1024维，但bge-large-zh-v1.5实际只有768维。必须以实际模型规格为准，文档需要同步更新
2. **占位URL是定时炸弹** — 不可达的占位URL会导致启动时无意义超时，空值保护是必须的
3. **Pydantic alias是跨系统通信的最佳实践** — Java camelCase ↔ Python snake_case 的转换，alias方案零侵入
4. **自动化验证比手动curl更可靠** — TestClient可在CI中运行，curl需要服务启动

### 踩过的坑及如何避免

1. **坑**: sandbox环境无法访问外部API（DashScope），导致uvicorn启动卡在lifespan
   - **解决**: 使用TestClient内存测试，不依赖外部网络
   - **避免**: 编写验证脚本时考虑网络不可达场景

2. **坑**: shell转义导致Python多行脚本执行失败
   - **解决**: 写成.py文件再执行
   - **避免**: 复杂Python代码不用-c参数

3. **坑**: 修改events.py后，所有引用events.llm_service的地方都需要更新
   - **解决**: 使用Task agent批量搜索替换
   - **避免**: 重构全局变量时先搜索所有引用点

### 最佳实践建议

1. **Embedding模型选型时必须确认输出维度** — 文档标注的维度不一定准确，以模型实际输出为准
2. **占位URL/Key使用空字符串而非假值** — 空字符串可以快速跳过，假值会触发无意义连接尝试
3. **API响应必须设置response_model_by_alias=True** — 否则alias只在输入解析时生效，输出仍是snake_case
4. **健康检查应区分"服务在线"和"服务健康"** — 200表示可用，503表示降级/不可用
5. **LLM调用必须有超时保护** — asyncio.wait_for是最简单的超时方案，超时后应触发降级
