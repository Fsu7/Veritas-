<script setup lang="ts">
import PlainExplanation from './PlainExplanation.vue'
import type { AnalysisResult } from '@/types/analysis'

withDefaults(defineProps<{
  analysis: AnalysisResult
  showPlainExplanation?: boolean
}>(), {
  showPlainExplanation: false
})

const emit = defineEmits<{
  (e: 'generate-report', analysisId: string): void
  (e: 'select-compare', analysisId: string): void
}>()

const DIMENSIONS = [
  { key: 'researchQuestion' as const, label: '研究问题', icon: '🎯' },
  { key: 'coreMethod' as const, label: '核心方法', icon: '🔧' },
  { key: 'keyExperiments' as const, label: '主要实验', icon: '🧪' },
  { key: 'coreFindings' as const, label: '核心结论', icon: '📊' },
  { key: 'limitations' as const, label: '局限性', icon: '⚠️' },
] as const
</script>

<template>
  <el-card class="analysis-card" shadow="hover">
    <div class="analysis-card__header">
      <span class="analysis-card__header-title">🤖 AI智能分析</span>
      <el-text type="info" size="small">AI生成，仅供参考</el-text>
      <el-tag
        v-if="analysis.degraded"
        type="warning"
        size="small"
        class="analysis-card__degraded"
      >
        部分降级
      </el-tag>
      <el-text
        v-if="analysis.degradedReason"
        type="warning"
        size="small"
      >
        {{ analysis.degradedReason }}
      </el-text>
    </div>

    <div v-if="analysis.result?.analysis">
      <div
        v-for="dim in DIMENSIONS"
        :key="dim.key"
        class="analysis-card__dimension"
      >
        <h4 class="analysis-card__dimension-title">{{ dim.icon }} {{ dim.label }}</h4>
        <p class="analysis-card__dimension-content">{{ analysis.result.analysis[dim.key] }}</p>
      </div>
    </div>

    <PlainExplanation
      v-if="showPlainExplanation && analysis.result?.analysis?.plainExplanation"
      :content="analysis.result.analysis.plainExplanation"
    />

    <div class="analysis-card__actions">
      <el-button
        type="primary"
        size="small"
        @click="emit('generate-report', analysis.analysisId)"
      >
        生成综述
      </el-button>
      <el-button
        size="small"
        @click="emit('select-compare', analysis.analysisId)"
      >
        选择对比
      </el-button>
    </div>
  </el-card>
</template>

<style scoped lang="scss">
.analysis-card {
  border-radius: var(--radius-md, 8px);
}

.analysis-card__header {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--spacing-sm, 8px);
  margin-bottom: var(--spacing-md, 16px);
  padding-bottom: var(--spacing-md, 16px);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.analysis-card__header-title {
  font-size: var(--font-size-lg, 16px);
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.analysis-card__degraded {
  margin-left: var(--spacing-sm, 8px);
}

.analysis-card__dimension {
  margin-bottom: var(--spacing-md, 16px);
}

.analysis-card__dimension-title {
  font-size: var(--font-size-lg, 16px);
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0 0 var(--spacing-sm, 8px);
}

.analysis-card__dimension-content {
  color: var(--el-text-color-regular);
  line-height: 1.8;
  margin: 0;
}

.analysis-card__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm, 8px);
  margin-top: var(--spacing-md, 16px);
  padding-top: var(--spacing-md, 16px);
  border-top: 1px solid var(--el-border-color-lighter);
}
</style>
