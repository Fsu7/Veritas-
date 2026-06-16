import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import AgentFlowChart from '@/components/agent/AgentFlowChart.vue'
import type { AgentState } from '@/types/agent'

// Mock echarts/core 以避免真实初始化
const mockSetOption = vi.fn()
const mockDispose = vi.fn()
const mockResize = vi.fn()
const mockOn = vi.fn()
const mockInit = vi.fn(() => ({
  setOption: mockSetOption,
  dispose: mockDispose,
  resize: mockResize,
  on: mockOn
}))

vi.mock('echarts/core', () => ({
  default: {
    init: (..._args: unknown[]) => mockInit(),
    use: vi.fn()
  },
  init: (..._args: unknown[]) => mockInit(),
  use: vi.fn()
}))
vi.mock('echarts/charts', () => ({ GraphChart: {}, BarChart: {}, EffectScatterChart: {} }))
vi.mock('echarts/components', () => ({
  TooltipComponent: {},
  EffectScatterComponent: {},
  TitleComponent: {},
  GridComponent: {},
  LegendComponent: {}
}))
vi.mock('echarts/renderers', () => ({ CanvasRenderer: {} }))

beforeEach(() => {
  mockSetOption.mockClear()
  mockDispose.mockClear()
  mockResize.mockClear()
  mockOn.mockClear()
  mockInit.mockClear()
})

const emptyStates: Record<string, AgentState> = {
  coordinator: { name: 'coordinator', status: 'waiting' },
  retriever:   { name: 'retriever',   status: 'waiting' },
  analyzer:    { name: 'analyzer',    status: 'waiting' },
  comparer:    { name: 'comparer',    status: 'waiting' },
  generator:   { name: 'generator',   status: 'waiting' },
  reviewer:    { name: 'reviewer',    status: 'waiting' }
}

describe('AgentFlowChart', () => {
  it('mounts and initializes ECharts', () => {
    const wrapper = mount(AgentFlowChart, {
      props: { agentStates: { ...emptyStates } }
    })
    expect(mockInit).toHaveBeenCalled()
    expect(mockSetOption).toHaveBeenCalled()
    wrapper.unmount()
  })

  it('renders chart container with BEM class', () => {
    const wrapper = mount(AgentFlowChart, {
      props: { agentStates: { ...emptyStates } }
    })
    expect(wrapper.find('.agent-flow-chart').exists()).toBe(true)
    wrapper.unmount()
  })

  it('re-renders when agentStates change', async () => {
    const wrapper = mount(AgentFlowChart, {
      props: { agentStates: { ...emptyStates } }
    })
    mockSetOption.mockClear()
    await wrapper.setProps({
      agentStates: {
        ...emptyStates,
        retriever: { name: 'retriever', status: 'running', progress: 0.5 }
      }
    })
    expect(mockSetOption).toHaveBeenCalled()
    wrapper.unmount()
  })

  it('disposes ECharts instance on unmount', () => {
    const wrapper = mount(AgentFlowChart, {
      props: { agentStates: { ...emptyStates } }
    })
    wrapper.unmount()
    expect(mockDispose).toHaveBeenCalled()
  })

  it('emits node-click with agent name', () => {
    const wrapper = mount(AgentFlowChart, {
      props: { agentStates: { ...emptyStates } }
    })
    // 取出 mockOn 注册的 click handler
    const clickCall = mockOn.mock.calls.find(c => c[0] === 'click')
    expect(clickCall).toBeDefined()
    const handler = clickCall![1] as (params: unknown) => void
    handler({ dataType: 'node', data: { value: { rawName: 'analyzer' } } })
    expect(wrapper.emitted('node-click')).toBeTruthy()
    expect(wrapper.emitted('node-click')![0]).toEqual(['analyzer'])
    wrapper.unmount()
  })

  it('does not emit node-click when clicking non-node', () => {
    const wrapper = mount(AgentFlowChart, {
      props: { agentStates: { ...emptyStates } }
    })
    const clickCall = mockOn.mock.calls.find(c => c[0] === 'click')
    const handler = clickCall![1] as (params: unknown) => void
    handler({ dataType: 'edge', data: {} })
    expect(wrapper.emitted('node-click')).toBeFalsy()
    wrapper.unmount()
  })
})
