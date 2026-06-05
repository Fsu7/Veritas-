<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts/core'
import { GraphChart } from 'echarts/charts'
import {
  TooltipComponent,
  LegendComponent,
  TitleComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useSessionStore } from '@/stores/sessionStore'
import { useAgentStore } from '@/stores/agentStore'
import type { AgentState } from '@/types/agent'

echarts.use([
  GraphChart,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  CanvasRenderer
])

const route = useRoute()
const router = useRouter()
const sessionStore = useSessionStore()
const agentStore = useAgentStore()

const analysisId = computed(() => route.params.analysisId as string)

const chartContainer = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

/** 6 个 Agent 节点（符合 03-agent-system.md） */
const AGENT_NODES: { name: string; label: string; x: number; y: number }[] = [
  { name: 'coordinator', label: '协调者', x: 100, y: 250 },
  { name: 'retriever',   label: '检索员', x: 300, y: 250 },
  { name: 'analyzer',    label: '分析员', x: 500, y: 250 },
  { name: 'comparer',    label: '对比员', x: 700, y: 150 },
  { name: 'generator',   label: '生成员', x: 700, y: 350 },
  { name: 'reviewer',    label: '审核员', x: 900, y: 250 }
]

/** 状态色映射（CSS 变量值，避免硬编码） */
const STATUS_COLORS: Record<string, string> = {
  waiting: '#c0c4cc',
  running: '#409eff',
  completed: '#67c23a',
  failed: '#f56c6c',
  unknown: '#909399'
}

const selectedAgent = ref<AgentState | null>(null)
const drawerVisible = ref(false)

function getNodeStatus(name: string): string {
  const state = agentStore.agentStates[name]
  return state?.status ?? 'waiting'
}

function getNodeColor(name: string): string {
  return STATUS_COLORS[getNodeStatus(name)] ?? STATUS_COLORS.unknown
}

function getNodeItemStyle(name: string): { color: string; borderColor: string; borderWidth: number } {
  const status = getNodeStatus(name)
  const color = getNodeColor(name)
  return {
    color,
    borderColor: status === 'running' ? '#fff' : color,
    borderWidth: status === 'running' ? 4 : 2
  }
}

function buildChartOption() {
  const nodes = AGENT_NODES.map(n => ({
    id: n.name,
    name: n.label,
    x: n.x,
    y: n.y,
    symbolSize: 70,
    itemStyle: getNodeItemStyle(n.name),
    label: {
      show: true,
      color: '#fff',
      fontSize: 14,
      fontWeight: 600
    },
    value: {
      status: getNodeStatus(n.name),
      rawName: n.name
    }
  }))

  const links = [
    { source: 'coordinator', target: 'retriever' },
    { source: 'retriever',   target: 'analyzer' },
    { source: 'analyzer',    target: 'comparer' },
    { source: 'analyzer',    target: 'generator' },
    { source: 'comparer',    target: 'generator' },
    { source: 'generator',   target: 'reviewer' }
  ]

  return {
    tooltip: {
      formatter: (params: { dataType: string; data: { name: string; value: { status: string; rawName: string } } }) => {
        if (params.dataType === 'node') {
          return `<b>${params.data.name}</b><br/>状态：${params.data.value.status}`
        }
        return ''
      }
    },
    series: [{
      type: 'graph',
      layout: 'none',
      roam: false,
      data: nodes,
      links,
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
      }
    }]
  }
}

function refreshChart() {
  if (!chart) return
  chart.setOption(buildChartOption(), { notMerge: true })
}

function handleNodeClick(params: { dataType?: string; data?: unknown }) {
  if (params.dataType !== 'node') return
  const data = params.data as { value?: { rawName?: string } } | null | undefined
  const rawName = data?.value?.rawName
  if (!rawName) return
  const state = agentStore.agentStates[rawName]
  if (!state) {
    ElMessage.info('该 Agent 尚未启动或无状态信息')
    return
  }
  selectedAgent.value = state
  drawerVisible.value = true
}

async function initChart() {
  if (!chartContainer.value) return
  chart = echarts.init(chartContainer.value, undefined, { renderer: 'canvas' })
  chart.setOption(buildChartOption())
  chart.on('click', handleNodeClick)
  window.addEventListener('resize', handleResize)
}

function handleResize() {
  chart?.resize()
}

async function connectStream() {
  if (!analysisId.value) return
  try {
    await sessionStore.fetchAnalysisResult(analysisId.value)
  } catch {
    // 即使拉取失败也尝试连接 SSE
  }
  sessionStore.connectAgentStream(analysisId.value)
}

function cleanup() {
  if (chart) {
    chart.dispose()
    chart = null
  }
  window.removeEventListener('resize', handleResize)
  sessionStore.disconnectSSE()
  agentStore.resetStates()
}

onMounted(async () => {
  await initChart()
  await connectStream()
})

onUnmounted(() => {
  cleanup()
})

watch(() => agentStore.agentStates, () => {
  refreshChart()
}, { deep: true })
</script>

<template>
  <div class="agent-flow-view">
    <div class="agent-flow-view__header">
      <el-page-header @back="router.back()" title="返回" content="Agent 协同过程" />
    </div>

    <el-card class="agent-flow-view__legend">
      <el-text type="info" size="small">图例：</el-text>
      <el-tag type="info" size="small" style="margin-left: 8px">
        <span :style="{ display: 'inline-block', width: '10px', height: '10px', background: STATUS_COLORS.waiting, marginRight: '4px' }"></span>
        等待 waiting
      </el-tag>
      <el-tag type="primary" size="small" style="margin-left: 8px">
        <span :style="{ display: 'inline-block', width: '10px', height: '10px', background: STATUS_COLORS.running, marginRight: '4px' }"></span>
        运行 running
      </el-tag>
      <el-tag type="success" size="small" style="margin-left: 8px">
        <span :style="{ display: 'inline-block', width: '10px', height: '10px', background: STATUS_COLORS.completed, marginRight: '4px' }"></span>
        完成 completed
      </el-tag>
      <el-tag type="danger" size="small" style="margin-left: 8px">
        <span :style="{ display: 'inline-block', width: '10px', height: '10px', background: STATUS_COLORS.failed, marginRight: '4px' }"></span>
        失败 failed
      </el-tag>
    </el-card>

    <el-card class="agent-flow-view__chart-card">
      <div ref="chartContainer" class="agent-flow-view__chart"></div>
    </el-card>

    <el-drawer
      v-model="drawerVisible"
      :title="selectedAgent?.name ?? 'Agent 详情'"
      direction="rtl"
      size="400px"
    >
      <div v-if="selectedAgent" class="agent-flow-view__detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="Agent 名称">
            {{ selectedAgent.name }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="selectedAgent.status === 'completed' ? 'success' : (selectedAgent.status === 'failed' ? 'danger' : 'primary')">
              {{ selectedAgent.status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="进度">
            <el-progress :percentage="Math.round((selectedAgent.progress ?? 0) * 100)" />
          </el-descriptions-item>
          <el-descriptions-item v-if="selectedAgent.durationMs != null" label="耗时">
            {{ (selectedAgent.durationMs / 1000).toFixed(2) }} s
          </el-descriptions-item>
          <el-descriptions-item v-if="selectedAgent.intermediateResult" label="中间结果">
            <pre class="agent-flow-view__intermediate">{{ selectedAgent.intermediateResult }}</pre>
          </el-descriptions-item>
          <el-descriptions-item v-if="selectedAgent.error" label="错误信息">
            <el-text type="danger">{{ selectedAgent.error }}</el-text>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped lang="scss">
.agent-flow-view {
  max-width: var(--content-max-width, 1200px);
  margin: 0 auto;
  padding: var(--spacing-lg, 24px);
}

.agent-flow-view__header {
  margin-bottom: var(--spacing-md, 16px);
}

.agent-flow-view__legend {
  margin-bottom: var(--spacing-md, 16px);
}

.agent-flow-view__chart-card {
  margin-bottom: var(--spacing-md, 16px);
}

.agent-flow-view__chart {
  width: 100%;
  height: 500px;
}

.agent-flow-view__detail {
  padding: 0 var(--spacing-md, 16px);
}

.agent-flow-view__intermediate {
  margin: 0;
  padding: var(--spacing-sm, 8px);
  background-color: var(--el-fill-color-light);
  border-radius: var(--radius-sm, 4px);
  font-size: var(--font-size-sm, 13px);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 300px;
  overflow-y: auto;
}
</style>
