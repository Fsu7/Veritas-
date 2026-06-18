<script setup lang="ts">
/**
 * Agent 协同流程图组件（ECharts Graph）
 * - 6 节点固定坐标布局（协调者/检索员/分析员/对比员/生成员/审核员）
 * - 6 条连线（含条件分支：analyzer → comparer / generator）
 * - 状态色随 agentStates 实时变化
 * - running 节点叠加 EffectScatter + 脉冲动画
 * - tooltip 显示名称/状态/进度/耗时/中间结果
 * - resize 自适应
 * - 点击节点 emit node-click
 * - 卸载释放 ECharts 实例 + resize 监听
 */
import { ref, computed, watch, onMounted, onUnmounted, markRaw } from 'vue'
import * as echarts from 'echarts/core'
import { GraphChart, EffectScatterChart } from 'echarts/charts'
import { AGENT_STATUS_COLORS } from '@/constants/agent'
import {
  TooltipComponent,
  TitleComponent,
  LegendComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { AgentState } from '@/types/agent'

echarts.use([
  GraphChart,
  EffectScatterChart,
  TooltipComponent,
  TitleComponent,
  LegendComponent,
  CanvasRenderer
])

const props = defineProps<{
  agentStates: Record<string, AgentState>
}>()

const emit = defineEmits<{
  (e: 'node-click', agentName: string): void
}>()

interface NodeDef { name: string; label: string; x: number; y: number }

const AGENT_NODES: NodeDef[] = [
  { name: 'coordinator', label: '协调者', x: 100, y: 250 },
  { name: 'retriever',   label: '检索员', x: 300, y: 250 },
  { name: 'analyzer',    label: '分析员', x: 500, y: 250 },
  { name: 'comparer',    label: '对比员', x: 700, y: 150 },
  { name: 'generator',   label: '生成员', x: 700, y: 350 },
  { name: 'reviewer',    label: '审核员', x: 900, y: 250 }
]

const AGENT_LINKS = [
  { source: 'coordinator', target: 'retriever' },
  { source: 'retriever',   target: 'analyzer' },
  { source: 'analyzer',    target: 'comparer' },
  { source: 'analyzer',    target: 'generator' },
  { source: 'comparer',    target: 'generator' },
  { source: 'generator',   target: 'reviewer' }
]

/**
 * Agent 状态色（与 styles/variables.scss 中 --agent-* 一一对应）
 * ECharts 配置中无法读取 CSS 变量，使用 hex 值并在源码注释对照
 * P2-4: 提取为 @/constants/agent.ts 共享常量
 */
const STATUS_COLORS: Record<string, string> = AGENT_STATUS_COLORS

const STATUS_LABELS: Record<string, string> = {
  waiting:   '等待中',
  running:   '执行中',
  completed: '已完成',
  failed:    '失败'
}

const chartContainer = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null
const handleWindowResize = () => chart?.resize()

function getStatus(name: string): string {
  return props.agentStates[name]?.status ?? 'waiting'
}

function getColor(name: string): string {
  return STATUS_COLORS[getStatus(name)] ?? STATUS_COLORS.waiting
}

function formatDuration(ms?: number): string {
  if (ms == null) return '-'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

/** P2-3: HTML 转义，防止 ECharts tooltip XSS */
function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

const chartOption = computed(() => {
  const nodes = AGENT_NODES.map(n => {
    const status = getStatus(n.name)
    const color = getColor(n.name)
    const isRunning = status === 'running'
    return {
      id: n.name,
      name: n.label,
      x: n.x,
      y: n.y,
      symbolSize: 70,
      itemStyle: {
        color,
        borderColor: isRunning ? '#ffffff' : color,
        borderWidth: isRunning ? 4 : 2,
        shadowBlur: isRunning ? 20 : 0,
        shadowColor: isRunning ? color : 'transparent'
      },
      label: {
        show: true,
        color: '#ffffff',
        fontSize: 14,
        fontWeight: 600
      },
      value: {
        rawName: n.name,
        status,
        statusLabel: STATUS_LABELS[status] ?? status,
        progress: props.agentStates[n.name]?.progress ?? 0,
        durationMs: props.agentStates[n.name]?.durationMs,
        intermediateResult: props.agentStates[n.name]?.intermediateResult
      }
    }
  })

  // running 节点叠加 EffectScatter 制造脉冲光晕
  const effectNodes = AGENT_NODES
    .filter(n => getStatus(n.name) === 'running')
    .map(n => ({
      name: `${n.name}-effect`,
      x: n.x,
      y: n.y,
      symbolSize: 70,
      value: n.label,
      itemStyle: {
        color: getColor(n.name),
        opacity: 0.4
      }
    }))

  return {
    tooltip: {
      formatter: (params: { dataType: string; data: { name: string; value: { statusLabel: string; progress: number; durationMs?: number; intermediateResult?: string } } }) => {
        if (params.dataType !== 'node') return ''
        const v = params.data.value
        const lines = [
          `<b>${params.data.name}</b>`,
          `状态：${v.statusLabel}`,
          `进度：${Math.round((v.progress ?? 0) * 100)}%`,
          `耗时：${formatDuration(v.durationMs)}`
        ]
        if (v.intermediateResult) {
          lines.push(`结果：${escapeHtml(v.intermediateResult.slice(0, 80))}${v.intermediateResult.length > 80 ? '...' : ''}`)
        }
        return lines.join('<br/>')
      }
    },
    series: [
      {
        type: 'graph',
        layout: 'none',
        roam: false,
        data: nodes,
        links: AGENT_LINKS,
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: 8,
        lineStyle: {
          color: '#dcdfe6',
          width: 2,
          curveness: 0.1
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: { width: 4, color: '#409eff' }
        },
        z: 2
      },
      {
        type: 'effectScatter',
        coordinateSystem: 'cartesian2d',
        data: effectNodes,
        showEffectOn: 'render',
        rippleEffect: { brushType: 'stroke', scale: 4, period: 2.5 },
        hoverAnimation: true,
        z: 1
      }
    ]
  }
})

function refreshChart() {
  if (!chart) return
  chart.setOption(chartOption.value, { notMerge: true })
}

function handleClick(params: unknown) {
  const p = params as { dataType?: string; data?: { value?: { rawName?: string } } | null }
  if (p.dataType !== 'node') return
  const rawName = p.data?.value?.rawName
  if (rawName) emit('node-click', rawName)
}

function initChart() {
  if (!chartContainer.value) return
  chart = markRaw(echarts.init(chartContainer.value, undefined, { renderer: 'canvas' }))
  chart.setOption(chartOption.value)
  chart.on('click', handleClick)
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
  <div ref="chartContainer" class="agent-flow-chart" />
</template>

<style scoped lang="scss">
.agent-flow-chart {
  width: 100%;
  height: var(--chart-height-lg);
  background-color: var(--el-bg-color);
  border-radius: var(--radius-md);
}
</style>
