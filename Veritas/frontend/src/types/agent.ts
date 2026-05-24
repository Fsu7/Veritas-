export interface AgentState {
  name: string
  status: 'waiting' | 'running' | 'completed' | 'failed'
  progress?: number
  intermediateResult?: string
  durationMs?: number
  error?: string
}

export interface FlowData {
  nodes: FlowNode[]
  links: FlowLink[]
}

export interface FlowNode {
  name: string
  label: string
  x: number
  y: number
}

export interface FlowLink {
  source: string
  target: string
}
