import { describe, it, expect } from 'vitest'
import { formatAuthors, formatMeta, formatDate } from '@/utils/format'
import type { Paper } from '@/types/paper'

describe('formatAuthors', () => {
  it('joins authors with comma', () => {
    expect(formatAuthors(['Zhang', 'Li', 'Wang'])).toBe('Zhang, Li, Wang')
  })

  it('returns empty string for empty array', () => {
    expect(formatAuthors([])).toBe('')
  })
})

describe('formatMeta', () => {
  it('formats all fields', () => {
    const paper = {
      authors: ['Zhang', 'Li'],
      year: 2024,
      venue: 'ACL',
      citationCount: 100
}
    expect(formatMeta(paper)).toBe('Zhang, Li · 2024 · ACL · 引用 100')
  })

  it('skips missing fields', () => {
    const paper = { authors: ['Zhang'], year: 2024, venue: '', citationCount: undefined }
    expect(formatMeta(paper as Paper)).toBe('Zhang · 2024')
  })

  it('returns empty string for empty paper', () => {
    expect(formatMeta({} as Paper)).toBe('')
  })
})

describe('formatDate', () => {
  it('formats ISO string to zh-CN locale', () => {
    const result = formatDate('2026-06-05T10:00:00Z')
    // 不同时区结果不同，仅检查格式含日期
    expect(result).toMatch(/\d{4}\/\d{1,2}\/\d{1,2}/)
  })

  it('returns empty string for null', () => {
    expect(formatDate(null)).toBe('')
  })

  it('returns empty string for invalid date', () => {
    expect(formatDate('invalid-date')).toBe('')
  })

  it('accepts Date object', () => {
    const d = new Date('2026-01-01T00:00:00Z')
    const result = formatDate(d)
    expect(result).toMatch(/\d{4}\/\d{1,2}\/\d{1,2}/)
  })
})
