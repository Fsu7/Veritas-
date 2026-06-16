<script setup lang="ts">
/**
 * 引用溯源弹窗组件
 * - el-dialog 展示论文引用详情
 * - 标题 / 原文片段 / 元数据（作者/年份/会议）
 * - 「查看论文详情」按钮 → emit go-detail
 * - 数据缺失 → "引用信息不可用"
 */
import { computed } from 'vue'
import { ElDialog, ElButton, ElText, ElTag, ElDescriptions, ElDescriptionsItem } from 'element-plus'
import type { CitationPopupData } from '@/utils/citation'

const props = defineProps<{
  visible: boolean
  citation: CitationPopupData | null
}>()

const emit = defineEmits<{
  (e: 'update:visible', val: boolean): void
  (e: 'go-detail', paperId: string): void
}>()

const dialogVisible = computed({
  get: () => props.visible,
  set: (val: boolean) => emit('update:visible', val)
})

const hasData = computed(() => props.citation !== null)

const title = computed(() => {
  if (!props.citation) return ''
  return props.citation.title ?? props.citation.paperId
})

const authorText = computed(() => {
  if (!props.citation?.authors?.length) return '未知'
  return props.citation.authors.join(', ')
})

function handleGoDetail() {
  if (props.citation?.paperId) {
    emit('go-detail', props.citation.paperId)
    emit('update:visible', false)
  }
}
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="title || '引用详情'"
    width="520px"
    destroy-on-close
    class="citation-link-dialog"
  >
    <template v-if="hasData && citation">
      <!-- 原文片段 -->
      <div class="citation-link__snippet">
        <el-text tag="blockquote" size="default" class="citation-link__quote">
          {{ citation.text }}
        </el-text>
      </div>

      <!-- 元数据 -->
      <el-descriptions :column="1" border size="small" class="citation-link__meta">
        <el-descriptions-item label="作者">
          {{ authorText }}
        </el-descriptions-item>
        <el-descriptions-item v-if="citation.year" label="年份">
          {{ citation.year }}
        </el-descriptions-item>
        <el-descriptions-item v-if="citation.venue" label="会议 / 期刊">
          <el-tag size="small" type="info">{{ citation.venue }}</el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <!-- 操作 -->
      <div class="citation-link__actions">
        <el-button type="primary" plain @click="handleGoDetail">
          查看论文详情
        </el-button>
      </div>
    </template>

    <template v-else>
      <el-empty description="引用信息不可用" />
    </template>
  </el-dialog>
</template>

<style scoped lang="scss">
.citation-link__snippet {
  margin-bottom: var(--spacing-md, 16px);
  padding: var(--spacing-md, 16px);
  background-color: var(--el-fill-color-light);
  border-radius: var(--radius-sm, 4px);
  border-left: 3px solid var(--el-color-primary);
}

.citation-link__quote {
  font-style: italic;
  line-height: 1.6;
  color: var(--el-text-color-regular);
}

.citation-link__meta {
  margin-bottom: var(--spacing-md, 16px);
}

.citation-link__actions {
  display: flex;
  justify-content: flex-end;
  padding-top: var(--spacing-sm, 8px);
  border-top: 1px solid var(--el-border-color-lighter);
}
</style>
