# Task 05: Pinia Store骨架（4个Store基础结构）

## 任务概述

| 项目 | 内容 |
|------|------|
| **版本** | v0.1 |
| **里程碑** | M1 / FM1：项目骨架与基础设施就绪 |
| **涉及层级** | 前端 (frontend) |
| **功能编号** | F1.1, F1.2, F1.3, F1.4, F1.5 |

## 需求描述

创建4个Pinia Store基础结构骨架（userStore、paperStore、sessionStore、agentStore），使用Composition API setup store风格，定义State/Getters/Actions基础框架。

## 影响范围

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `src/stores/userStore.ts` | 用户Store：Token管理+login/logout/fetchProfile/saveProfile |
| 新增 | `src/stores/paperStore.ts` | 论文Store：searchPapers/togglePaperSelection/toggleFavorite |
| 新增 | `src/stores/sessionStore.ts` | 会话Store：createSession/fetchAnalysisResult |
| 新增 | `src/stores/agentStore.ts` | Agent Store：agentStates/updateAgentState/resetStates/progress |
| 修改 | `src/main.ts` | 注册pinia插件 |

## 4个Store设计

### userStore

| 类型 | 成员 | 说明 |
|------|------|------|
| State | token, userId, username, profile | Token从localStorage初始化 |
| Getter | isLoggedIn, hasProfile | 计算属性 |
| Action | login, logout, fetchProfile, saveProfile | 调用userApi |

### paperStore

| 类型 | 成员 | 说明 |
|------|------|------|
| State | searchResults, selectedPapers, favorites, filters, currentQuery, totalResults, currentPage, pageSize | 搜索和选择状态 |
| Getter | selectedPaperIds, filteredResults | 计算属性 |
| Action | searchPapers, togglePaperSelection(≤5), toggleFavorite | 调用paperApi |

### sessionStore

| 类型 | 成员 | 说明 |
|------|------|------|
| State | currentSessionId, currentAnalysisId, analysisResults(Map) | 会话和分析状态 |
| Action | createSession, fetchAnalysisResult | 调用sessionApi/analysisApi |

### agentStore

| 类型 | 成员 | 说明 |
|------|------|------|
| State | agentStates(Record), flowData, isConnected, currentAnalysisId | Agent执行状态 |
| Getter | agentStatesList, activeAgents, progress | 计算属性 |
| Method | getAgentState, updateAgentState, resetStates | 状态操作 |

## 实现要求

- 全部使用Composition API setup store风格
- 按业务域划分，禁止全局大Store
- 异步操作在Actions中，不放组件内
- Token持久化到localStorage，logout时清除
- paperStore论文选择最多5篇

## 验收标准

- [ ] userStore：Token管理+login/logout/fetchProfile/saveProfile完整
- [ ] paperStore：searchPapers/togglePaperSelection(≤5)/toggleFavorite完整
- [ ] sessionStore：createSession/fetchAnalysisResult完整
- [ ] agentStore：updateAgentState/getAgentState/resetStates/progress完整
- [ ] 4个Store全部使用setup store风格
- [ ] Token持久化到localStorage，logout清除
- [ ] main.ts注册pinia插件
- [ ] Store按业务域划分，无全局大Store

## 验证命令

```bash
cd Veritas/frontend && npx vue-tsc --noEmit
cd Veritas/frontend && npm run dev
```
