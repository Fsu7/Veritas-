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
      <el-button text @click="handleLogout">退出</el-button>
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
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;

  &__logo {
    font-size: 18px;
    font-weight: 600;
    color: var(--el-color-primary);
    cursor: pointer;
    white-space: nowrap;
    margin-right: 20px;
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
    margin-right: 8px;
    font-size: 14px;
    color: #606266;
  }
}
</style>
