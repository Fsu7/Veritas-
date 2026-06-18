# Task 46：Agent 流程回放功能

> **里程碑**：FM5 功能完善与UI打磨（Week 11 Day 4）
> **优先级**：P2
> **涉及模块**：F1.5 Agent 可视化模块

---

## 一、任务概述

实现 Agent 流程回放功能。当前 AgentFlowView 仅支持实时 SSE 连接展示 Agent 协同过程，无历史回放能力。

**目标**：新增 useReplay composable 封装回放控制（播放/暂停/进度条/倍速 1x/2x/4x），agentStore 新增 replayStates/replayFrames/loadReplayData，AgentFlowView 增加"回放模式"切换+回放控制条，支持从已完成分析的 agentStates 历史数据回放。

---

## 二、涉及模块

| 模块 | 路径 | 职责 |
|------|------|------|
| useReplay | `src/composables/useReplay.ts` | 回放控制器（新建） |
| agentStore | `src/stores/agentStore.ts` | Agent 状态（新增回放状态） |
| AgentFlowView | `src/views/AgentFlowView.vue` | 可视化页（增加回放模式） |
| analysisApi | `src/api/analysis.ts` | 分析 API（新增 getAgentHistory） |
| agent types | `src/types/agent.ts` | 类型（新增 ReplayFrame） |
| AgentFlowChart | `src/components/agent/AgentFlowChart.vue` | 流程图（复用，响应式更新） |
| AgentStatusPanel | `src/components/agent/AgentStatusPanel.vue` | 状态面板（复用） |
| IntermediateResult | `src/components/agent/IntermediateResult.vue` | 中间结果（复用） |
| TimeStats | `src/components/agent/TimeStats.vue` | 耗时统计（复用） |

---

## 三、文件变更表

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| create | `Veritas/frontend/src/composables/useReplay.ts` | 新建回放控制器 composable |
| modify | `Veritas/frontend/src/stores/agentStore.ts` | 新增 replayFrames/loadReplayData/isReplayMode |
| modify | `Veritas/frontend/src/views/AgentFlowView.vue` | 增加回放模式切换+回放控制条 |
| modify | `Veritas/frontend/src/api/analysis.ts` | 新增 getAgentHistory（或复用 getResult） |
| modify | `Veritas/frontend/src/types/agent.ts` | 新增 ReplayFrame 类型 |

---

## 四、功能要求

| 编号 | 描述 | 优先级 |
|------|------|--------|
| FR-001 | useReplay 封装回放控制（play/pause/seek/setSpeed/progress/isPlaying） | P0 |
| FR-002 | agentStore.loadReplayData 从 analysisResult.agentStates 构建回放帧 | P0 |
| FR-003 | AgentFlowView 增加"回放模式"切换按钮 | P0 |
| FR-004 | 回放控制条：播放/暂停+进度条+倍速 1x/2x/4x+时间显示 | P1 |
| FR-005 | 回放时 4 个子组件同步更新（通过 agentStore.agentStates） | P0 |
| FR-006 | 回放结束自动暂停在最后一帧；拖拽进度条跳转；倍速实时切换 | P1 |

---

## 五、关键技术约束

1. **分层规范**：useReplay 通过 agentStore 更新状态，不直接调用 analysisApi
2. **内存管理**：pause/组件卸载时必须 clearInterval（防止内存泄漏）
3. **模式互斥**：回放模式与实时 SSE 模式互斥（切换时停止另一种）
4. **CSS 变量**：使用 `var(--spacing-md)` 等 CSS 变量
5. **帧数据来源**：从 analysisResult.agentStates 构建 ReplayFrame[]（按 timestamp 排序）

---

## 六、验收检查点

- [ ] AC-001：可加载已完成分析的 Agent 历史数据 — manual_test
- [ ] AC-002：回放支持播放/暂停 — manual_test
- [ ] AC-003：回放支持拖拽进度条跳转 — manual_test
- [ ] AC-004：回放支持 1x/2x/4x 倍速切换 — manual_test
- [ ] AC-005：回放时 4 个子组件同步更新 — manual_test
- [ ] AC-006：回放结束后自动暂停在最后一帧 — automated_test
- [ ] AC-007：切换回实时模式时正确停止回放并恢复 SSE 连接 — manual_test
- [ ] AC-008：所有新增/修改的代码通过 lint 和 build 验证 — code_review

---

## 七、验证命令

```bash
cd Veritas/frontend && npm run test -- --run useReplay AgentFlowView
cd Veritas/frontend && npm run lint
cd Veritas/frontend && npm run build
```

---

## 八、参考文档

- `AGENTS.md` — 项目全景上下文与前端约束
- `docs/frontend/前端模块系统架构文档.md` — 前端架构规范、F1.5 Agent 可视化模块设计
- `docs/frontend/前端模块项目里程碑文档.md` — FM5 里程碑任务分解（Week 11 Day 4）
- `docs/开发规范文档.md` — 前端编码规范
- `docs/架构决策记录(ADR).md` — 架构决策
