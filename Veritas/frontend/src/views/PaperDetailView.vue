<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Star, StarFilled, Document } from '@element-plus/icons-vue'
import { usePaperStore } from '@/stores/paperStore'
import { useSessionStore } from '@/stores/sessionStore'
import { useUserStore } from '@/stores/userStore'
import AnalysisCard from '@/components/analysis/AnalysisCard.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import { formatMeta } from '@/utils/format'
import type { Paper } from '@/types/paper'

const route = useRoute()
const router = useRouter()
const paperStore = usePaperStore()
const sessionStore = useSessionStore()
const userStore = useUserStore()

const paper = ref<Paper | null>(null)
const paperLoading = ref(true)
const paperError = ref<string | null>(null)

const paperId = computed(() => route.params.paperId as string)

const isFavorited = computed(() =>
  paperStore.favorites.includes(paperId.value)
)

const showPlainExplanation = computed(() => {
  const profile = userStore.profile
  if (!profile) return false
  return profile.knowledgeLevel === 'beginner' || profile.knowledgeLevel === 'intermediate'
})

const analyzing = computed(() => sessionStore.isAnalyzing)

const analysisError = computed(() => sessionStore.analysisError)

/** 从 sessionStore 单一数据源派生当前分析结果（FM2 Medium 修复） */
const analysisResult = computed(() => {
  const id = sessionStore.currentAnalysisId
  return id ? sessionStore.analysisResults.get(id) ?? null : null
})

const analysisStatusText = computed(() => {
  const statusMap: Record<string, string> = {
    creating_session: '正在创建会话...',
    starting_analysis: '正在启动分析...',
    polling: 'AI正在分析论文...',
    connecting_sse: '正在连接Agent状态流...'
  }
  return statusMap[sessionStore.analysisStatus] || ''
})

async function fetchPaperDetail() {
  paperLoading.value = true
  paperError.value = null
  try {
    // 统一通过 Store Action 调用（FM2 Medium 修复）
    paper.value = await paperStore.fetchDetail(paperId.value)
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : '加载失败'
    paperError.value = message
  } finally {
    paperLoading.value = false
  }
}

async function handleFavorite() {
  try {
    await paperStore.toggleFavorite(paperId.value)
    ElMessage.success(isFavorited.value ? '已取消收藏' : '收藏成功')
  } catch {
    ElMessage.error('操作失败')
  }
}

async function handleAnalyze() {
  if (!paper.value) return
  try {
    await sessionStore.startAnalysis(paper.value.title, paperId.value)
  } catch (e: unknown) {
    const message = sessionStore.analysisError || (e instanceof Error ? e.message : '分析失败')
    ElMessage.error(message)
  }
}

function handleGenerateReport(analysisId: string) {
  router.push({ name: 'Report', params: { analysisId } })
}

function handleSelectCompare(_analysisId: string) {
  router.push({ name: 'Compare' })
}

function openPdf(url: string) {
  window.open(url, '_blank')
}

onMounted(() => {
  fetchPaperDetail()
})

onUnmounted(() => {
  sessionStore.cleanup()
})
</script>

<template>
  <div class="paper-detail-view">
    <el-skeleton v-if="paperLoading" :rows="5" animated />

    <ErrorState
      v-else-if="paperError"
      title="加载失败"
      :description="paperError"
      @retry="fetchPaperDetail"
    />

    <EmptyState
      v-else-if="!paper"
      icon="document"
      title="论文未找到"
      description="该论文可能已被删除或链接无效"
      action-text="返回首页"
      @action="router.push({ name: 'Home' })"
    />

    <template v-else>
      <div class="paper-detail-view__header">
        <el-page-header @back="router.back()" :title="paper.title" content="论文详情" />
      </div>

      <el-card class="paper-detail-view__info">
        <h1 class="paper-detail-view__title">{{ paper.title }}</h1>

        <div v-if="formatMeta(paper)" class="paper-detail-view__meta">
          <el-text type="info" size="small">{{ formatMeta(paper) }}</el-text>
        </div>

        <div class="paper-detail-view__abstract">
          {{ paper.abstract }}
        </div>

        <div v-if="paper.keywords?.length" class="paper-detail-view__keywords">
          <el-tag
            v-for="kw in paper.keywords"
            :key="kw"
            size="small"
            type="info"
          >
            {{ kw }}
          </el-tag>
        </div>

        <div class="paper-detail-view__actions">
          <el-button
            size="small"
            :type="isFavorited ? 'danger' : 'default'"
            @click="handleFavorite"
          >
            <el-icon><component :is="isFavorited ? StarFilled : Star" /></el-icon>
            {{ isFavorited ? '已收藏' : '收藏' }}
          </el-button>

          <el-button
            v-if="paper.pdfUrl"
            type="primary"
            size="small"
            @click="openPdf(paper.pdfUrl!)"
          >
            <el-icon><Document /></el-icon>
            查看PDF
          </el-button>

          <el-button
            type="primary"
            :loading="analyzing"
            @click="handleAnalyze"
          >
            触发AI分析
          </el-button>
        </div>
      </el-card>

      <el-card class="paper-detail-view__analysis">
        <template #header>
          <div class="paper-detail-view__analysis-header">
            <span>AI智能分析</span>
            <el-text type="info" size="small">AI生成，仅供参考</el-text>
          </div>
        </template>

        <div v-if="!analysisResult && !analyzing && !analysisError" class="paper-detail-view__analysis-content">
          <el-empty description="尚未进行分析">
            <el-button type="primary" @click="handleAnalyze">触发AI分析</el-button>
          </el-empty>
        </div>

        <div v-else-if="analyzing" v-loading="true" class="paper-detail-view__analysis-content">
          <p class="paper-detail-view__analysis-progress">{{ analysisStatusText }}</p>
        </div>

        <div v-else-if="analysisResult" class="paper-detail-view__analysis-content">
          <AnalysisCard
            :analysis="analysisResult"
            :show-plain-explanation="showPlainExplanation"
            @generate-report="handleGenerateReport"
            @select-compare="handleSelectCompare"
          />
        </div>

        <div v-else-if="analysisError" class="paper-detail-view__analysis-content">
          <el-alert type="error" :title="analysisError" show-icon />
          <el-button type="primary" class="paper-detail-view__retry-btn" @click="handleAnalyze">
            重新分析
          </el-button>
        </div>
      </el-card>
    </template>
  </div>
</template>

<style scoped lang="scss">
.paper-detail-view {
  max-width: var(--content-max-width, 1200px);
  padding: var(--spacing-lg, 24px);
  margin: 0 auto;
}

.paper-detail-view__header {
  margin-bottom: var(--spacing-md, 16px);
}

.paper-detail-view__info {
  margin-bottom: var(--spacing-lg, 24px);
}

.paper-detail-view__title {
  font-size: var(--font-size-xxl, 24px);
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0 0 var(--spacing-md, 16px);
  line-height: 1.4;
}

.paper-detail-view__meta {
  margin-bottom: var(--spacing-md, 16px);
}

.paper-detail-view__abstract {
  font-size: var(--font-size-base, 14px);
  color: var(--el-text-color-regular);
  line-height: 1.8;
  margin-bottom: var(--spacing-md, 16px);
}

.paper-detail-view__keywords {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm, 8px);
  margin-bottom: var(--spacing-md, 16px);
}

.paper-detail-view__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm, 8px);
  padding-top: var(--spacing-md, 16px);
  border-top: 1px solid var(--el-border-color-lighter);
}

.paper-detail-view__analysis {
  margin-bottom: var(--spacing-lg, 24px);
}

.paper-detail-view__analysis-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm, 8px);
}

.paper-detail-view__analysis-content {
  min-height: 120px;
}

.paper-detail-view__analysis-progress {
  text-align: center;
  color: var(--el-text-color-secondary);
  padding: var(--spacing-xl, 32px) 0;
}

.paper-detail-view__retry-btn {
  margin-top: var(--spacing-md, 16px);
}
</style>
