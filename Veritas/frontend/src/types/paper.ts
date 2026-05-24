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

export interface FilterParams {
  yearFrom?: number
  yearTo?: number
  venue?: string
  minCitations?: number
  sort?: 'relevance' | 'year' | 'citations'
}
