# 02 — 技术栈与环境配置

> 加载时机：配置开发环境、添加新依赖、了解项目目录结构时加载。
> 关联文件：[07-standards.md](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/agents/07-standards.md)

---

## 1 技术栈版本

| 层级 | 技术 | 版本 |
|------|------|------|
| 前端 | Vue3 + Composition API + `<script setup>` | 3.5+ |
| 前端 | TypeScript | 5.0+ |
| 前端 | Vite | 6.0+ |
| 前端 | Element Plus | 2.14+ |
| 前端 | ECharts | 5.6+ |
| 前端 | Pinia | 2.3+ |
| 前端 | Axios | 1.7+ |
| 后端 | Java | 17 |
| 后端 | Spring Boot | 3.2+ |
| 后端 | Spring Data JPA | — |
| 后端 | Spring Data Redis | — |
| 后端 | HikariCP | max=20 |
| AI服务 | Python | 3.10+ |
| AI服务 | FastAPI | 0.115+ |
| AI服务 | LangGraph | — |
| AI服务 | chromadb | 0.5+ |
| AI服务 | pydantic-settings | — |
| 数据库 | MySQL | 8.0 |
| 数据库 | Redis | 7.0 |
| 向量库 | ChromaDB | 0.5+ |
| 图数据库 | Neo4j | 5.x Community |
| LLM（当前生效） | **DeepSeek V4 Flash**（外接API方案B） | 284B/13B MoE · 1M 上下文 |
| LLM（备选） | 软件方模型 / OpenAI兼容接口（讯飞星火/通义千问等） / 本地Qwen2 | 三路自动降级 |
| Embedding | BAAI/bge-m3（本地备选） / text-embedding-v4（阿里云百炼） | 1024维 |
| 部署 | Docker Compose | — |

---

## 2 本机环境

| 服务 | 地址 | 用户/密码 |
|------|------|----------|
| 本机MySQL 9 | localhost:3306 | root / Aa2105268075. |
| Docker MySQL 8 | Docker内 | root / root123 |
| Docker Redis | localhost:6379 | 无密码（内网） |

---

## 3 关键环境变量

```bash
MYSQL_ROOT_PASSWORD=your_password
MYSQL_DATABASE=literature_assistant
REDIS_HOST=redis
REDIS_PORT=6379
JWT_SECRET=your_jwt_secret
AI_SERVICE_URL=http://ai-service:8000
LLM_MODE=api                     # auto|builtin|api|local
# 当前生效：DeepSeek V4 Flash（外接API方案B，OpenAI 兼容）
LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
LLM_API_BASE=https://api.deepseek.com/v1
LLM_MODEL_NAME=deepseek-v4-flash
# 备选：软件方模型
# LLM_BUILTIN_URL=https://llm.literature-assistant.com/v1
# 备选：本地模型
# LLM_LOCAL_MODEL_PATH=Qwen/Qwen2-7B-Instruct
# Embedding：阿里云百炼（text-embedding-v4，1024 维）
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v4
DASHSCOPE_EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
CHROMA_PATH=./data/vector_db
EMBEDDING_MODEL_NAME=BAAI/bge-m3
```

---

## 4 项目目录结构

```
Veritas(求真)/
├── docs/                                    # 项目文档
├── Veritas/
│   ├── backend/                             # Java后端
│   │   ├── src/main/java/com/literatureassistant/
│   │   │   ├── config/                      # 配置类
│   │   │   ├── controller/                  # API控制器
│   │   │   ├── service/                     # 业务逻辑
│   │   │   ├── repository/                  # 数据访问
│   │   │   ├── entity/                      # JPA实体
│   │   │   ├── dto/                         # 数据传输对象
│   │   │   │   ├── request/                 # 请求DTO
│   │   │   │   ├── response/                # 响应DTO
│   │   │   │   └── common/                  # 通用DTO
│   │   │   ├── client/                      # 外部服务客户端
│   │   │   ├── mapper/                      # MapStruct映射器
│   │   │   ├── filter/                      # 过滤器/拦截器
│   │   │   │   └── RequestIdFilter.java     # 请求ID过滤器（MDC注入）
│   │   │   ├── exception/                   # 异常定义
│   │   │   ├── enums/                       # 枚举定义
│   │   │   └── util/                        # 工具类
│   │   └── src/main/resources/application.yml
│   │   └── src/main/resources/application-prod.yml
│   │   └── src/test/resources/application-test.yml
│   ├── ai-service/                          # Python AI服务
│   │   ├── app/
│   │   │   ├── main.py                      # FastAPI入口
│   │   │   ├── api/router.py                # API路由
│   │   │   ├── core/config.py               # 配置
│   │   │   ├── agents/                      # Agent模块
│   │   │   │   ├── coordinator.py / retriever.py / analyzer.py
│   │   │   │   ├── comparer.py / generator.py / reviewer.py
│   │   │   │   └── graph.py                 # LangGraph工作流
│   │   │   ├── services/                    # 服务层
│   │   │   │   ├── llm_service.py / embedding_service.py
│   │   │   │   ├── vector_store_service.py / prompt_manager.py
│   │   │   │   └── personalization_service.py  # 计划中
│   │   │   └── models/schemas.py            # Pydantic数据模型
│   │   ├── prompts/                         # Prompt模板
│   │   └── requirements.txt
│   ├── frontend/                            # 前端
│   │   ├── src/
│   │   │   ├── views/                       # 页面组件
│   │   │   ├── components/                  # 可复用组件
│   │   │   ├── stores/                      # Pinia状态管理
│   │   │   ├── api/                         # API封装
│   │   │   ├── router/                      # 路由配置
│   │   │   ├── composables/                 # 组合式函数
│   │   │   ├── types/                       # TypeScript类型
│   │   │   └── utils/                       # 工具函数
│   │   └── vite.config.ts
│   ├── docker-compose.yml                   # Docker编排
│   ├── .env.example                         # 环境变量模板
│   └── nginx.conf                           # Nginx反向代理配置
└── AGENTS.md                                # 项目全景上下文
```

---

## 5 Docker部署

### 5.1 启动顺序

```
mysql → redis → ai-service → java-backend → frontend(Nginx)
```

### 5.2 服务配置

| 服务 | 镜像 | 端口 | 健康检查 |
|------|------|------|---------|
| MySQL | mysql:8.0 | 3306 | — |
| Redis | redis:7-alpine | 6379 | — |
| AI Service | python:3.10-slim | 8000 | /health |
| Java Backend | eclipse-temurin:17-jre-alpine | 8080 | /actuator/health |
| Frontend | nginx:alpine | 80 | — |

### 5.3 Nginx关键配置

- `/` → 静态文件（SPA路由 try_files）
- `/api/*` → proxy_pass java-backend:8080
- SSE支持: `proxy_buffering off; proxy_cache off; proxy_read_timeout 300s;`
