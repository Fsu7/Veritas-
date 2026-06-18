import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AgentState, FlowData, ReplayFrame } from '@/types/agent'

export const useAgentStore = defineStore('agent', () => {
  const agentStates = ref<Record<string, AgentState>>({})
  const flowData = ref<FlowData | null>(null)
  const isConnected = ref(false)
  const currentAnalysisId = ref<string | null>(null)

  // 回放模式状态
  const replayFrames = ref<ReplayFrame[]>([])
  const isReplayMode = ref(false)
  const currentReplayIndex = ref(0)

  const agentStatesList = computed(() =>
    Object.values(agentStates.value)
  )

  const activeAgents = computed(() =>
    agentStatesList.value.filter(s => s.status === 'running')
  )

  const progress = computed(() => {
    const total = agentStatesList.value.length
    const completed = agentStatesList.value.filter(s => s.status === 'completed').length
    return total > 0 ? completed / total : 0
  })

  function getAgentState(agentName: string): AgentState | undefined {
    return agentStates.value[agentName]
  }

  function updateAgentState(agentName: string, state: Partial<AgentState>) {
    agentStates.value[agentName] = {
      ...agentStates.value[agentName],
      name: agentName,
      ...state
    }
  }

  function resetStates() {
    agentStates.value = {}
    flowData.value = null
    currentAnalysisId.value = null
  }

  /**
   * 加载回放数据，进入回放模式
   * @param frames 回放帧数组
   */
  function loadReplayData(frames: ReplayFrame[]) {
    replayFrames.value = frames
    isReplayMode.value = true
    currentReplayIndex.value = 0
    // 应用第一帧
    if (frames.length > 0) {
      applyReplayFrame(0)
    }
  }

  /**
   * 退出回放模式，清空回放数据
   */
  function exitReplayMode() {
    replayFrames.value = []
    isReplayMode.value = false
    currentReplayIndex.value = 0
  }

  /**
   * 应用指定索引的回放帧到 agentStates
   * @param index 帧索引
   */
  function applyReplayFrame(index: number) {
    const frame = replayFrames.value[index]
    if (!frame) return
    currentReplayIndex.value = index
    // 深拷贝快照到 agentStates，避免引用同一对象
    agentStates.value = JSON.parse(JSON.stringify(frame.agentStates))
  }

  return {
    agentStates, flowData, isConnected, currentAnalysisId,
    replayFrames, isReplayMode, currentReplayIndex,
    agentStatesList, activeAgents, progress,
    getAgentState, updateAgentState, resetStates,
    loadReplayData, exitReplayMode, applyReplayFrame
  }
})
