import http from './index'
import type { SessionResponse, SessionDetail } from '@/types/session'
import type { PageResponse } from '@/types/common'

export const sessionApi = {
  create: (data: { topic: string }): Promise<SessionResponse> =>
    http.post('/sessions', data),

  list: (params: { page: number; size: number }): Promise<PageResponse<SessionDetail>> =>
    http.get('/sessions', { params }),

  getDetail: (sessionId: string): Promise<SessionDetail> =>
    http.get(`/sessions/${sessionId}`),

  delete: (sessionId: string) =>
    http.delete(`/sessions/${sessionId}`)
}
