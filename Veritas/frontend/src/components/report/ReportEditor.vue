<script setup lang="ts">
/**
 * 综述内容编辑器组件
 * - 支持 v-model 双向绑定 Markdown 文本
 * - 支持编辑/预览/分屏三种模式
 * - 实时预览：使用 renderMarkdownWithCitations 渲染引用链接
 * - 工具栏：保存按钮、字数统计
 */
import { computed } from 'vue'
import { ElButton, ElInput, ElRadioGroup, ElRadioButton, ElText, ElIcon } from 'element-plus'
import { Document, View, Grid, Check } from '@element-plus/icons-vue'
import { renderMarkdownWithCitations } from '@/utils/markdown'
import type { Citation } from '@/types/analysis'

const props = withDefaults(defineProps<{
  modelValue: string
  citations?: Citation[]
  saving?: boolean
}>(), {
  citations: () => [],
  saving: false
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'save'): void
}>()

type ViewMode = 'edit' | 'preview' | 'split'
const mode = defineModel<ViewMode>('mode', { default: 'edit' as ViewMode })

const content = computed({
  get: () => props.modelValue,
  set: (val: string) => emit('update:modelValue', val)
})

const charCount = computed(() => content.value.length)
const wordCount = computed(() => {
  // 中英文混合字数统计：中文按字符，英文按单词
  const cn = (content.value.match(/[\u4e00-\u9fa5]/g) || []).length
  const en = (content.value.replace(/[\u4e00-\u9fa5]/g, ' ').match(/\b\w+\b/g) || []).length
  return cn + en
})

const previewHtml = computed(() =>
  renderMarkdownWithCitations(content.value, props.citations)
)

function handleSave() {
  emit('save')
}

function handlePreviewClick(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (target.tagName === 'A') {
    const href = target.getAttribute('href') || ''
    if (href.startsWith('paper:')) {
      e.preventDefault()
      // 预览模式下的引用点击由父组件处理（通过 emit 或直接跳转）
      // 此处仅阻止默认跳转，避免 404
    }
  }
}
</script>

<template>
  <div class="report-editor">
    <div class="report-editor__toolbar">
      <el-radio-group v-model="mode" size="small">
        <el-radio-button value="edit">
          <el-icon><Document /></el-icon>
          <span class="report-editor__mode-label">编辑</span>
        </el-radio-button>
        <el-radio-button value="preview">
          <el-icon><View /></el-icon>
          <span class="report-editor__mode-label">预览</span>
        </el-radio-button>
        <el-radio-button value="split">
          <el-icon><Grid /></el-icon>
          <span class="report-editor__mode-label">分屏</span>
        </el-radio-button>
      </el-radio-group>
      <div class="report-editor__toolbar-right">
        <el-text type="info" size="small">
          {{ charCount }} 字符 · {{ wordCount }} 词
        </el-text>
        <el-button
          type="primary"
          size="small"
          :loading="saving"
          :icon="Check"
          @click="handleSave"
        >
          保存
        </el-button>
      </div>
    </div>

    <div class="report-editor__body" :class="`report-editor__body--${mode}`">
      <div v-if="mode === 'edit' || mode === 'split'" class="report-editor__edit">
        <el-input
          v-model="content"
          type="textarea"
          :rows="20"
          placeholder="请输入综述内容（支持 Markdown 语法）"
          resize="vertical"
          class="report-editor__textarea"
        />
      </div>
      <div
        v-if="mode === 'preview' || mode === 'split'"
        class="report-editor__preview markdown-body"
        v-html="previewHtml"
        @click="handlePreviewClick"
      />
    </div>
  </div>
</template>

<style scoped lang="scss">
.report-editor {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm, 8px);

  &__toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: var(--spacing-sm, 8px);
    flex-wrap: wrap;
    padding: var(--spacing-xs, 4px) 0;
  }

  &__toolbar-right {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm, 8px);
  }

  &__mode-label {
    margin-left: 4px;
  }

  &__body {
    display: flex;
    gap: var(--spacing-md, 16px);
    min-height: 400px;

    &--edit {
      .report-editor__edit {
        flex: 1;
      }
    }

    &--preview {
      .report-editor__preview {
        flex: 1;
      }
    }

    &--split {
      .report-editor__edit,
      .report-editor__preview {
        flex: 1;
        min-width: 0;
      }
    }
  }

  &__edit {
    display: flex;
    flex-direction: column;
  }

  &__textarea {
    :deep(.el-textarea__inner) {
      font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
      font-size: var(--font-size-sm, 13px);
      line-height: 1.6;
      min-height: 400px;
    }
  }

  &__preview {
    padding: var(--spacing-md, 16px);
    border: 1px solid var(--el-border-color-lighter, #e4e7ed);
    border-radius: var(--radius-md, 6px);
    background: var(--el-bg-color, #fff);
    overflow-y: auto;
    max-height: 600px;
    line-height: 1.8;

    :deep(a) {
      color: var(--el-color-primary, #409eff);
    }

    :deep(h1),
    :deep(h2),
    :deep(h3) {
      margin-top: var(--spacing-md, 16px);
      margin-bottom: var(--spacing-sm, 8px);
    }

    :deep(p) {
      margin: var(--spacing-sm, 8px) 0;
    }

    :deep(code) {
      background: var(--el-fill-color-light, #f5f7fa);
      padding: 2px 6px;
      border-radius: 4px;
      font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
    }

    :deep(pre) {
      background: var(--el-fill-color-light, #f5f7fa);
      padding: var(--spacing-sm, 8px) var(--spacing-md, 16px);
      border-radius: var(--radius-md, 6px);
      overflow-x: auto;
    }
  }
}
</style>
