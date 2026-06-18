# 技术教学文档

## 开发思路

### 需求分析过程
FM5 是前端功能完善与 UI 打磨里程碑，核心目标：
1. **补齐 P1/P2 功能**：画像编辑、历史记录、论文收藏、综述编辑、Agent 回放、退出登录完善
2. **UI 统一打磨**：设计系统化、消除硬编码、通用工具类
3. **响应式布局**：平板和移动端基本可用
4. **测试覆盖**：补全 views/stores/composables/components 层级测试
5. **验收测试**：13 项 AC 检查点全部通过

### 技术选型考虑
- **CSS 变量 + SCSS mixins**：CSS 变量提供运行时主题切换能力，SCSS mixins 提供编译时复用（如 respond-to 媒体查询）
- **el-drawer 移动端导航**：Element Plus 内置组件，无需额外依赖
- **composable 回放系统**：useReplay 封装 setInterval 帧推进 + onScopeDispose 自动清理
- **vi.mock 测试隔离**：vitest 原生支持，避免真实网络请求

### 架构设计思路
```
View → Store → API（三层分离）
  ↓
Composable（横切关注点：useReplay/useAuth/usePagination）
  ↓
Component（可复用 UI：EmptyState/ErrorState/ReportEditor）
```

### 遇到的问题及解决方案

#### 问题 1: SCSS @media 无法使用 CSS 变量
- **现象**：`@media (max-width: var(--breakpoint-md))` 无效
- **原因**：CSS 变量是运行时值，@media 是编译时查询
- **解决**：respond-to mixin 内部硬编码断点值（640/768/1024/1280px），--breakpoint-* 变量保留供 JS 读取

#### 问题 2: toggleFavorite 签名变更导致调用方不兼容
- **现象**：toggleFavorite(paperId, paper?) 新增 paper 参数后，旧调用方报错
- **解决**：保持 `toggleFavorite(paperId: string, paper?: Paper)` 向后兼容

#### 问题 3: 401 拦截器中调用 async logout 未 await
- **现象**：Token 过期时 401 拦截器调用 logout 但未 await，导致状态清理不完整
- **解决**：`await userStore.logout()` 并设置 `userStore.isManualLogout = true`

#### 问题 4: useReplay currentFrame 是 computed 返回，与原数组元素非同一引用
- **现象**：测试中 `expect(currentFrame).toBe(frames[0])` 失败
- **解决**：使用 `toStrictEqual` 而非 `toBe` 做深比较

#### 问题 5: useReplay 使用 onScopeDispose 清理定时器
- **现象**：测试中定时器未清理
- **解决**：测试需用 `effectScope` 包裹 `useReplay()` 才能触发 onScopeDispose

## 实现步骤

### 1. Task 43-48：P1/P2 功能补充
- 画像编辑 + profileVersion 机制
- 历史记录分页 + 关键词搜索
- 论文收藏 + FavoritesView 收藏列表页
- 综述编辑 + ReportEditor 组件
- Agent 回放 + useReplay composable
- 退出登录 + isManualLogout 标志
- EmptyState + ErrorState 通用组件

### 2. Task 49：UI 设计系统统一打磨
- variables.scss 补全 --font-size-display/--breakpoint-*/--chart-height-*
- 新建 mixins.scss（respond-to/text-truncate/flex-center/card-shadow）
- global.scss 新增 .card-shadow/.text-*/.bg-primary 工具类
- 替换 HomeView/AgentFlowChart/TimeStats/SearchView/UserCenterView/FilterPanel 硬编码值

### 3. Task 50：响应式布局适配
- AppHeader 汉堡菜单 + el-drawer
- SearchView FilterPanel 抽屉化
- CompareView 表格横向滚动
- AgentFlowView 移动端上下布局
- ReportView/UserCenterView/FavoritesView 移动端字号缩小

### 4. Task 51：补全 14 份单元测试
- 2 stores（userStore/agentStore）
- 3 components（EmptyState/ErrorState/ReportEditor）
- 2 composables（useAuth/useReplay）
- 7 views（UserCenter/Login/Register/PaperDetail/Compare/Report/Favorites）

### 5. Task 52：FM5 集成验收测试
- fm5-acceptance.spec.ts，13 项 AC 检查点
- 使用 vi.mock 隔离所有外部依赖
- 使用 readFileSync 读取 scss 文件验证设计系统变量

## 解决了什么问题

### 核心问题描述
1. **UI 不统一**：硬编码尺寸值散落各组件，无通用工具类
2. **无移动端适配**：桌面端布局在小屏幕错乱
3. **测试覆盖不足**：views/stores/composables 层级无测试
4. **P1/P2 功能缺失**：画像编辑/收藏/综述编辑/回放/退出登录完善未实现

### 解决方案对比
| 问题 | 方案 A | 方案 B | 最终选择 |
|------|--------|--------|---------|
| UI 统一 | Tailwind CSS | CSS 变量 + SCSS mixins | CSS 变量（无需新依赖，与 Element Plus 主题一致） |
| 移动端导航 | 自定义 Modal | el-drawer | el-drawer（Element Plus 内置） |
| 回放系统 | requestAnimationFrame | setInterval | setInterval（帧间隔可控，便于测试） |
| 测试隔离 | 真实 API mock server | vi.mock | vi.mock（轻量，vitest 原生支持） |

### 最终方案的优势
- **零新依赖**：CSS 变量 + SCSS mixins + el-drawer 都是现有技术栈
- **与 Element Plus 主题一致**：使用 var(--el-color-*) 变量
- **测试友好**：vi.mock 隔离 + vi.useFakeTimers 控制定时器
- **渐进式增强**：从硬编码 → CSS 变量 → mixins 逐步演进

## 变更内容

### 新增文件
- `src/styles/mixins.scss` - SCSS mixins（respond-to/text-truncate/flex-center/card-shadow）
- `src/components/common/EmptyState.vue` - 通用空状态组件
- `src/components/common/ErrorState.vue` - 通用错误状态组件
- `src/components/report/ReportEditor.vue` - 综述编辑器（编辑/预览/分屏）
- `src/composables/useReplay.ts` - Agent 流程回放 composable
- `src/views/FavoritesView.vue` - 收藏列表页
- 14 份单元测试文件（stores/components/composables/views）
- `src/__tests__/integration/fm5-acceptance.spec.ts` - FM5 集成验收测试

### 修改文件
- `src/styles/variables.scss` - 新增 --font-size-display/--breakpoint-*/--chart-height-*
- `src/styles/global.scss` - 引入 mixins + 新增 .card-shadow/.text-*/.bg-primary 工具类
- `src/stores/userStore.ts` - profileVersion/isManualLogout + async logout
- `src/stores/paperStore.ts` - favoritesList/fetchFavorites
- `src/stores/agentStore.ts` - replayFrames/loadReplayData/applyReplayFrame/exitReplayMode
- `src/views/HomeView.vue` - 替换硬编码 48px + respond-to mixin
- `src/views/SearchView.vue` - FilterPanel 抽屉化 + 移动端响应式
- `src/views/CompareView.vue` - 表格横向滚动 + 移动端响应式
- `src/views/AgentFlowView.vue` - 回放控制条 + 移动端上下布局
- `src/views/ReportView.vue` - 编辑模式 + 移动端响应式
- `src/views/UserCenterView.vue` - 画像标签 + 历史搜索分页 + 移动端响应式
- `src/views/FavoritesView.vue` - 移动端响应式
- `src/components/layout/AppHeader.vue` - 汉堡菜单 + el-drawer + 移动端响应式
- `src/components/agent/AgentFlowChart.vue` - 替换硬编码 450px
- `src/components/agent/TimeStats.vue` - 替换硬编码 400px
- `src/components/common/FilterPanel.vue` - 替换硬编码 4px
- `src/router/index.ts` - /favorites 路由

### 配置变更
- 无配置文件变更（vite.config.ts 已全局注入 variables.scss）

## 关键技术点

### 使用的核心技术
- **CSS 变量设计系统**：:root 定义全局变量，组件通过 var(--xxx) 引用
- **SCSS mixins**：respond-to/text-truncate/flex-center/card-shadow
- **el-drawer**：Element Plus 内置抽屉组件，移动端导航
- **composable 模式**：useReplay 封装回放逻辑
- **Pinia Store setup 风格**：Composition API 定义状态和 actions
- **vi.mock 测试隔离**：vitest 原生 mock 能力
- **vi.useFakeTimers**：控制 setInterval 定时器测试

### 代码实现亮点
- **profileVersion 机制**：saveProfile 成功后 profileVersion++，watch 触发 fetchProfile 刷新
- **isManualLogout 标志**：区分主动退出/Token 过期，避免 401 拦截器误弹登录提示
- **useReplay onScopeDispose**：自动清理定时器，防止内存泄漏
- **respond-to mixin 硬编码断点**：规避 SCSS @media 无法使用 CSS 变量的限制
- **fm5-acceptance readFileSync 验证**：通过读取 scss 文件内容验证设计系统变量存在

### 需要注意的细节
- `vite.config.ts` 全局注入 `variables.scss`，但 `mixins.scss` 需在组件 scoped 样式中手动 `@use`
- `respond-to` mixin 使用硬编码断点值（非 CSS 变量），因 @media 是编译时查询
- `useReplay` 的 `currentFrame` 是 computed 返回，与原数组元素非同一引用，测试需用 `toStrictEqual`
- `useReplay` 使用 `onScopeDispose` 清理定时器，测试需用 `effectScope` 包裹

## 经验总结

### 开发过程中的收获
1. **CSS 变量 vs SCSS 变量**：CSS 变量是运行时值，SCSS 变量是编译时值。@media 查询只能使用编译时值，因此 respond-to mixin 必须硬编码断点。
2. **composable 生命周期**：onScopeDispose 在 effect scope 销毁时触发，测试中需用 effectScope 包裹才能验证清理逻辑。
3. **vi.mock hoisting**：vi.mock 会被提升到文件顶部，mock 工厂内不能引用外部变量（需用 vi.hoisted）。
4. **Element Plus 组件 stub**：测试中需 stub 所有用到的 Element Plus 组件，否则渲染失败。提取公共 commonStubs 配置可减少重复。

### 踩过的坑及如何避免
1. **toggleFavorite 签名变更**：新增参数时保持向后兼容（可选参数）
2. **401 拦截器 async logout 未 await**：异步操作必须 await，否则状态清理不完整
3. **useReplay currentFrame 引用问题**：computed 返回新引用，测试用 toStrictEqual
4. **fm4-acceptance ECharts jsdom 失败**：ECharts 在 jsdom 下需 mock，不能直接渲染

### 最佳实践建议
1. **设计系统优先**：先定义 variables.scss + mixins.scss，再开发组件，避免硬编码
2. **测试与开发同步**：每个功能完成后立即编写测试，避免积累技术债
3. **公共 stubs 配置**：提取 Element Plus 组件 stubs 到公共文件，减少测试重复代码
4. **响应式断点统一**：使用 respond-to mixin 而非直接写 @media，保证断点一致
5. **composable 清理**：使用 onScopeDispose 自动清理定时器/事件监听器，防止内存泄漏
