# 技术教学文档

## 开发思路

### 需求分析过程
本次任务源于M1阶段审阅（python-agent-review），审阅发现15项检查清单中有4项未通过：
1. **P0缺失**：API端点全是stub，无Pydantic请求模型 → 空topic不返回422
2. **P0缺失**：缺少.env配置文件 → 服务无法正常启动
3. **P1风险**：Embedding维度硬编码1024，load_model失败时残留错误值
4. **P1缺失**：缺少批量性能基准测试

审阅还发现了一个隐藏的Python导入陷阱Bug，导致/health端点始终返回"not_loaded"。

### 技术选型考虑
- **Pydantic v2 Field校验**：使用 `pattern` 正则替代自定义validator，更简洁
- **模块级单例模式**：通过 `app.core.events` 模块管理全局服务实例
- **property模式**：将 `dimension` 从实例属性改为property，延迟到load_model成功后才可用

### 架构设计思路
遵循分层架构约束：Router → Service → Infrastructure
- 路由层（endpoints/）仅做参数校验和服务调用
- 业务逻辑在services/层
- Pydantic模型定义在models/schemas.py，与路由分离

### 遇到的问题及解决方案

**问题1：Python导入陷阱**
```python
# 错误写法 — 导入时绑定None值
from app.core.events import embedding_service  # 此时embedding_service=None

# on_startup()中 global embedding_service = EmbeddingService(...)
# 但已导入的引用仍指向None！

# 正确写法 — 导入模块，通过属性访问
from app.core import events
# events.embedding_service 始终指向最新值
```

**问题2：.env文件污染测试**
创建.env后，pydantic-settings自动加载LLM_API_KEY，导致原本设计为"无API Key降级到local"的测试失败。解决方案：在测试中显式设置 `LLM_API_KEY=""`。

**问题3：Embedding维度不确定性**
bge-large-zh-v1.5实际输出1024维（非768维），text-embedding-v4也是1024维。硬编码值恰好正确，但设计不安全。改为property + None初始值。

## 实现步骤

1. **创建.env配置文件** — 从.env.example复制，填入DashScope API Key，配置LLM_MODE=api + qwen-turbo
2. **创建Pydantic数据模型** — 新建models/schemas.py，定义7个模型（UserProfile/AnalyzeRequest/SearchRequest/AnalyzeResponse/SearchResultItem/SearchResponse/ModelStatusResponse）
3. **更新API端点** — 替换3个stub端点为真实实现，接入Pydantic校验
4. **修复导入陷阱** — 将所有 `from app.core.events import xxx` 改为 `from app.core import events`
5. **修复Embedding维度安全性** — `self.dimension = 1024` → `self._dimension = None` + property
6. **补充测试** — 新建test_performance.py，更新test_vector_store.py和test_embedding.py
7. **端到端验证** — 启动服务 + curl测试 + pytest 77/77通过

## 解决了什么问题

### 核心问题描述
M1阶段审阅发现AI服务存在4类问题：配置缺失、API校验缺失、维度安全隐患、测试覆盖不足。此外还发现一个隐藏的Python导入陷阱Bug。

### 解决方案对比
| 方案 | 描述 | 优劣 |
|------|------|------|
| 方案A：最小修复 | 仅创建.env + 添加Pydantic模型 | 快速但遗漏导入陷阱和维度安全 |
| 方案B：全面修复 | 修复所有问题 + 发现隐藏Bug | ✅ 最终选择，彻底解决 |

### 最终方案的优势
- 修复了隐藏的导入陷阱Bug，否则所有端点都无法获取服务状态
- dimension改为property，从设计层面消除维度不匹配风险
- 77个测试全部通过，覆盖正常流+异常流+降级场景

## 变更内容

### 新增文件
- `app/models/__init__.py` — 包初始化
- `app/models/schemas.py` — 7个Pydantic请求/响应模型
- `.env` — DashScope API配置（含API Key）
- `tests/test_performance.py` — 批量编码性能基准测试

### 修改文件
- `app/main.py` — 导入方式从 `from app.core.events import xxx` 改为 `from app.core import events`
- `app/api/endpoints/agent.py` — 接入AnalyzeRequest/Response，服务就绪校验
- `app/api/endpoints/search.py` — 接入SearchRequest/Response，真实检索链路
- `app/api/endpoints/model.py` — 返回embedding维度+LLM provider
- `app/services/embedding_service.py` — `dimension` 从实例属性改为property，初始值None
- `tests/test_embedding.py` — `dimension is None` 初始状态断言
- `tests/test_vector_store.py` — `DEFAULT_EMBEDDING_DIM` 常量替代硬编码
- `tests/test_llm.py` — 修复.env污染导致的降级测试失败

### 配置变更
- `.env` 新增：`DASHSCOPE_API_KEY`、`LLM_MODE=api`、`LLM_API_KEY`、`LLM_API_BASE`、`LLM_MODEL_NAME=qwen-turbo`

## 关键技术点

### 1. Python模块级变量的导入陷阱
Python中 `from module import var` 在导入时绑定值，后续模块内 `global var = new_value` 不会更新已导入的引用。正确做法是 `import module` 然后通过 `module.var` 访问。

### 2. Pydantic v2 Field校验模式
```python
education_level: str = Field(..., pattern="^(undergraduate|master|phd|faculty)$")
topic: str = Field(..., min_length=1, max_length=500)
top_k: int = Field(default=10, ge=1, le=50)
```
- `pattern` 替代自定义validator，更简洁
- `min_length=1` 确保空字符串触发422
- `ge/le` 替代 `gt/lt`，边界值更明确

### 3. Property模式保护关键状态
```python
class EmbeddingService:
    def __init__(self, settings):
        self._dimension: int | None = None

    @property
    def dimension(self) -> int | None:
        return self._dimension
```
避免 `dimension` 在 `load_model()` 失败时残留错误的硬编码值。

### 4. FastAPI lifespan + 模块级全局服务
```python
# events.py
embedding_service = None  # 模块级变量

async def on_startup():
    global embedding_service
    embedding_service = EmbeddingService(settings)
```
通过 `from app.core import events` 访问，确保始终获取最新实例。

## 经验总结

### 开发过程中的收获
- **审阅驱动开发**：python-agent-review的9大风险维度审阅发现了隐藏Bug，比单纯功能测试更有效
- **导入陷阱是Python常见坑**：在FastAPI lifespan模式中尤其容易踩到，因为服务实例在启动时才创建

### 踩过的坑及如何避免
1. **坑**：`from module import var` 导入None后，global赋值不更新引用
   - **避免**：统一使用 `import module` + `module.var` 模式
2. **坑**：.env文件创建后污染测试环境，pydantic-settings自动加载
   - **避免**：测试中显式覆盖关键配置项（如 `LLM_API_KEY=""`）
3. **坑**：Embedding维度在不同模型间不一致（bge-large-zh=1024, text-embedding-v4=1024, 但文档写768）
   - **避免**：运行时动态获取维度，不硬编码

### 最佳实践建议
1. **FastAPI全局服务**：使用模块级变量 + `import module` 模式，不要用 `from module import var`
2. **Pydantic校验**：用 `pattern` 正则替代枚举校验，用 `min_length=1` 确保非空
3. **配置管理**：测试中始终显式设置关键配置项，避免.env污染
4. **维度安全**：Embedding维度通过property延迟绑定，初始值None
5. **审阅先行**：功能开发完成后，先用review skill审阅再验证
