/**
 * ExportPanel 组件测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'

const mockExportPdf = vi.fn()
const mockExportWord = vi.fn()

vi.mock('@/api/analysis', () => ({
  analysisApi: {
    exportPdf: mockExportPdf,
    exportWord: mockExportWord
  }
}))

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), info: vi.fn() },
  ElButton: {
    name: 'ElButton',
    props: ['type', 'loading', 'disabled'],
    emits: ['click'],
    template: '<button :class="[\'el-button\', loading ? \'is-loading\' : \'\']" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>'
  },
  ElText: {
    name: 'ElText',
    props: ['type', 'size'],
    template: '<span class="el-text"><slot /></span>'
  }
}))

// ============ 辅助 ============

async function mountExportPanel(props: {
  analysisId?: string
  reportTitle?: string
} = {}) {
  const { default: ExportPanel } = await import(
    '@/components/report/ExportPanel.vue'
  )
  return mount(ExportPanel, {
    props: {
      analysisId: 'test-analysis-id',
      reportTitle: 'Test Report',
      ...props
    },
    global: {
      stubs: {
        'el-button': {
          template: '<button :class="[\'el-button\', $props.loading ? \'is-loading\' : \'\']" :disabled="$props.disabled" @click="$emit(\'click\')"><slot /></button>',
          props: ['type', 'loading', 'disabled'],
          emits: ['click']
        },
        'el-text': {
          template: '<span class="el-text"><slot /></span>',
          props: ['type', 'size']
        }
      }
    }
  })
}

describe('ExportPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // 默认 mock 成功
    mockExportPdf.mockResolvedValue(new Blob(['pdf content'], { type: 'application/pdf' }))
    mockExportWord.mockResolvedValue(new Blob(['word content'], { type: 'application/msword' }))
  })

  it('应渲染 PDF 和 Word 两个导出按钮', async () => {
    const wrapper = await mountExportPanel()
    const buttons = wrapper.findAll('.el-button')
    expect(buttons).toHaveLength(2)
    expect(buttons[0].text()).toContain('PDF')
    expect(buttons[1].text()).toContain('Word')
  })

  it('应显示 AI 生成免责声明', async () => {
    const wrapper = await mountExportPanel()
    expect(wrapper.find('.el-text').text()).toContain('AI 生成')
  })

  it('点击 PDF 按钮应调用 exportPdf', async () => {
    const wrapper = await mountExportPanel()
    const pdfBtn = wrapper.findAll('.el-button')[0]
    await pdfBtn.trigger('click')
    await nextTick()
    await nextTick()

    expect(mockExportPdf).toHaveBeenCalledWith('test-analysis-id')
  })

  it('点击 Word 按钮应调用 exportWord', async () => {
    const wrapper = await mountExportPanel()
    const wordBtn = wrapper.findAll('.el-button')[1]
    await wordBtn.trigger('click')
    await nextTick()
    await nextTick()

    expect(mockExportWord).toHaveBeenCalledWith('test-analysis-id')
  })

  it('导出中应禁用另一个按钮', async () => {
    vi.useFakeTimers()
    // 让 exportPdf 不 resolve
    mockExportPdf.mockImplementation(() => new Promise(() => {}))

    const wrapper = await mountExportPanel()
    const pdfBtn = wrapper.findAll('.el-button')[0]
    await pdfBtn.trigger('click')
    await nextTick()

    const buttons = wrapper.findAll('.el-button')
    expect(buttons[0].classes()).toContain('is-loading')
    expect(buttons[1].attributes('disabled')).toBeDefined()

    vi.useRealTimers()
  })

  it('导出失败应 emit export-error', async () => {
    mockExportPdf.mockRejectedValue(new Error('Network error'))

    const wrapper = await mountExportPanel()
    const pdfBtn = wrapper.findAll('.el-button')[0]
    await pdfBtn.trigger('click')
    await nextTick()
    await nextTick()

    await new Promise(r => setTimeout(r, 10))
    expect(wrapper.emitted('export-error')).toBeTruthy()
    expect(wrapper.emitted('export-error')?.[0]?.[0]).toContain('PDF')
  })
})
