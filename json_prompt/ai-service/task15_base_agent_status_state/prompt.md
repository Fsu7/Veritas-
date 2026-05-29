# Task15: BaseAgent基类 + AgentStatus + AgentState

## 任务概述

| 项目 | 内容 |
|------|------|
| **版本** | v0.2 |
| **里程碑** | M2 / AM2：RAG检索与3-Agent基础可用 |
| **功能编号** | F3.1.1-F3.1.8 |
| **涉及层级** | python_ai_service |
| **优先级** | P0 |

## 需求描述

实现 Agent 基类 BaseAgent、Agent 状态枚举 AgentStatus、Agent 运行状态数据类 AgentState，产出 `agents/base.py`。BaseAgent 是 6-Agent 协同引擎的基础，所有具体 Agent 均继承此类。

## 影响范围

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `Veritas/ai-service/app/agents/base.py` | AgentStatus枚举 + AgentState数据类 + BaseAgent抽象基类 |
| 修改 | `Veritas/ai-service/app/agents/__init__.py` | 导出AgentStatus/AgentState/BaseAgent |

## 核心实现要求

### AgentStatus 枚举

```python
class AgentStatus(str, Enum):
    WAITING = "waiting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
```

- 继承 `str + Enum`，确保 JSON 序列化输出字符串值

### AgentState 数据类

```python
@dataclass
class AgentState:
    name: str
    status: AgentStatus = AgentStatus.WAITING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    progress: float = 0.0
    intermediate_result: Optional[str] = None
    error: Optional[str] = None
```

- 提供 `to_dict()` → dict（datetime转ISO字符串，AgentStatus转字符串）
- 提供 `update_progress(progress, intermediate_result)` 方法

### BaseAgent 抽象基类

```python
class BaseAgent(ABC):
    def __init__(self, name, llm_service, prompt_manager, timeout=30): ...
    async def execute(self, input_data, context) -> dict: ...
    @abstractmethod async def _run(self, prompt, input_data, context) -> dict: ...
    @abstractmethod def build_prompt(self, input_data, context) -> str: ...
    def _fallback_result(self, input_data) -> dict: ...
    def _summarize_result(self, result) -> str: ...
```

**execute() 流程**：
1. state.status = RUNNING，记录 started_at
2. build_prompt() 构建 Prompt
3. asyncio.wait_for(_run(), timeout=self.timeout)
4. 成功 → state.status = COMPLETED，记录 duration_ms
5. 超时 → state.status = FAILED，返回 _fallback_result()
6. 异常 → state.status = FAILED，返回 _fallback_result()

**降级返回格式**：`{"degraded": True, "agent": self.name, "error": self.state.error}`

## 依赖的已有模块

| 模块 | 复用方式 |
|------|---------|
| `app/exception.py` → AgentTimeoutException | 直接复用 |
| `app/core/config.py` → AGENT_TIMEOUT=30 | 直接复用 |
| `app/services/llm_service.py` → LLMService | 参考（子Agent调用） |
| `app/services/prompt_manager.py` → PromptManager | 参考（子Agent调用） |

## 约束

- Agent 异常不阻塞后续 Agent（execute 内部捕获所有异常）
- 超时时间从 settings.AGENT_TIMEOUT 读取，不硬编码
- AgentStatus 必须用 str+Enum（不用 IntEnum）
- 日志使用 Loguru，不在日志中输出敏感信息
- Python 命名规范：类名 PascalCase，函数 snake_case

## 禁止行为

- ❌ 输出伪代码或 TODO 注释
- ❌ 修改需求范围外的模块
- ❌ execute() 向上层抛出未捕获异常
- ❌ 硬编码超时时间
- ❌ 忽略降级场景

## 验证命令

```bash
cd Veritas/ai-service && python -m pytest tests/test_base_agent.py -v
cd Veritas/ai-service && python -c "from app.agents import AgentStatus, AgentState, BaseAgent; print('OK')"
```

## 验收标准

- [ ] AgentStatus 四值枚举，JSON 序列化输出字符串
- [ ] AgentState 含所有 SSE 推送字段，to_dict() 兼容 JSON
- [ ] BaseAgent 是 ABC，_run/build_prompt 是 @abstractmethod
- [ ] execute() 含超时控制，超时后返回降级结果不抛异常
- [ ] _fallback_result 返回 {degraded:True} 格式
- [ ] 超时从 settings 读取，不硬编码
- [ ] __init__.py 正确导出
- [ ] 所有 pytest 测试通过
