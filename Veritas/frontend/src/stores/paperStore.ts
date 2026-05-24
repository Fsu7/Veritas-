import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Paper, FilterParams } from '@/types/paper'

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

  const filteredResults = computed(() => searchResults.value)

  async function searchPapers(_query: string, _page: number = 1) {
    // TODO: 调用API搜索论文
  }

  function togglePaperSelection(paper: Paper) {
    const idx = selectedPapers.value.findIndex(p => p.paperId === paper.paperId)
    if (idx >= 0) {
      selectedPapers.value.splice(idx, 1)
    } else if (selectedPapers.value.length < 5) {
      selectedPapers.value.push(paper)
    }
  }

  async function toggleFavorite(_paperId: string) {
    // TODO: 调用API收藏/取消收藏
  }

  return {
    searchResults, selectedPapers, favorites, filters,
    currentQuery, totalResults, currentPage, pageSize,
    selectedPaperIds, filteredResults,
    searchPapers, togglePaperSelection, toggleFavorite
  }
})
