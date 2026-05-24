# FastAPI 项目骨架搭建

## 功能描述
- 解决了 Python AI 服务层缺少项目骨架的问题，为后续多 Agent 协同引擎、RAG 检索、个性化引擎等核心功能提供基础架构支撑
- 实现了完整的 FastAPI 项目目录结构、依赖管理、应用生命周期管理、路由聚合和占位端点
- 业务价值：为 M1 里程碑（基础设施就绪）提供 AI 服务层骨架，使后续开发可以基于此骨架快速迭代

## 实现逻辑
- 修改的核心文件列表：
  - `Veritas/ai-service/requirements.txt` — 22 个 Python 依赖，按功能分组锁定版本号
  - `Veritas/ai-service/app/main.py` — FastAPI 应用入口，含 lifespan 生命周期、/health 健康检查、全局异常处理器、路由注册
  - `Veritas/ai-service/app/api/router.py` — 路由聚合器，汇总 agent/search/model 三个子路由
  - `Veritas/ai-service/app/api/endpoints/agent.py` — Agent 分析接口占位（POST /api/agent/analyze）
  - `Veritas/ai-service/app/api/endpoints/search.py` — 检索接口占位（POST /api/search/）
  - `Veritas/ai-service/app/api/endpoints/model.py` — 模型状态接口占位（GET /api/model/status）
  - `Veritas/ai-service/app/core/config.py` — Pydantic Settings 配置（环境变量注入）
  - `Veritas/ai-service/app/core/events.py` — 启动/关闭事件管理
  - `Veritas/ai-service/app/core/logging.py` — Loguru 日志配置（控制台+文件轮转）
  - `Veritas/ai-service/.gitignore` — Python 项目忽略规则
  - 9 个 `__init__.py` 包初始化文件
  - 4 个 `.gitkeep` 目录占位文件

- 使用的设计模式：
  - **三层分离架构**（ADR-001）：Router → Service → Agent，路由层不包含业务逻辑
  - **lifespan 异步上下文管理器**：FastAPI 原生生命周期管理，替代已废弃的 on_event
  - **路由聚合模式**：APIRouter 嵌套组合，子路由独立定义后通过 router.py 统一注册
  - **统一异常处理**：全局 exception_handler 返回统一 JSON 格式

- 关键代码逻辑说明：
  - `lifespan` 函数在 yield 前执行启动逻辑（当前为日志占位），yield 后执行关闭逻辑
  - `/health` 端点返回服务状态和各组件状态（llm/embedding/chroma 占位值）
  - `RequestValidationError` 处理器捕获 Pydantic 校验失败，返回 422 + 统一格式
  - 通用 `Exception` 处理器兜底未预期异常，返回 500 + 统一格式
  - `config.py` 使用 `protected_namespaces=("settings_",)` 解决 pydantic v2 的 `model_` 命名空间冲突

## 接口变更

### GET /health
```json
{
  "status": "UP",
  "timestamp": "2026-05-24T11:33:39.052177",
  "llm": "not_loaded",
  "embedding": "not_loaded",
  "chroma": "not_connected"
}
```

### POST /api/agent/analyze（占位）
```json
{
  "message": "Agent analyze endpoint - to be implemented"
}
```

### POST /api/search/（占位）
```json
{
  "message": "Search endpoint - to be implemented"
}
```

### GET /api/model/status（占位）
```json
{
  "message": "Model status endpoint - to be implemented"
}
```

### 异常响应格式（422 / 500）
```json
{
  "code": 422,
  "message": "参数校验失败: ...",
  "data": null,
  "timestamp": 1716543219000
}
```

## 测试结果
- 测试场景1：`python -c "from app.main import app; print(app.title)"` → 输出 `Literature Assistant AI Service` ✅
- 测试场景2：`uvicorn app.main:app --host 0.0.0.0 --port 8000` 启动成功，日志输出启动信息和配置 ✅
- 测试场景3：`curl http://localhost:8000/health` → 返回 200 和正确 JSON ✅
- 测试场景4：`curl http://localhost:8000/api/model/status` → 返回占位 JSON ✅
- 测试场景5：`curl -X POST http://localhost:8000/api/agent/analyze` → 返回占位 JSON ✅
- 测试场景6：`curl -X POST http://localhost:8000/api/search/` → 返回占位 JSON ✅
- 测试场景7：目录结构与架构文档 §3.1 一致 ✅
- 是否通过：是

## 相关文件
- `Veritas/ai-service/requirements.txt`
- `Veritas/ai-service/.gitignore`
- `Veritas/ai-service/app/__init__.py`
- `Veritas/ai-service/app/main.py`
- `Veritas/ai-service/app/api/__init__.py`
- `Veritas/ai-service/app/api/router.py`
- `Veritas/ai-service/app/api/endpoints/__init__.py`
- `Veritas/ai-service/app/api/endpoints/agent.py`
- `Veritas/ai-service/app/api/endpoints/search.py`
- `Veritas/ai-service/app/api/endpoints/model.py`
- `Veritas/ai-service/app/core/__init__.py`
- `Veritas/ai-service/app/core/config.py`
- `Veritas/ai-service/app/core/events.py`
- `Veritas/ai-service/app/core/logging.py`
- `Veritas/ai-service/app/agents/__init__.py`
- `Veritas/ai-service/app/services/__init__.py`
- `Veritas/ai-service/app/models/__init__.py`
- `Veritas/ai-service/app/utils/__init__.py`
- `Veritas/ai-service/prompts/.gitkeep`
- `Veritas/ai-service/data/papers/.gitkeep`
- `Veritas/ai-service/data/vector_db/.gitkeep`
- `Veritas/ai-service/tests/__init__.py`
- `Veritas/ai-service/scripts/.gitkeep`
