/**
 * 后端统一响应格式
 */
export interface ApiResponse<T> {
  code: number
  message: string
  data: T
  timestamp: number
}

/**
 * 分页响应格式
 */
export interface PageResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
  totalPages: number
}
