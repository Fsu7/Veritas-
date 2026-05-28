# FM2 前端里程碑审阅计划

## 审阅范围

- 架构文档: `docs/frontend/前端模块系统架构文档.md`
- 里程碑文档: `docs/frontend/前端模块项目里程碑文档.md`
- 前端源码: `Veritas/frontend/src/`

## FM2 验收检查点逐项审查

### 1. □ 用户注册: 输入用户名/邮箱/密码可注册成功

**代码现状**: ✅ 已实现

- [RegisterView.vue](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/views/RegisterView.vue) — 完整实现
  - 表单字段: username / email / password / confirmPassword
  - 表单校验: 用户名3-50字符、邮箱格式、密码8-100字符、确认密码一致性
  - 密码变更时自动重新校验确认密码 (watch)
  - 注册成功: `ElMessage.success('注册成功，请登录')` + `router.push('/login')`
  - 注册失败: `ElMessage.error('注册失败，请重试')`
  - Loading状态: `registerLoading` 控制按钮和输入框禁用
- [userStore.register](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/stores/userStore.ts#L83) — 调用 `userApi.register`
- [userApi.register](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/api/user.ts#L5) — POST `/users/register`

**问题**: 无

**结论**: ✅ 代码完整，需后端联调验证

---

### 2. □ 用户登录: 输入用户名/密码可登录，Token存入LocalStorage

**代码现状**: ✅ 已实现

- [LoginView.vue](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/views/LoginView.vue) — 完整实现
  - 表单字段: username / password
  - 表单校验: 用户名3-50字符、密码8-100字符
  - 登录成功: `ElMessage.success('登录成功')` + 跳转redirect或首页
  - Loading状态: `loginLoading` 控制按钮和输入框禁用
  - 回车提交: `@keyup.enter="handleLogin"`
- [userStore.login](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/stores/userStore.ts#L29) — 调用 `userApi.login` → `persistLoginData`
- [persistLoginData](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/stores/userStore.ts#L20) — Token/userId/username 存入 LocalStorage

**问题**:
- [Medium] LoginView catch块为空，不显示自定义错误信息，完全依赖Axios拦截器。虽然拦截器会处理401等错误，但登录接口的401被特殊处理为"用户名或密码错误"，其他错误可能不够明确。

**结论**: ✅ 核心功能完整

---

### 3. □ 画像设置: 首次登录引导设置画像，4维度选择正确

**代码现状**: ⚠️ 部分实现

- [UserProfileForm.vue](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/components/common/UserProfileForm.vue) — 画像表单完整实现
  - 4维度: educationLevel / researchField / knowledgeLevel / preferredStyle
  - 枚举选项与后端一致: undergraduate/master/phd/faculty, beginner/intermediate/advanced/expert, simple/balanced/technical
  - 表单校验: 4个字段均required
  - initialData watch: 支持编辑模式回填
  - 保存: `userStore.saveProfile` → `ElMessage.success` → emit('saved')

**关键缺失**:
- ❌ **首次登录引导流程缺失** — LoginView.vue 登录成功后直接跳转首页或redirect，没有检查 `hasProfile` 并引导到画像设置页
- userStore.login 虽然检查了 `res.hasProfile` 并 `fetchProfile()`，但没有根据 hasProfile=false 跳转到画像设置页
- 架构文档4.2.1明确要求"首次登录引导设置画像"，但代码中未实现

**修复方案**:
1. LoginView.vue `handleLogin` 成功后，检查 `userStore.hasProfile`
2. 如果 `!hasProfile`，跳转到 `/user-center` 或显示画像设置对话框
3. 或者跳转到首页时显示画像设置引导弹窗

**结论**: ⚠️ 画像表单完整，但首次登录引导流程缺失

---

### 4. □ 画像保存: 保存后跳转首页，画像信息持久化

**代码现状**: ⚠️ 部分实现

- UserProfileForm handleSave → `userStore.saveProfile` → emit('saved')
- UserCenterView handleProfileSaved → `userStore.fetchProfile()` (仅刷新数据)

**问题**:
- ❌ **保存后跳转首页逻辑缺失** — 在UserCenterView中保存画像后只刷新数据，不跳转首页
- ⚠️ **画像信息未在LocalStorage持久化** — profile数据仅存在Pinia store内存中，页面刷新后需要重新从API获取
  - 这不算严重问题（Cache-Aside模式），但首次登录场景下如果API还没返回画像数据就刷新页面，画像会丢失
- 在首次登录引导场景中，保存画像后应跳转首页

**修复方案**:
1. UserProfileForm 添加 `redirectAfterSave` prop
2. 首次登录场景传入 `redirectAfterSave: true`，保存成功后 `router.push('/')`

**结论**: ⚠️ 画像保存功能正常，但缺少保存后跳转首页逻辑

---

### 5. □ 路由守卫: 未登录访问/search跳转/login

**代码现状**: ✅ 已实现

- [router/index.ts](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/router/index.ts#L71) — beforeEach守卫
  - `to.meta.requiresAuth && !userStore.isLoggedIn` → `next({ name: 'Login', query: { redirect: to.fullPath } })`
  - /search 路由 `meta: { requiresAuth: true }` ✅
  - 动态import避免循环依赖 ✅

**结论**: ✅ 完整实现

---

### 6. □ 已登录守卫: 已登录访问/login跳转首页

**代码现状**: ✅ 已实现

- [router/index.ts](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/router/index.ts#L77)
  - `(to.name === 'Login' || to.name === 'Register') && userStore.isLoggedIn` → `next({ name: 'Home' })`

**结论**: ✅ 完整实现

---

### 7. □ 主题输入: 输入研究主题，回车或点击按钮触发检索

**代码现状**: ✅ 已实现

- [HomeView.vue](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/views/HomeView.vue)
  - 输入框: `v-model="searchQuery"` + `@keyup.enter="handleSearch"`
  - 按钮: `@click="handleSearch"` + `:loading="isSearching"`
  - handleSearch: trim校验 → saveRecentSearch → 检查登录 → paperStore.searchPapers → router.push Search

**结论**: ✅ 完整实现

---

### 8. □ 历史搜索: 显示最近10条搜索记录，点击可快捷检索

**代码现状**: ✅ 已实现

- [HomeView.vue](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/views/HomeView.vue#L78) — recentSearches展示 + 点击快捷检索 + 清除按钮
- [storage.ts](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/utils/storage.ts) — getRecentSearches/saveRecentSearch(max 10)/clearRecentSearches

**结论**: ✅ 完整实现

---

### 9. □ 检索结果: 论文卡片列表正确展示，分页正常

**代码现状**: ✅ 已实现

- [SearchView.vue](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/views/SearchView.vue)
  - PaperCard列表: `v-for="paper in paperStore.searchResults"` + `:key="paper.paperId"`
  - 分页: `el-pagination` + `handlePageChange`
  - Loading: `v-loading="searchLoading"`
  - 空结果: `el-empty`
  - 错误: `el-result icon="error"` + 重试按钮
  - 统计: "找到 X 篇相关论文"
- [usePagination.ts](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/composables/usePagination.ts) — 分页逻辑封装

**结论**: ✅ 完整实现，需后端联调验证

---

### 10. □ 论文卡片: 标题/作者/摘要/关键词/相关度正确显示

**代码现状**: ✅ 已实现

- [PaperCard.vue](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/components/paper/PaperCard.vue)
  - 标题: `paper.title` ✅
  - 作者/年份/会议: `formatMeta()` ✅
  - 摘要: `truncateText(paper.abstract, 200)` ✅
  - 关键词: `paper.keywords.slice(0, 3)` ✅
  - 相关度: `formatScore(paper.score)` → "相关度 XX%" ✅
  - 推荐理由: `paper.recommendReason` ✅
  - 收藏状态: `isFavorited` prop ✅
  - 操作按钮: 分析 / 收藏 ✅

**结论**: ✅ 完整实现

---

### 11. □ 论文详情: 点击论文卡片进入详情页，元数据完整

**代码现状**: ✅ 已实现

- SearchView handleSelect → `router.push({ name: 'PaperDetail', params: { paperId } })`
- [PaperDetailView.vue](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/views/PaperDetailView.vue)
  - 元数据: title / authors / year / venue / citationCount / abstract / keywords / pdfUrl ✅
  - Loading: `el-skeleton` ✅
  - 错误: `el-result icon="error"` + 重试 ✅
  - 未找到: `el-result icon="warning"` ✅
  - 返回: `el-page-header @back="router.back()"` ✅
  - 收藏: toggleFavorite ✅
  - PDF: openPdf ✅

**结论**: ✅ 完整实现

---

### 12. □ AI分析: 点击分析按钮触发分析，loading状态正确

**代码现状**: ✅ 已实现

- PaperDetailView handleAnalyze → `sessionStore.startAnalysis(paper.title, paperId)`
- [sessionStore.startAnalysis](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/stores/sessionStore.ts#L63)
  - 创建会话 → 启动分析 → 连接SSE → 轮询状态
  - 分析状态: creating_session / starting_analysis / polling / connecting_sse
- PaperDetailView analyzing computed ✅
- analysisStatusText computed ✅ — 显示当前分析进度文字
- Loading: `v-loading="true"` + 进度文字 ✅
- onUnmounted: `sessionStore.cleanup()` ✅ — 清理轮询和SSE

**结论**: ✅ 完整实现，需后端联调验证

---

### 13. □ 分析结果: 5维度分析卡片正确展示

**代码现状**: ✅ 已实现

- [AnalysisCard.vue](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/components/analysis/AnalysisCard.vue)
  - DIMENSIONS: researchQuestion / coreMethod / keyExperiments / coreFindings / limitations ✅
  - 降级标签: `analysis.degraded` → "部分降级" ✅
  - 降级原因: `analysis.degradedReason` ✅
  - 通俗解释: PlainExplanation组件 + showPlainExplanation prop ✅
  - 操作: 生成综述 / 选择对比 ✅

**结论**: ✅ 完整实现

---

### 14. □ 错误处理: API错误时ElMessage提示正确

**代码现状**: ✅ 基本实现

- [api/index.ts](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/api/index.ts) 响应拦截器:
  - 业务错误 (code !== 200): `ElMessage.error(data.message)` ✅
  - 401 (登录接口): `ElMessage.error('用户名或密码错误')` ✅
  - 401 (其他接口): `userStore.logout()` + `router.push('/login')` + `ElMessage.error('登录已过期')` ✅
  - 403: `ElMessage.error('无权限访问')` ✅
  - 404: `ElMessage.error('请求的资源不存在')` ✅
  - 超时: `ElMessage.error('请求超时')` ✅
  - 其他: `ElMessage.error('网络错误')` ✅
- 各页面catch块: RegisterView ✅ / SearchView ✅ / PaperDetailView ✅

**问题**:
- [Low] LoginView catch块为空，依赖拦截器处理。虽然功能正常，但不够显式。

**结论**: ✅ 基本完整

---

### 15. □ 401处理: Token过期自动跳转登录页

**代码现状**: ✅ 已实现

- [api/index.ts](file:///Users/achieve/Documents/AchiEVE_MacBook_Air/Veritas(求真)/Veritas/frontend/src/api/index.ts#L44) — 401响应处理
  - 登录接口401: 仅显示错误提示（不跳转）
  - 其他接口401: `userStore.logout()` + `router.push('/login')` + `ElMessage.error('登录已过期')`
  - AUTH_WHITELIST机制避免登录接口触发登出 ✅

**结论**: ✅ 完整实现

---

### 16. □ 全链路: 注册→登录→画像→检索→详情→分析 无报错

**代码现状**: ⚠️ 链路存在断裂点

各环节代码均已实现，但存在以下断裂点:

1. **首次登录→画像设置引导缺失** — 登录成功后直接跳转首页，未引导设置画像
2. **画像设置→检索的衔接** — 首页不显示画像信息，用户可能不知道需要设置画像
3. **全链路需要后端API就绪** — 当前代码无法独立验证完整链路

**修复方案**: 实现首次登录引导画像设置流程后，全链路可贯通

**结论**: ⚠️ 各环节代码已实现，首次登录引导流程缺失导致链路断裂

---

## FM2 交付物完成度总览

| 序号 | 交付物 | 状态 | 说明 |
|------|--------|------|------|
| 1 | LoginView登录页 | ✅ | 完整实现 |
| 2 | RegisterView注册页 | ✅ | 完整实现 |
| 3 | UserProfileForm画像表单 | ✅ | 4维度完整，枚举与后端一致 |
| 4 | UserCenterView用户中心 | ✅ | 用户信息+画像编辑+历史记录 |
| 5 | userStore完整实现 | ✅ | FM1已完整实现 |
| 6 | useAuth鉴权组合函数 | ❌ | **未创建** — 路由守卫逻辑直接写在router中 |
| 7 | HomeView首页完整 | ✅ | FM1已完整实现 |
| 8 | SearchView检索结果页 | ✅ | 论文卡片+分页+loading+empty+error |
| 9 | PaperCard论文卡片组件 | ✅ | 标题/作者/摘要/关键词/相关度/推荐理由 |
| 10 | paperStore完整实现 | ✅ | FM1已完整实现 |
| 11 | PaperDetailView论文详情页 | ✅ | 元数据+AI分析+收藏+PDF |
| 12 | AnalysisCard分析卡片 | ✅ | 5维度+降级标签+通俗解释 |
| 13 | sessionStore基础实现 | ✅ | FM1已完整实现（含SSE和轮询） |
| 14 | usePagination分页组合函数 | ✅ | 完整实现 |
| 15 | 全链路联调 | ⚠️ | 需后端就绪+首次登录引导修复 |

---

## 发现的问题清单

### Critical (阻塞FM2验收)

| # | 问题 | 影响 | 修复方案 |
|---|------|------|---------|
| C1 | 首次登录引导画像设置流程缺失 | 全链路断裂：登录后无法引导用户设置画像，影响个性化功能 | LoginView handleLogin成功后检查hasProfile，若为false则跳转UserCenter或显示画像设置弹窗 |
| C2 | useAuth鉴权组合函数未创建 | FM2交付物第6项未完成，鉴权逻辑分散在router和api中 | 创建composables/useAuth.ts，封装isLoggedIn/requireAuth/redirectIfAuth逻辑 |

### High (严重影响用户体验)

| # | 问题 | 影响 | 修复方案 |
|---|------|------|---------|
| H1 | 画像保存后跳转首页逻辑缺失 | 首次登录设置画像后无法自动跳转首页 | UserProfileForm添加redirectAfterSave prop，首次登录场景保存后router.push('/') |

### Medium (影响代码质量)

| # | 问题 | 影响 | 修复方案 |
|---|------|------|---------|
| M1 | LoginView catch块为空 | 登录失败时无自定义错误处理，完全依赖拦截器 | 在catch块中添加显式错误处理或注释说明依赖拦截器 |
| M2 | AppHeader硬编码颜色值 | `#e4e7ed`、`#606266` 应使用CSS变量 | 替换为 `var(--el-border-color-lighter)` 和 `var(--el-text-color-secondary)` |
| M3 | HomeView硬编码样式值 | `font-size: 32px`、`margin-bottom: 48px` 应使用CSS变量 | 替换为 `var(--font-size-xxl)` 和 `var(--spacing-xl)` |

### Low (优化建议)

| # | 问题 | 影响 | 修复方案 |
|---|------|------|---------|
| L1 | PaperDetailView style属性内联 | `style="margin-top: 16px"` 应使用CSS类 | 提取为CSS类使用CSS变量 |

---

## 实施步骤

### Step 1: 创建 useAuth composable [C2]
- 创建 `composables/useAuth.ts`
- 封装 isLoggedIn / hasProfile / requireAuth / redirectIfAuth 逻辑
- 从 router/index.ts 和 api/index.ts 中提取鉴权逻辑

### Step 2: 实现首次登录引导画像设置流程 [C1]
- 修改 LoginView.vue handleLogin
- 登录成功后检查 `userStore.hasProfile`
- 若 hasProfile=false，跳转 `/user-center` 并显示引导提示
- 或在首页显示画像设置引导弹窗

### Step 3: 添加画像保存后跳转首页逻辑 [H1]
- UserProfileForm 添加 `redirectAfterSave` prop
- 首次登录场景传入 redirectAfterSave=true
- 保存成功后 router.push('/')

### Step 4: 修复 LoginView catch 块 [M1]
- 添加显式错误处理或注释

### Step 5: 修复硬编码颜色和样式值 [M2, M3, L1]
- AppHeader: 替换硬编码颜色为CSS变量
- HomeView: 替换硬编码样式值为CSS变量
- PaperDetailView: 提取内联样式为CSS类

### Step 6: 验证全链路
- 注册→登录→画像引导→画像设置→保存跳转首页→检索→详情→分析
- 确认所有16个验收检查点通过

---

## 审阅统计

| Severity | 数量 |
|----------|------|
| Critical | 2 |
| High | 1 |
| Medium | 3 |
| Low | 1 |

## FM2 完成度评估

- **代码完成度**: 13/15 交付物已完成 (86.7%)
- **验收检查点**: 12/16 完全通过 (75%), 3个部分通过, 1个需后端联调
- **关键阻塞**: 首次登录引导画像设置流程 + useAuth composable
- **预计修复工作量**: 约2-3小时
