import { describe, it, expect } from 'vitest'
import { parseCitations, linkifyCitations, splitReportSegments } from '@/utils/citation'
import type { Citation } from '@/types/analysis'

describe('parseCitations', () => {
  it('parses single citation', () => {
    const text = 'Recent work [Zhang, 2024] improves performance.'
    const result = parseCitations(text)
    expect(result).toHaveLength(1)
    expect(result[0]).toMatchObject({
      authors: 'Zhang',
      year: '2024',
      paperId: undefined
    })
    expect(result[0].raw).toBe('[Zhang, 2024]')
  })

  it('parses multiple citations', () => {
    const text = 'See [Zhang, 2024] and [Li, 2023] for details.'
    const result = parseCitations(text)
    expect(result).toHaveLength(2)
    expect(result[0].authors).toBe('Zhang')
    expect(result[1].authors).toBe('Li')
  })

  it('matches citation with paperId from list', () => {
    const text = 'Reference [Zhang, 2024]'
    const citations: Citation[] = [
      { paperId: 'arxiv_2024_001', text: 'Zhang et al., 2024', location: 'p.1' }
    ]
    const result = parseCitations(text, citations)
    expect(result[0].paperId).toBe('arxiv_2024_001')
  })

  it('returns empty array for empty text', () => {
    expect(parseCitations('')).toEqual([])
  })

  it('handles multi-author citation', () => {
    const text = 'Study [Smith, A. Author, 2024] confirms'
    const result = parseCitations(text)
    expect(result).toHaveLength(1)
    expect(result[0].authors).toBe('Smith')
    expect(result[0].year).toBe('2024')
  })
})

describe('linkifyCitations', () => {
  it('replaces citation with markdown link when paperId matched', () => {
    const text = 'See [Zhang, 2024]'
    const citations: Citation[] = [
      { paperId: 'p1', text: 'Zhang et al., 2024', location: 'p.1' }
    ]
    expect(linkifyCitations(text, citations)).toBe('See [Zhang, 2024](paper:p1)')
  })

  it('keeps original when no matching paperId', () => {
    const text = 'See [Zhang, 2024]'
    expect(linkifyCitations(text, [])).toBe('See [Zhang, 2024]')
  })

  it('handles empty input', () => {
    expect(linkifyCitations('')).toBe('')
  })
})

describe('splitReportSegments', () => {
  it('splits text into text and citation segments', () => {
    const text = 'Intro [Zhang, 2024] middle [Li, 2023] end.'
    const citations: Citation[] = [
      { paperId: 'p1', text: 'Zhang et al., 2024', location: 'p.1' },
      { paperId: 'p2', text: 'Li et al., 2023', location: 'p.2' }
    ]
    const segments = splitReportSegments(text, citations)
    expect(segments).toHaveLength(5)
    expect(segments[0]).toEqual({ type: 'text', value: 'Intro ' })
    expect(segments[1]).toMatchObject({ type: 'citation', authors: 'Zhang', year: '2024', paperId: 'p1' })
    expect(segments[2]).toEqual({ type: 'text', value: ' middle ' })
    expect(segments[3]).toMatchObject({ type: 'citation', authors: 'Li', year: '2023', paperId: 'p2' })
    expect(segments[4]).toEqual({ type: 'text', value: ' end.' })
  })

  it('marks citation without paperId as citation type with no paperId', () => {
    const text = 'Test [Wang, 2025]'
    const segments = splitReportSegments(text, [])
    expect(segments).toHaveLength(2)
    expect(segments[1]).toMatchObject({ type: 'citation', paperId: undefined })
  })

  it('returns single text segment for text without citations', () => {
    const text = 'Just plain text without references.'
    const segments = splitReportSegments(text, [])
    expect(segments).toEqual([{ type: 'text', value: 'Just plain text without references.' }])
  })
})
