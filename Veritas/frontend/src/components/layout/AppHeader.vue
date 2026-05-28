<script setup lang="ts">
import { computed } from 'vue'
import { useUserStore } from '@/stores/userStore'
import { useRouter } from 'vue-router'

const userStore = useUserStore()
const router = useRouter()

const menuItems = computed(() => {
  if (!userStore.isLoggedIn) return []
  return [
    { label: '首页', route: '/' },
    { label: '用户中心', route: '/user-center' }
  ]
})

function handleLogout() {
  userStore.logout()
  router.push('/login')
}
</script>

<template>
  <el-header class="app-header">
    <div class="app-header__logo" @click="router.push('/')">
      科研文献智能助手
    </div>
    <el-menu mode="horizontal" router :ellipsis="false" class="app-header__menu">
      <el-menu-item v-for="item in menuItems" :key="item.route" :index="item.route">
        {{ item.label }}
      </el-menu-item>
    </el-menu>
    <div class="app-header__user" v-if="userStore.isLoggedIn">
      <span class="app-header__username">{{ userStore.username }}</span>
      <el-button text class="app-header__logout" @click="handleLogout">退出</el-button>
    </div>
    <div class="app-header__auth" v-else>
      <el-button text @click="router.push('/login')">登录</el-button>
      <el-button text @click="router.push('/register')">注册</el-button>
    </div>
  </el-header>
</template>

<style scoped lang="scss">
.app-header {
  display: flex;
  align-items: center;
  height: var(--header-height);
  background-color: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color-lighter);
  padding: 0 var(--spacing-lg);

  &__logo {
    font-size: var(--font-size-lg);
    font-weight: 600;
    color: var(--el-color-primary);
    cursor: pointer;
    white-space: nowrap;
    margin-right: var(--spacing-lg);
  }

  &__menu {
    flex: 1;
    border-bottom: none;
  }

  &__user,
  &__auth {
    display: flex;
    align-items: center;
    white-space: nowrap;
  }

  &__username {
    margin-right: var(--spacing-sm);
    font-size: var(--font-size-base);
    color: var(--el-text-color-secondary);
  }
}
</style>
