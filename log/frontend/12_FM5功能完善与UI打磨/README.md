# FM5 功能完善与 UI 打磨

## 功能描述

### 解决了什么问题
- FM4 完成后前端功能完整但缺乏 P1/P2 功能（画像编辑、历史记录、论文收藏、综述编辑、Agent 回放、退出登录完善）
- UI 设计不统一（硬编码尺寸值、缺少通用工具类、无 SCSS mixins）
- 无移动端/平板适配
- 测试覆盖不足（缺少 views/stores/composables/components 层级测试）
- 无空状态/错误状态通用组件

### 实现了什么功能
- **画像编辑实时生效**：UserCenterView 支持修改已设置画像，profileVersion 版本号驱动刷新
- **历史记录分页+搜索**：UserCenterView 展示历史分析记录，按时间倒序，支持关键词搜索
- **论文收藏/取消收藏**：PaperCard 收藏按钮 + FavoritesView 收藏列表页
- **综述内容编辑**：ReportView 编辑模式 + ReportEditor 组件（编辑/预览/分屏）
- **Agent 流程回放**：useReplay composable + ReplayFrame 帧数据 + 回放控制条
- **退出登录 Token 黑名单**：isManualLogout 标志区分主动退出/Token 过期 + async logout
- **空状态/错误状态组件**：EmptyState + ErrorState 通用组件
- **UI 设计系统统一**：variables.scss 补全变量 + mixins.scss 新建 + global.scss 工具类
- **响应式布局适配**：AppHeader 汉堡菜单 + SearchView FilterPanel 抽屉化 + CompareView 表格横向滚动 + 移动端字号缩小

### 业务价值
- 完成前端 P0 100% + P1 >80% 验收标准
- UI 统一打磨，设计系统化
- 移动端基本可用（不要求完美）
- 测试覆盖率提升，213 个测试用例通过
- 13 项 FM5 验收检查点全部通过

## 实现逻辑

### 修改的核心文件列表（task43-task52 共 10 个任务）

#### Task 43: 画像编辑历史记录增强
- `src/stores/userStore.ts` - profileVersion/isManualLogout + async logout
- `src/components/common/UserProfileForm.vue` - 重置按钮 + saved payload
- `src/views/UserCenterView.vue` - 画像标签 + 历史搜索分页

#### Task 44: 论文收藏列表
- `src/api/paper.ts` - getFavorites 方法
- `src/stores/paperStore.ts` - favoritesList/fetchFavorites
- `src/views/FavoritesView.vue` - 收藏列表页
- `src/router/index.ts` - /favorites 路由
- `src/components/layout/AppHeader.vue` - 我的收藏菜单

#### Task 45: 综述内容编辑
- `src/utils/markdown.ts` - renderMarkdownWithCitations
- `src/api/analysis.ts` - saveReportContent
- `src/components/report/ReportEditor.vue` - 编辑/预览/分屏
- `src/views/ReportView.vue` - 编辑模式
- `src/components/report/ExportPanel.vue` - customContent prop

#### Task 46: Agent 流程回放
- `src/types/agent.ts` - ReplayFrame 接口
- `src/composables/useReplay.ts` - play/pause/seek/speed
- `src/stores/agentStore.ts` - replayFrames/loadReplayData/applyReplayFrame
- `src/views/AgentFlowView.vue` - 回放控制条

#### Task 47: 退出登录 Token 黑名单
- `src/api/user.ts` - logout 方法
- `src/composables/useAuth.ts` - async logout
- `src/api/index.ts` - 401 拦截器 isManualLogout 区分

#### Task 48: 空错误状态组件
- `src/components/common/EmptyState.vue` - 通用空状态
- `src/components/common/ErrorState.vue` - 通用错误状态

#### Task 49: UI 设计系统统一打磨
- `src/styles/variables.scss` - 新增 --font-size-display/--breakpoint-*/--chart-height-*
- `src/styles/mixins.scss` - 新建（respond-to/text-truncate/flex-center/card-shadow）
- `src/styles/global.scss` - 新增 .card-shadow/.text-*/.bg-primary 工具类
- `src/views/HomeView.vue` - 替换硬编码 48px
- `src/components/agent/AgentFlowChart.vue` - 替换硬编码 450px
- `src/components/agent/TimeStats.vue` - 替换硬编码 400px

#### Task 50: 响应式布局适配
- `src/components/layout/AppHeader.vue` - 汉堡菜单 + el-drawer
- `src/views/SearchView.vue` - FilterPanel 抽屉化
- `src/views/CompareView.vue` - 表格横向滚动
- `src/views/AgentFlowView.vue` - 移动端上下布局
- `src/views/ReportView.vue`/`UserCenterView.vue`/`FavoritesView.vue` - 移动端字号缩小

#### Task 51: 补全 14 份单元测试
- 2 stores（userStore/agentStore）
- 3 components（EmptyState/ErrorState/ReportEditor）
- 2 composables（useAuth/useReplay）
- 7 views（UserCenter/Login/Register/PaperDetail/Compare/Report/Favorites）

#### Task 52: FM5 集成验收测试
- `src/__tests__/integration/fm5-acceptance.spec.ts` - 13 项 AC 检查点

### 使用的设计模式
- **CSS 变量设计系统**：通过 `:root` 定义全局变量，组件通过 `var(--xxx)` 引用
- **SCSS mixins**：respond-to/text-truncate/flex-center/card-shadow 通用 mixin
- **响应式断点**：640/768/1024/1280px 四档断点
- **composable 模式**：useReplay 封装回放逻辑，setup 风格
- **Pinia Store setup 风格**：Composition API 定义状态和 actions
- **vi.mock 测试隔离**：所有测试使用 vi.mock 隔离外部依赖

### 关键代码逻辑说明
- **profileVersion 机制**：saveProfile 成功后 profileVersion++，watch profileVersion 触发 fetchProfile 刷新
- **isManualLogout 标志**：主动退出时设为 true，401 拦截器检查该标志区分主动退出/Token 过期
- **useReplay 回放系统**：ReplayFrame 数组 + setInterval 帧推进 + onScopeDispose 自动清理
- **respond-to mixin**：SCSS @media 无法使用 CSS 变量，因此硬编码断点值，--breakpoint-* 变量供 JS 读取

## 接口变更

### Request
（无新增 API，均为前端实现）

### Response
（无新增 API，均为前端实现）

## 测试结果

### 测试场景
- **单元测试**：14 份新增 spec 文件，172 个测试用例全部通过
  - stores: userStore(9) + agentStore(12) = 21
  - components: EmptyState(6) + ErrorState(7) + ReportEditor(8) = 21
  - composables: useAuth(17) + useReplay(44) = 61
  - views: LoginView(5) + RegisterView(6) + PaperDetailView(8) + FavoritesView(11) + UserCenterView(11) + CompareView(12) + ReportView(16) = 69
- **集成验收测试**：fm5-acceptance.spec.ts，13 项 AC 检查点，41 个测试用例全部通过
- **总计**：213 个测试用例全部通过

### 是否通过：是

## 相关文件

### 涉及的代码文件路径
- `src/styles/variables.scss`、`src/styles/mixins.scss`、`src/styles/global.scss`
- `src/stores/userStore.ts`、`src/stores/paperStore.ts`、`src/stores/agentStore.ts`
- `src/composables/useReplay.ts`、`src/composables/useAuth.ts`
- `src/components/common/EmptyState.vue`、`src/components/common/ErrorState.vue`
- `src/components/report/ReportEditor.vue`
- `src/views/FavoritesView.vue`、`src/views/UserCenterView.vue`、`src/views/ReportView.vue`
- `src/views/AgentFlowView.vue`、`src/views/SearchView.vue`、`src/views/CompareView.vue`
- `src/views/HomeView.vue`、`src/components/layout/AppHeader.vue`
- `src/__tests__/` 下 14 份单元测试 + fm5-acceptance.spec.ts

### 配置文件变更
- `vite.config.ts`（已全局注入 variables.scss，mixins.scss 需手动引入）
- `vitest.config.ts`（无变更）
