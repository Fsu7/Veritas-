<script setup lang="ts">
/**
 * 通用空状态组件
 * - 可自定义图标、标题、描述、操作按钮
 * - 用于替换各页面的 el-empty
 */
import { computed } from 'vue'
import { Box, Document, FolderOpened, Search } from '@element-plus/icons-vue'

const props = withDefaults(defineProps<{
  title?: string
  description?: string
  /** 图标类型：box/document/folder/search */
  icon?: 'box' | 'document' | 'folder' | 'search'
  /** 操作按钮文案，若提供则显示按钮 */
  actionText?: string
}>(), {
  title: '暂无数据',
  icon: 'box'
})

const emit = defineEmits<{
  (e: 'action'): void
}>()

const iconComponent = computed(() => {
  switch (props.icon) {
    case 'document': return Document
    case 'folder': return FolderOpened
    case 'search': return Search
    default: return Box
  }
})

function handleAction() {
  emit('action')
}
</script>

<template>
  <div class="empty-state">
    <el-icon class="empty-state__icon" :size="64">
      <component :is="iconComponent" />
    </el-icon>
    <h3 class="empty-state__title">{{ title }}</h3>
    <p v-if="description" class="empty-state__description">{{ description }}</p>
    <el-button
      v-if="actionText"
      type="primary"
      size="small"
      class="empty-state__action"
      @click="handleAction"
    >
      {{ actionText }}
    </el-button>
  </div>
</template>

<style scoped lang="scss">
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl, 32px) var(--spacing-lg, 24px);
  text-align: center;

  &__icon {
    color: var(--el-text-color-placeholder, #a8abb2);
    margin-bottom: var(--spacing-md, 16px);
  }

  &__title {
    font-size: var(--font-size-lg, 18px);
    font-weight: 500;
    color: var(--el-text-color-primary, #303133);
    margin: 0 0 var(--spacing-xs, 4px);
  }

  &__description {
    font-size: var(--font-size-base, 14px);
    color: var(--el-text-color-secondary, #909399);
    margin: 0 0 var(--spacing-md, 16px);
    max-width: 400px;
    line-height: 1.6;
  }

  &__action {
    margin-top: var(--spacing-sm, 8px);
  }
}
</style>
