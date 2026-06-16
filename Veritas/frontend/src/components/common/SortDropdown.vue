<script setup lang="ts">
/**
 * 排序下拉组件
 * - 三种排序方式：相关度 / 发表时间 / 引用数
 * - v-model 绑定 SortParams
 */
import { computed } from 'vue'
import { ElSelect, ElOption } from 'element-plus'
import type { SortParams, SortField } from '@/types/paper'

const props = defineProps<{
  modelValue: SortParams
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', sort: SortParams): void
}>()

const options: { label: string; field: SortField }[] = [
  { label: '相关度', field: 'relevance' },
  { label: '发表时间', field: 'publishedDate' },
  { label: '引用数', field: 'citationCount' }
]

const selectedField = computed({
  get: () => props.modelValue.field,
  set: (field: SortField) => {
    emit('update:modelValue', { ...props.modelValue, field })
  }
})
</script>

<template>
  <div class="sort-dropdown">
    <span class="sort-dropdown__label">排序：</span>
    <el-select
      v-model="selectedField"
      size="small"
      style="width: 140px"
    >
      <el-option
        v-for="opt in options"
        :key="opt.field"
        :label="opt.label"
        :value="opt.field"
      />
    </el-select>
  </div>
</template>

<style scoped lang="scss">
.sort-dropdown {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs, 4px);
}

.sort-dropdown__label {
  font-size: var(--font-size-sm, 13px);
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}
</style>
