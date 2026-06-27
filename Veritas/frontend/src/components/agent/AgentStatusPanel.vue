<script setup lang="ts">
/**
 * Agent 状态面板组件
 * - 6 个 Agent 状态标签（名称+图标+文字+耗时+状态色）
 * - 顶部进度条（已完成 / 6）
 * - 状态色+图标+文字三重传达（无障碍）
 * - 响应式：lg 横排 / sm 2×3 网格
 * - 点击标签展示中间结果（el-popover）+ emit agent-click
 * - 空状态：el-empty 等待开始分析
 */
import { computed } from 'vue'
import { Clock, Loading, Check, Close } from '@element-plus/icons-vue'
import { ElEmpty, ElProgress, ElPopover, ElTag, ElRow, ElCol } from 'element-plus'
import { AGENT_STATUS_COLORS } from '@/constants/agent'
import type { AgentState } from '@/types/agent'
import { formatDuration } from '@/utils/format'

const props = defineProps<{
  agentStates: Record<string, AgentState>
  /** 外部联动高亮的 Agent 名称 */
  highlightAgent?: string
}>()

const emit = defineEmits<{
  (e: 'agent-click', agentName: string): void
}>()

interface AgentMeta { name: string; label: string; description: string }

const AGENT_LIST: AgentMeta[] = [
  { name: 'coordinator', label: '协调者', description: '协调各 Agent 协同工作' },
  { name: 'retriever',   label: '检索员', description: '检索相关论文' },
  { name: 'analyzer',    label: '分析员', description: '深度分析论文内容' },
  { name: 'comparer',    label: '对比员', description: '多论文对比分析' },
  { name: 'generator',   label: '生成员', description: '生成综述内容' },
  { name: 'reviewer',    label: '审核员', description: '审核并反馈综述质量' }
]

/** 状态色（对应 --agent-*，统一引用 @/constants/agent） */
const STATUS_COLORS: Record<string, string> = AGENT_STATUS_COLORS

const STATUS_LABELS: Record<string, string> = {
  waiting:   '等待中',
  running:   '执行中',
  completed: '已完成',
  failed:    '失败'
}

const STATUS_ICONS: Record<string, unknown> = {
  waiting:   Clock,
  running:   Loading,
  completed: Check,
  failed:    Close
}

const isEmpty = computed(() => Object.keys(props.agentStates).length === 0)

const completedCount = computed(() =>
  Object.values(props.agentStates).filter(s => s.status === 'completed').length
)

const totalCount = computed(() => Object.keys(props.agentStates).length)

const progressPercent = computed(() => {
  if (totalCount.value === 0) return 0
  return Math.round((completedCount.value / 6) * 100)
})

function getStatus(name: string): string {
  return props.agentStates[name]?.status ?? 'waiting'
}

function getColor(name: string): string {
  return STATUS_COLORS[getStatus(name)] ?? STATUS_COLORS.waiting
}

function getLabel(name: string): string {
  const status = getStatus(name)
  return STATUS_LABELS[status] ?? status
}

function getIcon(name: string) {
  return STATUS_ICONS[getStatus(name)] ?? Clock
}

function handleClick(name: string) {
  emit('agent-click', name)
}
</script>

<template>
  <div class="agent-status-panel">
    <div class="agent-status-panel__header">
      <ElProgress
        :percentage="progressPercent"
        :status="progressPercent === 100 ? 'success' : ''"
        :stroke-width="14"
        text-inside
      />
      <span class="agent-status-panel__counter">
        已完成 <b>{{ completedCount }}</b> / 6
      </span>
    </div>

    <ElEmpty v-if="isEmpty" description="等待开始分析" :image-size="80" />

    <ElRow v-else :gutter="12" class="agent-status-panel__grid">
      <ElCol
        v-for="agent in AGENT_LIST"
        :key="agent.name"
        :xs="12"
        :sm="12"
        :md="8"
        :lg="4"
        class="agent-status-panel__col"
      >
        <div
          class="agent-status-panel__item"
          :class="{
            'is-running': getStatus(agent.name) === 'running',
            'is-highlight': highlightAgent === agent.name
          }"
          :style="{ borderColor: getColor(agent.name) }"
          @click="handleClick(agent.name)"
        >
          <div class="agent-status-panel__item-header">
            <ElTag
              :color="getColor(agent.name)"
              effect="dark"
              size="small"
              class="agent-status-panel__status-tag"
            >
              <el-icon class="agent-status-panel__status-icon" :class="{ 'is-spin': getStatus(agent.name) === 'running' }">
                <component :is="getIcon(agent.name)" />
              </el-icon>
              <span class="agent-status-panel__status-text">{{ getLabel(agent.name) }}</span>
            </ElTag>
          </div>

          <h4 class="agent-status-panel__name">{{ agent.label }}</h4>
          <p class="agent-status-panel__description">{{ agent.description }}</p>

          <div class="agent-status-panel__meta">
            <span v-if="getStatus(agent.name) === 'running' || getStatus(agent.name) === 'completed' || getStatus(agent.name) === 'failed'">
              耗时：{{ formatDuration(props.agentStates[agent.name]?.durationMs) }}
            </span>
            <span v-else>耗时：-</span>
          </div>

          <ElPopover
            v-if="props.agentStates[agent.name]?.intermediateResult"
            placement="top"
            :width="320"
            trigger="hover"
            :show-after="200"
          >
            <template #reference>
              <span class="agent-status-panel__result-hint" @click.stop>查看中间结果</span>
            </template>
            <pre class="agent-status-panel__result">{{ props.agentStates[agent.name]?.intermediateResult }}</pre>
          </ElPopover>
        </div>
      </ElCol>
    </ElRow>
  </div>
</template>

<style scoped lang="scss">
.agent-status-panel {
  width: 100%;

  &__header {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-md);
  }

  &__counter {
    color: var(--el-color-info);
    font-size: var(--font-size-sm);
    flex-shrink: 0;
  }

  &__grid {
    margin: 0 !important;
  }

  &__col {
    margin-bottom: var(--spacing-sm);
  }

  &__item {
    border: 2px solid;
    border-radius: var(--radius-md);
    padding: var(--spacing-sm) var(--spacing-md);
    background-color: var(--el-bg-color);
    cursor: pointer;
    transition: all var(--transition-fast);
    height: 100%;

    &:hover {
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
    }

    &.is-running {
      animation: agent-pulse 1.5s ease-in-out infinite;
    }

    &.is-highlight {
      box-shadow: 0 0 0 3px var(--el-color-primary-light-5);
    }
  }

  &__item-header {
    display: flex;
    justify-content: flex-end;
    margin-bottom: var(--spacing-xs);
  }

  &__status-tag {
    border: none;
  }

  &__status-icon {
    margin-right: 2px;
    vertical-align: middle;

    &.is-spin {
      animation: agent-spin 1.2s linear infinite;
    }
  }

  &__status-text {
    vertical-align: middle;
    color: #ffffff;
    font-weight: 500;
  }

  &__name {
    font-size: var(--font-size-base);
    font-weight: 600;
    color: var(--el-text-color-primary);
    margin: 0 0 var(--spacing-xs);
  }

  &__description {
    font-size: var(--font-size-sm);
    color: var(--el-color-info);
    margin: 0 0 var(--spacing-xs);
    line-height: 1.4;
  }

  &__meta {
    font-size: var(--font-size-sm);
    color: var(--el-color-info);
  }

  &__result-hint {
    display: inline-block;
    margin-top: var(--spacing-xs);
    color: var(--el-color-primary);
    font-size: var(--font-size-sm);
    cursor: pointer;

    &:hover {
      text-decoration: underline;
    }
  }

  &__result {
    margin: 0;
    padding: var(--spacing-sm);
    background-color: var(--el-fill-color-light);
    border-radius: var(--radius-sm);
    font-size: var(--font-size-sm);
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 200px;
    overflow-y: auto;
  }
}

@keyframes agent-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(64, 158, 255, 0.4); }
  50%      { box-shadow: 0 0 0 8px rgba(64, 158, 255, 0); }
}

@keyframes agent-spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
</style>
