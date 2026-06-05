# AM3-1 — API请求校验完善 + 统一响应格式

> **里程碑**: AM3：API完善与Java对接（Week 5-6）
> **版本**: v0.3
> **涉及层级**: python_ai_service + java_backend 联调前置
> **功能编号**: F3.5.1 / F3.5.2 / F3.5.4 / F3.5.5

---

## 1. 任务目标

为 Python AI 服务实现：
1. 严格的 Pydantic 请求体校验（Enum 校验 + 范围/长度校验 + extra='forbid'）
2. 统一响应格式包装器 `{code, message, data, timestamp}`（与 Java 端 `ApiResponse` 一致）
3. 422 错误响应细化（字段名 + 错误原因）
4. 所有 endpoint success 路径使用 `ok()` 包装

**与 Java 后端契约对齐**：Java 端 `ApiResponse<T>` 通过 WebClient 反序列化 `data` 字段为业务 DTO，要求 Python 端 JSON 字段名严格使用 camelCase（已通过 Pydantic alias 实现）。

---

## 2. 涉及文件

| 操作 | 路径 | 说明 |
|------|------|------|
| 新增 | `Veritas/ai-service/app/utils/response.py` | 统一响应工厂：ok/fail/now_ts_ms |
| 新增 | `Veritas/ai-service/app/models/enums.py` | 4 个 StrEnum + AgentStatus + LLMMode |
| 修改 | `Veritas/ai-service/app/models/schemas.py` | 升级字段为 Enum + extra='forbid' |
| 修改 | `Veritas/ai-service/app/main.py` | /health 用 ok() 包装 + 细化 422 message |
| 修改 | `Veritas/ai-service/app/api/endpoints/agent.py` | success 用 ok() 包装 |
| 修改 | `Veritas/ai-service/app/api/endpoints/search.py` | success 用 ok() 包装 |
| 修改 | `Veritas/ai-service/app/api/endpoints/model.py` | success 用 ok() 包装 |
| 新增 | `Veritas/ai-service/tests/test_request_validation_response.py` | pytest 单元测试 |

---

## 3. 实现要求

### 3.1 统一响应格式（FR-001）

```python
# app/utils/response.py
def ok(data: Any = None, message: str = "success", code: int = 200) -> dict:
    return {"code": code, "message": message, "data": data, "timestamp": now_ts_ms()}

def fail(message: str, code: int = 500, data: Any = None) -> dict:
    return {"code": code, "message": message, "data": data, "timestamp": now_ts_ms()}

def now_ts_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)
```

### 3.2 枚举定义（FR-002）

```python
# app/models/enums.py
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
```

### 3.3 字段升级为 Enum（FR-003）

```python
# app/models/schemas.py（修改）
class UserProfile(BaseModel):
    education_level: EducationLevel = Field(default=EducationLevel.MASTER, alias="educationLevel")
    knowledge_level: KnowledgeLevel = Field(default=KnowledgeLevel.INTERMEDIATE, alias="knowledgeLevel")
    preferred_style: PreferredStyle = Field(default=PreferredStyle.BALANCED, alias="preferredStyle")
    research_field: str = Field(default="", alias="researchField")
    model_config = ConfigDict(populate_by_name=True, extra="forbid")
```

### 3.4 全局异常处理器（FR-004 + FR-007）

```python
# app/main.py（修改）
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    field_msgs = [f"{'.'.join(str(x) for x in e['loc'][1:])}: {e['msg']}" for e in errors]
    return JSONResponse(
        status_code=422,
        content={
            "code": 422,
            "message": f"参数校验失败: {'; '.join(field_msgs)}",
            "data": None,
            "timestamp": now_ts_ms(),
        },
    )
```

---

## 4. 验收标准

- [ ] `app/utils/response.py` 实现完成
- [ ] `app/models/enums.py` 实现 4 个 StrEnum
- [ ] `schemas.py` 字段升级为 Enum，`extra="forbid"`
- [ ] 所有 endpoint success 路径用 `ok()` 包装
- [ ] 非法枚举值返回 422 + 统一格式
- [ ] 缺 `userId` 返回 422 + 明确字段提示
- [ ] Java 风格 camelCase 请求体可被正确反序列化
- [ ] 单元测试 100% 通过

---

## 5. 参考文档

- [AI服务架构 §4.4 API服务模块](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块系统架构文档.md)
- [AI服务里程碑 §5.3 AM3任务分解](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块项目里程碑文档.md)
- [Java后端统一响应实现](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/json_prompt/backend/task04_api_response_dto/)

---

## 6. 下一步建议

- 任务 2（task25）将基于本任务的统一响应格式，实现 SSE 流式推送
- 任务 3（task26）将扩展本任务的主入口和异常码
- 建议 Java 端先确认 `ApiResponse<T>` 反序列化 `data` 字段的 Jackson 配置（`@JsonIgnoreProperties(ignoreUnknown = true)` 必须开启）
