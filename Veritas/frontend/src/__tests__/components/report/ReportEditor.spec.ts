/**
 * ReportEditor 组件测试
 *
 * 被测代码实际功能：
 * - v-model:modelValue 双向绑定 Markdown 文本
 * - v-model:mode 切换 edit/preview/split 三种模式
 * - 实时预览：调用 renderMarkdownWithCitations 渲染
 * - 工具栏：模式切换 + 字数统计 + 保存按钮
 *
 * 注：实际代码无"取消按钮"和"加粗/斜体/标题/列表/引用"工具栏按钮，
 *     故根据实际代码调整测试用例。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'

// ============ Mock 依赖 ============

const mockRenderMarkdownWithCitations = vi.fn((text: string) => {
  if (!text) return ''
  return `<p>rendered: ${text}</p>`
})

vi.mock('@/utils/markdown', () => ({
  renderMarkdownWithCitations: mockRenderMarkdownWithCitations
}))

vi.mock('@element-plus/icons-vue', () => ({
  Document: { name: 'Document', template: '<i class="mock-icon-document"></i>' },
  View: { name: 'View', template: '<i class="mock-icon-view"></i>' },
  Grid: { name: 'Grid', template: '<i class="mock-icon-grid"></i>' },
  Check: { name: 'Check', template: '<i class="mock-icon-check"></i>' }
}))

// Mock Element Plus：所有组件定义放在 factory 内部，避免 hoisting 问题
vi.mock('element-plus', async () => {
  const { defineComponent, provide } = await import('vue')

  const ElButton = defineComponent({
    name: 'ElButton',
    props: {
      type: { type: String, default: '' },
      size: { type: String, default: '' },
      loading: { type: Boolean, default: false },
      icon: { type: [Object, String], default: null }
    },
    emits: ['click'],
    template: '<button class="el-button" :class="{ \'is-loading\': loading }" :disabled="loading" @click="$emit(\'click\')"><slot /></button>'
  })

  const ElInput = defineComponent({
    name: 'ElInput',
    props: {
      modelValue: { type: String, default: '' },
      type: { type: String, default: '' },
      rows: { type: Number, default: 2 },
      placeholder: { type: String, default: '' },
      resize: { type: String, default: '' },
      disabled: { type: Boolean, default: false }
    },
    emits: ['update:modelValue'],
    template: '<textarea v-if="type===\'textarea\'" class="el-input el-textarea" :value="modelValue" :placeholder="placeholder" @input="$emit(\'update:modelValue\', $event.target.value)"></textarea><input v-else class="el-input" :value="modelValue" :placeholder="placeholder" @input="$emit(\'update:modelValue\', $event.target.value)" />'
  })

  const ElRadioGroup = defineComponent({
    name: 'ElRadioGroup',
    props: {
      modelValue: { type: [String, Number, Boolean], default: '' },
      size: { type: String, default: '' }
    },
    emits: ['update:modelValue'],
    setup(_props, { emit, slots }) {
      const change = (val: any) => emit('update:modelValue', val)
      provide('elRadioGroup', { change })
      return () => slots.default?.()
    }
  })

  const ElRadioButton = defineComponent({
    name: 'ElRadioButton',
    props: {
      value: { type: [String, Number, Boolean], default: '' }
    },
    inject: ['elRadioGroup'],
    template: '<label class="el-radio-button" :data-value="value" @click="elRadioGroup && elRadioGroup.change(value)"><slot /></label>'
  })

  const ElText = defineComponent({
    name: 'ElText',
    props: {
      type: { type: String, default: '' },
      size: { type: String, default: '' }
    },
    template: '<span class="el-text"><slot /></span>'
  })

  const ElIcon = defineComponent({
    name: 'ElIcon',
    template: '<i class="el-icon"><slot /></i>'
  })

  return {
    ElButton,
    ElInput,
    ElRadioGroup,
    ElRadioButton,
    ElText,
    ElIcon
  }
})

// ============ 辅助 ============

async function mountReportEditor(props: {
  modelValue?: string
  citations?: any[]
  saving?: boolean
  mode?: 'edit' | 'preview' | 'split'
} = {}) {
  const { default: ReportEditor } = await import('@/components/report/ReportEditor.vue')
  return mount(ReportEditor, {
    props: {
      modelValue: '',
      mode: 'edit',
      ...props
    } as any
  })
}

describe('ReportEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockRenderMarkdownWithCitations.mockImplementation((text: string) => {
      if (!text) return ''
      return `<p>rendered: ${text}</p>`
    })
  })

  it('默认应渲染编辑模式：显示 textarea，不显示预览', async () => {
    const wrapper = await mountReportEditor({ modelValue: '# hello' })
    expect(wrapper.find('.report-editor__edit').exists()).toBe(true)
    expect(wrapper.find('.report-editor__preview').exists()).toBe(false)
    const textarea = wrapper.find('.el-textarea')
    expect(textarea.exists()).toBe(true)
    expect((textarea.element as HTMLTextAreaElement).value).toBe('# hello')
  })

  it('编辑 textarea 输入应 emit update:modelValue', async () => {
    const wrapper = await mountReportEditor({ modelValue: '' })
    const textarea = wrapper.find('.el-textarea')
    await textarea.setValue('新的综述内容')
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')?.[0]?.[0]).toBe('新的综述内容')
  })

  it('切换到预览模式应渲染 markdown（调用 renderMarkdownWithCitations）', async () => {
    const wrapper = await mountReportEditor({ modelValue: '# 标题', mode: 'edit' })
    // 切换到预览模式：点击预览 radio button
    const previewBtn = wrapper.find('.el-radio-button[data-value="preview"]')
    expect(previewBtn.exists()).toBe(true)
    await previewBtn.trigger('click')
    await nextTick()

    // 应 emit update:mode
    expect(wrapper.emitted('update:mode')).toBeTruthy()
    expect(wrapper.emitted('update:mode')?.[0]?.[0]).toBe('preview')

    // 更新 mode prop 模拟 v-model 同步
    await wrapper.setProps({ mode: 'preview' })
    await nextTick()

    // 预览区域应显示
    const preview = wrapper.find('.report-editor__preview')
    expect(preview.exists()).toBe(true)
    // 编辑区域应隐藏
    expect(wrapper.find('.report-editor__edit').exists()).toBe(false)
    // 应调用 renderMarkdownWithCitations
    expect(mockRenderMarkdownWithCitations).toHaveBeenCalledWith('# 标题', [])
    // 预览区域应包含渲染后的 HTML
    expect(preview.html()).toContain('rendered: # 标题')
  })

  it('切换到分屏模式应同时显示编辑区和预览区', async () => {
    const wrapper = await mountReportEditor({ modelValue: '内容', mode: 'edit' })
    const splitBtn = wrapper.find('.el-radio-button[data-value="split"]')
    await splitBtn.trigger('click')
    await wrapper.setProps({ mode: 'split' })
    await nextTick()

    expect(wrapper.find('.report-editor__edit').exists()).toBe(true)
    expect(wrapper.find('.report-editor__preview').exists()).toBe(true)
    // body 应有 split class
    expect(wrapper.find('.report-editor__body--split').exists()).toBe(true)
  })

  it('点击保存按钮应 emit("save") 事件', async () => {
    const wrapper = await mountReportEditor({ modelValue: '待保存内容' })
    // 保存按钮是工具栏右侧的 el-button
    const buttons = wrapper.findAll('.el-button')
    const saveBtn = buttons.find(b => b.text().includes('保存'))
    expect(saveBtn).toBeTruthy()
    await saveBtn!.trigger('click')
    expect(wrapper.emitted('save')).toBeTruthy()
    expect(wrapper.emitted('save')?.length).toBe(1)
  })

  it('saving=true 时保存按钮应处于 loading 状态', async () => {
    const wrapper = await mountReportEditor({ modelValue: '', saving: true })
    const buttons = wrapper.findAll('.el-button')
    const saveBtn = buttons.find(b => b.text().includes('保存'))
    expect(saveBtn).toBeTruthy()
    expect(saveBtn!.classes()).toContain('is-loading')
  })

  it('字数统计应正确显示字符数和词数', async () => {
    // 纯中文："科研综述" → 4 字符，4 词（中文按字符）
    const wrapper = await mountReportEditor({ modelValue: '科研综述' })
    const text = wrapper.find('.el-text')
    expect(text.exists()).toBe(true)
    expect(text.text()).toContain('4 字符')
    expect(text.text()).toContain('4 词')
  })

  it('中英文混合内容应正确统计字数', async () => {
    // "hello 世界" → 8 字符（hello=5 + 空格=1 + 世界=2）；中文 2 词 + 英文 1 词 = 3 词
    const wrapper = await mountReportEditor({ modelValue: 'hello 世界' })
    const text = wrapper.find('.el-text')
    expect(text.text()).toContain('8 字符')
    expect(text.text()).toContain('3 词')
  })
})
