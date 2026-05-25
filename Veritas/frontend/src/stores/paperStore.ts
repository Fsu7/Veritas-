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

  const selectedPaperIds = computed(() =>
    selectedPapers.value.map(p => p.paperId)
  )

  const filteredResults = computed(() => {
    let results = searchResults.value
    const f = filters.value
    if (f.yearFrom) {
      results = results.filter(p => p.year >= f.yearFrom!)
    }
    if (f.yearTo) {
      results = results.filter(p => p.year <= f.yearTo!)
    }
    if (f.venue) {
      results = results.filter(p =>
        p.venue?.toLowerCase().includes(f.venue!.toLowerCase())
      )
    }
    if (f.minCitations) {
      results = results.filter(p => (p.citationCount ?? 0) >= f.minCitations!)
    }
    if (f.sort === 'year') {
      results = [...results].sort((a, b) => b.year - a.year)
    } else if (f.sort === 'citations') {
      results = [...results].sort((a, b) => (b.citationCount ?? 0) - (a.citationCount ?? 0))
    }
    return results
  })

  async function searchPapers(query: string, page: number = 1) {
    currentQuery.value = query
    currentPage.value = page
    const res = await paperApi.search({
      q: query,
      page,
      size: pageSize.value,
      ...filters.value
    })
    searchResults.value = res.items
    totalResults.value = res.total
  }

  function togglePaperSelection(paper: Paper) {
    const idx = selectedPapers.value.findIndex(p => p.paperId === paper.paperId)
    if (idx >= 0) {
      selectedPapers.value.splice(idx, 1)
    } else if (selectedPapers.value.length < MAX_SELECTED_PAPERS) {
      selectedPapers.value.push(paper)
    }
  }

  async function toggleFavorite(paperId: string) {
    if (favorites.value.includes(paperId)) {
      await paperApi.removeFavorite(paperId)
      favorites.value = favorites.value.filter(id => id !== paperId)
    } else {
      await paperApi.addFavorite(paperId)
      favorites.value.push(paperId)
    }
  }

  return {
    searchResults, selectedPapers, favorites, filters,
    currentQuery, totalResults, currentPage, pageSize,
    selectedPaperIds, filteredResults,
    searchPapers, togglePaperSelection, toggleFavorite
  }
})
