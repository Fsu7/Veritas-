# 核心配置与日志基础设施

## 功能描述
- **解决的问题**：为 Python AI 服务建立统一的配置管理、日志输出和应用生命周期管理基础设施，使后续所有模块（Agent、LLM、RAG等）能够通过统一的 `settings` 单例获取配置，通过 Loguru 输出结构化日志
- **实现的功能**：
  1. 基于 pydantic-settings 的 `Settings` 配置类，从 `.env` 文件读取所有配置项
  2. 基于 Loguru 的双通道日志（控制台彩色 + 文件轮转压缩）
  3. FastAPI 启动/关闭生命周期事件处理
  4. 环境变量示例文件 `.env.example`（中文注释 + 分组）
  5. `/health` 健康检查端点（占位状态）
- **业务价值**：为 AM1 里程碑（项目骨架与模型层就绪）提供配置和日志基础，是后续所有模块的前提依赖

## 实现逻辑

### 修改/创建的核心文件
| 文件 | 操作 | 核心职责 |
|------|------|---------|
| `app/core/config.py` | 创建 | `Settings(BaseSettings)` + 全局 `settings` 单例 |
| `app/core/logging.py` | 创建 | `setup_logging()` — Loguru 双通道配置 |
| `app/core/events.py` | 创建 | `on_startup()` / `on_shutdown()` 生命周期事件 |
| `app/main.py` | 修改 | 集成 settings、events，保留已有 router/exception |
| `.env.example` | 创建 | 6组配置 + 中文注释 + LLM 三路方案 |

### 配置架构
```
.env / .env.example → Settings(BaseSettings) → settings 单例
                                                      ↓
  on_startup() → setup_logging() ←┐                main.py
       ↓                          │                   ↓
  记录非敏感配置                 Loguru             /health
       ↓                     ┌────┴────┐
  on_shutdown()          stdout(彩色)  文件(轮转+压缩)
```

### 配置字段（6组，25个字段）
| 组 | 关键字段 | 说明 |
|----|---------|------|
| 应用 | APP_NAME, DEBUG, HOST, PORT | FastAPI 运行参数 |
| ChromaDB | CHROMA_PATH | 向量数据库路径 |
| Embedding | EMBEDDING_MODEL_PATH, EMBEDDING_DEVICE, EMBEDDING_API_* | 嵌入模型配置 |
| LLM（三路） | LLM_MODE, LLM_BUILTIN_*, LLM_API_*, LLM_LOCAL_*, LLM_TIMEOUT/RETRY | 大模型配置+降级 |
| Agent | AGENT_TIMEOUT, AGENT_FULL_TIMEOUT, AGENT_MAX_REGENERATE | Agent 超时控制 |
| 日志 | LOG_LEVEL | 日志级别 |

### 日志格式
```
{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name}:{function}:{line} | {message}
```
- 控制台：按 `LOG_LEVEL` 级别，彩色输出
- 文件：DEBUG 级别，`logs/ai-service-{date}.log`，每天 00:00 轮转，保留 7 天，zip 压缩

## 接口变更

### /health
```
GET /health
```
```json
{
    "status": "UP",
    "timestamp": "2026-05-24T03:41:26.253186+00:00",
    "llm": "not_loaded",
    "embedding": "not_loaded",
    "chroma": "not_connected"
}
```

### 配置导入方式
```python
from app.core.config import settings
# settings.LLM_MODE → 'auto'
# settings.CHROMA_PATH → './data/vector_db'
```

## 测试结果
| 测试场景 | 命令 | 结果 |
|---------|------|------|
| 配置默认值加载 | `python -c "from app.core.config import settings; print(settings.LLM_MODE)"` | ✅ `auto` |
| .env 文件加载 | `cp .env.example .env && assert settings.LLM_MODE == 'auto'` | ✅ 通过 |
| 日志控制台输出 | `setup_logging('DEBUG'); logger.info('Test')` | ✅ 彩色输出正确 |
| 日志文件生成 | 同上 | ✅ `logs/ai-service-2026-05-24.log` 已生成 |
| /health 端点 | `curl localhost:8001/health` | ✅ JSON 响应正确 |
| 日志敏感信息 | 审查 `logs/ai-service-*.log` | ✅ 无 API Key 等敏感信息 |

**全部测试通过** ✅

## 相关文件
- `Veritas/ai-service/app/core/config.py`
- `Veritas/ai-service/app/core/logging.py`
- `Veritas/ai-service/app/core/events.py`
- `Veritas/ai-service/app/main.py`
- `Veritas/ai-service/.env.example`
- `Veritas/ai-service/.gitignore`（已包含 `.env`、`logs/`）