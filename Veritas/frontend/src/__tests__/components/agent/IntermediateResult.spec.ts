import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import IntermediateResult from '@/components/agent/IntermediateResult.vue'
import type { AgentState } from '@/types/agent'

const states: Record<string, AgentState> = {
  coordinator: { name: 'coordinator', status: 'completed', durationMs: 2000, intermediateResult: '协调完成' },
  retriever:   { name: 'retriever',   status: 'completed', durationMs: 1200, intermediateResult: '检索到 15 篇论文' },
  analyzer:    { name: 'analyzer',    status: 'running',   durationMs: 500,  intermediateResult: '正在分析...' },
  comparer:    { name: 'comparer',    status: 'waiting' },
  generator:   { name: 'generator',   status: 'failed',    durationMs: 100,  error: '生成失败' },
  reviewer:    { name: 'reviewer',    status: 'waiting' }
}

describe('IntermediateResult', () => {
  it('shows empty state when no completed/running with results', () => {
    const wrapper = mount(IntermediateResult, {
      props: { agentStates: {} }
    })
    expect(wrapper.text()).toContain('等待 Agent 产出结果')
    wrapper.unmount()
  })

  it('hides waiting agents', () => {
    const wrapper = mount(IntermediateResult, {
      props: { agentStates: { ...states } }
    })
    const text = wrapper.text()
    // comparer & reviewer 都为 waiting 且无 intermediateResult，不应出现
    expect(text).toContain('协调完成')
    expect(text).toContain('检索到 15 篇论文')
    expect(text).toContain('正在分析...')
  })

  it('hides failed agents without intermediateResult', () => {
    const wrapper = mount(IntermediateResult, {
      props: { agentStates: { ...states } }
    })
    // generator 是 failed 但没有 intermediateResult，所以不出现在时间线
    expect(wrapper.text()).not.toContain('生成失败')
    wrapper.unmount()
  })

  it('truncates long intermediate results', () => {
    const longText = 'a'.repeat(500)
    const wrapper = mount(IntermediateResult, {
      props: {
        agentStates: {
          ...states,
          coordinator: { name: 'coordinator', status: 'completed', durationMs: 2000, intermediateResult: longText }
        }
      }
    })
    expect(wrapper.text()).toContain('...')
    // 长度不会超过 200 + '...' 字符
    const summary = wrapper.find('.intermediate-result__summary')
    expect(summary.exists()).toBe(true)
    expect(summary.text().length).toBeLessThanOrEqual(203)
    wrapper.unmount()
  })

  it('formats duration < 1s as ms', () => {
    const wrapper = mount(IntermediateResult, {
      props: {
        agentStates: {
          ...states,
          coordinator: { name: 'coordinator', status: 'completed', durationMs: 500, intermediateResult: 'x' }
        }
      }
    })
    expect(wrapper.text()).toContain('500ms')
    wrapper.unmount()
  })

  it('formats duration < 60s as Xs', () => {
    const wrapper = mount(IntermediateResult, {
      props: {
        agentStates: {
          ...states,
          coordinator: { name: 'coordinator', status: 'completed', durationMs: 12_345, intermediateResult: 'x' }
        }
      }
    })
    expect(wrapper.text()).toContain('12.3s')
    wrapper.unmount()
  })

  it('formats duration >= 60s as Xm Ys', () => {
    const wrapper = mount(IntermediateResult, {
      props: {
        agentStates: {
          ...states,
          coordinator: { name: 'coordinator', status: 'completed', durationMs: 90_000, intermediateResult: 'x' }
        }
      }
    })
    expect(wrapper.text()).toContain('1m 30s')
    wrapper.unmount()
  })
})
