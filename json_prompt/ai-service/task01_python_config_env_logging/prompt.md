# Task01 — Python 核心配置、环境变量与日志

| 项目 | 内容 |
|------|------|
| **项目** | XH-202630 科研文献智能助手 |
| **版本** | v0.1 |
| **里程碑** | M1：基础设施就绪 / AM1：项目骨架与模型层就绪 |

## 需求描述

实现 Python AI 服务的核心配置模块：

1. **config.py** — 基于 pydantic-settings 的 BaseSettings 配置类，从 `.env` 环境变量读取所有配置项（应用配置、ChromaDB 配置、Embedding 配置、LLM 三路配置、Agent 配置、日志配置），所有配置项有合理默认值，创建全局 settings 单例
2. **.env.example** — 环境变量示例文件，包含所有配置项及中文注释说明，敏感值留空
3. **core/logging.py** — 基于 Loguru 的日志配置，支持控制台彩色输出 + 文件轮转输出，格式含时间/级别/模块:函数:行号/消息，文件日志按天轮转保留 7 天并压缩
4. **core/events.py** — FastAPI 启动/关闭事件处理函数，在 lifespan 中调用，启动时初始化日志、关闭时清理资源

## 涉及层级

- `python_ai_service`

## 功能编号

- F3.5 / F3.3 / F5.2 / F4.3

## 需要修改/新增的文件

| 操作 | 路径 | 说明 |
|------|------|------|
| modify | `Veritas/ai-service/app/core/config.py` | 替换占位文件，实现完整 Settings 类和全局 settings 单例 |
| modify | `Veritas/ai-service/app/core/logging.py` | 替换占位文件，实现 Loguru 日志配置 |
| modify | `Veritas/ai-service/app/core/events.py` | 替换占位文件，实现启动/关闭事件处理函数 |
| modify | `Veritas/ai-service/app/main.py` | 修改 lifespan 函数，集成 events.py 的 on_startup/on_shutdown |
| create | `Veritas/ai-service/.env.example` | 环境变量示例文件，包含所有配置项及中文注释 |

## 功能要求

| ID | 优先级 | 描述 |
|----|--------|------|
| FR-001 | P0 | config.py 创建 Settings 类继承 BaseSettings，包含 6 组配置：**应用配置**（APP_NAME/DEBUG/HOST/PORT）、**ChromaDB 配置**（CHROMA_PATH）、**Embedding 配置**（EMBEDDING_MODEL_PATH/DEVICE/API_KEY/API_BASE/API_MODEL）、**LLM 配置**（LLM_MODE/BUILTIN_URL/BUILTIN_API_KEY/BUILTIN_MODEL/API_KEY/API_BASE/MODEL_NAME/LOCAL_MODEL_PATH/TIMEOUT/RETRY_COUNT/RETRY_INTERVAL）、**Agent 配置**（AGENT_TIMEOUT/AGENT_FULL_TIMEOUT/AGENT_MAX_REGENERATE）、**日志配置**（LOG_LEVEL）。内部类 Config 设置 `env_file='.env', env_file_encoding='utf-8'` |
| FR-002 | P0 | config.py 创建全局 settings 单例：`settings = Settings()`，其他模块通过 `from app.core.config import settings` 使用 |
| FR-003 | P0 | .env.example 包含所有配置项，按功能分组并添加中文注释。敏感值（API Key 等）留空，非敏感值提供默认值。LLM 三路配置需注释说明优先级：方案 A(软件方) → 方案 B(外接 API) → 方案 C(本地模型) |
| FR-004 | P0 | logging.py 实现 setup_logging 函数：1) `logger.remove()` 移除默认 handler；2) `logger.add(sys.stdout, level=level, format='{time:YYYY-MM-DD HH:mm:ss} \| {level:<8} \| {name}:{function}:{line} \| {message}', colorize=True)`；3) `logger.add('logs/ai-service-{time:YYYY-MM-DD}.log', level='DEBUG', rotation='00:00', retention='7 days', compression='zip')`。确保 logs/ 目录在日志写入前自动创建 |
| FR-005 | P0 | events.py 实现 on_startup 和 on_shutdown 异步函数：on_startup 调用 `setup_logging(settings.LOG_LEVEL)`，然后 logger.info 记录关键配置信息（LLM_MODE、EMBEDDING_MODEL_PATH、CHROMA_PATH 等，**禁止记录 API Key 等敏感值**）；on_shutdown 记录关闭日志 |
| FR-006 | P0 | 修改 main.py 的 lifespan 函数，集成 events.py：yield 前调用 `await on_startup()`，yield 后调用 `await on_shutdown()`。移除原有的占位 logger.info 语句 |
| FR-007 | P1 | /health 接口使用 settings 中的配置信息，返回占位值（后续任务替换为实际组件状态） |

### LLM 三路降级配置

| 优先级 | Provider | 说明 |
|--------|----------|------|
| 1 | BuiltinLLMProvider | 软件方模型，开箱即用，最高优先级 |
| 2 | APILLMProvider | 外接 API，用户自配，中等优先级 |
| 3 | LocalLLMProvider | 本地模型，兜底方案，最低优先级 |

**降级触发条件**：连续 3 次调用失败 / 单次调用超时 30 秒 / HTTP 5xx 响应
**恢复策略**：每 5 分钟尝试恢复到更高级别 Provider

## 验收标准

| ID | 验收条件 | 验证方式 |
|----|---------|---------|
| AC-001 | Settings 类包含 6 组配置，所有字段有默认值 | 代码审查 |
| AC-002 | Settings 类 Config 内部类配置 `env_file='.env', env_file_encoding='utf-8'` | 代码审查 |
| AC-003 | 全局 settings 单例可正常 import，settings.LLM_MODE 返回 'auto' | 自动测试 |
| AC-004 | .env.example 包含所有配置项，按功能分组，有中文注释，敏感值留空 | 代码审查 |
| AC-005 | cp .env.example .env 后应用能正常启动 | 自动测试 |
| AC-006 | setup_logging 配置控制台彩色输出 + 文件轮转输出，格式含时间/级别/模块:函数:行号/消息 | 代码审查 |
| AC-007 | 日志文件按天轮转(rotation='00:00')，保留 7 天(retention='7 days')，压缩(compression='zip') | 代码审查 |
| AC-008 | logs/ 目录在首次日志写入前自动创建 | 自动测试 |
| AC-009 | on_startup 记录关键配置信息，不记录 API Key 等敏感值 | 代码审查 |
| AC-010 | main.py 的 lifespan 函数正确调用 on_startup/on_shutdown | 代码审查 |
| AC-011 | 代码中无硬编码敏感信息，日志中无敏感信息输出 | 代码审查 |

## 验证命令

```bash
# 1. 验证 Settings 加载
cd Veritas/ai-service && python -c "from app.core.config import settings; print(f'LLM_MODE={settings.LLM_MODE}, CHROMA_PATH={settings.CHROMA_PATH}')"
# 预期: LLM_MODE=auto, CHROMA_PATH=./data/vector_db

# 2. 验证日志配置
cd Veritas/ai-service && python -c "from app.core.logging import setup_logging; setup_logging('DEBUG'); from loguru import logger; logger.info('Test log')"
# 预期: 控制台输出日志，logs/ 目录下生成日志文件

# 3. 验证 .env.example 可用
cd Veritas/ai-service && cp .env.example .env && python -c "from app.core.config import settings; assert settings.LLM_MODE == 'auto'"
# 预期: 无断言错误

# 4. 启动服务测试
cd Veritas/ai-service && uvicorn app.main:app --host 0.0.0.0 --port 8000 & sleep 3 && curl http://localhost:8000/health
# 预期: 返回 JSON 含 status:'UP' 和配置信息
```
