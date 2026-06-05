# AM3-6 — 错误处理联调 + 降级机制验证

> **里程碑**: AM3：API完善与Java对接（Week 5-6）
> **版本**: v0.3
> **涉及层级**: python_ai_service + java_backend
> **功能编号**: F3.1.8 + F3.3.5 + F3.5

---

## 1. 任务目标

验证 Python AI 服务三级降级机制 + 错误码体系：

| 降级级别 | 触发条件 | 降级行为 |
|---------|---------|---------|
| **LLM Provider 级** | builtin 失败 | 自动切换到 api，再失败切 local |
| **Agent 级** | 单 Agent 超时 30s | 跳过该 Agent，继续后续 |
| **Workflow 级** | 多 Agent 失败 | 降级为 retrieve+generate 单 Agent 模式 |

并验证 4 类错误码：422（参数校验）/ 408（超时）/ 500（异常）/ 503（服务未就绪）。

---

## 2. 涉及文件

| 操作 | 路径 | 说明 |
|------|------|------|
| 新增 | `Veritas/ai-service/tests/test_degradation.py` | 降级机制验证（8 个测试用例） |
| 新增 | `Veritas/ai-service/tests/fixtures/mock_failing_providers.py` | Mock 失败 LLM Provider |
| 新增 | `Veritas/ai-service/docs/DEGRADATION_TEST_REPORT.md` | 降级测试报告（9 场景） |
| 修改 | `Veritas/ai-service/app/services/llm_service.py` | 可能新增 _test_all_providers() 辅助方法 |

---

## 3. 9 个降级场景

| 编号 | 场景 | 触发 | 预期 |
|------|------|------|------|
| S1 | LLM Provider 单级降级 | builtin 抛 ConnectionError | active_provider → api |
| S2 | LLM 三路全失败 | builtin/api/local 全失败 | 抛 LLMException(503) |
| S3 | Agent 超时降级 | AnalyzerAgent sleep 31s | generator 继续，status='degraded' |
| S4 | 多 Agent 失败 | retriever+analyzer 都失败 | generator 基于 topic 简化生成 |
| S5 | 全 Agent 失败 | 3 个全失败 | 500 + degradedReason='所有 Agent 均失败' |
| S6 | 参数校验 422 | 缺 userId | 422 + message 含字段名 |
| S7 | 服务未就绪 503 | LLMService=None | 503 + ModelNotLoadedException |
| S8 | Agent 超时 408 | Agent.execute() TimeoutError | 408 + 统一格式 |
| S9 | LLM 恢复机制 | 降级 5min 后尝试恢复 | 重新尝试 builtin |

---

## 4. 降级测试报告结构

```markdown
# Python AI 服务降级机制测试报告

## 1. 概述
- 测试时间、Python 版本、测试用例数

## 2. 降级场景实测结果（表格）
| 场景 | 触发条件 | 预期降级 | 实测降级 | 降级时长(ms) | 状态 |

## 3. LLM Provider 降级链路
（流程图：builtin → api → local → 报错）

## 4. Agent 降级链路
（流程图：单 Agent 失败 → 跳过 / 多 Agent 失败 → 单 Agent 模式）

## 5. 错误码体系验证
| code | 异常类 | 实测 HTTP | 实测 code | 触发场景 |

## 6. 降级日志摘录
（含 WARNING 级别的 'LLM fallback' / 'Agent ... failed' 日志）

## 7. 改进建议
```

---

## 5. 关键测试代码示例

```python
# tests/test_degradation.py
import pytest
from unittest.mock import patch, AsyncMock
from app.services.llm_service import LLMService
from app.exception import LLMException

@pytest.mark.asyncio
async def test_llm_provider_fallback_builtin_to_api(settings):
    settings.LLM_BUILTIN_URL = "http://fake-builtin"
    settings.LLM_API_KEY = "fake"
    settings.LLM_API_BASE = "http://fake-api"
    
    with patch("app.services.llm_service.BuiltinLLMProvider.test_connection",
               AsyncMock(side_effect=ConnectionError)):
        with patch("app.services.llm_service.APILLMProvider.test_connection",
                   AsyncMock(return_value=True)):
            service = LLMService(settings)
            await service.initialize()
            assert service.active_provider.mode == "api"

@pytest.mark.asyncio
async def test_agent_timeout_skip_continue():
    # 模拟 AnalyzerAgent 超时
    with patch("app.agents.analyzer.AnalyzerAgent.execute",
               AsyncMock(side_effect=asyncio.TimeoutError)):
        result = await run_workflow(request, agent_instances)
        assert result["status"] == "degraded"
        assert "analyzer" in result["degraded_reason"].lower()
        assert result["report"] is not None  # generator 仍执行
```

---

## 6. 验收标准

- [ ] LLM Provider 三路降级（builtin→api→local）正常工作
- [ ] 单 Agent 超时/失败不阻塞后续 Agent
- [ ] 多 Agent 失败时 status='degraded'，不返回 5xx
- [ ] 所有 Agent 失败时返回 500 + 降级信息
- [ ] 错误码 422/408/503 正确返回
- [ ] 降级测试报告含 9 个场景实测结果与降级时长
- [ ] 降级日志 WARNING 级别记录完整

---

## 7. 参考文档

- [AI服务架构 §5.7 工作流降级](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块系统架构文档.md)
- [AI服务架构 §7.5 LLM 自动降级时序](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块系统架构文档.md)
- [AI服务架构 §15.2 异常体系](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块系统架构文档.md)

---

## 8. 下一步建议

- 任务 7（task30）将基于本任务的降级行为，做 SSE 稳定性测试（降级事件推送）
- 任务 8（task31）将做完整集成测试 + Bug 修复
- 建议在 LLMService 增加 `_failure_count[mode]` 计数器，连续失败 3 次才降级（避免抖动）
