# task51_fm5_test_coverage_supplement

> **Day 10上午 | P1 | 测试模块 | 缺失测试补全（14份spec）**

---

## 一、任务概述

### 目标
补全前端缺失的单元测试，覆盖 task43-task50 新增/修改的代码。当前已有部分测试，但 7 个视图、2 个 store、2 个 composable、3 个组件共 14 份 spec 缺失。

### 里程碑上下文
- **项目**：XH-202630 科研文献智能助手
- **版本**：v0.5
- **里程碑**：M6 交付就绪 / FM5 功能完善与UI打磨（Week 12 Day 10上午）
- **功能编号**：F1.1, F1.2, F1.3, F1.4, F1.5

---

## 二、涉及模块

### 已有测试（参考模式）
| 类型 | 文件 | 参考价值 |
|------|------|---------|
| 集成测试 | `__tests__/integration/fm4-acceptance.spec.ts` | vi.mock + mount + describe/it 模式 |
| Store测试 | `__tests__/stores/paperStore.spec.ts` | store测试模式（mock api + setActivePinia） |
| Composable测试 | `__tests__/composables/usePagination.spec.ts` | composable测试模式 |
| 组件测试 | `__tests__/components/common/FilterPanel.spec.ts` | 组件测试模式（mount + props + emit + slot） |

### 待补全测试（14份）
| 类型 | 文件 |
|------|------|
| 视图测试 | UserCenterView / LoginView / RegisterView / PaperDetailView / CompareView / ReportView / FavoritesView |
| Store测试 | userStore / agentStore |
| Composable测试 | useAuth / useReplay |
| 组件测试 | EmptyState / ErrorState / ReportEditor |

---

## 三、文件变更表（全部新增）

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| create | `Veritas/frontend/src/__tests__/views/UserCenterView.spec.ts` | 画像保存后刷新、历史记录跳转、setupProfile模式 |
| create | `Veritas/frontend/src/__tests__/views/LoginView.spec.ts` | 表单验证、登录跳转、登录失败提示 |
| create | `Veritas/frontend/src/__tests__/views/RegisterView.spec.ts` | 表单验证、注册跳转、密码确认 |
| create | `Veritas/frontend/src/__tests__/views/PaperDetailView.spec.ts` | 详情加载、收藏切换、错误状态 |
| create | `Veritas/frontend/src/__tests__/views/CompareView.spec.ts` | 对比选择、结果展示、降级提示 |
| create | `Veritas/frontend/src/__tests__/views/ReportView.spec.ts` | 报告加载、编辑模式、导出、引用弹窗 |
| create | `Veritas/frontend/src/__tests__/views/FavoritesView.spec.ts` | 列表加载、分页、空状态 |
| create | `Veritas/frontend/src/__tests__/stores/userStore.spec.ts` | login/logout/fetchProfile/saveProfile + 计算属性 |
| create | `Veritas/frontend/src/__tests__/stores/agentStore.spec.ts` | updateAgentState/resetStates + progress + agentStatesList |
| create | `Veritas/frontend/src/__tests__/composables/useAuth.spec.ts` | 登录状态判断、自动跳转、Token过期处理 |
| create | `Veritas/frontend/src/__tests__/composables/useReplay.spec.ts` | 播放/暂停、进度跳转、倍速切换 |
| create | `Veritas/frontend/src/__tests__/components/common/EmptyState.spec.ts` | Props + Slot + Event |
| create | `Veritas/frontend/src/__tests__/components/common/ErrorState.spec.ts` | Props + Slot + retry Event |
| create | `Veritas/frontend/src/__tests__/components/report/ReportEditor.spec.ts` | 编辑、预览、保存、取消、工具栏 |

---

## 四、功能要求清单

| ID | 优先级 | 描述 | 验收条件 |
|----|--------|------|---------|
| FR-001 | P0 | UserCenterView测试：画像保存后刷新+提示、历史记录跳转、setupProfile模式、空历史状态 | 覆盖正常+边界，测试通过 |
| FR-002 | P0 | LoginView测试：表单验证、登录成功跳转、登录失败提示、已登录跳转 | 覆盖正常+错误，测试通过 |
| FR-003 | P0 | RegisterView测试：表单验证、密码确认、注册成功跳转、注册失败提示 | 覆盖正常+错误+边界，测试通过 |
| FR-004 | P0 | PaperDetailView测试：详情加载、渲染、收藏切换、错误状态+重试 | 覆盖正常+错误，测试通过 |
| FR-005 | P0 | CompareView测试：未登录确认框、未设置画像确认框、对比结果、降级提示 | 覆盖正常+降级，测试通过 |
| FR-006 | P0 | ReportView测试：报告加载、markdown渲染、编辑模式、导出、引用弹窗 | 覆盖正常+编辑+导出，测试通过 |
| FR-007 | P0 | FavoritesView测试：列表加载、分页、空状态、收藏切换后更新 | 覆盖正常+空状态，测试通过 |
| FR-008 | P0 | userStore测试：login持久化+fetchProfile、logout清除、fetchProfile更新、saveProfile更新、计算属性 | 覆盖所有action+getter，测试通过 |
| FR-009 | P0 | agentStore测试：updateAgentState、resetStates、progress计算、agentStatesList | 覆盖所有action+getter，测试通过 |
| FR-010 | P1 | useAuth测试：isLoggedIn、未登录跳转+redirect、Token过期处理 | 覆盖状态+跳转+过期，测试通过 |
| FR-011 | P1 | useReplay测试：play/pause、seek、setSpeed、播放结束暂停（task46未实现则标注待补充） | 覆盖播放控制（或标注），测试通过 |
| FR-012 | P0 | EmptyState测试：Props渲染、action事件、默认slot | 覆盖Props+Slot+Event，测试通过 |
| FR-013 | P0 | ErrorState测试：Props渲染、retry事件、showRetry=false、默认slot | 覆盖Props+Slot+Event，测试通过 |
| FR-014 | P0 | ReportEditor测试：编辑输入、预览切换、保存emit、取消emit、工具栏按钮 | 覆盖编辑+预览+保存+取消+工具栏，测试通过 |
| FR-015 | P1 | 所有测试使用vi.mock隔离外部依赖，无真实网络请求，独立可运行 | 无真实网络请求，独立可重复 |
| FR-016 | P1 | 测试覆盖率≥70% | 覆盖率≥70% |

---

## 五、验收检查点

| ID | 检查点 | 验证方式 |
|----|--------|---------|
| AC-001 | 14份新增测试文件全部创建 | code_review |
| AC-002 | 所有14份新增测试通过（`npm run test:run`） | automated_test |
| AC-003 | 无 `it.skip` / `it.only` | code_review |
| AC-004 | 所有测试使用 `vi.mock` 隔离外部依赖 | code_review |
| AC-005 | 测试覆盖率≥70% | automated_test |
| AC-006 | `npm run lint` 无错误 | code_review |
| AC-007 | 每个测试文件独立可重复运行 | code_review |
| AC-008 | 测试覆盖正常流程+错误流程+边界条件 | code_review |

---

## 六、禁止事项

| ID | 禁止行为 | 原因 | 严重度 |
|----|---------|------|--------|
| FA-001 | 输出伪代码或 TODO 注释 | 必须输出完整可执行测试代码 | critical |
| FA-002 | 修改需求范围外模块（修改被测源代码） | 本任务仅新增测试 | critical |
| FA-003 | 破坏三层分离架构 | 架构约束 ADR-001 | critical |
| FA-029 | 测试中发起真实网络请求 | 必须 `vi.mock` API 模块 | critical |
| FA-030 | 使用 `it.skip` / `it.only` | 必须全部启用 | critical |
| FA-031 | 测试依赖执行顺序 | 必须独立可重复运行 | high |
| FA-033 | 测试中使用真实 localStorage | 必须 `beforeEach` 清理 | high |
| FA-034 | 测试中使用真实 timer | 必须 `vi.useFakeTimers` | medium |

---

## 七、验证命令

```bash
cd Veritas/frontend && npm run test:run              # 所有测试通过（含14份新增）
cd Veritas/frontend && npm run lint                  # 无lint错误
cd Veritas/frontend && npm run test:run -- --coverage # 覆盖率≥70%
```

---

## 八、参考文档

- `AGENTS.md` — 项目全景上下文与前端测试规范
- `docs/frontend/前端模块系统架构文档.md` — 前端架构规范、组件/Store/Composable设计
- `docs/frontend/前端模块项目里程碑文档.md` — FM5 里程碑任务分解（Week 12 Day 10上午）
- `docs/开发规范文档.md` — 前端测试规范、vitest 使用规范
- `docs/架构决策记录(ADR).md` — 架构决策
