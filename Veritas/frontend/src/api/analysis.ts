import http from './index'
import type { AnalysisResult } from '@/types/analysis'
import type { UserProfile } from '@/types/user'

export const analysisApi = {
  analyzePaper: (data: { paperId: string }): Promise<AnalysisResult> =>
    http.post('/analysis/paper', data),

  comparePapers: (data: { paperIds: string[] }): Promise<AnalysisResult> =>
    http.post('/analysis/compare', data),

  /**
   * 生成个性化综述报告
   * profile 必填：后端根据用户画像生成不同风格综述
   */
  generateReport: (data: {
    topic: string
    paperIds: string[]
    profile: UserProfile
  }): Promise<AnalysisResult> =>
    http.post('/analysis/report', data),

  getResult: (analysisId: string): Promise<AnalysisResult> =>
    http.get(`/analysis/${analysisId}`),

  getStatus: (analysisId: string): Promise<AnalysisResult> =>
    http.get(`/analysis/${analysisId}/status`),

  getAgentStreamUrl: (analysisId: string): string => {
    // EventSource 不支持自定义请求头，通过 URL Query 传递 Token
    // 后端需同步支持 ?token=xxx 鉴权方式
    const token = localStorage.getItem('token') || ''
    return `/api/analysis/${analysisId}/agent-stream?token=${encodeURIComponent(token)}`
  },

  /** 导出综述报告为 PDF（返回 Blob） */
  exportPdf: (analysisId: string): Promise<Blob> =>
    http.get(`/analysis/${analysisId}/export/pdf`, { responseType: 'blob' }),

  /** 导出综述报告为 Word（返回 Blob） */
  exportWord: (analysisId: string): Promise<Blob> =>
    http.get(`/analysis/${analysisId}/export/word`, { responseType: 'blob' })
}
