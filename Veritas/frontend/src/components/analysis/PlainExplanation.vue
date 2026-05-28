<script setup lang="ts">
defineProps<{
  content: string
}>()
</script>

<template>
  <el-card class="plain-explanation__card">
    <el-alert
      type="info"
      :closable="false"
      show-icon
      class="plain-explanation"
    >
      <template #title>
        <el-text tag="b" class="plain-explanation__title">💡 通俗理解：</el-text>
      </template>
      <el-text class="plain-explanation__content">{{ content }}</el-text>
    </el-alert>
  </el-card>
</template>

<style scoped lang="scss">
.plain-explanation__card {
  margin-top: var(--spacing-md, 16px);
}

.plain-explanation__title {
  font-size: var(--font-size-base, 14px);
  color: var(--el-color-info);
}

.plain-explanation__content {
  line-height: 1.8;
  color: var(--el-text-color-regular);
}
</style>
