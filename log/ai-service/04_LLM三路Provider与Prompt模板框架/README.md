# LLM三路Provider与Prompt模板框架

## 功能描述
- 解决了AI服务层LLM调用的统一抽象与多Provider降级问题
- 实现了BuiltinLLMProvider（软件方云模型）、APILLMProvider（用户配置第三方API）、LocalLLMProvider（本地Transformers模型）三路Provider，支持启动时自动检测和运行时自动降级
- 实现了PromptManager模板框架，使用`string.Template`管理6个Agent的Prompt模板，支持变量替换
- 创建了Dockerfile，为AI服务Docker化部署提供基础
- 业务价值：确保AI服务在任何环境下至少有一路LLM可用，提升系统鲁棒性；Prompt模板框架为后续Agent开发提供标准化Prompt管理

## 实现逻辑

### 修改的核心文件列表
| 文件 | 操作 | 说明 |
|------|------|------|
| `app/services/llm_service.py` | 修改 | +LocalLLMProvider类 +LLMService三路降级逻辑 |
| `app/services/prompt_manager.py` | 新建 | PromptManager模板管理 |
| `app/core/events.py` | 修改 | +unload_model +prompt_manager初始化 |
| `app/main.py` | 修改 | /health添加prompts状态字段 |
| `.env.example` | 修改 | +方案B/C配置示例 |
| `Dockerfile` | 新建 | Docker镜像构建 |
| `prompts/coordinator.txt` | 新建 | 协调者Agent Prompt |
| `prompts/retriever.txt` | 新建 | 检索Agent Prompt |
| `prompts/analyzer.txt` | 新建 | 分析Agent Prompt |
| `prompts/comparer.txt` | 新建 | 对比Agent Prompt |
| `prompts/generator.txt` | 新建 | 生成Agent Prompt |
| `prompts/reviewer.txt` | 新建 | 审核Agent Prompt |
| `tests/test_llm.py` | 修改 | +LocalLLMProvider测试 +降级测试 |
| `tests/test_prompt_manager.py` | 新建 | PromptManager单元测试 |
| `tests/test_integration.py` | 新建 | 集成测试 |

### 使用的算法或设计模式
- **抽象工厂模式**：LLMProvider ABC定义统一接口，3个具体Provider实现
- **策略模式**：LLMService根据LLM_MODE选择Provider策略
- **降级模式（Circuit Breaker变体）**：三路Provider按优先级降级，5分钟恢复探测
- **模板方法模式**：PromptManager使用string.Template管理Prompt变量替换

### 关键代码逻辑说明

#### 三路Provider优先级链
```
BuiltinLLMProvider（方案A，最高优先级）
    ↓ 失败/超时
APILLMProvider（方案B，用户配置API）
    ↓ 失败/超时
LocalLLMProvider（方案C，本地模型兜底）
    ↓ 全部失败
RuntimeError("No LLM provider available")
```

#### LLMService降级状态跟踪
```python
_degradation_state = {
    "current_provider": None,       # 当前活跃Provider
    "fallback_count": 0,            # 降级总次数
    "last_fallback_at": None,       # 最近降级时间
    "consecutive_failures": {},     # 各Provider连续失败次数
}
```

#### LocalLLMProvider异步适配
- `load_model()` / `generate()` — `run_in_executor` 包装CPU密集操作
- `generate_stream()` — `TextIteratorStreamer` + `threading.Thread` + `queue.Queue` 适配异步迭代器
- `transformers` / `torch` 延迟导入，避免无GPU环境启动崩溃

## 接口变更

### Request — LLMService初始化配置
```json
{
    "LLM_MODE": "auto",
    "LLM_BUILTIN_URL": "https://llm.literature-assistant.com/v1",
    "LLM_BUILTIN_API_KEY": "",
    "LLM_BUILTIN_MODEL": "qwen-plus",
    "LLM_API_KEY": "sk-xxx",
    "LLM_API_BASE": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "LLM_MODEL_NAME": "qwen-plus",
    "LLM_LOCAL_MODEL_PATH": "Qwen/Qwen2-1.5B-Instruct"
}
```

### Response — /health端点
```json
{
    "status": "UP",
    "timestamp": "2026-05-25T12:00:00+00:00",
    "llm": "loaded",
    "embedding": "loaded",
    "chroma": "connected",
    "prompts": "loaded"
}
```

### Prompt模板变量替换示例
```python
# 输入
pm.get_prompt("analyzer", paper_title="Attention Is All You Need", paper_abstract="...", extra_instruction="")

# 输出：模板中 $paper_title 被替换为 "Attention Is All You Need"
```

## 测试结果
- **test_llm.py**：47个测试全部通过
  - TestLLMMode（4个）：枚举值验证
  - TestLLMProvider（1个）：抽象类不可实例化
  - TestBuiltinLLMProvider（6个）：初始化/generate/stream/connection
  - TestAPILLMProvider（8个）：初始化/验证/generate/stream/connection
  - TestLocalLLMProvider（8个）：初始化/load/generate/stream/unload/connection
  - TestLLMService（8个）：初始化/降级初始化/generate异常
  - TestLLMServiceDegradation（8个）：三路降级/运行时降级/状态跟踪/恢复
  - TestLLMService（4个）：原有基础测试
- **test_prompt_manager.py**：12个测试全部通过
  - 初始化/加载6个模板/变量替换/safe_substitute/KeyError/列表排序
- **test_integration.py**：6个测试全部通过
  - 模板加载/Agent模板完整性/变量替换/健康检查结构
- **全量回归**：86个测试通过，3个跳过（DashScope API Key）
- 是否通过：✅ 是

## 相关文件
- `Veritas/ai-service/app/services/llm_service.py`
- `Veritas/ai-service/app/services/prompt_manager.py`
- `Veritas/ai-service/app/core/events.py`
- `Veritas/ai-service/app/main.py`
- `Veritas/ai-service/.env.example`
- `Veritas/ai-service/Dockerfile`
- `Veritas/ai-service/prompts/coordinator.txt`
- `Veritas/ai-service/prompts/retriever.txt`
- `Veritas/ai-service/prompts/analyzer.txt`
- `Veritas/ai-service/prompts/comparer.txt`
- `Veritas/ai-service/prompts/generator.txt`
- `Veritas/ai-service/prompts/reviewer.txt`
- `Veritas/ai-service/tests/test_llm.py`
- `Veritas/ai-service/tests/test_prompt_manager.py`
- `Veritas/ai-service/tests/test_integration.py`
