<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { View, Connection, Download, Edit, Check } from '@element-plus/icons-vue'
import { useSessionStore } from '@/stores/sessionStore'
import { useUserStore } from '@/stores/userStore'
import { usePaperStore } from '@/stores/paperStore'
import { renderMarkdown } from '@/utils/markdown'
import { splitReportSegments, extractCitationData } from '@/utils/citation'
import { formatDate } from '@/utils/format'
import ExportPanel from '@/components/report/ExportPanel.vue'
import CitationLink from '@/components/report/CitationLink.vue'
import ReportEditor from '@/components/report/ReportEditor.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import type { AnalysisResult, Citation } from '@/types/analysis'
import type { CitationPopupData } from '@/utils/citation'

const route = useRoute()
const router = useRouter()
const sessionStore = useSessionStore()
const userStore = useUserStore()
const paperStore = usePaperStore()

const analysisId = computed(() => route.params.analysisId as string)

const result = ref<AnalysisResult | null>(null)
const loading = ref(true)
const loadError = ref<string | null>(null)

// 编辑模式状态
const editMode = ref(false)
const editableContent = ref('')
const editorMode = ref<'edit' | 'preview' | 'split'>('edit')
const savingContent = ref(false)

/** CitationLink 弹窗状态 */
const citePopupVisible = ref(false)
const selectedCitation = ref<CitationPopupData | null>(null)

const reportRawText = computed(() => result.value?.result?.report ?? '')

const reportMarkdown = computed(() => {
  if (!reportRawText.value) return ''
  return renderMarkdown(reportRawText.value)
})

const reportSegments = computed(() => {
  if (!reportRawText.value) return []
  const citations = (result.value?.result?.citations ?? []) as Citation[]
  return splitReportSegments(reportRawText.value, citations)
})

const reportTitle = computed(() => {
  return result.value?.result?.analysis?.researchQuestion ?? '文献综述报告'
})

const citationsList = computed<Citation[]>(() =>
  (result.value?.result?.citations ?? []) as Citation[]
)

const profileTags = computed(() => {
  const p = userStore.profile
  if (!p) return []
  return [
    { label: '教育阶段', type: 'info' as const, value: p.educationLevel },
    { label: '知识水平', type: 'primary' as const, value: p.knowledgeLevel },
    { label: '研究领域', type: 'success' as const, value: p.researchField },
    { label: '偏好风格', type: 'warning' as const, value: p.preferredStyle }
  ]
})

const paperCount = computed(() => {
  const citations = result.value?.result?.citations
  if (!citations?.length) return 0
  return new Set(citations.map(c => c.paperId)).size
})

const generatedAt = computed<string | undefined>(() => {
  if (!result.value) return undefined
  return (result.value as any).createdAt || (result.value as any).completedAt || undefined
})

async function loadResult() {
  if (!analysisId.value) {
    loadError.value = '分析 ID 缺失'
    loading.value = false
    return
  }
  loading.value = true
  loadError.value = null
  try {
    const res = await sessionStore.fetchAnalysisResult(analysisId.value)
    result.value = res
    // 初始化编辑内容
    editableContent.value = res.result?.report ?? ''
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : '加载综述失败'
    loadError.value = message
  } finally {
    loading.value = false
  }
}

/** 点击引用 → 弹窗展示详情 */
function handleCitationClick(paperId?: string, rawText?: string) {
  if (!paperId) return
  const citations = (result.value?.result?.citations ?? []) as Citation[]
  const data = extractCitationData(
    rawText ?? `[]`,
    citations,
    paperStore.searchResults
  )
  if (!data) {
    ElMessage.info('引用信息不可用')
    return
  }
  selectedCitation.value = data
  citePopupVisible.value = true
}

/** 引弹窗内查看论文详情 */
function handleGoDetail(paperId: string) {
  router.push({ name: 'PaperDetail', params: { paperId } })
}

function goAgentFlow() {
  if (!analysisId.value) return
  router.push({ name: 'AgentFlow', params: { analysisId: analysisId.value } })
}

function copyMarkdown() {
  const raw = reportRawText.value
  if (!raw) {
    ElMessage.warning('综述内容为空')
    return
  }
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(raw)
      .then(() => ElMessage.success('已复制 Markdown 源文'))
      .catch(() => ElMessage.error('复制失败，请手动复制'))
  } else {
    ElMessage.error('当前浏览器不支持剪贴板 API')
  }
}

/** 进入编辑模式 */
function handleEnterEdit() {
  editableContent.value = reportRawText.value
  editMode.value = true
  editorMode.value = 'edit'
}

/** 退出编辑模式（不保存） */
function handleExitEdit() {
  editMode.value = false
  editableContent.value = reportRawText.value
}

/** 保存编辑内容到后端 */
async function handleSaveContent() {
  if (!analysisId.value) return
  savingContent.value = true
  try {
    await sessionStore.saveReportContent(analysisId.value, editableContent.value)
    // 更新本地 result 中的 report，使预览模式立即反映新内容
    if (result.value?.result) {
      result.value.result.report = editableContent.value
    }
    ElMessage.success('综述内容保存成功')
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '保存失败'
    ElMessage.error(`保存失败：${msg}`)
  } finally {
    savingContent.value = false
  }
}

watch(analysisId, () => {
  loadResult()
})

onMounted(() => {
  loadResult()
})
</script>

<template>
  <div class="report-view">
    <div class="report-view__header">
      <el-page-header @back="router.back()" title="返回" content="文献综述报告" />
    </div>

    <el-skeleton v-if="loading" :rows="8" animated />

    <ErrorState
      v-else-if="loadError"
      title="加载失败"
      :description="loadError"
      @retry="loadResult"
    />

    <EmptyState
      v-else-if="!result"
      icon="document"
      title="综述未找到"
      description="该分析可能不存在或已被删除"
      action-text="返回首页"
      @action="router.push({ name: 'Home' })"
    />

    <template v-else>
      <!-- 元数据卡 -->
      <el-card class="report-view__meta">
        <template #header>
          <div class="report-view__meta-header">
            <h2 class="report-view__title">{{ reportTitle }}</h2>
            <el-tag
              v-if="result.degraded"
              type="warning"
              size="large"
              effect="dark"
            >
              <el-icon><Connection /></el-icon>
              <span style="margin-left: 4px">部分降级</span>
            </el-tag>
          </div>
        </template>

        <el-descriptions :column="2" border>
          <el-descriptions-item label="生成时间">
            {{ formatDate(generatedAt) }}
          </el-descriptions-item>
          <el-descriptions-item label="论文数量">
            {{ paperCount || '-' }} 篇
          </el-descriptions-item>
          <el-descriptions-item label="用户画像">
            <el-tag
              v-for="tag in profileTags"
              :key="tag.label"
              :type="tag.type"
              size="small"
            >
              {{ tag.label }}：{{ tag.value }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="分析状态">
            <el-tag :type="result.status === 'completed' ? 'success' : 'warning'">
              {{ result.status === 'completed' ? '已完成' : result.status }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="result.degraded && result.degradedReason" class="report-view__degraded-reason">
          <el-text type="warning" size="small">降级原因：{{ result.degradedReason }}</el-text>
        </div>

        <div class="report-view__meta-actions">
          <el-button :icon="View" @click="goAgentFlow">查看 Agent 协同过程</el-button>
          <el-button :icon="Download" @click="copyMarkdown">复制 Markdown</el-button>
          <el-button
            v-if="!editMode"
            type="warning"
            :icon="Edit"
            @click="handleEnterEdit"
          >
            编辑综述
          </el-button>
          <el-button
            v-else
            type="info"
            :icon="Check"
            @click="handleExitEdit"
          >
            完成编辑
          </el-button>
        </div>

        <!-- FM4 导出面板 -->
        <ExportPanel
          :analysis-id="analysisId"
          :report-title="reportTitle"
          :custom-content="editMode ? editableContent : undefined"
          class="report-view__export"
        />
      </el-card>

      <!-- 综述内容主体 -->
      <el-card v-if="reportRawText" class="report-view__content">
        <template #header>
          <div class="report-view__content-header">
            <span>综述内容</span>
            <el-text type="info" size="small">
              <span style="margin-left: 4px">点击引用 [Author, Year] 查看详情</span>
            </el-text>
          </div>
        </template>

        <!-- 编辑模式 -->
        <ReportEditor
          v-if="editMode"
          v-model="editableContent"
          v-model:mode="editorMode"
          :citations="citationsList"
          :saving="savingContent"
          @save="handleSaveContent"
        />

        <!-- 预览模式 -->
        <template v-else>
          <div class="report-view__segments">
            <template v-for="(segment, i) in reportSegments" :key="i">
              <span v-if="segment.type === 'text'" class="report-view__segment-text">{{ segment.value }}</span>
              <el-link
                v-else
                type="primary"
                :underline="false"
                :disabled="!segment.paperId"
                class="report-view__citation"
                @click="handleCitationClick(segment.paperId, segment.value)"
              >
                [{{ segment.authors }}, {{ segment.year }}]
              </el-link>
            </template>
          </div>

          <!-- Markdown 渲染备份 -->
          <div
            v-if="reportMarkdown"
            class="markdown-body report-view__markdown"
            v-html="reportMarkdown"
            @click="(e) => {
              const target = e.target as HTMLElement
              if (target.tagName === 'A' && target.getAttribute('href')?.startsWith('paper:')) {
                e.preventDefault()
                handleCitationClick(target.getAttribute('href')?.replace('paper:', '') ?? undefined)
              }
            }"
          />
        </template>
      </el-card>

      <el-empty v-else description="综述内容为空" />
    </template>

    <!-- 引用弹窗 -->
    <CitationLink
      v-model:visible="citePopupVisible"
      :citation="selectedCitation"
      @go-detail="handleGoDetail"
    />
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/mixins' as *;

.report-view {
  max-width: var(--content-max-width, 1200px);
  margin: 0 auto;
  padding: var(--spacing-lg, 24px);
}

.report-view__header {
  margin-bottom: var(--spacing-md, 16px);
}

.report-view__meta {
  margin-bottom: var(--spacing-md, 16px);
}

.report-view__meta-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md, 16px);
  flex-wrap: wrap;
}

.report-view__title {
  font-size: var(--font-size-xl, 20px);
  font-weight: 600;
  margin: 0;
  color: var(--el-text-color-primary);
  flex: 1;
  min-width: 200px;
}

.report-view__degraded-reason {
  margin-top: var(--spacing-sm, 8px);
}

.report-view__meta-actions {
  margin-top: var(--spacing-md, 16px);
  display: flex;
  gap: var(--spacing-sm, 8px);
  flex-wrap: wrap;
}

.report-view__export {
  margin-top: var(--spacing-md, 16px);
  padding-top: var(--spacing-md, 16px);
  border-top: 1px solid var(--el-border-color-lighter);
}

.report-view__content {
  margin-bottom: var(--spacing-md, 16px);
}

.report-view__content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-sm, 8px);
  flex-wrap: wrap;
}

.report-view__segments {
  font-size: var(--font-size-base, 14px);
  line-height: 1.8;
  color: var(--el-text-color-regular);
  margin-bottom: var(--spacing-md, 16px);
  white-space: pre-wrap;
  word-break: break-word;
}

.report-view__segment-text {
  white-space: pre-wrap;
}

.report-view__citation {
  font-weight: 500;
  margin: 0 2px;
  cursor: pointer;
}

.report-view__citation:hover {
  text-decoration: underline;
}

.report-view__markdown {
  margin-top: var(--spacing-md, 16px);
  padding-top: var(--spacing-md, 16px);
  border-top: 1px dashed var(--el-border-color-lighter);

  :deep(a) {
    color: var(--el-color-primary);
  }
}

/* Task 50: 移动端响应式 */
@include respond-to(md) {
  .report-view {
    padding: var(--spacing-md);
  }
  .report-view__title {
    font-size: var(--font-size-lg);
  }
  .report-view__meta-header {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
