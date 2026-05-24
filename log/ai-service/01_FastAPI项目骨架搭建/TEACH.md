# 技术教学文档

## 开发思路

### 需求分析过程
本次任务的目标是为 Python AI 服务创建 FastAPI 项目骨架。需求来源于 `task04_python_fastapi_skeleton.json`，核心要求包括：
1. 完整目录结构（与架构文档 §3.1 一致）
2. 依赖管理（requirements.txt 锁定版本号）
3. 应用入口（lifespan 生命周期 + /health + 异常处理器 + 路由注册）
4. 路由聚合（3 个子路由组：agent/search/model）
5. 占位文件（core/config、events、logging）

### 技术选型考虑
- **FastAPI**：选择 FastAPI 而非 Flask，因为原生支持 async/await、Pydantic 数据校验、自动 OpenAPI 文档
- **lifespan**：使用 FastAPI 的 `lifespan` 异步上下文管理器，替代已废弃的 `on_event("startup")/on_event("shutdown")`
- **Loguru**：替代标准库 logging，配置更简洁，支持文件轮转和压缩
- **pydantic-settings**：统一管理环境变量，支持 `.env` 文件自动加载

### 架构设计思路
采用 **三层分离架构**（ADR-001）：
```
Router（路由层）→ Service（服务层）→ Agent（Agent层）
```
路由层只负责请求分发和响应格式化，业务逻辑放在 Service 层，Agent 编排放在 Agent 层。

路由聚合采用 **嵌套 APIRouter** 模式：
```
main.py → include_router(api_router, prefix="/api")
router.py → include_router(agent_router, prefix="/agent")
router.py → include_router(search_router, prefix="/search")
router.py → include_router(model_router, prefix="/model")
```
最终路由路径：`/api/agent/analyze`、`/api/search/`、`/api/model/status`

### 遇到的问题及解决方案

#### 问题1：Python 3.13 与 pydantic 2.7.0 不兼容
- **现象**：`pip install pydantic==2.7.0` 在 Python 3.13 上编译 pydantic-core 失败
- **原因**：pydantic 2.7.0 的 pydantic-core 没有针对 Python 3.13 的预编译 wheel，且 maturin 构建失败
- **解决方案**：升级到 `pydantic==2.9.0`（有 Python 3.13 的预编译 wheel），同时升级 fastapi、uvicorn 等相关依赖到兼容版本
- **注意**：Docker 部署使用 Python 3.10 时可恢复原始版本号

#### 问题2：pydantic v2 的 `model_` 命名空间冲突
- **现象**：`Settings` 类中 `model_path` 字段触发 `UserWarning: Field "model_path" in Settings has conflict with protected namespace "model_"`
- **原因**：pydantic v2 将 `model_` 前缀保留为内部方法命名空间
- **解决方案**：在 `model_config` 中设置 `protected_namespaces=("settings_",)` 将保护前缀改为 `settings_`

#### 问题3：已有文件与新建文件冲突
- **现象**：项目中已存在 `app/exception.py`、`app/models/schemas.py`、`app/models/enums.py` 等文件，且 `main.py`、`events.py`、`logging.py` 已被之前的任务更新为更完整的版本
- **解决方案**：识别已有文件，确保 `config.py` 中的配置字段与 `events.py`、`main.py` 的引用保持一致

## 实现步骤

1. **创建目录结构**：使用 `mkdir -p` 批量创建所有子目录，然后创建 9 个 `__init__.py` 和 4 个 `.gitkeep`
2. **创建 requirements.txt**：按功能分组（Web Framework / AI/ML / Vector Database / LLM API / Data Processing / PDF Processing / arXiv / Utilities / Testing），锁定版本号
3. **创建 app/main.py**：实现 lifespan 异步上下文管理器、/health 健康检查、RequestValidationError 和通用 Exception 处理器、路由注册
4. **创建 app/api/router.py**：APIRouter 嵌套聚合 3 个子路由
5. **创建 3 个 endpoint 占位文件**：agent.py、search.py、model.py
6. **创建 core 占位文件**：config.py（Settings 类）、events.py（on_startup/on_shutdown）、logging.py（configure_logging）
7. **创建 .gitignore**：Python 项目标准忽略规则
8. **验证**：创建虚拟环境、安装核心依赖、import 测试、uvicorn 启动测试、/health 端点测试

## 解决了什么问题

### 核心问题描述
Python AI 服务层缺少项目骨架，无法启动和运行，后续的 Agent 开发、RAG 检索等功能无法在此基础上迭代。

### 解决方案对比
| 方案 | 优点 | 缺点 |
|------|------|------|
| 单文件 main.py | 简单快速 | 无法扩展，不符合分层架构 |
| 按功能分目录（当前方案） | 结构清晰，符合架构文档，易于扩展 | 初始文件较多 |
| 使用 FastAPI 脚手架工具 | 自动生成 | 生成结构与项目规范不一致 |

### 最终方案的优势
- 目录结构与架构文档 §3.1 完全一致，团队协作无歧义
- 三层分离架构（Router → Service → Agent）确保关注点分离
- lifespan 生命周期管理为后续模型加载/释放预留了标准入口
- 统一异常处理格式确保前后端对接一致

## 变更内容

### 新增文件
- `Veritas/ai-service/requirements.txt` — Python 依赖管理，22 个包按功能分组
- `Veritas/ai-service/.gitignore` — Python 项目忽略规则
- `Veritas/ai-service/app/main.py` — FastAPI 应用入口
- `Veritas/ai-service/app/api/router.py` — 路由聚合器
- `Veritas/ai-service/app/api/endpoints/agent.py` — Agent 分析接口占位
- `Veritas/ai-service/app/api/endpoints/search.py` — 检索接口占位
- `Veritas/ai-service/app/api/endpoints/model.py` — 模型状态接口占位
- `Veritas/ai-service/app/core/config.py` — Pydantic Settings 配置
- `Veritas/ai-service/app/core/events.py` — 启动/关闭事件
- `Veritas/ai-service/app/core/logging.py` — Loguru 日志配置
- 9 个 `__init__.py` 包初始化文件
- 4 个 `.gitkeep` 目录占位文件

### 修改文件
- `Veritas/ai-service/app/core/config.py` — 从简单占位升级为完整 Settings 类（添加 LOG_LEVEL、AGENT_TIMEOUT、AGENT_FULL_TIMEOUT 等字段），修复 pydantic v2 命名空间冲突

### 配置变更
- 新增环境变量支持：`APP_NAME`、`DEBUG`、`LOG_LEVEL`、`LLM_MODE`、`LLM_BUILTIN_URL`、`LLM_API_KEY`、`LLM_API_BASE`、`LLM_MODEL_NAME`、`CHROMA_PATH`、`EMBEDDING_MODEL_PATH`、`EMBEDDING_DEVICE`、`AGENT_TIMEOUT`、`AGENT_FULL_TIMEOUT`

## 关键技术点

### FastAPI lifespan 生命周期管理
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动阶段：加载模型、初始化连接
    logger.info("Starting AI Service...")
    yield
    # 关闭阶段：释放资源
    logger.info("Shutting down AI Service...")
```
这是 FastAPI 推荐的生命周期管理方式，替代了已废弃的 `@app.on_event("startup")`。yield 前后分别对应启动和关闭阶段。

### APIRouter 嵌套聚合
```python
# router.py
api_router = APIRouter()
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(model.router, prefix="/model", tags=["model"])

# main.py
app.include_router(api_router, prefix="/api")
```
这种嵌套模式使得每个 endpoint 模块独立定义自己的路由，通过 router.py 统一聚合，最终在 main.py 中注册。新增 endpoint 只需创建文件并在 router.py 中添加一行即可。

### pydantic-settings 配置管理
```python
class Settings(BaseSettings):
    LLM_MODE: str = "auto"
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        protected_namespaces=("settings_",),
    )
```
- 所有配置字段使用 `UPPER_SNAKE_CASE`（环境变量风格）
- `env_file=".env"` 自动从 `.env` 文件加载
- `protected_namespaces=("settings_",)` 解决 `model_` 前缀冲突

### 统一异常响应格式
```python
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(status_code=422, content={
        "code": 422,
        "message": str(exc),
        "data": None,
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
    })
```
确保所有错误响应遵循 `{code, message, data, timestamp}` 统一格式，与 Java 后端和前端约定一致。

## 经验总结

### 开发过程中的收获
1. **先读已有代码再创建**：项目中已有 `exception.py`、`schemas.py`、`enums.py` 等文件，且 `main.py` 已被之前的任务更新。创建新文件前必须先检查已有内容，避免覆盖或冲突
2. **Python 版本兼容性**：本机 Python 3.13 与部分旧版本依赖不兼容，需要升级版本号。Docker 部署环境（Python 3.10）可以使用原始版本
3. **pydantic v2 重大变更**：`model_` 前缀被保护、`on_event` 被废弃等，需要关注迁移指南

### 踩过的坑及如何避免
1. **zsh 方括号转义**：`pip install "uvicorn[standard]==0.29.0"` 在 zsh 中需要用引号包裹，否则方括号被解释为 glob 模式
2. **pydantic 命名空间冲突**：字段名以 `model_` 开头会触发警告，需在 ConfigDict 中调整 `protected_namespaces`
3. **虚拟环境位置**：`.venv` 在 `.gitignore` 中，不应被 Git 追踪

### 最佳实践建议
1. **依赖版本锁定**：requirements.txt 必须指定精确版本号（`==`），避免 `>=` 导致的不可控升级
2. **按功能分组注释**：requirements.txt 中用注释分组，便于维护和理解依赖用途
3. **lifespan 替代 on_event**：FastAPI 官方推荐使用 lifespan，on_event 已标记为废弃
4. **占位端点先创建**：即使功能未实现，也先创建占位端点，确保路由注册和 API 文档完整
5. **配置字段大写**：pydantic-settings 中配置字段使用 `UPPER_SNAKE_CASE`，与 `.env` 文件中的环境变量命名一致
