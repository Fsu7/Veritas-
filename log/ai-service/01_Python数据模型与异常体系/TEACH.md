# 技术教学文档 — Python数据模型与异常体系

## 开发思路

### 需求分析过程

1. **任务来源**：执行 `task06_python_schemas_enums_exception.json` 任务，实现Python AI服务的数据模型与异常体系
2. **核心需求**：
   - 定义与Java后端API契约一致的Pydantic模型
   - 创建业务枚举类并确保JSON序列化正确
   - 建立统一异常体系和全局异常处理器
3. **关键约束**：
   - 字段名使用camelCase与Java后端一致
   - 枚举必须继承(str, Enum)确保序列化为字符串
   - 异常消息禁止包含敏感信息

### 技术选型考虑

| 技术点 | 选型 | 原因 |
|-------|------|------|
| 数据验证 | Pydantic v2 | FastAPI原生支持，类型安全，Field校验丰富 |
| 枚举基类 | (str, Enum) | 确保JSON序列化为字符串值而非对象 |
| 配置管理 | pydantic-settings | 自动从.env加载，类型安全 |
| 日志框架 | Loguru | 开箱即用，支持轮转压缩 |
| 异常设计 | 继承体系 | 基础异常 + 业务子类，便于扩展和统一处理 |

### 架构设计思路

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Application                     │
├─────────────────────────────────────────────────────────────┤
│  Global Exception Handlers                                   │
│  ├── AIServiceException → {code, message, data, timestamp}  │
│  └── RequestValidationError → 422 + 统一格式                 │
├─────────────────────────────────────────────────────────────┤
│  Pydantic Models (schemas.py)                                │
│  ├── UserProfile (4维度画像)                                  │
│  ├── AnalyzeRequest (Agent分析请求)                          │
│  ├── SearchRequest (检索请求)                                │
│  └── UnifiedResponse (统一响应包装)                           │
├─────────────────────────────────────────────────────────────┤
│  Enums (enums.py)                                            │
│  ├── EducationLevel / KnowledgeLevel / PreferredStyle        │
│  ├── AnalysisType / AgentName / AgentStatus / LLMMode        │
├─────────────────────────────────────────────────────────────┤
│  Exception Hierarchy (exception.py)                          │
│  ├── AIServiceException (基础异常)                            │
│  │   ├── LLMException (503)                                  │
│  │   ├── VectorStoreException (503)                          │
│  │   ├── AgentTimeoutException (408)                         │
│  │   └── ModelNotLoadedException (503)                       │
└─────────────────────────────────────────────────────────────┘
```

### 遇到的问题及解决方案

| 问题 | 解决方案 |
|------|---------|
| ai-service目录不存在 | 创建完整目录结构（Task04/Task05前置文件） |
| 枚举JSON序列化为对象 | 继承(str, Enum)确保序列化为字符串值 |
| 字段名与Java契约不一致 | 使用camelCase字段名 + ConfigDict(populate_by_name=True) |
| 异常子类需要默认HTTP状态码 | 子类__init__中设置默认code参数 |

## 实现步骤

### 1. 创建目录结构与前置文件

```bash
mkdir -p Veritas/ai-service/app/{api/endpoints,core,agents,services,models,utils}
mkdir -p Veritas/ai-service/{prompts,data/{papers,vector_db},tests,scripts,logs}
```

创建前置文件：
- `requirements.txt` — Python依赖（FastAPI/Uvicorn/Pydantic/Loguru等）
- `.env.example` — 环境变量示例
- `.gitignore` — Python项目gitignore
- 各目录的`__init__.py`

### 2. 创建核心配置模块

- `app/core/config.py` — Settings配置类 + 全局settings单例
- `app/core/logging.py` — Loguru日志配置（控制台+文件轮转）
- `app/core/events.py` — 启动/关闭事件处理

### 3. 创建枚举定义（enums.py）

```python
from enum import Enum

class EducationLevel(str, Enum):
    UNDERGRADUATE = "undergraduate"
    MASTER = "master"
    PHD = "phd"
    FACULTY = "faculty"
```

**关键点**：继承`(str, Enum)`确保：
- `json.dumps(EducationLevel.MASTER)` → `"master"`（字符串值）
- `EducationLevel.MASTER == "master"` → `True`（可直接比较）

### 4. 创建Pydantic模型（schemas.py）

```python
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Any
from datetime import datetime

class UserProfile(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    educationLevel: EducationLevel = Field(..., description="学历层次")
    researchField: str = Field(..., min_length=1, max_length=100)
    knowledgeLevel: KnowledgeLevel = Field(..., description="知识水平")
    preferredStyle: PreferredStyle = Field(..., description="偏好风格")
```

**关键点**：
- 字段名使用camelCase（如`educationLevel`）
- `ConfigDict(populate_by_name=True)`支持两种命名方式
- `Field(...)`定义校验规则

### 5. 创建统一异常体系（exception.py）

```python
class AIServiceException(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)

class LLMException(AIServiceException):
    def __init__(self, message: str, code: int = 503):
        super().__init__(code=code, message=message)
```

**关键点**：
- 子类有默认HTTP状态码（LLM=503, Timeout=408）
- code参数可覆盖

### 6. 修改main.py添加全局异常处理器

```python
from app.exception import AIServiceException

@app.exception_handler(AIServiceException)
async def ai_service_exception_handler(request: Request, exc: AIServiceException):
    return JSONResponse(
        status_code=exc.code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": None,
            "timestamp": int(datetime.now().timestamp() * 1000),
        },
    )
```

### 7. 更新models/__init__.py导出

```python
from app.models.enums import EducationLevel, KnowledgeLevel, ...
from app.models.schemas import UserProfile, AnalyzeRequest, ...

__all__ = ["EducationLevel", "KnowledgeLevel", ...]
```

## 解决了什么问题

### 核心问题描述

1. **跨系统字段命名不一致**：Java后端使用camelCase，Python默认使用snake_case
2. **枚举序列化问题**：普通Enum序列化为对象`{"value": "master"}`而非字符串`"master"`
3. **异常处理分散**：各模块异常格式不统一，前端难以处理
4. **HTTP状态码不明确**：业务异常缺少默认HTTP状态码

### 解决方案对比

| 方案 | 优点 | 缺点 | 最终选择 |
|------|------|------|---------|
| Pydantic alias | 支持字段别名 | 需要每个字段单独设置 | ❌ |
| ConfigDict(populate_by_name) | 全局支持两种命名 | Pydantic v2特性 | ✅ |
| 枚举继承str | 简单直接 | 无 | ✅ |
| 异常继承体系 | 统一处理，可扩展 | 需要设计好层次 | ✅ |

### 最终方案的优势

1. **API契约一致性**：字段名与Java后端完全一致
2. **类型安全**：Pydantic自动校验，减少运行时错误
3. **统一响应格式**：所有异常返回`{code, message, data, timestamp}`
4. **可扩展性**：异常继承体系便于后续添加新异常类型

## 变更内容

### 新增文件

| 文件 | 作用 |
|------|------|
| `app/models/enums.py` | 7个业务枚举定义 |
| `app/models/schemas.py` | 9个Pydantic请求/响应模型 |
| `app/exception.py` | 统一异常体系 |
| `app/core/config.py` | Settings配置类 |
| `app/core/logging.py` | Loguru日志配置 |
| `app/core/events.py` | 启动/关闭事件 |
| `app/api/router.py` | 路由聚合器 |
| `app/api/endpoints/*.py` | 3个endpoint占位文件 |
| `app/main.py` | FastAPI入口 |

### 修改文件

| 文件 | 变更点 |
|------|--------|
| `app/models/__init__.py` | 导出所有模型和枚举 |

### 配置变更

| 配置项 | 说明 |
|-------|------|
| `.env.example` | 环境变量示例（敏感值留空） |
| `requirements.txt` | Python依赖锁定版本 |

## 关键技术点

### 1. 枚举继承(str, Enum)的原理

```python
class EducationLevel(str, Enum):
    MASTER = "master"

# 继承str后：
# 1. json.dumps()调用str()方法，返回"master"
# 2. 可直接与字符串比较：EducationLevel.MASTER == "master" → True
```

### 2. Pydantic ConfigDict(populate_by_name=True)

```python
class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    educationLevel: EducationLevel  # camelCase字段名

# 支持两种方式创建：
AnalyzeRequest(educationLevel="master", ...)  # camelCase
AnalyzeRequest(education_level="master", ...)  # snake_case（自动映射）
```

### 3. 异常子类默认参数设计

```python
class LLMException(AIServiceException):
    def __init__(self, message: str, code: int = 503):
        # message在前，code有默认值
        # 调用方式：
        # raise LLMException("LLM call failed")  # code=503
        # raise LLMException("LLM call failed", code=500)  # code=500
```

### 4. 毫秒时间戳生成

```python
timestamp: int = Field(
    default_factory=lambda: int(datetime.now().timestamp() * 1000)
)
```

## 经验总结

### 开发过程中的收获

1. **Pydantic v2变化**：`class Config`改为`model_config = ConfigDict(...)`
2. **枚举序列化陷阱**：不继承str会导致JSON序列化为对象
3. **FastAPI异常处理器**：`@app.exception_handler()`注册，返回`JSONResponse`

### 踩过的坑及如何避免

| 坑 | 原因 | 避免方法 |
|---|------|---------|
| 枚举序列化为对象 | 未继承str | 所有枚举继承(str, Enum) |
| 字段名与Java不一致 | Python默认snake_case | 使用camelCase + populate_by_name |
| 异常HTTP状态码错误 | 未设置默认值 | 子类__init__设置默认code |

### 最佳实践建议

1. **枚举定义**：始终继承(str, Enum)，枚举值使用lower_case
2. **Pydantic模型**：所有字段添加Field()校验和description
3. **异常设计**：基础异常包含code/message，子类设置默认HTTP状态码
4. **全局处理器**：返回统一格式，timestamp使用毫秒时间戳
5. **敏感信息**：异常消息禁止包含API Key、密码等敏感信息

---

**开发日期**：2026-05-24
**任务编号**：Task06
**里程碑**：M1 基础设施就绪 / AM1 项目骨架与模型层就绪
