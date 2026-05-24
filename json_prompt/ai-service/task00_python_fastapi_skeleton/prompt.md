# Task00 — Python FastAPI 项目骨架

| 项目 | 内容 |
|------|------|
| **项目** | XH-202630 科研文献智能助手 |
| **版本** | v0.1 |
| **里程碑** | M1：基础设施就绪 / AM1：项目骨架与模型层就绪 |

## 需求描述

创建 Python AI 服务 FastAPI 项目骨架，包含完整目录结构、requirements.txt（锁定版本号）、main.py（FastAPI 应用入口含 lifespan 生命周期管理占位、/health 健康检查、全局异常处理器占位、路由注册）、router.py（路由聚合）以及所有 `__init__.py` 文件。项目根目录为 `Veritas/ai-service/`。

## 涉及层级

- `python_ai_service`

## 功能编号

- F3.5 / F3.5.1 / F3.5.2 / F3.5.3 / F3.5.4

## 需要修改/新增的文件

| 操作 | 路径 | 说明 |
|------|------|------|
| create | `Veritas/ai-service/requirements.txt` | Python 依赖文件，全部必需依赖及锁定版本号 |
| create | `Veritas/ai-service/app/__init__.py` | 应用根包初始化 |
| create | `Veritas/ai-service/app/main.py` | FastAPI 应用入口（lifespan + /health + 异常处理器 + 路由注册） |
| create | `Veritas/ai-service/app/api/__init__.py` | API 路由包初始化 |
| create | `Veritas/ai-service/app/api/router.py` | 路由聚合器（agent/search/model 三个子路由） |
| create | `Veritas/ai-service/app/api/endpoints/__init__.py` | endpoints 包初始化 |
| create | `Veritas/ai-service/app/api/endpoints/agent.py` | Agent 调用接口占位（POST /api/agent/analyze） |
| create | `Veritas/ai-service/app/api/endpoints/search.py` | 检索接口占位（POST /api/search） |
| create | `Veritas/ai-service/app/api/endpoints/model.py` | 模型状态接口占位（GET /api/model/status） |
| create | `Veritas/ai-service/app/core/__init__.py` | 核心配置包初始化 |
| create | `Veritas/ai-service/app/core/config.py` | 占位文件，任务5实现 |
| create | `Veritas/ai-service/app/core/events.py` | 占位文件，后续任务实现 |
| create | `Veritas/ai-service/app/core/logging.py` | 占位文件，任务5实现 |
| create | `Veritas/ai-service/app/agents/__init__.py` | Agent 模块包初始化 |
| create | `Veritas/ai-service/app/services/__init__.py` | 服务层包初始化 |
| create | `Veritas/ai-service/app/models/__init__.py` | 数据模型包初始化 |
| create | `Veritas/ai-service/app/utils/__init__.py` | 工具函数包初始化 |
| create | `Veritas/ai-service/prompts/.gitkeep` | Prompt 模板目录占位 |
| create | `Veritas/ai-service/data/papers/.gitkeep` | 论文原始数据目录占位 |
| create | `Veritas/ai-service/data/vector_db/.gitkeep` | Chroma 向量数据库文件目录占位 |
| create | `Veritas/ai-service/tests/__init__.py` | 测试包初始化 |
| create | `Veritas/ai-service/scripts/.gitkeep` | 工具脚本目录占位 |
| create | `Veritas/ai-service/.gitignore` | Python 项目 gitignore |

## 功能要求

| ID | 优先级 | 描述 |
|----|--------|------|
| FR-001 | P0 | `requirements.txt` 包含全部 22 个依赖及锁定版本号（fastapi==0.110.0、uvicorn[standard]==0.29.0、python-multipart==0.0.9、sse-starlette==2.0.0、langgraph==0.0.50、langchain==0.1.16、langchain-community==0.0.34、transformers==4.40.0、torch==2.2.0、sentence-transformers==2.7.0、chromadb==0.5.0、openai==1.23.0、httpx==0.27.0、pydantic==2.7.0、pydantic-settings==2.2.1、numpy==1.26.0、pymupdf==1.23.0、arxiv==2.1.0、python-dotenv==1.0.0、loguru==0.7.0、pytest==8.1.0、pytest-asyncio==0.23.0），按功能分组并添加中文注释 |
| FR-002 | P0 | `main.py` 创建 FastAPI 应用，title='Literature Assistant AI Service'，version='1.0.0'，使用 lifespan 参数管理生命周期。lifespan 函数 yield 前为启动阶段（仅 logger.info 占位），yield 后为关闭阶段（仅 logger.info 占位） |
| FR-003 | P0 | `main.py` 注册 `/health` 健康检查接口（GET），返回 `{status: 'UP', timestamp: ISO格式, llm: 'not_loaded', embedding: 'not_loaded', chroma: 'not_connected'}` |
| FR-004 | P0 | `main.py` 注册全局异常处理器占位：AIServiceException 处理器和 RequestValidationError 处理器，返回统一格式 `{code, message, data: None, timestamp}` |
| FR-005 | P0 | `router.py` 创建 api_router = APIRouter()，聚合 3 个子路由：agent_router(prefix='/agent')、search_router(prefix='/search')、model_router(prefix='/model')。main.py 中 `app.include_router(api_router, prefix='/api')` |
| FR-006 | P0 | 创建完整目录结构：app/(api/endpoints/、core/、agents/、services/、models/、utils/)、prompts/、data/(papers/、vector_db/)、tests/、scripts/。每个 Python 包含 `__init__.py`，空目录含 `.gitkeep` |
| FR-007 | P1 | 3 个 endpoint 文件创建占位路由：agent.py 含 POST /analyze、search.py 含 POST /、model.py 含 GET /status，均返回占位 JSON |
| FR-008 | P1 | core/config.py、core/events.py、core/logging.py 创建占位文件（含基本 import 和空类/函数定义） |
| FR-009 | P0 | `.gitignore` 包含：`__pycache__/`、`*.py[cod]`、`.env`、`.venv/`、`*.egg-info/`、`data/vector_db/`、`models/`、`*.log`、`logs/`、`.DS_Store` 等 |

## 验收标准

| ID | 验收条件 | 验证方式 |
|----|---------|---------|
| AC-001 | requirements.txt 包含全部 22 个依赖及锁定版本号，按功能分组 | 代码审查 |
| AC-002 | pip install -r requirements.txt 成功，无依赖冲突 | 自动测试 |
| AC-003 | uvicorn app.main:app 启动成功，日志输出启动信息 | 自动测试 |
| AC-004 | curl http://localhost:8000/health 返回 200 和 `{status:'UP',...}` JSON | 自动测试 |
| AC-005 | curl http://localhost:8000/docs 返回 Swagger UI 页面，显示 3 个路由组 | 手动测试 |
| AC-006 | 目录结构与架构文档 §3.1 完全一致 | 代码审查 |
| AC-007 | 所有 Python 包含 `__init__.py`，空目录含 `.gitkeep` | 代码审查 |
| AC-008 | main.py 使用 lifespan 参数管理生命周期，包含启动和关闭占位日志 | 代码审查 |
| AC-009 | router.py 正确聚合 3 个子路由，main.py 注册 api_router 前缀 /api | 代码审查 |
| AC-010 | .gitignore 包含关键条目 | 代码审查 |
| AC-011 | 代码中无硬编码敏感信息 | 代码审查 |

## 验证命令

```bash
# 1. 安装依赖
cd Veritas/ai-service && pip install -r requirements.txt

# 2. 验证应用导入
cd Veritas/ai-service && python -c "from app.main import app; print(app.title)"
# 预期: Literature Assistant AI Service

# 3. 验证目录结构
cd Veritas/ai-service && find app -type d | sort
# 预期: 列出所有包目录

# 4. 启动服务并测试健康检查
cd Veritas/ai-service && uvicorn app.main:app --host 0.0.0.0 --port 8000 & sleep 3 && curl http://localhost:8000/health
# 预期: 返回 {status: 'UP', ...} JSON
```
