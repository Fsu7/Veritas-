<script setup lang="ts">
/**
 * 综述导出面板组件
 * - PDF / Word 双格式导出按钮
 * - 点击调用 analysisApi.exportPdf / exportWord → Blob 下载
 * - 导出中 loading 状态：当前按钮 loading，其他 disabled
 * - 失败 ElMessage.error + emit export-error
 * - 底部 "AI 生成，仅供参考" 提示
 */
import { ref } from 'vue'
import { ElMessage, ElButton, ElText } from 'element-plus'
import { analysisApi } from '@/api/analysis'

const props = defineProps<{
  analysisId: string
  reportTitle?: string
}>()

const emit = defineEmits<{
  (e: 'export-success', format: string): void
  (e: 'export-error', error: string): void
}>()

type ExportFormat = 'pdf' | 'word'

const exporting = ref<ExportFormat | null>(null)

function buildFilename(format: ExportFormat): string {
  const date = new Date().toISOString().slice(0, 10).replace(/-/g, '')
  const topic = props.reportTitle?.slice(0, 30) ?? 'report'
  const ext = format === 'pdf' ? 'pdf' : 'docx'
  return `综述报告_${topic}_${date}.${ext}`
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(url)
}

async function handleExport(format: ExportFormat) {
  if (exporting.value) return
  exporting.value = format
  try {
    const apiFn = format === 'pdf' ? analysisApi.exportPdf : analysisApi.exportWord
    const blob = await apiFn(props.analysisId)
    downloadBlob(blob, buildFilename(format))
    ElMessage.success(`${format.toUpperCase()} 导出成功`)
    emit('export-success', format)
  } catch (e: unknown) {
    const msg = e instanceof Error ? `${format.toUpperCase()} 导出失败: ${e.message}` : `${format.toUpperCase()} 导出失败`
    ElMessage.error(msg)
    emit('export-error', msg)
  } finally {
    exporting.value = null
  }
}
</script>

<template>
  <div class="export-panel">
    <div class="export-panel__buttons">
      <el-button
        type="primary"
        :loading="exporting === 'pdf'"
        :disabled="exporting !== null"
        @click="handleExport('pdf')"
      >
        导出 PDF
      </el-button>
      <el-button
        type="primary"
        :loading="exporting === 'word'"
        :disabled="exporting !== null"
        @click="handleExport('word')"
      >
        导出 Word
      </el-button>
    </div>
    <el-text class="export-panel__disclaimer" type="info" size="small">
      AI 生成，仅供参考
    </el-text>
  </div>
</template>

<style scoped lang="scss">
.export-panel {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm, 8px);
}

.export-panel__buttons {
  display: flex;
  gap: var(--spacing-sm, 8px);
}

.export-panel__disclaimer {
  text-align: right;
}
</style>
