import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import TimeStats from '@/components/agent/TimeStats.vue'
import type { AgentState } from '@/types/agent'

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
vi.mock('echarts/charts', () => ({ BarChart: {}, GraphChart: {}, EffectScatterChart: {} }))
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
  mockInit.mockClear()
})

const fullStates: Record<string, AgentState> = {
  coordinator: { name: 'coordinator', status: 'completed', durationMs: 2000 },
  retriever:   { name: 'retriever',   status: 'completed', durationMs: 1200 },
  analyzer:    { name: 'analyzer',    status: 'completed', durationMs: 3500 },
  comparer:    { name: 'comparer',    status: 'completed', durationMs: 1500 },
  generator:   { name: 'generator',   status: 'completed', durationMs: 8000 },
  reviewer:    { name: 'reviewer',    status: 'completed', durationMs: 1500 }
}

const inProgressStates: Record<string, AgentState> = {
  ...fullStates,
  generator: { name: 'generator', status: 'running', durationMs: 5000 }
}

describe('TimeStats', () => {
  it('mounts and initializes ECharts', () => {
    const wrapper = mount(TimeStats, {
      props: { agentStates: { ...fullStates } }
    })
    expect(mockInit).toHaveBeenCalled()
    expect(mockSetOption).toHaveBeenCalled()
    wrapper.unmount()
  })

  it('shows empty state when no states provided', () => {
    const wrapper = mount(TimeStats, {
      props: { agentStates: {} }
    })
    expect(wrapper.text()).toContain('暂无耗时数据')
    expect(mockInit).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('shows progress hint when analysis in progress', () => {
    const wrapper = mount(TimeStats, {
      props: { agentStates: { ...inProgressStates } }
    })
    expect(wrapper.text()).toContain('分析进行中')
    expect(wrapper.text()).toContain('5 / 6')
    wrapper.unmount()
  })

  it('does not show progress hint when all complete', () => {
    const wrapper = mount(TimeStats, {
      props: { agentStates: { ...fullStates } }
    })
    expect(wrapper.text()).not.toContain('分析进行中')
    wrapper.unmount()
  })

  it('re-renders on agentStates change', async () => {
    const wrapper = mount(TimeStats, {
      props: { agentStates: { ...fullStates } }
    })
    mockSetOption.mockClear()
    await wrapper.setProps({
      agentStates: { ...inProgressStates }
    })
    expect(mockSetOption).toHaveBeenCalled()
    wrapper.unmount()
  })

  it('disposes ECharts on unmount', () => {
    const wrapper = mount(TimeStats, {
      props: { agentStates: { ...fullStates } }
    })
    wrapper.unmount()
    expect(mockDispose).toHaveBeenCalled()
  })

  it('renders chart container with BEM class', () => {
    const wrapper = mount(TimeStats, {
      props: { agentStates: { ...fullStates } }
    })
    expect(wrapper.find('.time-stats__chart').exists()).toBe(true)
    wrapper.unmount()
  })
})
