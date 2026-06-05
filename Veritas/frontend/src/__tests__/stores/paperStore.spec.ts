import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { usePaperStore } from '@/stores/paperStore'
import type { Paper } from '@/types/paper'

const mockPapers: Paper[] = [
  { paperId: 'p1', title: 'Paper 1', authors: ['A'], abstract: '', year: 2024, venue: 'ACL', keywords: [], citationCount: 0 },
  { paperId: 'p2', title: 'Paper 2', authors: ['B'], abstract: '', year: 2024, venue: 'ACL', keywords: [], citationCount: 0 },
  { paperId: 'p3', title: 'Paper 3', authors: ['C'], abstract: '', year: 2024, venue: 'ACL', keywords: [], citationCount: 0 },
  { paperId: 'p4', title: 'Paper 4', authors: ['D'], abstract: '', year: 2024, venue: 'ACL', keywords: [], citationCount: 0 },
  { paperId: 'p5', title: 'Paper 5', authors: ['E'], abstract: '', year: 2024, venue: 'ACL', keywords: [], citationCount: 0 },
  { paperId: 'p6', title: 'Paper 6', authors: ['F'], abstract: '', year: 2024, venue: 'ACL', keywords: [], citationCount: 0 }
]

describe('usePaperStore.togglePaperSelection', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('adds paper on first toggle', () => {
    const store = usePaperStore()
    const result = store.togglePaperSelection(mockPapers[0])
    expect(result.success).toBe(true)
    expect(result.current).toBe(1)
    expect(result.max).toBe(5)
    expect(store.selectedPaperIds).toEqual(['p1'])
  })

  it('removes paper on second toggle (already selected)', () => {
    const store = usePaperStore()
    store.togglePaperSelection(mockPapers[0])
    const result = store.togglePaperSelection(mockPapers[0])
    expect(result.success).toBe(true)
    expect(result.current).toBe(0)
    expect(store.selectedPaperIds).toEqual([])
  })

  it('rejects 6th paper with reason when reaching MAX', () => {
    const store = usePaperStore()
    for (let i = 0; i < 5; i++) {
      store.togglePaperSelection(mockPapers[i])
    }
    const result = store.togglePaperSelection(mockPapers[5])
    expect(result.success).toBe(false)
    expect(result.reason).toContain('5')
    expect(result.current).toBe(5)
    expect(store.selectedPaperIds).toHaveLength(5)
  })

  it('canCompare returns true when 2-5 papers selected', () => {
    const store = usePaperStore()
    store.togglePaperSelection(mockPapers[0])
    expect(store.canCompare).toBe(false)
    store.togglePaperSelection(mockPapers[1])
    expect(store.canCompare).toBe(true)
    for (let i = 2; i < 5; i++) {
      store.togglePaperSelection(mockPapers[i])
    }
    expect(store.canCompare).toBe(true)
  })

  it('clearSelection empties the selection', () => {
    const store = usePaperStore()
    store.togglePaperSelection(mockPapers[0])
    store.togglePaperSelection(mockPapers[1])
    store.clearSelection()
    expect(store.selectedPaperIds).toEqual([])
    expect(store.canCompare).toBe(false)
  })
})
