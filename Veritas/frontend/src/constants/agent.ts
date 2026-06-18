/**
 * Agent 状态色常量（与 styles/variables.scss 中 --agent-* 一一对应）
 * ECharts 配置中无法读取 CSS 变量，使用 hex 值并在源码注释对照
 */
export const AGENT_STATUS_COLORS = {
  waiting:   '#C0C4CC', // --agent-waiting
  running:   '#409EFF', // --agent-running
  completed: '#67C23A', // --agent-completed
  failed:    '#F56C6C'  // --agent-failed
} as const

export type AgentStatus = keyof typeof AGENT_STATUS_COLORS
