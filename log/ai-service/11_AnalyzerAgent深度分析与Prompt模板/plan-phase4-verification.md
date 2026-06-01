# Phase 4: AnalyzerAgent 全局验证计划

## 背景

Task17 (AnalyzerAgent核心逻辑)、Task18 (Prompt模板增强)、Task19 (单元测试) 的代码已全部编写完成。本计划聚焦于 **Phase 4: 全局验证** — 运行测试确认所有代码正确工作。

## 当前文件状态

| 文件 | 状态 | 说明 |
|------|------|------|
| `app/agents/analyzer.py` | ✅ 已修改 | 5维度提取、JSON解析、降级、confidence计算、ai_disclaimer、analysis_id |
| `prompts/analyzer.txt` | ✅ 已修改 | 9块模板、CoT、嵌套JSON Schema、ai_disclaimer字段 |
| `tests/test_analyzer_agent.py` | ✅ 已重写 | ~42个测试方法、12个测试类 |

## 验证步骤

### Step 1: 运行 AnalyzerAgent 单元测试

```bash
cd /Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/ai-service
python3 -m pytest tests/test_analyzer_agent.py -v
```

**预期**: 全部 ~42 个测试通过

**潜在问题点**:
- `pytest-asyncio` 无 `asyncio_mode` 配置文件，使用默认 `strict` 模式 — 测试中已使用 `@pytest.mark.asyncio` 装饰器，应兼容
- `_fallback_result` 调用 `super()._fallback_result()` 返回 `{"degraded": True, "agent": ..., "error": ...}`，再 `.update()` 追加字段 — 需确认字段不冲突
- `TestExecuteIntegration.test_execute_error_flow` — LLM异常在 `_run` 内部被捕获，`execute` 正常完成（status=COMPLETED），需确认断言正确

### Step 2: 运行 PromptManager analyzer 相关测试

```bash
python3 -m pytest tests/test_prompt_manager.py -v -k "analyzer"
```

**预期**: 2个analyzer相关测试通过（`test_get_prompt_analyzer`, `test_get_prompt_safe_substitute`）

**潜在问题点**:
- `analyzer.txt` 新增了 `ai_disclaimer` 字段和第9块内容，但 `$variable` 语法未变，`safe_substitute` 应正常工作

### Step 3: 运行全量测试套件

```bash
python3 -m pytest tests/ -v --tb=short
```

**预期**: 所有测试通过（包括 retriever、prompt_manager、analyzer 等）

### Step 4: 修复任何失败的测试

根据 Step 1-3 的结果，定位并修复失败测试。常见修复方向：

| 问题类型 | 修复策略 |
|---------|---------|
| asyncio_mode 报错 | 添加 `pytest.ini` 配置 `asyncio_mode = auto` |
| Import 错误 | 检查 `__init__.py` 或模块路径 |
| 断言值不匹配 | 核对代码逻辑与测试期望是否一致 |
| Mock 行为不符 | 调整 mock 返回值或 side_effect |

### Step 5: 最终确认

全部测试通过后，确认：
- [ ] `test_analyzer_agent.py` 全部通过
- [ ] `test_prompt_manager.py` analyzer 测试通过
- [ ] 全量测试套件通过
- [ ] 无 lint/type 错误

## 风险评估

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| pytest-asyncio strict模式不兼容 | 中 | 测试无法运行 | 添加 pytest.ini 配置 |
| _fallback_result 字段冲突 | 低 | 断言失败 | 调整测试或代码 |
| conftest.py fixture 冲突 | 低 | 测试隔离问题 | 检查 fixture scope |
