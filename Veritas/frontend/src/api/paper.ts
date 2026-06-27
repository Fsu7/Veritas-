import http from './index'
import type { Paper, FilterParams, SortField, SortOrder } from '@/types/paper'
import type { PageResponse } from '@/types/common'

export const paperApi = {
  list: (params: { page: number; size: number }) =>
    http.get('/papers', { params }),

  getDetail: (paperId: string): Promise<Paper> =>
    http.get(`/papers/${paperId}`),

  search: (params: {
    q: string
    page?: number
    size?: number
    sort_by?: SortField
    sort_order?: SortOrder
  } & FilterParams, signal?: AbortSignal): Promise<PageResponse<Paper>> =>
    http.get('/papers/search', { params, signal }),

  addFavorite: (paperId: string) =>
    http.post(`/papers/${paperId}/favorite`),

  removeFavorite: (paperId: string) =>
    http.delete(`/papers/${paperId}/favorite`),

  /**
   * 获取当前用户收藏的论文列表（分页）
   * 对应后端 GET /users/me/favorites 或 /papers/favorites
   */
  getFavorites: (params?: { page?: number; pageSize?: number }): Promise<PageResponse<Paper>> =>
    http.get('/papers/favorites', { params })
}
