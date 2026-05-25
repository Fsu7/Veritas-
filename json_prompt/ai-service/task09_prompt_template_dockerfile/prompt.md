# task09 — Prompt模板框架 + Dockerfile + 集成测试

## 项目
XH-202630 科研文献智能助手 — v0.1 M1：基础设施就绪 / AM1：项目骨架与模型层就绪

## 需求概述
实现 Prompt 模板管理框架、6 个 Agent Prompt 模板文件、Dockerfile 和集成测试，完成 AI 服务 M1 里程碑的最后交付。

核心交付：
1. `services/prompt_manager.py` — PromptManager 统一管理模板加载和变量替换
2. `prompts/` — 6 个 Agent Prompt 模板文件（coordinator/retriever/analyzer/comparer/generator/reviewer）
3. `Dockerfile` — AI 服务 Docker 镜像构建
4. `tests/test_prompt_manager.py` — PromptManager 单元测试
5. `tests/test_integration.py` — 集成测试
6. `events.py` / `main.py` — 启动加载 + 健康检查

## 影响范围

| 层级 | 涉及模块 |
|------|---------|
| python_ai_service | app/services/prompt_manager.py（新增） |
| python_ai_service | prompts/*.txt（新增 6 个模板） |
| python_ai_service | Dockerfile（新增） |
| python_ai_service | tests/test_prompt_manager.py（新增） |
| python_ai_service | tests/test_integration.py（新增） |
| python_ai_service | app/core/events.py（修改：加载 PromptManager） |
| python_ai_service | app/main.py（修改：health 添加 prompts 状态） |

## 核心实现要求

### PromptManager
- `load_templates()` — 遍历 prompts/*.txt，创建 `string.Template` 对象
- `get_prompt(agent_name, **kwargs)` — `safe_substitute` 变量替换
- `list_templates()` — 返回排序后的模板名列表
- 模板加载失败不阻塞启动，记录 WARNING

### Prompt 模板变量规范
使用 `string.Template` 的 `$variable` 格式：

| 模板 | 变量 |
|------|------|
| coordinator.txt | $query, $user_profile |
| retriever.txt | $topic, $top_k |
| analyzer.txt | $paper_title, $paper_abstract, $extra_instruction |
| comparer.txt | $analysis_data |
| generator.txt | $personalization, $analysis_data, $comparison_data |
| reviewer.txt | $report_content, $original_papers |

### Dockerfile
- 基于 `python:3.10-slim`
- 安装系统依赖 + pip install
- HEALTHCHECK `curl -f http://localhost:8000/health`
- CMD `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1`

### 关键约束
- 使用 `safe_substitute` 而非 `substitute`（变量缺失时保留原样）
- Prompt 模板中不硬编码敏感信息
- Dockerfile 使用明确版本标签，不用 `latest`
- 模板加载失败不阻塞服务启动

## 文件清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | `Veritas/ai-service/app/services/prompt_manager.py` | PromptManager 实现 |
| 新增 | `Veritas/ai-service/prompts/coordinator.txt` | 协调者 Prompt |
| 新增 | `Veritas/ai-service/prompts/retriever.txt` | 检索 Prompt |
| 新增 | `Veritas/ai-service/prompts/analyzer.txt` | 分析 Prompt |
| 新增 | `Veritas/ai-service/prompts/comparer.txt` | 对比 Prompt |
| 新增 | `Veritas/ai-service/prompts/generator.txt` | 生成 Prompt |
| 新增 | `Veritas/ai-service/prompts/reviewer.txt` | 审核 Prompt |
| 新增 | `Veritas/ai-service/Dockerfile` | Docker 镜像构建 |
| 新增 | `Veritas/ai-service/tests/test_prompt_manager.py` | PromptManager 测试 |
| 新增 | `Veritas/ai-service/tests/test_integration.py` | 集成测试 |
| 修改 | `Veritas/ai-service/app/core/events.py` | 加载 PromptManager |
| 修改 | `Veritas/ai-service/app/main.py` | health 添加 prompts 状态 |

## 验收标准
- [ ] `PromptManager` 提供 `load_templates` / `get_prompt` / `list_templates` 三个方法
- [ ] 加载 6 个 Agent Prompt 模板
- [ ] `get_prompt()` 使用 `safe_substitute` 替换变量
- [ ] `analyzer.txt` 包含 5 维度提取 + JSON 输出格式
- [ ] `generator.txt` 包含 5 章节综述结构 + 引用标注
- [ ] 6 个模板均使用 `$variable` 格式
- [ ] Dockerfile 基于 `python:3.10-slim`，含 HEALTHCHECK
- [ ] `events.py` 启动时加载 PromptManager
- [ ] `/health` 包含 `prompts` 状态字段
- [ ] 单元测试和集成测试全部通过
- [ ] Prompt 模板中无硬编码敏感信息
