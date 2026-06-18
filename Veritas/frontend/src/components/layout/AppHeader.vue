<script setup lang="ts">
import { ref, computed } from 'vue'
import { useUserStore } from '@/stores/userStore'
import { useRouter } from 'vue-router'
import { Menu } from '@element-plus/icons-vue'

const userStore = useUserStore()
const router = useRouter()

const logoutLoading = ref(false)
const drawerVisible = ref(false)

const menuItems = computed(() => {
  if (!userStore.isLoggedIn) return []
  return [
    { label: '首页', route: '/' },
    { label: '我的收藏', route: '/favorites' },
    { label: '用户中心', route: '/user-center' }
  ]
})

async function handleLogout() {
  logoutLoading.value = true
  try {
    await userStore.logout()
    drawerVisible.value = false
    router.push('/login')
  } finally {
    logoutLoading.value = false
  }
}

function handleMenuSelect(route: string) {
  drawerVisible.value = false
  router.push(route)
}
</script>

<template>
  <el-header class="app-header">
    <div class="app-header__logo" @click="router.push('/')">
      科研文献智能助手
    </div>

    <!-- 桌面端导航 -->
    <div class="app-header__desktop">
      <el-menu mode="horizontal" router :ellipsis="false" class="app-header__menu">
        <el-menu-item v-for="item in menuItems" :key="item.route" :index="item.route">
          {{ item.label }}
        </el-menu-item>
      </el-menu>
      <div class="app-header__user" v-if="userStore.isLoggedIn">
        <span class="app-header__username">{{ userStore.username }}</span>
        <el-button
          text
          class="app-header__logout"
          :loading="logoutLoading"
          @click="handleLogout"
        >
          退出
        </el-button>
      </div>
      <div class="app-header__auth" v-else>
        <el-button text @click="router.push('/login')">登录</el-button>
        <el-button text @click="router.push('/register')">注册</el-button>
      </div>
    </div>

    <!-- 移动端汉堡按钮 -->
    <el-button class="app-header__hamburger" text @click="drawerVisible = true">
      <el-icon><Menu /></el-icon>
    </el-button>

    <!-- 移动端抽屉导航 -->
    <el-drawer v-model="drawerVisible" direction="ltr" size="240px" title="导航菜单">
      <el-menu router @select="handleMenuSelect">
        <el-menu-item v-for="item in menuItems" :key="item.route" :index="item.route">
          {{ item.label }}
        </el-menu-item>
      </el-menu>
      <div class="app-header__drawer-footer" v-if="userStore.isLoggedIn">
        <span class="app-header__username">{{ userStore.username }}</span>
        <el-button text :loading="logoutLoading" @click="handleLogout">退出</el-button>
      </div>
      <div class="app-header__drawer-footer" v-else>
        <el-button text @click="handleMenuSelect('/login')">登录</el-button>
        <el-button text @click="handleMenuSelect('/register')">注册</el-button>
      </div>
    </el-drawer>
  </el-header>
</template>

<style scoped lang="scss">
@use '@/styles/mixins' as *;

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

  &__desktop {
    display: flex;
    align-items: center;
    flex: 1;
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

  &__hamburger {
    display: none;
    margin-left: auto;
    font-size: var(--font-size-xl);
  }

  &__drawer-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--spacing-md);
    border-top: 1px solid var(--el-border-color-lighter);
  }
}

@include respond-to(md) {
  .app-header__desktop {
    display: none;
  }
  .app-header__hamburger {
    display: inline-flex;
  }
}
</style>
