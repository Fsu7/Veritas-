<script setup lang="ts">
/**
 * Agent 中间结果时间线组件
 * - el-timeline 展示 completed / running 的 Agent
 * - 时间戳（毫秒/秒/分秒）+ 中文名 + 摘要
 * - 新结果出现时自动滚动到底部（nextTick + scrollTop）
 * - 空状态：el-empty 等待 Agent 产出结果
 */
import { ref, computed, nextTick, watch } from 'vue'
import { ElEmpty, ElTimeline, ElTimelineItem, ElText } from 'element-plus'
import type { AgentState } from '@/types/agent'

const props = defineProps<{
  agentStates: Record<string, AgentState>
  /** 联动：自动滚动到指定 Agent 的节点 */
  scrollToAgent?: string
}>()

interface AgentMeta { name: string; label: string }
const AGENT_LIST: AgentMeta[] = [
  { name: 'coordinator', label: '协调者' },
  { name: 'retriever',   label: '检索员' },
  { name: 'analyzer',    label: '分析员' },
  { name: 'comparer',    label: '对比员' },
  { name: 'generator',   label: '生成员' },
  { name: 'reviewer',    label: '审核员' }
]

const MAX_SUMMARY_LENGTH = 200
const timelineRef = ref<HTMLElement | null>(null)

const visibleItems = computed(() => {
  return AGENT_LIST
    .map(agent => ({ agent, state: props.agentStates[agent.name] }))
    .filter(item => {
      const status = item.state?.status
      return (status === 'completed' || status === 'running') && item.state?.intermediateResult
    })
    .map(item => ({
      ...item,
      timestamp: formatTime(item.state?.durationMs),
      status: item.state!.status!,
      summary: truncate(item.state!.intermediateResult ?? '')
    }))
})

const isEmpty = computed(() => visibleItems.value.length === 0)

function formatTime(ms?: number): string {
  if (ms == null) return '00:00'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`
  const m = Math.floor(ms / 60_000)
  const s = Math.floor((ms % 60_000) / 1000)
  return `${m}m ${s}s`
}

function truncate(text: string): string {
  if (text.length <= MAX_SUMMARY_LENGTH) return text
  return text.slice(0, MAX_SUMMARY_LENGTH) + '...'
}

function getTimelineType(status: string): 'primary' | 'success' | 'danger' {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'danger'
  return 'primary'
}

async function scrollToBottom() {
  await nextTick()
  if (timelineRef.value) {
    timelineRef.value.scrollTop = timelineRef.value.scrollHeight
  }
}

async function scrollToAgent(agentName: string) {
  await nextTick()
  if (!timelineRef.value) return
  const el = timelineRef.value.querySelector(`[data-agent="${agentName}"]`) as HTMLElement | null
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

watch(() => visibleItems.value.length, async (newLen, oldLen) => {
  if (newLen > oldLen) {
    await scrollToBottom()
  }
})

watch(() => props.scrollToAgent, (name) => {
  if (name) scrollToAgent(name)
})
</script>

<template>
  <div ref="timelineRef" class="intermediate-result">
    <ElEmpty v-if="isEmpty" description="等待 Agent 产出结果" :image-size="80" />

    <ElTimeline v-else>
      <ElTimelineItem
        v-for="item in visibleItems"
        :key="item.agent.name"
        :timestamp="item.timestamp"
        :type="getTimelineType(item.status)"
        placement="top"
      >
        <div :data-agent="item.agent.name" class="intermediate-result__item">
          <h4 class="intermediate-result__title">
            <ElText type="primary" size="default" tag="b">{{ item.agent.label }}</ElText>
            <ElText type="info" size="small" class="intermediate-result__status">
              {{ item.status === 'completed' ? '已完成' : '执行中' }}
            </ElText>
          </h4>
          <p class="intermediate-result__summary">{{ item.summary }}</p>
        </div>
      </ElTimelineItem>
    </ElTimeline>
  </div>
</template>

<style scoped lang="scss">
.intermediate-result {
  max-height: 400px;
  overflow-y: auto;
  padding: var(--spacing-sm);

  &__item {
    padding: var(--spacing-xs) 0;
  }

  &__title {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    margin: 0 0 var(--spacing-xs);
  }

  &__status {
    font-weight: normal;
  }

  &__summary {
    margin: 0;
    padding: var(--spacing-sm);
    background-color: var(--el-fill-color-light);
    border-radius: var(--radius-sm);
    font-size: var(--font-size-sm);
    color: var(--el-text-color-regular);
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-word;
  }
}
</style>
