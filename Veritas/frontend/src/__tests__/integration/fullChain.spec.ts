import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useUserStore } from '@/stores/userStore'
import { usePaperStore } from '@/stores/paperStore'
import { useSessionStore } from '@/stores/sessionStore'
import { useAgentStore } from '@/stores/agentStore'
import type { Paper } from '@/types/paper'
import type { AnalysisResult } from '@/types/analysis'

class MockEventSource {
  url: string
  onerror: ((this: MockEventSource, ev: Event) => void) | null = null
  onmessage: ((this: MockEventSource, ev: MessageEvent) => void) | null = null
  onopen: ((this: MockEventSource, ev: Event) => void) | null = null
  private listeners: Record<string, EventListener[]> = {}

  static readonly CONNECTING = 0
  static readonly OPEN = 1
  static readonly CLOSED = 2

  constructor(url: string) {
    this.url = url
  }
  addEventListener(type: string, listener: EventListener) {
    if (!this.listeners[type]) this.listeners[type] = []
    this.listeners[type].push(listener)
  }
  removeEventListener() {}
  close() {}
  dispatchEvent() { return true }
}

vi.stubGlobal('EventSource', MockEventSource)

vi.mock('@/api/user', () => ({
  userApi: {
    register: vi.fn(),
    login: vi.fn(),
    getUserInfo: vi.fn(),
    getProfile: vi.fn(),
    createProfile: vi.fn(),
    updateProfile: vi.fn()
  }
}))

vi.mock('@/api/paper', () => ({
  paperApi: {
    search: vi.fn(),
    getDetail: vi.fn(),
    addFavorite: vi.fn(),
    removeFavorite: vi.fn()
  }
}))

vi.mock('@/api/analysis', () => ({
  analysisApi: {
    analyzePaper: vi.fn(),
    getResult: vi.fn(),
    getStatus: vi.fn(),
    getAgentStreamUrl: vi.fn().mockReturnValue('/api/analysis/test-id/agent-stream')
  }
}))

vi.mock('@/api/session', () => ({
  sessionApi: {
    create: vi.fn(),
    list: vi.fn(),
    getDetail: vi.fn(),
    delete: vi.fn()
  }
}))

import { userApi } from '@/api/user'
import { paperApi } from '@/api/paper'
import { analysisApi } from '@/api/analysis'
import { sessionApi } from '@/api/session'

const mockPaper: Paper = {
  paperId: 'paper_001',
  title: 'Multi-Agent Systems Survey',
  authors: ['Zhang', 'Li'],
  abstract: 'A comprehensive survey of multi-agent systems.',
  year: 2024,
  venue: 'ACL',
  keywords: ['Multi-Agent', 'LLM'],
  citationCount: 100,
  score: 0.95
}

const mockAnalysisResult: AnalysisResult = {
  analysisId: 'analysis_001',
  status: 'completed',
  type: 'paper_analysis',
  result: {
    analysis: {
      researchQuestion: 'How do multi-agent systems collaborate?',
      coreMethod: 'LangGraph-based orchestration',
      keyExperiments: '6-agent workflow evaluation',
      coreFindings: 'Multi-agent collaboration improves accuracy by 25%',
      limitations: 'Limited to English papers',
      plainExplanation: 'Multiple AI agents work together like a team to analyze papers.'
    }
  }
}

describe('Full Chain Integration', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('register → login → search → detail → analyze flow', async () => {
    vi.useFakeTimers()
    const userStore = useUserStore()
    const paperStore = usePaperStore()
    const sessionStore = useSessionStore()

    vi.mocked(userApi.register).mockResolvedValue({} as never)
    await userStore.register('testuser', 'test@example.com', 'password123')
    expect(userApi.register).toHaveBeenCalledWith({
      username: 'testuser',
      email: 'test@example.com',
      password: 'password123'
    })

    vi.mocked(userApi.login).mockResolvedValue({
      token: 'jwt_token_123',
      userId: 'user_001',
      username: 'testuser',
      hasProfile: false
    })
    await userStore.login('testuser', 'password123')
    expect(userStore.isLoggedIn).toBe(true)
    expect(userStore.token).toBe('jwt_token_123')
    expect(userStore.userId).toBe('user_001')

    vi.mocked(paperApi.search).mockResolvedValue({
      items: [mockPaper],
      total: 1,
      page: 1,
      size: 10,
      totalPages: 1
    })
    await paperStore.searchPapers('multi-agent')
    expect(paperStore.searchResults).toHaveLength(1)
    expect(paperStore.searchResults[0].paperId).toBe('paper_001')

    vi.mocked(paperApi.getDetail).mockResolvedValue(mockPaper)
    const paperDetail = await paperApi.getDetail('paper_001')
    expect(paperDetail.title).toBe('Multi-Agent Systems Survey')
    expect(paperDetail.authors).toEqual(['Zhang', 'Li'])

    vi.mocked(sessionApi.create).mockResolvedValue({
      sessionId: 'session_001',
      topic: 'Multi-Agent Systems Survey',
      status: 'active',
      createdAt: '2026-05-27T00:00:00Z'
    })
    vi.mocked(analysisApi.analyzePaper).mockResolvedValue({
      analysisId: 'analysis_001',
      status: 'pending',
      type: 'paper_analysis'
    } as never)
    vi.mocked(analysisApi.getStatus)
      .mockResolvedValueOnce({
        analysisId: 'analysis_001',
        status: 'processing',
        type: 'paper_analysis'
      } as never)
      .mockResolvedValueOnce(mockAnalysisResult as never)

    const analysisPromise = sessionStore.startAnalysis('Multi-Agent Systems Survey', 'paper_001')
    await vi.advanceTimersByTimeAsync(3000)
    await vi.advanceTimersByTimeAsync(3000)
    const result = await analysisPromise

    expect(result.analysisId).toBe('analysis_001')
    expect(result.result?.analysis?.researchQuestion).toBe('How do multi-agent systems collaborate?')
    expect(result.result?.analysis?.coreMethod).toBe('LangGraph-based orchestration')
    expect(result.result?.analysis?.coreFindings).toBe('Multi-agent collaboration improves accuracy by 25%')
    expect(result.result?.analysis?.limitations).toBe('Limited to English papers')

    vi.useRealTimers()
  })

  it('sessionStore analysisStatus transitions through stages', async () => {
    vi.useFakeTimers()
    const sessionStore = useSessionStore()
    expect(sessionStore.analysisStatus).toBe('idle')

    vi.mocked(sessionApi.create).mockResolvedValue({
      sessionId: 'session_001',
      topic: 'Test',
      status: 'active',
      createdAt: '2026-05-27T00:00:00Z'
    })
    vi.mocked(analysisApi.analyzePaper).mockResolvedValue({
      analysisId: 'analysis_001',
      status: 'pending',
      type: 'paper_analysis'
    } as never)
    vi.mocked(analysisApi.getStatus).mockResolvedValue(mockAnalysisResult as never)

    const promise = sessionStore.startAnalysis('Test', 'paper_001')
    await vi.advanceTimersByTimeAsync(3000)
    await promise

    expect(sessionStore.analysisStatus).toBe('completed')
    expect(sessionStore.isAnalysisCompleted).toBe(true)

    vi.useRealTimers()
  })

  it('sessionStore handles analysis failure', async () => {
    const sessionStore = useSessionStore()

    vi.mocked(sessionApi.create).mockResolvedValue({
      sessionId: 'session_001',
      topic: 'Test',
      status: 'active',
      createdAt: '2026-05-27T00:00:00Z'
    })
    vi.mocked(analysisApi.analyzePaper).mockRejectedValue(new Error('Service unavailable'))

    await expect(sessionStore.startAnalysis('Test', 'paper_001')).rejects.toThrow()
    expect(sessionStore.isAnalysisFailed).toBe(true)
    expect(sessionStore.analysisError).toBe('Service unavailable')
  })

  it('sessionStore cleanup resets state', async () => {
    const sessionStore = useSessionStore()
    const agentStore = useAgentStore()

    agentStore.updateAgentState('retriever', { status: 'running', progress: 0.5 })
    sessionStore.analysisStatus = 'polling'
    sessionStore.analysisError = 'some error'

    sessionStore.cleanup()

    expect(sessionStore.analysisStatus).toBe('idle')
    expect(sessionStore.analysisError).toBeNull()
    expect(agentStore.agentStatesList).toHaveLength(0)
  })

  it('agentStore updates from SSE events', () => {
    const agentStore = useAgentStore()

    agentStore.updateAgentState('coordinator', {
      status: 'completed',
      progress: 1,
      durationMs: 1200
    })
    agentStore.updateAgentState('retriever', {
      status: 'running',
      progress: 0.6,
      intermediateResult: '找到15篇相关论文'
    })

    expect(agentStore.agentStatesList).toHaveLength(2)
    expect(agentStore.getAgentState('coordinator')?.status).toBe('completed')
    expect(agentStore.getAgentState('retriever')?.progress).toBe(0.6)
    expect(agentStore.progress).toBe(0.5)
  })

  it('userStore profile controls plain explanation visibility', async () => {
    const userStore = useUserStore()

    expect(userStore.hasProfile).toBe(false)

    vi.mocked(userApi.getProfile).mockResolvedValue({
      educationLevel: 'undergraduate',
      researchField: 'NLP',
      knowledgeLevel: 'beginner',
      preferredStyle: 'simple'
    })
    userStore.userId = 'user_001'
    await userStore.fetchProfile()

    expect(userStore.hasProfile).toBe(true)
    expect(userStore.profile?.knowledgeLevel).toBe('beginner')
  })
})
