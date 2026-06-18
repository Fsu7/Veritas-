# Task 49：UI 设计系统统一打磨

> **里程碑**：FM5 功能完善与UI打磨（Week 11 Day 7-8）
> **优先级**：P1
> **涉及模块**：全局（样式系统）

---

## 一、任务概述

UI 设计系统统一打磨。当前 variables.scss 已定义 CSS 变量（颜色/间距/圆角/阴影/字号），但部分组件仍使用硬编码值（如 HomeView 的 48px 标题、AgentFlowChart 的 450px 高度、TimeStats 的 400px 高度），缺少 mixins.scss 常用 mixin，global.scss 工具类不完整。

**目标**：补充 variables.scss 缺失变量、新建 mixins.scss、补充 global.scss 工具类、清理所有组件硬编码尺寸值统一使用 CSS 变量。

---

## 二、涉及模块

| 模块 | 路径 | 职责 |
|------|------|------|
| variables.scss | `src/styles/variables.scss` | CSS 变量（补充） |
| mixins.scss | `src/styles/mixins.scss` | SCSS mixin（新建） |
| global.scss | `src/styles/global.scss` | 工具类（补充） |
| HomeView | `src/views/HomeView.vue` | 清理硬编码 48px |
| AgentFlowChart | `src/components/agent/AgentFlowChart.vue` | 清理硬编码 450px |
| TimeStats | `src/components/agent/TimeStats.vue` | 清理硬编码 400px |
| 其他页面/组件 | 各 views/components | 清理硬编码值 |

---

## 三、文件变更表

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| modify | `Veritas/frontend/src/styles/variables.scss` | 补充 --chart-height-*/--font-size-display/--breakpoint-* |
| create | `Veritas/frontend/src/styles/mixins.scss` | 新建 respond-to/text-truncate/flex-center mixin |
| modify | `Veritas/frontend/src/styles/global.scss` | 补充 .card-shadow/.text-primary 等工具类 |
| modify | `Veritas/frontend/src/views/HomeView.vue` | 48px → var(--font-size-display) |
| modify | `Veritas/frontend/src/components/agent/AgentFlowChart.vue` | 450px → var(--chart-height-lg) |
| modify | `Veritas/frontend/src/components/agent/TimeStats.vue` | 400px → var(--chart-height-md) |
| modify | 其他含硬编码值的组件 | 统一使用 CSS 变量 |

---

## 四、功能要求

| 编号 | 描述 | 优先级 |
|------|------|--------|
| FR-001 | variables.scss 补充 --chart-height-lg/md/sm、--font-size-display、--breakpoint-* | P0 |
| FR-002 | mixins.scss 新建 respond-to/text-truncate/flex-center mixin | P1 |
| FR-003 | global.scss 补充 .card-shadow/.text-primary/.text-secondary 等工具类 | P1 |
| FR-004 | 清理 HomeView/AgentFlowChart/TimeStats 硬编码值 | P0 |
| FR-005 | 全局扫描清理所有硬编码尺寸值 | P0 |
| FR-006 | 统一按钮尺寸（small/default/large） | P1 |
| FR-007 | 统一表单间距 | P2 |

---

## 五、关键技术约束

1. **仅样式变更**：本任务仅修改 `<style>` 块和 styles/ 目录，不修改组件 `<script>` 逻辑
2. **CSS 变量**：所有尺寸值必须使用 CSS 变量（间距/字号/圆角/阴影/颜色）
3. **向后兼容**：仅新增/扩展变量和工具类，不删除现有定义
4. **不修改 template**：避免引入布局变更，仅修改样式
5. **mixin 复用**：mixins.scss 通过 `@use` 引入到需要的组件

---

## 六、验收检查点

- [ ] AC-001：variables.scss 补充 --chart-height-*/--font-size-display/--breakpoint-* — code_review
- [ ] AC-002：mixins.scss 新建 respond-to/text-truncate/flex-center mixin — code_review
- [ ] AC-003：global.scss 补充 .card-shadow/.text-primary 等工具类 — code_review
- [ ] AC-004：无硬编码尺寸值（所有 px/rem 替换为 CSS 变量） — code_review
- [ ] AC-005：间距/字号/颜色/圆角/阴影全统一 — manual_test
- [ ] AC-006：视觉风格一致（无布局错乱） — manual_test
- [ ] AC-007：所有新增/修改的代码通过 lint 和 build 验证 — code_review

---

## 七、验证命令

```bash
cd Veritas/frontend && npm run lint
cd Veritas/frontend && npm run build
cd Veritas/frontend && npm run test
```

---

## 八、参考文档

- `AGENTS.md` — 项目全景上下文与前端约束
- `docs/frontend/前端模块系统架构文档.md` — 前端架构规范、样式规范、CSS 变量定义
- `docs/frontend/前端模块项目里程碑文档.md` — FM5 里程碑任务分解（Week 11 Day 6-7）
- `docs/开发规范文档.md` — 前端编码规范、CSS 规范
- `docs/架构决策记录(ADR).md` — 架构决策
