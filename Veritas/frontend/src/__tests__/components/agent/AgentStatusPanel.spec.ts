import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AgentStatusPanel from '@/components/agent/AgentStatusPanel.vue'
import type { AgentState } from '@/types/agent'

const baseStates: Record<string, AgentState> = {
  coordinator: { name: 'coordinator', status: 'completed', durationMs: 2000 },
  retriever:   { name: 'retriever',   status: 'running',   progress: 0.6, durationMs: 1200 },
  analyzer:    { name: 'analyzer',    status: 'waiting' },
  comparer:    { name: 'comparer',    status: 'waiting' },
  generator:   { name: 'generator',   status: 'failed',    durationMs: 500 },
  reviewer:    { name: 'reviewer',    status: 'waiting' }
}

describe('AgentStatusPanel', () => {
  it('renders 6 agent items', () => {
    const wrapper = mount(AgentStatusPanel, {
      props: { agentStates: { ...baseStates } }
    })
    const items = wrapper.findAll('.agent-status-panel__item')
    expect(items).toHaveLength(6)
    wrapper.unmount()
  })

  it('renders Chinese agent names', () => {
    const wrapper = mount(AgentStatusPanel, {
      props: { agentStates: { ...baseStates } }
    })
    const text = wrapper.text()
    expect(text).toContain('协调者')
    expect(text).toContain('检索员')
    expect(text).toContain('分析员')
    expect(text).toContain('对比员')
    expect(text).toContain('生成员')
    expect(text).toContain('审核员')
    wrapper.unmount()
  })

  it('renders correct status labels', () => {
    const wrapper = mount(AgentStatusPanel, {
      props: { agentStates: { ...baseStates } }
    })
    const text = wrapper.text()
    expect(text).toContain('已完成')
    expect(text).toContain('执行中')
    expect(text).toContain('失败')
    expect(text).toContain('等待中')
    wrapper.unmount()
  })

  it('renders progress counter', () => {
    const wrapper = mount(AgentStatusPanel, {
      props: { agentStates: { ...baseStates } }
    })
    expect(wrapper.text()).toContain('已完成')
    expect(wrapper.text()).toMatch(/\d+\s*\/\s*6/)
    wrapper.unmount()
  })

  it('emits agent-click when item clicked', async () => {
    const wrapper = mount(AgentStatusPanel, {
      props: { agentStates: { ...baseStates } }
    })
    const items = wrapper.findAll('.agent-status-panel__item')
    await items[1].trigger('click') // retriever
    expect(wrapper.emitted('agent-click')).toBeTruthy()
    expect(wrapper.emitted('agent-click')![0]).toEqual(['retriever'])
    wrapper.unmount()
  })

  it('applies is-running class for running status', () => {
    const wrapper = mount(AgentStatusPanel, {
      props: { agentStates: { ...baseStates } }
    })
    const items = wrapper.findAll('.agent-status-panel__item')
    const retrieverItem = items[1] // retriever is running
    expect(retrieverItem.classes()).toContain('is-running')
    wrapper.unmount()
  })

  it('applies is-highlight class when highlightAgent matches', () => {
    const wrapper = mount(AgentStatusPanel, {
      props: { agentStates: { ...baseStates }, highlightAgent: 'analyzer' }
    })
    const items = wrapper.findAll('.agent-status-panel__item')
    const analyzerItem = items[2] // analyzer
    expect(analyzerItem.classes()).toContain('is-highlight')
    wrapper.unmount()
  })

  it('shows empty state when no states provided', () => {
    const wrapper = mount(AgentStatusPanel, {
      props: { agentStates: {} }
    })
    expect(wrapper.text()).toContain('等待开始分析')
    wrapper.unmount()
  })

  it('renders duration for completed/running/failed agents', () => {
    const wrapper = mount(AgentStatusPanel, {
      props: { agentStates: { ...baseStates } }
    })
    const text = wrapper.text()
    // coordinator 2000ms → 2.0s
    expect(text).toMatch(/2\.0s/)
    wrapper.unmount()
  })

  it('formats long duration as Xm Ys', () => {
    const wrapper = mount(AgentStatusPanel, {
      props: {
        agentStates: {
          ...baseStates,
          coordinator: { name: 'coordinator', status: 'completed', durationMs: 90_000 }
        }
      }
    })
    expect(wrapper.text()).toContain('1m 30s')
    wrapper.unmount()
  })
})
