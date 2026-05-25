import { describe, it, expect, beforeEach } from 'vitest'
import {
  getRecentSearches,
  saveRecentSearch,
  clearRecentSearches,
} from '@/utils/storage'

describe('storage utils', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  describe('getRecentSearches', () => {
    it('returns empty array when no data', () => {
      expect(getRecentSearches()).toEqual([])
    })

    it('returns parsed array from localStorage', () => {
      localStorage.setItem('recent_searches', JSON.stringify(['a', 'b']))
      expect(getRecentSearches()).toEqual(['a', 'b'])
    })

    it('returns empty array on corrupt data', () => {
      localStorage.setItem('recent_searches', 'not-json')
      expect(getRecentSearches()).toEqual([])
    })
  })

  describe('saveRecentSearch', () => {
    it('prepends new query to list', () => {
      saveRecentSearch('hello')
      expect(getRecentSearches()).toEqual(['hello'])
    })

    it('moves existing query to front (dedup)', () => {
      saveRecentSearch('a')
      saveRecentSearch('b')
      saveRecentSearch('a')
      expect(getRecentSearches()).toEqual(['a', 'b'])
    })

    it('limits to 10 entries', () => {
      for (let i = 0; i < 15; i++) {
        saveRecentSearch(`query-${i}`)
      }
      const result = getRecentSearches()
      expect(result.length).toBe(10)
      expect(result[0]).toBe('query-14')
      expect(result[9]).toBe('query-5')
    })
  })

  describe('clearRecentSearches', () => {
    it('removes all search history', () => {
      saveRecentSearch('test')
      clearRecentSearches()
      expect(getRecentSearches()).toEqual([])
    })
  })
})
