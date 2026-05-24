# Python AI服务数据模型与异常体系

## 功能描述

- **解决的问题**：为Python AI服务建立统一的数据模型规范和异常处理机制，确保与Java后端的API契约一致性
- **实现的功能**：
  - 7个业务枚举类（学历层次、知识水平、偏好风格、分析类型、Agent名称、Agent状态、LLM模式）
  - 9个Pydantic请求/响应模型（用户画像、分析请求、检索请求、Agent状态响应、分析响应、检索结果、检索响应、模型状态响应、统一响应包装）
  - 统一异常体系（1个基础异常 + 4个业务异常子类）
  - 全局异常处理器（AIServiceException处理器 + RequestValidationError处理器）
- **业务价值**：为后续Agent协同引擎、RAG检索、LLM服务等模块提供标准化的数据交互基础

## 实现逻辑

### 修改的核心文件列表

| 文件 | 说明 |
|------|------|
| `app/models/enums.py` | 7个枚举定义，全部继承(str, Enum) |
| `app/models/schemas.py` | 9个Pydantic模型，字段名使用camelCase |
| `app/exception.py` | 统一异常体系（AIServiceException + 4个子类） |
| `app/main.py` | 全局异常处理器 |
| `app/models/__init__.py` | 导出所有模型和枚举 |

### 使用的设计模式

1. **继承(str, Enum)模式**：确保枚举JSON序列化为字符串值而非对象
2. **Pydantic ConfigDict模式**：通过`populate_by_name=True`支持camelCase和snake_case双向兼容
3. **异常继承体系**：基础异常 + 业务子类，子类有默认HTTP状态码

### 关键代码逻辑说明

#### 枚举定义（继承str确保JSON序列化正确）

```python
class EducationLevel(str, Enum):
    UNDERGRADUATE = "undergraduate"
    MASTER = "master"
    PHD = "phd"
    FACULTY = "faculty"
```

#### Pydantic模型（camelCase字段名 + Field校验）

```python
class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    topic: str = Field(..., min_length=1, max_length=500, description="研究主题")
    paperIds: List[str] = Field(default_factory=list, description="论文ID列表")
    userProfile: UserProfile = Field(..., description="用户画像")
    analysisType: AnalysisType = Field(..., description="分析类型")
    analysisId: str = Field(..., min_length=1, description="分析任务ID")
```

#### 异常子类（默认HTTP状态码）

```python
class LLMException(AIServiceException):
    def __init__(self, message: str, code: int = 503):
        super().__init__(code=code, message=message)

class AgentTimeoutException(AIServiceException):
    def __init__(self, message: str, code: int = 408):
        super().__init__(code=code, message=message)
```

#### 全局异常处理器

```python
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

## 接口变更

### Request - AnalyzeRequest

```json
{
    "topic": "Multi-Agent协同决策",
    "paperIds": ["arxiv_2024_001"],
    "userProfile": {
        "educationLevel": "master",
        "researchField": "NLP",
        "knowledgeLevel": "intermediate",
        "preferredStyle": "balanced"
    },
    "analysisType": "report",
    "analysisId": "anl_001"
}
```

### Response - UnifiedResponse

```json
{
    "code": 200,
    "message": "success",
    "data": {
        "analysisId": "anl_001",
        "status": "completed",
        "report": "..."
    },
    "timestamp": 1716451200000
}
```

### Response - 错误响应

```json
{
    "code": 422,
    "message": "参数校验失败: ...",
    "data": null,
    "timestamp": 1716451200000
}
```

## 测试结果

| 测试场景 | 结果 |
|---------|------|
| 枚举序列化：`json.dumps(EducationLevel.MASTER)` → `"master"` | ✅ 通过 |
| AnalyzeRequest camelCase JSON序列化 | ✅ 通过 |
| 空`topic`创建抛ValidationError | ✅ 通过 |
| `topK=100`超范围抛ValidationError | ✅ 通过 |
| `LLMException`默认code=503 | ✅ 通过 |
| `AgentTimeoutException`默认code=408 | ✅ 通过 |
| AIServiceException处理器返回统一格式 | ✅ 通过 |
| RequestValidationError处理器返回422 | ✅ 通过 |
| `from app.models import AnalyzeRequest, EducationLevel` | ✅ 通过 |

**是否通过**：是

## 相关文件

### 新增文件

- `Veritas/ai-service/app/models/enums.py` — 7个枚举定义
- `Veritas/ai-service/app/models/schemas.py` — 9个Pydantic模型
- `Veritas/ai-service/app/exception.py` — 统一异常体系
- `Veritas/ai-service/app/core/config.py` — Pydantic Settings配置
- `Veritas/ai-service/app/core/logging.py` — Loguru日志配置
- `Veritas/ai-service/app/core/events.py` — 启动/关闭事件
- `Veritas/ai-service/app/api/router.py` — 路由聚合器
- `Veritas/ai-service/app/api/endpoints/agent.py` — Agent接口占位
- `Veritas/ai-service/app/api/endpoints/search.py` — 检索接口占位
- `Veritas/ai-service/app/api/endpoints/model.py` — 模型状态接口占位
- `Veritas/ai-service/app/main.py` — FastAPI入口
- `Veritas/ai-service/requirements.txt` — Python依赖
- `Veritas/ai-service/.env.example` — 环境变量示例
- `Veritas/ai-service/.gitignore` — Python项目gitignore

### 配置变更

- 无敏感配置硬编码，所有配置通过`.env`环境变量注入
