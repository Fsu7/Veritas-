# task50_fm5_responsive_layout

> **Day 9 | P2 | 全局模块 | 响应式布局适配（平板+移动端）**

---

## 一、任务概述

### 目标
为前端所有页面增加响应式布局适配，支持平板（768-1024px）和移动端（<768px）。当前所有页面仅针对桌面端（≥1024px）设计，移动端基本不可用。

### 里程碑上下文
- **项目**：XH-202630 科研文献智能助手
- **版本**：v0.5
- **里程碑**：M6 交付就绪 / FM5 功能完善与UI打磨（Week 12 Day 9）
- **功能编号**：F1.1, F1.2, F1.3, F1.4, F1.5

---

## 二、涉及模块

| 模块 | 路径 | 职责 |
|------|------|------|
| variables.scss | `Veritas/frontend/src/styles/variables.scss` | CSS变量定义 |
| mixins.scss | `Veritas/frontend/src/styles/mixins.scss` | 响应式mixin（task49已创建） |
| AppHeader | `Veritas/frontend/src/components/layout/AppHeader.vue` | 顶部导航 |
| SearchView | `Veritas/frontend/src/views/SearchView.vue` | 论文搜索页 |
| CompareView | `Veritas/frontend/src/views/CompareView.vue` | 论文对比页 |
| AgentFlowView | `Veritas/frontend/src/views/AgentFlowView.vue` | Agent可视化页 |
| ReportView | `Veritas/frontend/src/views/ReportView.vue` | 综述报告页 |
| UserCenterView | `Veritas/frontend/src/views/UserCenterView.vue` | 用户中心页 |
| FavoritesView | `Veritas/frontend/src/views/FavoritesView.vue` | 收藏列表页 |

---

## 三、文件变更表

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| modify | `Veritas/frontend/src/styles/variables.scss` | 新增断点变量 `--breakpoint-sm/md/lg/xl` |
| modify | `Veritas/frontend/src/components/layout/AppHeader.vue` | 移动端汉堡菜单 + `el-drawer` 侧边导航 |
| modify | `Veritas/frontend/src/views/SearchView.vue` | 移动端 `FilterPanel` 抽屉化 |
| modify | `Veritas/frontend/src/views/CompareView.vue` | 移动端表格横向滚动 + 固定首列 |
| modify | `Veritas/frontend/src/views/AgentFlowView.vue` | 移动端流程图自适应缩放 + tab面板上下布局 |
| modify | `Veritas/frontend/src/views/ReportView.vue` | 移动端元数据卡单列 |
| modify | `Veritas/frontend/src/views/UserCenterView.vue` | 移动端单列布局 |
| modify | `Veritas/frontend/src/views/FavoritesView.vue` | 移动端单列布局 |

---

## 四、功能要求清单

| ID | 优先级 | 描述 | 验收条件 |
|----|--------|------|---------|
| FR-001 | P0 | `variables.scss` 新增 `--breakpoint-sm: 640px` / `--breakpoint-md: 768px` / `--breakpoint-lg: 1024px` / `--breakpoint-xl: 1280px` | 断点变量定义正确，可被 `respond-to` mixin 使用 |
| FR-002 | P0 | `AppHeader` 移动端（<768px）隐藏 `el-menu mode='horizontal'`，显示汉堡按钮 + `el-drawer` 侧边导航（含 `menuItems` + 用户名 + 退出按钮），drawer 宽度 `var(--sidebar-width)` | 移动端汉堡菜单可点击展开 drawer，导航功能完整 |
| FR-003 | P1 | `SearchView` 移动端 `FilterPanel` 抽屉化：桌面端保持侧边栏；移动端显示"筛选"按钮，点击展开 `el-drawer` 包含 `FilterPanel` | 移动端筛选按钮可展开 drawer，筛选功能正常 |
| FR-004 | P1 | `CompareView` 移动端表格横向滚动（`overflow-x: auto`）+ 固定首列（`position: sticky; left: 0`），表格最小宽度 600px | 移动端表格可横向滚动，首列固定可见 |
| FR-005 | P1 | `AgentFlowView` 移动端流程图自适应缩放（监听 `window resize` 触发 ECharts `resize()`）+ tab 面板上下布局（`flex-direction: column`） | 移动端流程图自适应缩放，tab 面板上下布局 |
| FR-006 | P0 | `ReportView` / `UserCenterView` / `FavoritesView` 移动端单列布局（`el-col :span="24"`） | 移动端三页面单列布局，无横向滚动 |
| FR-007 | P0 | 所有响应式样式使用 `@include respond-to($bp)` mixin，禁止直接写 `@media (max-width: 768px)` | 无直接 `@media` 断点值，全部使用 `respond-to` mixin |
| FR-008 | P2 | 移动端字号缩小一档：`--font-size-xxl` → `--font-size-xl` 等（通过 `respond-to(md)` 覆盖） | 移动端字号缩小一档 |

---

## 五、验收检查点

| ID | 检查点 | 验证方式 |
|----|--------|---------|
| AC-001 | `variables.scss` 新增 `--breakpoint-sm/md/lg/xl` 断点变量 | code_review |
| AC-002 | 平板（768-1024px）布局合理，无横向滚动 | manual_test |
| AC-003 | 移动端（<768px）基本功能可用，无布局错乱 | manual_test |
| AC-004 | 移动端导航可用（汉堡菜单 + drawer 展开/关闭） | manual_test |
| AC-005 | 移动端 `FilterPanel` 抽屉化正常 | manual_test |
| AC-006 | 移动端对比表格横向滚动 + 首列固定 | manual_test |
| AC-007 | 移动端流程图自适应缩放 | manual_test |
| AC-008 | `ReportView` / `UserCenterView` / `FavoritesView` 移动端单列布局 | manual_test |
| AC-009 | 所有响应式代码使用 `@include respond-to($bp)` mixin | code_review |
| AC-010 | 桌面端（≥1024px）现有布局不受影响 | manual_test |
| AC-011 | `lint` + `build` + `test:run` 全部通过 | code_review |

---

## 六、禁止事项

| ID | 禁止行为 | 原因 | 严重度 |
|----|---------|------|--------|
| FA-001 | 输出伪代码或 TODO 注释 | 必须输出完整可执行代码 | critical |
| FA-002 | 修改需求范围外模块（如修改组件业务逻辑） | 本任务仅涉及响应式布局 | high |
| FA-003 | 破坏三层分离架构 | 架构约束 ADR-001 | critical |
| FA-013 | 使用硬编码尺寸值 | 必须使用 CSS 变量 | critical |
| FA-027 | 使用 `@media` 直接写断点值 | 必须用 `@include respond-to($bp)` mixin | critical |
| FA-028 | 破坏桌面端（≥1024px）现有布局 | 响应式变更仅影响 <1024px | high |
| FA-029 | 删除现有 CSS 变量或 mixin | 向后兼容 | high |

---

## 七、验证命令

```bash
cd Veritas/frontend && npm run lint        # 无lint错误
cd Veritas/frontend && npm run build       # 构建成功无SCSS编译错误
cd Veritas/frontend && npm run test:run    # 所有测试通过
```

---

## 八、参考文档

- `AGENTS.md` — 项目全景上下文与前端约束
- `docs/frontend/前端模块系统架构文档.md` — 前端架构规范、响应式设计要求
- `docs/frontend/前端模块项目里程碑文档.md` — FM5 里程碑任务分解（Week 12 Day 9）
- `docs/开发规范文档.md` — 前端编码规范、CSS 规范
- `docs/架构决策记录(ADR).md` — 架构决策
