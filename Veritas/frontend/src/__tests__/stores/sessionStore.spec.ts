import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSessionStore } from '@/stores/sessionStore'

describe('sessionStore SSE URL generation', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('getAgentStreamUrl includes token in query', async () => {
    // 直接调用 analysisApi.getAgentStreamUrl
    const { analysisApi } = await import('@/api/analysis')
    const url = analysisApi.getAgentStreamUrl('ana_001', 'test-jwt-token-123')
    expect(url).toContain('token=test-jwt-token-123')
    expect(url).toContain('/api/analysis/ana_001/agent-stream')
  })

  it('handles missing token gracefully', async () => {
    const { analysisApi } = await import('@/api/analysis')
    const url = analysisApi.getAgentStreamUrl('ana_002', '')
    expect(url).toContain('token=')
  })

  it('URL-encodes special characters in token', async () => {
    const { analysisApi } = await import('@/api/analysis')
    const url = analysisApi.getAgentStreamUrl('ana_003', 'token+with/special=chars')
    expect(url).toContain('token=token%2Bwith%2Fspecial%3Dchars')
  })
})

describe('sessionStore cleanup', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('resets analysis status on cleanup', () => {
    const store = useSessionStore()
    store.analysisStatus = 'completed'
    store.analysisError = 'test'
    store.cleanup()
    expect(store.analysisStatus).toBe('idle')
    expect(store.analysisError).toBe(null)
  })
})
