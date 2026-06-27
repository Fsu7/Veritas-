<script setup lang="ts">
/**
 * 画像可视化看板组件
 * - 雷达图：4 维度画像（学历、知识水平、偏好风格、研究活跃度）
 * - 个性化洞察卡片：根据画像维度生成推荐建议
 * - 研究活跃度综合评分
 */
import { ref, computed, watch, onMounted, onUnmounted, markRaw } from 'vue'
import * as echarts from 'echarts/core'
import { RadarChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { UserProfile } from '@/types/user'

echarts.use([RadarChart, TooltipComponent, LegendComponent, TitleComponent, CanvasRenderer])

const props = defineProps<{
  profile: UserProfile
  sessionsCount: number
  favoritesCount: number
}>()

// ---- 维度量化映射 ----
const educationScore: Record<UserProfile['educationLevel'], number> = {
  undergraduate: 25,
  master: 50,
  phd: 75,
  faculty: 100
}
const knowledgeScore: Record<UserProfile['knowledgeLevel'], number> = {
  beginner: 25,
  intermediate: 50,
  advanced: 75,
  expert: 100
}
const styleScore: Record<UserProfile['preferredStyle'], number> = {
  simple: 33,
  balanced: 66,
  technical: 100
}

const educationLabels: Record<UserProfile['educationLevel'], string> = {
  undergraduate: '本科生',
  master: '硕士研究生',
  phd: '博士研究生',
  faculty: '教师/研究者'
}
const knowledgeLabels: Record<UserProfile['knowledgeLevel'], string> = {
  beginner: '初级',
  intermediate: '中级',
  advanced: '高级',
  expert: '专家'
}
const styleLabels: Record<UserProfile['preferredStyle'], string> = {
  simple: '通俗',
  balanced: '均衡',
  technical: '专业'
}

// ---- 计算属性 ----
const radarValues = computed(() => {
  const activity = Math.min(100, props.sessionsCount * 15 + props.favoritesCount * 10)
  return [
    educationScore[props.profile.educationLevel],
    knowledgeScore[props.profile.knowledgeLevel],
    styleScore[props.profile.preferredStyle],
    activity
  ]
})

const overallScore = computed(() => {
  const [edu, know, style, act] = radarValues.value
  return Math.round((edu + know + style + act) / 4)
})

const scoreLevel = computed(() => {
  const s = overallScore.value
  if (s >= 75) return { label: '深度研究者', color: '#67C23A', icon: '🏆' }
  if (s >= 50) return { label: '积极学习者', color: '#409EFF', icon: '📚' }
  if (s >= 25) return { label: '入门探索者', color: '#E6A23C', icon: '🌱' }
  return { label: '科研新手', color: '#909399', icon: '🎯' }
})

// 个性化洞察
const insights = computed(() => {
  const list: { icon: string; text: string }[] = []
  const p = props.profile

  // 学历洞察
  if (p.educationLevel === 'faculty' || p.educationLevel === 'phd') {
    list.push({ icon: '🎓', text: '高学历研究者，推荐使用专业级深度分析和对比功能' })
  } else if (p.educationLevel === 'undergraduate') {
    list.push({ icon: '📖', text: '本科生阶段，建议从通俗风格综述入门，逐步深入' })
  }

  // 知识水平洞察
  if (p.knowledgeLevel === 'expert' || p.knowledgeLevel === 'advanced') {
    list.push({ icon: '🧠', text: '专业知识扎实，系统将优先推荐前沿论文和深度技术分析' })
  } else if (p.knowledgeLevel === 'beginner') {
    list.push({ icon: '💡', text: '初学者模式，系统会自动简化术语并提供背景知识补充' })
  }

  // 风格偏好洞察
  if (p.preferredStyle === 'technical') {
    list.push({ icon: '⚙️', text: '偏好专业风格，综述将包含完整引用和技术细节' })
  } else if (p.preferredStyle === 'simple') {
    list.push({ icon: '✨', text: '偏好通俗风格，系统将用类比和日常语言解释学术概念' })
  }

  // 活跃度洞察
  const activity = props.sessionsCount + props.favoritesCount
  if (activity === 0) {
    list.push({ icon: '🚀', text: '尚未开始分析，试试搜索感兴趣的论文并启动智能分析' })
  } else if (activity >= 5) {
    list.push({ icon: '🔥', text: `活跃度高（${activity} 次互动），系统将基于历史推荐相关论文` })
  }

  // 研究方向洞察
  if (p.researchField) {
    list.push({ icon: '🔬', text: `研究方向「${p.researchField}」，系统将优先检索该领域最新成果` })
  }

  return list
})

const profileSummary = computed(() => {
  return [
    { label: '学历', value: educationLabels[props.profile.educationLevel], color: '#409EFF' },
    { label: '水平', value: knowledgeLabels[props.profile.knowledgeLevel], color: '#67C23A' },
    { label: '风格', value: styleLabels[props.profile.preferredStyle], color: '#E6A23C' },
    { label: '方向', value: props.profile.researchField || '未设置', color: '#F56C6C' }
  ]
})

// ---- ECharts 雷达图 ----
const chartContainer = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null

const chartOption = computed(() => ({
  tooltip: {
    trigger: 'item',
    backgroundColor: 'rgba(255,255,255,0.95)',
    borderColor: '#e4e7ed',
    textStyle: { color: '#303133', fontSize: 13 },
    formatter: () => {
      const labels = ['学历层次', '知识水平', '偏好风格', '研究活跃度']
      const vals = radarValues.value
      let html = '<div style="font-weight:600;margin-bottom:4px;">画像维度</div>'
      labels.forEach((l, i) => {
        html += `<div style="display:flex;justify-content:space-between;gap:16px;"><span>${l}</span><b>${vals[i]}</b></div>`
      })
      return html
    }
  },
  radar: {
    indicator: [
      { name: '学历层次', max: 100 },
      { name: '知识水平', max: 100 },
      { name: '偏好风格', max: 100 },
      { name: '研究活跃度', max: 100 }
    ],
    radius: '65%',
    center: ['50%', '52%'],
    axisName: {
      color: '#606266',
      fontSize: 13,
      padding: [3, 5]
    },
    splitLine: { lineStyle: { color: 'rgba(0,0,0,0.08)' } },
    splitArea: {
      areaStyle: {
        color: ['rgba(64,158,255,0.03)', 'rgba(64,158,255,0.06)', 'rgba(64,158,255,0.09)', 'rgba(64,158,255,0.12)']
      }
    },
    axisLine: { lineStyle: { color: 'rgba(0,0,0,0.1)' } }
  },
  series: [
    {
      type: 'radar',
      data: [{
        value: radarValues.value,
        name: '我的画像',
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: { width: 2, color: '#409EFF' },
        itemStyle: { color: '#409EFF' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64,158,255,0.35)' },
            { offset: 1, color: 'rgba(64,158,255,0.05)' }
          ])
        },
        label: {
          show: true,
          color: '#303133',
          fontSize: 12,
          fontWeight: 'bold',
          formatter: (params: { value: number[] }) => params.value
        }
      }]
    }
  ]
}))

function initChart() {
  if (!chartContainer.value) return
  chart = markRaw(echarts.init(chartContainer.value, undefined, { renderer: 'canvas' }))
  chart.setOption(chartOption.value)
  window.addEventListener('resize', handleResize)
  if (typeof ResizeObserver !== 'undefined' && chartContainer.value) {
    resizeObserver = new ResizeObserver(() => chart?.resize())
    resizeObserver.observe(chartContainer.value)
  }
}

function refreshChart() {
  if (!chart) return
  chart.setOption(chartOption.value, { notMerge: true })
}

function handleResize() {
  chart?.resize()
}

function disposeChart() {
  window.removeEventListener('resize', handleResize)
  resizeObserver?.disconnect()
  resizeObserver = null
  if (chart) {
    chart.dispose()
    chart = null
  }
}

watch(() => [props.profile, props.sessionsCount, props.favoritesCount], refreshChart, { deep: true })

onMounted(initChart)
onUnmounted(disposeChart)
</script>

<template>
  <div class="profile-dashboard">
    <!-- 综合评分 -->
    <div class="profile-dashboard__score-bar">
      <div class="profile-dashboard__score-left">
        <div class="profile-dashboard__score-ring" :style="{ '--score-color': scoreLevel.color }">
          <span class="profile-dashboard__score-num">{{ overallScore }}</span>
          <span class="profile-dashboard__score-unit">分</span>
        </div>
      </div>
      <div class="profile-dashboard__score-right">
        <div class="profile-dashboard__score-level">
          <span class="profile-dashboard__score-icon">{{ scoreLevel.icon }}</span>
          <span :style="{ color: scoreLevel.color }">{{ scoreLevel.label }}</span>
        </div>
        <div class="profile-dashboard__score-desc">
          基于学历、知识水平、风格偏好和研究活跃度综合评估
        </div>
      </div>
    </div>

    <!-- 雷达图 + 维度摘要 -->
    <div class="profile-dashboard__main">
      <div class="profile-dashboard__chart-wrap">
        <div ref="chartContainer" class="profile-dashboard__chart" />
      </div>
      <div class="profile-dashboard__summary">
        <div
          v-for="item in profileSummary"
          :key="item.label"
          class="profile-dashboard__summary-item"
        >
          <span
            class="profile-dashboard__summary-dot"
            :style="{ background: item.color }"
          />
          <span class="profile-dashboard__summary-label">{{ item.label }}</span>
          <span class="profile-dashboard__summary-value">{{ item.value }}</span>
        </div>
      </div>
    </div>

    <!-- 活跃度统计 -->
    <div class="profile-dashboard__stats">
      <div class="profile-dashboard__stat">
        <span class="profile-dashboard__stat-num">{{ sessionsCount }}</span>
        <span class="profile-dashboard__stat-label">分析会话</span>
      </div>
      <el-divider direction="vertical" class="profile-dashboard__divider" />
      <div class="profile-dashboard__stat">
        <span class="profile-dashboard__stat-num">{{ favoritesCount }}</span>
        <span class="profile-dashboard__stat-label">收藏论文</span>
      </div>
      <el-divider direction="vertical" class="profile-dashboard__divider" />
      <div class="profile-dashboard__stat">
        <span class="profile-dashboard__stat-num">{{ profile.researchField || '—' }}</span>
        <span class="profile-dashboard__stat-label">研究方向</span>
      </div>
    </div>

    <!-- 个性化洞察 -->
    <div v-if="insights.length > 0" class="profile-dashboard__insights">
      <div class="profile-dashboard__insights-title">个性化洞察</div>
      <div
        v-for="(insight, i) in insights"
        :key="i"
        class="profile-dashboard__insight-item"
      >
        <span class="profile-dashboard__insight-icon">{{ insight.icon }}</span>
        <span class="profile-dashboard__insight-text">{{ insight.text }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.profile-dashboard {
  width: 100%;

  &__score-bar {
    display: flex;
    align-items: center;
    gap: var(--spacing-lg);
    padding: var(--spacing-md) var(--spacing-lg);
    background: linear-gradient(135deg, rgba(64,158,255,0.06), rgba(103,194,58,0.04));
    border-radius: var(--radius-md);
    margin-bottom: var(--spacing-lg);
  }

  &__score-ring {
    width: 64px;
    height: 64px;
    border-radius: 50%;
    border: 4px solid var(--score-color, #409EFF);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  &__score-num {
    font-size: 22px;
    font-weight: 700;
    color: var(--score-color, #409EFF);
    line-height: 1;
  }

  &__score-unit {
    font-size: 10px;
    color: var(--el-text-color-secondary);
    margin-top: 2px;
  }

  &__score-right {
    flex: 1;
    min-width: 0;
  }

  &__score-level {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    font-size: var(--font-size-lg);
    font-weight: 600;
    margin-bottom: 4px;
  }

  &__score-icon {
    font-size: 20px;
  }

  &__score-desc {
    font-size: var(--font-size-sm);
    color: var(--el-text-color-secondary);
  }

  &__main {
    display: flex;
    gap: var(--spacing-lg);
    align-items: center;
  }

  &__chart-wrap {
    flex: 1;
    min-width: 0;
  }

  &__chart {
    width: 100%;
    height: 280px;
  }

  &__summary {
    width: 160px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
  }

  &__summary-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    font-size: var(--font-size-base);
  }

  &__summary-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  &__summary-label {
    color: var(--el-text-color-secondary);
    flex-shrink: 0;
  }

  &__summary-value {
    font-weight: 500;
    color: var(--el-text-color-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__stats {
    display: flex;
    align-items: center;
    justify-content: space-around;
    padding: var(--spacing-md) 0;
    margin-top: var(--spacing-md);
    border-top: 1px solid var(--el-border-color-lighter);
  }

  &__stat {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    flex: 1;
  }

  &__stat-num {
    font-size: var(--font-size-xl);
    font-weight: 700;
    color: var(--el-color-primary);
  }

  &__stat-label {
    font-size: var(--font-size-sm);
    color: var(--el-text-color-secondary);
  }

  &__divider {
    height: 32px;
  }

  &__insights {
    margin-top: var(--spacing-md);
    padding: var(--spacing-md);
    background: var(--el-fill-color-light);
    border-radius: var(--radius-md);
  }

  &__insights-title {
    font-size: var(--font-size-base);
    font-weight: 600;
    color: var(--el-text-color-primary);
    margin-bottom: var(--spacing-sm);
  }

  &__insight-item {
    display: flex;
    align-items: flex-start;
    gap: var(--spacing-sm);
    padding: 6px 0;
    font-size: var(--font-size-sm);
    color: var(--el-text-color-regular);
    line-height: 1.6;
  }

  &__insight-icon {
    flex-shrink: 0;
    font-size: 16px;
  }

  &__insight-text {
    flex: 1;
  }
}

@media (max-width: 768px) {
  .profile-dashboard__main {
    flex-direction: column;
  }

  .profile-dashboard__summary {
    width: 100%;
    flex-direction: row;
    flex-wrap: wrap;
    gap: var(--spacing-md);
  }

  .profile-dashboard__summary-item {
    flex: 1 1 40%;
  }

  .profile-dashboard__chart {
    height: 240px;
  }
}
</style>
