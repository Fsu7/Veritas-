<script setup lang="ts">
/**
 * 搜索输入框组件
 * - 300ms 防抖
 * - 回车立即搜索
 * - 清除按钮
 * - loading 时 disabled + loading 图标
 * - 可选历史标签（从 localStorage 读取）
 */
import { ref, computed, watch, onUnmounted } from 'vue'
import { ElInput } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { getRecentSearches, saveRecentSearch } from '@/utils/storage'

const props = withDefaults(defineProps<{
  modelValue: string
  placeholder?: string
  loading?: boolean
}>(), {
  placeholder: '搜索论文关键词...',
  loading: false
})

const emit = defineEmits<{
  (e: 'update:modelValue', val: string): void
  (e: 'search', query: string): void
  (e: 'clear'): void
}>()

const localValue = ref(props.modelValue)
let debounceTimer: ReturnType<typeof setTimeout> | null = null

const recentSearches = computed(() => getRecentSearches())

watch(() => props.modelValue, (val) => {
  localValue.value = val
})

watch(localValue, (val) => {
  emit('update:modelValue', val)
  // 300ms 防抖搜索
  clearDebounce()
  debounceTimer = setTimeout(() => {
    if (val.trim()) {
      emit('search', val.trim())
    }
  }, 300)
})

function handleEnter() {
  clearDebounce()
  const query = localValue.value.trim()
  if (query) {
    saveRecentSearch(query)
    emit('search', query)
  }
}

function clearDebounce() {
  if (debounceTimer) {
    clearTimeout(debounceTimer)
    debounceTimer = null
  }
}

function handleClear() {
  clearDebounce()
  emit('clear')
}

function handleTagClick(query: string) {
  localValue.value = query
  saveRecentSearch(query)
  clearDebounce()
  emit('search', query)
}

onUnmounted(() => {
  clearDebounce()
})
</script>

<template>
  <div class="search-input">
    <el-input
      v-model="localValue"
      :placeholder="placeholder"
      :loading="loading"
      :disabled="loading"
      size="large"
      clearable
      @keyup.enter="handleEnter"
      @clear="handleClear"
    >
      <template #prefix>
        <el-icon><Search /></el-icon>
      </template>
    </el-input>

    <!-- 历史搜索标签 -->
    <div v-if="recentSearches.length > 0 && !localValue" class="search-input__history">
      <span class="search-input__history-label">最近搜索：</span>
      <el-tag
        v-for="(query, idx) in recentSearches.slice(0, 5)"
        :key="idx"
        size="small"
        class="search-input__history-tag"
        @click="handleTagClick(query)"
      >
        {{ query }}
      </el-tag>
    </div>
  </div>
</template>

<style scoped lang="scss">
.search-input {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm, 8px);
}

.search-input__history {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--spacing-xs, 4px);
}

.search-input__history-label {
  font-size: var(--font-size-xs, 12px);
  color: var(--el-text-color-placeholder);
  white-space: nowrap;
}

.search-input__history-tag {
  cursor: pointer;
}
</style>
