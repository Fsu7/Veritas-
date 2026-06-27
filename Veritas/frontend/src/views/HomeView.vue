<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/userStore'
import { getRecentSearches, saveRecentSearch, clearRecentSearches } from '@/utils/storage'
import AppFooter from '@/components/layout/AppFooter.vue'
import DotMatrixClock from '@/components/common/DotMatrixClock.vue'

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
      <div class="home-view__search-box">
        <h1 class="home-view__title">科研文献智能助手</h1>
        <p class="home-view__subtitle">领域知识个性化生成与多智能体协同决策系统</p>
        <div class="home-view__input-wrapper">
          <el-input
            v-model="searchQuery"
            size="large"
            clearable
            placeholder="输入研究主题，如Multi-Agent协同决策"
            @keyup.enter="handleSearch"
          >
            <template #append>
              <el-button
                type="primary"
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
      <DotMatrixClock class="home-view__clock" />
    </div>
    <AppFooter class="home-view__footer" />
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/mixins' as *;

.home-view {
  position: fixed;
  top: var(--header-height);
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background-color: var(--el-bg-color-page);
  z-index: 1;
}

.home-view__content {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--spacing-md);
  overflow-y: auto;
}

.home-view__search-box {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  max-width: 720px;
  text-align: center;
}

.home-view__input-wrapper {
  width: 100%;
  margin-bottom: var(--spacing-lg);

  :deep(.el-input__wrapper) {
    padding: 4px 16px;
    border-radius: var(--radius-md);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  }

  :deep(.el-input__inner) {
    height: 56px;
    font-size: var(--font-size-lg);
  }

  :deep(.el-input-group__append) {
    background-color: var(--el-color-primary);
    border-radius: 0 var(--radius-md) var(--radius-md) 0;
  }

  :deep(.el-input-group__append .el-button) {
    height: 56px;
    padding: 0 32px;
    font-size: var(--font-size-base);
    font-weight: 500;
    color: #fff;
    border: none;
  }
}

.home-view__title {
  font-size: var(--font-size-display);
  font-weight: 700;
  line-height: 1.2;
  margin: 0 0 var(--spacing-md);
  color: var(--el-text-color-primary);
  text-align: center;
  letter-spacing: -0.5px;

  @include respond-to(md) {
    font-size: var(--font-size-xxl);
  }
}

.home-view__subtitle {
  font-size: var(--font-size-lg);
  color: var(--el-color-info);
  margin: 0 0 var(--spacing-xl);
  text-align: center;
  font-weight: 400;
}

.home-view__recent {
  margin-top: var(--spacing-md);
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--spacing-sm);
  max-width: 720px;
}

.home-view__recent-label {
  color: var(--el-color-info);
  font-size: var(--font-size-sm);
  margin-right: var(--spacing-xs);
}

.home-view__recent-tag {
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    transform: translateY(-1px);
  }
}

.home-view__clock {
  flex-shrink: 0;
  margin-bottom: var(--spacing-lg);
  max-width: 620px;
}

.home-view__footer {
  flex-shrink: 0;
}
</style>
