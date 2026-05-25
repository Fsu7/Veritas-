# XH-202630 科研文献智能助手 — AI服务模块系统架构文档

> **课题编号**：XH-202630  
> **课题名称**：领域知识个性化生成与多智能体协同决策系统研究  
> **发榜单位**：上海云之脑智能科技有限公司（科大讯飞全资子公司）  
> **文档版本**：v1.0  
> **创建日期**：2026年5月23日  
> **文档状态**：初稿

---

## 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.0 | 2026-05-23 | 项目组 | 初始版本 |

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
| F3.1 | 多Agent协同引擎 | Agent角色定义、LangGraph工作流编排、降级机制 |
| F3.2 | RAG检索模块 | 文档向量化、语义检索、混合检索、重排序 |
| F3.3 | LLM服务模块 | 三路模型配置(软件方/外接API/本地)、推理服务、降级切换 |
| F3.4 | 个性化引擎模块 | 用户画像解析、Prompt个性化、难度/风格适配 |
| F3.5 | API服务模块 | FastAPI路由、请求校验、SSE推送 |
| F5.2 | Embedding模型模块 | 文本向量化(text-embedding-v4阿里云百炼API)、批量处理 |
| F4.3 | 向量数据库模块 | Chroma向量存储、相似度检索 |

### 1.3 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.10+ | 编程语言 |
| **FastAPI** | 0.110+ | AI服务框架 |
| **Uvicorn** | 0.29+ | ASGI服务器 |
| **LangGraph** | 0.0.50+ | 多Agent编排框架 |
| **LangChain** | 0.1.0+ | LLM应用框架 |
| **Transformers** | 4.40+ | 本地模型加载（HuggingFace） |
| **Sentence-Transformers** | 2.7+ | Embedding模型加载 |
| **ChromaDB** | 0.5.0+ | 向量数据库 |
| **Pydantic** | 2.7+ | 数据验证与配置管理 |
| **OpenAI SDK** | 1.23+ | 外接API调用（兼容接口） |
| **httpx** | 0.27+ | 异步HTTP客户端 |
| **Loguru** | 0.7.0 | 日志框架 |
| **NumPy** | 1.26+ | 数值计算 |
| **PyMuPDF** | 1.23+ | PDF解析 |
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
│  协调者Agent → 检索Agent → 分析Agent → 对比Agent            │
│  → 生成Agent → 审核Agent                                    │
│  工作流编排 → 状态管理 → 降级策略 → 超时控制                │
├─────────────────────────────────────────────────────────────┤
│                      服务层（Business Services）              │
│  LLMService → EmbeddingService → VectorStoreService         │
│  PersonalizationService → SearchService                     │
├─────────────────────────────────────────────────────────────┤
│                      基础设施层（Infrastructure）             │
│  ChromaDB → text-embedding-v4(阿里云百炼) → Qwen2/API/软件方模型             │
│  Prompt模板 → Redis（可选） → MySQL（通过Java间接访问）      │
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
    │   │ 协调者Agent分解任务
    │   ▼
    │   检索Agent → EmbeddingService.encode() → ChromaDB.query()
    │   │ SSE推送Agent状态
    │   ▼
    │   分析Agent → LLMService.generate()（结构化提取）
    │   │ SSE推送Agent状态
    │   ▼
    │   对比Agent（可选）→ LLMService.generate()
    │   │ SSE推送Agent状态
    │   ▼
    │   生成Agent → PersonalizationService.build_prompt() → LLMService.generate()
    │   │ SSE推送Agent状态
    │   ▼
    │   审核Agent → LLMService.generate()（事实核查）
    │   │ SSE推送Agent状态
    │   ▼
    │   协调者Agent汇总 → 返回最终结果
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
ai-service-python/
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI入口，应用生命周期管理
│   │
│   ├── api/                             # API路由层
│   │   ├── __init__.py
│   │   ├── router.py                    # 路由聚合（汇总所有endpoint）
│   │   └── endpoints/
│   │       ├── __init__.py
│   │       ├── agent.py                 # Agent调用接口（POST /api/agent/analyze）
│   │       ├── search.py                # 检索接口（POST /api/search）
│   │       └── model.py                 # 模型状态接口（GET /api/model/status）
│   │
│   ├── core/                            # 核心配置
│   │   ├── __init__.py
│   │   ├── config.py                    # Pydantic Settings配置（环境变量）
│   │   ├── events.py                    # 启动/关闭事件（模型加载/释放）
│   │   └── logging.py                   # 日志配置（Loguru）
│   │
│   ├── agents/                          # 多Agent模块（F3.1）
│   │   ├── __init__.py
│   │   ├── coordinator.py               # 协调者Agent
│   │   ├── retriever.py                  # 检索Agent
│   │   ├── analyzer.py                   # 分析Agent
│   │   ├── comparer.py                   # 对比Agent
│   │   ├── generator.py                 # 生成Agent
│   │   ├── reviewer.py                  # 审核Agent
│   │   ├── base.py                      # Agent基类
│   │   ├── tools.py                     # Agent工具定义（向量检索、关键词搜索）
│   │   └── graph.py                    # LangGraph工作流定义
│   │
│   ├── services/                        # 服务层
│   │   ├── __init__.py
│   │   ├── llm_service.py              # LLM推理服务（F3.3）
│   │   ├── embedding_service.py        # Embedding向量化服务（F5.2）
│   │   ├── vector_store_service.py     # Chroma向量存储服务（F3.2+F4.3）
│   │   ├── search_service.py           # 检索服务（F3.2）
│   │   └── personalization_service.py  # 个性化引擎服务（F3.4）
│   │
│   ├── models/                          # 数据模型
│   │   ├── __init__.py
│   │   ├── schemas.py                  # Pydantic请求/响应模型
│   │   └── enums.py                    # 枚举定义
│   │
│   └── utils/                           # 工具函数
│       ├── __init__.py
│       ├── text_processing.py          # 文本处理（分块、清洗）
│       └── citation_parser.py          # 引用解析
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
│   └── reviewer.txt                     # 审核Agent Prompt
│
├── tests/                               # 测试
│   ├── __init__.py
│   ├── test_agents.py                   # Agent测试
│   ├── test_search.py                   # 检索测试
│   ├── test_llm.py                      # LLM服务测试
│   └── test_embedding.py               # Embedding测试
│
├── scripts/                             # 工具脚本
│   ├── import_papers.py                # 论文数据导入脚本
│   ├── build_vector_db.py              # 向量数据库构建脚本
│   └── evaluate.py                     # 评估脚本
│
├── Dockerfile                           # Docker构建文件
├── requirements.txt                     # Python依赖
├── .env                                 # 环境变量（不入Git）
├── .env.example                         # 环境变量示例
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
from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # === 启动阶段 ===
    logger.info("Starting AI Service...")

    # 1. 初始化Embedding服务（text-embedding-v4，阿里云百炼API）
    await embedding_service.load_model()
    logger.info("Embedding model loaded")

    # 2. 初始化Chroma连接
    await vector_store_service.initialize()
    logger.info("ChromaDB initialized")

    # 3. 初始化LLM服务（根据配置选择模型来源）
    await llm_service.initialize()
    logger.info(f"LLM service initialized, mode={settings.LLM_MODE}")

    # 4. 加载Prompt模板
    await prompt_manager.load_templates()
    logger.info("Prompt templates loaded")

    logger.info("AI Service started successfully")
    yield

    # === 关闭阶段 ===
    logger.info("Shutting down AI Service...")

    # 1. 释放LLM模型显存（如果是本地模型）
    await llm_service.unload_model()

    # 2. 关闭Chroma连接
    await vector_store_service.close()

    logger.info("AI Service shut down")

app = FastAPI(
    title="Literature Assistant AI Service",
    version="1.0.0",
    lifespan=lifespan
)

# 注册路由
app.include_router(api_router, prefix="/api")
```

### 4.3 路由定义

```python
# api/router.py
from fastapi import APIRouter

api_router = APIRouter()

# Agent调用接口
api_router.include_router(
    agent_router,
    prefix="/agent",
    tags=["agent"]
)

# 检索接口
api_router.include_router(
    search_router,
    prefix="/search",
    tags=["search"]
)

# 模型状态接口
api_router.include_router(
    model_router,
    prefix="/model",
    tags=["model"]
)
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

#### 4.4.3 健康检查与模型状态

```python
# api/endpoints/model.py
@router.get("/status")
async def model_status() -> ModelStatusResponse:
    """
    查询模型加载状态

    响应：
    {
        "llmStatus": "loaded",             // loading / loaded / error
        "llmMode": "builtin",              // builtin / api / local
        "embeddingStatus": "loaded",
        "chromaStatus": "connected",
        "gpuAvailable": true,
        "gpuMemoryUsed": "4.2GB / 16GB"
    }
    """
```

#### 4.4.4 根路径健康检查

```python
# main.py
@app.get("/health")
async def health():
    return {
        "status": "UP",
        "timestamp": datetime.now().isoformat(),
        "llm": llm_service.status,
        "embedding": embedding_service.status,
        "chroma": vector_store_service.status
    }
```

### 4.5 API接口清单

| 编号 | 方法 | 路径 | 优先级 | 说明 |
|------|------|------|--------|------|
| F3.5.1 | POST | `/api/agent/analyze` | P0 | 启动Agent分析任务 |
| F3.5.1 | POST | `/api/agent/analyze/stream` | P1 | Agent分析+SSE推送 |
| F3.5.2 | POST | `/api/search` | P0 | 语义检索论文 |
| F3.5.3 | GET | `/health` | P0 | 健康检查 |
| F3.5.4 | GET | `/api/model/status` | P1 | 模型状态查询 |

---

## 5 多Agent协同引擎模块（F3.1）

### 5.1 模块概述

系统的核心创新模块，基于LangGraph编排6个Agent角色的协同工作流，实现任务分解、分配、监督和结果汇总。支持条件分支（对比Agent仅在多论文时激活）和降级机制。

### 5.2 Agent角色定义

| Agent | 文件 | 角色定位 | 输入 | 输出 | 核心工具 |
|-------|------|---------|------|------|---------|
| **协调者Agent** | `coordinator.py` | 项目经理 | 用户问题 + 用户画像 | 任务分解指令 + 最终回答 | 任务分解器 |
| **检索Agent** | `retriever.py` | 图书管理员 | 研究主题关键词 | Top10论文列表 | 向量检索、关键词搜索 |
| **分析Agent** | `analyzer.py` | 论文审稿人 | 论文全文/摘要 | 结构化分析卡片(5维度) | 文本提取、信息抽取 |
| **对比Agent** | `comparer.py` | 对比研究员 | 2-5篇论文分析结果 | 对比表格+差异总结+矛盾发现 | 对比引擎 |
| **生成Agent** | `generator.py` | 学术写手 | 分析结果+用户画像 | 个性化综述报告 | 大模型生成 |
| **审核Agent** | `reviewer.py` | 学术编辑 | 生成内容+原始论文 | 审核通过/修改建议 | 引用核查、事实比对 |

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

class BaseAgent(ABC):
    """Agent基类"""

    def __init__(self, name: str, llm_service, prompt_template: str):
        self.name = name
        self.llm_service = llm_service
        self.prompt_template = prompt_template
        self.state = AgentState(name=name)
        self.timeout = 30  # 单Agent超时30秒

    async def execute(self, input_data: dict, context: dict) -> dict:
        """执行Agent任务（含状态管理和超时控制）"""
        # 1. 更新状态为running
        self.state.status = AgentStatus.RUNNING
        self.state.started_at = datetime.now()

        try:
            # 2. 构建Prompt
            prompt = self.build_prompt(input_data, context)

            # 3. 执行核心逻辑（带超时控制）
            result = await asyncio.wait_for(
                self._run(prompt, input_data, context),
                timeout=self.timeout
            )

            # 4. 更新状态为completed
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
    async def _run(self, prompt: str, input_data: dict, context: dict) -> dict:
        """子类实现的核心执行逻辑"""
        pass

    @abstractmethod
    def build_prompt(self, input_data: dict, context: dict) -> str:
        """构建Agent Prompt"""
        pass

    def _fallback_result(self, input_data: dict) -> dict:
        """降级时的默认返回"""
        return {"degraded": True, "agent": self.name, "error": self.state.error}

    def _summarize_result(self, result: dict) -> str:
        """生成中间结果摘要（用于可视化）"""
        return str(result)[:200]
```

### 5.4 各Agent详细设计

#### 5.4.1 协调者Agent（Coordinator）

```python
# agents/coordinator.py
class CoordinatorAgent(BaseAgent):
    """
    协调者Agent — 项目经理角色

    职责：
    1. 接收用户问题和画像
    2. 分解为子任务（检索、分析、对比、生成、审核）
    3. 分配子任务给对应Agent
    4. 监督执行进度
    5. 汇总最终结果
    """

    async def _run(self, prompt: str, input_data: dict, context: dict) -> dict:
        # 1. 使用LLM分析用户问题，分解子任务
        task_breakdown = await self.llm_service.generate(prompt)

        # 2. 确定任务列表
        tasks = self._parse_task_breakdown(task_breakdown, input_data)

        # 3. 返回任务分解结果（后续由LangGraph图执行）
        return {
            "sub_tasks": tasks,
            "task_count": len(tasks),
            "requires_compare": len(input_data.get("paperIds", [])) >= 2
        }

    def _parse_task_breakdown(self, breakdown: str, input_data: dict) -> list:
        """解析LLM生成的任务分解结果"""
        tasks = [
            {"name": "retrieve", "description": f"检索关于'{input_data['topic']}'的相关论文"},
            {"name": "analyze", "description": "分析检索到的论文核心内容"},
        ]
        # 多论文时添加对比任务
        if len(input_data.get("paperIds", [])) >= 2:
            tasks.append({"name": "compare", "description": "对比多篇论文的方法和结论"})
        tasks.append({"name": "generate", "description": "生成个性化文献综述"})
        tasks.append({"name": "review", "description": "审核生成内容的准确性和引用"})
        return tasks
```

#### 5.4.2 检索Agent（Retriever）

```python
# agents/retriever.py
class RetrieverAgent(BaseAgent):
    """
    检索Agent — 图书管理员角色

    职责：
    1. 接收检索关键词
    2. 从Chroma向量库中检索相关论文
    3. 支持元数据过滤（年份、会议等）
    4. 返回Top10结果
    """

    async def _run(self, prompt: str, input_data: dict, context: dict) -> dict:
        query = input_data.get("topic", "")
        top_k = input_data.get("top_k", 10)

        # 1. 向量语义检索
        vector_results = await vector_store_service.search(
            query=query, top_k=top_k
        )

        # 2. 关键词检索（可选，混合检索）
        # keyword_results = ...

        # 3. 融合结果
        papers = vector_results

        self.state.intermediate_result = f"找到{len(papers)}篇相关论文，筛选Top{min(top_k, len(papers))}"

        return {
            "papers": papers[:top_k],
            "total_found": len(papers)
        }
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
    3. 输出结构化JSON

    5维度：
    - 研究问题（Research Question）
    - 核心方法（Core Method）
    - 主要实验（Key Experiments）
    - 核心结论（Core Findings）
    - 局限性（Limitations）
    """

    async def _run(self, prompt: str, input_data: dict, context: dict) -> dict:
        papers = input_data.get("papers", [])
        analysis_results = []

        for i, paper in enumerate(papers):
            self.state.progress = (i + 1) / len(papers)
            self.state.intermediate_result = f"已分析{i+1}/{len(papers)}篇"

            # 构建分析Prompt
            analysis_prompt = self.build_analysis_prompt(paper)

            # 调用LLM提取结构化信息
            result_text = await self.llm_service.generate(analysis_prompt)

            # 解析为结构化JSON
            analysis = self._parse_analysis(result_text, paper)
            analysis_results.append(analysis)

        return {
            "analysis_results": analysis_results,
            "analyzed_count": len(analysis_results)
        }

    def _parse_analysis(self, result_text: str, paper: dict) -> dict:
        """解析LLM输出为结构化分析结果"""
        try:
            return json.loads(result_text)
        except json.JSONDecodeError:
            return {
                "paperId": paper.get("paperId"),
                "researchQuestion": result_text[:200],
                "coreMethod": "",
                "keyExperiments": "",
                "coreFindings": "",
                "limitations": ""
            }
```

#### 5.4.4 对比Agent（Comparer）

```python
# agents/comparer.py
class ComparerAgent(BaseAgent):
    """
    对比Agent — 对比研究员角色

    职责：
    1. 接收2-5篇论文的分析结果
    2. 在方法、数据集、性能、结论维度进行对比
    3. 生成对比表格和差异总结
    4. 检测论文间的观点矛盾
    """

    async def _run(self, prompt: str, input_data: dict, context: dict) -> dict:
        analysis_results = input_data.get("analysis_results", [])

        # 构建对比Prompt
        compare_prompt = self.build_compare_prompt(analysis_results)

        # 调用LLM生成对比
        result_text = await self.llm_service.generate(compare_prompt)

        # 解析对比结果
        comparison = self._parse_comparison(result_text)

        return {
            "comparison_table": comparison.get("table", {}),
            "summary": comparison.get("summary", ""),
            "conflicts": comparison.get("conflicts", [])  # 矛盾发现
        }
```

#### 5.4.5 生成Agent（Generator）

```python
# agents/generator.py
class GeneratorAgent(BaseAgent):
    """
    生成Agent — 学术写手角色

    职责：
    1. 接收分析结果和用户画像
    2. 生成个性化文献综述
    3. 综述包含：引言、研究现状、方法对比、研究趋势、参考文献
    4. 根据画像调整内容深度和表达风格
    """

    async def _run(self, prompt: str, input_data: dict, context: dict) -> dict:
        # 1. 从上下文获取用户画像
        user_profile = context.get("user_profile", {})

        # 2. 使用个性化引擎构建Prompt
        personalized_prompt = personalization_service.build_generation_prompt(
            analysis_results=input_data.get("analysis_results", []),
            comparison_result=input_data.get("comparison_result", {}),
            user_profile=user_profile
        )

        # 3. 调用LLM生成综述
        report = await self.llm_service.generate(personalized_prompt)

        # 4. 提取引用标注
        citations = citation_parser.extract_citations(report)

        return {
            "report": report,
            "citations": citations,
            "word_count": len(report)
        }
```

#### 5.4.6 审核Agent（Reviewer）

```python
# agents/reviewer.py
class ReviewerAgent(BaseAgent):
    """
    审核Agent — 学术编辑角色

    职责：
    1. 检查生成内容的准确性
    2. 与知识库原文比对，标记不一致之处
    3. 对涉及具体数字、日期、名称的信息重点核查
    4. 核查引用正确性
    5. 返回审核通过或修改建议
    """

    async def _run(self, prompt: str, input_data: dict, context: dict) -> dict:
        report = input_data.get("report", "")
        original_papers = context.get("papers", [])

        # 1. 构建审核Prompt
        review_prompt = self.build_review_prompt(report, original_papers)

        # 2. 调用LLM进行审核
        review_result = await self.llm_service.generate(review_prompt)

        # 3. 解析审核结果
        review = self._parse_review(review_result)

        return {
            "approved": review.get("approved", False),
            "issues": review.get("issues", []),
            "suggestions": review.get("suggestions", []),
            "citation_accuracy": review.get("citation_accuracy", 0.0)
        }
```

### 5.5 LangGraph工作流定义

```python
# agents/graph.py
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any, Optional

class WorkflowState(TypedDict):
    """LangGraph工作流状态定义"""
    # 输入
    query: str                          # 用户原始查询
    user_profile: dict                  # 用户画像
    analysis_type: str                  # 分析类型
    analysis_id: str                    # 分析任务ID

    # 中间状态
    sub_tasks: list                     # 分解的子任务
    search_results: list                # 检索结果
    analysis_results: list              # 分析结果
    compare_result: dict                # 对比结果
    report: str                         # 生成的综述
    review_result: dict                 # 审核结果
    citations: list                     # 引用列表

    # 最终输出
    final_output: str                   # 最终输出
    agent_states: dict                  # 各Agent状态（用于可视化）

    # 错误处理
    errors: list                        # 错误记录
    degraded: bool                      # 是否降级


def build_agent_graph(
    coordinator: CoordinatorAgent,
    retriever: RetrieverAgent,
    analyzer: AnalyzerAgent,
    comparer: ComparerAgent,
    generator: GeneratorAgent,
    reviewer: ReviewerAgent
) -> StateGraph:
    """构建Agent协同工作流图"""

    # 创建状态图
    graph = StateGraph(WorkflowState)

    # 添加节点
    graph.add_node("coordinate", coordinator_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("compare", compare_node)
    graph.add_node("generate", generate_node)
    graph.add_node("review", review_node)

    # 设置入口
    graph.set_entry_point("coordinate")

    # 添加边
    graph.add_edge("coordinate", "retrieve")
    graph.add_edge("retrieve", "analyze")

    # 条件边：分析后根据论文数量决定是否进入对比
    graph.add_conditional_edges(
        "analyze",
        should_compare,
        {
            True: "compare",
            False: "generate"
        }
    )

    graph.add_edge("compare", "generate")
    graph.add_edge("generate", "review")

    # 条件边：审核后决定是否返回生成
    graph.add_conditional_edges(
        "review",
        should_regenerate,
        {
            True: "generate",      # 审核不通过，重新生成
            False: END             # 审核通过，结束
        }
    )

    return graph.compile()


def should_compare(state: WorkflowState) -> bool:
    """判断是否需要对比（论文数 >= 2）"""
    return len(state.get("search_results", [])) >= 2

def should_regenerate(state: WorkflowState) -> bool:
    """判断是否需要重新生成"""
    review = state.get("review_result", {})
    # 最多重试1次
    regenerate_count = state.get("regenerate_count", 0)
    if not review.get("approved", True) and regenerate_count < 1:
        return True
    return False
```

### 5.6 工作流可视化

```
START → coordinate → retrieve → analyze
                                    │
                    ┌───────────────┤
                    │               │
                    ▼               ▼
               compare        generate
                    │               │
                    └───────┬───────┘
                            │
                            ▼
                         review
                            │
                    ┌───────┤
                    │       │
              不通过 │       │ 通过
                    ▼       ▼
              generate     END
              (重试1次)

超时控制：
├── 单节点超时：30秒
├── 全流程超时：120秒
└── 降级策略：单节点失败跳过，多节点失败降级为单Agent模式
```

### 5.7 降级策略

```
降级层级：

Level 0：全Agent协同（正常模式）
├── 6个Agent按LangGraph工作流顺序执行
├── 支持条件分支（对比Agent可选）
└── 全流程耗时目标：60秒内

Level 1：单Agent失败跳过
├── 某个Agent执行超时（30秒）→ 跳过该Agent
├── 审核Agent失败 → 跳过审核，直接输出
├── 对比Agent失败 → 跳过对比，直接生成
└── 记录失败日志，在最终结果中标注"部分降级"

Level 2：多Agent失败 → 单Agent模式
├── 3个以上Agent失败 → 降级为单Agent模式
├── 仅执行：检索 + 生成（跳过分析/对比/审核）
├── 返回部分结果 + 降级说明
└── 最终结果标注"已降级"

Level 3：全部失败
├── 所有Agent均失败 → 返回错误提示
└── "系统暂时无法完成分析，请稍后重试"
```

### 5.8 Agent状态管理（用于可视化推送）

```python
# 实时状态结构（通过SSE推送给Java后端）
{
    "coordinator": {
        "status": "completed",           # waiting / running / completed / failed
        "startedAt": "2026-05-23T10:00:00",
        "completedAt": "2026-05-23T10:00:02",
        "durationMs": 2000,
        "intermediateResult": "分解为4个子任务"
    },
    "retriever": {
        "status": "completed",
        "startedAt": "2026-05-23T10:00:02",
        "completedAt": "2026-05-23T10:00:03",
        "durationMs": 1200,
        "intermediateResult": "找到15篇相关论文，筛选Top10"
    },
    "analyzer": {
        "status": "running",
        "startedAt": "2026-05-23T10:00:03",
        "progress": 0.8,
        "intermediateResult": "已分析8/10篇"
    },
    "comparer": {
        "status": "waiting"
    },
    "generator": {
        "status": "waiting"
    },
    "reviewer": {
        "status": "waiting"
    }
}
```

### 5.9 功能清单

| 编号 | 功能 | 优先级 | 说明 |
|------|------|--------|------|
| F3.1.1 | 协调者Agent | P0 | 任务分解、分配、监督、结果汇总 |
| F3.1.2 | 检索Agent | P0 | 向量检索+关键词检索，返回Top10 |
| F3.1.3 | 分析Agent | P0 | 提取5维度核心信息，输出JSON |
| F3.1.4 | 对比Agent | P1 | 多论文方法/结论对比，矛盾发现 |
| F3.1.5 | 生成Agent | P0 | 个性化综述生成，含引用标注 |
| F3.1.6 | 审核Agent | P1 | 事实核查+引用核查，审核通过/修改建议 |
| F3.1.7 | 工作流编排 | P0 | LangGraph StateGraph，条件分支，超时控制 |
| F3.1.8 | 降级机制 | P1 | 单Agent失败跳过，多Agent失败降级为单Agent模式 |

---

## 6 RAG检索模块（F3.2）

### 6.1 模块概述

基于向量语义检索和关键词检索的混合RAG（Retrieval-Augmented Generation）模块，为检索Agent和搜索接口提供论文检索能力。

### 6.2 类设计

#### 6.2.1 SearchService

```python
# services/search_service.py
class SearchService:
    """检索服务 — 协调向量检索和关键词检索"""

    def __init__(self, vector_store_service, embedding_service):
        self.vector_store = vector_store_service
        self.embedding = embedding_service

    async def search(self, query: str, top_k: int = 10,
                     filters: dict = None) -> list:
        """
        语义检索

        流程：
        1. query → embedding_service.encode() → 查询向量
        2. 向量 → vector_store_service.search() → TopK结果
        3. 结果 → 重排序 → 返回
        """
        # 1. 向量化查询
        query_embedding = await self.embedding.encode(query)

        # 2. 向量检索
        results = await self.vector_store.search(
            embedding=query_embedding,
            top_k=top_k,
            filters=filters
        )

        # 3. 重排序（P1）
        if self.reranker:
            results = await self.reranker.rerank(query, results)

        return results

    async def hybrid_search(self, query: str, top_k: int = 10,
                            filters: dict = None) -> list:
        """
        混合检索（P1功能）

        流程：
        1. 并行执行语义检索和关键词检索
        2. 使用RRF（Reciprocal Rank Fusion）融合两路结果
        3. 返回融合排序后的结果
        """
        # 并行检索
        semantic_results, keyword_results = await asyncio.gather(
            self.search(query, top_k=top_k * 2, filters=filters),
            self.keyword_search(query, top_k=top_k * 2, filters=filters)
        )

        # RRF融合
        fused = self._reciprocal_rank_fusion(
            semantic_results, keyword_results, k=60
        )

        return fused[:top_k]

    def _reciprocal_rank_fusion(self, list1: list, list2: list,
                                 k: int = 60) -> list:
        """
        Reciprocal Rank Fusion

        RRF_score(d) = Σ 1/(k + rank_i(d))
        """
        scores = {}
        for rank, item in enumerate(list1):
            pid = item["paperId"]
            scores[pid] = scores.get(pid, 0) + 1 / (k + rank + 1)
            if pid not in scores:
                scores[pid] = {"item": item}

        for rank, item in enumerate(list2):
            pid = item["paperId"]
            scores[pid] = scores.get(pid, 0) + 1 / (k + rank + 1)

        # 按融合分数排序
        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [v["item"] for _, v in sorted_items]
```

#### 6.2.2 Reranker（重排序，P1功能）

```python
# services/reranker.py
class Reranker:
    """对检索结果进行相关性重排序"""

    async def rerank(self, query: str, results: list) -> list:
        """
        重排序策略：
        1. 规则方法：根据标题匹配度、关键词匹配度调整排序
        2. Cross-Encoder方法（可选）：使用Cross-Encoder模型重新打分
        """
        # 规则重排序
        for item in results:
            score = item.get("score", 0)
            # 标题包含查询关键词 → 加分
            if query.lower() in item.get("title", "").lower():
                score += 0.1
            item["rerank_score"] = score

        results.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        return results
```

### 6.3 检索流程

```
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
Reranker.rerank()（P1）
    │ 规则重排序 + 关键词加分
    │ 筛选Top10
    ▼
返回结果
    [{paperId, title, abstract, score, year, venue}, ...]
```

### 6.4 功能清单

| 编号 | 功能 | 优先级 | 说明 |
|------|------|--------|------|
| F3.2.1 | 文档向量化 | P0 | 论文标题+摘要 → 1024维向量，批量100条/10秒 |
| F3.2.2 | 向量存储 | P0 | 向量+元数据存入Chroma，建立papers collection |
| F3.2.3 | 语义检索 | P0 | 查询向量 → TopK相似论文，cosine相似度 |
| F3.2.4 | 混合检索 | P1 | 语义检索 + 关键词检索 + RRF融合 |
| F3.2.5 | 重排序 | P1 | 规则重排序，提升Top5质量 |
| F3.2.6 | 检索优化 | P2 | 调整chunk_size、top_k、similarity_threshold |

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
│  LLM_BUILTIN_URL=https://llm.literature-assistant.com/v1   │
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
│  默认选择：方案A（软件方模型），不可用时自动降级            │
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

    def __init__(self, settings):
        self.settings = settings
        self.mode = settings.LLM_MODE
        self.providers = {}      # {mode: LLMProvider}
        self.active_provider = None
        self.status = "initializing"

    async def initialize(self):
        """初始化LLM服务，根据配置加载Provider"""
        if self.mode in (LLMMode.AUTO, LLMMode.BUILTIN):
            try:
                self.providers["builtin"] = BuiltinLLMProvider(self.settings)
                await self.providers["builtin"].test_connection()
                self.active_provider = self.providers["builtin"]
                self.status = "loaded"
                logger.info("LLM: Using builtin provider (软件方模型)")
                return
            except Exception as e:
                logger.warning(f"Builtin provider failed: {e}")

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
            return await self.active_provider.generate(
                prompt, max_tokens, temperature
            )
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            # 降级到下一个可用Provider
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
    - DeepSeek
    - 通义千问
    - 任何OpenAI兼容端点
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

    # 难度适配映射
    DIFFICULTY_MAP = {
        "beginner": {
            "term_density": "<5%",
            "strategy": "通俗解释+类比+入门路线",
            "example_type": "日常例子",
            "avoid": "复杂公式、专业术语、深入技术细节"
        },
        "intermediate": {
            "term_density": "~20%",
            "strategy": "标准描述+示例+方法对比",
            "example_type": "代码示例",
            "avoid": "过度简化"
        },
        "advanced": {
            "term_density": "~40%",
            "strategy": "专业术语+深入分析+研究空白",
            "example_type": "实验数据",
            "avoid": "基础概念解释"
        },
        "expert": {
            "term_density": ">50%",
            "strategy": "前沿洞察+创新建议+技术细节",
            "example_type": "论文引用",
            "avoid": "任何简化"
        }
    }

    # 风格适配映射
    STYLE_MAP = {
        "simple": {
            "tone": "日常用语+比喻",
            "paragraph": "简短段落",
            "structure": "要点式",
            "example": "Multi-Agent就像一个AI项目组，每个成员负责不同任务..."
        },
        "balanced": {
            "tone": "标准学术表达",
            "paragraph": "适度展开",
            "structure": "总分总",
            "example": "Multi-Agent系统通过多个智能体协同工作..."
        },
        "technical": {
            "tone": "正式学术+引用",
            "paragraph": "深入论证",
            "structure": "IMRAD",
            "example": "基于LangGraph框架（LangChain, 2024）的多智能体协同架构..."
        }
    }

    def build_generation_prompt(self, analysis_results: list,
                                 comparison_result: dict,
                                 user_profile: dict) -> str:
        """
        构建个性化的综述生成Prompt

        Args:
            analysis_results: 论文分析结果列表
            comparison_result: 对比分析结果
            user_profile: 用户画像

        Returns:
            完整的个性化Prompt
        """
        # 1. 解析画像
        education = user_profile.get("educationLevel", "master")
        field = user_profile.get("researchField", "")
        knowledge = user_profile.get("knowledgeLevel", "intermediate")
        style = user_profile.get("preferredStyle", "balanced")

        # 2. 获取适配策略
        difficulty = self.DIFFICULTY_MAP.get(knowledge, self.DIFFICULTY_MAP["intermediate"])
        style_config = self.STYLE_MAP.get(style, self.STYLE_MAP["balanced"])

        # 3. 构建个性化Prompt片段
        personalization_block = f"""
【重要】请根据以下用户信息调整回答内容：
- 用户身份：{self._education_label(education)}
- 研究方向：{field}（优先推荐该领域的案例和论文）
- 知识水平：{self._knowledge_label(knowledge)}
  → 术语密度：{difficulty['term_density']}
  → 内容策略：{difficulty['strategy']}
  → 示例类型：{difficulty['example_type']}
  → 需避免：{difficulty['avoid']}
- 表达风格：{self._style_label(style)}
  → 语气：{style_config['tone']}
  → 段落：{style_config['paragraph']}
  → 结构：{style_config['structure']}
"""

        # 4. 组装完整Prompt
        prompt = self._load_template("generator.txt")
        prompt = prompt.replace("{{personalization}}", personalization_block)
        prompt = prompt.replace("{{analysis_data}}", json.dumps(analysis_results, ensure_ascii=False))
        prompt = prompt.replace("{{comparison_data}}", json.dumps(comparison_result, ensure_ascii=False))

        return prompt

    def build_analysis_prompt(self, paper: dict, user_profile: dict) -> str:
        """
        构建个性化的论文分析Prompt
        """
        knowledge = user_profile.get("knowledgeLevel", "intermediate")

        # 初级/中级用户额外请求通俗解释
        extra_instruction = ""
        if knowledge in ("beginner", "intermediate"):
            extra_instruction = "\n额外要求：请为每个维度同时提供通俗解释，使用类比和日常例子。"

        prompt = self._load_template("analyzer.txt")
        prompt = prompt.replace("{{paper_title}}", paper.get("title", ""))
        prompt = prompt.replace("{{paper_abstract}}", paper.get("abstract", ""))
        prompt = prompt.replace("{{extra_instruction}}", extra_instruction)

        return prompt

    def _education_label(self, level: str) -> str:
        labels = {
            "undergraduate": "本科学生",
            "master": "硕士研究生",
            "phd": "博士研究生",
            "faculty": "教师/研究者"
        }
        return labels.get(level, level)

    def _knowledge_label(self, level: str) -> str:
        labels = {
            "beginner": "初级（对该领域了解较少）",
            "intermediate": "中级（有基础了解）",
            "advanced": "高级（深入研究）",
            "expert": "专家（领域权威）"
        }
        return labels.get(level, level)

    def _style_label(self, style: str) -> str:
        labels = {"simple": "通俗", "balanced": "均衡", "technical": "专业"}
        return labels.get(style, style)

    def _load_template(self, filename: str) -> str:
        """加载Prompt模板文件"""
        template_path = Path(__file__).parent.parent / "prompts" / filename
        return template_path.read_text(encoding="utf-8")
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

| 编号 | 功能 | 优先级 | 说明 |
|------|------|--------|------|
| F3.4.1 | 用户画像解析 | P0 | 解析Java后端传递的画像JSON |
| F3.4.2 | Prompt个性化 | P0 | 根据画像动态构建个性化Prompt片段 |
| F3.4.3 | 内容难度适配 | P0 | 根据knowledge_level调整术语密度和内容策略 |
| F3.4.4 | 风格适配 | P1 | 根据preferred_style调整表达方式 |
| F3.4.5 | 推荐策略 | P2 | 根据研究方向+历史偏好推荐论文 |

---

## 9 Embedding模型模块（F5.2）

### 9.1 模块概述

负责将文本转换为高维向量表示，是语义检索的基础。优先使用阿里云百炼API（text-embedding-v4），备选本地模型（bge-large-zh-v1.5）。

### 9.2 EmbeddingService实现

```python
# services/embedding_service.py
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import Union

class EmbeddingService:
    """文本向量化服务"""

    def __init__(self, settings):
        self.settings = settings
        self.model = None
        self.dimension = 1024
        self.status = "initializing"
        self._api_client = None  # 外接API客户端（备选）

    async def load_model(self):
        """加载本地Embedding模型"""
        try:
            self.model = SentenceTransformer(
                self.settings.EMBEDDING_MODEL_PATH or "BAAI/bge-large-zh-v1.5",
                device=self.settings.EMBEDDING_DEVICE or "cpu"
            )
            self.dimension = self.model.get_sentence_embedding_dimension()
            self.status = "loaded"
            logger.info(f"Embedding model loaded, dimension={self.dimension}")
        except Exception as e:
            logger.warning(f"Failed to load local embedding model: {e}")
            # 尝试使用外接API
            if self.settings.EMBEDDING_API_KEY:
                self._init_api_client()
                self.status = "loaded_api"
            else:
                self.status = "error"
                raise

    def _init_api_client(self):
        """初始化外接Embedding API"""
        from openai import AsyncOpenAI
        self._api_client = AsyncOpenAI(
            api_key=self.settings.EMBEDDING_API_KEY,
            base_url=self.settings.EMBEDDING_API_BASE or "https://api.openai.com/v1"
        )

    async def encode(self, text: Union[str, list]) -> np.ndarray:
        """
        文本向量化

        Args:
            text: 单条文本或文本列表

        Returns:
            1024维向量（单条）或向量矩阵（多条）
        """
        if self.model:
            # 本地模型
            return self.model.encode(text, normalize_embeddings=True)

        if self._api_client:
            # 外接API
            return await self._encode_via_api(text)

        raise RuntimeError("No embedding service available")

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

    async def _encode_via_api(self, text: Union[str, list]) -> np.ndarray:
        """通过外接API获取向量"""
        if isinstance(text, str):
            text = [text]

        model_name = self.settings.EMBEDDING_API_MODEL or "text-embedding-3-small"
        response = await self._api_client.embeddings.create(
            model=model_name,
            input=text
        )

        embeddings = [item.embedding for item in response.data]
        return np.array(embeddings)
```

### 9.3 功能清单

| 编号 | 功能 | 优先级 | 说明 |
|------|------|--------|------|
| F5.2.1 | 阿里云百炼API配置 | P0 | 配置text-embedding-v4 API，向量维度1024 |
| F5.2.2 | 文本向量化 | P0 | 单条/批量文本→1024维向量，支持本地或API |
| F5.2.3 | 批量向量化 | P0 | 100条/10秒，分批处理 |
| F5.2.4 | 外接Embedding API | P1 | Jina/OpenAI等API作为备选 |

---

## 10 向量数据库模块（F4.3）

### 10.1 VectorStoreService实现

```python
# services/vector_store_service.py
import chromadb
from typing import Optional

class VectorStoreService:
    """Chroma向量数据库服务"""

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

| 编号 | 功能 | 优先级 | 说明 |
|------|------|--------|------|
| F4.3.1 | 论文向量存储 | P0 | 向量+元数据存入Chroma |
| F4.3.2 | 语义相似度检索 | P0 | cosine相似度，TopK结果 |
| F4.3.3 | 向量索引管理 | P1 | 创建、更新、删除操作 |
| F4.3.4 | 批量导入 | P0 | 支持200+篇论文批量导入 |

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

| 编号 | 功能 | 优先级 | 说明 |
|------|------|--------|------|
| F4.4.1 | arXiv数据采集 | P0 | 从arXiv API下载AI/Agent领域论文200+篇 |
| F4.4.2 | 数据清洗 | P0 | 去重（按标题+作者）、格式统一 |
| F4.4.3 | 文档分块 | P0 | 按章节分块（500-1000字），保留章节标题 |
| F4.4.4 | 质量检查 | P0 | 检查数据完整性、格式正确性、内容准确性 |

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

### 12.2 Prompt模板示例

#### analyzer.txt

```
你是一位资深学术论文审稿人。请对以下论文进行深度分析，提取以下5个维度的核心信息：

【论文标题】：{{paper_title}}

【论文摘要】：{{paper_abstract}}

{{extra_instruction}}

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

{{personalization}}

【研究主题】：基于提供的论文分析数据

【论文分析数据】：
{{analysis_data}}

【对比分析数据】（如有）：
{{comparison_data}}

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
| `{{paper_title}}` | 论文标题 | analyzer |
| `{{paper_abstract}}` | 论文摘要 | analyzer |
| `{{extra_instruction}}` | 个性化额外指令 | analyzer |
| `{{personalization}}` | 个性化Prompt片段 | generator |
| `{{analysis_data}}` | 分析结果JSON | generator |
| `{{comparison_data}}` | 对比结果JSON | generator, comparer |
| `{{report_content}}` | 生成的综述内容 | reviewer |
| `{{original_papers}}` | 原始论文数据 | reviewer |

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
│  (graph.py)        │  │  (search_service)   │
│                    │  │                     │
│  coordinator ──┐   │  │  ┌── embedding_service
│  retriever  ───┤   │  │  └── vector_store_service
│  analyzer   ───┤   │  └────────────────────┘
│  comparer   ───┤   │
│  generator  ───┤   │
│  reviewer   ───┘   │
│        │           │
│        ▼           │
│  ┌─────────────────┤
│  │  llm_service    │
│  │  embedding_svc  │
│  │  vector_store   │
│  │  personalization│
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
from pydantic import BaseModel, Field
from typing import Optional, List
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
    educationLevel: EducationLevel
    researchField: str
    knowledgeLevel: KnowledgeLevel
    preferredStyle: PreferredStyle

class AnalyzeRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500)
    paperIds: List[str] = Field(default_factory=list)
    userProfile: UserProfile
    analysisType: AnalysisType
    analysisId: str = Field(..., min_length=1)

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    topK: int = Field(default=10, ge=1, le=50)
    filters: Optional[dict] = None

# ===== 响应模型 =====

class AgentStateResponse(BaseModel):
    agentName: str
    status: str           # waiting / running / completed / failed
    progress: Optional[float] = None
    intermediateResult: Optional[str] = None
    durationMs: Optional[int] = None

class AnalyzeResponse(BaseModel):
    analysisId: str
    status: str
    report: Optional[str] = None
    citations: Optional[list] = None
    agentStates: Optional[List[AgentStateResponse]] = None
    degraded: Optional[bool] = None
    degradedReason: Optional[str] = None

class SearchResult(BaseModel):
    paperId: str
    title: str
    abstract: Optional[str] = None
    score: float
    year: Optional[int] = None
    venue: Optional[str] = None

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int

class ModelStatusResponse(BaseModel):
    llmStatus: str         # loading / loaded / error
    llmMode: str           # builtin / api / local
    embeddingStatus: str   # loading / loaded / error
    chromaStatus: str      # connected / disconnected
    gpuAvailable: bool = False
    gpuMemoryUsed: Optional[str] = None
```

### 14.2 枚举定义

```python
# models/enums.py
class AgentName(str, Enum):
    COORDINATOR = "coordinator"
    RETRIEVER = "retriever"
    ANALYZER = "analyzer"
    COMPARER = "comparer"
    GENERATOR = "generator"
    REVIEWER = "reviewer"

class AgentStatus(str, Enum):
    WAITING = "waiting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class LLMMode(str, Enum):
    AUTO = "auto"
    BUILTIN = "builtin"
    API = "api"
    LOCAL = "local"
```

---

## 15 统一响应与异常处理

### 15.1 统一响应格式

```python
# 标准响应（与Java后端保持一致）
{
    "code": 200,
    "message": "success",
    "data": {...},
    "timestamp": 1716451200000
}

# 错误响应
{
    "code": 400,
    "message": "参数校验失败: topic不能为空",
    "data": null,
    "timestamp": 1716451200000
}
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
    pass

class VectorStoreException(AIServiceException):
    """向量数据库异常"""
    pass

class AgentTimeoutException(AIServiceException):
    """Agent执行超时"""
    pass

class ModelNotLoadedException(AIServiceException):
    """模型未加载"""
    pass
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
            "timestamp": int(datetime.now().timestamp() * 1000)
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={
            "code": 400,
            "message": f"参数校验失败: {str(exc)}",
            "data": None,
            "timestamp": int(datetime.now().timestamp() * 1000)
        }
    )
```

---

## 16 配置管理

### 16.1 Pydantic Settings配置

```python
# core/config.py
from pydantic_settings import BaseSettings

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
    EMBEDDING_MODEL_PATH: str = "BAAI/bge-large-zh-v1.5"
    EMBEDDING_DEVICE: str = "cpu"              # cpu / cuda
    EMBEDDING_API_KEY: str = ""                # 外接Embedding API Key
    EMBEDDING_API_BASE: str = ""               # 外接Embedding API Base URL
    EMBEDDING_API_MODEL: str = ""              # 外接Embedding API 模型名

    # LLM配置
    LLM_MODE: str = "auto"                     # auto / builtin / api / local
    LLM_BUILTIN_URL: str = "https://llm.literature-assistant.com/v1"
    LLM_BUILTIN_API_KEY: str = "builtin"
    LLM_BUILTIN_MODEL: str = "literature-assistant-pro"
    LLM_API_KEY: str = ""                      # 用户自配API Key
    LLM_API_BASE: str = ""                     # 用户自配API Base URL
    LLM_MODEL_NAME: str = ""                   # 用户自配API 模型名
    LLM_LOCAL_MODEL_PATH: str = ""             # 本地模型路径
    LLM_TIMEOUT: int = 30                      # 单次推理超时(秒)
    LLM_RETRY_COUNT: int = 1                   # 重试次数
    LLM_RETRY_INTERVAL: int = 3                # 重试间隔(秒)

    # 讯飞星火配置（可选）
    XFYUN_API_KEY: str = ""
    XFYUN_API_SECRET: str = ""

    # Agent配置
    AGENT_TIMEOUT: int = 30                    # 单Agent超时(秒)
    AGENT_FULL_TIMEOUT: int = 120              # 全流程超时(秒)
    AGENT_MAX_REGENERATE: int = 1              # 最大重新生成次数

    # 日志配置
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

### 16.2 .env.example

```bash
# AI Service 环境变量配置

# ChromaDB
CHROMA_PATH=./data/vector_db

# Embedding
EMBEDDING_MODEL_PATH=BAAI/bge-large-zh-v1.5
EMBEDDING_DEVICE=cpu
# EMBEDDING_API_KEY=          # 外接API Key（备选方案）
# EMBEDDING_API_BASE=         # 外接API Base URL
# EMBEDDING_API_MODEL=        # 外接API 模型名

# LLM配置（三路并行，auto模式按优先级降级）
LLM_MODE=auto
# 方案A：软件方模型（最高优先级，开箱即用）
LLM_BUILTIN_URL=https://llm.literature-assistant.com/v1
# 方案B：外接API（中等优先级，用户自配）
# LLM_API_KEY=sk-xxx
# LLM_API_BASE=https://api.deepseek.com/v1
# LLM_MODEL_NAME=deepseek-chat
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

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 论文检索响应时间 | ≤ 3秒 | Embedding+Chroma检索 |
| 单篇论文分析响应时间 | ≤ 30秒 | 5维度信息提取 |
| 综述生成端到端响应时间 | ≤ 60秒 | 6-Agent协同全过程 |
| 流式首字节响应时间 | ≤ 2秒 | LLM流式生成 |
| 批量向量化速度 | 100条/10秒 | text-embedding-v4 API批量处理 |
| Agent协同降级成功率 | ≥ 95% | 降级后仍返回部分结果 |
| AI服务调用成功率 | ≥ 99% | 含重试和降级 |
| 单Agent超时时间 | 30秒 | 超时后跳过 |

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
| Agent启动 | INFO | `Agent {name} started, task={analysis_id}` |
| Agent完成 | INFO | `Agent {name} completed, duration={ms}ms` |
| Agent超时 | WARNING | `Agent {name} timed out after {timeout}s` |
| Agent降级 | WARNING | `Agent workflow degraded: {reason}` |
| LLM调用 | DEBUG | `LLM call: mode={mode}, tokens={count}, duration={ms}ms` |
| LLM降级 | WARNING | `LLM fallback: {from_mode} → {to_mode}` |
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
fastapi==0.110.0
uvicorn[standard]==0.29.0
python-multipart==0.0.9
sse-starlette==2.0.0

# AI/ML
langgraph==0.0.50
langchain==0.1.16
langchain-community==0.0.34
transformers==4.40.0
torch==2.2.0
sentence-transformers==2.7.0

# Vector Database
chromadb==0.5.0

# LLM API
openai==1.23.0
httpx==0.27.0

# Data Processing
pydantic==2.7.0
pydantic-settings==2.2.1
numpy==1.26.0

# PDF Processing
pymupdf==1.23.0

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
□ FastAPI应用是否正确配置生命周期（模型加载/释放）？
□ Pydantic请求模型是否包含完整的字段校验？
□ LLM服务是否实现三路降级（软件方→API→本地）？
□ 每个Agent是否有超时控制（30秒）？
□ Agent协同是否实现降级机制（单Agent失败→跳过，多Agent失败→单Agent模式）？
□ LangGraph工作流是否正确设置条件分支？
□ 个性化Prompt是否正确注入用户画像信息？
□ Embedding模型是否支持本地+API两种方式？
□ ChromaDB是否使用PersistentClient（数据持久化）？
□ SSE推送是否正确实现Agent状态更新？
□ Prompt模板是否从文件加载（不硬编码）？
□ 敏感信息（API Key）是否通过环境变量注入？
□ 日志是否包含足够的调试信息？
□ 健康检查接口是否返回所有组件状态？
□ 错误响应是否与Java后端保持统一格式？
```

---

## 附录B：AI服务与Java后端接口契约

### B.1 Java → Python 请求格式

```json
// POST /api/agent/analyze
{
    "topic": "Multi-Agent协同决策",
    "paperIds": ["arxiv_2024_001", "arxiv_2024_002"],
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

```
event: agent_state_update
data: {"agentName":"retriever","status":"running","progress":0.3,"analysisId":"anl_001"}

event: agent_state_update
data: {"agentName":"retriever","status":"completed","intermediateResult":"找到10篇论文","durationMs":1200,"analysisId":"anl_001"}

event: analysis_completed
data: {"analysisId":"anl_001","status":"completed"}
```

---

> **文档维护**：架构变更时需更新本文档，重大变更需记录修订历史  
> **变更控制**：模块间接口变更需项目组讨论确认  
> **下一步**：依据本文档开始Python AI服务开发，按F3.5→F5.2/F4.3→F3.3→F3.2→F3.4→F3.1顺序实现
