# 技术教学文档

## 开发思路
- 需求分析过程：本次开发承接task00-05创建的Vue3项目骨架，补全M1里程碑剩余的4个基础设施任务。分析发现所有文件已存在但内容不完整——类型文件缺少JSDoc映射注释、CSS变量缺少5类变量、全局样式缺少工具类和EP定制、AppFooter缺少版本号和AI标注、HomeView缺少登录检查和LocalStorage持久化
- 技术选型考虑：
  - CSS变量体系选择`:root`选择器集中定义，配合Vite `additionalData`全局注入，避免每个组件手动`@use`
  - 搜索历史选择LocalStorage而非Pinia Store，因为历史记录是持久化需求、无需跨组件响应式共享
  - 测试框架选择vitest + jsdom环境 + shallowMount，避免Element Plus CSS导入问题
- 架构设计思路：按照自底向上原则执行——types（类型基础）→ styles（样式基础）→ layout（布局组件）→ views（页面+测试）
- 遇到的问题及解决方案：
  1. `analysis.ts`中`AgentStateInfo`使用`status: string`而非联合类型 → 删除并从`agent.ts`导入`AgentState`
  2. vitest配置与vue-tsc -b构建模式冲突 → 分离为独立的`vitest.config.ts`
  3. Element Plus CSS导入导致测试超时 → 使用`shallowMount`替代`mount`，stub所有子组件
  4. vitest `deps.inline`已弃用警告 → 迁移到`server.deps.inline`

## 实现步骤
1. **Task 06 类型修复**：修复`analysis.ts`中的`AgentStateInfo`→`AgentState`导入，为5个类型文件添加JSDoc注释标注JSON snake_case字段映射
2. **Task 07 CSS变量补全**：在`variables.scss`中补充间距/圆角/阴影/字体/过渡5类变量，重写`global.scss`添加`@use`导入、CSS变量引用、4个工具类（text-ellipsis/flex-center/page-container/section-title）、3个EP定制（el-card/el-button/el-tag）、1个AI标注类
3. **Task 08 布局组件**：AppHeader添加`app-header__logout` BEM class，AppFooter重写为3行结构（项目名+版本号+AI标注）+居中对齐+BEM命名
4. **Task 09 首页与测试**：创建`utils/storage.ts`实现LocalStorage搜索历史管理（去重+10条限制），重写HomeView集成AppHeader/Footer/userStore登录检查/LocalStorage，编写13个测试用例

## 解决了什么问题
- 核心问题描述：
  1. `AgentStateInfo`类型不安全（`status: string`而非联合类型），导致Store和组件无法正确类型约束
  2. CSS变量体系不完整，组件中硬编码颜色/间距/字体值，维护成本高
  3. AppFooter信息不完整，缺少版本号和AI内容标注（安全合规要求）
  4. HomeView未集成布局组件和登录检查，未登录用户可直接进入搜索页
- 解决方案对比：
  - vitest配置方案A：在`vite.config.ts`中用`/// <reference types="vitest" />` → 与vue-tsc -b冲突
  - vitest配置方案B：独立`vitest.config.ts` → ✅ 构建和测试互不干扰
- 最终方案的优势：配置分离使`npm run build`和`npm run test`各自使用正确的类型上下文

## 变更内容
### 新增文件
- `Veritas/frontend/src/utils/storage.ts` — LocalStorage搜索历史管理（getRecentSearches/saveRecentSearch/clearRecentSearches）
- `Veritas/frontend/vitest.config.ts` — 独立vitest配置（jsdom环境/关闭CSS/Element Plus inline）
- `Veritas/frontend/src/__tests__/utils/storage.spec.ts` — storage工具7个测试用例
- `Veritas/frontend/src/__tests__/views/HomeView.spec.ts` — HomeView 6个集成测试用例

### 修改文件
- `src/types/analysis.ts` — 删除`AgentStateInfo`，改为从`agent.ts`导入`AgentState`；添加6个interface的JSDoc注释
- `src/types/common.ts` — 添加ApiResponse/PageResponse的JSDoc
- `src/types/paper.ts` — 添加Paper/FilterParams的JSDoc（字段映射：paperId↔paper_id等）
- `src/types/user.ts` — 添加UserProfile/LoginResponse/ProfileResponse的JSDoc
- `src/types/agent.ts` — 添加AgentState/FlowData/FlowNode/FlowLink的JSDoc
- `src/styles/variables.scss` — 补充5类变量（间距5个/圆角3个/阴影3个/字体6个/过渡2个）
- `src/styles/global.scss` — 重写：添加@use、body CSS变量、4个工具类、3个EP定制、1个AI标注
- `src/components/layout/AppHeader.vue` — 退出按钮添加`app-header__logout` class
- `src/components/layout/AppFooter.vue` — 重写：3行信息+居中+BEM+#f5f7fa背景
- `src/views/HomeView.vue` — 重写：集成AppHeader/Footer/userStore/storage/ElMessage/登录检查

### 配置变更
- `package.json` — 新增`jsdom`开发依赖（vitest测试环境需要）
- `vitest.config.ts` — 新增独立vitest配置文件

## 关键技术点
- **CSS变量全局注入**：Vite `css.preprocessorOptions.scss.additionalData`配置`@use "@/styles/variables.scss" as *`，所有SCSS文件自动获取变量访问权限
- **BEM命名规范**：`.app-header__logo`（block__element）、`.app-footer__ai-label`（block__element），保持CSS可维护性
- **跨系统字段映射**：TypeScript camelCase ↔ JSON snake_case，通过JSDoc注释标注映射关系（如`@field paperId ↔ paper_id`），Axios响应拦截器自动转换
- **联合字面量类型 vs enum**：项目规范使用`'waiting' | 'running' | 'completed' | 'failed'`而非`enum`关键字，确保类型安全和tree-shaking友好
- **shallowMount测试策略**：Vue Test Utils的shallowMount自动stub子组件，避免Element Plus CSS导入问题，同时仍可验证组件结构和行为

## 经验总结
- 开发过程中的收获：
  1. CSS变量体系化设计大幅减少硬编码值，后续换主题只需修改`variables.scss`
  2. vitest与vite配置分离是必要的，vue-tsc -b构建模式不认识vitest的`test`属性
  3. `shallowMount` + stub策略是测试含Element Plus组件的最佳实践
- 踩过的坑及如何避免：
  1. **vitest defineConfig冲突**：`import { defineConfig } from 'vitest/config'`会引入与vite不同版本的Plugin类型 → 解决：使用独立`vitest.config.ts`
  2. **Element Plus CSS测试超时**：`vi.mock('element-plus', async (importOriginal) => ...)`在jsdom中导入CSS会卡住 → 解决：使用`shallowMount`自动stub
  3. **deps.inline弃用**：vitest 3.x中`deps.inline`已弃用 → 解决：迁移到`server.deps.inline`
  4. **jsdom缺失**：vitest默认Node环境无localStorage → 解决：安装jsdom并配置`environment: 'jsdom'`
- 最佳实践建议：
  1. 每次修改类型文件后立即运行`vue-tsc --noEmit`验证类型完整性
  2. CSS变量命名使用kebab-case（如`--agent-waiting`），与CSS规范一致
  3. 全局样式仅包含重置和工具类，组件样式写在scoped style中
  4. 测试文件与源码放在对应目录结构中（`__tests__/utils/`、`__tests__/views/`）
