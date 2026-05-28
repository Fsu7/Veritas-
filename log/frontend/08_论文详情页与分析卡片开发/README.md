# 论文详情页与分析卡片开发

## 功能描述
- 解决了论文详情页从空壳占位到完整功能页面的问题，实现了论文元数据展示、收藏操作、AI分析触发、分析结果展示的完整用户流程
- 实现了AnalysisCard 5维度结构化分析卡片组件和PlainExplanation通俗解释组件，支持降级标签显示、通俗解释条件渲染、操作按钮上行
- 增强了sessionStore会话状态管理，添加了分析流程编排方法（startAnalysis）、轮询方法（pollAnalysisStatus）、SSE连接方法（connectAgentStream）和清理方法（cleanup）
- 实现了注册→登录→检索→分析全链路联调验证测试
- 业务价值：完成FM3里程碑（论文分析+对比页面可用）的前端核心功能，用户可以查看论文详情、触发AI分析、查看5维度分析结果

## 实现逻辑

### 修改的核心文件列表
| 文件 | 操作 | 说明 |
|------|------|------|
| `src/views/PaperDetailView.vue` | 修改→修改→修改 | Task18完整实现→Task19替换占位为AnalysisCard→Task20重构使用sessionStore |
| `src/components/analysis/AnalysisCard.vue` | 新建 | 5维度分析卡片业务组件 |
| `src/components/analysis/PlainExplanation.vue` | 新建 | 通俗解释纯展示组件 |
| `src/stores/sessionStore.ts` | 修改 | 增强分析流程编排、轮询、SSE、清理 |
| `src/api/analysis.ts` | 修改 | 补全API返回类型注解 |
| `src/__tests__/integration/fullChain.spec.ts` | 新建 | 全链路集成测试 |

### 使用的设计模式
- **组件化模式**：AnalysisCard和PlainExplanation为纯展示+事件上行组件，不直接操作Store/API，保证可复用性
- **状态机模式**：sessionStore.analysisStatus跟踪7个阶段（idle→creating_session→starting_analysis→polling→connecting_sse→completed/failed）
- **递归setTimeout轮询**：替代setInterval，便于控制清理和超时保护
- **手动EventSource**：在Pinia Store中直接创建EventSource，避免composable在Store中的使用限制
- **BEM命名规范**：所有CSS类名遵循Block__Element--Modifier规范

### 关键代码逻辑说明

**1. PaperDetailView三态展示**
- Loading态：el-skeleton骨架屏
- Error态：el-result + 重试按钮
- 正常态：论文元数据卡片 + AI分析区域（未分析/分析中/分析完成/分析失败四态）

**2. AnalysisCard 5维度渲染**
- DIMENSIONS常量数组定义5个维度（key/label/icon）
- v-for遍历渲染，每个维度读取analysis.result.analysis[dim.key]
- 降级标签：degraded=true时显示el-tag "部分降级" + degradedReason
- 通俗解释：showPlainExplanation prop控制，PlainExplanation子组件条件渲染
- 操作按钮：emit上行generate-report和select-compare事件

**3. sessionStore.startAnalysis编排流程**
```
cleanup() → creating_session → createSession(topic) → starting_analysis
→ analysisApi.analyzePaper({paperId}) → polling → pollAnalysisStatus + connectAgentStream
→ completed → 返回最终AnalysisResult
```

**4. pollAnalysisStatus递归轮询**
- 3秒间隔，最大60次（3分钟超时）
- completed → 缓存到analysisResults Map
- failed → 设置analysisError
- 使用setTimeout递归而非setInterval

**5. connectAgentStream SSE连接**
- 手动创建EventSource（不使用useSSE composable）
- 监听agent_state_update事件 → agentStore.updateAgentState
- 监听analysis_completed事件 → disconnectSSE + analysisStatus='completed'
- onerror → 自动重连（3s/5次）

## 接口变更

### Request — 触发分析
```json
POST /api/analysis/paper
{
  "paperId": "paper_001"
}
```

### Response — 分析结果
```json
{
  "code": 200,
  "data": {
    "analysisId": "analysis_001",
    "status": "completed",
    "type": "paper_analysis",
    "result": {
      "analysis": {
        "researchQuestion": "研究问题内容",
        "coreMethod": "核心方法内容",
        "keyExperiments": "主要实验内容",
        "coreFindings": "核心结论内容",
        "limitations": "局限性内容",
        "plainExplanation": "通俗解释内容（可选）"
      }
    },
    "degraded": false,
    "degradedReason": null
  }
}
```

### SSE事件格式
```
event: agent_state_update
data: {"agentName": "retriever", "status": "running", "progress": 0.6, "intermediateResult": "找到15篇相关论文"}

event: analysis_completed
data: {"analysisId": "analysis_001", "status": "completed"}
```

## 测试结果
- 测试场景1：TypeScript类型检查（vue-tsc --noEmit）→ 0错误 ✅
- 测试场景2：全量单元测试（vitest run）→ 7文件/66用例全部通过 ✅
- 测试场景3：全链路集成测试（注册→登录→搜索→详情→分析）→ 6用例全部通过 ✅
- 测试场景4：sessionStore分析状态转换（idle→creating_session→starting_analysis→polling→completed）→ 通过 ✅
- 测试场景5：sessionStore分析失败处理 → 通过 ✅
- 测试场景6：sessionStore cleanup清理 → 通过 ✅
- 是否通过：是

## 相关文件
- `Veritas/frontend/src/views/PaperDetailView.vue` — 论文详情页
- `Veritas/frontend/src/components/analysis/AnalysisCard.vue` — 分析卡片组件
- `Veritas/frontend/src/components/analysis/PlainExplanation.vue` — 通俗解释组件
- `Veritas/frontend/src/stores/sessionStore.ts` — 会话状态管理（增强）
- `Veritas/frontend/src/api/analysis.ts` — 分析API（类型注解补全）
- `Veritas/frontend/src/__tests__/integration/fullChain.spec.ts` — 全链路集成测试
