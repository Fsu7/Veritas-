import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { AnalysisResult } from '@/types/analysis'

export const useSessionStore = defineStore('session', () => {
  const currentSessionId = ref<string | null>(null)
  const currentAnalysisId = ref<string | null>(null)
  const analysisResults = ref<Map<string, AnalysisResult>>(new Map())

  async function createSession(_topic: string) {
    // TODO: 调用API创建会话
  }

  async function fetchAnalysisResult(_analysisId: string) {
    // TODO: 调用API获取分析结果
  }

  return {
    currentSessionId, currentAnalysisId, analysisResults,
    createSession, fetchAnalysisResult
  }
})
