# task07 — APILLMProvider（外接API）

## 项目
XH-202630 科研文献智能助手 — v0.1 M1：基础设施就绪 / AM1：项目骨架与模型层就绪

## 需求概述
在 task06 的 LLM 服务骨架基础上，实现 APILLMProvider（外接第三方 API），支持用户自配 OpenAI 兼容 API。

核心交付：
1. `services/llm_service.py` — 新增 APILLMProvider 类 + 扩展 LLMService.initialize() 降级逻辑
2. `.env.example` — 补充方案 B 外接 API 配置示例

## 影响范围

| 层级 | 涉及模块 |
|------|---------|
| python_ai_service | app/services/llm_service.py（修改：新增 APILLMProvider + 扩展 initialize） |
| python_ai_service | .env.example（修改：补充 API 配置示例） |

## 核心实现要求

### APILLMProvider
- 继承 LLMProvider，`mode='api'`
- `__init__` 校验 `LLM_API_KEY` 非空，为空抛出 `ValueError`
- 使用 `openai.AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_API_BASE)`
- `generate()` / `generate_stream()` / `test_connection()` 与 BuiltinLLMProvider 逻辑一致
- 支持讯飞星火 / DeepSeek / 通义千问 / 任何 OpenAI 兼容端点

### LLMService.initialize() 扩展
- AUTO 模式：Builtin 失败后尝试 APILLMProvider
- Builtin 成功时仍将 APILLMProvider 加入 providers 字典备用
- API 模式：跳过 Builtin，直接使用 APILLMProvider

### 关键约束
- LLM_API_KEY 通过环境变量注入，禁止硬编码
- 必须使用 AsyncOpenAI
- 不修改 BuiltinLLMProvider 已有实现
- 日志中禁止输出完整 API Key

## 文件清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `Veritas/ai-service/app/services/llm_service.py` | 新增 APILLMProvider + 扩展 initialize |
| 修改 | `Veritas/ai-service/.env.example` | 补充外接 API 配置示例 |

## 验收标准
- [ ] `APILLMProvider` 继承 `LLMProvider`，`mode == 'api'`
- [ ] `LLM_API_KEY` 为空时 `__init__` 抛出 `ValueError`
- [ ] `generate()` / `generate_stream()` 逻辑与 BuiltinLLMProvider 一致
- [ ] AUTO 模式下 Builtin 失败后自动降级到 APILLMProvider
- [ ] Builtin 成功时 APILLMProvider 仍被加入 providers 备用
- [ ] `.env.example` 包含 DeepSeek / 讯飞星火等配置示例
- [ ] 未修改 BuiltinLLMProvider 已有实现
- [ ] 日志中不输出完整 API Key
