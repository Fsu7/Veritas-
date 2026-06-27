import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { paperApi } from '@/api/paper'
import type { Paper, FilterParams, SortParams } from '@/types/paper'
import { DEFAULT_SORT } from '@/types/paper'

const MAX_SELECTED_PAPERS = 5
const MIN_SELECTED_PAPERS = 2

/** 取消上一次搜索请求，防止并发搜索竞态 */
let searchAbortController: AbortController | null = null

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
  // 收藏列表（带详情），用于 FavoritesView 展示
  const favoritesList = ref<Paper[]>([])
  const favoritesTotal = ref(0)
  const favoritesLoading = ref(false)
  const favoritesError = ref<string | null>(null)
  const filters = ref<FilterParams>({})
  const sortBy = ref<SortParams>({ ...DEFAULT_SORT })
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

  async function searchPapers(query: string, page: number = 1, sort?: SortParams) {
    searchAbortController?.abort()
    const controller = new AbortController()
    searchAbortController = controller
    loading.value = true
    error.value = null
    currentQuery.value = query
    currentPage.value = page
    const effectiveSort = sort ?? sortBy.value
    try {
      const res = await paperApi.search({
        q: query,
        page,
        size: pageSize.value,
        ...filters.value,
        sort_by: effectiveSort.field,
        sort_order: effectiveSort.order
      }, controller.signal)
      searchResults.value = res.items
      totalResults.value = res.total
    } catch (e: unknown) {
      if (e instanceof Error && e.name === 'CanceledError') return
      const message = e instanceof Error ? e.message : '搜索失败'
      error.value = message
    } finally {
      if (!controller.signal.aborted) {
        loading.value = false
      }
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

  async function toggleFavorite(paperId: string, paper?: Paper) {
    const wasFavorited = favorites.value.includes(paperId)
    if (wasFavorited) {
      favorites.value = favorites.value.filter(id => id !== paperId)
      // 同步移除收藏列表中的对应项
      favoritesList.value = favoritesList.value.filter(p => p.paperId !== paperId)
      favoritesTotal.value = Math.max(0, favoritesTotal.value - 1)
    } else {
      favorites.value.push(paperId)
      // 同步加入收藏列表（若已加载过列表且有 paper 详情）
      if (paper && (favoritesList.value.length > 0 || favoritesTotal.value > 0)) {
        favoritesList.value.unshift(paper)
        favoritesTotal.value += 1
      }
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
        // 回滚 favoritesList
        if (paper) {
          favoritesList.value.unshift(paper)
          favoritesTotal.value += 1
        }
      } else {
        favorites.value = favorites.value.filter(id => id !== paperId)
        favoritesList.value = favoritesList.value.filter(p => p.paperId !== paperId)
        favoritesTotal.value = Math.max(0, favoritesTotal.value - 1)
      }
      throw new Error('收藏操作失败')
    }
  }

  /**
   * 拉取收藏列表（分页）
   * @param page 页码（从 1 开始）
   * @param pageSize 每页条数
   */
  async function fetchFavorites(page: number = 1, pageSize: number = 10) {
    favoritesLoading.value = true
    favoritesError.value = null
    try {
      const res = await paperApi.getFavorites({ page, pageSize })
      favoritesList.value = res.items
      favoritesTotal.value = res.total
      // 同步 favorites id 数组（用于 PaperCard 收藏状态判断）
      favorites.value = res.items.map(p => p.paperId)
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : '收藏列表加载失败'
      favoritesError.value = message
      favoritesList.value = []
      favoritesTotal.value = 0
    } finally {
      favoritesLoading.value = false
    }
  }

  async function updateFilters(newFilters: FilterParams) {
    filters.value = { ...filters.value, ...newFilters }
    if (currentQuery.value) {
      await searchPapers(currentQuery.value, 1)
    }
  }

  // P0-9: 封装 sortBy 修改为 Action，禁止外部直接修改 Store State
  function setSortBy(sort: SortParams) {
    sortBy.value = sort
    if (currentQuery.value) {
      searchPapers(currentQuery.value, 1, sort)
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
    searchResults, selectedPapers, favorites,
    favoritesList, favoritesTotal, favoritesLoading, favoritesError,
    filters,
    sortBy,
    currentQuery, totalResults, currentPage, pageSize,
    loading, error,
    selectedPaperIds, hasResults, totalPages, canCompare,
    searchPapers, togglePaperSelection, clearSelection, fetchDetail,
    toggleFavorite, fetchFavorites, updateFilters, setSortBy, resetSearch
  }
})
