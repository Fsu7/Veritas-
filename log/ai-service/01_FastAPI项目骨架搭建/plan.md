# Task04: Python FastAPI 项目骨架创建计划

## 任务概述

创建 Python AI 服务 FastAPI 项目骨架，包含完整目录结构、依赖管理、应用入口、路由聚合和占位文件。项目根目录为 `Veritas/ai-service/`。

---

## 实现步骤

### Step 1: 创建目录结构与占位文件

创建所有目录及 `__init__.py` / `.gitkeep` 占位文件：

| 文件路径 | 类型 |
|---------|------|
| `app/__init__.py` | 包初始化 |
| `app/api/__init__.py` | 包初始化 |
| `app/api/endpoints/__init__.py` | 包初始化 |
| `app/core/__init__.py` | 包初始化 |
| `app/agents/__init__.py` | 包初始化 |
| `app/services/__init__.py` | 包初始化 |
| `app/models/__init__.py` | 包初始化 |
| `app/utils/__init__.py` | 包初始化 |
| `prompts/.gitkeep` | 目录占位 |
| `data/papers/.gitkeep` | 目录占位 |
| `data/vector_db/.gitkeep` | 目录占位 |
| `tests/__init__.py` | 包初始化 |
| `scripts/.gitkeep` | 目录占位 |

### Step 2: 创建 requirements.txt

按功能分组，锁定版本号（来自架构文档 §19.3）：

- Web Framework: fastapi, uvicorn, python-multipart, sse-starlette
- AI/ML: langgraph, langchain, langchain-community, transformers, torch, sentence-transformers
- Vector Database: chromadb
- LLM API: openai, httpx
- Data Processing: pydantic, pydantic-settings, numpy
- PDF Processing: pymupdf
- arXiv: arxiv
- Utilities: python-dotenv, loguru
- Testing: pytest, pytest-asyncio

### Step 3: 创建 app/main.py

核心内容：
1. **lifespan 异步上下文管理器** — 启动阶段 `logger.info("Starting AI Service...")` 占位，关闭阶段 `logger.info("Shutting down AI Service...")` 占位
2. **FastAPI 实例** — `title="Literature Assistant AI Service"`, `version="1.0.0"`, `lifespan=lifespan`
3. **/health 健康检查** — 返回 `{status: "UP", timestamp: ISO格式, llm: "not_loaded", embedding: "not_loaded", chroma: "not_connected"}`
4. **全局异常处理器** — `RequestValidationError` 处理器（返回统一格式 `{code, message, data: None, timestamp}`），`AIServiceException` 占位（先使用通用 Exception）
5. **路由注册** — `app.include_router(api_router, prefix="/api")`

### Step 4: 创建 app/api/router.py

- 创建 `api_router = APIRouter()`
- 聚合 3 个子路由：`agent_router(prefix="/agent", tags=["agent"])`、`search_router(prefix="/search", tags=["search"])`、`model_router(prefix="/model", tags=["model"])`

### Step 5: 创建 3 个 endpoint 占位文件

- `app/api/endpoints/agent.py` — `POST /analyze` 返回占位 JSON
- `app/api/endpoints/search.py` — `POST /` 返回占位 JSON
- `app/api/endpoints/model.py` — `GET /status` 返回占位 JSON

### Step 6: 创建 core 占位文件

- `app/core/config.py` — 基础 Settings 类占位（含 import 和空类定义）
- `app/core/events.py` — 启动/关闭事件占位
- `app/core/logging.py` — 日志配置占位

### Step 7: 创建 .gitignore

包含：`__pycache__/`, `*.py[cod]`, `*$py.class`, `.env`, `.venv/`, `env/`, `*.egg-info/`, `dist/`, `build/`, `.pytest_cache/`, `data/vector_db/`, `models/`, `*.log`, `logs/`, `.DS_Store`

### Step 8: 验证

1. `pip install -r requirements.txt` — 依赖安装成功
2. `python -c "from app.main import app; print(app.title)"` — 输出应用标题
3. `find app -type d | sort` — 目录结构正确
4. `uvicorn app.main:app` 启动 + `curl http://localhost:8000/health` — 健康检查正常

---

## 关键约束

- **禁止硬编码敏感信息** — 所有配置通过 `.env` 环境变量注入
- **禁止伪代码/TODO注释** — 必须输出完整可执行代码
- **禁止路由函数中写业务逻辑** — Router → Service → Agent 分层
- **目录结构必须与架构文档 §3.1 一致**
- **所有 Python 包含 `__init__.py`，空目录含 `.gitkeep`**
- **requirements.txt 必须锁定版本号**
- **JSON 字段使用 snake_case**

---

## 文件创建清单（24个文件）

```
Veritas/ai-service/
├── requirements.txt
├── .gitignore
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py
│   │   └── endpoints/
│   │       ├── __init__.py
│   │       ├── agent.py
│   │       ├── search.py
│   │       └── model.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── events.py
│   │   └── logging.py
│   ├── agents/
│   │   └── __init__.py
│   ├── services/
│   │   └── __init__.py
│   ├── models/
│   │   └── __init__.py
│   └── utils/
│       └── __init__.py
├── prompts/
│   └── .gitkeep
├── data/
│   ├── papers/
│   │   └── .gitkeep
│   └── vector_db/
│       └── .gitkeep
├── tests/
│   └── __init__.py
└── scripts/
    └── .gitkeep
```
