import type { AgentState } from './agent'

/**
 * 分析结果实体
 * JSON字段映射: analysisId ↔ analysis_id, degradedReason ↔ degraded_reason
 */
export interface AnalysisResult {
  analysisId: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  type: 'paper_analysis' | 'compare' | 'report'
  result?: {
    report?: string
    citations?: Citation[]
    analysis?: StructuredAnalysis
    comparison?: CompareResult
  }
  agentStates?: AgentState[]
  degraded?: boolean
  degradedReason?: string
}

/**
 * 5维度结构化分析
 * JSON字段映射: researchQuestion ↔ research_question, coreMethod ↔ core_method,
 * keyExperiments ↔ key_experiments, coreFindings ↔ core_findings,
 * plainExplanation ↔ plain_explanation
 */
export interface StructuredAnalysis {
  researchQuestion: string
  coreMethod: string
  keyExperiments: string
  coreFindings: string
  limitations: string
  plainExplanation?: string
}

/**
 * 对比结果含矛盾发现
 */
export interface CompareResult {
  table: CompareRow[]
  summary: string
  conflicts: Conflict[]
}

/**
 * 对比表格行
 */
export interface CompareRow {
  dimension: string
  values: string[]
}

/**
 * 引用信息
 * JSON字段映射: paperId ↔ paper_id
 */
export interface Citation {
  paperId: string
  text: string
  location: string
}

/**
 * 矛盾发现
 * JSON字段映射: possibleReason ↔ possible_reason
 */
export interface Conflict {
  description: string
  possibleReason: string
  papers: string[]
}
