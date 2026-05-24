import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AgentState, FlowData } from '@/types/agent'

export const useAgentStore = defineStore('agent', () => {
  const agentStates = ref<Record<string, AgentState>>({})
  const flowData = ref<FlowData | null>(null)
  const isConnected = ref(false)
  const currentAnalysisId = ref<string | null>(null)

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

  return {
    agentStates, flowData, isConnected, currentAnalysisId,
    agentStatesList, activeAgents, progress,
    getAgentState, updateAgentState, resetStates
  }
})
