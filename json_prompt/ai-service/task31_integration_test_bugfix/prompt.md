# AM3-8 — 集成测试 + Bug修复

> **里程碑**: AM3：API完善与Java对接（Week 5-6）
> **版本**: v0.3
> **涉及层级**: python_ai_service + java_backend + frontend + data_layer + infra（全栈）
> **功能编号**: F3.5 + F3.1 + F3.3

---

## 1. 任务目标

AM3 阶段收尾：
1. **一键集成测试**：执行 task24~task30 全部 40+ 用例
2. **性能基线**：测量 4 项关键指标 + 3 类降级时长
3. **Bug 修复**：本阶段发现的所有 P0/P1 Bug 必须修复
4. **AM3 测试报告**：8 章节 + 12 项 AM3 检查点对应结果
5. **AM4 任务建议**：基于测试发现，提出 AM4 任务规划

---

## 2. 涉及文件

| 操作 | 路径 | 说明 |
|------|------|------|
| 新增 | `Veritas/ai-service/tests/test_integration_am3.py` | 集成测试主类（pytest 集合） |
| 新增 | `Veritas/ai-service/tests/performance/test_perf_baseline.py` | 性能基线测试 |
| 新增 | `Veritas/ai-service/docs/AM3_TEST_REPORT.md` | AM3 阶段测试报告 |
| 新增 | `Veritas/ai-service/docs/AM3_BUGFIX_LOG.md` | Bug 修复日志 |

---

## 3. 性能基线指标

| 指标 | 目标 | 测量方法 |
|------|------|---------|
| `/health` 响应时间 | < 100ms (P95) | pytest-benchmark |
| `/api/search` 响应时间 | < 3s (P95) | pytest-benchmark |
| `/api/agent/analyze` 响应时间 | < 60s (P95) | pytest-benchmark |
| `/api/agent/analyze/stream` 首事件 | < 2s | SSE 流连接后首个事件耗时 |
| 10 并发 `/analyze` 吞吐 | ≥ 0.2 req/s | asyncio.gather |

**降级时长基线**：

| 场景 | 目标 | 测量方法 |
|------|------|---------|
| LLM Provider 降级 | < 2s | builtin 失败 → api 切换 |
| 单 Agent 超时降级 | < 35s | agent 超时 30s + 跳过 |
| 多 Agent 降级为单 Agent | < 60s | retriever+analyzer 失败 → 仅 generate |

---

## 4. AM3 测试报告结构

```markdown
# AM3 阶段测试报告

## 1. 概述
- 测试时间、Python/Java 版本、测试用例总数

## 2. 测试结果总览
- PASS/FAIL/SKIP 统计
- 折线图（每日通过率）

## 3. 模块覆盖度
| 功能编号 | 测试用例数 | 通过率 |

## 4. 性能基线
| 指标 | 目标 | 实测 P50 | 实测 P95 | 实测 P99 | 达标 |

## 5. 错误码验证
| 错误码 | 触发场景 | 实测状态 |

## 6. Bug 清单（按严重程度）
| Bug ID | 描述 | 严重程度 | 修复状态 |

## 7. AM3 检查点（12 项）
| 检查点 | 状态 | 实测证据 |

## 8. AM4 任务建议
（基于 AM3 测试发现，给出 AM4 任务优先级）
```

---

## 5. AM3 检查点（12 项，对应里程碑文档 §5.4）

| # | 检查点 | 状态 |
|---|--------|------|
| 1 | 请求校验：空 topic 返回 422 | ⬜ |
| 2 | 统一响应：{code, message, data, timestamp} 格式 | ⬜ |
| 3 | SSE 推送：Agent 状态流正常 | ⬜ |
| 4 | 健康检查：/health 三组件状态 | ⬜ |
| 5 | 模型状态：/api/model/status 详情 | ⬜ |
| 6 | Java 调用：成功 POST /api/agent/analyze | ⬜ |
| 7 | 字段转换：camelCase ↔ snake_case | ⬜ |
| 8 | 响应解析：Java 正确解析 JSON | ⬜ |
| 9 | 错误处理：统一格式错误响应 | ⬜ |
| 10 | 降级：Python 不可用时 Java 收到降级提示 | ⬜ |
| 11 | SSE 事件格式：event + data | ⬜ |
| 12 | 超时：30s 超时正常返回 | ⬜ |

---

## 6. Bug 严重程度分级

| 级别 | 描述 | 修复 SLA |
|------|------|---------|
| P0-致命 | 系统不可用 / 数据丢失 / 安全漏洞 | AM3 内立即修复 |
| P1-严重 | 核心功能异常 / API 契约不一致 | AM3 内修复 |
| P2-一般 | 非核心功能异常 / 性能略超基线 | AM4 修复 |
| P3-轻微 | UI 瑕疵 / 日志格式 / 文档缺失 | 后续迭代修复 |

---

## 7. AM4 任务建议（基于 AM3 测试结果）

| 任务 | 优先级 | 触发条件 |
|------|--------|---------|
| CoordinatorAgent 协调者 | P0 | task25 SSE 流需 coordinator 节点 |
| ComparerAgent 对比 | P0 | 性能基线显示分析耗时 15s，对比可优化 |
| ReviewerAgent 审核 | P1 | 综述质量待审核 |
| 完整 6-Agent 工作流 | P0 | AM3 已有 3-Agent 基础 |
| 降级机制完善 | P1 | 9 场景已有 8 通过 |
| SSE 完善（AM4） | P0 | 已有 keep-alive/Last-Event-ID |

---

## 8. 验收标准

- [ ] task24~task30 全部测试 40+ 用例 PASS
- [ ] 4 项性能基线达标（health <100ms / search <3s / analyze <60s / stream 首事件 <2s）
- [ ] 10 并发 `/analyze` 吞吐 ≥ 0.2 req/s
- [ ] 3 类降级时长基线测量完成
- [ ] `AM3_BUGFIX_LOG.md` 记录所有 Bug + 修复状态，P0/P1 全部修复
- [ ] `AM3_TEST_REPORT.md` 含 8 章节 + 12 项 AM3 检查点对应结果
- [ ] Java 联调测试 7/7 PASS
- [ ] 测试报告不含 API Key / 内部 IP

---

## 9. 参考文档

- [AI服务里程碑 §5.4 AM3 检查清单](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块项目里程碑文档.md)
- [AI服务里程碑 §5.6 风险与应对](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/docs/ai-service/AI服务模块项目里程碑文档.md)
- [AM4 6-Agent 任务列表](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/json_prompt/ai-service/task22_langgraph_workflow_state_graph/prompt.md)

---

## 10. 下一步建议

- AM4 任务依赖本任务通过：必须所有 P0/P1 Bug 修复后才能进入 AM4
- 建议在 GitHub Actions / GitLab CI 集成 `pytest -m am3`，每次提交自动执行
- 性能基线 JSON 应纳入版本控制，每次发版对比回归
- AM3 完成后，更新 `AGENTS.md` 中 AM3 状态为 ✅
