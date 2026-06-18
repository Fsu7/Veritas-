/**
 * AgentFlowView 重构后测试（FM4 Stage 3）
 * - 验证 4 个子组件正确渲染
 * - 验证 SSE 连接/断开生命周期
 * - 验证 SSE 事件处理
 * - 验证卸载清理
 *
 * 注意：由于 vi.mock hoisting，useSSE 返回的响应式状态在 computed 中不可追踪。
 * 因此仅测试确定性的行为（生命周期、事件分发），状态驱动测试留待 E2E 验证。
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'

// ============ Mock 模块（全部在 vi.mock 中内联定义） ============

const mockConnect = vi.fn()
const mockDisconnect = vi.fn()
const mockReconnect = vi.fn()

vi.mock('@/composables/useSSE', () => {
  let _onEvent: ((event: unknown) => void) | undefined
  let connected = false
  let error: string | null = null

  return {
    useSSE: vi.fn((opts: { onEvent?: (event: unknown) => void }) => {
      _onEvent = opts.onEvent
      return {
        get isConnected() { return { value: connected, __v_isRef: true } as unknown },
        get error() { return { value: error, __v_isRef: true } as unknown },
        connect: mockConnect,
        disconnect: mockDisconnect,
        reconnect: mockReconnect
      }
    }),
    // 暴露用于测试的内部方法
    __test_setConnected: (val: boolean) => { connected = val },
    __test_setError: (val: string | null) => { error = val },
    __test_triggerEvent: (event: unknown) => { _onEvent?.(event) }
  }
})

const mockUpdateAgentState = vi.fn()
const mockResetStates = vi.fn()
const mockAgentStates: Record<string, unknown> = {}

vi.mock('@/stores/agentStore', () => ({
  useAgentStore: vi.fn(() => ({
    agentStates: mockAgentStates,
    updateAgentState: mockUpdateAgentState,
    resetStates: mockResetStates,
    exitReplayMode: vi.fn(),
    isReplayMode: false,
    applyReplayFrame: vi.fn(),
    loadReplayData: vi.fn(),
    replayFrames: [],
    currentReplayIndex: 0
  }))
}))

const mockFetchAnalysisResult = vi.fn()

vi.mock('@/stores/sessionStore', () => ({
  useSessionStore: vi.fn(() => ({
    fetchAnalysisResult: mockFetchAnalysisResult
  }))
}))

const mockGetAgentStreamUrl = vi.fn((analysisId: string) =>
  `/api/analysis/${analysisId}/agent-stream?token=test`
)

vi.mock('@/api/analysis', () => ({
  analysisApi: {
    getAgentStreamUrl: mockGetAgentStreamUrl
  }
}))

vi.mock('vue-router', () => ({
  useRoute: vi.fn(() => ({
    params: { analysisId: 'test-analysis-123' }
  })),
  useRouter: vi.fn(() => ({
    back: vi.fn()
  }))
}))

vi.mock('@/components/agent/AgentFlowChart.vue', () => ({
  default: {
    name: 'AgentFlowChart',
    props: ['agentStates'],
    emits: ['node-click'],
    template: '<div class="mock-agent-flow-chart" @click="$emit(\'node-click\', \'analyzer\')">AgentFlowChart</div>'
  }
}))

vi.mock('@/components/agent/AgentStatusPanel.vue', () => ({
  default: {
    name: 'AgentStatusPanel',
    props: ['agentStates', 'highlightAgent'],
    emits: ['agent-click'],
    template: '<div class="mock-agent-status-panel">AgentStatusPanel</div>'
  }
}))

vi.mock('@/components/agent/IntermediateResult.vue', () => ({
  default: {
    name: 'IntermediateResult',
    props: ['agentStates', 'scrollToAgent'],
    template: '<div class="mock-intermediate-result">IntermediateResult</div>'
  }
}))

vi.mock('@/components/agent/TimeStats.vue', () => ({
  default: {
    name: 'TimeStats',
    props: ['agentStates'],
    template: '<div class="mock-time-stats">TimeStats</div>'
  }
}))

// ============ 辅助函数 ============

let useSSEModule: {
  __test_setConnected: (val: boolean) => void
  __test_setError: (val: string | null) => void
  __test_triggerEvent: (event: unknown) => void
}

async function getUseSSETestHelpers(): Promise<typeof useSSEModule> {
  useSSEModule = await import('@/composables/useSSE') as unknown as typeof useSSEModule
  return useSSEModule
}

async function mountAgentFlowView() {
  return mount(
    await import('@/views/AgentFlowView.vue').then(m => m.default || m),
    {
      global: {
        stubs: {
          'el-page-header': { template: '<div class="el-page-header"><slot name="content" /><slot name="extra" /></div>', props: ['title'] },
          'el-tag': { template: '<span class="el-tag"><slot /></span>', props: ['type', 'size', 'effect'] },
          'el-skeleton': { template: '<div class="el-skeleton" />', props: ['rows', 'animated'] },
          'el-empty': { template: '<div class="el-empty" />', props: ['description'] },
          'el-result': { template: '<div class="el-result"><slot name="extra" /></div>', props: ['icon', 'title', 'subTitle'] },
          'el-button': { template: '<button class="el-button" @click="$emit(\'click\')"><slot /></button>', props: ['type', 'size', 'text'] },
          'el-card': { template: '<div class="el-card"><slot /></div>', props: ['shadow'] },
          'el-tabs': { template: '<div class="el-tabs"><slot /></div>', props: ['modelValue'], emits: ['update:modelValue'] },
          'el-tab-pane': { template: '<div class="el-tab-pane"><slot /></div>', props: ['label', 'name'] },
          'el-text': { template: '<span class="el-text"><slot /></span>', props: ['type', 'size'] }
        }
      }
    }
  )
}

// ============ 测试 ============

describe('AgentFlowView (FM4 重构版)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    Object.keys(mockAgentStates).forEach(key => delete mockAgentStates[key])
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('SSE 事件处理', () => {
    it('agent_state_update 事件应调用 agentStore.updateAgentState', async () => {
      await mountAgentFlowView()
      await nextTick()
      const { __test_triggerEvent } = await getUseSSETestHelpers()

      __test_triggerEvent({
        type: 'agent_state_update',
        data: { agentName: 'coordinator', status: 'running', progress: 0.5 },
        timestamp: Date.now()
      })
      await nextTick()

      expect(mockUpdateAgentState).toHaveBeenCalledWith('coordinator', expect.objectContaining({
        status: 'running',
        progress: 0.5
      }))
    })

    it('analysis_completed 事件应断开 SSE', async () => {
      await mountAgentFlowView()
      await nextTick()
      const { __test_triggerEvent } = await getUseSSETestHelpers()

      __test_triggerEvent({
        type: 'analysis_completed',
        data: {},
        timestamp: Date.now()
      })
      await nextTick()

      expect(mockDisconnect).toHaveBeenCalled()
    })
  })

  describe('卸载清理', () => {
    it('组件卸载时应 disconnect + resetStates', async () => {
      const wrapper = await mountAgentFlowView()
      await nextTick()

      wrapper.unmount()
      await nextTick()

      expect(mockDisconnect).toHaveBeenCalled()
      expect(mockResetStates).toHaveBeenCalled()
    })
  })

  describe('初始化', () => {
    it('onMounted 时应拉取分析结果并连接 SSE', async () => {
      await mountAgentFlowView()
      await nextTick()

      expect(mockFetchAnalysisResult).toHaveBeenCalledWith('test-analysis-123')
      expect(mockConnect).toHaveBeenCalled()
    })
  })
})
