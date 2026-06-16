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

/**
 * SSE 事件类型
 */
export type SSEEventType =
  | 'agent_state_update'
  | 'analysis_completed'
  | 'agent_error'
  | 'progress_update'

/**
 * SSE 事件载荷
 * 字段命名遵循 TS camelCase；data 内部字段由事件类型决定
 */
export interface SSEEvent {
  type: SSEEventType
  data: Record<string, unknown>
  timestamp: number
}
