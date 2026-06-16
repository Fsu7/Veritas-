<script setup lang="ts">
/**
 * 论文筛选面板组件
 * - 年份范围选择（两个 el-date-picker type="year"）
 * - 会议多选（el-select multiple）
 * - 引用数下限（el-input-number）
 * - 重置按钮
 */
import { computed } from 'vue'
import type { FilterParams } from '@/types/paper'

const props = defineProps<{
  filters: FilterParams
  conferences?: string[]
}>()

const emit = defineEmits<{
  (e: 'update:filters', filters: FilterParams): void
  (e: 'reset'): void
}>()

const DEFAULT_CONFERENCES = [
  'ACL', 'EMNLP', 'NAACL', 'COLING',
  'NeurIPS', 'ICML', 'ICLR', 'AAAI', 'IJCAI'
]

const availableConferences = computed(() =>
  props.conferences?.length ? props.conferences : DEFAULT_CONFERENCES
)

const localYearFrom = computed({
  get: () => props.filters.yearFrom?.toString() ?? '',
  set: (val: string) => {
    const num = val ? Number(val) : undefined
    emitUpdate({ yearFrom: num })
  }
})

const localYearTo = computed({
  get: () => props.filters.yearTo?.toString() ?? '',
  set: (val: string) => {
    const num = val ? Number(val) : undefined
    emitUpdate({ yearTo: num })
  }
})

const localConferences = computed({
  get: () => props.filters.conferences ?? [],
  set: (val: string[]) => {
    emitUpdate({ conferences: val.length > 0 ? val : undefined })
  }
})

const localMinCitations = computed({
  get: () => props.filters.minCitations ?? 0,
  set: (val: number) => {
    emitUpdate({ minCitations: val > 0 ? val : undefined })
  }
})

function emitUpdate(patch: Partial<FilterParams>) {
  emit('update:filters', { ...props.filters, ...patch })
}

function handleReset() {
  emit('reset')
}
</script>

<template>
  <div class="filter-panel">
    <h4 class="filter-panel__title">筛选条件</h4>

    <!-- 年份范围 -->
    <div class="filter-panel__group">
      <label class="filter-panel__label">年份范围</label>
      <div class="filter-panel__year-row">
        <el-input
          :model-value="localYearFrom"
          placeholder="起始年"
          type="number"
          :min="1900"
          :max="2030"
          size="small"
          clearable
          @update:model-value="localYearFrom = $event"
        />
        <span class="filter-panel__separator">—</span>
        <el-input
          :model-value="localYearTo"
          placeholder="截止年"
          type="number"
          :min="1900"
          :max="2030"
          size="small"
          clearable
          @update:model-value="localYearTo = $event"
        />
      </div>
    </div>

    <!-- 会议多选 -->
    <div class="filter-panel__group">
      <label class="filter-panel__label">会议</label>
      <el-select
        :model-value="localConferences"
        multiple
        placeholder="选择会议"
        size="small"
        style="width: 100%"
        collapse-tags
        collapse-tags-tooltip
        @update:model-value="localConferences = $event"
      >
        <el-option
          v-for="conf in availableConferences"
          :key="conf"
          :label="conf"
          :value="conf"
        />
      </el-select>
    </div>

    <!-- 引用数 -->
    <div class="filter-panel__group">
      <label class="filter-panel__label">最少引用数</label>
      <el-input-number
        :model-value="localMinCitations"
        :min="0"
        size="small"
        style="width: 100%"
        @update:model-value="localMinCitations = $event"
      />
    </div>

    <!-- 操作 -->
    <div class="filter-panel__actions">
      <el-button size="small" @click="handleReset">
        重置筛选
      </el-button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.filter-panel {
  padding: var(--spacing-sm, 8px) 0;
}

.filter-panel__title {
  margin: 0 0 var(--spacing-md, 16px);
  font-size: var(--font-size-base, 14px);
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.filter-panel__group {
  margin-bottom: var(--spacing-md, 16px);
}

.filter-panel__label {
  display: block;
  font-size: var(--font-size-sm, 13px);
  color: var(--el-text-color-secondary);
  margin-bottom: var(--spacing-xs, 4px);
}

.filter-panel__year-row {
  display: flex;
  align-items: center;
  gap: 4px;
}

.filter-panel__separator {
  flex-shrink: 0;
  color: var(--el-text-color-placeholder);
  font-size: var(--font-size-sm, 13px);
}

.filter-panel__actions {
  padding-top: var(--spacing-sm, 8px);
  border-top: 1px solid var(--el-border-color-lighter);
}
</style>
