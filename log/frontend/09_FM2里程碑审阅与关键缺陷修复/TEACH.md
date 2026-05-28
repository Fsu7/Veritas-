# 技术教学文档

## 开发思路
- 需求分析过程：依据前端里程碑文档FM2的16个验收检查点，逐项对照前端源码进行代码级审查，而非仅看页面是否可运行
- 技术选型考虑：useAuth composable采用Vue3 Composition API标准模式，与项目已有的usePagination保持一致
- 架构设计思路：鉴权逻辑从router/api分散实现收敛到composable统一封装，遵循"单一职责"和"逻辑复用"原则
- 遇到的问题及解决方案：
  - 首次登录引导流程缺失：通过useAuth.redirectAfterLogin()检查hasProfile，无画像时跳转UserCenter?setupProfile=true
  - 画像保存后跳转：UserCenterView检测setupProfile查询参数，保存后自动router.push('/')
  - LoginView catch块为空：添加显式ElMessage.error提示，不依赖隐式拦截器行为

## 实现步骤
1. 审阅阶段：逐项阅读FM2全部16个验收检查点对应的前端源码，标记完成状态和问题
2. 问题分级：按Critical/High/Medium/Low四级分类，确定修复优先级
3. 创建useAuth composable：封装isLoggedIn/hasProfile/requireAuth/redirectIfAuthenticated/redirectAfterLogin/logout
4. 修改LoginView：使用useAuth.redirectAfterLogin()替代硬编码跳转逻辑
5. 修改UserCenterView：支持setupProfile查询参数，显示引导提示，保存后跳转首页
6. 修复硬编码值：AppHeader颜色、HomeView样式值、PaperDetailView内联样式统一替换为CSS变量
7. 验证：运行typecheck和vitest确认无回归

## 解决了什么问题
- 核心问题描述：FM2全链路（注册→登录→画像→检索→详情→分析）在"登录→画像"环节断裂，首次登录用户无法被引导设置画像
- 解决方案对比：
  - 方案A：在首页显示画像设置弹窗 → 需要额外组件，侵入性强
  - 方案B：登录后跳转UserCenter并显示引导提示 → 复用现有页面，改动最小
  - 最终选择方案B，通过query参数传递状态，UserCenterView检测后显示引导Alert
- 最终方案的优势：零侵入、复用现有组件、用户体验自然（设置完画像自动跳转首页）

## 变更内容
### 新增文件
- `src/composables/useAuth.ts` — 鉴权组合函数，封装isLoggedIn/hasProfile/requireAuth/redirectIfAuthenticated/redirectAfterLogin/logout

### 修改文件
- `src/views/LoginView.vue` — 移除router/route直接引用，使用useAuth.redirectAfterLogin()实现首次登录引导；catch块添加ElMessage.error
- `src/views/UserCenterView.vue` — 添加isProfileSetup computed检测setupProfile查询参数；handleProfileSaved保存后跳转首页；template添加el-alert引导提示；样式添加setup-hint
- `src/components/layout/AppHeader.vue` — #fff→var(--el-bg-color)、#e4e7ed→var(--el-border-color-lighter)、#606266→var(--el-text-color-secondary)、硬编码px→CSS变量
- `src/views/HomeView.vue` — 32px→var(--font-size-xxl)、48px→var(--spacing-xl)
- `src/views/PaperDetailView.vue` — style="margin-top: 16px"提取为.paper-detail-view__retry-btn CSS类

### 配置变更
无

## 关键技术点
- Vue3 Composable模式：useAuth作为可复用逻辑单元，内部使用useRouter和useUserStore，对外暴露computed和方法
- Query参数状态传递：通过router.push({ query: { setupProfile: 'true' } })在页面间传递引导状态，避免全局状态污染
- CSS变量替换硬编码值：统一使用Element Plus CSS变量（--el-bg-color、--el-border-color-lighter等）和项目自定义变量（--font-size-xxl、--spacing-xl等）
- Axios拦截器AUTH_WHITELIST：登录接口401不触发全局登出逻辑，避免循环跳转

## 经验总结
- 开发过程中的收获：里程碑审阅必须逐项代码级审查，不能仅看页面是否渲染；关键断裂点往往在"衔接"处（如登录→画像的过渡）
- 踩过的坑及如何避免：LoginView catch块为空导致错误信息依赖隐式拦截器行为，应在catch中添加显式错误处理，提高代码可读性和可维护性
- 最佳实践建议：
  1. 每个里程碑交付物都应有明确的验收检查点清单，逐项对照代码审查
  2. 全链路测试应在开发阶段就考虑，而非等到联调时才发现断裂
  3. 鉴权逻辑应收敛到composable，避免在router/api中分散实现
  4. CSS变量替换硬编码值应作为代码审查的常规检查项
  5. 首次使用引导是用户体验的关键环节，应在架构设计阶段就规划
