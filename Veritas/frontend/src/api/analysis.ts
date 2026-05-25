import http from './index'
import type { AnalysisResult } from '@/types/analysis'

export const analysisApi = {
  analyzePaper: (data: { paperId: string }) =>
    http.post('/analysis/paper', data),

  comparePapers: (data: { paperIds: string[] }) =>
    http.post('/analysis/compare', data),

  generateReport: (data: { topic: string; paperIds: string[] }) =>
    http.post('/analysis/report', data),

  getResult: (analysisId: string): Promise<AnalysisResult> =>
    http.get(`/analysis/${analysisId}`),

  getStatus: (analysisId: string) =>
    http.get(`/analysis/${analysisId}/status`),

  getAgentStreamUrl: (analysisId: string): string =>
    `/api/analysis/${analysisId}/agent-stream`
}
