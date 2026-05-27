<script setup lang="ts">
import type { Paper } from '@/types/paper'

const props = withDefaults(defineProps<{
  paper: Paper
  selectable?: boolean
  selected?: boolean
  isFavorited?: boolean
}>(), {
  selectable: false,
  selected: false,
  isFavorited: false
})

const emit = defineEmits<{
  (e: 'select', paperId: string): void
  (e: 'analyze', paperId: string): void
  (e: 'favorite', paperId: string): void
}>()

function truncateText(text: string, maxLength: number = 200): string {
  if (!text) return ''
  return text.length > maxLength ? text.slice(0, maxLength) + '...' : text
}

function formatMeta(): string {
  const parts: string[] = []
  if (props.paper.authors?.length) {
    parts.push(props.paper.authors.join(', '))
  }
  if (props.paper.year) {
    parts.push(String(props.paper.year))
  }
  if (props.paper.venue) {
    parts.push(props.paper.venue)
  }
  return parts.join(' · ')
}

function formatScore(score: number): string {
  return `相关度 ${Math.round(score * 100)}%`
}
</script>

<template>
  <el-card class="paper-card" :class="{ 'paper-card--selected': selected }" shadow="hover">
    <div class="paper-card__header">
      <h3 class="paper-card__title" @click="emit('select', paper.paperId)">
        {{ paper.title }}
      </h3>
      <el-tag
        v-if="paper.score != null"
        class="paper-card__score"
        type="success"
        size="small"
      >
        {{ formatScore(paper.score) }}
      </el-tag>
    </div>

    <div v-if="formatMeta()" class="paper-card__meta">
      {{ formatMeta() }}
    </div>

    <p class="paper-card__abstract">{{ truncateText(paper.abstract) }}</p>

    <div v-if="paper.keywords?.length" class="paper-card__keywords">
      <el-tag
        v-for="kw in paper.keywords.slice(0, 3)"
        :key="kw"
        size="small"
        type="info"
      >
        {{ kw }}
      </el-tag>
    </div>

    <div v-if="paper.recommendReason" class="paper-card__recommend">
      <el-text type="warning" size="small">推荐理由：</el-text>
      <el-text type="info" size="small">{{ paper.recommendReason }}</el-text>
    </div>

    <div class="paper-card__actions">
      <el-button size="small" type="primary" @click="emit('analyze', paper.paperId)">
        分析
      </el-button>
      <el-button
        size="small"
        :type="isFavorited ? 'danger' : 'default'"
        @click="emit('favorite', paper.paperId)"
      >
        {{ isFavorited ? '已收藏' : '收藏' }}
      </el-button>
    </div>
  </el-card>
</template>

<style scoped lang="scss">
.paper-card {
  margin-bottom: var(--spacing-md);
}

.paper-card--selected {
  border-color: var(--el-color-primary);
}

.paper-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
}

.paper-card__title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--el-text-color-primary);
  cursor: pointer;
  margin: 0;
  flex: 1;
  line-height: 1.4;
}

.paper-card__title:hover {
  color: var(--el-color-primary);
}

.paper-card__score {
  flex-shrink: 0;
}

.paper-card__meta {
  font-size: var(--font-size-sm);
  color: var(--el-color-info);
  margin-bottom: var(--spacing-sm);
}

.paper-card__abstract {
  font-size: var(--font-size-base);
  color: var(--el-text-color-regular);
  line-height: 1.6;
  margin-bottom: var(--spacing-sm);
}

.paper-card__keywords {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-sm);
}

.paper-card__recommend {
  margin-bottom: var(--spacing-sm);
  display: flex;
  align-items: baseline;
  gap: var(--spacing-xs);
}

.paper-card__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-xs);
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--el-border-color-lighter);
}
</style>
