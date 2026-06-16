<script setup lang="ts">
/**
 * Agent 耗时统计柱状图组件（ECharts Bar）
 * - X 轴：Agent 中文名
 * - Y 轴：耗时（秒）
 * - 柱体颜色与 Agent 状态色一致
 * - 进行中：部分柱 + 提示「分析进行中」
 * - 全部完成：完整柱状图
 * - resize 自适应；卸载释放实例
 */
import { ref, computed, watch, onMounted, onUnmounted, markRaw } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart } from 'echarts/charts'
import {
  TooltipComponent,
  GridComponent,
  TitleComponent,
  LegendComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { ElEmpty, ElText } from 'element-plus'
import type { AgentState } from '@/types/agent'

echarts.use([
  BarChart,
  TooltipComponent,
  GridComponent,
  TitleComponent,
  LegendComponent,
  CanvasRenderer
])

const props = defineProps<{
  agentStates: Record<string, AgentState>
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

const STATUS_COLORS: Record<string, string> = {
  waiting:   '#C0C4CC',
  running:   '#409EFF',
  completed: '#67C23A',
  failed:    '#F56C6C'
}

const chartContainer = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null
const handleWindowResize = () => chart?.resize()

const totalCount = computed(() => Object.keys(props.agentStates).length)
const finishedCount = computed(() =>
  Object.values(props.agentStates).filter(s => s.status === 'completed' || s.status === 'failed').length
)
const isInProgress = computed(() => totalCount.value > 0 && finishedCount.value < totalCount.value)
const hasAnyData = computed(() => totalCount.value > 0)

const chartOption = computed(() => {
  const labels = AGENT_LIST.map(a => a.label)
  const durations = AGENT_LIST.map(a => {
    const ms = props.agentStates[a.name]?.durationMs
    if (ms == null) return 0
    return Number((ms / 1000).toFixed(2))
  })
  const colors = AGENT_LIST.map(a => STATUS_COLORS[props.agentStates[a.name]?.status ?? 'waiting'] ?? STATUS_COLORS.waiting)
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: Array<{ name: string; value: number; dataIndex: number }>) => {
        const p = params[0]
        const agent = AGENT_LIST[p.dataIndex]
        const status = props.agentStates[agent.name]?.status ?? 'waiting'
        return `Agent: <b>${agent.label}</b><br/>状态: ${status}<br/>耗时: ${p.value}s`
      }
    },
    grid: {
      left: 40,
      right: 20,
      top: 30,
      bottom: 40
    },
    xAxis: {
      type: 'category',
      data: labels,
      axisLabel: { color: '#909399', fontSize: 12 }
    },
    yAxis: {
      type: 'value',
      name: '耗时 (秒)',
      nameTextStyle: { color: '#909399' },
      axisLabel: { color: '#909399' }
    },
    series: [
      {
        type: 'bar',
        data: colors.map((c, i) => ({
          value: durations[i],
          itemStyle: {
            color: c,
            borderRadius: [4, 4, 0, 0]
          }
        })),
        barMaxWidth: 50,
        label: {
          show: true,
          position: 'top',
          color: '#606266',
          fontSize: 12,
          formatter: (params: { value: number }) => params.value > 0 ? `${params.value}s` : ''
        }
      }
    ]
  }
})

function refreshChart() {
  if (!chart) return
  chart.setOption(chartOption.value, { notMerge: true })
}

function initChart() {
  if (!chartContainer.value) return
  chart = markRaw(echarts.init(chartContainer.value, undefined, { renderer: 'canvas' }))
  chart.setOption(chartOption.value)
  window.addEventListener('resize', handleWindowResize)
  if (typeof ResizeObserver !== 'undefined' && chartContainer.value) {
    resizeObserver = new ResizeObserver(() => chart?.resize())
    resizeObserver.observe(chartContainer.value)
  }
}

function disposeChart() {
  window.removeEventListener('resize', handleWindowResize)
  resizeObserver?.disconnect()
  resizeObserver = null
  if (chart) {
    chart.dispose()
    chart = null
  }
}

watch(() => props.agentStates, refreshChart, { deep: true })

onMounted(initChart)
onUnmounted(disposeChart)
</script>

<template>
  <div class="time-stats">
    <div v-if="isInProgress" class="time-stats__hint">
      <ElText type="warning" size="small">分析进行中...（已展示 {{ finishedCount }} / {{ totalCount }} 个 Agent）</ElText>
    </div>
    <ElEmpty v-if="!hasAnyData" description="暂无耗时数据" :image-size="80" />
    <div v-else ref="chartContainer" class="time-stats__chart" />
  </div>
</template>

<style scoped lang="scss">
.time-stats {
  width: 100%;

  &__hint {
    margin-bottom: var(--spacing-sm);
  }

  &__chart {
    width: 100%;
    height: 400px;
  }
}
</style>
