# 技术教学文档 — 核心配置与日志基础设施

## 开发思路

### 需求分析过程
本任务是 AM1（项目骨架与模型层就绪）的关键子任务，对应需求编号 F3.5/F3.3/F5.2/F4.3。核心诉求是在 Python AI 服务中建立"开箱即用"的配置和日志基础设施——即使用户不提供 `.env` 文件，应用也能以合理的默认值启动。

### 技术选型考虑

| 技术项 | 候选方案 | 最终选择 | 理由 |
|--------|---------|---------|------|
| 配置管理 | os.environ / python-dotenv / pydantic-settings | **pydantic-settings** | 类型安全 + 环境变量自动映射 + 默认值 + .env 文件支持 |
| 日志框架 | logging / structlog / Loguru | **Loguru** | 零配置开箱即用 + 彩色输出 + 文件轮转原生支持 |
| 环境变量格式 | camelCase / UPPER_SNAKE_CASE | **UPPER_SNAKE_CASE** | Docker/Shell 生态标准，pydantic-settings 原生支持 |

### 架构设计思路
采用"配置中心 + 日志门面 + 生命周期钩子"的三层模式：

```
配置层(config.py) → 日志层(logging.py) → 生命周期层(events.py) → 应用层(main.py)
```

- **配置层**：单一 Settings 类承载所有配置，全局单例避免重复读取 .env
- **日志层**：封装 Loguru 配置，通过 setup_logging() 统一初始化，控制台/文件分离
- **生命周期层**：FastAPI lifespan 事件中调用，启动时初始化日志+记录配置，关闭时清理
- **应用层**：main.py 仅做组装，不包含业务逻辑

### 遇到的问题及解决方案

#### 问题1：pydantic-settings v2 字段名大小写
- **现象**：在 Python 3.13 + pydantic-settings 2.14 环境下，`UPPER_SNAKE_CASE` 字段名可正常访问 `settings.LLM_MODE`
- **排查**：旧版本 pydantic-settings 会将字段转为小写，但 v2.14+ 已修复
- **解决**：使用 `model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")` 替代旧版 `class Config`

#### 问题2：venv 环境 pip 未安装
- **现象**：`python3 -m venv .venv` 创建的虚拟环境缺少 pip 和 uvicorn
- **解决**：删除旧 .venv 后重新 `python3 -m venv .venv && .venv/bin/pip install ...`

#### 问题3：`.pyc` 缓存导致代码变更不生效
- **现象**：修改 config.py 后，`from app.core.config import Settings` 仍返回旧字段
- **原因**：`__pycache__` 中有之前版本的编译缓存
- **解决**：每次测试前 `find . -name "__pycache__" -type d -exec rm -rf {} +`

#### 问题4：main.py 需兼容已有模块
- **现象**：其他并行任务已创建 `app/api/router.py`、`app/exception.py`、`app/api/endpoints/`
- **解决**：main.py 保留 `api_router`、异常处理器等已有功能，仅集成 settings 和 events

## 实现步骤

### 第一步：创建 Settings 配置类
在 `app/core/config.py` 中定义 `Settings(BaseSettings)`，包含全部 25 个配置字段，每个字段提供合理默认值。敏感字段（API Key 类）默认值为空字符串。使用 `SettingsConfigDict` 指定 `.env` 文件路径。

**关键点**：
- 使用 `pydantic-settings` 的 `BaseSettings`（非 `pydantic.BaseModel`）
- 字段名保持 `UPPER_SNAKE_CASE`（如 `LLM_MODE`），与环境变量名一致
- 创建模块级 `settings = Settings()` 单例

### 第二步：实现 Loguru 日志配置
在 `app/core/logging.py` 中实现 `setup_logging(level)` 函数：
1. `logger.remove()` 移除默认 handler
2. `logger.add(sys.stdout, ...)` 添加控制台输出（彩色，按传入 level）
3. `os.makedirs("logs", exist_ok=True)` 确保目录存在
4. `logger.add("logs/...", ...)` 添加文件输出（DEBUG 级别，轮转+压缩）

**关键点**：`os.makedirs` 必须在 `logger.add` 之前调用，否则日志文件写入会失败。

### 第三步：实现生命周期事件
在 `app/core/events.py` 中：
- `on_startup()`：调用 `setup_logging(settings.LOG_LEVEL)` → 用 `logger.info` 记录非敏感配置
- `on_shutdown()`：`logger.info("AI Service shut down")`

**关键点**：只记录 `LLM_MODE`、`CHROMA_PATH`、`EMBEDDING_MODEL_PATH` 等配置，**禁止**记录 `LLM_API_KEY` 等敏感值。

### 第四步：集成到 FastAPI 应用
修改 `app/main.py`：
1. 导入 `settings`、`on_startup`、`on_shutdown`
2. 在 `lifespan` 中 `yield` 前后调用
3. FastAPI 实例使用 `settings.APP_NAME` 作为 title
4. `/health` 端点返回占位状态

### 第五步：创建 .env.example
按 6 组分类，添加中文注释说明，LLM 部分注释三路方案优先级。敏感值用 `# 注解=` 格式注释掉并留空。

## 解决了什么问题

### 核心问题
Python AI 服务需要一个统一的、类型安全的配置管理方案，避免在代码中硬编码配置值，同时支持用户通过环境变量覆盖默认值。

### 解决方案对比
| 方案 | 类型安全 | .env支持 | 默认值 | 全局单例 | 结论 |
|------|---------|---------|--------|---------|------|
| `os.getenv()` | ❌ | ❌ | 需手动 | ❌ | 过于原始 |
| `python-dotenv` + dataclass | ⚠️ | ✅ | ✅ | ⚠️ | 可用但不优雅 |
| **pydantic-settings** | ✅ | ✅ | ✅ | ✅ | **最佳实践** |

### 最终方案的优势
1. **零配置启动**：无 `.env` 文件时全部使用默认值
2. **类型安全**：编译器/IDE 可自动补全和类型检查
3. **安全设计**：敏感字段默认空值，日志不输出 API Key
4. **可扩展**：后续模块只需 `from app.core.config import settings`

## 变更内容

### 新增文件
| 文件 | 作用 |
|------|------|
| `app/core/config.py` | `Settings` 配置类 + `settings` 单例 |
| `app/core/logging.py` | `setup_logging()` 日志初始化 |
| `app/core/events.py` | `on_startup()` / `on_shutdown()` 生命周期 |
| `.env.example` | 环境变量模板 |

### 修改文件
| 文件 | 变更点 |
|------|--------|
| `app/main.py` | 导入 `settings` 替代硬编码标题；导入 `on_startup/on_shutdown` 替代占位日志；`/health` 使用 UTC 时间 |

### 配置变更
- `.env.example` 已提交（不含敏感值）
- `.env` 已在 `.gitignore` 中排除
- `logs/` 已在 `.gitignore` 中排除

## 关键技术点

### 1. pydantic-settings v2 的 SettingsConfigDict
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )
```
**注意**：v2 使用 `model_config` 而非内部 `class Config`。

### 2. Loguru 日志轮转配置
```python
logger.add(
    "logs/ai-service-{time:YYYY-MM-DD}.log",
    rotation="00:00",      # 每天午夜轮转
    retention="7 days",    # 保留7天
    compression="zip",     # 旧日志压缩为zip
)
```
`{time:YYYY-MM-DD}` 使文件名包含日期，`rotation="00:00"` 在每天 00:00 创建新文件。

### 3. FastAPI lifespan 异步上下文管理器
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await on_startup()   # yield 前 = 启动阶段
    yield                # 应用运行中
    await on_shutdown()  # yield 后 = 关闭阶段

app = FastAPI(lifespan=lifespan)
```

### 4. on_startup 中的安全日志策略
只记录非敏感配置（LLM_MODE、CHROMA_PATH、DEBUG 等），明确排除 API Key。日志文件也不包含敏感信息——这是一条防线。

## 经验总结

### 开发过程中的收获
1. **pydantic-settings 是 Python 配置管理的事实标准**，比手动 os.getenv 更安全、更优雅
2. **Loguru 比 logging 方便太多**，轮转、压缩、彩色输出都是开箱即用
3. **FastAPI lifespan 替代了旧版 on_event 装饰器**，更符合 Python 异步编程习惯

### 踩过的坑及如何避免
1. **`__pycache__` 缓存问题**：修改代码后不生效，先清缓存再测试
2. **虚拟环境创建**：确保 `python3 -m venv` 创建的环境包含 pip，必要时使用 `ensurepip`
3. **并行任务冲突**：main.py 被其他任务同时修改，需关注文件内容是否被覆盖
4. **端口冲突**：8000 端口可能已被占用，测试时使用 8001 等备用端口

### 最佳实践建议
1. **配置字段默认值要能支撑"零配置启动"**：用户 clone 项目后应能直接运行
2. **敏感字段默认值为空字符串**：强制用户通过 .env 配置，避免误提交
3. **日志目录在代码中自动创建**：不依赖部署脚本
4. **归档时编写 TEACH.md**：记录技术决策和踩坑经验，加速后续开发者上手