import type { Paper } from '@/types/paper'

/**
 * 格式化作者列表
 * @example ['Zhang', 'Li'] → 'Zhang, Li'
 */
export function formatAuthors(authors: string[]): string {
  return authors.join(', ')
}

/**
 * 格式化论文元数据（作者 · 年份 · 期刊 · 引用数）
 * 缺省字段自动跳过
 */
export function formatMeta(
  paper: Pick<Paper, 'authors' | 'year' | 'venue' | 'citationCount'>
): string {
  const parts: string[] = []
  if (paper.authors?.length) {
    parts.push(formatAuthors(paper.authors))
  }
  if (paper.year) {
    parts.push(String(paper.year))
  }
  if (paper.venue) {
    parts.push(paper.venue)
  }
  if (paper.citationCount != null) {
    parts.push(`引用 ${paper.citationCount}`)
  }
  return parts.join(' · ')
}

/**
 * 格式化日期（zh-CN）
 * @example '2026-06-05T10:00:00Z' → '2026/6/5 18:00:00'
 */
export function formatDate(value: string | number | Date | undefined | null): string {
  if (!value) return ''
  const d = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString('zh-CN', { hour12: false })
}

/**
 * 格式化耗时（毫秒 → 人类可读）
 * - null/undefined → '-'
 * - <1s → '123ms'
 * - <1m → '1.5s'
 * - ≥1m → '2m 30s'
 */
export function formatDuration(ms?: number | null): string {
  if (ms == null) return '-'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`
  const m = Math.floor(ms / 60_000)
  const s = Math.floor((ms % 60_000) / 1000)
  return `${m}m ${s}s`
}
