# Task 43：画像编辑实时生效 + 历史记录分页搜索增强

> **里程碑**：FM5 功能完善与UI打磨（Week 11 Day 1）
> **优先级**：P1
> **涉及模块**：F1.1 用户界面模块

---

## 一、任务概述

完善用户画像编辑功能（保存后实时生效）+ 增强历史记录查看（分页、关键词搜索、按时间倒序）。

**当前状态**：
- UserCenterView 已实现画像编辑表单和历史记录时间线（最多10条）
- 画像保存后页面画像标签未即时刷新
- 历史记录无分页、无搜索、未明确按时间倒序

**目标**：补全这些 P1 功能，使画像编辑和历史记录达到 FM5 验收标准。

---

## 二、涉及模块

| 模块 | 路径 | 职责 |
|------|------|------|
| UserCenterView | `src/views/UserCenterView.vue` | 用户中心页：用户信息+画像编辑+历史记录 |
| UserProfileForm | `src/components/common/UserProfileForm.vue` | 画像4维度表单组件 |
| userStore | `src/stores/userStore.ts` | 用户状态管理 |
| userApi | `src/api/user.ts` | 用户API |
| sessionApi | `src/api/session.ts` | 会话API（历史记录） |
| usePagination | `src/composables/usePagination.ts` | 分页组合函数（复用） |

---

## 三、文件变更表

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| modify | `Veritas/frontend/src/views/UserCenterView.vue` | 画像保存后同步刷新画像标签；历史记录增加分页+搜索+按时间倒序 |
| modify | `Veritas/frontend/src/components/common/UserProfileForm.vue` | 增加"重置"按钮；保存成功 emit `saved` 事件带 profile 数据 |
| modify | `Veritas/frontend/src/stores/userStore.ts` | 新增 profileVersion 计数器强制刷新计算属性 |
| modify | `Veritas/frontend/src/api/user.ts` | 新增 getHistorySessions（若走 user 维度） |
| modify | `Veritas/frontend/src/api/session.ts` | list 方法支持 q 关键词搜索参数 |

---

## 四、功能要求

| 编号 | 描述 | 优先级 |
|------|------|--------|
| FR-001 | 画像保存成功后，UserCenterView 页面画像标签即时刷新 | P0 |
| FR-002 | 历史记录按 createdAt 倒序展示（最新在最上方） | P0 |
| FR-003 | 历史记录支持分页（每页10条，usePagination） | P1 |
| FR-004 | 历史记录支持关键词搜索（按 topic 模糊匹配，300ms 防抖） | P1 |
| FR-005 | UserProfileForm 增加"重置"按钮，恢复 initialData 初始值 | P2 |
| FR-006 | userStore 新增 profileVersion 计数器，saveProfile 后自增 | P1 |

---

## 五、关键技术约束

1. **分层规范**：View → Store → API，组件内不直接调用 Axios
2. **排序责任**：历史记录按 createdAt 倒序由后端返回，前端仅做展示（禁止前端排序）
3. **CSS 变量**：使用 `var(--spacing-md)` 等 CSS 变量，禁止硬编码尺寸值
4. **防抖**：搜索输入 300ms 防抖，避免频繁请求
5. **响应式刷新**：通过 profileVersion 计数器或 watch profile 实现画像标签刷新

---

## 六、验收检查点

- [ ] AC-001：画像修改保存后，页面画像标签立即反映新值（无需刷新页面）— manual_test
- [ ] AC-002：历史记录按 createdAt 倒序展示，最新会话在第一条 — automated_test
- [ ] AC-003：历史记录分页正常，页码切换无报错，每页10条 — automated_test
- [ ] AC-004：历史记录搜索框输入关键词后结果正确筛选，清空后恢复完整列表 — manual_test
- [ ] AC-005：UserProfileForm 重置按钮可恢复表单到初始值 — automated_test
- [ ] AC-006：所有新增/修改的代码通过 lint 和 build 验证 — code_review

---

## 七、验证命令

```bash
cd Veritas/frontend && npm run test -- --run UserCenterView UserProfileForm
cd Veritas/frontend && npm run lint
cd Veritas/frontend && npm run build
```

---

## 八、参考文档

- `AGENTS.md` — 项目全景上下文与前端约束
- `docs/frontend/前端模块系统架构文档.md` — 前端架构规范、F1.1 用户界面模块设计
- `docs/frontend/前端模块项目里程碑文档.md` — FM5 里程碑任务分解（Week 11 Day 1）
- `docs/开发规范文档.md` — 前端编码规范（View→Store→API 分层、命名规范）
- `docs/架构决策记录(ADR).md` — 架构决策（三层分离、状态管理）
