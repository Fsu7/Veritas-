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
  agentStates?: AgentStateInfo[]
  degraded?: boolean
  degradedReason?: string
}

export interface StructuredAnalysis {
  researchQuestion: string
  coreMethod: string
  keyExperiments: string
  coreFindings: string
  limitations: string
  plainExplanation?: string
}

export interface CompareResult {
  table: CompareRow[]
  summary: string
  conflicts: Conflict[]
}

export interface CompareRow {
  dimension: string
  values: string[]
}

export interface Citation {
  paperId: string
  text: string
  location: string
}

export interface Conflict {
  description: string
  possibleReason: string
  papers: string[]
}

export interface AgentStateInfo {
  name: string
  status: string
  durationMs?: number
}
