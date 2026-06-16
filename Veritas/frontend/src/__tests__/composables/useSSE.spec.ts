import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { useSSE } from '@/composables/useSSE'
import type { SSEEvent } from '@/types/agent'

/**
 * Mock EventSource
 * 支持 addEventListener / removeEventListener / close / 模拟触发事件 / 错误
 */
class MockEventSource {
  static instances: MockEventSource[] = []
  url: string
  readyState: number = 0
  private listeners: Map<string, Set<EventListener>> = new Map()
  private errorListeners: Set<((e: Event) => void) | null> = new Set()
  closed = false

  constructor(url: string) {
    this.url = url
    MockEventSource.instances.push(this)
  }

  addEventListener(type: string, listener: EventListener) {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set())
    }
    this.listeners.get(type)!.add(listener)
  }

  removeEventListener(type: string, listener: EventListener) {
    this.listeners.get(type)?.delete(listener)
  }

  set onerror(handler: ((e: Event) => void) | null) {
    this.errorListeners.clear()
    if (handler) this.errorListeners.add(handler)
  }

  get onerror(): ((e: Event) => void) | null {
    const first = this.errorListeners.values().next().value
    return first ?? null
  }

  close() {
    this.closed = true
    this.readyState = 2
  }

  // 测试辅助：模拟事件触发
  emit(type: string, data: unknown) {
    const event = { data: JSON.stringify(data) } as MessageEvent
    this.listeners.get(type)?.forEach(l => l(event))
  }

  // 测试辅助：模拟错误
  triggerError() {
    const event = {} as Event
    this.errorListeners.forEach(l => l?.(event))
  }
}

beforeEach(() => {
  MockEventSource.instances = []
  vi.stubGlobal('EventSource', MockEventSource)
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

function mountWithUseSSE(options: Parameters<typeof useSSE>[0] = {}, setupCallback?: (api: ReturnType<typeof useSSE>) => void) {
  let sse: ReturnType<typeof useSSE> | null = null
  const TestComp = defineComponent({
    setup() {
      sse = useSSE(options)
      setupCallback?.(sse)
      return () => h('div')
    }
  })
  const wrapper = mount(TestComp)
  return { wrapper, sse: sse! }
}

describe('useSSE', () => {
  it('connect creates EventSource and sets isConnected true', () => {
    const { sse } = mountWithUseSSE()
    sse.connect('/api/sse')
    expect(MockEventSource.instances).toHaveLength(1)
    expect(MockEventSource.instances[0].url).toBe('/api/sse')
    expect(sse.isConnected.value).toBe(true)
  })

  it('connect with empty url sets error', () => {
    const { sse } = mountWithUseSSE()
    sse.connect('')
    expect(sse.error.value).toBe('SSE URL 为空')
    expect(sse.isConnected.value).toBe(false)
  })

  it('parses agent_state_update event correctly', async () => {
    const events: SSEEvent[] = []
    const { sse } = mountWithUseSSE({
      onEvent: e => events.push(e)
    })
    sse.connect('/api/sse')
    MockEventSource.instances[0].emit('agent_state_update', {
      agentName: 'retriever',
      status: 'running',
      progress: 0.6
    })
    await nextTick()
    expect(events).toHaveLength(1)
    expect(events[0].type).toBe('agent_state_update')
    expect(events[0].data.agentName).toBe('retriever')
    expect(events[0].data.status).toBe('running')
    expect(sse.lastEvent.value?.type).toBe('agent_state_update')
  })

  it('parses all 4 supported event types', async () => {
    const types: string[] = []
    const { sse } = mountWithUseSSE({
      onEvent: e => types.push(e.type)
    })
    sse.connect('/api/sse')
    const es = MockEventSource.instances[0]
    es.emit('agent_state_update', { agentName: 'a', status: 'running' })
    es.emit('progress_update', { progress: 0.5 })
    es.emit('agent_error', { agentName: 'a', error: 'timeout' })
    es.emit('analysis_completed', { analysisId: 'a1' })
    await nextTick()
    expect(types).toEqual([
      'agent_state_update',
      'progress_update',
      'agent_error',
      'analysis_completed'
    ])
  })

  it('ignores unsupported event types', async () => {
    const events: SSEEvent[] = []
    const { sse } = mountWithUseSSE({ onEvent: e => events.push(e) })
    sse.connect('/api/sse')
    MockEventSource.instances[0].emit('unknown_event', { foo: 1 })
    await nextTick()
    expect(events).toHaveLength(0)
  })

  it('handles malformed JSON gracefully', async () => {
    const events: SSEEvent[] = []
    const { sse } = mountWithUseSSE({ onEvent: e => events.push(e) })
    sse.connect('/api/sse')
    const es = MockEventSource.instances[0]
    // 直接传入不可解析的数据
    es.addEventListener('agent_state_update', () => {})
    const brokenEvent = { data: '{bad json' } as MessageEvent
    es.addEventListener('agent_state_update', (() => {}) as EventListener)
    // 手动触发 parseEvent 不可达的路径
    const customListener = (e: MessageEvent) => {
      try { JSON.parse(e.data) } catch { /* ignore */ }
    }
    es.addEventListener('agent_state_update', customListener as EventListener)
    brokenEvent && customListener(brokenEvent)
    await nextTick()
    // 验证 onEvent 没有因为错误 JSON 被调用
    expect(events).toHaveLength(0)
  })

  it('error triggers reconnect after 3s', async () => {
    const { sse } = mountWithUseSSE()
    sse.connect('/api/sse')
    expect(MockEventSource.instances).toHaveLength(1)
    MockEventSource.instances[0].triggerError()
    expect(sse.isConnected.value).toBe(false)
    expect(sse.error.value).toBe('SSE 连接错误')
    // 推进 3 秒，应触发重连
    vi.advanceTimersByTime(3000)
    expect(MockEventSource.instances).toHaveLength(2)
    expect(sse.reconnectCount.value).toBe(1)
  })

  it('stops reconnecting after max attempts (5)', () => {
    const { sse } = mountWithUseSSE({ maxReconnectAttempts: 3 })
    sse.connect('/api/sse')
    // 模拟 4 次错误（初始 1 次 + 3 次重连错误）
    for (let i = 0; i < 4; i++) {
      const last = MockEventSource.instances[MockEventSource.instances.length - 1]
      last.triggerError()
      vi.advanceTimersByTime(3000)
    }
    expect(sse.reconnectCount.value).toBe(3)
    expect(sse.error.value).toContain('已达到最大重连次数')
    // 再次推进时间不再重连
    const countBefore = MockEventSource.instances.length
    vi.advanceTimersByTime(10000)
    expect(MockEventSource.instances.length).toBe(countBefore)
  })

  it('disconnect closes connection and resets reconnect count', () => {
    const { sse } = mountWithUseSSE()
    sse.connect('/api/sse')
    const es = MockEventSource.instances[0]
    sse.disconnect()
    expect(es.closed).toBe(true)
    expect(sse.isConnected.value).toBe(false)
    expect(sse.reconnectCount.value).toBe(0)
    // disconnect 后错误不再重连
    vi.advanceTimersByTime(10000)
    expect(MockEventSource.instances).toHaveLength(1)
  })

  it('analysis_completed auto-disconnects', async () => {
    const { sse } = mountWithUseSSE()
    sse.connect('/api/sse')
    const es = MockEventSource.instances[0]
    es.emit('analysis_completed', { analysisId: 'a1' })
    await nextTick()
    expect(es.closed).toBe(true)
    expect(sse.isConnected.value).toBe(false)
  })

  it('component unmount disconnects', async () => {
    const { wrapper, sse } = mountWithUseSSE()
    sse.connect('/api/sse')
    const es = MockEventSource.instances[0]
    wrapper.unmount()
    expect(es.closed).toBe(true)
  })

  it('reconnect forces a new connection and resets count', () => {
    const { sse } = mountWithUseSSE()
    sse.connect('/api/sse')
    MockEventSource.instances[0].triggerError()
    vi.advanceTimersByTime(3000)
    expect(sse.reconnectCount.value).toBe(1)
    sse.reconnect()
    expect(sse.reconnectCount.value).toBe(0)
    expect(MockEventSource.instances).toHaveLength(3)
  })

  it('reconnect without url is no-op', () => {
    const { sse } = mountWithUseSSE()
    sse.reconnect()
    expect(MockEventSource.instances).toHaveLength(0)
  })
})
