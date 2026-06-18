# task52_fm5_integration_acceptance

> **Day 10下午 | P0 | 全局模块 | FM5集成验收测试（13项检查点）**

---

## 一、任务概述

### 目标
FM5 功能完善与UI打磨里程碑的集成验收测试。FM5 共 10 份任务（task43-task52），覆盖 13 项验收检查点。本次任务新建 `fm5-acceptance.spec.ts`，参考 `fm4-acceptance.spec.ts` 模式，确保 FM5 全部交付物通过验收。

### 里程碑上下文
- **项目**：XH-202630 科研文献智能助手
- **版本**：v0.5
- **里程碑**：M6 交付就绪 / FM5 功能完善与UI打磨（验收里程碑，Week 12 Day 10下午）
- **功能编号**：F1.1, F1.2, F1.3, F1.4, F1.5

---

## 二、涉及模块

### 参考文件
| 文件 | 参考价值 |
|------|---------|
| `__tests__/integration/fm4-acceptance.spec.ts` | vi.mock + mount + describe/it 模式（15项AC） |
| `__tests__/integration/fullChain.spec.ts` | 跨 Store 协作测试模式 |

### FM5 验收检查点对应模块
| AC | 检查点 | 对应模块 |
|----|--------|---------|
| AC-001 | 画像编辑实时生效 | UserCenterView（task43） |
| AC-002 | 历史记录分页+搜索 | UserCenterView（task43） |
| AC-003 | 论文收藏/取消收藏 | PaperCard + paperStore |
| AC-004 | 收藏列表展示 | FavoritesView（task44） |
| AC-005 | 综述内容编辑 | ReportView + ReportEditor（task45） |
| AC-006 | 编辑后导出 | ExportPanel（task45） |
| AC-007 | Agent流程回放 | AgentFlowView + useReplay（task46） |
| AC-008 | 退出登录Token黑名单 | AppHeader + userStore（task47） |
| AC-009 | UI统一 | variables.scss + mixins.scss + global.scss（task49） |
| AC-010 | 空状态设计 | EmptyState（task48） |
| AC-011 | 错误状态设计 | ErrorState（task48） |
| AC-012 | 响应式布局 | variables.scss + mixins.scss（task50） |
| AC-013 | P0功能100%通过 | 汇总P0检查点 |

---

## 三、文件变更表

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| create | `Veritas/frontend/src/__tests__/integration/fm5-acceptance.spec.ts` | FM5 验收集成测试（13项检查点） |

---

## 四、功能要求清单

| ID | 优先级 | 描述 | 验收条件 |
|----|--------|------|---------|
| FR-001 | P0 | 包含13项验收检查点（AC-001~AC-013），每项对应一个describe块 | 13个describe块全部存在 |
| FR-002 | P0 | AC-001画像编辑实时生效：mount UserCenterView，mock saveProfile成功，验证fetchProfile调用+profile标签更新 | 画像保存后profile刷新验证通过 |
| FR-003 | P0 | AC-002历史记录分页+搜索：mount UserCenterView，mock sessionApi.list返回分页数据，验证分页切换+关键词搜索触发API | 分页+搜索功能验证通过 |
| FR-004 | P0 | AC-003论文收藏/取消收藏：mount PaperCard，mock toggleFavorite，验证收藏按钮点击触发toggleFavorite+状态切换 | 收藏切换功能验证通过 |
| FR-005 | P0 | AC-004收藏列表展示：mount FavoritesView，mock fetchFavorites返回列表，验证列表渲染+分页 | 收藏列表渲染验证通过 |
| FR-006 | P0 | AC-005综述内容编辑：mount ReportView，验证编辑按钮切换编辑模式+ReportEditor渲染+保存调用saveReportContent | 编辑模式+保存功能验证通过 |
| FR-007 | P1 | AC-006编辑后导出：mount ExportPanel，传入customContent，验证导出使用customContent | 编辑后导出功能验证通过 |
| FR-008 | P1 | AC-007 Agent流程回放：mount AgentFlowView，验证回放模式+useReplay控制（task46未实现则标注待补充） | 回放功能验证通过（或标注） |
| FR-009 | P0 | AC-008退出登录Token黑名单：mount AppHeader，mock userApi.logout，验证退出调用logout+清除状态+跳转Login | 退出登录+Token黑名单验证通过 |
| FR-010 | P1 | AC-009 UI统一：验证variables.scss/mixins.scss/global.scss包含所需变量/mixin/工具类（import无错误） | UI统一验证通过 |
| FR-011 | P0 | AC-010空状态设计：mount EmptyState，验证Props渲染+action按钮emit('action') | EmptyState渲染+事件验证通过 |
| FR-012 | P0 | AC-011错误状态设计：mount ErrorState，验证Props渲染+retry按钮emit('retry')+showRetry=false隐藏 | ErrorState渲染+事件验证通过 |
| FR-013 | P1 | AC-012响应式布局：验证variables.scss包含--breakpoint-*变量+mixins.scss respond-to mixin存在 | 响应式基础设施验证通过 |
| FR-014 | P0 | AC-013 P0功能100%通过：汇总AC-001/002/003/004/005/008/010/011的P0检查点 | 所有P0检查点验证通过 |
| FR-015 | P1 | 使用vi.mock mock所有外部依赖，参考fm4-acceptance.spec.ts的mock基础设施 | 所有外部依赖被mock |
| FR-016 | P1 | 每个describe块包含至少一个it，测试名称使用中文描述 | 13个describe块均有it |

---

## 五、验收检查点

| ID | 检查点 | 验证方式 |
|----|--------|---------|
| AC-001 | `fm5-acceptance.spec.ts` 包含13项验收检查点 | code_review |
| AC-002 | 所有13项检查点测试通过（`npm run test:run`） | automated_test |
| AC-003 | 测试覆盖FM5检查清单全部13项 | code_review |
| AC-004 | `npm run test:run` 全部通过 | automated_test |
| AC-005 | 无 `it.skip` / `it.only` | code_review |
| AC-006 | 所有外部依赖使用 `vi.mock` 隔离 | code_review |
| AC-007 | 每个describe块包含至少一个it，测试名称使用中文描述 | code_review |
| AC-008 | `npm run lint` 无错误 | code_review |

---

## 六、禁止事项

| ID | 禁止行为 | 原因 | 严重度 |
|----|---------|------|--------|
| FA-001 | 输出伪代码或 TODO 注释 | 必须输出完整可执行测试代码 | critical |
| FA-002 | 修改需求范围外模块（修改源代码） | 本任务仅新增集成测试 | critical |
| FA-003 | 破坏三层分离架构 | 架构约束 ADR-001 | critical |
| FA-029 | 测试中发起真实网络请求 | 必须 `vi.mock` API 模块 | critical |
| FA-030 | 使用 `it.skip` / `it.only` | 必须全部启用 | critical |
| FA-032 | 遗漏13项检查点中的任何一项 | FM5验收完整性 | critical |
| FA-035 | 测试依赖执行顺序 | 必须独立可重复运行 | high |

---

## 七、验证命令

```bash
cd Veritas/frontend && npm run test:run   # 所有测试通过（含fm5-acceptance.spec.ts的13项检查点）
cd Veritas/frontend && npm run lint       # 无lint错误
```

---

## 八、参考文档

- `AGENTS.md` — 项目全景上下文与前端测试规范
- `docs/frontend/前端模块系统架构文档.md` — 前端架构规范、FM5交付物清单
- `docs/frontend/前端模块项目里程碑文档.md` — FM5里程碑验收检查点（13项）
- `docs/开发规范文档.md` — 前端测试规范、集成测试规范
- `docs/架构决策记录(ADR).md` — 架构决策
