import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { sessionApi } from '@/api/session'
import { analysisApi } from '@/api/analysis'
import { useAgentStore } from '@/stores/agentStore'
import type { AnalysisResult } from '@/types/analysis'
import type { SessionResponse, SessionDetail } from '@/types/session'
import type { PageResponse } from '@/types/common'

type AnalysisStatus = 'idle' | 'creating_session' | 'starting_analysis' | 'polling' | 'connecting_sse' | 'completed' | 'failed'

const MAX_POLL_ATTEMPTS = 60
const POLL_INTERVAL = 3000
const SSE_RECONNECT_INTERVAL = 3000
const SSE_MAX_RECONNECT = 5

export const useSessionStore = defineStore('session', () => {
  const agentStore = useAgentStore()

  const currentSessionId = ref<string | null>(null)
  const currentAnalysisId = ref<string | null>(null)
  const analysisResults = ref<Map<string, AnalysisResult>>(new Map())

  const analysisStatus = ref<AnalysisStatus>('idle')
  const analysisError = ref<string | null>(null)
  const pollTimer = ref<ReturnType<typeof setTimeout> | null>(null)
  const eventSource = ref<EventSource | null>(null)
  const reconnectTimer = ref<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttempts = ref(0)

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
    disconnectSSE()
    agentStore.resetStates()
    analysisStatus.value = 'idle'
    analysisError.value = null
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
      connectAgentStream(result.analysisId)
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

  function connectAgentStream(analysisId: string) {
    if (!analysisId) return

    analysisStatus.value = 'connecting_sse'
    const url = analysisApi.getAgentStreamUrl(analysisId)
    const es = new EventSource(url)
    eventSource.value = es

    es.addEventListener('agent_state_update', (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data)
        agentStore.updateAgentState(data.agentName, {
          status: data.status,
          progress: data.progress,
          intermediateResult: data.intermediateResult,
          durationMs: data.durationMs,
          error: data.error
        })
      } catch {
        // ignore parse errors
      }
    })

    es.addEventListener('analysis_completed', () => {
      disconnectSSE()
      analysisStatus.value = 'completed'
    })

    es.onerror = () => {
      es.close()
      eventSource.value = null
      if (reconnectAttempts.value >= SSE_MAX_RECONNECT) return
      if (!currentAnalysisId.value) return
      reconnectAttempts.value++
      reconnectTimer.value = setTimeout(() => {
        // 防止 disconnectSSE() 后定时器仍触发幽灵连接
        if (currentAnalysisId.value) {
          connectAgentStream(currentAnalysisId.value)
        }
      }, SSE_RECONNECT_INTERVAL)
    }
  }

  function disconnectSSE() {
    if (reconnectTimer.value) {
      clearTimeout(reconnectTimer.value)
      reconnectTimer.value = null
    }
    if (eventSource.value) {
      eventSource.value.close()
      eventSource.value = null
    }
    reconnectAttempts.value = 0
  }

  // ============================================================
  // P0-8: View 层 API 调用迁移到 Store Action
  // ============================================================

  async function comparePapers(paperIds: string[]): Promise<any> {
    analysisError.value = null
    try {
      const result = await analysisApi.comparePapers({ paperIds })
      return result
    } catch (e: any) {
      analysisError.value = e.message || '对比失败'
      throw e
    }
  }

  async function generateReport(params: { topic: string; paperIds: string[]; profile: any }): Promise<any> {
    analysisError.value = null
    try {
      const result = await analysisApi.generateReport(params)
      return result
    } catch (e: any) {
      analysisError.value = e.message || '生成报告失败'
      throw e
    }
  }

  async function saveReportContent(analysisId: string, content: string): Promise<void> {
    try {
      await analysisApi.saveReportContent(analysisId, content)
    } catch (e: any) {
      analysisError.value = e.message || '保存失败'
      throw e
    }
  }

  return {
    currentSessionId, currentAnalysisId, analysisResults,
    analysisStatus, analysisError, pollTimer, eventSource, reconnectAttempts,
    isAnalyzing, isAnalysisCompleted, isAnalysisFailed,
    createSession, fetchAnalysisResult, fetchSessions,
    startAnalysis, pollAnalysisStatus, connectAgentStream, disconnectSSE, cleanup,
    comparePapers, generateReport, saveReportContent
  }
})
