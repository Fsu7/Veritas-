# FM3-Task21 PlainExplanation 通俗解释组件

## 任务概述
实现 `PlainExplanation.vue` 通俗解释组件：在 AnalysisCard 中根据用户知识水平（`beginner` / `intermediate` 自动展示；`advanced` / `expert` 隐藏）显示由 AI 后端生成的 `plain_explanation` 字段，支持加载/为空/错误三种状态，保持单文件 ≤ 300 行。

## 里程碑
FM3：论文分析与对比页面完成（v0.3）

## 涉及模块
- `components/analysis/PlainExplanation.vue`（新增/覆盖）
- `components/analysis/AnalysisCard.vue`（父级，已具备控制逻辑）
- `types/analysis.ts`（`StructuredAnalysis.plainExplanation`）
- `stores/userStore.ts`（父级按 `profile.knowledgeLevel` 决策）

## 文件变更
| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | `Veritas/frontend/src/components/analysis/PlainExplanation.vue` | 完整实现组件 |

## 功能要求
1. **FR-001** Props：`content: string`（必填）、`loading?: boolean`、`error?: string | null`、`collapsible?: boolean`、`defaultCollapsed?: boolean`、`maxLength?: number`（默认 600）
2. **FR-002** 状态机：
   - `loading=true` → `el-skeleton` 3 行占位
   - `error` 非空 → `el-alert type=error`
   - `content` 空白 → `el-empty description='暂无通俗解释'`
   - 正常 → `el-alert type=info` 标题 `💡 通俗理解`，超长可折叠
3. **FR-003** 父级 `AnalysisCard` 已用 `v-if` 控制渲染，组件内部不读取 userStore
4. **FR-004** 样式：scoped + BEM 命名（`plain-explanation__*`），全部使用 CSS 变量
5. **FR-005** 可访问性：`role="note"`、`aria-live="polite"`、图标按钮 `aria-label`

## 跨系统一致性
- `plainExplanation` ↔ `plain_explanation`，前端 props 保持 camelCase

## 验收标准
- [ ] 4 种状态正确切换
- [ ] AnalysisCard 中 `showPlainExplanation=false` 不渲染，`true` 且有 `plainExplanation` 时渲染
- [ ] 组件代码 ≤ 300 行
- [ ] 样式全部使用 CSS 变量，无硬编码颜色
- [ ] `npx vue-tsc --noEmit` 通过
- [ ] `npx vitest run PlainExplanation.spec.ts` 通过

## 验证命令
```bash
cd Veritas/frontend && npx vue-tsc --noEmit
cd Veritas/frontend && npx vitest run src/__tests__/components/analysis/PlainExplanation.spec.ts
```
