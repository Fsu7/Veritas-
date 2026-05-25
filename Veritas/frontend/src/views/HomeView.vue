<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/userStore'
import { getRecentSearches, saveRecentSearch, clearRecentSearches } from '@/utils/storage'

const router = useRouter()
const userStore = useUserStore()

const searchQuery = ref('')
const recentSearches = ref<string[]>(getRecentSearches())

function handleSearch() {
  const query = searchQuery.value.trim()
  if (!query) return

  saveRecentSearch(query)
  recentSearches.value = getRecentSearches()

  if (!userStore.isLoggedIn) {
    ElMessage.warning('请先登录')
    router.push('/login')
    return
  }

  router.push({ name: 'Search', query: { q: query } })
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
      <div class="home-view__search">
        <h1 class="home-view__title">🔍 科研文献智能助手</h1>
        <div class="home-view__search-input">
          <el-input
            v-model="searchQuery"
            placeholder="输入研究主题，如Multi-Agent协同决策"
            size="large"
            clearable
            @keyup.enter="handleSearch"
          />
        </div>
        <el-button type="primary" size="large" @click="handleSearch">检索</el-button>
        <div class="home-view__recent" v-if="recentSearches.length">
          <span class="home-view__recent-label">最近搜索：</span>
          <el-tag
            v-for="tag in recentSearches"
            :key="tag"
            effect="plain"
            size="small"
            style="cursor: pointer"
            @click="handleRecentClick(tag)"
          >
            {{ tag }}
          </el-tag>
          <el-button class="home-view__clear-btn" text size="small" @click="handleClearRecent">清除</el-button>
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

.home-view__search {
  width: 100%;
  max-width: 640px;
}

.home-view__title {
  font-size: var(--font-size-xxl);
  font-weight: 600;
  margin-bottom: var(--spacing-lg);
  color: #303133;
  text-align: center;
}

.home-view__search-input {
  margin-bottom: var(--spacing-md);
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

.home-view__clear-btn {
  margin-left: auto;
}
</style>
