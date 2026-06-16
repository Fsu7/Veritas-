<script setup lang="ts">
/**
 * Agent 协同可视化页面（FM4 重构版）
 * - 组合 AgentFlowChart / AgentStatusPanel / IntermediateResult / TimeStats
 * - 使用 useSSE composable 管理 SSE 连接
 * - 数据流：SSE → onEvent → agentStore.updateAgentState → 子组件 Props
 * - 布局：上部 60% 流程图 + 下部 40% el-tabs
 * - 状态：loading(骨架屏) / empty(等待开始) / error(错误+重试)
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAgentStore } from '@/stores/agentStore'
import { useSessionStore } from '@/stores/sessionStore'
import { useSSE } from '@/composables/useSSE'
import { analysisApi } from '@/api/analysis'
import AgentFlowChart from '@/components/agent/AgentFlowChart.vue'
import AgentStatusPanel from '@/components/agent/AgentStatusPanel.vue'
import IntermediateResult from '@/components/agent/IntermediateResult.vue'
import TimeStats from '@/components/agent/TimeStats.vue'
import type { SSEEvent } from '@/types/agent'

const route = useRoute()
const router = useRouter()
const agentStore = useAgentStore()
const sessionStore = useSessionStore()

const analysisId = computed(() => route.params.analysisId as string)

/** 当前高亮选中的 Agent（流程图节点点击联动） */
const selectedAgent = ref<string>('')

/** 当前激活的下部面板 tab */
const activeTab = ref('status')

const { isConnected, error: sseError, connect, disconnect } = useSSE({
  onEvent: handleSSEEvent
})

/** 是否为首次加载中（未连接且无任何 Agent 状态） */
const isLoading = computed(() =>
  !isConnected.value && Object.keys(agentStore.agentStates).length === 0 && !sseError.value
)

/** 是否为空状态（已连接但无 Agent 状态） */
const isEmpty = computed(() =>
  isConnected.value && Object.keys(agentStore.agentStates).length === 0
)

/** 是否有错误 */
const hasError = computed(() =>
  !!sseError.value && Object.keys(agentStore.agentStates).length === 0
)

/**
 * SSE 事件处理：agent_state_update → agentStore，analysis_completed → 断开
 */
function handleSSEEvent(event: SSEEvent) {
  if (event.type === 'agent_state_update') {
    const { agentName, agent_name, status, progress, intermediateResult, intermediate_result, durationMs, duration_ms, error: err } = event.data
    const name = (agentName ?? agent_name ?? '') as string
    if (!name) return
    agentStore.updateAgentState(name, {
      status: (status ?? 'running') as 'waiting' | 'running' | 'completed' | 'failed',
      progress: progress as number | undefined,
      intermediateResult: (intermediateResult ?? intermediate_result) as string | undefined,
      durationMs: (durationMs ?? duration_ms) as number | undefined,
      error: err as string | undefined
    })
  } else if (event.type === 'analysis_completed') {
    disconnect()
  }
}

/** 流程图节点点击 → 联动面板 */
function handleNodeClick(agentName: string) {
  selectedAgent.value = agentName
  activeTab.value = 'status'
}

/** 重试 SSE 连接 */
function handleRetry() {
  if (!analysisId.value) return
  const url = analysisApi.getAgentStreamUrl(analysisId.value)
  connect(url)
}

onMounted(async () => {
  if (!analysisId.value) return

  // 尝试拉取已有分析结果（幂等）
  try {
    await sessionStore.fetchAnalysisResult(analysisId.value)
  } catch {
    // 拉取失败不影响 SSE 连接
  }

  const url = analysisApi.getAgentStreamUrl(analysisId.value)
  connect(url)
})

onUnmounted(() => {
  disconnect()
  agentStore.resetStates()
})
</script>

<template>
  <div class="agent-flow-view">
    <!-- 顶部导航 -->
    <div class="agent-flow-view__header">
      <el-page-header @back="router.back()" title="返回">
        <template #content>
          <span class="agent-flow-view__title">Agent 协同过程</span>
        </template>
        <template #extra>
          <el-tag v-if="isConnected" type="success" size="small" effect="plain">
            <span class="agent-flow-view__status-dot agent-flow-view__status-dot--connected" />
            已连接
          </el-tag>
          <el-tag v-else-if="isLoading" type="info" size="small" effect="plain">
            <span class="agent-flow-view__status-dot agent-flow-view__status-dot--loading" />
            连接中...
          </el-tag>
          <el-tag v-else-if="hasError" type="danger" size="small" effect="plain">
            连接失败
          </el-tag>
          <el-tag v-else type="warning" size="small" effect="plain">
            未连接
          </el-tag>
        </template>
      </el-page-header>
    </div>

    <!-- Loading 状态 -->
    <div v-if="isLoading" class="agent-flow-view__loading">
      <el-skeleton :rows="3" animated />
      <el-skeleton :rows="5" animated style="margin-top: 16px" />
      <p class="agent-flow-view__loading-text">正在连接 Agent 服务...</p>
    </div>

    <!-- Error 状态 -->
    <div v-else-if="hasError" class="agent-flow-view__error">
      <el-result
        icon="error"
        title="连接失败"
        :sub-title="sseError ?? '无法连接到 Agent 服务'"
      >
        <template #extra>
          <el-button type="primary" @click="handleRetry">重试</el-button>
        </template>
      </el-result>
    </div>

    <!-- Empty 状态 -->
    <div v-else-if="isEmpty" class="agent-flow-view__empty">
      <el-empty description="等待开始分析" />
    </div>

    <!-- 正常内容 -->
    <template v-else>
      <!-- 上部 60%：流程图 -->
      <div class="agent-flow-view__chart-section">
        <AgentFlowChart
          :agent-states="agentStore.agentStates"
          @node-click="handleNodeClick"
        />
      </div>

      <!-- 下部 40%：Tab 切换面板 -->
      <div class="agent-flow-view__panel-section">
        <el-card shadow="hover" class="agent-flow-view__panel-card">
          <el-tabs v-model="activeTab" class="agent-flow-view__tabs">
            <el-tab-pane label="状态面板" name="status">
              <AgentStatusPanel
                :agent-states="agentStore.agentStates"
                :highlight-agent="selectedAgent"
                @agent-click="handleNodeClick"
              />
            </el-tab-pane>
            <el-tab-pane label="中间结果" name="intermediate">
              <IntermediateResult
                :agent-states="agentStore.agentStates"
                :scroll-to-agent="selectedAgent"
              />
            </el-tab-pane>
            <el-tab-pane label="耗时统计" name="time">
              <TimeStats :agent-states="agentStore.agentStates" />
            </el-tab-pane>
          </el-tabs>

          <!-- 底部连接信息 -->
          <div class="agent-flow-view__connection-info">
            <el-text type="info" size="small">
              SSE 状态：
              <el-tag :type="isConnected ? 'success' : 'warning'" size="small" effect="plain">
                {{ isConnected ? '已连接' : '未连接' }}
              </el-tag>
            </el-text>
            <el-button
              v-if="!isConnected && !hasError"
              type="primary"
              size="small"
              text
              @click="handleRetry"
            >
              重新连接
            </el-button>
          </div>
        </el-card>
      </div>
    </template>
  </div>
</template>

<style scoped lang="scss">
.agent-flow-view {
  max-width: var(--content-max-width, 1200px);
  margin: 0 auto;
  padding: var(--spacing-lg, 24px);
  height: calc(100vh - 64px);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md, 16px);
}

.agent-flow-view__header {
  flex-shrink: 0;
}

.agent-flow-view__title {
  font-weight: 600;
}

/* 连接状态指示点 */
.agent-flow-view__status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 4px;
  vertical-align: middle;

  &--connected {
    background-color: var(--el-color-success);
    animation: status-pulse 2s infinite;
  }

  &--loading {
    background-color: var(--el-color-primary);
    animation: status-pulse 1s infinite;
  }
}

@keyframes status-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* Loading */
.agent-flow-view__loading {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: var(--spacing-xl, 32px);
}

.agent-flow-view__loading-text {
  text-align: center;
  color: var(--el-text-color-secondary);
  margin-top: var(--spacing-lg, 24px);
  font-size: var(--font-size-base, 14px);
}

/* Error */
.agent-flow-view__error {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Empty */
.agent-flow-view__empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 流程图区域 - flex: 6 = 60% */
.agent-flow-view__chart-section {
  flex: 6;
  min-height: 300px;
  overflow: hidden;
  border-radius: var(--radius-md, 8px);
  border: 1px solid var(--el-border-color-light);
  background-color: var(--el-bg-color);
}

/* 面板区域 - flex: 4 = 40% */
.agent-flow-view__panel-section {
  flex: 4;
  min-height: 200px;
  display: flex;
  flex-direction: column;
}

.agent-flow-view__panel-card {
  flex: 1;
  display: flex;
  flex-direction: column;

  :deep(.el-card__body) {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: var(--spacing-md, 16px);
    overflow: hidden;
  }
}

.agent-flow-view__tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  :deep(.el-tabs__content) {
    flex: 1;
    overflow-y: auto;
  }
}

.agent-flow-view__connection-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: var(--spacing-sm, 8px);
  border-top: 1px solid var(--el-border-color-lighter);
  flex-shrink: 0;
}
</style>
