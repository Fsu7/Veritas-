import { defineStore } from 'pinia'
import { ref } from 'vue'
import { sessionApi } from '@/api/session'
import { analysisApi } from '@/api/analysis'
import type { AnalysisResult } from '@/types/analysis'
import type { SessionResponse } from '@/types/session'

export const useSessionStore = defineStore('session', () => {
  const currentSessionId = ref<string | null>(null)
  const currentAnalysisId = ref<string | null>(null)
  const analysisResults = ref<Map<string, AnalysisResult>>(new Map())

  async function createSession(topic: string): Promise<SessionResponse> {
    const res = await sessionApi.create({ topic })
    currentSessionId.value = res.sessionId
    return res
  }

  async function fetchAnalysisResult(analysisId: string): Promise<AnalysisResult> {
    const res = await analysisApi.getResult(analysisId)
    analysisResults.value.set(analysisId, res)
    return res
  }

  return {
    currentSessionId, currentAnalysisId, analysisResults,
    createSession, fetchAnalysisResult
  }
})
