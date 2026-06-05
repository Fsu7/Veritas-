import type { Citation } from '@/types/analysis'

/**
 * 解析后的引用片段
 */
export interface ParsedCitation {
  /** 原始匹配文本，如 [Zhang, 2024] */
  raw: string
  /** 作者名（首位作者 last name） */
  authors: string
  /** 出版年份 */
  year: string
  /** 关联论文 ID（从 Citation 列表反查得到） */
  paperId?: string
}

/**
 * 综述文本片段，用于分段渲染（避免 v-html XSS 风险）
 */
export type ReportSegment =
  | { type: 'text'; value: string }
  | { type: 'citation'; value: string; paperId?: string; authors: string; year: string }

/**
 * 引用匹配正则
 * 支持格式：[Author, 2024] / [Author, A. Author, 2024]
 * 至少需要 1 个 lastname，0~N 个 "A. Firstname" 形式
 */
const CITATION_PATTERN = /\[([A-Z][a-zA-Z]+)(?:,\s*[A-Z]\.\s*[A-Z][a-zA-Z]+)*,\s*(\d{4})\]/g

/**
 * 从综述文本中解析所有 [Author, Year] 引用
 */
export function parseCitations(text: string, citations: Citation[] = []): ParsedCitation[] {
  if (!text) return []
  const results: ParsedCitation[] = []
  const regex = new RegExp(CITATION_PATTERN.source, 'g')
  let match: RegExpExecArray | null
  while ((match = regex.exec(text)) !== null) {
    const [, authors, year] = match
    const matched = citations.find(c =>
      c.text.includes(authors) && c.text.includes(year)
    )
    results.push({
      raw: match[0],
      authors,
      year,
      paperId: matched?.paperId
    })
  }
  return results
}

/**
 * 将 [Author, Year] 替换为可点击的 Markdown 链接
 * 输出格式：[Author, Year](paper:paperId)
 * 若无匹配的 paperId 则保留原文本
 */
export function linkifyCitations(text: string, citations: Citation[] = []): string {
  if (!text) return ''
  return text.replace(CITATION_PATTERN, (match, authors, year) => {
    const matched = citations.find(c =>
      c.text.includes(authors) && c.text.includes(year)
    )
    if (matched) {
      return `[${match.slice(1, -1)}](paper:${matched.paperId})`
    }
    return match
  })
}

/**
 * 将综述文本拆分为片段数组
 * 用于 v-for + ElLink 渲染，避免 v-html XSS 风险
 * 仅匹配带 paperId 的引用为可点击片段，其余为纯文本片段
 */
export function splitReportSegments(text: string, citations: Citation[] = []): ReportSegment[] {
  if (!text) return []
  const segments: ReportSegment[] = []
  const regex = new RegExp(CITATION_PATTERN.source, 'g')
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = regex.exec(text)) !== null) {
    // 引用前的纯文本
    if (match.index > lastIndex) {
      segments.push({
        type: 'text',
        value: text.slice(lastIndex, match.index)
      })
    }

    const [, authors, year] = match
    const matched = citations.find(c =>
      c.text.includes(authors) && c.text.includes(year)
    )

    segments.push({
      type: 'citation',
      value: match[0],
      paperId: matched?.paperId,
      authors,
      year
    })

    lastIndex = match.index + match[0].length
  }

  // 剩余尾部纯文本
  if (lastIndex < text.length) {
    segments.push({
      type: 'text',
      value: text.slice(lastIndex)
    })
  }

  return segments
}
