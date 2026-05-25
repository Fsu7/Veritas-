# M1审阅修复与Pydantic模型补全

## 功能描述
- 解决了M1阶段审阅发现的6项问题（1项缺失、3项风险、2项待验证），将M1检查清单通过率从73%提升至93%
- 补全了Pydantic请求/响应数据模型，使API端点具备参数校验能力（空topic返回422）
- 修复了Python模块导入陷阱导致服务状态无法正确传递的关键Bug
- 修复了Embedding维度硬编码的安全隐患
- 创建了.env配置文件，使服务可通过DashScope API正常启动
- 业务价值：M1基础设施就绪检查清单从11/15通过提升至14/15通过，为M2单Agent可用奠定基础

## 实现逻辑
- 修改的核心文件列表：
  - `app/models/schemas.py`（新建）— 7个Pydantic模型
  - `app/models/__init__.py`（新建）— 包初始化
  - `app/api/endpoints/agent.py`（修改）— 接入AnalyzeRequest/Response
  - `app/api/endpoints/search.py`（修改）— 接入SearchRequest/Response，真实检索链路
  - `app/api/endpoints/model.py`（修改）— 返回embedding维度+LLM provider
  - `app/main.py`（修改）— 修复Python导入陷阱
  - `app/services/embedding_service.py`（修改）— dimension改为property
  - `.env`（新建）— DashScope API Key配置
  - `tests/test_performance.py`（新建）— 批量性能基准测试
  - `tests/test_vector_store.py`（修改）— 动态维度适配
  - `tests/test_embedding.py`（修改）— dimension初始值断言更新
  - `tests/test_llm.py`（修改）— 修复.env污染导致的降级测试失败
- 使用的设计模式：Pydantic Field校验模式、Python模块级单例（events模块）
- 关键代码逻辑说明：
  - `from app.core import events` 替代 `from app.core.events import xxx`，避免导入时绑定None值
  - `dimension` 从实例属性改为property，初始值None，load_model()成功后才赋值
  - Pydantic模型使用 `Field(..., min_length=1)` + `pattern` 正则实现枚举校验

## 接口变更

### Request — POST /api/agent/analyze
```json
{
  "topic": "Multi-Agent协同决策",
  "paper_ids": ["arxiv_2024_001"],
  "user_id": "usr_001",
  "user_profile": {
    "education_level": "master",
    "research_field": "NLP",
    "knowledge_level": "intermediate",
    "preferred_style": "balanced"
  }
}
```

### Response — POST /api/agent/analyze
```json
{
  "analysis_id": "ana_56c986c1a538",
  "status": "processing"
}
```

### Request — POST /api/search/
```json
{
  "query": "大语言模型在科研中的应用",
  "top_k": 10,
  "filters": {"yearFrom": 2022, "yearTo": 2024}
}
```

### Response — POST /api/search/
```json
{
  "results": [
    {
      "paper_id": "arxiv_2024_001",
      "title": "Multi-Agent Survey",
      "abstract": "A survey on multi-agent systems",
      "score": 0.95,
      "year": 2024,
      "venue": "ACL"
    }
  ],
  "total": 1
}
```

### Response — GET /api/model/status
```json
{
  "llm": "loaded",
  "embedding": "loaded_api",
  "chroma": "connected",
  "prompts": "loaded",
  "embedding_dimension": 1024,
  "active_llm_provider": "api"
}
```

### 422 校验失败响应
```json
{
  "code": 422,
  "message": "参数校验失败: 1 validation error:\n  {'type': 'string_too_short', 'loc': ('body', 'topic'), ...}",
  "data": null,
  "timestamp": 1779694050323
}
```

## 测试结果
- 测试场景1：空topic请求 → 返回422（Pydantic校验生效）：✅ 通过
- 测试场景2：无效education_level → 返回422：✅ 通过
- 测试场景3：正常analyze请求 → 返回analysis_id：✅ 通过
- 测试场景4：search请求（空ChromaDB）→ 返回空结果：✅ 通过
- 测试场景5：/health端点 → 返回所有服务正确状态：✅ 通过
- 测试场景6：/api/model/status → 返回embedding维度和LLM provider：✅ 通过
- 测试场景7：pytest 77/77全部通过（71单元+6集成）：✅ 通过
- 是否通过：是

## 相关文件
- `Veritas/ai-service/.env` — 新建，DashScope API配置
- `Veritas/ai-service/app/models/schemas.py` — 新建，7个Pydantic模型
- `Veritas/ai-service/app/models/__init__.py` — 新建
- `Veritas/ai-service/app/api/endpoints/agent.py` — 修改
- `Veritas/ai-service/app/api/endpoints/search.py` — 修改
- `Veritas/ai-service/app/api/endpoints/model.py` — 修改
- `Veritas/ai-service/app/main.py` — 修改，修复导入陷阱
- `Veritas/ai-service/app/services/embedding_service.py` — 修改，dimension安全性
- `Veritas/ai-service/tests/test_performance.py` — 新建
- `Veritas/ai-service/tests/test_vector_store.py` — 修改
- `Veritas/ai-service/tests/test_embedding.py` — 修改
- `Veritas/ai-service/tests/test_llm.py` — 修改
