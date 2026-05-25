/**
 * 论文实体，对应后端papers表
 * JSON字段映射: paperId ↔ paper_id, citationCount ↔ citation_count,
 * pdfUrl ↔ pdf_url, recommendReason ↔ recommend_reason
 */
export interface Paper {
  paperId: string
  title: string
  authors: string[]
  abstract: string
  year: number
  venue?: string
  keywords?: string[]
  citationCount?: number
  pdfUrl?: string
  score?: number
  recommendReason?: string
}

/**
 * 论文筛选参数
 */
export interface FilterParams {
  yearFrom?: number
  yearTo?: number
  venue?: string
  minCitations?: number
  sort?: 'relevance' | 'year' | 'citations'
}
