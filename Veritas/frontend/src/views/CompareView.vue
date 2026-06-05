<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { usePaperStore } from '@/stores/paperStore'
import { useUserStore } from '@/stores/userStore'
import { useAgentStore } from '@/stores/agentStore'
import { analysisApi } from '@/api/analysis'
import PaperCard from '@/components/paper/PaperCard.vue'
import type { AnalysisResult, CompareResult } from '@/types/analysis'

const router = useRouter()
const paperStore = usePaperStore()
const userStore = useUserStore()
const agentStore = useAgentStore()

const compareLoading = ref(false)
const compareResult = ref<CompareResult | null>(null)
const resultDegraded = ref(false)
const resultDegradedReason = ref<string | undefined>()

const canCompare = computed(() => paperStore.canCompare)

const agentSummary = computed(() => {
  const list = agentStore.agentStatesList
  if (list.length === 0) return ''
  const completed = list.filter(a => a.status === 'completed').length
  return `Agent 进度：${completed}/${list.length}`
})

async function handleStartCompare() {
  if (!userStore.isLoggedIn) {
    ElMessageBox.confirm('请先登录后再使用对比功能', '提示', {
      confirmButtonText: '去登录',
      cancelButtonText: '取消',
      type: 'warning'
    }).then(() => {
      router.push({ name: 'Login' })
    }).catch(() => {})
    return
  }
  if (!userStore.hasProfile) {
    ElMessageBox.confirm('建议先完善用户画像以获得更精准的对比结果', '提示', {
      confirmButtonText: '去设置',
      cancelButtonText: '继续对比',
      type: 'info'
    }).then(() => {
      router.push({ name: 'UserCenter' })
    }).catch(() => {
      doCompare()
    })
    return
  }
  doCompare()
}

async function doCompare() {
  if (!canCompare.value) {
    if (paperStore.selectedPapers.length < 2) {
      ElMessage.warning('请至少选择 2 篇论文进行对比')
    } else {
      ElMessage.warning('最多选择 5 篇论文，请取消部分选择')
    }
    return
  }
  compareLoading.value = true
  compareResult.value = null
  resultDegraded.value = false
  resultDegradedReason.value = undefined
  try {
    const result = await analysisApi.comparePapers({
      paperIds: paperStore.selectedPaperIds
    })
    processResult(result)
    ElMessage.success('对比分析完成')
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : '对比分析失败'
    ElMessage.error(message)
  } finally {
    compareLoading.value = false
  }
}

function processResult(result: AnalysisResult) {
  compareResult.value = result.result?.comparison ?? null
  resultDegraded.value = result.degraded ?? false
  resultDegradedReason.value = result.degradedReason
}

async function handleGenerateReport() {
  if (!compareResult.value) {
    ElMessage.warning('请先完成对比分析')
    return
  }
  if (!userStore.profile) {
    ElMessage.warning('请先完善用户画像')
    router.push({ name: 'UserCenter' })
    return
  }
  const topic = paperStore.selectedPapers.map(p => p.title).join(' / ')
  compareLoading.value = true
  try {
    const result = await analysisApi.generateReport({
      topic,
      paperIds: paperStore.selectedPaperIds,
      profile: userStore.profile
    })
    ElMessage.success('综述生成中，请稍候...')
    router.push({ name: 'Report', params: { analysisId: result.analysisId } })
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : '综述生成失败'
    ElMessage.error(message)
  } finally {
    compareLoading.value = false
  }
}

function handleRemovePaper(paper: import('@/types/paper').Paper) {
  paperStore.togglePaperSelection(paper)
}

function handleClearSelection() {
  paperStore.clearSelection()
  compareResult.value = null
}

function goSearch() {
  router.push({ name: 'Search' })
}

const compareTableData = computed(() => {
  if (!compareResult.value) return []
  return compareResult.value.table.map(row => ({
    dimension: row.dimension,
    ...row.values.reduce<Record<string, string>>((acc, v, i) => {
      acc[`paper_${i}`] = v
      return acc
    }, {})
  }))
})

interface CompareTableColumn {
  prop: string
  label: string
  minWidth: number
  fixed?: 'left'
}

const compareTableColumns = computed<CompareTableColumn[]>(() => {
  const cols: CompareTableColumn[] = [
    { prop: 'dimension', label: '对比维度', minWidth: 120, fixed: 'left' }
  ]
  paperStore.selectedPapers.forEach((paper, i) => {
    const title = paper.title ?? ''
    cols.push({
      prop: `paper_${i}`,
      label: title.length > 16 ? title.slice(0, 16) + '…' : title || `论文 ${i + 1}`,
      minWidth: 200
    })
  })
  return cols
})

onMounted(() => {
  if (paperStore.selectedPapers.length === 0) {
    ElMessageBox.confirm('尚未选择论文，是否前往检索？', '提示', {
      confirmButtonText: '去检索',
      cancelButtonText: '取消',
      type: 'info'
    }).then(() => {
      router.push({ name: 'Search' })
    }).catch(() => {})
  }
})
</script>

<template>
  <div class="compare-view">
    <div class="compare-view__header">
      <el-page-header @back="router.back()" title="返回" content="多论文对比" />
    </div>

    <el-card class="compare-view__control">
      <div class="compare-view__control-row">
        <div class="compare-view__control-info">
          <el-text size="large">
            已选 <el-text type="primary" size="large" tag="b">{{ paperStore.selectedPapers.length }}</el-text>
            / {{ 5 }} 篇
          </el-text>
          <el-text type="info" size="small" v-if="agentSummary">{{ agentSummary }}</el-text>
        </div>
        <div class="compare-view__control-actions">
          <el-button @click="goSearch">前往检索</el-button>
          <el-button
            :disabled="paperStore.selectedPapers.length === 0"
            @click="handleClearSelection"
          >
            清空选择
          </el-button>
          <el-button
            type="primary"
            :loading="compareLoading"
            :disabled="!canCompare"
            @click="handleStartCompare"
          >
            开始对比
          </el-button>
        </div>
      </div>
    </el-card>

    <el-card v-if="paperStore.selectedPapers.length === 0" class="compare-view__empty">
      <el-empty description="尚未选择论文，请前往检索页面勾选 2-5 篇论文">
        <el-button type="primary" @click="goSearch">去检索</el-button>
      </el-empty>
    </el-card>

    <el-card v-else class="compare-view__selected">
      <template #header>
        <span>已选论文</span>
      </template>
      <PaperCard
        v-for="paper in paperStore.selectedPapers"
        :key="paper.paperId"
        :paper="paper"
        :selectable="true"
        :selected="true"
        :is-favorited="paperStore.favorites.includes(paper.paperId)"
        @toggle-select="handleRemovePaper"
      />
      <div class="compare-view__selected-actions">
        <el-button
          v-for="paper in paperStore.selectedPapers"
          :key="`remove-${paper.paperId}`"
          size="small"
          type="danger"
          plain
          @click="handleRemovePaper(paper)"
        >
          移除《{{ paper.title.slice(0, 12) }}{{ paper.title.length > 12 ? '...' : '' }}》
        </el-button>
      </div>
    </el-card>

    <div v-if="resultDegraded" class="compare-view__degraded">
      <el-alert type="warning" :closable="false" show-icon>
        <template #title>
          <span>部分降级</span>
        </template>
        <span>{{ resultDegradedReason ?? '对比分析因部分模块失败而降级，结果可能不完整' }}</span>
      </el-alert>
    </div>

    <el-card
      v-if="compareResult"
      v-loading="compareLoading"
      class="compare-view__result"
    >
      <template #header>
        <div class="compare-view__result-header">
          <span>对比结果</span>
          <el-button type="primary" :loading="compareLoading" @click="handleGenerateReport">
            生成综述
          </el-button>
        </div>
      </template>

      <div v-if="compareResult.conflicts?.length" class="compare-view__conflicts">
        <el-alert
          v-for="(conflict, idx) in compareResult.conflicts"
          :key="idx"
          type="warning"
          :title="`观点冲突 #${idx + 1}`"
          show-icon
          :closable="false"
        >
          <template #default>
            <p class="compare-view__conflict-desc">{{ conflict.description }}</p>
            <p class="compare-view__conflict-reason">
              <strong>可能原因：</strong>{{ conflict.possibleReason }}
            </p>
            <div class="compare-view__conflict-papers">
              <el-tag
                v-for="paperId in conflict.papers"
                :key="paperId"
                type="info"
                size="small"
              >
                {{ paperId }}
              </el-tag>
            </div>
          </template>
        </el-alert>
      </div>

      <el-table
        :data="compareTableData"
        border
        stripe
        style="width: 100%"
      >
        <el-table-column
          v-for="col in compareTableColumns"
          :key="col.prop"
          :prop="col.prop"
          :label="col.label"
          :min-width="col.minWidth"
          :fixed="col.fixed"
        />
      </el-table>

      <div v-if="compareResult.summary" class="compare-view__summary">
        <h3>对比总结</h3>
        <p>{{ compareResult.summary }}</p>
      </div>
    </el-card>
  </div>
</template>

<style scoped lang="scss">
.compare-view {
  max-width: var(--content-max-width, 1200px);
  margin: 0 auto;
  padding: var(--spacing-lg, 24px);
}

.compare-view__header {
  margin-bottom: var(--spacing-md, 16px);
}

.compare-view__control {
  margin-bottom: var(--spacing-md, 16px);
}

.compare-view__control-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-md, 16px);
  flex-wrap: wrap;
}

.compare-view__control-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs, 4px);
}

.compare-view__control-actions {
  display: flex;
  gap: var(--spacing-sm, 8px);
}

.compare-view__empty {
  margin-bottom: var(--spacing-md, 16px);
}

.compare-view__selected {
  margin-bottom: var(--spacing-md, 16px);
}

.compare-view__selected-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-xs, 4px);
  margin-top: var(--spacing-sm, 8px);
  padding-top: var(--spacing-sm, 8px);
  border-top: 1px dashed var(--el-border-color-lighter);
}

.compare-view__degraded {
  margin-bottom: var(--spacing-md, 16px);
}

.compare-view__result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.compare-view__conflicts {
  margin-bottom: var(--spacing-md, 16px);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm, 8px);
}

.compare-view__conflict-desc {
  margin: 0 0 var(--spacing-xs, 4px);
  color: var(--el-text-color-regular);
}

.compare-view__conflict-reason {
  margin: 0 0 var(--spacing-xs, 4px);
  color: var(--el-text-color-secondary);
  font-size: var(--font-size-sm, 13px);
}

.compare-view__conflict-papers {
  display: flex;
  gap: var(--spacing-xs, 4px);
  flex-wrap: wrap;
}

.compare-view__summary {
  margin-top: var(--spacing-md, 16px);
  padding: var(--spacing-md, 16px);
  background-color: var(--el-fill-color-light);
  border-radius: var(--radius-sm, 4px);

  h3 {
    margin: 0 0 var(--spacing-sm, 8px);
    color: var(--el-text-color-primary);
  }

  p {
    margin: 0;
    color: var(--el-text-color-regular);
    line-height: 1.8;
  }
}
</style>
