<script setup lang="ts">
import AppHeader from '@/components/layout/AppHeader.vue'
import AppFooter from '@/components/layout/AppFooter.vue'
</script>

<template>
  <div class="app-container">
    <AppHeader />
    <main class="app-main">
      <RouterView />
    </main>
    <AppFooter />
  </div>
</template>

