# 技术教学文档

## 开发思路

### 需求分析过程
本次开发涉及3个连续任务（Task18/19/20），属于FM3里程碑（论文分析+对比页面可用）的前端核心功能：
- Task18需要从空壳占位实现完整的PaperDetailView论文详情页
- Task19需要创建可复用的AnalysisCard和PlainExplanation组件，并替换Task18中的5维度占位文本
- Task20需要增强sessionStore，将PaperDetailView中的内联分析逻辑抽取到Store层统一编排

三个任务存在严格的依赖关系：Task18先实现完整页面（含5维度占位）→ Task19创建组件并替换占位 → Task20重构分析逻辑到Store层。这种"先实现后重构"的策略确保了每个阶段都有可验证的交付物。

### 技术选型考虑
1. **递归setTimeout vs setInterval**：选择递归setTimeout，因为：
   - 每次轮询完成后才设置下一次定时器，避免并发问题
   - 便于在任意步骤中断轮询链
   - 清理更简单，只需clearTimeout一次

2. **手动EventSource vs useSSE composable**：在sessionStore中选择手动创建EventSource，因为：
   - Vue composable依赖组件setup上下文，不能在Pinia Store中直接使用
   - Store层需要管理SSE连接的生命周期（connect/disconnect/reconnect）
   - 参考useSSE的实现逻辑，在Store中重新实现EventSource连接

3. **AnalysisCard纯展示+事件上行**：不直接操作Store/API，因为：
   - 保证组件可复用性（PaperDetailView和CompareView均可使用）
   - 遵循"Props Down / Events Up"的Vue组件通信原则
   - 数据获取由父组件负责，组件只负责渲染和事件通知

### 架构设计思路
```
数据流：
用户点击[触发AI分析] → PaperDetailView.handleAnalyze()
  → sessionStore.startAnalysis(topic, paperId)
    → createSession(topic) → analysisApi.analyzePaper({paperId})
    → pollAnalysisStatus(analysisId) [3s递归轮询]
    → connectAgentStream(analysisId) [SSE实时推送]
    → completed → analysisResults Map缓存
  → PaperDetailView渲染AnalysisCard
    → AnalysisCard读取analysis prop渲染5维度
    → 用户点击[生成综述] → emit上行 → PaperDetailView路由跳转
```

### 遇到的问题及解决方案

**问题1：TypeScript类型错误 — API返回类型缺失**
- 现象：`analysisApi.analyzePaper`和`analysisApi.getStatus`缺少返回类型注解，导致TypeScript推断为`AxiosResponse`
- 解决：为所有analysisApi方法添加`Promise<AnalysisResult>`返回类型注解

**问题2：模板中window不可访问**
- 现象：`@click="window.open(url, '_blank')"` 在Vue模板中报错，因为模板上下文不包含window
- 解决：封装`openPdf(url)`方法，在方法中调用`window.open()`

**问题3：EventSource在jsdom测试环境中未定义**
- 现象：集成测试中`new EventSource(url)`抛出ReferenceError
- 解决：创建MockEventSource类，使用`vi.stubGlobal('EventSource', MockEventSource)`全局替换

**问题4：轮询测试超时**
- 现象：3秒间隔的轮询导致测试超过5秒默认超时
- 解决：使用`vi.useFakeTimers()` + `vi.advanceTimersByTimeAsync(3000)`模拟时间推进

## 实现步骤

1. **Task18 — PaperDetailView完整实现**：从空壳占位替换为完整论文详情页，包含返回导航、论文元数据卡片（标题/作者/年份/会议/摘要/关键词/引用数/PDF链接）、收藏操作、触发AI分析按钮、AI分析区域四态展示、通俗解释条件渲染、Loading/Empty/Error三态

2. **Task19 — AnalysisCard + PlainExplanation组件**：创建PlainExplanation纯展示组件（el-alert包裹通俗解释），创建AnalysisCard 5维度分析卡片组件（DIMENSIONS常量+降级标签+AI标注+操作按钮emit上行），将PaperDetailView的5维度占位替换为AnalysisCard集成

3. **Task20 — sessionStore增强 + 全链路测试**：增强sessionStore添加startAnalysis/pollAnalysisStatus/connectAgentStream/disconnectSSE/cleanup方法和analysisStatus/analysisError/isAnalyzing等状态，重构PaperDetailView使用sessionStore.startAnalysis()替代内联逻辑，创建全链路集成测试验证注册→登录→搜索→详情→分析完整数据流转

4. **类型修复**：补全analysisApi返回类型注解，修复window.open模板访问问题

5. **测试修复**：MockEventSource解决jsdom环境限制，vi.useFakeTimers解决轮询超时

## 解决了什么问题

### 核心问题描述
1. 论文详情页从空壳到完整功能页面的缺失
2. 5维度分析结果缺乏组件化展示，无法复用
3. 分析流程逻辑散落在View组件中，无法统一管理和复用
4. 缺少全链路集成测试验证数据流转

### 解决方案对比
| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| 5维度占位文本（Task18临时方案） | 快速实现 | 不可复用、样式不统一 | ✅ 临时 |
| AnalysisCard组件化（Task19） | 可复用、BEM规范 | 需额外组件开发 | ✅ 最终 |
| 内联轮询逻辑（Task18临时方案） | 简单直接 | 逻辑散落、不可复用 | ✅ 临时 |
| sessionStore编排（Task20） | 统一管理、可复用 | Store复杂度增加 | ✅ 最终 |
| useSSE composable | 封装完善 | 依赖组件上下文，不能在Store中使用 | ❌ |
| 手动EventSource | Store中可用 | 需手动管理重连 | ✅ 最终 |

### 最终方案的优势
- 组件化：AnalysisCard/PlainExplanation可在PaperDetailView和CompareView中复用
- 统一编排：sessionStore.startAnalysis()封装完整分析流程，View组件只需一行调用
- 状态机：analysisStatus 7阶段状态机清晰跟踪分析进度
- 可测试：全链路集成测试覆盖完整数据流转

## 变更内容

### 新增文件
- `src/components/analysis/AnalysisCard.vue` — 5维度分析卡片业务组件，Props(analysis, showPlainExplanation) + Emits(generate-report, select-compare)
- `src/components/analysis/PlainExplanation.vue` — 通俗解释纯展示组件，Props(content)
- `src/__tests__/integration/fullChain.spec.ts` — 全链路集成测试（6用例）

### 修改文件
- `src/views/PaperDetailView.vue` — 空壳占位→完整论文详情页→AnalysisCard集成→sessionStore.startAnalysis()重构
- `src/stores/sessionStore.ts` — 新增analysisStatus/analysisError/pollTimer/eventSource/reconnectAttempts状态，新增startAnalysis/pollAnalysisStatus/connectAgentStream/disconnectSSE/cleanup方法，新增isAnalyzing/isAnalysisCompleted/isAnalysisFailed Getters
- `src/api/analysis.ts` — 补全analyzePaper/comparePapers/generateReport/getStatus的`Promise<AnalysisResult>`返回类型注解

### 配置变更
- 无配置文件变更

## 关键技术点

### 1. Vue3组件通信：Props Down / Events Up
AnalysisCard是纯展示+事件上行组件的典型实践：
- 父组件通过Props传入数据（analysis, showPlainExplanation）
- 子组件通过Emits上行事件（generate-report, select-compare）
- 子组件不直接操作Store或API，保证可复用性

### 2. Pinia Store中的异步流程编排
sessionStore.startAnalysis()是一个5阶段异步编排方法：
- 每个阶段更新analysisStatus，便于UI展示进度
- 任何阶段失败统一设置failed状态
- cleanup()方法在startAnalysis开始时自动调用，确保清理上一次状态

### 3. 递归setTimeout轮询模式
```typescript
function poll(analysisId: string, attempt = 0): Promise<AnalysisResult> {
  if (attempt >= MAX) return reject(new Error('超时'))
  pollTimer.value = setTimeout(async () => {
    const result = await getStatus(analysisId)
    if (result.status === 'completed') return resolve(result)
    if (result.status === 'failed') return reject(new Error('失败'))
    poll(analysisId, attempt + 1).then(resolve).catch(reject)
  }, 3000)
}
```
优势：每次轮询完成后才设置下一次，避免并发；清理只需clearTimeout一次。

### 4. Pinia Store中手动实现EventSource
由于Vue composable不能在Pinia Store中使用，需手动实现SSE连接：
- 创建EventSource实例并存储到ref
- addEventListener监听agent_state_update和analysis_completed事件
- onerror实现自动重连（3s/5次）
- disconnectSSE()关闭连接并重置重连计数

### 5. 测试中的Mock策略
- `vi.mock()`模拟API模块，避免真实网络请求
- `vi.stubGlobal('EventSource', MockEventSource)`替换全局EventSource
- `vi.useFakeTimers()` + `vi.advanceTimersByTimeAsync()`控制轮询时间
- `as never`绕过TypeScript类型检查的mock类型不匹配

## 经验总结

### 开发过程中的收获
1. **渐进式开发策略有效**：先实现完整功能（Task18含占位），再组件化（Task19替换占位），最后重构到Store层（Task20），每个阶段都有可验证的交付物
2. **API返回类型注解的重要性**：Axios封装的API方法必须显式声明返回类型，否则TypeScript推断为AxiosResponse导致类型错误
3. **Pinia Store中不能使用composable**：这是一个重要的架构约束，需要在Store中手动实现composable的逻辑

### 踩过的坑及如何避免
1. **Vue模板中不能直接访问window**：封装方法调用window API
2. **jsdom中没有EventSource**：测试需要MockEventSource，使用vi.stubGlobal全局替换
3. **轮询测试超时**：使用vi.useFakeTimers控制时间，避免真实等待
4. **require()在ESM中不可用**：sessionStore中使用import而非require导入agentStore

### 最佳实践建议
1. API封装时始终添加返回类型注解：`Promise<ResponseType>`
2. 组件设计遵循"纯展示+事件上行"原则，不直接操作Store/API
3. 异步轮询使用递归setTimeout而非setInterval
4. SSE连接在Store中手动实现EventSource，不依赖composable
5. 集成测试使用vi.useFakeTimers + vi.stubGlobal处理定时器和浏览器API
6. 渐进式开发：先实现→再组件化→最后重构，确保每步可验证
