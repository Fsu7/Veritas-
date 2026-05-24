# Task02 — Python 数据模型、枚举与异常体系

| 项目 | 内容 |
|------|------|
| **项目** | XH-202630 科研文献智能助手 |
| **版本** | v0.1 |
| **里程碑** | M1：基础设施就绪 / AM1：项目骨架与模型层就绪 |

## 需求描述

实现 Python AI 服务的数据模型与异常体系：

1. **models/schemas.py** — 基于 Pydantic v2 的请求/响应模型定义，包含 UserProfile、AnalyzeRequest、SearchRequest、AgentStateResponse、AnalyzeResponse、SearchResult、SearchResponse、ModelStatusResponse、UnifiedResponse，所有模型含 Field 校验和描述
2. **models/enums.py** — 枚举定义，包含 EducationLevel、KnowledgeLevel、PreferredStyle、AnalysisType、AgentName、AgentStatus、LLMMode，所有枚举继承 `str` 和 `Enum` 确保 JSON 序列化正确
3. **exception.py** — 统一异常体系，包含 AIServiceException 基础异常（code+message）、LLMException、VectorStoreException、AgentTimeoutException、ModelNotLoadedException，以及 main.py 中的全局异常处理器

## 涉及层级

- `python_ai_service`

## 功能编号

- F3.5 / F3.1 / F3.2 / F3.3 / F3.4

## 需要修改/新增的文件

| 操作 | 路径 | 说明 |
|------|------|------|
| create | `Veritas/ai-service/app/models/schemas.py` | Pydantic 请求/响应模型定义（9 个模型） |
| create | `Veritas/ai-service/app/models/enums.py` | 枚举定义（7 个枚举类） |
| create | `Veritas/ai-service/app/exception.py` | 统一异常体系（1 个基础异常 + 4 个子类） |
| modify | `Veritas/ai-service/app/main.py` | 添加全局异常处理器，替换占位处理器 |
| modify | `Veritas/ai-service/app/models/__init__.py` | 导出所有模型和枚举 |

## 功能要求

| ID | 优先级 | 描述 |
|----|--------|------|
| FR-001 | P0 | enums.py 定义 7 个枚举类，全部继承 `(str, Enum)`：EducationLevel(undergraduate/master/phd/faculty)、KnowledgeLevel(beginner/intermediate/advanced/expert)、PreferredStyle(simple/balanced/technical)、AnalysisType(paper_analysis/compare/report)、AgentName(coordinator/retriever/analyzer/comparer/generator/reviewer)、AgentStatus(waiting/running/completed/failed)、LLMMode(auto/builtin/api/local)。枚举值使用 lower_case |
| FR-002 | P0 | schemas.py 定义 UserProfile 模型：educationLevel:EducationLevel、researchField:str=Field(...,min_length=1,max_length=100)、knowledgeLevel:KnowledgeLevel、preferredStyle:PreferredStyle。字段名使用 **camelCase**（与 Java 后端 API 契约一致），通过 `model_config` 设置 `populate_by_name=True` |
| FR-003 | P0 | schemas.py 定义 AnalyzeRequest 模型：topic:str=Field(...,min_length=1,max_length=500)、paperIds:List[str]=Field(default_factory=list)、userProfile:UserProfile、analysisType:AnalysisType、analysisId:str=Field(...,min_length=1)。字段名使用 camelCase |
| FR-004 | P0 | schemas.py 定义 SearchRequest 模型：query:str=Field(...,min_length=1,max_length=500)、topK:int=Field(default=10,ge=1,le=50)、filters:Optional[dict]=Field(default=None) |
| FR-005 | P0 | schemas.py 定义 5 个响应模型：AgentStateResponse(agentName/status/progress/intermediateResult/durationMs)、AnalyzeResponse(analysisId/status/report/citations/agentStates/degraded/degradedReason)、SearchResult(paperId/title/abstract/score/year/venue)、SearchResponse(results/total)、ModelStatusResponse(llmStatus/llmMode/embeddingStatus/chromaStatus/gpuAvailable/gpuMemoryUsed) |
| FR-006 | P0 | schemas.py 定义 UnifiedResponse 泛型统一响应包装：code:int=200、message:str='success'、data:Optional[Any]=None、timestamp:int=毫秒时间戳。提供类方法 `success(data, message='success')` 和 `error(code, message)` 快速创建响应 |
| FR-007 | P0 | exception.py 定义 AIServiceException 基础异常（code:int + message:str），4 个子类：LLMException(默认 code=503)、VectorStoreException(默认 code=503)、AgentTimeoutException(默认 code=408)、ModelNotLoadedException(默认 code=503)。子类 __init__ 接受 message 参数，code 有默认值但可覆盖 |
| FR-008 | P0 | main.py 添加全局异常处理器：1) AIServiceException 处理器返回 JSONResponse(status_code=exc.code, content={code,message,data:None,timestamp})；2) RequestValidationError 处理器返回 JSONResponse(status_code=422, content={code:422,message,data:None,timestamp})。替换占位处理器 |
| FR-009 | P1 | models/__init__.py 导出所有模型和枚举，方便 `from app.models import AnalyzeRequest` 等 |

### 跨系统字段命名映射

> API 请求/响应模型字段名使用 **camelCase** 与 Java 后端契约一致（如 educationLevel 而非 education_level），通过 Pydantic `model_config` 的 `populate_by_name=True` 支持两种命名方式。

| Java | Python (Pydantic) | JSON |
|------|-------------------|------|
| educationLevel | educationLevel | educationLevel |
| knowledgeLevel | knowledgeLevel | knowledgeLevel |
| preferredStyle | preferredStyle | preferredStyle |
| paperIds | paperIds | paperIds |
| analysisType | analysisType | analysisType |
| analysisId | analysisId | analysisId |
| agentStates | agentStates | agentStates |
| agentName | agentName | agentName |
| intermediateResult | intermediateResult | intermediateResult |
| durationMs | durationMs | durationMs |
| topK | topK | topK |
| paperId | paperId | paperId |
| llmStatus | llmStatus | llmStatus |
| llmMode | llmMode | llmMode |
| embeddingStatus | embeddingStatus | embeddingStatus |
| chromaStatus | chromaStatus | chromaStatus |
| gpuAvailable | gpuAvailable | gpuAvailable |
| gpuMemoryUsed | gpuMemoryUsed | gpuMemoryUsed |

## 验收标准

| ID | 验收条件 | 验证方式 |
|----|---------|---------|
| AC-001 | enums.py 包含 7 个枚举类，全部继承 (str, Enum)，枚举值使用 lower_case | 代码审查 |
| AC-002 | EducationLevel 枚举值与 MySQL user_profiles 表 education_level 字段 ENUM 值一致 | 代码审查 |
| AC-003 | schemas.py 包含 9 个 Pydantic 模型 | 代码审查 |
| AC-004 | AnalyzeRequest 字段名使用 camelCase 与 Java 后端 API 契约一致 | 代码审查 |
| AC-005 | AnalyzeRequest 空 topic 创建失败抛 ValidationError，非法枚举值创建失败 | 自动测试 |
| AC-006 | SearchRequest topK 范围 1-50，默认 10，超范围创建失败 | 自动测试 |
| AC-007 | UnifiedResponse.success() 和 .error() 类方法正确创建响应，timestamp 为毫秒时间戳 | 自动测试 |
| AC-008 | exception.py 包含 AIServiceException 基础异常和 4 个子类，子类有默认 HTTP 状态码 | 代码审查 |
| AC-009 | LLMException 默认 code=503，AgentTimeoutException 默认 code=408 | 自动测试 |
| AC-010 | 全局异常处理器返回统一格式 {code, message, data:null, timestamp}，与 Java 后端一致 | 自动测试 |
| AC-011 | RequestValidationError 处理器返回 422 状态码和统一格式 JSON | 自动测试 |
| AC-012 | 异常消息中不包含 API Key 等敏感信息 | 代码审查 |

## 验证命令

```bash
# 1. 验证枚举序列化
cd Veritas/ai-service && python -c "from app.models.enums import EducationLevel, AgentStatus, LLMMode; print(EducationLevel.MASTER.value, AgentStatus.RUNNING.value, LLMMode.AUTO.value)"
# 预期: master running auto

# 2. 验证请求模型创建
cd Veritas/ai-service && python -c "from app.models.schemas import AnalyzeRequest; req = AnalyzeRequest(topic='test',paperIds=[],userProfile={'educationLevel':'master','researchField':'NLP','knowledgeLevel':'intermediate','preferredStyle':'balanced'},analysisType='report',analysisId='anl_001'); print(req.model_dump_json())"
# 预期: 输出正确 JSON 字符串

# 3. 验证字段校验（空 topic 应失败）
cd Veritas/ai-service && python -c "from app.models.schemas import AnalyzeRequest; AnalyzeRequest(topic='',paperIds=[],userProfile={'educationLevel':'master','researchField':'NLP','knowledgeLevel':'intermediate','preferredStyle':'balanced'},analysisType='report',analysisId='anl_001')" 2>&1
# 预期: 抛出 ValidationError

# 4. 验证异常体系
cd Veritas/ai-service && python -c "from app.exception import LLMException, AgentTimeoutException; e1=LLMException('test'); e2=AgentTimeoutException('timeout'); print(e1.code, e2.code)"
# 预期: 503 408

# 5. 验证全局异常处理器
cd Veritas/ai-service && uvicorn app.main:app --host 0.0.0.0 --port 8000 & sleep 3 && curl -s -X POST http://localhost:8000/api/agent/analyze -H 'Content-Type: application/json' -d '{"topic":""}'
# 预期: 返回 422 和统一格式 JSON
```
