import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { paperApi } from '@/api/paper'
import type { Paper, FilterParams } from '@/types/paper'

const MAX_SELECTED_PAPERS = 5
const MIN_SELECTED_PAPERS = 2

/**
 * 论文选择结果
 * 告知 UI 是否成功及原因，便于 ElMessage 提示
 */
export interface ToggleSelectionResult {
  success: boolean
  reason?: string
  current: number
  max: number
}

export const usePaperStore = defineStore('paper', () => {
  const searchResults = ref<Paper[]>([])
  const selectedPapers = ref<Paper[]>([])
  const favorites = ref<string[]>([])
  const filters = ref<FilterParams>({})
  const currentQuery = ref('')
  const totalResults = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(10)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const selectedPaperIds = computed(() =>
    selectedPapers.value.map(p => p.paperId)
  )

  const hasResults = computed(() => searchResults.value.length > 0)

  const totalPages = computed(() =>
    Math.ceil(totalResults.value / pageSize.value) || 1
  )

  /** 是否满足"开始对比"的下限要求 */
  const canCompare = computed(() =>
    selectedPapers.value.length >= MIN_SELECTED_PAPERS &&
    selectedPapers.value.length <= MAX_SELECTED_PAPERS
  )

  async function searchPapers(query: string, page: number = 1) {
    loading.value = true
    error.value = null
    currentQuery.value = query
    currentPage.value = page
    try {
      const res = await paperApi.search({
        q: query,
        page,
        size: pageSize.value,
        ...filters.value
      })
      searchResults.value = res.items
      totalResults.value = res.total
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : '搜索失败'
      error.value = message
    } finally {
      loading.value = false
    }
  }

  /**
   * 切换论文选择状态（加入或移除对比池）
   * @returns ToggleSelectionResult 包含成功状态、原因、当前数量
   */
  function togglePaperSelection(paper: Paper): ToggleSelectionResult {
    const idx = selectedPapers.value.findIndex(p => p.paperId === paper.paperId)
    if (idx >= 0) {
      selectedPapers.value.splice(idx, 1)
      return {
        success: true,
        current: selectedPapers.value.length,
        max: MAX_SELECTED_PAPERS
      }
    }
    if (selectedPapers.value.length >= MAX_SELECTED_PAPERS) {
      return {
        success: false,
        reason: `最多选择 ${MAX_SELECTED_PAPERS} 篇论文，请先取消部分选择`,
        current: selectedPapers.value.length,
        max: MAX_SELECTED_PAPERS
      }
    }
    selectedPapers.value.push(paper)
    return {
      success: true,
      current: selectedPapers.value.length,
      max: MAX_SELECTED_PAPERS
    }
  }

  function clearSelection() {
    selectedPapers.value = []
  }

  /**
   * 获取论文详情（FM2 Medium 遗留修复：统一通过 Store Action）
   */
  async function fetchDetail(paperId: string): Promise<Paper> {
    return await paperApi.getDetail(paperId)
  }

  async function toggleFavorite(paperId: string) {
    const wasFavorited = favorites.value.includes(paperId)
    if (wasFavorited) {
      favorites.value = favorites.value.filter(id => id !== paperId)
    } else {
      favorites.value.push(paperId)
    }
    try {
      if (wasFavorited) {
        await paperApi.removeFavorite(paperId)
      } else {
        await paperApi.addFavorite(paperId)
      }
    } catch {
      if (wasFavorited) {
        favorites.value.push(paperId)
      } else {
        favorites.value = favorites.value.filter(id => id !== paperId)
      }
      throw new Error('收藏操作失败')
    }
  }

  async function fetchFavorites() {
    // FM5 待实现：需后端提供 GET /users/{userId}/favorites 后接入
    favorites.value = []
  }

  function updateFilters(newFilters: FilterParams) {
    filters.value = { ...filters.value, ...newFilters }
    if (currentQuery.value) {
      searchPapers(currentQuery.value, 1)
    }
  }

  function resetSearch() {
    searchResults.value = []
    currentQuery.value = ''
    filters.value = {}
    totalResults.value = 0
    currentPage.value = 1
    error.value = null
  }

  return {
    searchResults, selectedPapers, favorites, filters,
    currentQuery, totalResults, currentPage, pageSize,
    loading, error,
    selectedPaperIds, hasResults, totalPages, canCompare,
    searchPapers, togglePaperSelection, clearSelection, fetchDetail,
    toggleFavorite, fetchFavorites, updateFilters, resetSearch
  }
})
