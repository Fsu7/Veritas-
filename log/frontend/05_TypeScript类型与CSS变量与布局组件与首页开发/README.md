# TypeScript类型定义与CSS变量体系与布局组件与首页开发

## 功能描述
- 解决了前端M1里程碑中基础设施层剩余的4个核心任务（Task 06-09），补全了TypeScript类型体系、CSS变量与全局样式、布局组件和首页功能
- 实现了16个TypeScript接口的完整定义与JSDoc字段映射注释、8类CSS变量体系、全局样式工具类与Element Plus定制、AppHeader/AppFooter布局组件、HomeView首页搜索与LocalStorage历史记录功能
- 业务价值：为后续FM2-FM6所有业务页面提供统一的类型安全、样式一致性和布局骨架基础

## 实现逻辑
- 修改的核心文件列表：
  - `src/types/analysis.ts` — 删除AgentStateInfo，改为从agent.ts导入AgentState，添加JSDoc
  - `src/types/common.ts` — 添加JSDoc注释
  - `src/types/paper.ts` — 添加JSDoc（JSON字段映射：paperId↔paper_id等）
  - `src/types/user.ts` — 添加JSDoc，ProfileResponse枚举字段使用UserProfile['xxx']类型引用
  - `src/types/agent.ts` — 添加JSDoc（intermediateResult↔intermediate_result等）
  - `src/styles/variables.scss` — 补全8类CSS变量（间距/圆角/阴影/字体/过渡）
  - `src/styles/global.scss` — 重写：添加@use导入、CSS变量引用、工具类、EP定制、AI标注
  - `src/components/layout/AppHeader.vue` — 退出按钮添加BEM class
  - `src/components/layout/AppFooter.vue` — 重写：3行信息（项目名/版本号/AI标注），BEM命名
  - `src/views/HomeView.vue` — 重写：集成AppHeader/Footer、userStore登录检查、LocalStorage持久化
  - `src/utils/storage.ts` — 新建：LocalStorage搜索历史管理
  - `vitest.config.ts` — 新建：独立vitest配置（jsdom/CSS/Element Plus inline）
  - `src/__tests__/utils/storage.spec.ts` — 新建：7个测试用例
  - `src/__tests__/views/HomeView.spec.ts` — 新建：6个测试用例
- 使用的算法或设计模式：
  - **BEM命名规范**：block__element--modifier CSS类命名
  - **CSS变量体系**：:root选择器集中定义，Vite additionalData全局注入
  - **LocalStorage搜索历史**：去重+头部插入+10条限制的FIFO策略
  - **shallowMount测试**：Vue Test Utils浅挂载避免Element Plus CSS导入问题
- 关键代码逻辑说明：
  - `analysis.ts`中AgentStateInfo（status:string）→ 从agent.ts导入AgentState（status:'waiting'|'running'|'completed'|'failed'），确保类型安全
  - `global.scss`通过`@use './variables' as *`导入CSS变量，body样式使用`var(--font-family)`等
  - HomeView未登录用户搜索时：ElMessage.warning('请先登录') → router.push('/login')
  - vitest.config.ts独立于vite.config.ts，避免`test`属性与vue-tsc -b构建模式冲突

## 接口变更
### Request
本次不涉及API接口变更，为纯前端基础设施层开发。

### Response
TypeScript类型定义对应后端统一响应格式：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "paper_id": "arxiv_2024_001",
    "title": "Multi-Agent协同决策",
    "authors": ["Zhang San", "Li Si"],
    "abstract": "...",
    "year": 2024,
    "citation_count": 42
  },
  "timestamp": 1716633600000
}
```
前端通过Axios响应拦截器自动将snake_case转换为camelCase。

## 测试结果
- **storage工具测试（7/7通过）**：
  - getRecentSearches：空数据返回空数组 ✅
  - getRecentSearches：正确解析localStorage数据 ✅
  - getRecentSearches：损坏数据返回空数组 ✅
  - saveRecentSearch：新查询插入头部 ✅
  - saveRecentSearch：已存在查询移到头部（去重） ✅
  - saveRecentSearch：超过10条截断 ✅
  - clearRecentSearches：正确清除 ✅
- **HomeView集成测试（6/6通过）**：
  - 渲染AppHeader和AppFooter ✅
  - 渲染搜索标题和区域 ✅
  - 从LocalStorage显示最近搜索 ✅
  - 无搜索历史时不显示最近搜索区域 ✅
  - 未登录用户isLoggedIn为false ✅
  - 点击清除按钮清空搜索历史 ✅
- **构建验证**：
  - `vue-tsc --noEmit`：TypeScript编译无错误 ✅
  - `npm run build`：构建成功 ✅
  - `vitest run`：13/13测试全部通过 ✅

## 相关文件
- `Veritas/frontend/src/types/common.ts`
- `Veritas/frontend/src/types/paper.ts`
- `Veritas/frontend/src/types/user.ts`
- `Veritas/frontend/src/types/analysis.ts`
- `Veritas/frontend/src/types/agent.ts`
- `Veritas/frontend/src/styles/variables.scss`
- `Veritas/frontend/src/styles/global.scss`
- `Veritas/frontend/src/components/layout/AppHeader.vue`
- `Veritas/frontend/src/components/layout/AppFooter.vue`
- `Veritas/frontend/src/views/HomeView.vue`
- `Veritas/frontend/src/utils/storage.ts`
- `Veritas/frontend/vitest.config.ts`
- `Veritas/frontend/src/__tests__/utils/storage.spec.ts`
- `Veritas/frontend/src/__tests__/views/HomeView.spec.ts`
- 配置文件变更：`package.json`（新增jsdom开发依赖）
