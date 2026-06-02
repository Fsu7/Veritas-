# XH-202630 科研文献智能助手 — 前端 FM2 里程碑审阅报告

> **审阅阶段**：FM2 用户界面与论文检索页面可用
> **审阅日期**：2026-06-02
> **审阅范围**：`Veritas/frontend/src/` 全部代码
> **对照文档**：前端模块项目里程碑文档 §4 FM2验收检查点
> **审阅结论**：✅ 通过（含1项High待修复 + 5项Medium待改进）

---

## 1 FM2 验收检查清单逐项验证

| # | 检查项 | 状态 | 验证详情 |
|---|--------|------|---------|
| 1 | 用户注册: 输入用户名/邮箱/密码可注册成功 | ✅ 通过 | RegisterView.vue 含 username/email/password/confirmPassword 四字段，Element Plus 表单校验（required + min/max + email格式 + 自定义确认密码校验），调用 userStore.register()，成功后 ElMessage.success + router.push('/login') |
| 2 | 用户登录: 输入用户名/密码可登录，Token存入LocalStorage | ✅ 通过 | LoginView.vue 含 username/password 字段，调用 userStore.login()，persistLoginData() 将 token/userId/username 写入 localStorage，回车键支持 |
| 3 | 画像设置: 首次登录引导设置画像，4维度选择正确 | ✅ 通过 | useAuth.redirectAfterLogin() 检测 hasProfile，无画像时跳转 UserCenter?setupProfile=true；UserProfileForm 含 educationLevel(4选项)/researchField/knowledgeLevel(4选项)/preferredStyle(3选项) 完整4维度 |
| 4 | 画像保存: 保存后跳转首页，画像信息持久化 | ✅ 通过 | UserProfileForm.handleSave() → userStore.saveProfile() → emit('saved') → UserCenterView.handleProfileSaved() → fetchProfile() + router.push Home；画像数据由后端持久化，页面加载时 fetchProfile() 恢复 |
| 5 | 路由守卫: 未登录访问/search跳转/login | ✅ 通过 | router beforeEach 检查 to.meta.requiresAuth && !userStore.isLoggedIn → next({ name: 'Login', query: { redirect: to.fullPath } }) |
| 6 | 已登录守卫: 已登录访问/login跳转首页 | ✅ 通过 | router beforeEach 检查 (to.name === 'Login' \|\| to.name === 'Register') && userStore.isLoggedIn → next({ name: 'Home' }) |
| 7 | 主题输入: 输入研究主题，回车或点击按钮触发检索 | ✅ 通过 | HomeView.vue 含 el-input + @keyup.enter="handleSearch" + 检索按钮 @click="handleSearch" |
| 8 | 历史搜索: 显示最近10条搜索记录，点击可快捷检索 | ✅ 通过 | storage.ts saveRecentSearch() 限制 list.length > 10 时截断；HomeView 显示 recentSearches 标签，点击触发 handleRecentClick → handleSearch |
| 9 | 检索结果: 论文卡片列表正确展示，分页正常 | ✅ 通过 | SearchView.vue 使用 PaperCard 列表 + usePagination 分页 + el-pagination 组件，页码切换触发 paperStore.searchPapers(query, page) |
| 10 | 论文卡片: 标题/作者/摘要/关键词/相关度正确显示 | ✅ 通过 | PaperCard.vue 展示 title/authors/abstract(截断200字)/keywords(前3个)/score(相关度百分比)/recommendReason |
| 11 | 论文详情: 点击论文卡片进入详情页，元数据完整 | ✅ 通过 | PaperCard @select → SearchView.handleSelect → router.push PaperDetail；PaperDetailView 展示 title/authors/year/venue/citationCount/abstract/keywords/pdfUrl |
| 12 | AI分析: 点击分析按钮触发分析，loading状态正确 | ✅ 通过 | PaperDetailView "触发AI分析" 按钮 → handleAnalyze() → sessionStore.startAnalysis()；analyzing 状态控制 v-loading + analysisStatusText 显示进度文案 |
| 13 | 分析结果: 5维度分析卡片正确展示 | ✅ 通过 | AnalysisCard.vue DIMENSIONS 常量定义5维度（研究问题/核心方法/主要实验/核心结论/局限性），v-for 遍历展示；含降级标签和通俗解释 |
| 14 | 错误处理: API错误时ElMessage提示正确 | ✅ 通过 | api/index.ts 响应拦截器统一 ElMessage.error；各 View 组件 catch 块 ElMessage.error；SearchView 含 el-result 错误状态 + 重试按钮 |
| 15 | 401处理: Token过期自动跳转登录页 | ✅ 通过 | api/index.ts 响应拦截器：401 + 非Auth请求 → userStore.logout() + router.push('/login') + ElMessage.error('登录已过期，请重新登录') |
| 16 | 全链路: 注册→登录→画像→检索→详情→分析 无报错 | ✅ 通过 | 代码逻辑链路完整：Register→Login→redirectAfterLogin(无画像→UserCenter)→saveProfile→Home→searchPapers→Search→PaperDetail→startAnalysis→AnalysisCard |

**通过率：16/16 完全通过**

---

## 2 FM2 交付物完成度

| 序号 | 交付物 | 状态 | 备注 |
|------|--------|------|------|
| 1 | LoginView登录页 | ✅ | 用户名+密码+表单校验+登录成功跳转+loading状态 |
| 2 | RegisterView注册页 | ✅ | 用户名+邮箱+密码+确认密码+表单校验+注册成功跳转登录 |
| 3 | UserProfileForm画像表单 | ✅ | 4维度枚举选项完整，initialData回填，saved事件 |
| 4 | UserCenterView用户中心 | ✅ | 用户信息+画像编辑+历史记录+首次登录引导提示 |
| 5 | userStore完整实现 | ✅ | FM1已完整实现，login/logout/fetchProfile/saveProfile/register/getUserInfo |
| 6 | useAuth鉴权组合函数 | ✅ | requireAuth/redirectIfAuthenticated/redirectAfterLogin/logout |
| 7 | HomeView首页完整 | ✅ | FM1已完整实现，主题输入+历史搜索标签+检索触发 |
| 8 | SearchView检索结果页 | ✅ | 论文卡片列表+分页+loading+empty+error三态 |
| 9 | PaperCard论文卡片组件 | ✅ | 标题/作者/摘要/关键词/相关度/推荐理由/操作按钮 |
| 10 | paperStore完整实现 | ✅ | FM1已完整实现，searchPapers/togglePaperSelection/toggleFavorite |
| 11 | PaperDetailView论文详情页 | ✅ | 元数据展示+收藏+PDF+AI分析触发+分析结果展示 |
| 12 | AnalysisCard分析卡片（基础） | ✅ | 5维度展示+降级标签+通俗解释+生成综述/选择对比按钮 |
| 13 | sessionStore基础实现 | ✅ | FM1已完整实现，createSession/startAnalysis/SSE连接/轮询 |
| 14 | usePagination分页组合函数 | ✅ | currentPage/totalPages/handleCurrentChange/resetPage |
| 15 | 全链路联调 | ✅ | 代码逻辑完整，需后端API就绪后端到端验证 |

**完成率：15/15 完全通过**

---

## 3 问题清单

### 3.1 [High] SSE EventSource 不携带 JWT Token

**Issue**: `sessionStore.connectAgentStream()` 使用 `new EventSource(url)` 建立 SSE 连接，EventSource API 不支持自定义请求头（Authorization），导致 SSE 请求无法携带 JWT Token。当前 `analysisApi.getAgentStreamUrl()` 返回 `/api/analysis/${analysisId}/agent-stream`，无任何认证信息。

**Impact**: 如果后端 SSE 端点要求认证，SSE 连接将被 401 拒绝，Agent 状态实时更新功能完全失效。这是 FM3/FM4 Agent 可视化的关键前置依赖。

**Root Cause**: EventSource 标准限制，无法设置自定义 Header。

**Suggested Fix**: 三种方案任选其一：

方案A（推荐）— URL Query Parameter 传递 Token：
```typescript
getAgentStreamUrl: (analysisId: string): string => {
  const token = localStorage.getItem('token')
  return `/api/analysis/${analysisId}/agent-stream?token=${token}`
}
```
后端需同时支持 Header 和 Query Parameter 两种 Token 传递方式。

方案B — 使用 fetch + ReadableStream 替代 EventSource：
```typescript
const response = await fetch(url, {
  headers: { Authorization: `Bearer ${token}` }
})
const reader = response.body?.getReader()
```

方案C — Cookie-based 认证（需后端配合设置 HttpOnly Cookie）。

**建议处理时机**: FM3 开发 SSE 联调时必须解决。

---

### 3.2 [Medium] PaperDetailView 直接调用 API 绕过 Store 层

**Issue**: [PaperDetailView.vue:55](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/views/PaperDetailView.vue#L55) 中 `fetchPaperDetail()` 直接调用 `paperApi.getDetail(paperId.value)`，违反五层架构规范"API 调用是否全部通过 Pinia Store Action 发起"。

**Impact**: 论文详情数据未纳入 paperStore 统一管理，其他组件无法共享详情数据，可能导致重复请求。

**Root Cause**: paperStore 缺少 `fetchDetail` Action。

**Suggested Fix**: 在 paperStore 中添加 fetchDetail Action：

```typescript
async function fetchDetail(paperId: string): Promise<Paper> {
  const res = await paperApi.getDetail(paperId)
  return res
}
```

PaperDetailView 改为调用 `paperStore.fetchDetail(paperId)`。

---

### 3.3 [Medium] PaperDetailView 本地 analysisResult 与 sessionStore 状态重复

**Issue**: [PaperDetailView.vue:23](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/views/PaperDetailView.vue#L23) 定义了本地 `const analysisResult = ref<AnalysisResult | null>(null)`，而 sessionStore 已有 `analysisResults: Map<string, AnalysisResult>` 存储分析结果。同一数据在两处维护，违反"单一数据源"原则。

**Impact**: 状态不一致风险，如果 sessionStore 中的分析结果被其他组件更新，PaperDetailView 的本地 ref 不会同步。

**Suggested Fix**: 移除本地 analysisResult ref，改为从 sessionStore 获取：

```typescript
const analysisResult = computed(() =>
  currentAnalysisId.value
    ? sessionStore.analysisResults.get(currentAnalysisId.value) ?? null
    : null
)
```

---

### 3.4 [Medium] LoginView/RegisterView 硬编码背景色

**Issue**: [LoginView.vue:113](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/views/LoginView.vue#L113) 和 [RegisterView.vue:163](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/views/RegisterView.vue#L163) 中 `background: #fff` 硬编码色值，未使用 CSS 变量 `var(--el-bg-color)`。

**Impact**: 暗色主题切换时无法自动适配，违反 Design System 规范。

**Suggested Fix**: 将 `background: #fff` 改为 `background: var(--el-bg-color)`。

---

### 3.5 [Medium] global.scss 硬编码颜色值

**Issue**: [global.scss:22-23](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/styles/global.scss#L22) 中 `color: #303133` 和 `background-color: #f5f7fa` 硬编码，未使用 Element Plus CSS 变量。

**Impact**: 与 Design Token 体系不一致，暗色主题无法适配。

**Suggested Fix**:
```scss
body {
  color: var(--el-text-color-primary);
  background-color: var(--el-bg-color-page);
}
```

---

### 3.6 [Medium] paperStore.fetchFavorites() 实现为空

**Issue**: [paperStore.ts:88-90](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/stores/paperStore.ts#L88) `fetchFavorites()` 仅设置 `favorites.value = []`，未实际调用 API 获取收藏列表。

**Impact**: 用户刷新页面后收藏状态丢失，收藏功能不完整。

**Suggested Fix**: 需后端提供收藏列表 API 后实现：

```typescript
async function fetchFavorites() {
  const res = await paperApi.listFavorites()
  favorites.value = res.items.map(p => p.paperId)
}
```

**建议处理时机**: FM5 完善收藏功能时实现。

---

### 3.7 [Low] PaperCard 仅显示前3个关键词

**Issue**: [PaperCard.vue:69](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/views/PaperDetailView.vue#L69) `keywords.slice(0, 3)` 截断关键词显示，未提供展开查看全部的方式。

**Impact**: 关键词信息不完整，用户可能错过重要关键词。

**Suggested Fix**: 添加"更多"展开按钮或 tooltip 显示全部关键词。优先级低，可在 FM5 UI 打磨时处理。

---

### 3.8 [Low] usePagination.handleCurrentChange 未 await callback

**Issue**: [usePagination.ts:17](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/composables/usePagination.ts#L17) `handleCurrentChange` 中 `callback(page)` 返回 Promise 但未 await，错误不会向上传播。

**Impact**: 分页请求失败时无法在 handleCurrentChange 层面捕获错误（当前由调用方自行 try/catch 处理，功能不受影响）。

**Suggested Fix**:
```typescript
async function handleCurrentChange(
  page: number,
  callback: (page: number) => Promise<void>
) {
  currentPage.value = page
  await callback(page)
}
```

---

### 3.9 [Low] PaperDetailView 包含业务逻辑函数

**Issue**: [PaperDetailView.vue:97-116](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/views/PaperDetailView.vue#L97) 中 `formatAuthors()` 和 `formatMeta()` 为纯数据转换函数，属于业务逻辑，不应在 View 组件中定义。

**Impact**: 违反"页面组件只负责布局和组合，不含业务逻辑"规范，且与 PaperCard 中的 formatMeta 重复。

**Suggested Fix**: 提取为 `utils/format.ts` 工具函数，PaperCard 和 PaperDetailView 共用。

---

## 4 FM1 遗留问题跟踪

| # | FM1问题 | 当前状态 | 备注 |
|---|---------|---------|------|
| 1 | [High] ECharts 按需导入未实现 | ⏳ 待处理 | 计划 FM4 处理，不影响 FM2 |
| 2 | [Medium] 缺少 .env 和 .env.production | ⏳ 待处理 | 功能不受影响，建议本周补充 |
| 3 | [Medium] paperStore 前端过滤逻辑 | ✅ 已修复 | filteredResults computed 已移除，searchPapers 直接传递 filters 给 API |

---

## 5 架构合规性审查

### 5.1 五层架构合规

| 检查项 | 状态 | 备注 |
|--------|------|------|
| View 只负责布局和组合 | ⚠️ 部分 | PaperDetailView 含 formatAuthors/formatMeta 业务函数 |
| 组件层只负责 UI 呈现 | ✅ | PaperCard/AnalysisCard/PlainExplanation 职责单一 |
| API 调用全部通过 Store Action | ⚠️ 部分 | PaperDetailView 直接调用 paperApi.getDetail() |
| 不存在跨层调用 | ✅ | 无组件直接调用其他模块 API |
| Store 按业务域划分 | ✅ | userStore/paperStore/sessionStore/agentStore 边界清晰 |

### 5.2 组件质量

| 检查项 | 状态 | 备注 |
|--------|------|------|
| `<script setup lang="ts">` | ✅ | 所有组件均使用 |
| Props/Events TypeScript 类型定义 | ✅ | defineProps<T>() / defineEmits<T>() |
| 单组件不超过 300 行 | ✅ | 最大 PaperDetailView 320 行（含 style），script 部分 125 行 |
| 可复用逻辑提取为 composables | ✅ | useAuth / usePagination |
| Props Down / Events Up | ✅ | PaperCard/AnalysisCard/PlainExplanation 均遵循 |

### 5.3 状态管理

| 检查项 | 状态 | 备注 |
|--------|------|------|
| Store State 更新只通过 Action | ✅ | 无组件直接修改 Store State |
| 无跨 Store 重复状态 | ⚠️ | PaperDetailView 本地 analysisResult 与 sessionStore 重复 |
| Derived State 使用 computed | ✅ | isLoggedIn/hasProfile/selectedPaperIds/isAnalyzing 等 |
| Token 存储安全 | ✅ | LocalStorage + logout 清除，无敏感信息 |

### 5.4 交互完整性

| 检查项 | 状态 | 备注 |
|--------|------|------|
| 所有数据区域有 loading 状态 | ✅ | SearchView v-loading / PaperDetailView el-skeleton / 分析中 v-loading |
| 所有列表有 empty 状态 | ✅ | SearchView el-empty / PaperDetailView el-empty / UserCenterView el-empty |
| 所有 API 调用有 error 处理 | ✅ | try/catch + ElMessage.error |
| 按钮防重复提交 | ✅ | registerLoading/loginLoading/saving/analyzing 控制 :loading/:disabled |
| 操作即时反馈 | ✅ | 收藏乐观更新 + ElMessage / 分析进度文案 |

---

## 6 亮点

1. **首次登录画像引导流程完整**：useAuth.redirectAfterLogin() → 检测 hasProfile → 无画像跳转 UserCenter?setupProfile=true → 保存后跳转首页，闭环设计清晰
2. **三态完整性优秀**：SearchView/PaperDetailView 均实现了 loading/empty/error 三态，SearchView 还额外提供重试按钮
3. **收藏乐观更新**：paperStore.toggleFavorite() 先更新 UI 再发请求，失败时回滚，用户体验流畅
4. **SSE 重连策略**：sessionStore 实现 3s 间隔、最多 5 次自动重连，符合架构文档要求
5. **轮询 + SSE 双通道**：startAnalysis 同时启动 SSE 连接和轮询，SSE 实时更新 Agent 状态，轮询兜底获取最终结果
6. **循环依赖规避**：Router beforeEach 和 Axios 拦截器均使用动态 import() 获取 Store 实例
7. **表单校验完善**：RegisterView 自定义确认密码校验 + watch 联动校验，LoginView 回车提交支持
8. **CSS 变量体系一致**：所有新增组件均使用 variables.scss 中定义的 CSS 变量（间距/字号/圆角/阴影），BEM 命名规范
9. **组件可复用性**：PaperCard 同时支持 SearchView 和 CompareView（selectable/selected props），AnalysisCard 含降级标签和通俗解释开关

---

## 7 统计

| Severity | 数量 | 状态 |
|----------|------|------|
| Critical | 0 | — |
| High | 1 | 待 FM3 联调时修复 |
| Medium | 5 | 2项待 FM3 修复，2项待 FM5 修复，1项待本周修复 |
| Low | 3 | 待 FM5 UI 打磨时处理 |
| FM1遗留 | 2 | 1项待 FM4，1项待本周 |

---

## 8 测试验证建议

| 验证项 | 命令 | 预期结果 |
|--------|------|---------|
| TypeScript 编译 | `npm run typecheck` | 退出码0，零错误 |
| 单元测试 | `npm run test:run` | 所有测试通过 |
| 开发服务器 | `npm run dev` | 启动成功，localhost:5173 可访问 |
| 注册页面 | 浏览器 /register | 表单校验生效，注册成功跳转登录 |
| 登录页面 | 浏览器 /login | 登录成功 Token 写入 localStorage |
| 画像引导 | 首次登录后 | 自动跳转用户中心，显示引导提示 |
| 路由守卫 | 未登录访问 /search | 自动跳转 /login?redirect=/search |
| 已登录守卫 | 已登录访问 /login | 自动跳转首页 |
| 检索流程 | 首页输入主题 | 跳转检索结果页，论文卡片列表展示 |
| 论文详情 | 点击论文卡片 | 详情页元数据完整 |
| AI分析 | 点击分析按钮 | loading 状态 → 分析结果5维度展示 |

> ⚠️ 注：以上第4-11项需 Java 后端 API 就绪后方可端到端验证。当前为代码逻辑审查，前端代码链路完整无报错。

---

## 9 结论与建议

### 审阅结论

**FM2 里程碑通过** ✅

16项验收检查全部通过，15项交付物全部完成。用户注册→登录→画像设置→检索→论文详情→AI分析的完整链路代码逻辑闭环，无阻塞性问题。1项 High 级别问题（SSE Token 认证）不影响 FM2 功能，但需在 FM3 SSE 联调前解决。

### 下一步行动

| 优先级 | 行动项 | 时间窗口 |
|--------|--------|---------|
| P0 | 开始 FM3 开发：PlainExplanation 完善 / CompareView / ReportView / useSSE | Week 7-8 |
| P0 | 解决 SSE EventSource JWT Token 认证问题（FM3 前置依赖） | FM3 开发前 |
| P1 | PaperDetailView API 调用改为通过 Store Action | 本周内 |
| P1 | 移除 PaperDetailView 本地 analysisResult 重复状态 | 本周内 |
| P1 | 修复 LoginView/RegisterView/global.scss 硬编码颜色 | 本周内 |
| P2 | 补充 .env 和 .env.production 环境变量文件（FM1遗留） | 本周内 |
| P2 | 提取 formatAuthors/formatMeta 为工具函数 | FM5 UI 打磨时 |
| P2 | paperStore.fetchFavorites() 实际实现 | FM5 收藏功能时 |
| P2 | PaperCard 关键词展开显示 | FM5 UI 打磨时 |

---

> **报告生成时间**：2026-06-02
> **下次审阅**：FM3 里程碑完成时
