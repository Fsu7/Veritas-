<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const searchQuery = ref('')
const recentSearches = ref<string[]>([])

function handleSearch() {
  const query = searchQuery.value.trim()
  if (!query) return

  if (!recentSearches.value.includes(query)) {
    recentSearches.value.unshift(query)
    if (recentSearches.value.length > 10) {
      recentSearches.value.pop()
    }
  }

  router.push({ path: '/search', query: { q: query } })
}

function handleTagClick(tag: string) {
  searchQuery.value = tag
  handleSearch()
}
</script>

<template>
  <div class="home-view">
    <div class="home-view__hero">
      <h1 class="home-view__title">科研文献智能助手</h1>
      <p class="home-view__subtitle">领域知识个性化生成与多智能体协同决策系统</p>

      <div class="home-view__search">
        <el-input
          v-model="searchQuery"
          placeholder='输入研究主题，如"Multi-Agent协同决策"'
          size="large"
          @keyup.enter="handleSearch"
        >
          <template #append>
            <el-button @click="handleSearch">检索</el-button>
          </template>
        </el-input>
      </div>

      <div class="home-view__recent" v-if="recentSearches.length > 0">
        <span class="home-view__recent-label">最近搜索：</span>
        <el-tag
          v-for="tag in recentSearches"
          :key="tag"
          class="home-view__tag"
          effect="plain"
          @click="handleTagClick(tag)"
        >
          {{ tag }}
        </el-tag>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.home-view {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - var(--header-height) - 48px);

  &__hero {
    text-align: center;
    max-width: 640px;
    width: 100%;
  }

  &__title {
    font-size: 32px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 8px;
  }

  &__subtitle {
    font-size: 16px;
    color: #909399;
    margin-bottom: 32px;
  }

  &__search {
    margin-bottom: 16px;
  }

  &__recent {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
  }

  &__recent-label {
    font-size: 14px;
    color: #909399;
  }

  &__tag {
    cursor: pointer;
  }
}
</style>
