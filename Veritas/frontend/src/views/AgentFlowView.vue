<script setup lang="ts">
/**
 * Agent 协同可视化页面（FM4 重构版 + FM5 回放模式）
 * - 组合 AgentFlowChart / AgentStatusPanel / IntermediateResult / TimeStats
 * - 使用 useSSE composable 管理 SSE 连接
 * - 数据流：SSE → onEvent → agentStore.updateAgentState → 子组件 Props
 * - 布局：上部 60% 流程图 + 下部 40% el-tabs
 * - 状态：loading(骨架屏) / empty(等待开始) / error(错误+重试)
 * - FM5 新增：回放模式（useReplay composable + 回放控制条）
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { VideoPlay, VideoPause, RefreshLeft, DArrowLeft, DArrowRight } from '@element-plus/icons-vue'

import { useAgentStore } from '@/stores/agentStore'
import { useSessionStore } from '@/stores/sessionStore'
import { useUserStore } from '@/stores/userStore'
import { useSSE } from '@/composables/useSSE'
import { useReplay, type PlaybackSpeed } from '@/composables/useReplay'
import { analysisApi } from '@/api/analysis'
import AgentFlowChart from '@/components/agent/AgentFlowChart.vue'
import AgentStatusPanel from '@/components/agent/AgentStatusPanel.vue'
import IntermediateResult from '@/components/agent/IntermediateResult.vue'
import TimeStats from '@/components/agent/TimeStats.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import type { SSEEvent, ReplayFrame, AgentState } from '@/types/agent'

const route = useRoute()
const router = useRouter()
const agentStore = useAgentStore()
const sessionStore = useSessionStore()
const userStore = useUserStore()

const analysisId = computed(() => route.params.analysisId as string)

/** 当前高亮选中的 Agent（流程图节点点击联动） */
const selectedAgent = ref<string>('')

/** 当前激活的下部面板 tab */
const activeTab = ref('status')

/** 回放模式状态 */
const hasReplayData = ref(false)
const replayLoading = ref(false)

const { isConnected, error: sseError, connect, disconnect } = useSSE({
  onEvent: handleSSEEvent
})

const {
  isPlaying,
  currentIndex,
  playbackSpeed,
  progress,
  totalFrames,
  play,
  pause,
  reset,
  seek,
  stepForward,
  stepBackward,
  setSpeed,
  loadFrames,
  clear: clearReplay
} = useReplay({
  onFrameChange: (_frame, index) => {
    agentStore.applyReplayFrame(index)
  },
  onComplete: () => {
    ElMessage.info('回放已结束')
  }
})

/** 是否为首次加载中（未连接且无任何 Agent 状态） */
const isLoading = computed(() =>
  !agentStore.isReplayMode &&
  !isConnected.value &&
  Object.keys(agentStore.agentStates).length === 0 &&
  !sseError.value
)

/** 是否为空状态（已连接但无 Agent 状态） */
const isEmpty = computed(() =>
  !agentStore.isReplayMode &&
  isConnected.value &&
  Object.keys(agentStore.agentStates).length === 0
)

/** 是否有错误 */
const hasError = computed(() =>
  !agentStore.isReplayMode &&
  !!sseError.value &&
  Object.keys(agentStore.agentStates).length === 0
)

const speedOptions: { label: string; value: PlaybackSpeed }[] = [
  { label: '0.5x', value: 0.5 },
  { label: '1x', value: 1 },
  { label: '2x', value: 2 },
  { label: '4x', value: 4 }
]

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
  const url = analysisApi.getAgentStreamUrl(analysisId.value, userStore.token)
  connect(url)
}

/** 进入回放模式 */
async function handleEnterReplay() {
  if (!analysisId.value) return
  replayLoading.value = true
  try {
    // 从后端拉取历史 Agent 事件（若后端不支持则使用当前快照构造单帧）
    const result = await sessionStore.fetchAnalysisResult(analysisId.value)
    const frames = buildReplayFramesFromResult(result)
    if (frames.length === 0) {
      ElMessage.warning('暂无历史回放数据')
      return
    }
    // 断开实时 SSE
    disconnect()
    agentStore.loadReplayData(frames)
    loadFrames(frames)
    hasReplayData.value = true
    ElMessage.success(`已加载 ${frames.length} 帧回放数据`)
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '加载回放数据失败'
    ElMessage.error(msg)
  } finally {
    replayLoading.value = false
  }
}

/** 退出回放模式 */
function handleExitReplay() {
  pause()
  clearReplay()
  agentStore.exitReplayMode()
  agentStore.resetStates()
  hasReplayData.value = false
  // 重新连接实时 SSE
  if (analysisId.value) {
    const url = analysisApi.getAgentStreamUrl(analysisId.value, userStore.token)
    connect(url)
  }
}

/** 处理进度条拖动 */
function handleProgressChange(value: number | number[]) {
  const v = Array.isArray(value) ? value[0] : value
  seek(v)
}

/** 处理速度切换 */
function handleSpeedChange(value: string | number | boolean | undefined) {
  setSpeed(Number(value) as PlaybackSpeed)
}

/**
 * 从分析结果构造回放帧
 * 若后端返回 agentStates 数组，则按顺序构造帧；否则使用当前快照构造单帧
 */
function buildReplayFramesFromResult(result: { agentStates?: AgentState[] }): ReplayFrame[] {
  const states = result.agentStates
  if (!states || states.length === 0) {
    // 若当前 agentStore 已有状态，构造单帧
    if (Object.keys(agentStore.agentStates).length > 0) {
      return [{
        timestamp: Date.now(),
        agentStates: JSON.parse(JSON.stringify(agentStore.agentStates)),
        event: {
          type: 'analysis_completed',
          data: {},
          timestamp: Date.now()
        }
      }]
    }
    return []
  }
  // 按 Agent 状态变化构造帧（每个 Agent 完成一个帧）
  const frames: ReplayFrame[] = []
  const snapshot: Record<string, AgentState> = {}
  for (let i = 0; i < states.length; i++) {
    const s = states[i]
    snapshot[s.name] = s
    frames.push({
      timestamp: Date.now() + i * 1000,
      agentStates: JSON.parse(JSON.stringify(snapshot)),
      event: {
        type: 'agent_state_update',
        data: { agentName: s.name, status: s.status },
        timestamp: Date.now() + i * 1000
      }
    })
  }
  return frames
}

onMounted(async () => {
  if (!analysisId.value) return

  // 尝试拉取已有分析结果（幂等）
  try {
    await sessionStore.fetchAnalysisResult(analysisId.value)
  } catch {
    // 拉取失败不影响 SSE 连接
  }

  const url = analysisApi.getAgentStreamUrl(analysisId.value, userStore.token)
  connect(url)
})

onUnmounted(() => {
  disconnect()
  agentStore.resetStates()
  agentStore.exitReplayMode()
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
          <!-- 回放模式标识 -->
          <el-tag v-if="agentStore.isReplayMode" type="warning" size="small" effect="dark">
            回放模式
          </el-tag>
          <template v-else>
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
        </template>
      </el-page-header>
    </div>

    <!-- 回放控制条 -->
    <div v-if="agentStore.isReplayMode" class="agent-flow-view__replay-bar">
      <el-button-group>
        <el-button :icon="VideoPlay" @click="play" :disabled="isPlaying" size="small" />
        <el-button :icon="VideoPause" @click="pause" :disabled="!isPlaying" size="small" />
        <el-button :icon="DArrowLeft" @click="stepBackward" :disabled="currentIndex === 0" size="small" />
        <el-button :icon="DArrowRight" @click="stepForward" :disabled="currentIndex >= totalFrames - 1" size="small" />
        <el-button :icon="RefreshLeft" @click="reset" size="small" />
      </el-button-group>
      <el-slider
        :model-value="currentIndex"
        :min="0"
        :max="Math.max(totalFrames - 1, 0)"
        :step="1"
        :show-tooltip="false"
        class="agent-flow-view__replay-progress"
        @change="handleProgressChange"
      />
      <el-select
        :model-value="playbackSpeed"
        size="small"
        class="agent-flow-view__replay-speed"
        @change="handleSpeedChange"
      >
        <el-option
          v-for="opt in speedOptions"
          :key="opt.value"
          :label="opt.label"
          :value="opt.value"
        />
      </el-select>
      <el-text type="info" size="small" class="agent-flow-view__replay-info">
        {{ currentIndex + 1 }} / {{ totalFrames }}
      </el-text>
      <el-button type="danger" size="small" @click="handleExitReplay">
        退出回放
      </el-button>
    </div>

    <!-- 非回放模式：进入回放按钮 -->
    <div v-else-if="!isLoading && !hasError" class="agent-flow-view__replay-entry">
      <el-button
        type="warning"
        size="small"
        :loading="replayLoading"
        @click="handleEnterReplay"
      >
        进入回放模式
      </el-button>
    </div>

    <!-- Loading 状态 -->
    <div v-if="isLoading" class="agent-flow-view__loading">
      <el-skeleton :rows="3" animated />
      <el-skeleton :rows="5" animated style="margin-top: 16px" />
      <p class="agent-flow-view__loading-text">正在连接 Agent 服务...</p>
    </div>

    <!-- Error 状态 -->
    <div v-else-if="hasError" class="agent-flow-view__error">
      <ErrorState
        title="连接失败"
        :description="sseError ?? '无法连接到 Agent 服务'"
        @retry="handleRetry"
      />
    </div>

    <!-- Empty 状态 -->
    <div v-else-if="isEmpty" class="agent-flow-view__empty">
      <EmptyState
        icon="box"
        title="等待开始分析"
        description="Agent 服务已连接，等待分析任务启动"
      />
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
              <template v-if="agentStore.isReplayMode">
                回放进度：{{ progress }}%
              </template>
              <template v-else>
                SSE 状态：
                <el-tag :type="isConnected ? 'success' : 'warning'" size="small" effect="plain">
                  {{ isConnected ? '已连接' : '未连接' }}
                </el-tag>
              </template>
            </el-text>
            <el-button
              v-if="!agentStore.isReplayMode && !isConnected && !hasError"
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
@use '@/styles/mixins' as *;

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

/* 回放控制条 */
.agent-flow-view__replay-bar {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm, 8px);
  padding: var(--spacing-sm, 8px) var(--spacing-md, 16px);
  background: var(--el-fill-color-light, #f5f7fa);
  border-radius: var(--radius-md, 8px);
  flex-shrink: 0;
  flex-wrap: wrap;
}

.agent-flow-view__replay-progress {
  flex: 1;
  min-width: 200px;
  margin: 0 var(--spacing-sm, 8px);
}

.agent-flow-view__replay-speed {
  width: 90px;
}

.agent-flow-view__replay-info {
  white-space: nowrap;
  min-width: 60px;
}

.agent-flow-view__replay-entry {
  display: flex;
  justify-content: flex-end;
  padding: 0 var(--spacing-sm, 8px);
  flex-shrink: 0;
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

/* Task 50: 移动端响应式 */
@include respond-to(md) {
  .agent-flow-view {
    height: auto;
    min-height: calc(100vh - 64px);
    padding: var(--spacing-md);
  }

  .agent-flow-view__chart-section {
    flex: none;
    height: var(--chart-height-sm);
    min-height: var(--chart-height-sm);
  }

  .agent-flow-view__panel-section {
    flex: none;
    min-height: 300px;
  }

  .agent-flow-view__replay-bar {
    flex-wrap: wrap;
    gap: var(--spacing-xs);
  }

  .agent-flow-view__replay-progress {
    min-width: 100%;
    margin: 0;
  }
}
</style>
