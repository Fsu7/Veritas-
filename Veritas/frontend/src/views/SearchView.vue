<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { usePaperStore } from '@/stores/paperStore'
import { usePagination } from '@/composables/usePagination'
import PaperCard from '@/components/paper/PaperCard.vue'
import SearchInput from '@/components/common/SearchInput.vue'
import FilterPanel from '@/components/common/FilterPanel.vue'
import SortDropdown from '@/components/common/SortDropdown.vue'
import type { FilterParams, SortParams } from '@/types/paper'

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

/** 论文筛选 */
function handleUpdateFilters(filters: FilterParams) {
  paperStore.updateFilters(filters)
}

/** 重置筛选 */
function handleResetFilters() {
  paperStore.updateFilters({})
}

/** 排序变更 */
function handleSortChange(sort: SortParams) {
  paperStore.sortBy = sort
  if (paperStore.currentQuery) {
    paperStore.searchPapers(paperStore.currentQuery, 1, sort)
  }
}

/** 搜索 */
async function handleSearch(query: string) {
  if (!query) return
  searchQuery.value = query
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

/** 清除搜索 */
function handleClearSearch() {
  searchQuery.value = ''
  paperStore.resetSearch()
  hasSearched.value = false
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
  if (searchQuery.value) {
    handleSearch(searchQuery.value)
  }
}

function initSearch() {
  const q = route.query.q as string
  if (q) {
    searchQuery.value = q
    handleSearch(q)
  }
}

onMounted(() => {
  initSearch()
})

watch(() => route.query.q, (newQ) => {
  if (newQ && typeof newQ === 'string' && newQ !== paperStore.currentQuery) {
    searchQuery.value = newQ
    handleSearch(newQ)
  }
})
</script>

<template>
  <div class="search-view">
    <!-- 搜索栏 -->
    <div class="search-view__search-bar">
      <SearchInput
        v-model="searchQuery"
        :loading="searchLoading"
        placeholder="输入研究主题或关键词"
        @search="handleSearch"
        @clear="handleClearSearch"
      />
    </div>

    <!-- 错误状态 -->
    <div v-if="hasError" class="search-view__error">
      <el-result icon="error" title="检索失败" :sub-title="paperStore.error || ''">
        <template #extra>
          <el-button type="primary" @click="handleRetry">重试</el-button>
        </template>
      </el-result>
    </div>

    <template v-else>
      <el-container class="search-view__layout">
        <!-- 左侧筛选面板 -->
        <el-aside width="240px" class="search-view__aside">
          <el-card shadow="hover">
            <FilterPanel
              :filters="paperStore.filters"
              @update:filters="handleUpdateFilters"
              @reset="handleResetFilters"
            />
          </el-card>
        </el-aside>

        <!-- 右侧主内容 -->
        <el-main class="search-view__main">
          <!-- 空状态 -->
          <div
            v-if="hasSearched && !searchLoading && !paperStore.searchResults.length"
            class="search-view__empty"
          >
            <el-empty description="未找到相关论文，试试调整搜索词？" />
          </div>

          <template v-else>
            <!-- 结果统计 + 排序 -->
            <div v-if="paperStore.totalResults > 0" class="search-view__toolbar">
              <el-text size="small" type="info">
                找到 {{ paperStore.totalResults }} 篇相关论文
              </el-text>
              <SortDropdown
                v-model="paperStore.sortBy"
                @update:model-value="handleSortChange"
              />
            </div>

            <!-- 论文列表 -->
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

            <!-- 分页 -->
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
        </el-main>
      </el-container>
    </template>
  </div>
</template>

<style scoped lang="scss">
.search-view {
  max-width: var(--content-max-width, 1200px);
  margin: 0 auto;
  padding: var(--spacing-lg, 24px);
}

.search-view__search-bar {
  margin-bottom: var(--spacing-lg, 24px);
}

.search-view__layout {
  gap: var(--spacing-md, 16px);
}

.search-view__aside {
  flex-shrink: 0;
}

.search-view__main {
  padding: 0;
  min-height: 400px;
}

.search-view__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-md, 16px);
}

.search-view__results {
  min-height: 200px;
}

.search-view__empty {
  padding: 48px 0;
}

.search-view__error {
  padding: var(--spacing-lg, 24px) 0;
}

.search-view__pagination {
  display: flex;
  justify-content: center;
  padding: var(--spacing-lg, 24px) 0;
}
</style>
