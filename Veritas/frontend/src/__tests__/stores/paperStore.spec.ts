import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { usePaperStore } from '@/stores/paperStore'
import type { Paper } from '@/types/paper'

vi.mock('@/api/paper', () => ({
  paperApi: {
    search: vi.fn(),
    addFavorite: vi.fn(),
    removeFavorite: vi.fn()
  }
}))

import { paperApi } from '@/api/paper'

const mockPaper: Paper = {
  paperId: 'p1',
  title: 'Test Paper',
  authors: ['Author A', 'Author B'],
  abstract: 'Abstract text',
  year: 2024,
  venue: 'ACL',
  keywords: ['NLP', 'LLM'],
  citationCount: 50,
  score: 0.95,
  recommendReason: 'Highly relevant'
}

describe('paperStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('searchPapers', () => {
    it('sets loading=true during search and loading=false after success', async () => {
      const store = usePaperStore()
      vi.mocked(paperApi.search).mockResolvedValue({
        items: [mockPaper],
        total: 1,
        page: 1,
        size: 10,
        totalPages: 1
      })

      const promise = store.searchPapers('test')
      expect(store.loading).toBe(true)
      await promise
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('updates searchResults and totalResults on success', async () => {
      const store = usePaperStore()
      vi.mocked(paperApi.search).mockResolvedValue({
        items: [mockPaper],
        total: 1,
        page: 1,
        size: 10,
        totalPages: 1
      })

      await store.searchPapers('test')
      expect(store.searchResults).toHaveLength(1)
      expect(store.searchResults[0].paperId).toBe('p1')
      expect(store.totalResults).toBe(1)
      expect(store.currentQuery).toBe('test')
      expect(store.currentPage).toBe(1)
    })

    it('sets error on failure', async () => {
      const store = usePaperStore()
      vi.mocked(paperApi.search).mockRejectedValue(new Error('Network error'))

      await store.searchPapers('test')
      expect(store.loading).toBe(false)
      expect(store.error).toBe('Network error')
      expect(store.searchResults).toHaveLength(0)
    })
  })

  describe('togglePaperSelection', () => {
    it('adds paper to selectedPapers', () => {
      const store = usePaperStore()
      store.togglePaperSelection(mockPaper)
      expect(store.selectedPapers).toHaveLength(1)
      expect(store.selectedPaperIds).toContain('p1')
    })

    it('removes paper if already selected', () => {
      const store = usePaperStore()
      store.togglePaperSelection(mockPaper)
      store.togglePaperSelection(mockPaper)
      expect(store.selectedPapers).toHaveLength(0)
    })

    it('limits selection to 5 papers', () => {
      const store = usePaperStore()
      for (let i = 0; i < 6; i++) {
        store.togglePaperSelection({ ...mockPaper, paperId: `p${i}` })
      }
      expect(store.selectedPapers).toHaveLength(5)
    })
  })

  describe('clearSelection', () => {
    it('clears selectedPapers', () => {
      const store = usePaperStore()
      store.togglePaperSelection(mockPaper)
      store.clearSelection()
      expect(store.selectedPapers).toHaveLength(0)
    })
  })

  describe('toggleFavorite', () => {
    it('adds to favorites on success', async () => {
      const store = usePaperStore()
      vi.mocked(paperApi.addFavorite).mockResolvedValue({} as never)
      await store.toggleFavorite('p1')
      expect(store.favorites).toContain('p1')
    })

    it('removes from favorites on success', async () => {
      const store = usePaperStore()
      vi.mocked(paperApi.addFavorite).mockResolvedValue({} as never)
      await store.toggleFavorite('p1')
      vi.mocked(paperApi.removeFavorite).mockResolvedValue({} as never)
      await store.toggleFavorite('p1')
      expect(store.favorites).not.toContain('p1')
    })

    it('rolls back on API failure', async () => {
      const store = usePaperStore()
      vi.mocked(paperApi.addFavorite).mockRejectedValue(new Error('fail'))
      await expect(store.toggleFavorite('p1')).rejects.toThrow('收藏操作失败')
      expect(store.favorites).not.toContain('p1')
    })
  })

  describe('updateFilters', () => {
    it('merges filters and triggers search', async () => {
      const store = usePaperStore()
      vi.mocked(paperApi.search).mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        size: 10,
        totalPages: 0
      })
      store.currentQuery = 'test'
      store.updateFilters({ yearFrom: 2020 })
      expect(store.filters.yearFrom).toBe(2020)
    })
  })

  describe('resetSearch', () => {
    it('resets search state but keeps selectedPapers and favorites', () => {
      const store = usePaperStore()
      store.searchResults = [mockPaper]
      store.currentQuery = 'test'
      store.totalResults = 1
      store.currentPage = 2
      store.error = 'some error'
      store.togglePaperSelection(mockPaper)
      store.favorites = ['p1']

      store.resetSearch()

      expect(store.searchResults).toHaveLength(0)
      expect(store.currentQuery).toBe('')
      expect(store.totalResults).toBe(0)
      expect(store.currentPage).toBe(1)
      expect(store.error).toBeNull()
      expect(store.selectedPapers).toHaveLength(1)
      expect(store.favorites).toContain('p1')
    })
  })

  describe('hasResults', () => {
    it('returns true when searchResults has items', () => {
      const store = usePaperStore()
      store.searchResults = [mockPaper]
      expect(store.hasResults).toBe(true)
    })

    it('returns false when searchResults is empty', () => {
      const store = usePaperStore()
      expect(store.hasResults).toBe(false)
    })
  })

  describe('totalPages', () => {
    it('calculates total pages correctly', () => {
      const store = usePaperStore()
      store.totalResults = 25
      store.pageSize = 10
      expect(store.totalPages).toBe(3)
    })

    it('returns 1 when totalResults is 0', () => {
      const store = usePaperStore()
      store.totalResults = 0
      expect(store.totalPages).toBe(1)
    })
  })
})
