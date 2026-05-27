import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { paperApi } from '@/api/paper'
import type { Paper, FilterParams } from '@/types/paper'

const MAX_SELECTED_PAPERS = 5

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

  function togglePaperSelection(paper: Paper) {
    const idx = selectedPapers.value.findIndex(p => p.paperId === paper.paperId)
    if (idx >= 0) {
      selectedPapers.value.splice(idx, 1)
    } else if (selectedPapers.value.length < MAX_SELECTED_PAPERS) {
      selectedPapers.value.push(paper)
    }
  }

  function clearSelection() {
    selectedPapers.value = []
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
    selectedPaperIds, hasResults, totalPages,
    searchPapers, togglePaperSelection, clearSelection,
    toggleFavorite, fetchFavorites, updateFilters, resetSearch
  }
})
