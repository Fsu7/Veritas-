/**
 * Agent执行状态
 * JSON字段映射: intermediateResult ↔ intermediate_result, durationMs ↔ duration_ms
 */
export interface AgentState {
  name: string
  status: 'waiting' | 'running' | 'completed' | 'failed'
  progress?: number
  intermediateResult?: string
  durationMs?: number
  error?: string
}

/**
 * ECharts流程图数据
 */
export interface FlowData {
  nodes: FlowNode[]
  links: FlowLink[]
}

/**
 * 流程图节点
 */
export interface FlowNode {
  name: string
  label: string
  x: number
  y: number
}

/**
 * 流程图连线
 */
export interface FlowLink {
  source: string
  target: string
}
