# Task 07: 全局样式 + CSS变量 + Agent状态色

## 任务概述

| 项目 | 内容 |
|------|------|
| **版本** | v0.1 |
| **里程碑** | M1 / FM1：项目骨架与基础设施就绪 |
| **涉及层级** | 前端 (frontend) |
| **功能编号** | F1.1, F1.2, F1.3, F1.4, F1.5 |

## 需求描述

创建全局样式文件（styles/variables.scss和styles/global.scss），定义CSS变量体系包括Element Plus主题色覆盖、Agent状态色、布局变量、间距/圆角/阴影/字体变量，全局重置样式、Element Plus组件定制、通用工具类，并在main.ts和vite.config.ts中配置导入。

## 影响范围

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `src/styles/variables.scss` | CSS变量定义（8类变量） |
| 新增 | `src/styles/global.scss` | 全局样式（重置+工具类+组件定制） |
| 修改 | `src/main.ts` | 导入全局样式 |
| 修改 | `vite.config.ts` | 配置SCSS全局注入variables.scss |

## CSS变量体系设计

### variables.scss（8类变量）

| 类别 | 变量 | 值 |
|------|------|-----|
| **Element Plus主题色** | --el-color-primary | #409EFF |
| | --el-color-success | #67C23A |
| | --el-color-warning | #E6A23C |
| | --el-color-danger | #F56C6C |
| | --el-color-info | #909399 |
| **Agent状态色** | --agent-waiting | #C0C4CC |
| | --agent-running | #409EFF |
| | --agent-completed | #67C23A |
| | --agent-failed | #F56C6C |
| **布局** | --header-height | 60px |
| | --sidebar-width | 240px |
| | --content-max-width | 1200px |
| **间距** | --spacing-xs/sm/md/lg/xl | 4/8/16/24/32px |
| **圆角** | --radius-sm/md/lg | 4/8/12px |
| **阴影** | --shadow-sm/md/lg | 3级阴影 |
| **字体** | --font-family / --font-size-sm~xxl | 字体栈+5级字号 |
| **过渡** | --transition-fast/normal | 0.15s/0.3s ease |

### global.scss

| 类别 | 内容 |
|------|------|
| **全局重置** | html/body margin/padding/font-family/color/background |
| **工具类** | .text-ellipsis / .flex-center / .page-container / .section-title |
| **Element Plus定制** | el-card圆角+阴影 / el-button字重 / el-tag圆角 |
| **AI标注样式** | .ai-generated-label |

## 实现要求

- CSS变量命名使用kebab-case
- variables.scss通过vite.config.ts全局注入，组件无需手动@use
- global.scss在main.ts中导入
- Agent状态色与ECharts Agent可视化颜色保持一致
- 禁止在global.scss中编写组件特定样式
- 禁止使用!important覆盖Element Plus样式

## 验收标准

- [ ] variables.scss包含8类CSS变量
- [ ] global.scss包含重置样式、工具类、Element Plus定制、AI标注样式
- [ ] main.ts正确导入global.scss
- [ ] vite.config.ts配置SCSS全局注入
- [ ] npm run dev启动成功，SCSS编译无错误
- [ ] npm run build构建成功
- [ ] Agent状态色变量定义正确

## 验证命令

```bash
cd Veritas/frontend && npm run dev
cd Veritas/frontend && npm run build
```
