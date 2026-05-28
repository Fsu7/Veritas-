# Task19: AnalysisCard + 5维度展示 + 触发分析

## 任务概述
实现AnalysisCard分析卡片业务组件和PlainExplanation通俗解释组件。AnalysisCard展示5维度结构化分析结果，支持降级标签、通俗解释条件渲染、操作按钮上行。同时将PaperDetailView中的5维度占位替换为AnalysisCard组件集成。

## 里程碑
FM3：论文分析+对比页面可用

## 涉及模块
- F1.3.2 智能分析（5维度结构化展示）
- F1.3.3 通俗解释（初级/中级用户自动展示）

## 文件变更
| 操作 | 文件 | 说明 |
|------|------|------|
| 新增 | Veritas/frontend/src/components/analysis/AnalysisCard.vue | 5维度分析卡片组件 |
| 新增 | Veritas/frontend/src/components/analysis/PlainExplanation.vue | 通俗解释组件 |
| 修改 | Veritas/frontend/src/views/PaperDetailView.vue | 集成AnalysisCard替换占位文本 |

## 功能要求

### P0 - 必须实现
1. **AnalysisCard Props**: `analysis: AnalysisResult; showPlainExplanation?: boolean`
2. **AnalysisCard Emits**: `generate-report(analysisId)`, `select-compare(analysisId)`
3. **5维度展示**: 🎯研究问题/🔧核心方法/🧪主要实验/📊核心结论/⚠️局限性，v-for渲染
4. **通俗解释**: showPlainExplanation=true且有plainExplanation时渲染PlainExplanation组件
5. **操作按钮**: [生成综述]emit('generate-report')、[选择对比]emit('select-compare')
6. **PlainExplanation**: el-alert type='info'包裹，前缀'💡 通俗理解：'
7. **PaperDetailView集成**: 替换5维度占位文本为AnalysisCard组件
8. **BEM样式**: analysis-card__* / plain-explanation__* 类名规范

### P1 - 应该实现
1. **降级标签**: degraded=true时显示el-tag '部分降级'+原因
2. **AI内容标注**: header显示'AI智能分析 · AI生成，仅供参考'

## 5维度展示格式
```
┌─── 🤖 AI智能分析 · AI生成，仅供参考 ──────┐
│                                             │
│  🎯 研究问题                                │
│  如何实现多个大语言模型Agent的高效协同？      │
│                                             │
│  🔧 核心方法                                │
│  基于图结构的Agent编排框架...                │
│                                             │
│  🧪 主要实验                                │
│  在4个基准数据集上进行评测...                │
│                                             │
│  📊 核心结论                                │
│  多Agent协同在复杂任务上优于单Agent...       │
│                                             │
│  ⚠️ 局限性                                  │
│  未考虑Agent间的通信开销...                  │
│                                             │
│  ┌─── 💡 通俗理解 ───────────────────┐     │  ← 仅beginner/intermediate
│  │  这篇论文就像在研究"如何让多个AI    │     │
│  │  助手合作完成一项复杂任务"...       │     │
│  └────────────────────────────────────┘     │
│                                             │
│                    [生成综述] [选择对比]      │
└─────────────────────────────────────────────┘
```

## 验收标准
- [ ] 5维度完整展示（图标+标签+内容）
- [ ] 降级标签正确显示/隐藏
- [ ] 通俗解释根据showPlainExplanation条件渲染
- [ ] 操作按钮emit事件正确，传递analysisId
- [ ] AI内容标注'AI生成，仅供参考'
- [ ] PaperDetailView成功集成AnalysisCard
- [ ] AnalysisCard可复用（不依赖Store/API）
- [ ] BEM命名+CSS变量+8px间距
- [ ] TypeScript类型检查通过
- [ ] 单组件≤300行
