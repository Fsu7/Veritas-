<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/userStore'
import { useSessionStore } from '@/stores/sessionStore'
import UserProfileForm from '@/components/common/UserProfileForm.vue'
import type { SessionDetail } from '@/types/session'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const sessionStore = useSessionStore()

const loading = ref(false)
const sessions = ref<SessionDetail[]>([])

const isProfileSetup = computed(() => route.query.setupProfile === 'true')

async function handleProfileSaved() {
  await userStore.fetchProfile()
  ElMessage.success('画像保存成功')
  if (isProfileSetup.value) {
    router.push({ name: 'Home' })
  }
}

async function handleSessionClick(sessionId: string) {
  router.push(`/search?sessionId=${sessionId}`)
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([
      userStore.getUserInfo(),
      userStore.fetchProfile(),
      loadSessions()
    ])
  } catch {
    ElMessage.error('页面加载失败，请刷新重试')
  } finally {
    loading.value = false
  }
})

async function loadSessions() {
  try {
    const res = await sessionStore.fetchSessions({ page: 1, size: 10 })
    sessions.value = res.items
  } catch {
    ElMessage.error('历史记录加载失败')
  }
}
</script>

<template>
  <div v-loading="loading" class="user-center-view">
    <div class="user-center-view__content">
      <el-card class="user-center-view__card" shadow="hover">
        <template #header>
          <h2 class="user-center-view__card-title">用户信息</h2>
        </template>
        <el-descriptions
          v-if="userStore.userInfo"
          :column="1"
          border
        >
          <el-descriptions-item label="用户名">
            {{ userStore.userInfo.username }}
          </el-descriptions-item>
          <el-descriptions-item label="邮箱">
            {{ userStore.userInfo.email }}
          </el-descriptions-item>
          <el-descriptions-item label="注册时间">
            {{ formatDate(userStore.userInfo.createdAt) }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card class="user-center-view__card" shadow="hover">
        <template #header>
          <h2 class="user-center-view__card-title">用户画像</h2>
        </template>
        <el-alert
          v-if="isProfileSetup"
          title="欢迎使用科研文献智能助手"
          description="请先设置您的用户画像，以便我们为您提供个性化的文献分析和综述服务。"
          type="info"
          show-icon
          :closable="false"
          class="user-center-view__setup-hint"
        />
        <UserProfileForm
          :initial-data="userStore.profile ?? undefined"
          @saved="handleProfileSaved"
        />
      </el-card>

      <el-card class="user-center-view__card" shadow="hover">
        <template #header>
          <h2 class="user-center-view__card-title">历史记录</h2>
        </template>
        <el-timeline v-if="sessions.length > 0">
          <el-timeline-item
            v-for="session in sessions"
            :key="session.sessionId"
            :timestamp="formatDate(session.createdAt)"
            placement="top"
          >
            <div
              class="user-center-view__session-item"
              @click="handleSessionClick(session.sessionId)"
            >
              {{ session.topic }}
            </div>
          </el-timeline-item>
        </el-timeline>
        <el-empty
          v-else
          description="暂无分析记录"
        />
      </el-card>
    </div>
  </div>
</template>

<style scoped lang="scss">
.user-center-view {
  padding: var(--spacing-lg);

  &__content {
    max-width: var(--content-max-width);
    margin: 0 auto;
  }

  &__card {
    margin-bottom: var(--spacing-lg);

    &:last-child {
      margin-bottom: 0;
    }
  }

  &__card-title {
    font-size: var(--font-size-lg);
    font-weight: 600;
    margin: 0;
  }

  &__setup-hint {
    margin-bottom: var(--spacing-lg);
  }

  &__session-item {
    cursor: pointer;
    font-size: var(--font-size-base);
    color: var(--el-color-primary);
    transition: color var(--transition-fast);

    &:hover {
      color: var(--el-color-primary-dark-2);
    }
  }
}
</style>
