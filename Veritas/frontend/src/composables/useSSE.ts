import { ref, onScopeDispose } from 'vue'
import type { Ref } from 'vue'
import type { SSEEvent, SSEEventType } from '@/types/agent'

/** useSSE 配置项 */
export interface UseSSEOptions {
  /** 自定义事件回调（可覆盖默认行为） */
  onEvent?: (event: SSEEvent) => void
  /** 重连间隔（毫秒），默认 3000 */
  reconnectInterval?: number
  /** 最大重连次数，默认 5 */
  maxReconnectAttempts?: number
}

/** useSSE 返回值 */
export interface UseSSEReturn {
  isConnected: Ref<boolean>
  lastEvent: Ref<SSEEvent | null>
  reconnectCount: Ref<number>
  error: Ref<string | null>
  connect: (url: string) => void
  disconnect: () => void
  reconnect: () => void
}

const DEFAULT_RECONNECT_INTERVAL = 3000
const DEFAULT_MAX_RECONNECT_ATTEMPTS = 5
const SUPPORTED_EVENT_TYPES: SSEEventType[] = [
  'agent_state_update',
  'analysis_completed',
  'agent_error',
  'progress_update'
]

/**
 * SSE 连接管理 composable
 * - 封装 EventSource 生命周期
 * - 自动解析 4 种事件类型
 * - 错误自动重连（间隔 3s，最多 5 次）
 * - 组件作用域销毁时自动断开
 */
export function useSSE(options: UseSSEOptions = {}): UseSSEReturn {
  const {
    onEvent,
    reconnectInterval = DEFAULT_RECONNECT_INTERVAL,
    maxReconnectAttempts = DEFAULT_MAX_RECONNECT_ATTEMPTS
  } = options

  const isConnected = ref(false)
  const lastEvent = ref<SSEEvent | null>(null)
  const reconnectCount = ref(0)
  const error = ref<string | null>(null)

  let eventSource: EventSource | null = null
  let currentUrl: string | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let manualDisconnect = false

  function clearReconnectTimer() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  function parseEvent(type: string, rawData: string): SSEEvent | null {
    if (!SUPPORTED_EVENT_TYPES.includes(type as SSEEventType)) {
      return null
    }
    let parsed: Record<string, unknown>
    try {
      parsed = JSON.parse(rawData) as Record<string, unknown>
    } catch {
      return null
    }
    return {
      type: type as SSEEventType,
      data: parsed,
      timestamp: Date.now()
    }
  }

  function attachListeners(es: EventSource) {
    es.onopen = () => {
      isConnected.value = true
      reconnectCount.value = 0
    }

    SUPPORTED_EVENT_TYPES.forEach(eventType => {
      es.addEventListener(eventType, (event: MessageEvent) => {
        const parsed = parseEvent(eventType, event.data)
        if (!parsed) return
        lastEvent.value = parsed
        if (eventType === 'analysis_completed') {
          // 完成后自动断开
          disconnect()
        }
        onEvent?.(parsed)
      })
    })

    es.onerror = () => {
      isConnected.value = false
      error.value = 'SSE 连接错误'
      es.close()
      eventSource = null
      if (manualDisconnect) return
      scheduleReconnect()
    }
  }

  function scheduleReconnect() {
    if (manualDisconnect) return
    if (reconnectCount.value >= maxReconnectAttempts) {
      error.value = `已达到最大重连次数 ${maxReconnectAttempts}`
      return
    }
    if (!currentUrl) return
    clearReconnectTimer()
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      if (manualDisconnect || !currentUrl) return
      reconnectCount.value++
      doConnect(currentUrl)
    }, reconnectInterval)
  }

  function doConnect(url: string) {
    cleanupConnection()
    manualDisconnect = false
    const es = new EventSource(url)
    eventSource = es
    error.value = null
    attachListeners(es)
  }

  function connect(url: string) {
    if (!url) {
      error.value = 'SSE URL 为空'
      return
    }
    currentUrl = url
    reconnectCount.value = 0
    clearReconnectTimer()
    doConnect(url)
  }

  function disconnect() {
    manualDisconnect = true
    clearReconnectTimer()
    cleanupConnection()
    reconnectCount.value = 0
  }

  function cleanupConnection() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    isConnected.value = false
  }

  function reconnect() {
    if (!currentUrl) return
    reconnectCount.value = 0
    clearReconnectTimer()
    doConnect(currentUrl)
  }

  // 组件作用域销毁时自动清理
  onScopeDispose(() => {
    disconnect()
  })

  return {
    isConnected,
    lastEvent,
    reconnectCount,
    error,
    connect,
    disconnect,
    reconnect
  }
}
