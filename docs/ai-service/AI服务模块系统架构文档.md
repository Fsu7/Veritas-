# XH-202630 科研文献智能助手 — AI服务模块系统架构文档

> **课题编号**：XH-202630  
> **课题名称**：领域知识个性化生成与多智能体协同决策系统研究  
> **发榜单位**：上海云之脑智能科技有限公司（科大讯飞全资子公司）  
> **文档版本**：v1.4
> **创建日期**：2026年5月23日
> **文档状态**：已同步代码

---

## 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.0 | 2026-05-23 | 项目组 | 初始版本 |
| v1.1 | 2026-05-25 | 项目组 | M1修复后更新：Embedding模型bge-large-zh→bge-m3、维度校验、软件方URL空值保护、camelCase alias、/health 503、LLM超时控制、AppState重构 |
| v1.2 | 2026-06-03 | 项目组 | LLM外接API方案B切换：默认LLM从阿里云DashScope(qwen-plus)切到 **DeepSeek V4 Flash**（OpenAI 兼容，`https://api.deepseek.com/v1`）。原因：1M 上下文、推理接近 V4-Pro、价格仅 ¥1/百万 tokens（输入）。Embedding仍保留阿里云百炼 text-embedding-v4。冒烟测试已通过。 |
| v1.3 | 2026-06-08 | 项目组 | 全面同步代码实现状态：Agent工作流3节点实际架构、AgentOrchestrator SSE编排器（7种事件+keep-alive+Last-Event-ID）、Reranker复合评分、Embedding切换DashScope API优先、搜索API扩展3端点、LLM自动恢复、中文友好校验、统一响应工具、新增异常类、配置项更新 |
| v1.4 | 2026-06-08 | 项目组 | 同步代码演进：工作流升级4节点（retrieve→analyze→generate→review+条件边+重试循环）、Reviewer Agent已实现review_node并接入graph、SSE事件8种（新增review_rejected）、NODE_ORDER含reviewer、新增citation_parser.py、修正FastAPI生命周期/版本号/critical_ok/校验状态码/异常默认code/Generator返回字段等9处中影响+6处低影响差异 |

---

## 目录

- [1 文档概述](#1-文档概述)
- [2 AI服务总体架构](#2-ai服务总体架构)
- [3 项目结构与规范](#3-项目结构与规范)
- [4 API服务模块（F3.5）](#4-api服务模块f35)
- [5 多Agent协同引擎模块（F3.1）](#5-多agent协同引擎模块f31)
- [6 RAG检索模块（F3.2）](#6-rag检索模块f32)
- [7 LLM服务模块（F3.3）](#7-llm服务模块f33)
- [8 个性化引擎模块（F3.4）](#8-个性化引擎模块f34)
- [9 Embedding模型模块（F5.2）](#9-embedding模型模块f52)
- [10 向量数据库模块（F4.3）](#10-向量数据库模块f43)
- [11 论文数据采集模块（F4.4）](#11-论文数据采集模块f44)
- [12 Prompt工程规范](#12-prompt工程规范)
- [13 模块间依赖与交互](#13-模块间依赖与交互)
- [14 数据模型规范](#14-数据模型规范)
- [15 统一响应与异常处理](#15-统一响应与异常处理)
- [16 配置管理](#16-配置管理)
- [17 性能规范](#17-性能规范)
- [18 日志与监控](#18-日志与监控)
- [19 部署架构](#19-部署架构)

---

## 1 文档概述

### 1.1 编写目的

本文档详细定义科研文献智能助手系统中Python AI服务的系统架构，包括多Agent协同引擎、RAG检索、LLM服务、个性化引擎、Embedding模型等模块的设计规范，为Python AI服务开发提供完整的设计蓝图。

### 1.2 适用范围

本文档覆盖Python AI服务全部5个核心子模块及2个支撑模块：

| 模块编号 | 模块名称 | 核心职责 |
|---------|---------|---------|
| F3.1 | 多Agent协同引擎 | Agent角色定义、LangGraph工作流编排（4节点：retrieve→analyze→generate→review，含条件边+重试循环）、降级机制、SSE编排器 |
| F3.2 | RAG检索模块 | 文档向量化、语义检索、混合检索、关键词检索、重排序、搜索建议 |
| F3.3 | LLM服务模块 | 三路模型配置(软件方/外接API/本地)、推理服务、降级切换 |
| F3.4 | 个性化引擎模块 | 用户画像解析、Prompt个性化、难度/风格适配 |
| F3.5 | API服务模块 | FastAPI路由、请求校验、SSE推送、统一响应包装 |
| F5.2 | Embedding模型模块 | 文本向量化(text-embedding-v4阿里云百炼API)、批量处理 |
| F4.3 | 向量数据库模块 | Chroma向量存储、相似度检索 |

### 1.3 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.10+ | 编程语言 |
| **FastAPI** | 0.115+ | AI服务框架 |
| **Uvicorn** | 0.32+ | ASGI服务器 |
| **LangGraph** | 0.2.28+ | 多Agent编排框架 |
| **LangChain** | 0.3.0+ | LLM应用框架 |
| **Transformers** | 4.45+ | 本地模型加载（HuggingFace） |
| **Sentence-Transformers** | 3.1+ | Embedding模型加载 |
| **ChromaDB** | 0.5.0+ | 向量数据库 |
| **Pydantic** | 2.9+ | 数据验证与配置管理 |
| **Pydantic Settings** | 2.5+ | 环境变量配置管理 |
| **OpenAI SDK** | 1.50+ | 外接API调用（兼容接口） |
| **httpx** | 0.27+ | 异步HTTP客户端 |
| **Loguru** | 0.7.0 | 日志框架 |
| **NumPy** | 1.26+ | 数值计算 |
| **PyMuPDF** | 1.25+ | PDF解析 |
| **pytest** | 8.1+ | 测试框架 |

---

## 2 AI服务总体架构

### 2.1 分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                      API路由层（FastAPI Router）              │
│  请求校验(Pydantic) → 路由分发 → 调用Service → 返回Response  │
│  SSE流式推送 → 健康检查 → 模型状态查询                       │
├─────────────────────────────────────────────────────────────┤
│                    Agent协同引擎层（LangGraph）                │
│  检索Agent → 分析Agent → 生成Agent → 审核Agent（条件边）    │
│  工作流编排 → 状态管理 → 降级策略 → 超时控制 → 重试循环    │
├─────────────────────────────────────────────────────────────┤
│                      服务层（Business Services）              │
│  LLMService → EmbeddingService → VectorStoreService         │
│  PersonalizationService → SearchService                     │
├─────────────────────────────────────────────────────────────┤
│                      基础设施层（Infrastructure）             │
│  ChromaDB → DashScope text-embedding-v4(阿里云百炼 Embedding API) → DeepSeek V4 Flash(外接API)/软件方模型/本地Qwen2 │
│  PromptManager → Reranker → SearchService → Redis（可选） → MySQL（通过Java间接访问）      │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 请求流转

```
Java后端请求
    │ POST /api/agent/analyze  或  POST /api/search
    ▼
FastAPI路由层
    │ Pydantic请求校验 → 路由分发
    ▼
Agent协同引擎 / SearchService
    │
    ├── Agent协同引擎
    │   │ 检索Agent分解任务
    │   ▼
    │   检索Agent → EmbeddingService.encode() → ChromaDB.query()
    │   │ SSE推送Agent状态
    │   ▼
    │   分析Agent → LLMService.generate()（结构化提取）
    │   │ SSE推送Agent状态
    │   ▼
    │   生成Agent → PersonalizationService.build_prompt() → LLMService.generate()
    │   │ SSE推送Agent状态
    │   ▼
    │   审核Agent（条件边触发）→ citation验证+事实核查
    │   │ 审核不通过 → 重新生成（regenerate_count < 1时重试）
    │   │ SSE推送Agent状态 / review_rejected事件
    │   ▼
    │   返回最终结果
    │
    └── SearchService
        │ EmbeddingService.encode(query) → ChromaDB.query()
        ▼
        返回检索结果
```

### 2.3 与Java后端的通信边界

```
┌──────────────────────────────┐     ┌──────────────────────────────┐
│      Java后端（Spring Boot）   │     │    Python AI服务（FastAPI）    │
│                              │     │                              │
│  职责边界：                    │     │  职责边界：                    │
│  ├── 用户管理（注册/登录）     │     │  ├── 多Agent协同编排           │
│  ├── 论文元数据CRUD           │     │  ├── LLM推理服务              │
│  ├── 会话生命周期管理         │     │  ├── RAG检索                  │
│  ├── 分析任务创建/结果存储    │     │  ├── 个性化Prompt构建         │
│  ├── 缓存管理（Redis）        │     │  ├── Embedding向量化          │
│  ├── JWT鉴权                  │     │  └── Agent状态推送            │
│  └── 前端API入口              │     │                              │
│                              │     │                              │
│  不做：                       │     │  不做：                       │
│  ├── 不直接调用LLM            │     │  ├── 不管理用户账号           │
│  ├── 不操作向量数据库         │     │  ├── 不操作MySQL              │
│  └── 不构建Agent工作流        │     │  ├── 不管理JWT/鉴权          │
│                              │     │  └── 不直接与前端通信         │
└──────────────────────────────┘     └──────────────────────────────┘
         │                                      ▲
         │  HTTP REST + SSE                      │
         └──────────────────────────────────────┘
```

---

## 3 项目结构与规范

### 3.1 目录结构

```
ai-service/
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI入口，应用生命周期管理，健康检查，异常处理器
│   ├── exception.py                     # 异常体系（6类异常）
│   │
│   ├── api/                             # API路由层
│   │   ├── __init__.py
│   │   ├── router.py                    # 路由聚合（agent/search/model）
│   │   └── endpoints/
│   │       ├── __init__.py
│   │       ├── agent.py                 # Agent调用接口（POST /api/agent/analyze, /analyze/stream）
│   │       ├── search.py                # 检索接口（POST /, /hybrid, GET /suggest）
│   │       └── model.py                 # 模型状态接口（GET /api/model/status）
│   │
│   ├── core/                            # 核心配置
│   │   ├── __init__.py
│   │   ├── config.py                    # Pydantic Settings配置（环境变量）
│   │   ├── events.py                    # 启动/关闭事件（AppState 6组件+超时保护初始化）
│   │   └── logging.py                   # 日志配置（Loguru）
│   │
│   ├── agents/                          # 多Agent模块（F3.1）
│   │   ├── __init__.py
│   │   ├── base.py                      # Agent基类（含AgentState.to_dict/update_progress）
│   │   ├── coordinator.py               # 协调者Agent（已实现，未接入graph）
│   │   ├── retriever.py                 # 检索Agent（已接入graph）
│   │   ├── analyzer.py                  # 分析Agent（已接入graph，含rule-based降级）
│   │   ├── comparer.py                  # 对比Agent（已实现，未接入graph，4维度+5类矛盾根因）
│   │   ├── generator.py                 # 生成Agent（已接入graph，含citation提取+term_density+fallback报告）
│   │   ├── tools.py                     # Agent工具定义（vector_search/keyword_search/hybrid_search/rerank）
│   │   ├── graph.py                     # LangGraph工作流定义（3节点：retrieve→analyze→generate）
│   │   └── orchestrator.py             # SSE流式编排器（7种事件+keep-alive+Last-Event-ID）
│   │
│   ├── services/                        # 服务层
│   │   ├── __init__.py
│   │   ├── llm_service.py              # LLM推理服务（F3.3，三路降级+自动恢复）
│   │   ├── embedding_service.py        # Embedding向量化服务（F5.2，DashScope API优先）
│   │   ├── vector_store_service.py     # Chroma向量存储服务（F3.2+F4.3，10个方法）
│   │   ├── search_service.py           # 检索服务（F3.2，语义+关键词+混合+建议）
│   │   ├── reranker.py                 # 重排序服务（复合评分：RRF+字段+流行度+年份+个性化）
│   │   ├── personalization_service.py  # 个性化引擎服务（F3.4，agent级别差异化指令）
│   │   └── prompt_manager.py           # Prompt模板管理（string.Template渲染）
│   │
│   ├── models/                          # 数据模型
│   │   ├── __init__.py
│   │   ├── schemas.py                  # Pydantic请求/响应模型（含extra="forbid"安全策略）
│   │   └── enums.py                    # 枚举定义（StrEnum兼容）
│   │
│   └── utils/                           # 工具函数
│       ├── __init__.py
│       ├── text_processing.py          # 文本处理（分块、清洗、截断）
│       ├── citation_parser.py          # 引用解析（extract_citations/validate_citations/calculate_citation_accuracy）
│       └── response.py                 # 统一响应包装（ok/fail/fail_response/now_ts_ms）
│
├── data/                                # 数据目录
│   ├── papers/                          # 论文原始数据（JSON/PDF）
│   └── vector_db/                       # Chroma向量数据库文件
│
├── prompts/                             # Prompt模板目录
│   ├── coordinator.txt                  # 协调者Agent Prompt
│   ├── retriever.txt                    # 检索Agent Prompt
│   ├── analyzer.txt                     # 分析Agent Prompt
│   ├── comparer.txt                     # 对比Agent Prompt
│   ├── generator.txt                    # 生成Agent Prompt
│   └── reviewer.txt                     # 审核Agent Prompt（预留）
│
├── tests/                               # 测试（30+文件）
│   ├── __init__.py
│   ├── conftest.py                      # 测试配置
│   ├── test_agent_endpoint.py           # Agent端点测试
│   ├── test_analyzer_agent.py           # 分析Agent测试
│   ├── test_base_agent.py               # 基类测试
│   ├── test_comparer_agent.py           # 对比Agent测试
│   ├── test_coordinator_agent.py        # 协调者Agent测试
│   ├── test_generator_agent.py          # 生成Agent测试
│   ├── test_retriever_agent.py          # 检索Agent测试
│   ├── test_graph.py                    # 工作流测试
│   ├── test_embedding.py               # Embedding测试
│   ├── test_llm.py                      # LLM服务测试
│   ├── test_reranker.py                # 重排序测试
│   ├── test_search_service.py           # 搜索服务测试
│   ├── test_search_accuracy.py          # 搜索精度测试
│   ├── test_vector_store.py             # 向量存储测试
│   ├── test_personalization_service.py  # 个性化服务测试
│   ├── test_prompt_manager.py           # Prompt管理器测试
│   ├── test_text_processing.py          # 文本处理测试
│   ├── test_integration.py              # 集成测试
│   ├── test_integration_am3.py          # AM3集成测试
│   ├── test_degradation.py              # 降级测试
│   ├── test_sse_basic_push.py           # SSE基础推送测试
│   ├── test_sse_reconnect_frontend.py   # SSE断线重连测试
│   ├── test_sse_stability.py            # SSE稳定性测试
│   ├── test_health_model_status.py      # 健康检查/模型状态测试
│   ├── test_request_validation_response.py  # 请求校验/响应测试
│   ├── test_field_mapping_consistency.py # 字段映射一致性测试
│   ├── test_import_papers.py            # 论文导入测试
│   ├── test_validate_papers.py          # 论文校验测试
│   ├── test_performance.py              # 性能测试
│   ├── fixtures/                        # 测试夹具
│   ├── integration/                     # 集成测试
│   ├── performance/                     # 性能测试
│   └── test_data/                       # 测试数据
│
├── scripts/                             # 工具脚本
│   ├── import_papers.py                # 论文数据导入脚本
│   ├── build_vector_db.py              # 向量数据库构建脚本
│   ├── evaluate_search.py              # 检索评估脚本
│   ├── fetch_arxiv_json.py             # arXiv数据获取脚本
│   ├── list_chroma_papers.py           # Chroma论文列表脚本
│   ├── sync_chroma_to_mysql.py         # Chroma→MySQL同步脚本
│   ├── validate_papers.py              # 论文数据校验脚本
│   └── start_test_server.sh            # 测试服务器启动脚本
│
├── docs/                                # 项目文档
│   ├── AM3_BUGFIX_LOG.md               # AM3修复日志
│   ├── AM3_TEST_REPORT.md              # AM3测试报告
│   ├── DEGRADATION_TEST_REPORT.md      # 降级测试报告
│   └── FIELD_MAPPING.md                # 字段映射文档
│
├── Dockerfile                           # Docker构建文件
├── .dockerignore                        # Docker忽略文件
├── requirements.txt                     # Python依赖
├── .env.example                         # 环境变量示例
├── .gitignore                           # Git忽略文件
├── validation_report.json               # 校验报告
└── README.md                            # 项目说明
```

### 3.2 命名规范

| 类别 | 规范 | 示例 |
|------|------|------|
| 文件名 | 小写下划线 | `llm_service.py` |
| 类名 | 大驼峰 | `LLMService` |
| 函数/方法 | 小写下划线 | `generate_report()` |
| 常量 | 大写下划线 | `DEFAULT_TOP_K` |
| Pydantic模型 | 大驼峰+后缀 | `AnalyzeRequest` / `AnalyzeResponse` |
| 枚举类 | 大驼峰 | `AnalysisType` |
| 环境变量 | 大写下划线 | `LLM_MODE` |
| API路径 | 小写连字符 | `/api/agent/analyze` |

---

## 4 API服务模块（F3.5）

### 4.1 模块概述

基于FastAPI的API服务层，是Python AI服务对外暴露的唯一入口。负责请求校验、路由分发、SSE流式推送和健康检查。

### 4.2 FastAPI应用生命周期

```python
# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.api.router import api_router
from app.core.events import on_startup, on_shutdown
from app.utils.response import ok, fail, now_ts_ms

@asynccontextmanager
async def lifespan(app: FastAPI):
    await on_startup()
    yield
    await on_shutdown()

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

# 注册路由
app.include_router(api_router, prefix="/api")


# ===== 异常处理器 =====

@app.exception_handler(AIServiceException)
async def ai_service_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": None,
            "timestamp": now_ts_ms(),
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Pydantic 422校验错误：返回中文友好message"""
    error_list = exc.errors() if hasattr(exc, "errors") else []
    msg = _extract_chinese_field_message(error_list)
    return JSONResponse(
        status_code=422,
        content={
            "code": 422,
            "message": msg,
            "data": None,
            "timestamp": now_ts_ms(),
        }
    )

def _extract_chinese_field_message(errors: list) -> str:
    """中文友好的校验错误提取（直接用loc路径+错误类型判断）"""
    if not errors:
        return "参数校验失败"
    parts = []
    for err in errors:
        loc = err.get("loc", [])
        field = ".".join(str(x) for x in loc[1:]) if len(loc) > 1 else (str(loc[0]) if loc else "未知字段")
        err_type = err.get("type", "")
        if err_type == "missing":
            parts.append(f"{field} 字段必填")
        elif err_type == "string_too_short":
            parts.append(f"{field} 不能为空")
        elif err_type in ("enum", "literal_error"):
            parts.append(f"{field} 取值非法")
        elif err_type.startswith("value_error"):
            parts.append(f"{field} 校验失败")
        else:
            msg = err.get("msg", "校验失败")
            parts.append(f"{field}: {msg}")
    return "参数校验失败: " + "; ".join(parts)


# ===== 健康检查 =====

@app.get("/health")
async def health_check():
    """健康检查（3组件 critical_ok 规则 + 统一响应格式）"""
    data = _build_health_data()  # 6组件: llm, embedding, chroma, prompts, searchService, reranker
    critical_ok = _is_critical_ok(data)
    data["status"] = "UP" if critical_ok else "DEGRADED"
    response = ok(data=data, message="success" if critical_ok else "DEGRADED")
    return JSONResponse(status_code=200 if critical_ok else 503, content=response)

def _build_health_data() -> dict:
    """构建6组件健康数据"""
    return {
        "llm": app_state.llm_service.status if app_state.llm_service else "not_loaded",
        "embedding": app_state.embedding_service.status if app_state.embedding_service else "not_loaded",
        "chroma": app_state.vector_store_service.status if app_state.vector_store_service else "not_connected",
        "prompts": app_state.prompt_manager.status if app_state.prompt_manager else "not_loaded",
        "searchService": "ready" if app_state.search_service else "not_initialized",
        "reranker": "ready" if app_state.reranker else "not_initialized",
    }

def _is_critical_ok(data: dict) -> bool:
    """判断关键组件是否正常（llm + embedding + chroma，共3组件）"""
    return (
        data["llm"] == "loaded"
        and data["embedding"] in ("loaded", "loaded_api", "loaded_local")
        and data["chroma"] == "connected"
    )
```

### 4.3 路由定义

```python
# core/events.py
class AppState:
    """应用全局状态（替代全局变量）"""
    embedding_service = None
    vector_store_service = None
    llm_service = None
    prompt_manager = None
    search_service = None
    reranker = None

app_state = AppState()

# api/router.py
from fastapi import APIRouter
from app.api.endpoints import agent, search, model

api_router = APIRouter()

api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(model.router, prefix="/model", tags=["model"])
```

### 4.4 接口详细设计

#### 4.4.1 Agent调用接口

```python
# api/endpoints/agent.py
from fastapi import APIRouter, BackgroundTasks
from sse_starlette.sse import EventSourceResponse

router = APIRouter()

@router.post("/analyze")
async def analyze(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    启动Agent协同分析任务

    请求体：
    {
        "topic": "Multi-Agent协同决策",
        "paperIds": ["arxiv_2024_001", "arxiv_2024_002"],
        "userProfile": {
            "educationLevel": "master",
            "researchField": "NLP",
            "knowledgeLevel": "intermediate",
            "preferredStyle": "balanced"
        },
        "analysisType": "report",          // paper_analysis / compare / report
        "analysisId": "anl_20240523_001"   // Java端生成的任务ID
    }

    响应：
    {
        "analysisId": "anl_20240523_001",
        "status": "processing",
        "agentStates": [...]
    }
    """
    # 1. 校验请求
    # 2. 启动Agent工作流（异步）
    # 3. 返回任务ID和初始状态
    result = await agent_orchestrator.run(request)
    return AnalyzeResponse(
        analysisId=request.analysisId,
        status="processing",
        agentStates=result.agent_states
    )

@router.post("/analyze/stream", response_class=EventSourceResponse)
async def analyze_stream(request: AnalyzeRequest):
    """
    启动Agent协同分析任务，SSE流式推送Agent状态

    SSE事件格式：
    event: agent_state_update
    data: {"agentName": "retriever", "status": "running", "progress": 0.3}

    event: agent_state_update
    data: {"agentName": "retriever", "status": "completed", "intermediateResult": "找到10篇论文"}

    event: analysis_completed
    data: {"analysisId": "anl_001", "status": "completed"}
    """
    async def event_generator():
        async for event in agent_orchestrator.run_stream(request):
            yield {
                "event": event.event_type,
                "data": event.json()
            }
    return EventSourceResponse(event_generator())
```

#### 4.4.2 检索接口

```python
# api/endpoints/search.py
@router.post("")
async def search(request: SearchRequest) -> SearchResponse:
    """
    语义检索论文

    请求体：
    {
        "query": "Multi-Agent协同决策",
        "topK": 10,
        "filters": {
            "yearFrom": 2020,
            "yearTo": 2024,
            "venue": "ACL"
        }
    }

    响应：
    {
        "results": [
            {
                "paperId": "arxiv_2024_001",
                "title": "...",
                "abstract": "...",
                "score": 0.92,
                "year": 2024,
                "venue": "ACL"
            }
        ],
        "total": 15
    }
    """
    results = await search_service.search(request.query, request.top_k, request.filters)
    return SearchResponse(results=results, total=len(results))
```

#### 4.4.3 模型状态

```python
# api/endpoints/model.py
from app.utils.response import ok

@router.get("/status")
async def model_status():
    """
    查询模型加载状态（12字段）

    响应（统一格式）：
    {
        "code": 200,
        "data": {
            "llm": "loaded",                     // loading / loaded / error
            "embedding": "loaded_api",            // loading / loaded / loaded_api / loaded_local / error
            "chroma": "connected",                // connected / disconnected / error
            "prompts": "loaded",                  // loaded / not_loaded / error
            "embeddingDimension": 1024,           // 向量维度
            "activeLlmProvider": "api",           // builtin / api / local
            "providerCandidates": ["api"],        // 可用Provider列表
            "chromaPaperCount": 200,              // Chroma中论文数量
            "gpuMemoryUsed": "4.2GB / 16GB",      // GPU显存使用
            "llmProviderCount": 1,                // 已初始化Provider数量
            "searchService": "initialized",       // initialized / not_initialized
            "reranker": "initialized"             // initialized / not_initialized
        },
        "timestamp": 1716451200000
    }
    """
    data = _build_model_status()
    return ok(data=data)
```

#### 4.4.4 健康检查

> 健康检查端点已在4.2节 `main.py` 中定义，采用3组件+critical_ok规则+统一响应格式。
> 关键组件：llm + embedding + chroma，任一不可用则返回503 DEGRADED。

### 4.5 API接口清单

| 编号 | 方法 | 路径 | 优先级 | 说明 |
|------|------|------|--------|------|
| F3.5.1 | POST | `/api/agent/analyze` | P0 | 启动Agent分析任务 |
| F3.5.1 | POST | `/api/agent/analyze/stream` | P1 | Agent分析+SSE推送（8种事件+keep-alive+Last-Event-ID+review_rejected） |
| F3.5.2 | POST | `/api/search/` | P0 | 语义检索论文 |
| F3.5.2 | POST | `/api/search/hybrid` | P1 | 混合检索（语义+关键词+RRF融合+个性化重排序） |
| F3.5.2 | GET | `/api/search/suggest` | P2 | 搜索建议（标题自动补全） |
| F3.5.3 | GET | `/health` | P0 | 健康检查（3组件critical_ok规则） |
| F3.5.4 | GET | `/api/model/status` | P1 | 模型状态查询（12字段） |

---

## 5 多Agent协同引擎模块（F3.1）

### 5.1 模块概述

基于LangGraph编排4个核心Agent的协同工作流（retrieve→analyze→generate→review，含条件边+重试循环），同时实现了Coordinator/Comparer Agent但尚未接入graph。通过AgentOrchestrator实现SSE流式编排，支持8种事件类型、keep-alive心跳和断线重连。

### 5.2 Agent角色定义

| Agent | 文件 | 角色定位 | 接入状态（2026-06-28 复验） | 核心工具 |
|-------|------|---------|---------|---------|
| **协调者Agent** | `coordinator.py`（538行） | 项目经理 | ✅ 已接入graph（graph.py:469 coordinator_node） | LLM任务分解+规则降级 |
| **检索Agent** | `retriever.py` | 图书管理员 | ✅ 已接入graph | hybrid_search+reranker |
| **分析Agent** | `analyzer.py` | 论文审稿人 | ✅ 已接入graph | LLM 5维度提取+rule-based降级 |
| **对比Agent** | `comparer.py`（795行） | 对比研究员 | ✅ 已接入graph（条件边：论文数>=2 触发） | LLM 4维度对比+5类矛盾根因+规则降级 |
| **生成Agent** | `generator.py` | 学术写手 | ✅ 已接入graph | LLM生成+citation提取+term_density+fallback报告 |
| **审核Agent** | `reviewer.py`（358行） | 学术编辑 | ✅ 已接入graph（review_node + 条件边触发重试） | citation验证+事实核查+4级JSON解析降级+重试建议 |

> **⚠️ 阻断性警告**：因 `app/models/` 目录缺失（schemas.py + enums.py 不存在），所有 Agent 的 import 断裂，graph.py 无法实际启动。但 6 Agent 类 + graph.py 工作流的**代码逻辑已完整**，修复 schemas 后即可启动。

### 5.3 Agent基类设计

```python
# agents/base.py
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

class AgentStatus(str, Enum):
    WAITING = "waiting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class AgentState:
    """Agent运行状态（用于可视化）"""
    name: str
    status: AgentStatus = AgentStatus.WAITING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    progress: float = 0.0
    intermediate_result: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """序列化为dict（用于SSE推送）"""
        ...

    def update_progress(self, progress: float, intermediate_result: Optional[str] = None) -> None:
        """更新进度和中间结果"""
        ...

class BaseAgent(ABC):
    """Agent基类"""

    def __init__(self, name: str, llm_service, prompt_manager, timeout: int = None):
        self.name = name
        self.llm_service = llm_service
        self.prompt_manager = prompt_manager
        self.state = AgentState(name=name)
        self.timeout = timeout if timeout is not None else settings.AGENT_TIMEOUT

    async def execute(self, input_data: dict, context: dict) -> dict:
        """执行Agent任务（含状态管理和超时控制）"""
        # 1. 更新状态为running
        self.state.status = AgentStatus.RUNNING
        self.state.started_at = datetime.now()

        try:
            # 2. 执行核心逻辑（带超时控制）
            result = await asyncio.wait_for(
                self._run(input_data, context),
                timeout=self.timeout
            )

            # 3. 更新状态为completed
            self.state.status = AgentStatus.COMPLETED
            self.state.completed_at = datetime.now()
            self.state.duration_ms = int(
                (self.state.completed_at - self.state.started_at).total_seconds() * 1000
            )
            self.state.intermediate_result = self._summarize_result(result)

            return result

        except asyncio.TimeoutError:
            self.state.status = AgentStatus.FAILED
            self.state.error = f"Agent {self.name} timed out after {self.timeout}s"
            logger.warning(self.state.error)
            return self._fallback_result(input_data)

        except Exception as e:
            self.state.status = AgentStatus.FAILED
            self.state.error = str(e)
            logger.error(f"Agent {self.name} failed: {e}")
            return self._fallback_result(input_data)

    @abstractmethod
    async def _run(self, input_data: dict, context: dict) -> dict:
        """子类实现的核心执行逻辑"""
        pass

    def _fallback_result(self, input_data: dict) -> dict:
        """降级时的默认返回"""
        return {"degraded": True, "agent": self.name, "error": self.state.error}

    def _summarize_result(self, result: dict) -> str:
        """生成中间结果摘要（用于可视化）"""
        return str(result)[:200]
```

### 5.4 各Agent详细设计

#### 5.4.1 协调者Agent（Coordinator）— 已实现但未接入graph

```python
# agents/coordinator.py
class CoordinatorAgent(BaseAgent):
    """
    协调者Agent — 项目经理角色（已实现但未接入graph）

    职责：
    1. 接收用户问题和画像
    2. 使用LLM分解为子任务
    3. 计算requires_compare/requires_review标记
    4. LLM失败时规则降级分解
    """

    def __init__(self, llm_service, prompt_manager, timeout=30,
                 llm_temperature=0.3, llm_max_tokens=1024):
        super().__init__("coordinator", llm_service, prompt_manager, timeout)
        self.llm_temperature = llm_temperature
        self.llm_max_tokens = llm_max_tokens

    async def _run(self, input_data: dict, context: dict) -> dict:
        # 1. Prompt注入防护
        topic = self._sanitize_topic(input_data.get("topic", ""))

        # 2. 使用LLM分析用户问题，分解子任务
        task_breakdown = await self.llm_service.generate(prompt)

        # 3. 解析LLM输出的任务分解
        tasks = self._parse_task_breakdown(task_breakdown, input_data)

        # 4. 计算条件标记
        return {
            "sub_tasks": tasks,
            "task_count": len(tasks),
            "requires_compare": len(input_data.get("paperIds", [])) >= 2,
            "requires_review": False
        }

    def _parse_task_breakdown(self, breakdown: str, input_data: dict) -> list:
        """解析LLM生成的任务分解结果（4种JSON提取策略）"""
        # 提取JSON → 过滤VALID_TASK_TYPES → 2-5约束
        ...

    def _rule_based_decomposition(self, input_data: dict) -> list:
        """LLM失败时的规则降级分解"""
        ...

    def _sanitize_topic(self, topic: str) -> str:
        """Prompt注入防护（MAX_QUERY_LENGTH=500）"""
        ...

    def _fallback_result(self, input_data: dict) -> dict:
        """覆盖基类，使用规则分解"""
        return {
            "degraded": True,
            "agent": self.name,
            "sub_tasks": self._rule_based_decomposition(input_data),
            "requires_compare": len(input_data.get("paperIds", [])) >= 2,
            "requires_review": False
        }
```

#### 5.4.2 检索Agent（Retriever）

```python
# agents/retriever.py
class RetrieverAgent(BaseAgent):
    """
    检索Agent — 图书管理员角色

    职责：
    1. 接收检索关键词
    2. LLM生成搜索策略（core_keywords+filters）
    3. 执行hybrid_search（向量+关键词混合检索）
    4. reranker个性化重排序
    5. 返回Top10结果
    """

    def __init__(self, llm_service, prompt_manager, search_service,
                 reranker=None, timeout=30):
        super().__init__("retriever", llm_service, prompt_manager, timeout)
        self.search_service = search_service
        self.reranker = reranker

    async def _run(self, input_data: dict, context: dict) -> dict:
        topic = input_data.get("topic", "")
        user_profile = context.get("user_profile", {})

        # 1. LLM生成搜索策略
        strategy = await self._generate_search_strategy(topic, user_profile)

        # 2. hybrid_search混合检索
        papers = await self.search_service.hybrid_search(
            query=topic,
            core_keywords=strategy.get("core_keywords", [topic]),
            filters=strategy.get("filters", {}),
            top_k=input_data.get("top_k", 10)
        )

        # 3. reranker个性化重排序
        if self.reranker and papers:
            papers = await self.reranker.rerank(papers, user_profile)

        self.state.intermediate_result = f"找到{len(papers)}篇相关论文"

        return {
            "papers": papers[:input_data.get("top_k", 10)],
            "total_found": len(papers)
        }

    async def _generate_search_strategy(self, topic: str, user_profile: dict) -> dict:
        """LLM生成搜索策略（core_keywords+filters）"""
        ...

    def _parse_search_strategy(self, result_text: str, topic: str) -> dict:
        """解析JSON搜索策略，失败时使用fallback topic"""
        ...
```

#### 5.4.3 分析Agent（Analyzer）

```python
# agents/analyzer.py
class AnalyzerAgent(BaseAgent):
    """
    分析Agent — 论文审稿人角色

    职责：
    1. 接收论文全文/摘要
    2. 使用LLM提取5个维度核心信息
    3. 输出结构化dict（每维度含summary+confidence+references）
    4. LLM失败时rule-based降级提取
    5. 支持个性化指令差异化

    5维度：
    - 研究问题（Research Question）
    - 核心方法（Core Method）
    - 主要实验（Key Experiments）
    - 核心结论（Core Findings）
    - 局限性（Limitations）
    """

    def __init__(self, llm_service, prompt_manager,
                 personalization_service=None, max_papers=10,
                 timeout=30, llm_temperature=0.3, llm_max_tokens=2048):
        super().__init__("analyzer", llm_service, prompt_manager, timeout)
        self.personalization_service = personalization_service
        self.max_papers = max_papers
        self.llm_temperature = llm_temperature
        self.llm_max_tokens = llm_max_tokens

    async def _run(self, input_data: dict, context: dict) -> dict:
        papers = input_data.get("papers", [])
        analysis_results = []

        for i, paper in enumerate(papers[:self.max_papers]):
            self.state.update_progress(
                (i + 1) / len(papers),
                f"已分析{i+1}/{len(papers)}篇"
            )

            # 获取个性化指令
            extra_instruction = self._get_extra_instruction(context)

            # 构建分析Prompt → 调用LLM提取
            result_text = await self.llm_service.generate(prompt)

            # 解析为结构化dict
            analysis = self._parse_analysis(result_text, paper)

            # 维度校验
            analysis = self._validate_dimensions(analysis)

            analysis_results.append(analysis)

        return {
            "analysis_results": analysis_results,
            "analyzed_count": len(analysis_results)
        }

    def _validate_dimensions(self, analysis: dict) -> dict:
        """校验每个维度数据类型（summary: str, confidence: float, references: list）"""
        ...

    def _rule_based_extraction(self, paper: dict) -> dict:
        """LLM失败时的规则提取（confidence=0.3）"""
        ...

    def _get_extra_instruction(self, context: dict) -> str:
        """通过personalization_service获取agent级别差异化指令"""
        ...

    def _fallback_result(self, input_data: dict) -> dict:
        """覆盖基类，对所有论文使用rule-based提取"""
        papers = input_data.get("papers", [])
        return {
            "degraded": True,
            "agent": self.name,
            "analysis_results": [self._rule_based_extraction(p) for p in papers],
            "analyzed_count": len(papers)
        }
```

#### 5.4.4 对比Agent（Comparer）— 已实现但未接入graph

```python
# agents/comparer.py
class ComparerAgent(BaseAgent):
    """
    对比Agent — 对比研究员角色（已实现但未接入graph）

    职责：
    1. 接收2-5篇论文的分析结果
    2. LLM 4维度对比：research_problem, core_method, main_experiments, core_conclusions
    3. 5类矛盾根因：dataset_bias, metric_difference, condition_difference,
       assumption_difference, methodological_conflict
    4. LLM失败时规则降级：C(N,2)两两对比+Jaccard相似度+矛盾关键词检测
    """

    def __init__(self, llm_service, prompt_manager, timeout=30,
                 llm_temperature=0.4, llm_max_tokens=3072):
        super().__init__("comparer", llm_service, prompt_manager, timeout)
        self.llm_temperature = llm_temperature
        self.llm_max_tokens = llm_max_tokens

    async def _run(self, input_data: dict, context: dict) -> dict:
        analysis_results = input_data.get("analysis_results", [])

        # 构建对比Prompt → 调用LLM生成对比
        result_text = await self.llm_service.generate(prompt)

        # 解析对比结果
        comparison = self._parse_comparison(result_text)

        return {
            "comparison_table": comparison.get("table", {}),
            "summary": comparison.get("summary", ""),
            "conflicts": comparison.get("conflicts", []),
            "disclaimer": "⚠️ AI生成内容仅供参考，请以原始论文为准"
        }

    def _rule_based_comparison(self, analysis_results: list) -> dict:
        """C(N,2)两两对比+Jaccard相似度+矛盾关键词检测"""
        ...

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """简化Jaccard相似度（字符+2-gram）"""
        ...

    def _detect_conflict_keywords(self, text: str) -> list:
        """12个中英文矛盾关键词检测"""
        ...
```

#### 5.4.5 生成Agent（Generator）

```python
# agents/generator.py
class GeneratorAgent(BaseAgent):
    """
    生成Agent — 学术写手角色

    职责：
    1. 接收分析结果和用户画像
    2. 构建个性化Prompt
    3. LLM生成文献综述
    4. 报告验证（5个必需章节）
    5. citation提取（[Author, Year]和[数字]两种格式）
    6. term_density计算（约48个学术术语）
    7. LLM失败时生成模板报告
    """

    def __init__(self, llm_service, prompt_manager,
                 personalization_service=None, timeout=30,
                 llm_temperature=0.7, llm_max_tokens=4096):
        super().__init__("generator", llm_service, prompt_manager, timeout)
        self.personalization_service = personalization_service
        self.llm_temperature = llm_temperature
        self.llm_max_tokens = llm_max_tokens

    async def _run(self, prompt: str, input_data: dict, context: dict) -> dict:
        # 1. 构建个性化Prompt
        user_profile = context.get("user_profile", {})
        try:
            full_prompt = self.build_prompt(input_data, context)
        except Exception:
            full_prompt = prompt

        # 2. LLM生成综述
        llm_output = await self.llm_service.generate(full_prompt, ...)

        # 3. 报告验证（5个必需章节，缺失时自动补占位符）
        validation = self._validate_report(llm_output)
        report = validation["report"]

        # 4. citation提取
        citation_list = self._extract_citations(report, analysis_results)

        # 5. term_density计算
        term_density_actual = self._calculate_term_density(report, knowledge_level)

        # 6. 个性化应用记录
        personalization_applied = self._build_personalization_applied(user_profile)

        # 7. AI免责声明
        AI_DISCLAIMER = "⚠️ 本内容由 AI 生成，仅供参考"
        if AI_DISCLAIMER not in report:
            report = report.rstrip() + "\n\n" + AI_DISCLAIMER

        return {
            "report": report,
            "citation_list": citation_list,
            "term_density_actual": term_density_actual,
            "personalization_applied": personalization_applied,
        }

    def _extract_citations(self, report: str) -> list:
        """提取[Author, Year]和[数字]两种引用格式"""
        ...

    def _validate_report(self, report: str) -> str:
        """检查5个必需章节，缺失时自动补占位符"""
        ...

    def _calculate_term_density(self, report: str) -> dict:
        """约48个学术术语密度计算"""
        ...

    def _generate_fallback_report(self, input_data: dict) -> str:
        """LLM失败时生成模板报告（5章节占位符）"""
        ...

    def _fallback_result(self, input_data: dict) -> dict:
        """覆盖基类，使用模板报告"""
        report = self._generate_fallback_report(input_data)
        return {
            "degraded": True,
            "agent": self.name,
            "report": report,
            "citations": [],
            "term_density": {},
            "word_count": len(report)
        }
```

#### 5.4.6 审核Agent（Reviewer）— ✅ 已实现，条件边触发

```python
# agents/graph.py — review_node
async def review_node(state: WorkflowState, agent_instances: Dict[str, Any]) -> dict:
    """审核节点：调用 ReviewerAgent 审核生成结果

    触发条件：should_review() 返回 True（report非空且非退化）
    审核不通过：regenerate_count < 1 时触发重新生成循环
    Reviewer不存在：跳过审核，标记approved=True（不阻塞流程）
    Reviewer降级：标记approved=True（不阻塞流程）
    """

    reviewer = agent_instances.get("reviewer")
    if reviewer is None:
        # Reviewer不存在时跳过审核，直接标记通过
        return {
            "review_result": {"approved": True, "issues": [], "suggestions": [],
                              "citation_accuracy": 1.0, "fact_accuracy": 1.0},
            "agent_states": {..., "reviewer": {"status": "skipped"}},
        }

    result = await reviewer.execute(
        input_data={"report": report, "original_papers": search_results,
                     "retry_context": retry_context},
        context={"user_profile": user_profile},
    )

    review_result = {
        "approved": result.get("approved", False),
        "issues": result.get("issues", []),
        "suggestions": result.get("suggestions", []),
        "citation_accuracy": result.get("citation_accuracy", 0.0),
        "fact_accuracy": result.get("fact_accuracy", 0.0),
    }

    # 审核不通过 → 递增regenerate_count → 触发重新生成
    if not review_result.get("approved", True):
        update["regenerate_count"] = regenerate_count + 1

    # Reviewer降级 → 标记approved=True，不阻塞流程
    if result.get("degraded", False):
        review_result["approved"] = True

def should_review(state: WorkflowState) -> bool:
    """条件边：report非空且非退化时进入审核"""
    report = state.get("report", "")
    degraded = state.get("degraded", False)
    return bool(report and report.strip()) and not (degraded and not state.get("review_result"))

def should_regenerate(state: WorkflowState) -> str:
    """条件边：审核不通过且regenerate_count < 1时返回'regenerate'，否则返回'end'"""
    review_result = state.get("review_result") or {}
    approved = review_result.get("approved", True)
    regenerate_count = state.get("regenerate_count", 0)
    if not approved and regenerate_count < 1:
        return "regenerate"
    return "end"
```

> **运行时说明**：当前 `agent.py` 的 `_build_agent_instances()` 仅创建 retriever/analyzer/generator 三个实例，未实例化 reviewer。因此运行时 review_node 会走"跳过审核"路径，直接标记 approved=True。如需启用审核功能，需在 `_build_agent_instances()` 中添加 reviewer 实例。

### 5.5 LangGraph工作流定义

```python
# agents/graph.py
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any, Optional

class WorkflowState(TypedDict):
    """LangGraph工作流状态定义"""
    # 输入
    query: str                          # 用户原始查询
    user_profile: Dict[str, Any]        # 用户画像
    analysis_type: str                  # 分析类型
    analysis_id: str                    # 分析任务ID

    # 中间状态
    sub_tasks: List[str]                # 分解的子任务
    search_results: List[Dict]          # 检索结果
    analysis_results: List[Dict]        # 分析结果
    compare_result: Optional[Dict]      # 对比结果
    report: Optional[str]               # 生成的综述
    review_result: Optional[Dict]       # 审核结果
    citations: List[Dict]               # 引用列表

    # 最终输出
    final_output: Optional[str]         # 最终输出
    agent_states: Dict[str, Dict]       # 各Agent状态（用于可视化）

    # 错误处理
    errors: List[Dict]                  # 错误记录
    degraded: bool                      # 是否降级
    regenerate_count: int               # 重新生成次数

    # 时间追踪
    started_at: Optional[str]           # 开始时间
    completed_at: Optional[str]         # 完成时间


def build_agent_graph(agent_instances: Dict[str, Any]) -> StateGraph:
    """构建4节点Agent协同工作流图（含条件边+重试循环）"""

    # 创建状态图
    graph = StateGraph(WorkflowState)

    # 添加4个核心节点
    graph.add_node("retrieve", _retrieve)
    graph.add_node("analyze", _analyze)
    graph.add_node("generate", _generate)
    graph.add_node("review", _review)

    # 设置入口
    graph.set_entry_point("retrieve")

    # 线性边：retrieve → analyze → generate
    graph.add_edge("retrieve", "analyze")
    graph.add_edge("analyze", "generate")

    # 条件边：generate → review | END
    graph.add_conditional_edges(
        "generate",
        _should_review,    # should_review(): report非空且非退化→"review"，否则→"end"
        {"review": "review", "end": END},
    )

    # 条件边：review → regenerate(→generate) | END
    graph.add_conditional_edges(
        "review",
        _should_regenerate,  # should_regenerate(): 审核不通过且count<1→"regenerate"，否则→"end"
        {"regenerate": "generate", "end": END},
    )

    return graph.compile()
```

#### 5.5.1 AgentOrchestrator SSE编排器

```python
# agents/orchestrator.py
class AgentOrchestrator:
    """流式Agent编排器 — SSE事件实时推送"""
    NODE_ORDER = ["retriever", "analyzer", "generator", "reviewer"]
    PING_INTERVAL = 15  # keep-alive心跳间隔

    # 8种SSE事件类型：
    # agent_started     : Agent开始执行
    # agent_state_update: Agent状态变更（progress更新）
    # agent_completed    : Agent正常完成
    # agent_failed       : Agent执行失败（不中断流）
    # analysis_completed : 全流程结束
    # error              : 错误事件
    # ping               : keep-alive心跳
    # review_rejected    : 审核不通过，触发重新生成

    # task30增强：
    # - Keep-alive ping：距上次事件 > 15s 时自动 yield ping 事件
    # - Last-Event-ID：支持断线重连，跳过已发送事件
    # - 客户端断开优雅处理：捕获 asyncio.CancelledError

    # Reviewer重试循环（orchestrator层面）：
    # - reviewer存在且report非空时进入审核
    # - 审核不通过且regenerate_count < 1时触发重新生成
    # - 最多执行2次：首次审核 + 1次重试
    # - yield review_rejected事件通知客户端
```

### 5.6 工作流可视化

```
START → retrieve → analyze → generate → [should_review?]
                                              │
                                    ┌─────────┴─────────┐
                                    │ Yes                │ No
                                    ▼                    ▼
                                  review → [should_regenerate?]
                                              │
                                    ┌─────────┴─────────┐
                                    │ regenerate        │ end
                                    ▼                   ▼
                                  generate ←─────────── END
                                    │
                                    └──→ (重新进入条件判断)

SSE事件序列：
├── agent_started(retriever)
├── agent_state_update(retriever, progress=0.1)
├── agent_completed(retriever, "Found N papers")
├── agent_started(analyzer)
├── agent_state_update(analyzer, progress=0.5, "Analyzing 5/10")
├── agent_completed(analyzer, "Analyzed 10 papers")
├── agent_started(generator)
├── agent_state_update(generator, progress=0.4, "Generating review")
├── agent_completed(generator, "Report generated")
├── agent_started(reviewer)          ← 条件边触发
├── agent_completed(reviewer, "Review approved")
│   └── 或 agent_failed(reviewer) + review_rejected事件 + 重新生成
└── analysis_completed(status="completed")

超时控制：
├── 单节点超时：30秒
├── 全流程超时：120秒
├── keep-alive ping：15秒间隔
└── 重试循环：最多1次重新生成（regenerate_count < 1）
```

### 5.7 降级策略

```
降级层级：

Level 0：全Agent协同（正常模式）
├── 4个Agent按LangGraph工作流执行（含条件边+重试循环）
├── 每个Agent内部有LLM失败→规则降级
└── 全流程耗时目标：60秒内

Level 1：单Agent内部降级
├── RetrieverAgent：LLM搜索策略失败→使用原始topic
├── AnalyzerAgent：LLM分析失败→rule-based提取（confidence=0.3）
├── GeneratorAgent：LLM生成失败→模板报告（5章节占位符）
├── ReviewerAgent：审核失败→标记approved=True（不阻塞流程）
└── 标记 degraded=True，记录错误信息

Level 2：Agent执行超时/异常
├── 单Agent超时(30s)→BaseAgent.execute()捕获→_fallback_result()
├── Agent不存在→graph节点返回空结果+errors记录
├── Reviewer不存在→跳过审核，标记approved=True
└── 不中断后续Agent执行

Level 3：全流程超时/异常
├── 全流程超时(120s)→run_workflow()捕获→返回部分结果
├── 工作流异常→返回错误信息+降级标记
└── 最终结果标注"已降级"

Level 4：审核重试循环
├── 审核不通过→regenerate_count < 1时触发重新生成
├── 重新生成后再次审核→仍不通过→标记降级但返回结果
└── 最多重试1次（regenerate_count上限=1）
```

### 5.8 Agent状态管理（SSE事件格式）

```python
# 8种SSE事件格式

# 1. agent_started
event: agent_started
data: {"agentName":"retriever","status":"running","analysisId":"anl_001","timestamp":1716451200000}

# 2. agent_state_update
event: agent_state_update
data: {"agentName":"retriever","status":"running","progress":0.6,"analysisId":"anl_001","intermediateResult":"Searching...","durationMs":0}

# 3. agent_completed
event: agent_completed
data: {"agentName":"retriever","status":"completed","progress":1.0,"analysisId":"anl_001","intermediateResult":"Found 10 papers","durationMs":1200}

# 4. agent_failed
event: agent_failed
data: {"agentName":"analyzer","status":"failed","analysisId":"anl_001","errorMessage":"Agent timed out","durationMs":30000}

# 5. analysis_completed
event: analysis_completed
data: {"analysisId":"anl_001","status":"completed","finalReport":"...","degraded":false,"degradedReason":null,"totalDurationMs":25000}

# 6. error
event: error
data: {"analysisId":"anl_001","errorCode":500,"errorMessage":"analyzer failed: timeout"}

# 7. ping（keep-alive）
event: ping
data: {}

# 8. review_rejected（审核不通过，触发重新生成）
event: review_rejected
data: {"agentName":"reviewer","analysisId":"anl_001","regenerateCount":1,"issues":[{"claim":"...","error_type":"citation_error"}]}
```

### 5.9 功能清单

| 编号 | 功能 | 优先级 | 状态 | 说明 |
|------|------|--------|------|------|
| F3.1.1 | 协调者Agent | P0 | ✅ 已接入 graph（graph.py:469 coordinator_node） | LLM任务分解+规则降级+Prompt注入防护 |
| F3.1.2 | 检索Agent | P0 | ✅ 已接入 | hybrid_search+LLM搜索策略+reranker |
| F3.1.3 | 分析Agent | P0 | ✅ 已接入 | 5维度dict结构+rule-based降级+个性化指令 |
| F3.1.4 | 对比Agent | P1 | ✅ 已接入 graph（条件边：论文数>=2 触发） | 4维度对比+5类矛盾根因+规则降级 |
| F3.1.5 | 生成Agent | P0 | ✅ 已接入 | citation提取+term_density+报告验证+fallback |
| F3.1.6 | 审核Agent | P1 | ✅ 已实现 review_node（reviewer.py 358行），条件边触发 + 重试循环 | citation验证+事实核查+4级JSON解析降级+重试建议 |
| F3.1.7 | 工作流编排 | P0 | ✅ 已实现（6 节点 LangGraph StateGraph + 条件边 + 重试循环） | coordinator→retrieve→analyze→[compare]→generate→[review→regenerate]→END |
| F3.1.8 | SSE流式编排 | P0 | ✅ 已实现 | AgentOrchestrator，8种事件+keep-alive+Last-Event-ID+review_rejected |
| F3.1.9 | 降级机制 | P0 | ✅ 已实现 | Agent内部降级+超时降级+全流程降级 |

---

## 6 RAG检索模块（F3.2）

### 6.1 模块概述

基于向量语义检索和关键词检索的混合RAG（Retrieval-Augmented Generation）模块，为检索Agent和搜索接口提供论文检索能力。

### 6.2 类设计

#### 6.2.1 SearchService

```python
# services/search_service.py
class SearchService:
    """检索服务 — 协调语义检索、关键词检索和混合检索"""
    RRF_K = 60

    def __init__(self, vector_store_service, embedding_service, reranker=None):
        self.vector_store_service = vector_store_service
        self.embedding_service = embedding_service
        self.reranker = reranker

    async def search(self, query, top_k=10, filters=None) -> List[dict]:
        """语义检索：query→embedding→ChromaDB.query()→rerank"""
        query_embedding = await self.embedding_service.encode(query)
        raw_results = await self.vector_store_service.search(embedding=query_embedding.tolist(), top_k=top_k, filters=filters)
        results = self._format_results(raw_results)
        if self.reranker: results = await self.reranker.rerank(query, results)
        return results

    async def keyword_search(self, query, top_k=10, filters=None) -> List[dict]:
        """关键词检索：ChromaDB $contains 查询"""
        raw_results = await self.vector_store_service.search_by_keywords(query_text=query, top_k=top_k, filters=filters)
        return self._format_results(raw_results)

    async def hybrid_search(self, query, top_k=10, filters=None) -> List[dict]:
        """混合检索：语义+关键词并行→RRF融合→rerank"""
        candidate_k = top_k * 2
        semantic_results, keyword_results = await asyncio.gather(
            self.search(query, top_k=candidate_k, filters=filters),
            self.keyword_search(query, top_k=candidate_k, filters=filters),
        )
        fused = self._reciprocal_rank_fusion(semantic_results, keyword_results, k=self.RRF_K)
        if self.reranker: fused = await self.reranker.rerank(query, fused)
        return fused[:top_k]

    async def suggest(self, query, top_k=5) -> List[str]:
        """搜索建议：ChromaDB query_texts→标题列表"""
        return await self.vector_store_service.suggest_titles(query, top_k=top_k)

    def _format_results(self, raw_results) -> List[dict]:
        """统一格式化：paperId/paper_id→paper_id"""
        ...

    def _reciprocal_rank_fusion(self, list1, list2, k=60) -> list:
        """
        Reciprocal Rank Fusion

        RRF_score(d) = Σ 1/(k + rank_i(d))
        """
        scores = {}
        for rank, item in enumerate(list1):
            pid = item.get("paper_id") or item.get("paperId")
            scores[pid] = scores.get(pid, 0) + 1 / (k + rank + 1)
            if pid not in scores:
                scores[pid] = {"item": item}

        for rank, item in enumerate(list2):
            pid = item.get("paper_id") or item.get("paperId")
            scores[pid] = scores.get(pid, 0) + 1 / (k + rank + 1)

        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [v["item"] for _, v in sorted_items]
```

#### 6.2.2 Reranker（复合评分重排序）

```python
# services/reranker.py
class Reranker:
    """复合评分重排序器"""
    WEIGHT_RRF = 0.5          # RRF/语义分数权重
    WEIGHT_FIELD = 0.3        # 字段相关性权重
    WEIGHT_POPULARITY = 0.2   # 流行度权重
    YEAR_DECAY_RATE = 0.05    # 年份衰减率
    RECENT_YEAR_THRESHOLD = 3 # 近年阈值
    TITLE_MATCH_BOOST = 0.1   # 标题匹配加分
    KEYWORD_DENSITY_WEIGHT = 0.05  # 关键词密度权重
    CITATION_BOOST_WEIGHT = 0.1    # 引用数加分
    PERSONALIZATION_BOOST = 0.05   # 个性化加权

    async def rerank(self, query, results, user_profile=None) -> List[dict]:
        """复合评分公式：
        composite = score_rrf * 0.5
                  + (title_match + keyword_density + citation_boost) * year_decay * 0.3
                  + popularity * 0.2
                  + personalization_boost
        """
        for result in results:
            # 标题匹配加分
            title_match_boost = sum(TITLE_MATCH_BOOST for kw in query_keywords if kw in title)
            # 关键词密度
            keyword_density_boost = (keyword_count / abstract_len) * KEYWORD_DENSITY_WEIGHT
            # 引用数加分
            citation_boost = min(citation_count / 100, 1.0) * CITATION_BOOST_WEIGHT
            # 年份衰减
            score_year = 1.0 if years_diff <= 3 else exp(-0.05 * years_diff)
            # 字段相关性
            field_score = (title_match + keyword_density + citation) * score_year
            # 流行度
            popularity_score = min(citation_count / 100, 1.0)
            # 复合评分
            composite = score_rrf * 0.5 + field_score * 0.3 + popularity * 0.2
            # 个性化加权（研究方向匹配venue/keywords）
            if user_profile and research_field in venue: composite += 0.05
```

### 6.3 检索流程

```
1. 语义检索流程：

查询文本 "Multi-Agent协同决策"
    │
    ▼
EmbeddingService.encode()
    │ text-embedding-v4 → 1024维向量
    │ 耗时约50ms
    ▼
VectorStoreService.search()
    │ ChromaDB相似度检索（cosine）
    │ TopK=20 → 返回20个候选
    │ 耗时约100ms
    ▼
元数据过滤（可选）
    │ year >= 2020, venue = "ACL"
    ▼
Reranker.rerank()
    │ 复合评分重排序（RRF+字段+流行度+年份+个性化）
    │ 筛选Top10
    ▼
返回结果
    [{paper_id, title, abstract, score, year, venue}, ...]

2. 混合检索流程：

查询文本 "Multi-Agent协同决策"
    │
    ├──→ 语义检索（search）
    │    EmbeddingService.encode() → VectorStoreService.search()
    │    → candidate_k个结果
    │
    └──→ 关键词检索（keyword_search）
         VectorStoreService.search_by_keywords()
         → candidate_k个结果
    │
    ▼
RRF融合（_reciprocal_rank_fusion）
    │ RRF_score(d) = Σ 1/(k + rank_i(d))
    │ k=60
    ▼
Reranker.rerank()
    │ 复合评分重排序
    ▼
返回TopK结果

3. 搜索建议流程：

查询文本 "Multi-Agent"
    │
    ▼
VectorStoreService.suggest_titles()
    │ ChromaDB query_texts → 标题匹配
    ▼
返回标题列表（去重，Top5）
    ["Multi-Agent协同决策系统研究", "Multi-Agent强化学习综述", ...]
```

### 6.4 功能清单

| 编号 | 功能 | 优先级 | 状态 | 说明 |
|------|------|--------|------|------|
| F3.2.1 | 文档向量化 | P0 | ✅ | DashScope text-embedding-v4→1024维向量 |
| F3.2.2 | 向量存储 | P0 | ✅ | ChromaDB papers collection |
| F3.2.3 | 语义检索 | P0 | ✅ | cosine相似度，TopK |
| F3.2.4 | 关键词检索 | P0 | ✅ | ChromaDB $contains查询 |
| F3.2.5 | 混合检索 | P1 | ✅ | 语义+关键词+RRF融合 |
| F3.2.6 | 复合重排序 | P1 | ✅ | RRF+字段+流行度+年份+个性化 |
| F3.2.7 | 搜索建议 | P2 | ✅ | 标题自动补全 |
| F3.2.8 | 检索优化 | P2 | 待优化 | 调整chunk_size、top_k、similarity_threshold |

---

## 7 LLM服务模块（F3.3）

### 7.1 模块概述

封装统一的大语言模型推理接口，支持三种模型来源的灵活配置与按优先级自动降级切换。是所有Agent的核心依赖。

### 7.2 三路并行架构

```
┌────────────────────────────────────────────────────────────┐
│                    LLMService（统一接口）                     │
│                                                            │
│  generate(prompt, stream=False) → str                      │
│  generate_stream(prompt) → AsyncIterator[str]               │
│                                                            │
│  配置项（环境变量）：                                       │
│  LLM_MODE=auto|builtin|api|local                           │
│  LLM_BUILTIN_URL=（待发榜单位提供，未配置时自动跳过）   │
│  LLM_API_KEY=xxx              # 用户自配API密钥             │
│  LLM_API_BASE=https://api.xxx.com/v1                       │
│  LLM_MODEL_NAME=qwen2-7b-instruct                          │
├──────────┬───────────────┬───────────────┬─────────────────┤
│          │               │               │                 │
│ ┌────────▼──────┐ ┌─────▼─────────┐ ┌───▼──────────────┐ │
│ │ 方案A:         │ │ 方案B:         │ │ 方案C:           │ │
│ │ BuiltinLLM   │ │ APILLM         │ │ LocalLLM         │ │
│ │ Provider     │ │ Provider       │ │ Provider         │ │
│ │ (最高优先级) │ │ (中等优先级)   │ │ (最低优先级)     │ │
│ │               │ │                 │ │                  │ │
│ │ 软件方提供   │ │ 用户自配第三方 │ │ 用户本机部署     │ │
│ │ 云端模型服务 │ │ API             │ │ 开源模型         │ │
│ │ 开箱即用     │ │ 讯飞星火       │ │ Qwen2-7B        │ │
│ │ 无需配置     │ │ DeepSeek       │ │ Qwen2-1.5B      │ │
│ │ 流式生成     │ │ 通义千问等     │ │ 其他开源模型     │ │
│ │ 需: 仅网络  │ │ 流式生成       │ │ 流式生成         │ │
│ │              │ │ 需: API Key    │ │ 需: GPU/CPU+模型 │ │
│ └──────────────┘ └────────────────┘ └──────────────────┘ │
│                                                            │
│  降级策略：方案A(软件方) → 方案B(API) → 方案C(本地) → 错误│
│  重试策略：失败后重试1次，间隔3秒                          │
│  超时策略：单次推理30秒超时                                │
│  默认选择：auto模式按优先级降级，方案A URL未配置时直接使用方案B            │
└────────────────────────────────────────────────────────────┘
```

### 7.3 LLMService实现

```python
# services/llm_service.py
from enum import Enum
from typing import AsyncIterator, Optional

class LLMMode(str, Enum):
    AUTO = "auto"       # 自动选择（按优先级降级）
    BUILTIN = "builtin" # 强制使用软件方模型
    API = "api"         # 强制使用外接API
    LOCAL = "local"     # 强制使用本地模型

class LLMService:
    """统一LLM推理服务"""

    PROVIDER_PRIORITY = ["builtin", "api", "local"]

    def __init__(self, settings):
        self.settings = settings
        self.mode = settings.LLM_MODE
        self.providers = {}      # {mode: LLMProvider}
        self.active_provider = None
        self.status = "initializing"
        self._degradation_state = {
            "current_provider": None,
            "fallback_count": 0,
            "last_fallback_at": None,
            "consecutive_failures": {},  # 按provider记录连续失败次数
        }
        self._recovery_task: asyncio.Task | None = None

    async def initialize(self):
        """初始化LLM服务，根据配置加载Provider"""
        if self.mode in (LLMMode.AUTO, LLMMode.BUILTIN):
            if self.settings.LLM_BUILTIN_URL:
                try:
                    self.providers["builtin"] = BuiltinLLMProvider(self.settings)
                    await self.providers["builtin"].test_connection()
                    self.active_provider = self.providers["builtin"]
                    self.status = "loaded"
                    logger.info("LLM: Using builtin provider (软件方模型)")
                    return
                except Exception as e:
                    logger.warning(f"Builtin provider failed: {e}")
            else:
                logger.info("LLM: Builtin provider skipped (LLM_BUILTIN_URL not configured)")

        if self.mode in (LLMMode.AUTO, LLMMode.API):
            if self.settings.LLM_API_KEY:
                try:
                    self.providers["api"] = APILLMProvider(self.settings)
                    await self.providers["api"].test_connection()
                    self.active_provider = self.providers["api"]
                    self.status = "loaded"
                    logger.info("LLM: Using API provider")
                    return
                except Exception as e:
                    logger.warning(f"API provider failed: {e}")

        if self.mode in (LLMMode.AUTO, LLMMode.LOCAL):
            try:
                self.providers["local"] = LocalLLMProvider(self.settings)
                await self.providers["local"].load_model()
                self.active_provider = self.providers["local"]
                self.status = "loaded"
                logger.info("LLM: Using local provider")
                return
            except Exception as e:
                logger.warning(f"Local provider failed: {e}")

        self.status = "error"
        raise RuntimeError("No LLM provider available")

    async def generate(self, prompt: str, max_tokens: int = 2048,
                       temperature: float = 0.7) -> str:
        """
        同步生成（阻塞等待完整结果）

        Args:
            prompt: 输入提示词
            max_tokens: 最大生成Token数
            temperature: 温度参数

        Returns:
            生成的文本
        """
        try:
            return await asyncio.wait_for(
                self.active_provider.generate(prompt, max_tokens, temperature),
                timeout=self.settings.LLM_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.error(f"LLM generation timed out after {self.settings.LLM_TIMEOUT}s")
            await self._fallback()
            return await self.active_provider.generate(
                prompt, max_tokens, temperature
            )
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            await self._fallback()
            return await self.active_provider.generate(
                prompt, max_tokens, temperature
            )

    async def generate_stream(self, prompt: str, max_tokens: int = 2048,
                               temperature: float = 0.7) -> AsyncIterator[str]:
        """
        流式生成（逐Token输出）

        Yields:
            每次产出一个Token
        """
        try:
            async for token in self.active_provider.generate_stream(
                prompt, max_tokens, temperature
            ):
                yield token
        except Exception as e:
            logger.error(f"LLM stream generation failed: {e}")
            await self._fallback()
            async for token in self.active_provider.generate_stream(
                prompt, max_tokens, temperature
            ):
                yield token

    async def _fallback(self):
        """降级到下一个可用的Provider"""
        priority = ["builtin", "api", "local"]
        current = self.active_provider.mode if self.active_provider else None

        for provider_mode in priority:
            if provider_mode == current:
                continue
            if provider_mode in self.providers:
                try:
                    await self.providers[provider_mode].test_connection()
                    self.active_provider = self.providers[provider_mode]
                    logger.warning(f"LLM fallback to {provider_mode}")
                    return
                except Exception:
                    continue

        raise RuntimeError("All LLM providers failed")

    async def unload_model(self):
        """释放模型显存"""
        if "local" in self.providers:
            await self.providers["local"].unload_model()

    def _start_recovery_task(self):
        """启动自动恢复任务（每300秒轮询高优先级provider）"""
        async def _recovery_loop():
            while True:
                await asyncio.sleep(300)
                # 检查比当前provider优先级更高的provider是否恢复
                ...
        self._recovery_task = asyncio.create_task(_recovery_loop())
```

### 7.4 Provider实现

#### 7.4.1 BuiltinLLMProvider（软件方模型，最高优先级）

```python
class BuiltinLLMProvider:
    """
    软件方提供的云端模型服务

    特点：
    - 开箱即用，无需用户配置
    - 使用OpenAI兼容接口
    - 内置API端点和凭证
    """

    mode = "builtin"

    def __init__(self, settings):
        self.client = AsyncOpenAI(
            api_key=settings.LLM_BUILTIN_API_KEY or "builtin",
            base_url=settings.LLM_BUILTIN_URL
        )
        self.model_name = settings.LLM_BUILTIN_MODEL or "literature-assistant-pro"

    async def generate(self, prompt: str, max_tokens: int,
                       temperature: float) -> str:
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content

    async def generate_stream(self, prompt: str, max_tokens: int,
                               temperature: float) -> AsyncIterator[str]:
        stream = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def test_connection(self):
        """测试连接是否可用"""
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        return True
```

#### 7.4.2 APILLMProvider（外接API，中等优先级）

```python
class APILLMProvider:
    """
    用户自行配置的第三方API

    支持：
    - OpenAI兼容接口
    - 讯飞星火（OpenAI兼容模式）
    - DeepSeek（含 V4-Flash，当前默认）
    - 通义千问
    - 任何OpenAI兼容端点

    当前生效配置（2026-06 起）：
        base_url = https://api.deepseek.com/v1
        model    = deepseek-v4-flash
    """

    mode = "api"

    def __init__(self, settings):
        self.client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_API_BASE
        )
        self.model_name = settings.LLM_MODEL_NAME

    # generate / generate_stream 同BuiltinLLMProvider
```

#### 7.4.3 LocalLLMProvider（用户本地模型，最低优先级）

```python
class LocalLLMProvider:
    """
    用户本机部署的开源模型

    支持：
    - Qwen2-7B（需GPU，显存≥16GB）
    - Qwen2-1.5B（CPU可运行）
    - 其他Transformers兼容模型
    """

    mode = "local"

    def __init__(self, settings):
        self.model_path = settings.LLM_LOCAL_MODEL_PATH
        self.model = None
        self.tokenizer = None

    async def load_model(self):
        """加载本地模型"""
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            torch_dtype="auto",
            device_map="auto"
        )

    async def generate(self, prompt: str, max_tokens: int,
                       temperature: float) -> str:
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=True
        )
        return self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:],
                                      skip_special_tokens=True)

    async def generate_stream(self, prompt: str, max_tokens: int,
                               temperature: float) -> AsyncIterator[str]:
        """流式生成（使用TextIteratorStreamer）"""
        from transformers import TextIteratorStreamer
        import threading

        streamer = TextIteratorStreamer(self.tokenizer, skip_special_tokens=True)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

        generation_kwargs = {
            **inputs,
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "streamer": streamer,
            "do_sample": True
        }

        thread = threading.Thread(target=self.model.generate, kwargs=generation_kwargs)
        thread.start()

        for text in streamer:
            yield text

        thread.join()

    async def unload_model(self):
        """释放GPU显存"""
        del self.model
        del self.tokenizer
        self.model = None
        self.tokenizer = None
        import gc, torch
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
```

### 7.5 自动降级时序

```
启动时自动检测：

LLM_MODE=auto
    │
    ├── 1. 尝试BuiltinLLMProvider
    │   ├── 软件方模型可用 → 使用方案A ✅
    │   └── 软件方模型不可用 → 继续检测
    │
    ├── 2. 尝试APILLMProvider
    │   ├── API Key已配置且可用 → 使用方案B ✅
    │   └── API Key未配置或不可用 → 继续检测
    │
    ├── 3. 尝试LocalLLMProvider
    │   ├── 本地模型文件存在 → 使用方案C ✅
    │   └── 本地模型文件不存在 → 报错
    │
    └── 至少一路可用即可启动系统

运行时降级：

方案A调用失败（超时/异常）
    │
    ├── 降级到方案B（如果API Key可用）
    │   ├── 方案B可用 → 继续推理 ✅
    │   └── 方案B不可用 → 继续降级
    │
    ├── 降级到方案C（如果本地模型可用）
    │   ├── 方案C可用 → 继续推理 ✅
    │   └── 方案C不可用 → 返回错误
    │
    └── 所有方案均失败 → 返回AIServiceException

运行时自动恢复（_recovery_task）：

每300秒轮询：
├── 检查比当前active_provider优先级更高的provider
├── 如果高优先级provider恢复 → 自动切回
├── 例：api→builtin 恢复后自动切回builtin
└── 日志记录：LLM recovered: api → builtin

降级状态追踪（_degradation_state）：
├── current_provider: 当前活跃provider
├── fallback_count: 累计降级次数
├── last_fallback_at: 最近降级时间
└── consecutive_failures: 各provider连续失败次数
```

### 7.6 功能清单

| 编号 | 功能 | 优先级 | 说明 |
|------|------|--------|------|
| F3.3.1 | 灵活模型配置 | P0 | 支持软件方/外接API/本地模型三路，按优先级自动选择 |
| F3.3.2 | 模型推理 | P0 | 统一推理接口，屏蔽底层差异，同步调用 |
| F3.3.3 | 流式输出 | P1 | 逐Token流式生成，首字节<2秒 |
| F3.3.4 | Prompt管理 | P0 | 独立Prompt模板文件，支持变量替换 |
| F3.3.5 | 自动降级 | P0 | 软件方→API→本地，降级对调用方透明 |
| F3.3.6 | 外接API管理 | P0 | 统一管理密钥、端点，OpenAI兼容接口 |
| F3.3.7 | 模型量化 | P2 | INT4/INT8量化，速度提升30%+，精度下降<5% |

---

## 8 个性化引擎模块（F3.4）

### 8.1 模块概述

根据用户画像动态构建个性化Prompt，实现内容难度适配、风格适配和推荐增强。是"领域知识个性化生成"核心要求的实现模块。

### 8.2 类设计

```python
# services/personalization_service.py
class PersonalizationService:
    """个性化引擎 — 画像驱动的Prompt构建"""

    # 核心映射表
    DIFFICULTY_MAP = {"beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4}
    STYLE_MAP = {
        "simple": {"tone": "日常用语+比喻", "paragraph": "短段落", "structure": "先举例后总结"},
        "balanced": {"tone": "标准学术", "paragraph": "中等段落", "structure": "先总后分"},
        "technical": {"tone": "正式学术+引用", "paragraph": "长段落", "structure": "严格学术结构"},
    }
    EDUCATION_ADAPTATION = {
        "undergraduate": "适当补充背景知识，使用类比说明",
        "master": "侧重方法论对比和实验设计分析",
        "phd": "关注创新点和前沿贡献",
        "faculty": "关注教学适用性和知识体系构建",
    }
    FIELD_EMPHASIS = {"NLP": "...", "CV": "...", "RL": "...", ...}
    TERM_DENSITY_TARGET = {"beginner": 0.05, "intermediate": 0.20, "advanced": 0.40, "expert": 0.50}

    def get_personalization_block(self, user_profile) -> str:
        """构建个性化Prompt片段（学历适配+术语密度+写作风格+领域侧重）"""

    def get_extra_instruction(self, user_profile, agent_name="") -> str:
        """Agent级别差异化指令
        - analyzer: _ANALYZER_INSTRUCTIONS + _ANALYZER_EDUCATION_INSTRUCTIONS
        - generator: _GENERATOR_INSTRUCTIONS + _GENERATOR_EDUCATION_INSTRUCTIONS
        """

    def build_generation_prompt(self, analysis_results, comparison_result, user_profile) -> str:
        """构建个性化综述生成Prompt（优先使用prompt_manager，fallback到文件加载）"""
```

### 8.3 个性化效果对比

```
同一主题"Multi-Agent协同决策"，不同用户画像的输出差异：

用户A：本科生·初级·通俗风格
→ "Multi-Agent就像一个AI项目组，每个成员负责不同任务。
   比如写论文时，有人负责查资料，有人负责写代码，有人负责检查..."
   术语密度<5%，有大量类比，无公式

用户B：硕士生·中级·均衡风格
→ "Multi-Agent系统通过多个智能体协同工作，实现复杂任务的分解与执行。
   常见框架包括LangGraph和AutoGen，前者基于图结构编排..."
   术语密度~20%，有代码示例，标准学术表达

用户C：博士生·高级·专业风格
→ "现有Multi-Agent框架在实时性（Zhang et al., 2024）和可扩展性
   （Li et al., 2023）方面存在不足。基于LangGraph的图结构编排
   虽然提供了灵活的工作流定义，但在处理动态任务分配时..."
   术语密度>40%，有论文引用，包含研究空白分析
```

### 8.4 功能清单

| 编号 | 功能 | 优先级 | 状态 | 说明 |
|------|------|--------|------|------|
| F3.4.1 | 用户画像解析 | P0 | ✅ | camelCase→snake_case归一化 |
| F3.4.2 | Prompt个性化 | P0 | ✅ | 学历适配+术语密度+写作风格+领域侧重 |
| F3.4.3 | 内容难度适配 | P0 | ✅ | 4级knowledge_level→术语密度目标 |
| F3.4.4 | 风格适配 | P1 | ✅ | 3级preferred_style→语气/段落/结构 |
| F3.4.5 | Agent差异化指令 | P1 | ✅ | analyzer/generator独立指令集 |
| F3.4.6 | 推荐策略 | P2 | 待实现 | 根据研究方向+历史偏好推荐论文 |

---

## 9 Embedding模型模块（F5.2）

### 9.1 模块概述

负责将文本转换为高维向量表示。**当前配置使用阿里云百炼 DashScope API（text-embedding-v4）作为主要方式**，本地模型（BAAI/bge-m3）因用户策略已禁用。维度1024与API对齐。

### 9.2 EmbeddingService实现

```python
# services/embedding_service.py
import numpy as np
from typing import Union

class EmbeddingService:
    """文本向量化服务"""
    EXPECTED_DIMENSION = 1024

    def __init__(self, settings):
        self.settings = settings
        self.model = None           # 本地模型（当前禁用）
        self._dimension: int | None = None
        self.status = "initializing"
        self._api_client = None     # DashScope API客户端

    async def load_model(self) -> None:
        """初始化Embedding服务
        优先级：DashScope API > 本地模型（已禁用） > disabled
        """
        if self.settings.DASHSCOPE_API_KEY:
            self._init_dashscope_client()
            self._dimension = self.settings.EMBEDDING_EXPECTED_DIMENSION
            self.status = "loaded_api"
            return
        # 本地模型已禁用
        self.status = "disabled"

    def _init_dashscope_client(self) -> None:
        """初始化DashScope Embedding API客户端"""
        from openai import AsyncOpenAI
        from httpx import Timeout
        self._api_client = AsyncOpenAI(
            api_key=self.settings.DASHSCOPE_API_KEY,
            base_url=self.settings.DASHSCOPE_EMBEDDING_BASE_URL,
            timeout=Timeout(30.0, connect=10.0),
            max_retries=2,
        )

    async def encode(self, text) -> np.ndarray:
        """文本向量化（单条/批量）"""
        if self._api_client: return await self._encode_via_api(text)
        if self.model: return await self._encode_local(text)
        raise ModelNotLoadedException("Embedding model not loaded")

    async def _encode_via_api(self, text) -> np.ndarray:
        """通过DashScope API获取向量"""
        response = await self._api_client.embeddings.create(
            model=self.settings.DASHSCOPE_EMBEDDING_MODEL,
            input=text,
        )
        embeddings = [item.embedding for item in response.data]
        return np.array(embeddings, dtype=np.float32)

    async def encode_batch(self, texts: list, batch_size: int = 32) -> np.ndarray:
        """
        批量向量化

        目标性能：100条/10秒

        Args:
            texts: 文本列表
            batch_size: 每批处理数量

        Returns:
            向量矩阵 (N, 1024)
        """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = await self.encode(batch)
            all_embeddings.append(embeddings)

        return np.vstack(all_embeddings)
```

### 9.3 功能清单

| 编号 | 功能 | 优先级 | 状态 | 说明 |
|------|------|--------|------|------|
| F5.2.1 | DashScope API配置 | P0 | ✅ | text-embedding-v4，1024维，阿里云百炼 |
| F5.2.2 | 文本向量化 | P0 | ✅ | 单条/批量→1024维向量 |
| F5.2.3 | 批量向量化 | P0 | ✅ | encode_batch，batch_size=32 |
| F5.2.4 | 本地模型 | P2 | 已禁用 | BAAI/bge-m3，因用户策略禁用 |

---

## 10 向量数据库模块（F4.3）

### 10.1 VectorStoreService实现

```python
# services/vector_store_service.py
import chromadb
from typing import Optional

class VectorStoreService:
    """Chroma向量数据库服务"""

    EXPECTED_DIMENSION = 1024

    def __init__(self, settings):
        self.settings = settings
        self.client = None
        self.collection = None
        self.status = "disconnected"

    async def initialize(self):
        """初始化Chroma连接"""
        self.client = chromadb.PersistentClient(
            path=self.settings.CHROMA_PATH or "./data/vector_db"
        )

        # 获取或创建papers collection
        self.collection = self.client.get_or_create_collection(
            name="papers",
            metadata={
                "hnsw:space": "cosine",           # 余弦相似度
                "hnsw:M": 16,                      # HNSW图连接数
                "hnsw:construction_ef": 200        # 构建时搜索宽度
            }
        )
        self.status = "connected"
        logger.info(f"ChromaDB initialized, papers count={self.collection.count()}")

    async def add_papers(self, paper_ids: list, embeddings: list,
                          metadatas: list, documents: list):
        """
        添加论文向量

        Args:
            paper_ids: 论文ID列表（如["arxiv_2024_001", ...]）
            embeddings: 向量列表（每条1024维）
            metadatas: 元数据列表 [{paper_id, title, year, venue, ...}]
            documents: 文档文本列表（标题+摘要）
        """
        if embeddings and len(embeddings[0]) != self.EXPECTED_DIMENSION:
            raise VectorStoreException(
                code=400,
                message=f"Embedding dimension mismatch: got {len(embeddings[0])}, expected {self.EXPECTED_DIMENSION}"
            )
        self.collection.add(
            ids=paper_ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )
        logger.info(f"Added {len(paper_ids)} papers to ChromaDB")

    async def search(self, embedding: list, top_k: int = 10,
                     filters: dict = None) -> list:
        """
        向量相似度检索

        Args:
            embedding: 查询向量（1024维）
            top_k: 返回数量
            filters: 元数据过滤条件

        Returns:
            检索结果列表
        """
        where_filter = None
        if filters:
            conditions = []
            if filters.get("yearFrom"):
                conditions.append({"year": {"$gte": filters["yearFrom"]}})
            if filters.get("yearTo"):
                conditions.append({"year": {"$lte": filters["yearTo"]}})
            if filters.get("venue"):
                conditions.append({"venue": {"$eq": filters["venue"]}})
            if conditions:
                where_filter = {"$and": conditions} if len(conditions) > 1 else conditions[0]

        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=where_filter,
            include=["metadatas", "distances", "documents"]
        )

        # 格式化结果
        formatted = []
        for i in range(len(results["ids"][0])):
            formatted.append({
                "paperId": results["metadatas"][0][i].get("paper_id"),
                "title": results["metadatas"][0][i].get("title"),
                "abstract": results["documents"][0][i],
                "score": 1 - results["distances"][0][i],  # cosine距离→相似度
                "year": results["metadatas"][0][i].get("year"),
                "venue": results["metadatas"][0][i].get("venue")
            })

        return formatted

    async def delete_papers(self, paper_ids: list):
        """删除论文向量"""
        self.collection.delete(ids=paper_ids)

    async def count(self) -> int:
        """获取向量数量"""
        return self.collection.count()

    async def close(self):
        """关闭连接"""
        self.client = None
        self.status = "disconnected"

    async def add_papers_batch(self, paper_ids, embeddings, metadatas, documents, batch_size=50) -> None:
        """批量导入论文（分批写入，每批间隔0.5秒）"""

    async def get_paper_by_id(self, paper_id) -> Optional[dict]:
        """按ID获取论文详情"""

    async def update_paper_metadata(self, paper_id, metadata) -> None:
        """更新论文元数据"""

    async def search_by_keywords(self, query_text, top_k=10, filters=None) -> List[dict]:
        """关键词检索（ChromaDB $contains查询，逐关键词检索去重）"""

    async def suggest_titles(self, query, top_k=5) -> List[str]:
        """搜索建议（query_texts→标题列表去重）"""
```

### 10.2 Chroma Schema

```python
# Collection: papers
# 向量维度：1024（text-embedding-v4输出维度）

collection_schema = {
    "name": "papers",
    "metadata": {
        "hnsw:space": "cosine",
        "hnsw:M": 16,
        "hnsw:construction_ef": 200
    }
}

# 文档元数据Schema
metadata_schema = {
    "paper_id": str,          # 关联MySQL中的paper_id
    "title": str,             # 论文标题
    "year": int,              # 发表年份
    "venue": str,             # 发表会议/期刊
    "citation_count": int,    # 引用数
    "chunk_index": int,       # 分块索引
    "chunk_type": str         # title_abstract / section
}
```

### 10.3 功能清单

| 编号 | 功能 | 优先级 | 状态 | 说明 |
|------|------|--------|------|------|
| F4.3.1 | 论文向量存储 | P0 | ✅ | 向量+元数据存入Chroma |
| F4.3.2 | 语义相似度检索 | P0 | ✅ | cosine相似度，TopK |
| F4.3.3 | 向量索引管理 | P1 | ✅ | 添加/删除/更新/按ID查询 |
| F4.3.4 | 批量导入 | P0 | ✅ | 分批写入，batch_size=50 |
| F4.3.5 | 关键词检索 | P0 | ✅ | $contains查询，多关键词去重 |
| F4.3.6 | 搜索建议 | P2 | ✅ | 标题自动补全 |

---

## 11 论文数据采集模块（F4.4）

### 11.1 数据采集脚本

```python
# scripts/import_papers.py
"""
论文数据导入脚本

功能：
1. 从arXiv API下载AI/Agent领域论文元数据
2. 清洗和格式化数据
3. 将论文元数据导入MySQL（通过Java后端API）
4. 将论文向量化并导入Chroma

使用方式：
    python scripts/import_papers.py --count 200 --category "cs.AI"
"""

import arxiv
import json
import asyncio

async def fetch_papers(category: str, count: int) -> list:
    """从arXiv API获取论文"""
    client = arxiv.Client()
    search = arxiv.Search(
        query=f"cat:{category}",
        max_results=count,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    papers = []
    for result in client.results(search):
        papers.append({
            "paperId": f"arxiv_{result.entry_id.split('/')[-1]}",
            "title": result.title,
            "authors": [a.name for a in result.authors],
            "abstract": result.summary.replace("\n", " "),
            "year": result.published.year,
            "venue": result.primary_category,
            "keywords": result.categories,
            "pdfUrl": result.pdf_url
        })

    return papers

def clean_papers(papers: list) -> list:
    """数据清洗：去重、格式统一"""
    seen = set()
    cleaned = []
    for p in papers:
        if p["title"] in seen:
            continue
        seen.add(p["title"])
        p["title"] = p["title"].strip()
        p["abstract"] = p["abstract"].strip()
        cleaned.append(p)
    return cleaned

async def import_to_vector_db(papers: list):
    """将论文向量化并导入Chroma"""
    texts = [f"{p['title']} {p['abstract']}" for p in papers]
    embeddings = await embedding_service.encode_batch(texts)

    metadatas = [{
        "paper_id": p["paperId"],
        "title": p["title"],
        "year": p["year"],
        "venue": p["venue"],
        "citation_count": 0
    } for p in papers]

    await vector_store_service.add_papers(
        paper_ids=[p["paperId"] for p in papers],
        embeddings=embeddings.tolist(),
        metadatas=metadatas,
        documents=texts
    )
```

### 11.2 功能清单

| 编号 | 功能 | 优先级 | 状态 | 说明 |
|------|------|--------|------|------|
| F4.4.1 | arXiv数据采集 | P0 | ✅ | 从arXiv API下载AI/Agent领域论文 |
| F4.4.2 | 数据清洗 | P0 | ✅ | 去重+格式统一 |
| F4.4.3 | 文档分块 | P0 | ✅ | chunk_text()，800字+100字overlap |
| F4.4.4 | 质量检查 | P0 | ✅ | validate_papers.py |

---

## 12 Prompt工程规范

### 12.1 Prompt模板目录

```
prompts/
├── coordinator.txt    # 协调者Agent Prompt
├── retriever.txt      # 检索Agent Prompt
├── analyzer.txt       # 分析Agent Prompt
├── comparer.txt       # 对比Agent Prompt
├── generator.txt      # 生成Agent Prompt
└── reviewer.txt       # 审核Agent Prompt
```

> 注：PromptManager 使用 `string.Template.safe_substitute()` 渲染，变量格式为 `$variable` 或 `${variable}`。

### 12.2 Prompt模板示例

#### analyzer.txt

```
你是一位资深学术论文审稿人。请对以下论文进行深度分析，提取以下5个维度的核心信息：

【论文标题】：$paper_title

【论文摘要】：$paper_abstract

$extra_instruction

请严格按照以下JSON格式输出：

```json
{
    "researchQuestion": "论文要解决的核心研究问题",
    "coreMethod": "论文提出的核心方法/算法",
    "keyExperiments": "论文的主要实验设置和结果",
    "coreFindings": "论文的核心结论",
    "limitations": "论文的局限性和不足"
}
```

要求：
1. 每个维度的描述应简洁准确，100-200字
2. 提取的信息必须基于论文原文，不可臆造
3. 如论文未涉及某维度，填写"论文未明确提及"
```

#### generator.txt

```
你是一位专业的学术文献综述撰写专家。请根据以下论文分析数据，撰写一篇结构完整的文献综述。

$personalization

【研究主题】：基于提供的论文分析数据

【论文分析数据】：
$analysis_data

【对比分析数据】（如有）：
$comparison_data

请撰写综述，包含以下结构：

## 1 引言
简要介绍研究背景和综述范围

## 2 研究现状
概述当前领域的主要研究方向和进展

## 3 方法对比
对比不同论文提出的方法，分析各自优缺点

## 4 研究趋势
分析领域的发展趋势和未来方向

## 5 参考文献
列出引用的论文

要求：
1. 每个观点必须引用具体论文（格式：[作者, 年份]）
2. 内容必须基于提供的论文数据，不可编造
3. 综述逻辑清晰，层次分明
4. 字数控制在2000-3000字
```

### 12.3 Prompt变量替换规范

| 变量 | 说明 | 使用位置 |
|------|------|---------|
| `$paper_title` | 论文标题 | analyzer |
| `$paper_abstract` | 论文摘要 | analyzer |
| `$extra_instruction` | 个性化额外指令 | analyzer |
| `$personalization` | 个性化Prompt片段 | generator |
| `$analysis_data` | 分析结果JSON | generator |
| `$comparison_data` | 对比结果JSON | generator, comparer |
| `$report_content` | 生成的综述内容 | reviewer |
| `$original_papers` | 原始论文数据 | reviewer |
| `$user_profile_summary` | 用户画像摘要文本 | generator, comparer |

---

## 13 模块间依赖与交互

### 13.1 依赖关系图

```
┌─────────────────────────────────────────────────────────────┐
│                    API路由层                                  │
│  agent.py → search.py → model.py                            │
└────────────┬───────────────────┬────────────────────────────┘
             │                   │
             ▼                   ▼
┌────────────────────┐  ┌────────────────────┐
│  Agent协同引擎      │  │  SearchService      │
│  (AgentOrchestrator)│  │  (search_service)   │
│                    │  │                     │
│  coordinator ──┐   │  │  ┌── embedding_service
│  retriever  ───┤   │  │  ├── vector_store_service
│  analyzer   ───┤   │  │  └── Reranker
│  comparer   ───┤   │  └────────────────────┘
│  generator  ───┤   │
│  reviewer   ───┘   │
│        │           │
│        ▼           │
│  ┌─────────────────┤
│  │  llm_service    │
│  │  embedding_svc  │
│  │  vector_store   │
│  │  personalization│
│  │  search_service │
│  │  reranker       │
│  └─────────────────┘
└────────────────────┘
```

### 13.2 调用关系矩阵

| 调用方 | 被调用方 | 调用方式 | 说明 |
|--------|---------|---------|------|
| agent.py (API) | graph.py (工作流) | 函数调用 | 启动Agent协同分析 |
| search.py (API) | SearchService | 函数调用 | 执行论文检索 |
| graph.py | 各Agent | 函数调用 | 按工作流执行Agent |
| RetrieverAgent | VectorStoreService | 方法调用 | 向量检索 |
| RetrieverAgent | EmbeddingService | 方法调用 | 查询向量化 |
| AnalyzerAgent | LLMService | 方法调用 | 结构化信息提取 |
| ComparerAgent | LLMService | 方法调用 | 对比分析生成 |
| GeneratorAgent | LLMService | 方法调用 | 综述生成 |
| GeneratorAgent | PersonalizationService | 方法调用 | 构建个性化Prompt |
| ReviewerAgent | LLMService | 方法调用 | 内容审核 |
| SearchService | EmbeddingService | 方法调用 | 查询向量化 |
| SearchService | VectorStoreService | 方法调用 | 向量检索 |
| VectorStoreService | ChromaDB | SDK调用 | 向量存储/检索 |

---

## 14 数据模型规范

### 14.1 Pydantic请求模型

```python
# models/schemas.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from enum import Enum

class EducationLevel(str, Enum):
    UNDERGRADUATE = "undergraduate"
    MASTER = "master"
    PHD = "phd"
    FACULTY = "faculty"

class KnowledgeLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class PreferredStyle(str, Enum):
    SIMPLE = "simple"
    BALANCED = "balanced"
    TECHNICAL = "technical"

class AnalysisType(str, Enum):
    PAPER_ANALYSIS = "paper_analysis"
    COMPARE = "compare"
    REPORT = "report"

# ===== 请求模型 =====

class UserProfile(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    education_level: EducationLevel = Field(alias="educationLevel")
    research_field: str = Field(alias="researchField")
    knowledge_level: KnowledgeLevel = Field(alias="knowledgeLevel")
    preferred_style: PreferredStyle = Field(alias="preferredStyle")

class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    topic: str = Field(..., min_length=1, max_length=500)
    paper_ids: List[str] = Field(default_factory=list, alias="paperIds")
    user_id: str = Field(..., min_length=1, alias="userId")
    user_profile: UserProfile = Field(alias="userProfile")
    analysis_type: AnalysisType = Field(alias="analysisType")
    analysis_id: str = Field(..., min_length=1, alias="analysisId")

class SearchRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(default=10, ge=1, le=50, alias="topK")
    filters: Optional[dict] = None

class HybridSearchRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(default=10, ge=1, le=50, alias="topK")
    filters: Optional[Dict[str, Any]] = None
    user_profile: Optional[UserProfile] = Field(default=None, alias="userProfile")

# ===== 响应模型 =====

class AgentStateResponse(BaseModel):
    agent_name: str = Field(alias="agentName")
    status: str
    progress: Optional[float] = None
    intermediate_result: Optional[str] = Field(default=None, alias="intermediateResult")
    duration_ms: Optional[int] = Field(default=None, alias="durationMs")

class AnalyzeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    analysis_id: str = Field(alias="analysisId")
    status: str
    report: Optional[str] = None
    citations: Optional[list] = None
    agent_states: Optional[List[AgentStateResponse]] = Field(default=None, alias="agentStates")
    degraded: Optional[bool] = None
    degraded_reason: Optional[str] = Field(default=None, alias="degradedReason")

class SearchResultItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    paper_id: str = Field(alias="paperId")
    title: str
    abstract: Optional[str] = None
    score: float
    year: Optional[int] = None
    venue: Optional[str] = None

class SearchResponse(BaseModel):
    results: List[SearchResultItem]
    total: int

class SearchSuggestResponse(BaseModel):
    suggestions: List[str] = Field(default_factory=list)
    total: int = Field(default=0, ge=0)

class ModelStatusResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    llm: str
    embedding: str
    chroma: str
    prompts: str
    embedding_dimension: Optional[int] = Field(default=None, alias="embeddingDimension")
    active_llm_provider: Optional[str] = Field(default=None, alias="activeLlmProvider")
    # task26扩展字段
    provider_candidates: List[str] = Field(default_factory=list, alias="providerCandidates")
    chroma_paper_count: Optional[int] = Field(default=None, alias="chromaPaperCount")
    gpu_memory_used: Optional[str] = Field(default=None, alias="gpuMemoryUsed")
    llm_provider_count: int = Field(default=0, alias="llmProviderCount")
    search_service: Optional[str] = Field(default=None, alias="searchService")
    reranker: Optional[str] = Field(default=None)

# 注：API端点应设置 response_model_by_alias=True 以输出camelCase
```

### 14.2 枚举定义

```python
# models/enums.py
from enum import Enum

try:
    from enum import StrEnum
except ImportError:
    class StrEnum(str, Enum): pass

class EducationLevel(StrEnum):
    UNDERGRADUATE = "undergraduate"
    MASTER = "master"
    PHD = "phd"
    FACULTY = "faculty"

class KnowledgeLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class PreferredStyle(StrEnum):
    SIMPLE = "simple"
    BALANCED = "balanced"
    TECHNICAL = "technical"

class AnalysisType(StrEnum):
    PAPER_ANALYSIS = "paper_analysis"
    COMPARE = "compare"
    REPORT = "report"

class AgentName(StrEnum):
    COORDINATOR = "coordinator"
    RETRIEVER = "retriever"
    ANALYZER = "analyzer"
    COMPARER = "comparer"
    GENERATOR = "generator"
    REVIEWER = "reviewer"

class AgentStatus(StrEnum):
    WAITING = "waiting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class LLMMode(StrEnum):
    AUTO = "auto"
    BUILTIN = "builtin"
    API = "api"
    LOCAL = "local"
```

---

## 15 统一响应与异常处理

### 15.1 统一响应格式

```python
# utils/response.py
from fastapi.responses import JSONResponse
from datetime import datetime, timezone

def ok(data=None, message="success", code=200) -> Dict:
    return {"code": code, "message": message, "data": data, "timestamp": now_ts_ms()}

def fail(message, code=500, data=None) -> Dict:
    return {"code": code, "message": message, "data": data, "timestamp": now_ts_ms()}

def fail_response(message, code=500, data=None) -> JSONResponse:
    return JSONResponse(status_code=code, content=fail(message, code, data))

def now_ts_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)

# 使用示例：
# return ok(data={"results": [...]})
# return fail_response("论文检索失败", code=500)
```

### 15.2 异常体系

```python
# exception.py
class AIServiceException(Exception):
    """AI服务基础异常"""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message

class LLMException(AIServiceException):
    """LLM调用异常"""
    def __init__(self, message: str, code: int = 503):
        super().__init__(code=code, message=message)

class VectorStoreException(AIServiceException):
    """向量数据库异常"""
    def __init__(self, message: str, code: int = 503):
        super().__init__(code=code, message=message)

class AgentTimeoutException(AIServiceException):
    """Agent执行超时"""
    def __init__(self, message: str, code: int = 408):
        super().__init__(code=code, message=message)

class ModelNotLoadedException(AIServiceException):
    """模型未加载"""
    def __init__(self, message: str, code: int = 503):
        super().__init__(code=code, message=message)

class ValidationException(AIServiceException):
    """业务校验异常（语义层面，与Pydantic自动校验422区分）"""
    def __init__(self, message: str, code: int = 422):
        super().__init__(code=code, message=message)

class RateLimitException(AIServiceException):
    """限流异常"""
    def __init__(self, message: str = "请求过于频繁，请稍后重试", code: int = 429):
        super().__init__(code=code, message=message)
```

### 15.3 全局异常处理器

```python
# main.py
@app.exception_handler(AIServiceException)
async def ai_service_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": None,
            "timestamp": now_ts_ms(),
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Pydantic 422校验错误：返回中文友好message"""
    error_list = exc.errors() if hasattr(exc, "errors") else []
    message = _extract_chinese_field_message(error_list)
    return JSONResponse(status_code=422, content={
        "code": 422, "message": message, "data": None, "timestamp": now_ts_ms()
    })

def _extract_chinese_field_message(errors: list) -> str:
    """将Pydantic校验错误转为中文友好提示（直接用loc路径+错误类型判断）"""
    if not errors:
        return "参数校验失败"
    parts = []
    for err in errors:
        loc = err.get("loc", [])
        field = ".".join(str(x) for x in loc[1:]) if len(loc) > 1 else (str(loc[0]) if loc else "未知字段")
        err_type = err.get("type", "")
        if err_type == "missing":
            parts.append(f"{field} 字段必填")
        elif err_type == "string_too_short":
            parts.append(f"{field} 不能为空")
        elif err_type in ("enum", "literal_error"):
            parts.append(f"{field} 取值非法")
        elif err_type.startswith("value_error"):
            parts.append(f"{field} 校验失败")
        else:
            msg = err.get("msg", "校验失败")
            parts.append(f"{field}: {msg}")
    return "参数校验失败: " + "; ".join(parts)
```

---

## 16 配置管理

### 16.1 Pydantic Settings配置

```python
# core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """应用配置（从环境变量读取）"""

    # 应用配置
    APP_NAME: str = "Literature Assistant AI Service"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ChromaDB配置
    CHROMA_PATH: str = "./data/vector_db"

    # Embedding配置
    EMBEDDING_MODEL_PATH: str = "BAAI/bge-m3"
    EMBEDDING_DEVICE: str = "cpu"              # cpu / cuda
    EMBEDDING_EXPECTED_DIMENSION: int = 1024
    EMBEDDING_API_KEY: str = ""                # 外接Embedding API Key
    EMBEDDING_API_BASE: str = ""               # 外接Embedding API Base URL
    EMBEDDING_API_MODEL: str = ""              # 外接Embedding API 模型名

    # DashScope配置（当前主要Embedding方式）
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_EMBEDDING_MODEL: str = "text-embedding-v4"
    DASHSCOPE_EMBEDDING_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # LLM配置
    LLM_MODE: str = "api"                      # auto / builtin / api / local
    LLM_BUILTIN_URL: str = ""
    LLM_BUILTIN_API_KEY: str = ""
    LLM_BUILTIN_MODEL: str = ""
    LLM_API_KEY: str = ""                      # 用户自配API Key
    LLM_API_BASE: str = ""                     # 用户自配API Base URL
    LLM_MODEL_NAME: str = ""                   # 用户自配API 模型名
    LLM_LOCAL_MODEL_PATH: str = ""             # 本地模型路径
    LLM_TIMEOUT: int = 30                      # 单次推理超时(秒)
    LLM_RETRY_COUNT: int = 1                   # 重试次数
    LLM_RETRY_INTERVAL: int = 3                # 重试间隔(秒)

    # Agent配置
    AGENT_TIMEOUT: int = 30                    # 单Agent超时(秒)
    AGENT_FULL_TIMEOUT: int = 120              # 全流程超时(秒)
    AGENT_MAX_REGENERATE: int = 1              # 最大重新生成次数

    # 日志配置
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
```

### 16.2 .env.example

```bash
# AI Service 环境变量配置

# ChromaDB
CHROMA_PATH=./data/vector_db

# Embedding（DashScope API优先）
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v4
DASHSCOPE_EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
# 本地模型（已禁用）
# EMBEDDING_MODEL_PATH=BAAI/bge-m3
# EMBEDDING_DEVICE=cpu
# EMBEDDING_EXPECTED_DIMENSION=1024

# LLM配置（三路并行，auto模式按优先级降级）
LLM_MODE=api
# 方案A：软件方模型（最高优先级，待发榜单位提供URL后配置）
# LLM_BUILTIN_URL=https://llm.literature-assistant.com/v1
# 方案B：外接API（中等优先级，当前生效 = DeepSeek V4 Flash）
LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
LLM_API_BASE=https://api.deepseek.com/v1
LLM_MODEL_NAME=deepseek-v4-flash
# 方案C：本地模型（最低优先级，兜底方案）
# LLM_LOCAL_MODEL_PATH=Qwen/Qwen2-7B-Instruct

# Agent
AGENT_TIMEOUT=30
AGENT_FULL_TIMEOUT=120

# 日志
LOG_LEVEL=INFO
```

---

## 17 性能规范

### 17.1 性能指标

| 指标 | 目标值 | 实际值 | 说明 |
|------|--------|--------|------|
| 论文检索响应时间 | ≤ 3秒 | ~1-2秒 | Embedding+Chroma检索 |
| 单篇论文分析响应时间 | ≤ 30秒 | ~5-15秒 | 5维度信息提取 |
| 综述生成端到端响应时间 | ≤ 60秒 | ~30-50秒 | 3-Agent协同全过程 |
| 流式首字节响应时间 | ≤ 2秒 | ~1秒 | LLM流式生成 |
| 批量向量化速度 | 100条/10秒 | ~100条/8秒 | DashScope API批量处理 |
| SSE keep-alive间隔 | 15秒 | 15秒 | 防止连接超时 |

### 17.2 性能优化策略

| 优化项 | 策略 | 涉及模块 |
|--------|------|---------|
| LLM推理 | 流式输出（首字节<2秒）；模型量化（INT4，P2） | F3.3 |
| Embedding | 批量处理（batch_size=32）；GPU加速（可选） | F5.2 |
| 向量检索 | HNSW索引参数优化；结果缓存 | F3.2 |
| Agent协同 | 独立Agent并行执行（检索与分析可并行）；超时跳过 | F3.1 |
| 降级 | 单Agent失败跳过；多Agent失败降级为单Agent模式 | F3.1 |

---

## 18 日志与监控

### 18.1 日志配置

```python
# core/logging.py
from loguru import logger
import sys

def setup_logging(level: str = "INFO"):
    logger.remove()  # 移除默认handler

    logger.add(
        sys.stdout,
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name}:{function}:{line} | {message}",
        colorize=True
    )

    logger.add(
        "logs/ai-service-{time:YYYY-MM-DD}.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name}:{function}:{line} | {message}",
        rotation="00:00",       # 每天轮转
        retention="7 days",     # 保留7天
        compression="zip"       # 压缩旧日志
    )
```

### 18.2 关键日志点

| 操作 | 级别 | 日志内容 |
|------|------|---------|
| 模型加载 | INFO | `Model loaded: {model_name}, dimension={dim}` |
| Chroma初始化 | INFO | `ChromaDB initialized, papers count={count}` |
| SearchService初始化 | INFO | `SearchService initialized` |
| Reranker初始化 | INFO | `Reranker initialized and injected into SearchService` |
| Agent启动 | INFO | `Agent {name} started, task={analysis_id}` |
| Agent完成 | INFO | `Agent {name} completed, duration={ms}ms` |
| Agent超时 | WARNING | `Agent {name} timed out after {timeout}s` |
| Agent降级 | WARNING | `Agent workflow degraded: {reason}` |
| LLM调用 | DEBUG | `LLM call: mode={mode}, tokens={count}, duration={ms}ms` |
| LLM降级 | WARNING | `LLM fallback: {from_mode} → {to_mode}` |
| LLM自动恢复 | INFO | `LLM recovered: {old} → {new}` |
| SSE流取消 | DEBUG | `SSE stream cancelled for analysis_id={id}` |
| 混合检索 | INFO | `Hybrid search completed: query=..., semantic=N, keyword=N, fused=N, elapsed=...ms` |
| 重排序 | INFO | `Rerank completed: input_count=N, top1_score=..., elapsed_ms=...` |
| 检索请求 | DEBUG | `Search: query={query}, top_k={k}, results={count}` |
| 向量化 | DEBUG | `Embedding: {count} texts, duration={ms}ms` |
| 异常 | ERROR | `Exception in {module}: {error}` |

---

## 19 部署架构

### 19.1 Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p /app/data/papers /app/data/vector_db /app/logs

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

### 19.2 Docker Compose配置

```yaml
# Python AI服务
ai-service:
  build: ./ai-service-python
  ports:
    - "8000:8000"
  volumes:
    - ./models:/app/models           # 本地模型文件
    - ./data:/app/data               # 数据目录（论文+向量库）
  environment:
    - LLM_MODE=${LLM_MODE:-auto}
    - LLM_BUILTIN_URL=${LLM_BUILTIN_URL:-https://llm.literature-assistant.com/v1}
    - LLM_API_KEY=${LLM_API_KEY:-}
    - LLM_API_BASE=${LLM_API_BASE:-}
    - LLM_MODEL_NAME=${LLM_MODEL_NAME:-}
    - CHROMA_PATH=/app/data/vector_db
    - LOG_LEVEL=INFO
  # GPU支持（可选）
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
  networks:
    - app-network
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

### 19.3 requirements.txt

```
# Web Framework
fastapi==0.115.0
uvicorn[standard]==0.32.0
python-multipart==0.0.12
sse-starlette==2.1.0

# AI/ML
langgraph==0.2.28
langchain==0.3.0
langchain-community==0.3.0
transformers==4.45.0
torch==2.6.0
sentence-transformers==3.1.0

# Vector Database
chromadb==0.5.0

# LLM API
openai==1.50.0
httpx==0.27.0

# Data Processing
pydantic==2.9.0
pydantic-settings==2.5.0
numpy>=1.26.0,<2.0.0

# PDF Processing
pymupdf==1.25.0

# arXiv
arxiv==2.1.0

# Utilities
python-dotenv==1.0.0
loguru==0.7.0

# Testing
pytest==8.1.0
pytest-asyncio==0.23.0
```

---

## 附录A：AI服务开发检查清单

```
□ FastAPI应用是否正确配置生命周期（_safe_init超时保护）？
□ Pydantic请求模型是否包含extra="forbid"安全策略？
□ AnalyzeRequest是否包含必填的userId字段？
□ LLM服务是否实现三路降级+自动恢复（300s轮询）？
□ 每个Agent是否有超时控制（30秒）+规则降级？
□ LangGraph工作流是否为4节点（retrieve→analyze→generate→review+条件边+重试循环）？
□ AgentOrchestrator是否支持8种SSE事件+keep-alive+Last-Event-ID+review_rejected？
□ 个性化Prompt是否注入agent级别差异化指令？
□ Embedding是否优先使用DashScope API？
□ ChromaDB是否使用PersistentClient（数据持久化）？
□ Reranker是否实现复合评分（RRF+字段+流行度+年份+个性化）？
□ 搜索API是否支持3种端点（语义/混合/建议）？
□ 健康检查是否检查3组件（llm+embedding+chroma）+critical_ok规则？
□ 校验错误是否返回中文友好message？
□ 统一响应是否使用ok()/fail()包装器？
□ 敏感信息（API Key）是否通过环境变量注入？
```

---

## 附录B：AI服务与Java后端接口契约

### B.1 Java → Python 请求格式

```json
// POST /api/agent/analyze
{
    "topic": "Multi-Agent协同决策",
    "paperIds": ["arxiv_2024_001", "arxiv_2024_002"],
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

### B.2 Python → Java 响应格式

```json
// HTTP 200 响应
{
    "analysisId": "anl_20240523_001",
    "status": "completed",
    "result": {
        "report": "## 文献综述\n...",
        "citations": [
            {"paperId": "arxiv_2024_001", "text": "原文片段", "location": "第3段"}
        ],
        "structure": {
            "introduction": "...",
            "currentStatus": "...",
            "methodComparison": "...",
            "trends": "...",
            "references": "..."
        }
    },
    "agentStates": [
        {"name": "coordinator", "status": "completed", "durationMs": 2000, "intermediateResult": "分解为4个子任务"},
        {"name": "retriever", "status": "completed", "durationMs": 1200, "intermediateResult": "找到15篇相关论文"},
        {"name": "analyzer", "status": "completed", "durationMs": 8000, "intermediateResult": "已分析10篇论文"},
        {"name": "generator", "status": "completed", "durationMs": 15000, "intermediateResult": "综述生成完毕"},
        {"name": "reviewer", "status": "completed", "durationMs": 5000, "intermediateResult": "审核通过"}
    ],
    "degraded": false,
    "degradedReason": null
}
```

### B.3 SSE事件格式

AgentOrchestrator 支持8种SSE事件类型：

#### 1. agent_started — Agent开始执行

```
event: agent_started
data: {"agentName":"retriever","analysisId":"anl_001"}
```

#### 2. agent_state_update — Agent状态更新

```
event: agent_state_update
data: {"agentName":"retriever","status":"running","progress":0.3,"analysisId":"anl_001"}
```

#### 3. agent_completed — Agent执行完成

```
event: agent_completed
data: {"agentName":"retriever","status":"completed","intermediateResult":"找到10篇论文","durationMs":1200,"analysisId":"anl_001"}
```

#### 4. agent_failed — Agent执行失败

```
event: agent_failed
data: {"agentName":"comparer","status":"failed","error":"Agent comparer timed out after 30s","analysisId":"anl_001"}
```

#### 5. analysis_completed — 全流程分析完成

```
event: analysis_completed
data: {"analysisId":"anl_001","status":"completed","degraded":false}
```

#### 6. error — 系统级错误

```
event: error
data: {"code":500,"message":"LLM服务不可用","analysisId":"anl_001"}
```

#### 7. ping — keep-alive心跳

```
event: ping
data: {"timestamp":1716451200000}
```

#### 8. review_rejected — 审核不通过，触发重新生成

```
event: review_rejected
data: {"agentName":"reviewer","analysisId":"anl_001","regenerateCount":1,"issues":[{"claim":"...","error_type":"citation_error"}]}
```

---

> **文档维护**：架构变更时需更新本文档，重大变更需记录修订历史  
> **变更控制**：模块间接口变更需项目组讨论确认  
> **下一步**：
> - **P0（2026-06-28 复验阻断性缺陷）**：创建 `app/models/__init__.py` + `schemas.py` + `enums.py`，按 `test_graph.py:226-232` 与 `test_agent_endpoint.py:51-63` 契约反推字段定义（AnalyzeRequest、AnalyzeResponse、UserProfile、SearchRequest、SearchResponse、SearchResultItem、ModelStatusResponse 12 字段、AgentStateResponse、HybridSearchRequest、SearchSuggestResponse、AnalysisType/EducationLevel/KnowledgeLevel/PreferredStyle 枚举），使用 `populate_by_name=True` 支持 snake_case↔camelCase 双向
> - **P0**：在 `AppState` 类中添加 `personalization_service = None` 属性，在 `on_startup()` 中实例化 `PersonalizationService(prompt_manager=app_state.prompt_manager)`，消除个性化旁路
> - **P1**：实现 AnalyzerAgent 并行化（asyncio.gather + 信号量）
> - **P2**：LRU 缓存 LLM 响应、Embedding 批量优化、Prometheus 指标暴露
> - 后续按 F3.5→F5.2/F4.3→F3.3→F3.2→F3.4→F3.1 顺序实现各项增强功能
