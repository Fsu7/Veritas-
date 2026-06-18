import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAgentStore } from '@/stores/agentStore'
import type { AgentState, ReplayFrame, SSEEvent } from '@/types/agent'

// 构造一个基础 AgentState
function makeState(
  name: string,
  status: AgentState['status'],
  extra: Partial<AgentState> = {}
): AgentState {
  return { name, status, ...extra }
}

// 构造一个回放帧
function makeFrame(
  agentStates: Record<string, AgentState>,
  timestamp = Date.now()
): ReplayFrame {
  const event: SSEEvent = {
    type: 'agent_state_update',
    data: {},
    timestamp
  }
  return { timestamp, agentStates, event }
}

describe('useAgentStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('updateAgentState', () => {
    it('更新指定 agent 状态', () => {
      const store = useAgentStore()
      const state = makeState('coordinator', 'running', { progress: 50 })
      store.updateAgentState('coordinator', state)

      const result = store.getAgentState('coordinator')
      expect(result).toBeDefined()
      expect(result?.name).toBe('coordinator')
      expect(result?.status).toBe('running')
      expect(result?.progress).toBe(50)
    })

    it('保留已有字段（合并更新）', () => {
      const store = useAgentStore()
      // 先写入完整状态
      store.updateAgentState('retriever', makeState('retriever', 'running', {
        progress: 30,
        intermediateResult: 'partial',
        durationMs: 100
      }))

      // 仅更新 status，其他字段应保留
      store.updateAgentState('retriever', { status: 'completed' })

      const result = store.getAgentState('retriever')
      expect(result?.status).toBe('completed')
      expect(result?.progress).toBe(30)
      expect(result?.intermediateResult).toBe('partial')
      expect(result?.durationMs).toBe(100)
      expect(result?.name).toBe('retriever')
    })
  })

  describe('resetStates', () => {
    it('清空所有状态', () => {
      const store = useAgentStore()
      store.updateAgentState('coordinator', makeState('coordinator', 'running'))
      store.updateAgentState('retriever', makeState('retriever', 'waiting'))
      store.currentAnalysisId = 'ana_001'

      store.resetStates()

      expect(store.agentStates).toEqual({})
      expect(store.flowData).toBeNull()
      expect(store.currentAnalysisId).toBeNull()
      // getAgentState 返回 undefined
      expect(store.getAgentState('coordinator')).toBeUndefined()
    })
  })

  describe('progress 计算属性', () => {
    it('无 agent 返回 0', () => {
      const store = useAgentStore()
      expect(store.progress).toBe(0)
    })

    it('部分完成返回正确比例', () => {
      const store = useAgentStore()
      store.updateAgentState('a1', makeState('a1', 'completed'))
      store.updateAgentState('a2', makeState('a2', 'running'))
      store.updateAgentState('a3', makeState('a3', 'waiting'))
      store.updateAgentState('a4', makeState('a4', 'completed'))

      // 2/4 = 0.5
      expect(store.progress).toBe(0.5)
    })

    it('全部完成返回 1', () => {
      const store = useAgentStore()
      store.updateAgentState('a1', makeState('a1', 'completed'))
      store.updateAgentState('a2', makeState('a2', 'completed'))

      expect(store.progress).toBe(1)
    })
  })

  describe('agentStatesList', () => {
    it('返回数组', () => {
      const store = useAgentStore()
      store.updateAgentState('a1', makeState('a1', 'running'))
      store.updateAgentState('a2', makeState('a2', 'completed'))

      const list = store.agentStatesList
      expect(Array.isArray(list)).toBe(true)
      expect(list).toHaveLength(2)
      expect(list.map(s => s.name).sort()).toEqual(['a1', 'a2'])
    })
  })

  describe('activeAgents', () => {
    it('返回 running 状态的 agent', () => {
      const store = useAgentStore()
      store.updateAgentState('a1', makeState('a1', 'running'))
      store.updateAgentState('a2', makeState('a2', 'completed'))
      store.updateAgentState('a3', makeState('a3', 'running'))
      store.updateAgentState('a4', makeState('a4', 'waiting'))

      const active = store.activeAgents
      expect(active).toHaveLength(2)
      expect(active.every(s => s.status === 'running')).toBe(true)
      expect(active.map(s => s.name).sort()).toEqual(['a1', 'a3'])
    })
  })

  describe('loadReplayData', () => {
    it('进入回放模式 + 应用第一帧', () => {
      const store = useAgentStore()
      const frame0States: Record<string, AgentState> = {
        coordinator: makeState('coordinator', 'running', { progress: 10 })
      }
      const frame1States: Record<string, AgentState> = {
        coordinator: makeState('coordinator', 'completed', { progress: 100 })
      }
      const frames = [
        makeFrame(frame0States, 1000),
        makeFrame(frame1States, 2000)
      ]

      store.loadReplayData(frames)

      // 进入回放模式
      expect(store.isReplayMode).toBe(true)
      expect(store.replayFrames).toHaveLength(2)
      expect(store.currentReplayIndex).toBe(0)

      // 应用第一帧：agentStates 应等于第一帧的快照
      expect(store.getAgentState('coordinator')).toBeDefined()
      expect(store.getAgentState('coordinator')?.status).toBe('running')
      expect(store.getAgentState('coordinator')?.progress).toBe(10)
    })
  })

  describe('exitReplayMode', () => {
    it('退出回放模式', () => {
      const store = useAgentStore()
      const frames = [makeFrame({ a1: makeState('a1', 'running') })]
      store.loadReplayData(frames)

      // 确认进入回放
      expect(store.isReplayMode).toBe(true)

      store.exitReplayMode()

      expect(store.isReplayMode).toBe(false)
      expect(store.replayFrames).toEqual([])
      expect(store.currentReplayIndex).toBe(0)
    })
  })

  describe('applyReplayFrame', () => {
    it('应用指定帧', () => {
      const store = useAgentStore()
      const frame0States: Record<string, AgentState> = {
        a1: makeState('a1', 'waiting')
      }
      const frame1States: Record<string, AgentState> = {
        a1: makeState('a1', 'running', { progress: 50 }),
        a2: makeState('a2', 'running')
      }
      const frame2States: Record<string, AgentState> = {
        a1: makeState('a1', 'completed', { progress: 100 }),
        a2: makeState('a2', 'completed', { progress: 100 })
      }
      const frames = [
        makeFrame(frame0States, 1000),
        makeFrame(frame1States, 2000),
        makeFrame(frame2States, 3000)
      ]

      store.loadReplayData(frames)
      // 初始应用第 0 帧
      expect(store.getAgentState('a1')?.status).toBe('waiting')

      // 应用第 1 帧
      store.applyReplayFrame(1)
      expect(store.currentReplayIndex).toBe(1)
      expect(store.getAgentState('a1')?.status).toBe('running')
      expect(store.getAgentState('a1')?.progress).toBe(50)
      expect(store.getAgentState('a2')?.status).toBe('running')

      // 应用第 2 帧
      store.applyReplayFrame(2)
      expect(store.currentReplayIndex).toBe(2)
      expect(store.getAgentState('a1')?.status).toBe('completed')
      expect(store.getAgentState('a1')?.progress).toBe(100)
      expect(store.getAgentState('a2')?.status).toBe('completed')
    })

    it('应用指定帧时进行深拷贝，修改 store 状态不影响原始帧数据', () => {
      const store = useAgentStore()
      const frameStates: Record<string, AgentState> = {
        a1: makeState('a1', 'running', { progress: 50 })
      }
      const frames = [makeFrame(frameStates, 1000)]

      store.loadReplayData(frames)

      // 修改 store 中的状态
      store.updateAgentState('a1', { status: 'completed', progress: 100 })

      // 原始帧数据应未被修改
      expect(frames[0].agentStates.a1.status).toBe('running')
      expect(frames[0].agentStates.a1.progress).toBe(50)
    })
  })
})
