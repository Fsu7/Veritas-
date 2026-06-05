<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { usePaperStore } from '@/stores/paperStore'
import { usePagination } from '@/composables/usePagination'
import PaperCard from '@/components/paper/PaperCard.vue'

const route = useRoute()
const router = useRouter()
const paperStore = usePaperStore()

const searchQuery = ref('')
const hasSearched = ref(false)
const searchLoading = ref(false)

const { currentPage, handleCurrentChange, resetPage } = usePagination(
  computed(() => paperStore.totalResults)
)

const hasError = computed(() => !!paperStore.error)

const showPagination = computed(() =>
  paperStore.totalResults > paperStore.pageSize
)

async function handleSearch() {
  const query = searchQuery.value.trim()
  if (!query) return

  searchLoading.value = true
  hasSearched.value = true
  try {
    await paperStore.searchPapers(query, 1)
    resetPage()
  } catch {
    ElMessage.error('检索失败，请稍后重试')
  } finally {
    searchLoading.value = false
  }
}

async function handlePageChange(page: number) {
  handleCurrentChange(page, async (p) => {
    searchLoading.value = true
    try {
      await paperStore.searchPapers(paperStore.currentQuery, p)
    } catch {
      ElMessage.error('加载失败，请稍后重试')
    } finally {
      searchLoading.value = false
    }
  })
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function handleFavorite(paperId: string) {
  const wasFavorited = paperStore.favorites.includes(paperId)
  try {
    await paperStore.toggleFavorite(paperId)
    ElMessage.success(wasFavorited ? '已取消收藏' : '收藏成功')
  } catch {
    ElMessage.error('操作失败')
  }
}

function handleAnalyze(paperId: string) {
  router.push({ name: 'PaperDetail', params: { paperId } })
}

function handleSelect(paperId: string) {
  router.push({ name: 'PaperDetail', params: { paperId } })
}

function handleToggleSelect(paper: import('@/types/paper').Paper) {
  const result = paperStore.togglePaperSelection(paper)
  if (!result.success) {
    ElMessage.warning(result.reason ?? '操作失败')
  }
}

function handleRetry() {
  handleSearch()
}

function initSearch() {
  const q = route.query.q as string
  if (q) {
    searchQuery.value = q
    handleSearch()
  }
}

onMounted(() => {
  initSearch()
})

watch(() => route.query.q, (newQ) => {
  if (newQ && typeof newQ === 'string' && newQ !== paperStore.currentQuery) {
    searchQuery.value = newQ
    handleSearch()
  }
})
</script>

<template>
  <div class="search-view">
    <div class="search-view__header">
      <el-input
        v-model="searchQuery"
        size="large"
        clearable
        :disabled="searchLoading"
        placeholder="输入研究主题或关键词"
        @keyup.enter="handleSearch"
      >
        <template #append>
          <el-button type="primary" :loading="searchLoading" @click="handleSearch">
            检索
          </el-button>
        </template>
      </el-input>
    </div>

    <div v-if="hasError" class="search-view__error">
      <el-result icon="error" title="检索失败" :sub-title="paperStore.error || ''">
        <template #extra>
          <el-button type="primary" @click="handleRetry">重试</el-button>
        </template>
      </el-result>
    </div>

    <div v-else-if="hasSearched && !searchLoading && !paperStore.searchResults.length" class="search-view__empty">
      <el-empty description="未找到相关论文，试试调整搜索词？" />
    </div>

    <template v-else>
      <div v-if="paperStore.totalResults > 0" class="search-view__stats">
        <el-text size="small" type="info">
          找到 {{ paperStore.totalResults }} 篇相关论文
        </el-text>
      </div>

      <div v-loading="searchLoading" class="search-view__results">
        <PaperCard
          v-for="paper in paperStore.searchResults"
          :key="paper.paperId"
          :paper="paper"
          :selectable="true"
          :selected="paperStore.selectedPaperIds.includes(paper.paperId)"
          :is-favorited="paperStore.favorites.includes(paper.paperId)"
          @select="handleSelect"
          @analyze="handleAnalyze"
          @favorite="handleFavorite"
          @toggle-select="handleToggleSelect"
        />
      </div>

      <div v-if="showPagination" class="search-view__pagination">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="paperStore.pageSize"
          :total="paperStore.totalResults"
          layout="prev, pager, next, total"
          @current-change="handlePageChange"
        />
      </div>
    </template>
  </div>
</template>

<style scoped lang="scss">
.search-view {
  max-width: var(--content-max-width);
  margin: 0 auto;
  padding: var(--spacing-lg);
}

.search-view__header {
  margin-bottom: var(--spacing-lg);
}

.search-view__stats {
  margin-bottom: var(--spacing-md);
}

.search-view__results {
  min-height: 200px;
}

.search-view__empty {
  padding: 48px 0;
}

.search-view__error {
  padding: var(--spacing-lg) 0;
}

.search-view__pagination {
  display: flex;
  justify-content: center;
  padding: var(--spacing-lg) 0;
}
</style>
