# FM2里程碑审阅与关键缺陷修复

## 功能描述
- 对FM2（用户界面与论文检索页面可用）里程碑的16个验收检查点进行逐项代码审查
- 发现2个Critical级缺陷（首次登录引导画像设置流程缺失、useAuth鉴权组合函数未创建）、1个High级缺陷（画像保存后跳转首页逻辑缺失）、3个Medium级缺陷（LoginView catch块为空、AppHeader硬编码颜色、HomeView硬编码样式值）、1个Low级缺陷（PaperDetailView内联样式）
- 修复全部7个缺陷，使FM2交付物完成度从86.7%提升至100%，验收检查点通过率从75%提升至100%
- 业务价值：确保注册→登录→画像→检索→详情→分析全链路代码层面贯通，为后端联调做好准备

## 实现逻辑
- 修改的核心文件列表：
  - `src/composables/useAuth.ts`（新建）— 封装鉴权组合函数
  - `src/views/LoginView.vue` — 使用useAuth实现首次登录引导
  - `src/views/UserCenterView.vue` — 支持setupProfile引导提示和保存后跳转
  - `src/components/layout/AppHeader.vue` — 替换硬编码颜色为CSS变量
  - `src/views/HomeView.vue` — 替换硬编码样式值为CSS变量
  - `src/views/PaperDetailView.vue` — 提取内联样式为CSS类
- 使用的设计模式：Composable模式（useAuth）、Query参数状态传递（setupProfile=true）
- 关键代码逻辑说明：
  - useAuth.redirectAfterLogin()：登录成功后检查hasProfile，无画像跳转UserCenter?setupProfile=true
  - UserCenterView：检测setupProfile查询参数，显示引导提示，保存后自动跳转首页
  - Axios拦截器AUTH_WHITELIST机制：登录接口401不触发全局登出

## 接口变更
### Request
无新增API接口，本次为纯前端逻辑修复

### Response
无变更

## 测试结果
- TypeScript typecheck：0 errors ✅
- Vitest单元测试：66/66 tests passed (7 test files) ✅
- FM2验收检查点逐项审查：16/16 通过 ✅
- FM2交付物完成度：15/15 (100%) ✅
- 是否通过：是

## 相关文件
- `src/composables/useAuth.ts`（新建）
- `src/views/LoginView.vue`（修改）
- `src/views/UserCenterView.vue`（修改）
- `src/components/layout/AppHeader.vue`（修改）
- `src/views/HomeView.vue`（修改）
- `src/views/PaperDetailView.vue`（修改）
- `.trae/documents/fm2-frontend-milestone-review.md`（审阅计划文档）
