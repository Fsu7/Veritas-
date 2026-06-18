import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'
import type { AnalysisResult, Citation } from '@/types/analysis'
import type { UserProfile } from '@/types/user'
import type { Paper } from '@/types/paper'

// ============ Mock 数据 ============

const mockCitations: Citation[] = [
  {
    paperId: 'p001',
    text: '[Zhang, 2024] 提出了一种新的多智能体框架',
    location: 'Section 3.2'
  }
]

const mockReportText = '本文综述了多智能体系统的发展。[Zhang, 2024] 提出了一种新的多智能体框架。'

const mockAnalysisResult: AnalysisResult = {
  analysisId: 'a001',
  status: 'completed',
  type: 'report',
  degraded: false,
  result: {
    report: mockReportText,
    citations: mockCitations,
    analysis: {
      researchQuestion: '多智能体系统的发展现状',
      coreMethod: 'Transformer',
      keyExperiments: 'GLUE',
      coreFindings: '显著提升',
      limitations: '数据集有限'
    }
  }
}

const mockProfile: UserProfile = {
  educationLevel: 'master',
  researchField: 'NLP',
  knowledgeLevel: 'intermediate',
  preferredStyle: 'balanced'
}

const mockPapers: Paper[] = [
  {
    paperId: 'p001',
    title: 'Multi-Agent Systems Survey',
    authors: ['Zhang', 'Li'],
    abstract: 'A comprehensive survey on multi-agent systems.',
    year: 2024,
    venue: 'ACL',
    keywords: ['Multi-Agent'],
    score: 0.95
  }
]

// ============ Mock 基础设施 ============

const mocks = vi.hoisted(() => ({
  // sessionStore
  fetchAnalysisResult: vi.fn(),
  // analysisApi
  saveReportContent: vi.fn(),
  exportPdf: vi.fn(),
  exportWord: vi.fn(),
  getResult: vi.fn(),
  // router
  routerPush: vi.fn(),
  routerBack: vi.fn(),
  // utils
  renderMarkdown: vi.fn((text: string) => `<p>${text}</p>`),
  splitReportSegments: vi.fn(),
  extractCitationData: vi.fn(),
  formatDate: vi.fn((v: string) => v || ''),
  // elMessage
  elMessage: {
    error: vi.fn(),
    success: vi.fn(),
    info: vi.fn(),
    warning: vi.fn()
  },
  // 路由参数
  routeParams: { analysisId: 'a001' } as Record<string, string>,
  // 响应式状态
  state: null as null | {
    profile: ReturnType<typeof ref<UserProfile | null>>
    searchResults: ReturnType<typeof ref<Paper[]>>
  }
}))

vi.mock('@/stores/sessionStore', () => ({
  useSessionStore: vi.fn(() => ({
    fetchAnalysisResult: mocks.fetchAnalysisResult
  }))
}))

vi.mock('@/stores/userStore', () => ({
  useUserStore: vi.fn(() => ({
    get profile() {
      return mocks.state!.profile.value
    }
  }))
}))

vi.mock('@/stores/paperStore', () => ({
  usePaperStore: vi.fn(() => ({
    get searchResults() {
      return mocks.state!.searchResults.value
    }
  }))
}))

vi.mock('@/api/analysis', () => ({
  analysisApi: {
    getResult: mocks.getResult,
    saveReportContent: mocks.saveReportContent,
    exportPdf: mocks.exportPdf,
    exportWord: mocks.exportWord,
    comparePapers: vi.fn(),
    generateReport: vi.fn()
  }
}))

vi.mock('@/utils/markdown', () => ({
  renderMarkdown: mocks.renderMarkdown,
  renderMarkdownWithCitations: vi.fn((text: string) => `<p>${text}</p>`)
}))

vi.mock('@/utils/citation', () => ({
  splitReportSegments: mocks.splitReportSegments,
  extractCitationData: mocks.extractCitationData
}))

vi.mock('@/utils/format', () => ({
  formatDate: mocks.formatDate
}))

vi.mock('vue-router', () => ({
  useRoute: vi.fn(() => ({
    get params() {
      return mocks.routeParams
    },
    query: {}
  })),
  useRouter: vi.fn(() => ({ push: mocks.routerPush, back: mocks.routerBack }))
}))

vi.mock('element-plus', async (importOriginal) => {
  const actual = await importOriginal() as Record<string, unknown>
  return {
    ...actual,
    ElMessage: mocks.elMessage,
    ElMessageBox: { confirm: vi.fn().mockResolvedValue('confirm') }
  }
})

// 桩掉子组件
vi.mock('@/components/report/ExportPanel.vue', () => ({
  default: {
    name: 'ExportPanel',
    props: ['analysisId', 'reportTitle', 'customContent'],
    emits: ['export-success', 'export-error'],
    template: '<div class="mock-export-panel" :data-analysis-id="analysisId">{{ reportTitle }}</div>'
  }
}))

vi.mock('@/components/report/CitationLink.vue', () => ({
  default: {
    name: 'CitationLink',
    props: ['visible', 'citation'],
    emits: ['update:visible', 'go-detail'],
    template: '<div class="mock-citation-link" v-if="visible" />'
  }
}))

vi.mock('@/components/report/ReportEditor.vue', () => ({
  default: {
    name: 'ReportEditor',
    props: ['modelValue', 'mode', 'citations', 'saving'],
    emits: ['update:modelValue', 'update:mode', 'save'],
    template:
      '<div class="mock-report-editor"><button class="save-btn" @click="$emit(\'save\')">保存</button></div>'
  }
}))

vi.mock('@/components/common/EmptyState.vue', () => ({
  default: {
    name: 'EmptyState',
    props: ['title', 'description', 'icon', 'actionText'],
    emits: ['action'],
    template: '<div class="mock-empty-state"><button class="action-btn" @click="$emit(\'action\')">{{ actionText }}</button></div>'
  }
}))

vi.mock('@/components/common/ErrorState.vue', () => ({
  default: {
    name: 'ErrorState',
    props: ['title', 'description', 'error', 'actionText'],
    emits: ['retry'],
    template: '<div class="mock-error-state"><button class="retry-btn" @click="$emit(\'retry\')">重试</button></div>'
  }
}))

import ReportView from '@/views/ReportView.vue'

// ============ 辅助函数 ============

function mountReportView() {
  return mount(ReportView, {
    global: {
      stubs: {
        'el-page-header': {
          name: 'ElPageHeader',
          template: '<div class="el-page-header"><slot /></div>',
          props: ['title', 'content'],
          emits: ['back']
        },
        'el-skeleton': { name: 'ElSkeleton', template: '<div class="el-skeleton" />', props: ['rows', 'animated'] },
        'el-card': { name: 'ElCard', template: '<div class="el-card"><slot name="header" /><slot /></div>', props: ['shadow'] },
        'el-descriptions': { name: 'ElDescriptions', template: '<div class="el-descriptions"><slot /></div>', props: ['column', 'border'] },
        'el-descriptions-item': { name: 'ElDescriptionsItem', template: '<div class="el-descriptions-item"><slot /></div>', props: ['label'] },
        'el-tag': { name: 'ElTag', template: '<span class="el-tag"><slot /></span>', props: ['type', 'size', 'effect'] },
        'el-text': { name: 'ElText', template: '<span class="el-text"><slot /></span>', props: ['type', 'size'] },
        'el-button': {
          name: 'ElButton',
          template: '<button class="el-button" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
          props: ['type', 'size', 'loading', 'disabled', 'icon'],
          emits: ['click']
        },
        'el-icon': { name: 'ElIcon', template: '<span class="el-icon"><slot /></span>' },
        'el-link': {
          name: 'ElLink',
          template: '<a class="el-link" :disabled="disabled" @click="$emit(\'click\')"><slot /></a>',
          props: ['type', 'underline', 'disabled'],
          emits: ['click']
        },
        'el-empty': { name: 'ElEmpty', template: '<div class="el-empty" />', props: ['description'] }
      }
    }
  })
}

// ============ 测试 ============

describe('ReportView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
    mocks.state = {
      profile: ref<UserProfile | null>(mockProfile),
      searchResults: ref<Paper[]>(mockPapers)
    }
    mocks.routeParams = { analysisId: 'a001' }
    mocks.fetchAnalysisResult.mockResolvedValue(mockAnalysisResult)
    mocks.saveReportContent.mockResolvedValue(undefined)
    mocks.exportPdf.mockResolvedValue(new Blob(['pdf'], { type: 'application/pdf' }))
    mocks.exportWord.mockResolvedValue(new Blob(['word'], { type: 'application/msword' }))
    mocks.renderMarkdown.mockImplementation((text: string) => `<p>${text}</p>`)
    mocks.splitReportSegments.mockImplementation((text: string) => {
      // 简化分段：返回纯文本片段
      return [{ type: 'text', value: text }]
    })
    mocks.extractCitationData.mockImplementation((_raw, _citations, _papers) => ({
      paperId: 'p001',
      title: 'Multi-Agent Systems Survey',
      authors: ['Zhang', 'Li'],
      year: 2024,
      text: '[Zhang, 2024] 提出了一种新的多智能体框架',
      venue: 'ACL'
    }))
    mocks.formatDate.mockImplementation((v: string) => v || '')
  })

  it('报告加载时显示 loading 状态（el-skeleton）', async () => {
    // 让 fetchAnalysisResult 永不 resolve，保持 loading
    mocks.fetchAnalysisResult.mockReturnValue(new Promise(() => {}))
    const wrapper = mountReportView()
    await flushPromises()

    expect(wrapper.find('.el-skeleton').exists()).toBe(true)
  })

  it('报告加载完成后渲染 markdown 内容', async () => {
    const wrapper = mountReportView()
    await flushPromises()

    // 综述内容卡片存在
    expect(wrapper.find('.report-view__content').exists()).toBe(true)
    // renderMarkdown 被调用
    expect(mocks.renderMarkdown).toHaveBeenCalledWith(mockReportText)
    // markdown-body 存在
    expect(wrapper.find('.report-view__markdown').exists()).toBe(true)
  })

  it('报告加载完成后渲染标题', async () => {
    const wrapper = mountReportView()
    await flushPromises()

    expect(wrapper.find('.report-view__title').text()).toContain('多智能体系统的发展现状')
  })

  it('加载失败时显示 ErrorState 并支持重试', async () => {
    mocks.fetchAnalysisResult.mockRejectedValue(new Error('网络错误'))
    const wrapper = mountReportView()
    await flushPromises()

    expect(wrapper.find('.mock-error-state').exists()).toBe(true)

    // 重试
    mocks.fetchAnalysisResult.mockResolvedValue(mockAnalysisResult)
    await wrapper.find('.retry-btn').trigger('click')
    await flushPromises()

    expect(mocks.fetchAnalysisResult).toHaveBeenCalledTimes(2)
  })

  it('编辑模式切换：点击"编辑综述"进入编辑模式', async () => {
    const wrapper = mountReportView()
    await flushPromises()

    const buttons = wrapper.findAll('.el-button')
    const editBtn = buttons.find(b => b.text().includes('编辑综述'))
    expect(editBtn).toBeDefined()
    await editBtn!.trigger('click')
    await flushPromises()

    // 进入编辑模式后应渲染 ReportEditor
    expect(wrapper.find('.mock-report-editor').exists()).toBe(true)
    // 按钮文案变为"完成编辑"
    const buttons2 = wrapper.findAll('.el-button')
    const exitBtn = buttons2.find(b => b.text().includes('完成编辑'))
    expect(exitBtn).toBeDefined()
  })

  it('编辑模式切换：点击"完成编辑"退出编辑模式', async () => {
    const wrapper = mountReportView()
    await flushPromises()

    // 进入编辑模式
    const buttons = wrapper.findAll('.el-button')
    const editBtn = buttons.find(b => b.text().includes('编辑综述'))
    await editBtn!.trigger('click')
    await flushPromises()

    // 退出编辑模式
    const buttons2 = wrapper.findAll('.el-button')
    const exitBtn = buttons2.find(b => b.text().includes('完成编辑'))
    await exitBtn!.trigger('click')
    await flushPromises()

    expect(wrapper.find('.mock-report-editor').exists()).toBe(false)
  })

  it('编辑模式下点击保存按钮调用 analysisApi.saveReportContent', async () => {
    const wrapper = mountReportView()
    await flushPromises()

    // 进入编辑模式
    const buttons = wrapper.findAll('.el-button')
    const editBtn = buttons.find(b => b.text().includes('编辑综述'))
    await editBtn!.trigger('click')
    await flushPromises()

    // 点击保存
    const saveBtn = wrapper.find('.mock-report-editor .save-btn')
    await saveBtn.trigger('click')
    await flushPromises()

    expect(mocks.saveReportContent).toHaveBeenCalledWith('a001', mockReportText)
    expect(mocks.elMessage.success).toHaveBeenCalledWith('综述内容保存成功')
  })

  it('保存失败时 ElMessage.error 提示', async () => {
    mocks.saveReportContent.mockRejectedValue(new Error('保存失败'))
    const wrapper = mountReportView()
    await flushPromises()

    // 进入编辑模式
    const buttons = wrapper.findAll('.el-button')
    const editBtn = buttons.find(b => b.text().includes('编辑综述'))
    await editBtn!.trigger('click')
    await flushPromises()

    // 点击保存
    const saveBtn = wrapper.find('.mock-report-editor .save-btn')
    await saveBtn.trigger('click')
    await flushPromises()

    expect(mocks.elMessage.error).toHaveBeenCalledWith('保存失败：保存失败')
  })

  it('导出按钮调用 ExportPanel 组件', async () => {
    const wrapper = mountReportView()
    await flushPromises()

    // ExportPanel 应被渲染，并接收正确的 props
    const exportPanel = wrapper.find('.mock-export-panel')
    expect(exportPanel.exists()).toBe(true)
    expect(exportPanel.attributes('data-analysis-id')).toBe('a001')
    expect(exportPanel.text()).toContain('多智能体系统的发展现状')
  })

  it('引用点击弹窗：点击引用链接触发 handleCitationClick', async () => {
    // 让 splitReportSegments 返回一个 citation 片段
    mocks.splitReportSegments.mockImplementation(() => [
      {
        type: 'citation',
        value: '[Zhang, 2024]',
        paperId: 'p001',
        authors: 'Zhang',
        year: '2024'
      }
    ])
    const wrapper = mountReportView()
    await flushPromises()

    // 点击引用链接
    const citationLink = wrapper.find('.report-view__citation')
    expect(citationLink.exists()).toBe(true)
    await citationLink.trigger('click')
    await flushPromises()

    // extractCitationData 被调用
    expect(mocks.extractCitationData).toHaveBeenCalled()
    // 弹窗显示
    expect(wrapper.find('.mock-citation-link').exists()).toBe(true)
  })

  it('引用点击无 paperId 时不弹窗', async () => {
    mocks.splitReportSegments.mockImplementation(() => [
      {
        type: 'citation',
        value: '[Unknown, 2020]',
        paperId: undefined,
        authors: 'Unknown',
        year: '2020'
      }
    ])
    const wrapper = mountReportView()
    await flushPromises()

    const citationLink = wrapper.find('.report-view__citation')
    await citationLink.trigger('click')
    await flushPromises()

    // 弹窗不显示
    expect(wrapper.find('.mock-citation-link').exists()).toBe(false)
  })

  it('引用信息不可用时 ElMessage.info 提示', async () => {
    mocks.splitReportSegments.mockImplementation(() => [
      {
        type: 'citation',
        value: '[Zhang, 2024]',
        paperId: 'p001',
        authors: 'Zhang',
        year: '2024'
      }
    ])
    mocks.extractCitationData.mockReturnValue(null)
    const wrapper = mountReportView()
    await flushPromises()

    const citationLink = wrapper.find('.report-view__citation')
    await citationLink.trigger('click')
    await flushPromises()

    expect(mocks.elMessage.info).toHaveBeenCalledWith('引用信息不可用')
  })

  it('复制 Markdown 调用 navigator.clipboard.writeText', async () => {
    const writeTextSpy = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: writeTextSpy },
      configurable: true
    })
    const wrapper = mountReportView()
    await flushPromises()

    const buttons = wrapper.findAll('.el-button')
    const copyBtn = buttons.find(b => b.text().includes('复制 Markdown'))
    expect(copyBtn).toBeDefined()
    await copyBtn!.trigger('click')
    await flushPromises()

    expect(writeTextSpy).toHaveBeenCalledWith(mockReportText)
    expect(mocks.elMessage.success).toHaveBeenCalledWith('已复制 Markdown 源文')
  })

  it('查看 Agent 协同过程跳转 AgentFlow', async () => {
    const wrapper = mountReportView()
    await flushPromises()

    const buttons = wrapper.findAll('.el-button')
    const agentBtn = buttons.find(b => b.text().includes('查看 Agent 协同过程'))
    expect(agentBtn).toBeDefined()
    await agentBtn!.trigger('click')

    expect(mocks.routerPush).toHaveBeenCalledWith({ name: 'AgentFlow', params: { analysisId: 'a001' } })
  })

  it('降级报告显示降级标签', async () => {
    mocks.fetchAnalysisResult.mockResolvedValue({
      ...mockAnalysisResult,
      degraded: true,
      degradedReason: '部分 Agent 失败'
    })
    const wrapper = mountReportView()
    await flushPromises()

    expect(wrapper.find('.report-view__degraded-reason').exists()).toBe(true)
    expect(wrapper.find('.report-view__degraded-reason').text()).toContain('部分 Agent 失败')
  })

  it('analysisId 缺失时显示错误状态', async () => {
    mocks.routeParams = {}
    const wrapper = mountReportView()
    await flushPromises()

    expect(wrapper.find('.mock-error-state').exists()).toBe(true)
  })
})
