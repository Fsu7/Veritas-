<script setup lang="ts">
/**
 * 全局 Loading 遮罩组件
 * - el-overlay + 旋转图标 + 文字
 * - 默认 text="加载中..."
 * - 默认 z-index=2000
 */
import { computed } from 'vue'
import { Loading } from '@element-plus/icons-vue'

const props = withDefaults(defineProps<{
  visible: boolean
  text?: string
  zIndex?: number
}>(), {
  text: '加载中...',
  zIndex: 2000
})

const zIndexStyle = computed(() => ({
  zIndex: props.zIndex
}))
</script>

<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="loading-overlay"
      :style="zIndexStyle"
    >
      <div class="loading-overlay__content">
        <el-icon class="loading-overlay__icon" :size="36">
          <Loading />
        </el-icon>
        <p class="loading-overlay__text">{{ text }}</p>
      </div>
    </div>
  </Teleport>
</template>

<style scoped lang="scss">
.loading-overlay {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(255, 255, 255, 0.75);
}

.loading-overlay__content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-md, 16px);
  padding: var(--spacing-xl, 32px);
  background-color: var(--el-bg-color);
  border-radius: var(--radius-md, 8px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}

.loading-overlay__icon {
  animation: loading-spin 1s linear infinite;
  color: var(--el-color-primary);
}

@keyframes loading-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.loading-overlay__text {
  margin: 0;
  font-size: var(--font-size-base, 14px);
  color: var(--el-text-color-secondary);
}
</style>
