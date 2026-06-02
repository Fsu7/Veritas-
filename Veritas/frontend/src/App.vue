<script setup lang="ts">
import AppHeader from '@/components/layout/AppHeader.vue'
</script>

<template>
  <div class="app-container">
    <AppHeader />
    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>

