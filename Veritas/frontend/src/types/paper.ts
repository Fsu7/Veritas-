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
 * 兼容 FM3 字段命名，FM4 新增 conferences 多选
 */
export interface FilterParams {
  yearFrom?: number
  yearTo?: number
  /** 多选会议列表（FM4 新增） */
  conferences?: string[]
  minCitations?: number
  /** @deprecated 保留兼容，建议使用 conferences */
  venue?: string
}

/** 排序字段 */
export type SortField = 'relevance' | 'publishedDate' | 'citationCount'

/** 排序方向 */
export type SortOrder = 'asc' | 'desc'

/** 排序参数 */
export interface SortParams {
  field: SortField
  order: SortOrder
}

/** 默认排序：按相关度降序 */
export const DEFAULT_SORT: SortParams = { field: 'relevance', order: 'desc' }
