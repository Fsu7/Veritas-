<script setup lang="ts">
/**
 * 通用错误状态组件
 * - 可自定义标题、描述、错误对象、重试按钮
 * - 用于替换各页面的 el-result icon="error"
 */
import { computed } from 'vue'
import { WarningFilled } from '@element-plus/icons-vue'

const props = withDefaults(defineProps<{
  title?: string
  description?: string
  /** 错误对象，若提供则显示错误消息作为描述的补充 */
  error?: Error | string | null
  /** 重试按钮文案，默认"重试" */
  actionText?: string
}>(), {
  title: '加载失败',
  actionText: '重试'
})

const emit = defineEmits<{
  (e: 'retry'): void
}>()

const fullDescription = computed(() => {
  if (props.description) return props.description
  if (props.error instanceof Error) return props.error.message
  if (typeof props.error === 'string') return props.error
  return '请稍后重试'
})

function handleRetry() {
  emit('retry')
}
</script>

<template>
  <div class="error-state">
    <el-icon class="error-state__icon" :size="64" color="var(--el-color-danger, #f56c6c)">
      <WarningFilled />
    </el-icon>
    <h3 class="error-state__title">{{ title }}</h3>
    <p class="error-state__description">{{ fullDescription }}</p>
    <el-button
      type="primary"
      size="small"
      class="error-state__action"
      @click="handleRetry"
    >
      {{ actionText }}
    </el-button>
  </div>
</template>

<style scoped lang="scss">
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl, 32px) var(--spacing-lg, 24px);
  text-align: center;

  &__icon {
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
    word-break: break-word;
  }

  &__action {
    margin-top: var(--spacing-sm, 8px);
  }
}
</style>
