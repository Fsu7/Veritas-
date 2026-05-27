<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/userStore'
import { usePaperStore } from '@/stores/paperStore'
import { getRecentSearches, saveRecentSearch, clearRecentSearches } from '@/utils/storage'

const router = useRouter()
const userStore = useUserStore()
const paperStore = usePaperStore()

const searchQuery = ref('')
const isSearching = ref(false)
const recentSearches = ref<string[]>(getRecentSearches())

async function handleSearch() {
  const query = searchQuery.value.trim()
  if (!query) return

  saveRecentSearch(query)
  recentSearches.value = getRecentSearches()

  if (!userStore.isLoggedIn) {
    ElMessage.warning('请先登录')
    router.push('/login')
    return
  }

  isSearching.value = true
  try {
    await paperStore.searchPapers(query)
    router.push({ name: 'Search', query: { q: query } })
  } catch {
    ElMessage.error('检索失败，请稍后重试')
  } finally {
    isSearching.value = false
  }
}

function handleRecentClick(query: string) {
  searchQuery.value = query
  handleSearch()
}

function handleClearRecent() {
  clearRecentSearches()
  recentSearches.value = []
}
</script>

<template>
  <div class="home-view">
    <div class="home-view__content">
      <div class="home-view__search-box">
        <h1 class="home-view__title">科研文献智能助手</h1>
        <p class="home-view__subtitle">领域知识个性化生成与多智能体协同决策系统</p>
        <div class="home-view__input-wrapper">
          <el-input
            v-model="searchQuery"
            size="large"
            clearable
            :disabled="isSearching"
            placeholder="输入研究主题，如Multi-Agent协同决策"
            @keyup.enter="handleSearch"
          >
            <template #append>
              <el-button
                type="primary"
                :loading="isSearching"
                @click="handleSearch"
              >
                检索
              </el-button>
            </template>
          </el-input>
        </div>
        <div v-if="recentSearches.length" class="home-view__recent">
          <span class="home-view__recent-label">最近搜索：</span>
          <el-tag
            v-for="tag in recentSearches"
            :key="tag"
            effect="plain"
            size="small"
            class="home-view__recent-tag"
            @click="handleRecentClick(tag)"
          >
            {{ tag }}
          </el-tag>
          <el-button text size="small" @click="handleClearRecent">清除</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.home-view {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.home-view__content {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl);
}

.home-view__search-box {
  width: 100%;
  max-width: 600px;
  text-align: center;
}

.home-view__title {
  font-size: 32px;
  font-weight: 600;
  margin-bottom: var(--spacing-sm);
  color: var(--el-text-color-primary);
  text-align: center;
}

.home-view__subtitle {
  font-size: var(--font-size-base);
  color: var(--el-color-info);
  margin-bottom: 48px;
}

.home-view__input-wrapper {
  margin-bottom: var(--spacing-lg);
}

.home-view__recent {
  margin-top: var(--spacing-lg);
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.home-view__recent-label {
  color: var(--el-color-info);
  font-size: var(--font-size-sm);
  margin-right: var(--spacing-sm);
}

.home-view__recent-tag {
  cursor: pointer;
}
</style>
