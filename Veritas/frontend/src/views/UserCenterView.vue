<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/userStore'
import { useSessionStore } from '@/stores/sessionStore'
import { usePaperStore } from '@/stores/paperStore'
import UserProfileForm from '@/components/common/UserProfileForm.vue'
import ProfileDashboard from '@/components/common/ProfileDashboard.vue'
import type { SessionDetail } from '@/types/session'
import type { UserProfile } from '@/types/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const sessionStore = useSessionStore()
const paperStore = usePaperStore()

const loading = ref(false)
const sessions = ref<SessionDetail[]>([])
const favoritesCount = ref(0)

// 历史记录搜索与分页状态
const historySearchKeyword = ref('')
const historyCurrentPage = ref(1)
const historyPageSize = 5

const isProfileSetup = computed(() => route.query.setupProfile === 'true')

// 画像标签展示数据
const educationLabels: Record<UserProfile['educationLevel'], string> = {
  undergraduate: '本科生',
  master: '硕士研究生',
  phd: '博士研究生',
  faculty: '教师/研究者'
}
const knowledgeLabels: Record<UserProfile['knowledgeLevel'], string> = {
  beginner: '初级',
  intermediate: '中级',
  advanced: '高级',
  expert: '专家'
}
const styleLabels: Record<UserProfile['preferredStyle'], string> = {
  simple: '通俗',
  balanced: '均衡',
  technical: '专业'
}

const profileTags = computed(() => {
  const p = userStore.profile
  if (!p) return []
  return [
    { key: 'education', label: '学历', value: educationLabels[p.educationLevel] },
    { key: 'field', label: '方向', value: p.researchField },
    { key: 'knowledge', label: '水平', value: knowledgeLabels[p.knowledgeLevel] },
    { key: 'style', label: '风格', value: styleLabels[p.preferredStyle] }
  ]
})

// 历史记录：倒序 + 关键词过滤 + 分页
const filteredSessions = computed(() => {
  const keyword = historySearchKeyword.value.trim().toLowerCase()
  const list = keyword
    ? sessions.value.filter(s => s.topic.toLowerCase().includes(keyword))
    : sessions.value.slice()
  // 倒序：按 createdAt 降序
  list.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
  return list
})

const pagedSessions = computed(() => {
  const start = (historyCurrentPage.value - 1) * historyPageSize
  return filteredSessions.value.slice(start, start + historyPageSize)
})

function handleHistorySearch() {
  // 搜索时重置回第一页
  historyCurrentPage.value = 1
}

function handleHistoryPageChange(page: number) {
  historyCurrentPage.value = page
}

// 监听画像版本号变化，触发画像标签刷新（saveProfile 已自增 profileVersion）
watch(() => userStore.profileVersion, () => {
  // profile 已在 store 内更新，此处仅触发响应式依赖
})

async function handleProfileSaved(_profile: UserProfile) {
  // store.saveProfile 已更新 profile 并自增 profileVersion
  // 此处再次拉取以确保后端数据一致
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
      loadSessions(),
      loadFavoritesCount()
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

async function loadFavoritesCount() {
  try {
    // 仅取第一页第一条以获取 total，避免加载过多数据
    await paperStore.fetchFavorites(1, 1)
    favoritesCount.value = paperStore.favoritesTotal
  } catch {
    // 收藏数量加载失败不阻塞页面
    favoritesCount.value = 0
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
          <el-descriptions-item label="收藏论文">
            <el-link type="primary" :underline="false" @click="router.push('/favorites')">
              {{ favoritesCount }} 篇
            </el-link>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card class="user-center-view__card" shadow="hover">
        <template #header>
          <h2 class="user-center-view__card-title">我的画像</h2>
        </template>
        <ProfileDashboard
          v-if="userStore.profile"
          :profile="userStore.profile"
          :sessions-count="sessions.length"
          :favorites-count="favoritesCount"
        />
        <el-alert
          v-else
          title="尚未设置画像"
          description="请在下方设置您的用户画像。"
          type="info"
          show-icon
          :closable="false"
          class="user-center-view__setup-hint"
        />
      </el-card>

      <el-card class="user-center-view__card" shadow="hover">
        <template #header>
          <h2 class="user-center-view__card-title">编辑画像</h2>
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
          <div class="user-center-view__history-header">
            <h2 class="user-center-view__card-title">历史记录</h2>
            <el-input
              v-model="historySearchKeyword"
              class="user-center-view__history-search"
              placeholder="搜索历史记录"
              clearable
              :prefix-icon="'Search'"
              @input="handleHistorySearch"
              @clear="handleHistorySearch"
            />
          </div>
        </template>
        <el-timeline v-if="pagedSessions.length > 0">
          <el-timeline-item
            v-for="session in pagedSessions"
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
          :description="historySearchKeyword ? '未找到匹配的历史记录' : '暂无分析记录'"
        />
        <div
          v-if="filteredSessions.length > historyPageSize"
          class="user-center-view__history-pagination"
        >
          <el-pagination
            v-model:current-page="historyCurrentPage"
            :page-size="historyPageSize"
            :total="filteredSessions.length"
            layout="prev, pager, next"
            background
            @current-change="handleHistoryPageChange"
          />
        </div>
      </el-card>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/mixins' as *;

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

  &__profile-tags {
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-sm);
  }

  &__profile-tag {
    display: inline-flex;
    align-items: center;
    padding: var(--spacing-xs) var(--spacing-sm);
  }

  &__profile-tag-label {
    color: var(--el-text-color-secondary);
    margin-right: 4px;
  }

  &__profile-tag-value {
    color: var(--el-color-primary);
    font-weight: 500;
  }

  &__history-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--spacing-md);
    flex-wrap: wrap;
  }

  &__history-search {
    width: var(--sidebar-width);
    max-width: 100%;
  }

  &__history-pagination {
    display: flex;
    justify-content: center;
    margin-top: var(--spacing-lg);
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

/* Task 50: 移动端响应式 */
@include respond-to(md) {
  .user-center-view {
    padding: var(--spacing-md);
  }

  .user-center-view__history-search {
    width: 100%;
  }

  .user-center-view__history-header {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-sm);
  }
}
</style>
