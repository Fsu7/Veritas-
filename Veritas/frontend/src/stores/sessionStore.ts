import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { sessionApi } from '@/api/session'
import { analysisApi } from '@/api/analysis'
import { useAgentStore } from '@/stores/agentStore'
import type { AnalysisResult } from '@/types/analysis'
import type { SessionResponse, SessionDetail } from '@/types/session'
import type { PageResponse } from '@/types/common'
import type { UserProfile } from '@/types/user'

type AnalysisStatus = 'idle' | 'creating_session' | 'starting_analysis' | 'polling' | 'connecting_sse' | 'completed' | 'failed'

const MAX_POLL_ATTEMPTS = 60
const POLL_INTERVAL = 3000

export const useSessionStore = defineStore('session', () => {
  const agentStore = useAgentStore()

  const currentSessionId = ref<string | null>(null)
  const currentAnalysisId = ref<string | null>(null)
  const analysisResults = ref<Map<string, AnalysisResult>>(new Map())

  const analysisStatus = ref<AnalysisStatus>('idle')
  const analysisError = ref<string | null>(null)
  const pollTimer = ref<ReturnType<typeof setTimeout> | null>(null)

  const isAnalyzing = computed(() =>
    ['creating_session', 'starting_analysis', 'polling', 'connecting_sse'].includes(analysisStatus.value)
  )
  const isAnalysisCompleted = computed(() => analysisStatus.value === 'completed')
  const isAnalysisFailed = computed(() => analysisStatus.value === 'failed')

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

  async function fetchSessions(params: { page: number; size: number }): Promise<PageResponse<SessionDetail>> {
    return await sessionApi.list(params)
  }

  function cleanup() {
    if (pollTimer.value) {
      clearTimeout(pollTimer.value)
      pollTimer.value = null
    }
    agentStore.resetStates()
    analysisStatus.value = 'idle'
    analysisError.value = null
    currentSessionId.value = null
    currentAnalysisId.value = null
  }

  async function startAnalysis(topic: string, paperId: string): Promise<AnalysisResult> {
    cleanup()
    analysisError.value = null

    try {
      analysisStatus.value = 'creating_session'
      await createSession(topic)

      analysisStatus.value = 'starting_analysis'
      const result = await analysisApi.analyzePaper({ paperId })
      currentAnalysisId.value = result.analysisId

      analysisStatus.value = 'polling'
      const finalResult = await pollAnalysisStatus(result.analysisId)

      return finalResult
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : '分析失败'
      analysisStatus.value = 'failed'
      analysisError.value = message
      throw e
    }
  }

  function pollAnalysisStatus(analysisId: string, attempt: number = 0): Promise<AnalysisResult> {
    return new Promise((resolve, reject) => {
      if (attempt >= MAX_POLL_ATTEMPTS) {
        analysisStatus.value = 'failed'
        analysisError.value = '分析超时'
        reject(new Error('分析超时'))
        return
      }

      pollTimer.value = setTimeout(async () => {
        try {
          const result = await analysisApi.getStatus(analysisId)
          if (result.status === 'completed') {
            analysisResults.value.set(analysisId, result)
            analysisStatus.value = 'completed'
            resolve(result)
          } else if (result.status === 'failed') {
            analysisStatus.value = 'failed'
            analysisError.value = '分析失败'
            reject(new Error('分析失败'))
          } else {
            pollAnalysisStatus(analysisId, attempt + 1).then(resolve).catch(reject)
          }
        } catch (e: unknown) {
          const message = e instanceof Error ? e.message : '轮询失败'
          analysisStatus.value = 'failed'
          analysisError.value = message
          reject(new Error(message))
        }
      }, POLL_INTERVAL)
    })
  }

  // ============================================================
  // P0-8: View 层 API 调用迁移到 Store Action
  // ============================================================

  async function comparePapers(paperIds: string[]): Promise<AnalysisResult> {
    analysisError.value = null
    try {
      const result = await analysisApi.comparePapers({ paperIds })
      return result
    } catch (e: unknown) {
      analysisError.value = e instanceof Error ? e.message : '对比失败'
      throw e
    }
  }

  async function generateReport(params: { topic: string; paperIds: string[]; profile: UserProfile }): Promise<AnalysisResult> {
    analysisError.value = null
    try {
      const result = await analysisApi.generateReport(params)
      return result
    } catch (e: unknown) {
      analysisError.value = e instanceof Error ? e.message : '生成报告失败'
      throw e
    }
  }

  async function saveReportContent(analysisId: string, content: string): Promise<void> {
    try {
      await analysisApi.saveReportContent(analysisId, content)
    } catch (e: unknown) {
      analysisError.value = e instanceof Error ? e.message : '保存失败'
      throw e
    }
  }

  return {
    currentSessionId, currentAnalysisId, analysisResults,
    analysisStatus, analysisError, pollTimer,
    isAnalyzing, isAnalysisCompleted, isAnalysisFailed,
    createSession, fetchAnalysisResult, fetchSessions,
    startAnalysis, pollAnalysisStatus, cleanup,
    comparePapers, generateReport, saveReportContent
  }
})
