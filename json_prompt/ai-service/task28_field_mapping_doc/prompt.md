# AM3-5 — 请求/响应格式兼容性验证 + 字段映射文档

> **里程碑**: AM3：API完善与Java对接（Week 5-6）
> **版本**: v0.3
> **涉及层级**: python_ai_service + java_backend + frontend
> **功能编号**: F3.5.1~F3.5.5 + F2.5

---

## 1. 任务目标

基于 task27 联调测试结果，产出 1 份**三方契约文档**《Java↔Python AI服务字段映射与契约文档》，供前端 / Java / Python 三端共同查阅。

---

## 2. 涉及文件

| 操作 | 路径 | 说明 |
|------|------|------|
| 新增 | `Veritas/ai-service/docs/FIELD_MAPPING.md` | 字段映射与契约文档（≥300 行） |
| 新增 | `Veritas/ai-service/tests/test_field_mapping_consistency.py` | 字段映射一致性自动验证 |

---

## 3. 文档结构

```markdown
# Java ↔ Python AI 服务字段映射与契约文档

## 1. 概述
- 文档目的、三方使用方式

## 2. 5 个核心端点契约（每个端点一节）
### 2.1 POST /api/agent/analyze
### 2.2 POST /api/agent/analyze/stream (SSE)
### 2.3 POST /api/search
### 2.4 POST /api/search/hybrid
### 2.5 GET /api/search/suggest
### 2.6 GET /api/model/status
### 2.7 GET /health
（每节：URL/方法/Request Headers/Request Body/Response Body/Status Codes/Errors/Curl 示例）

## 3. 字段命名映射表（≥30 行）
| Java (camelCase) | Python (snake_case) | JSON (camelCase) | 类型 | 说明 |

## 4. 枚举映射表
| 枚举类 | Java | Python | JSON | 取值 |

## 5. SSE 事件清单（6 个事件）
| Event Name | 触发时机 | data payload |

## 6. ChromaDB 字段映射
| metadata 字段 | 类型 | 来源 |

## 7. 错误码体系（≥6 行）
| code | 异常类 | 触发场景 | 前端处理建议 |

## 8. 降级语义
## 9. 附录：完整 curl 示例
```

---

## 4. 字段映射表示例

| Java (camelCase) | Python (snake_case) | JSON (camelCase) | 类型 | 说明 |
|------------------|---------------------|------------------|------|------|
| `educationLevel` | `education_level` | `educationLevel` | str | 学历层次 |
| `researchField` | `research_field` | `researchField` | str | 研究方向 |
| `knowledgeLevel` | `knowledge_level` | `knowledgeLevel` | str | 知识水平 |
| `preferredStyle` | `preferred_style` | `preferredStyle` | str | 偏好风格 |
| `paperIds` | `paper_ids` | `paperIds` | List[str] | 论文ID列表 |
| `analysisType` | `analysis_type` | `analysisType` | str | 分析类型 |
| `analysisId` | `analysis_id` | `analysisId` | str | 任务ID |
| `userId` | `user_id` | `userId` | str | 用户ID |
| `agentName` | `agent_name` | `agentName` | str | Agent名称 |
| `intermediateResult` | `intermediate_result` | `intermediateResult` | str | 中间结果 |
| `durationMs` | `duration_ms` | `durationMs` | int | 耗时(毫秒) |
| `embeddingDimension` | `embedding_dimension` | `embeddingDimension` | int | 向量维度 |
| `activeLlmProvider` | `active_llm_provider` | `activeLlmProvider` | str | 活跃LLM Provider |
| `providerCandidates` | `provider_candidates` | `providerCandidates` | List[str] | 可用 Provider |
| `chromaPaperCount` | `chroma_paper_count` | `chromaPaperCount` | int | 论文数量 |
| `gpuMemoryUsed` | `gpu_memory_used` | `gpuMemoryUsed` | str | GPU 显存 |
| `llmProviderCount` | `llm_provider_count` | `llmProviderCount` | int | Provider 数量 |
| `degradedReason` | `degraded_reason` | `degradedReason` | str | 降级原因 |
| `errorCode` | `error_code` | `errorCode` | int | 错误码 |
| `errorMessage` | `error_message` | `errorMessage` | str | 错误信息 |
| `userProfile` | `user_profile` | `userProfile` | object | 用户画像 |
| `agentStates` | `agent_states` | `agentStates` | List | Agent状态 |
| `searchService` | `search_service` | `searchService` | str | SearchService 状态 |
| `createdAt` | `created_at` | `createdAt` | str | 创建时间 |
| `updatedAt` | `updated_at` | `updatedAt` | str | 更新时间 |

---

## 5. 错误码表

| code | 异常类 | 触发场景 | 前端处理建议 |
|------|--------|---------|------------|
| 200 | - | 成功 | 正常处理 |
| 408 | AgentTimeoutException | Agent 超时 30s | 提示用户重试 |
| 422 | ValidationException / RequestValidationError | 请求参数校验失败 | 字段级错误提示 |
| 429 | RateLimitException | 限流（未来扩展） | 提示用户稍后重试 |
| 500 | AIServiceException | 工作流执行异常 | 降级提示 |
| 503 | LLMException / VectorStoreException / ModelNotLoadedException | 模型/服务未就绪 | 提示后端维护中 |

---

## 6. 验收标准

- [ ] 文档行数 ≥ 300，含 7 个端点章节
- [ ] 字段映射表 ≥ 30 行（Java/Python/JSON 三列对齐）
- [ ] 枚举映射表 4 个枚举
- [ ] SSE 事件清单 6 个事件
- [ ] 错误码表 ≥ 6 行
- [ ] ≥ 5 个 curl 示例
- [ ] 文档不暴露 API Key / 内部 IP
- [ ] 自动验证脚本 20+ 字段断言全部通过

---

## 7. 参考文档

- [AI服务架构 §4.4 + §14 + §附录B](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块系统架构文档.md)
- [信息架构文档(IA)](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/信息架构文档(IA).md)
- [Java 端 PythonAIClient 契约](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/json_prompt/backend/task19_python_ai_client/prompt.md)

---

## 8. 下一步建议

- 任务 6（task29）将基于本文档做错误处理联调 + 降级测试
- 建议将本文档链接到 `AGENTS.md` 的 "渐进式加载" 索引
- 文档变更需同步通知前端（避免 Vue3 store 类型不匹配）
