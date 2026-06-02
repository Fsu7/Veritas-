<script setup lang="ts">
</script>

<template>
  <footer class="app-footer">
    <div class="app-footer__content">
      <p class="app-footer__info">XH-202630 科研文献智能助手</p>
      <p class="app-footer__info">v0.1</p>
      <p class="app-footer__ai-label ai-generated-label">AI生成内容仅供参考</p>
    </div>
  </footer>
</template>

<style scoped lang="scss">
.app-footer {
  flex-shrink: 0;
  background-color: #f5f7fa;
  border-top: 1px solid #e4e7ed;
  padding: var(--spacing-md) 0;

  &__content {
    text-align: center;
  }

  &__info {
    font-size: var(--font-size-sm);
    color: var(--el-color-info);
    line-height: 1.8;
  }

  &__ai-label {
    margin-top: var(--spacing-xs);
  }
}
</style>
