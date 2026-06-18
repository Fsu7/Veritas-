import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'
import type { Paper } from '@/types/paper'
import type { UserProfile } from '@/types/user'
import type { AnalysisResult } from '@/types/analysis'

// ============ Mock 数据 ============

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
  },
  {
    paperId: 'p002',
    title: 'LLM Reasoning Analysis',
    authors: ['Wang'],
    abstract: 'An analysis of LLM reasoning capabilities.',
    year: 2023,
    venue: 'NeurIPS',
    keywords: ['LLM'],
    score: 0.88
  }
]

const mockProfile: UserProfile = {
  educationLevel: 'master',
  researchField: 'NLP',
  knowledgeLevel: 'intermediate',
  preferredStyle: 'balanced'
}

const mockCompareResult: AnalysisResult = {
  analysisId: 'a001',
  status: 'completed',
  type: 'compare',
  degraded: false,
  result: {
    comparison: {
      table: [
        { dimension: '方法', values: ['Transformer', 'CNN'] },
        { dimension: '数据集', values: ['GLUE', 'SQuAD'] }
      ],
      summary: '两篇论文在方法和数据集上存在差异',
      conflicts: [
        {
          description: '观点冲突描述',
          possibleReason: '数据集差异',
          papers: ['p001', 'p002']
        }
      ]
    }
  }
}

const mockDegradedResult: AnalysisResult = {
  analysisId: 'a002',
  status: 'completed',
  type: 'compare',
  degraded: true,
  degradedReason: '部分 Agent 模块失败',
  result: {
    comparison: {
      table: [{ dimension: '方法', values: ['Transformer'] }],
      summary: '降级结果',
      conflicts: []
    }
  }
}

// ============ Mock 基础设施 ============

const mocks = vi.hoisted(() => ({
  // paperStore
  togglePaperSelection: vi.fn(),
  clearSelection: vi.fn(),
  routerPush: vi.fn(),
  routerBack: vi.fn(),
  elMessage: {
    error: vi.fn(),
    success: vi.fn(),
    info: vi.fn(),
    warning: vi.fn()
  },
  elMessageBoxConfirm: vi.fn().mockResolvedValue('confirm'),
  // analysisApi
  comparePapers: vi.fn(),
  generateReport: vi.fn(),
  // 响应式状态容器
  state: null as null | {
    selectedPapers: ReturnType<typeof ref<Paper[]>>
    favorites: ReturnType<typeof ref<string[]>>
    profile: ReturnType<typeof ref<UserProfile | null>>
    isLoggedIn: ReturnType<typeof ref<boolean>>
    agentStatesList: ReturnType<typeof ref<unknown[]>>
  }
}))

vi.mock('@/stores/paperStore', () => ({
  usePaperStore: vi.fn(() => ({
    get selectedPapers() {
      return mocks.state!.selectedPapers.value
    },
    get selectedPaperIds() {
      return (mocks.state!.selectedPapers as { value: Paper[] }).value.map(p => p.paperId)
    },
    get favorites() {
      return mocks.state!.favorites.value
    },
    get canCompare() {
      const len = (mocks.state!.selectedPapers as { value: Paper[] }).value.length
      return len >= 2 && len <= 5
    },
    togglePaperSelection: mocks.togglePaperSelection,
    clearSelection: mocks.clearSelection
  }))
}))

vi.mock('@/stores/userStore', () => ({
  useUserStore: vi.fn(() => ({
    get isLoggedIn() {
      return mocks.state!.isLoggedIn.value
    },
    get hasProfile() {
      return mocks.state!.profile.value !== null
    },
    get profile() {
      return mocks.state!.profile.value
    }
  }))
}))

vi.mock('@/stores/agentStore', () => ({
  useAgentStore: vi.fn(() => ({
    get agentStatesList() {
      return mocks.state!.agentStatesList.value
    }
  }))
}))

vi.mock('@/api/analysis', () => ({
  analysisApi: {
    comparePapers: mocks.comparePapers,
    generateReport: mocks.generateReport,
    getResult: vi.fn(),
    saveReportContent: vi.fn(),
    exportPdf: vi.fn(),
    exportWord: vi.fn()
  }
}))

vi.mock('vue-router', () => ({
  useRoute: vi.fn(() => ({ params: {}, query: {} })),
  useRouter: vi.fn(() => ({ push: mocks.routerPush, back: mocks.routerBack }))
}))

vi.mock('element-plus', async (importOriginal) => {
  const actual = await importOriginal() as Record<string, unknown>
  return {
    ...actual,
    ElMessage: mocks.elMessage,
    ElMessageBox: { confirm: mocks.elMessageBoxConfirm }
  }
})

// 桩掉子组件
vi.mock('@/components/paper/PaperCard.vue', () => ({
  default: {
    name: 'PaperCard',
    props: ['paper', 'selectable', 'selected', 'isFavorited'],
    emits: ['toggle-select', 'select', 'favorite', 'analyze'],
    template: '<div class="mock-paper-card">{{ paper.title }}</div>'
  }
}))

vi.mock('@/components/common/EmptyState.vue', () => ({
  default: {
    name: 'EmptyState',
    props: ['title', 'description', 'icon', 'actionText'],
    emits: ['action'],
    template:
      '<div class="mock-empty-state"><button class="empty-action" @click="$emit(\'action\')">{{ actionText }}</button></div>'
  }
}))

import CompareView from '@/views/CompareView.vue'

// ============ 辅助函数 ============

function mountCompareView() {
  return mount(CompareView, {
    global: {
      stubs: {
        'el-page-header': {
          name: 'ElPageHeader',
          template: '<div class="el-page-header"><slot /></div>',
          props: ['title', 'content'],
          emits: ['back']
        },
        'el-card': { name: 'ElCard', template: '<div class="el-card"><slot name="header" /><slot /></div>', props: ['shadow'] },
        'el-button': {
          name: 'ElButton',
          template: '<button class="el-button" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
          props: ['type', 'size', 'loading', 'disabled'],
          emits: ['click']
        },
        'el-text': { name: 'ElText', template: '<span class="el-text"><slot /></span>', props: ['type', 'size', 'tag'] },
        'el-alert': {
          name: 'ElAlert',
          template: '<div class="el-alert"><slot name="title" /><slot /></div>',
          props: ['type', 'title', 'showIcon', 'closable']
        },
        'el-tag': { name: 'ElTag', template: '<span class="el-tag"><slot /></span>', props: ['type', 'size'] },
        'el-table': { name: 'ElTable', template: '<div class="el-table"><slot /></div>', props: ['data', 'border', 'stripe'] },
        'el-table-column': { name: 'ElTableColumn', template: '<div class="el-table-column" />', props: ['prop', 'label', 'minWidth', 'fixed'] }
      },
      directives: {
        loading: {
          mounted() {},
          updated() {}
        }
      }
    }
  })
}

// ============ 测试 ============

describe('CompareView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
    mocks.state = {
      selectedPapers: ref<Paper[]>([]),
      favorites: ref<string[]>([]),
      profile: ref<UserProfile | null>(mockProfile),
      isLoggedIn: ref<boolean>(true),
      agentStatesList: ref<unknown[]>([])
    }
    mocks.comparePapers.mockResolvedValue(mockCompareResult)
    mocks.generateReport.mockResolvedValue({ analysisId: 'a003' })
    mocks.elMessageBoxConfirm.mockResolvedValue('confirm')
  })

  it('未登录点击对比弹出登录确认框并跳转 Login', async () => {
    mocks.state!.isLoggedIn.value = false
    mocks.state!.selectedPapers.value = mockPapers
    const wrapper = mountCompareView()
    await flushPromises()

    const buttons = wrapper.findAll('.el-button')
    const compareBtn = buttons.find(b => b.text().includes('开始对比'))
    expect(compareBtn).toBeDefined()
    await compareBtn!.trigger('click')
    await flushPromises()

    expect(mocks.elMessageBoxConfirm).toHaveBeenCalledWith(
      '请先登录后再使用对比功能',
      '提示',
      expect.objectContaining({ confirmButtonText: '去登录' })
    )
    expect(mocks.routerPush).toHaveBeenCalledWith({ name: 'Login' })
  })

  it('未设置画像弹出画像确认框，确认后跳转 UserCenter', async () => {
    mocks.state!.profile.value = null
    mocks.state!.selectedPapers.value = mockPapers
    const wrapper = mountCompareView()
    await flushPromises()

    const buttons = wrapper.findAll('.el-button')
    const compareBtn = buttons.find(b => b.text().includes('开始对比'))
    await compareBtn!.trigger('click')
    await flushPromises()

    expect(mocks.elMessageBoxConfirm).toHaveBeenCalledWith(
      '建议先完善用户画像以获得更精准的对比结果',
      '提示',
      expect.objectContaining({ confirmButtonText: '去设置' })
    )
    expect(mocks.routerPush).toHaveBeenCalledWith({ name: 'UserCenter' })
  })

  it('未设置画像但选择"继续对比"时调用 doCompare', async () => {
    mocks.state!.profile.value = null
    mocks.state!.selectedPapers.value = mockPapers
    // 用户取消（点"继续对比"）→ catch 分支调用 doCompare
    mocks.elMessageBoxConfirm.mockRejectedValueOnce('cancel')
    const wrapper = mountCompareView()
    await flushPromises()

    const buttons = wrapper.findAll('.el-button')
    const compareBtn = buttons.find(b => b.text().includes('开始对比'))
    await compareBtn!.trigger('click')
    await flushPromises()

    expect(mocks.comparePapers).toHaveBeenCalledWith({ paperIds: ['p001', 'p002'] })
    expect(mocks.elMessage.success).toHaveBeenCalledWith('对比分析完成')
  })

  it('对比结果展示：渲染对比表格与总结', async () => {
    mocks.state!.selectedPapers.value = mockPapers
    mocks.comparePapers.mockResolvedValue(mockCompareResult)
    const wrapper = mountCompareView()
    await flushPromises()

    const buttons = wrapper.findAll('.el-button')
    const compareBtn = buttons.find(b => b.text().includes('开始对比'))
    await compareBtn!.trigger('click')
    await flushPromises()

    // 对比结果卡片存在
    expect(wrapper.find('.compare-view__result').exists()).toBe(true)
    // 冲突提示存在
    expect(wrapper.find('.compare-view__conflicts').exists()).toBe(true)
    // 总结存在
    expect(wrapper.find('.compare-view__summary').exists()).toBe(true)
    expect(wrapper.find('.compare-view__summary').text()).toContain('两篇论文在方法和数据集上存在差异')
  })

  it('降级提示（resultDegraded=true）显示 el-alert', async () => {
    mocks.state!.selectedPapers.value = mockPapers
    mocks.comparePapers.mockResolvedValue(mockDegradedResult)
    const wrapper = mountCompareView()
    await flushPromises()

    const buttons = wrapper.findAll('.el-button')
    const compareBtn = buttons.find(b => b.text().includes('开始对比'))
    await compareBtn!.trigger('click')
    await flushPromises()

    expect(wrapper.find('.compare-view__degraded').exists()).toBe(true)
    expect(wrapper.find('.compare-view__degraded').text()).toContain('部分降级')
    expect(wrapper.find('.compare-view__degraded').text()).toContain('部分 Agent 模块失败')
  })

  it('对比分析失败时 ElMessage.error 提示', async () => {
    mocks.state!.selectedPapers.value = mockPapers
    mocks.comparePapers.mockRejectedValue(new Error('对比服务不可用'))
    const wrapper = mountCompareView()
    await flushPromises()

    const buttons = wrapper.findAll('.el-button')
    const compareBtn = buttons.find(b => b.text().includes('开始对比'))
    await compareBtn!.trigger('click')
    await flushPromises()

    expect(mocks.elMessage.error).toHaveBeenCalledWith('对比服务不可用')
  })

  it('已登录已设置画像直接调用 doCompare', async () => {
    mocks.state!.selectedPapers.value = mockPapers
    const wrapper = mountCompareView()
    await flushPromises()

    const buttons = wrapper.findAll('.el-button')
    const compareBtn = buttons.find(b => b.text().includes('开始对比'))
    await compareBtn!.trigger('click')
    await flushPromises()

    expect(mocks.elMessageBoxConfirm).not.toHaveBeenCalled()
    expect(mocks.comparePapers).toHaveBeenCalledWith({ paperIds: ['p001', 'p002'] })
  })

  it('点击"生成综述"调用 generateReport 并跳转 Report', async () => {
    mocks.state!.selectedPapers.value = mockPapers
    mocks.comparePapers.mockResolvedValue(mockCompareResult)
    const wrapper = mountCompareView()
    await flushPromises()

    // 先完成对比
    const buttons = wrapper.findAll('.el-button')
    const compareBtn = buttons.find(b => b.text().includes('开始对比'))
    await compareBtn!.trigger('click')
    await flushPromises()

    // 点击生成综述
    const buttons2 = wrapper.findAll('.el-button')
    const reportBtn = buttons2.find(b => b.text().includes('生成综述'))
    expect(reportBtn).toBeDefined()
    await reportBtn!.trigger('click')
    await flushPromises()

    expect(mocks.generateReport).toHaveBeenCalledWith(expect.objectContaining({
      paperIds: ['p001', 'p002'],
      profile: mockProfile
    }))
    expect(mocks.routerPush).toHaveBeenCalledWith({ name: 'Report', params: { analysisId: 'a003' } })
  })

  it('未选论文时显示 EmptyState', async () => {
    mocks.state!.selectedPapers.value = []
    const wrapper = mountCompareView()
    await flushPromises()

    expect(wrapper.find('.mock-empty-state').exists()).toBe(true)
  })

  it('点击"清空选择"调用 paperStore.clearSelection', async () => {
    mocks.state!.selectedPapers.value = mockPapers
    const wrapper = mountCompareView()
    await flushPromises()

    const buttons = wrapper.findAll('.el-button')
    const clearBtn = buttons.find(b => b.text().includes('清空选择'))
    expect(clearBtn).toBeDefined()
    await clearBtn!.trigger('click')
    await flushPromises()

    expect(mocks.clearSelection).toHaveBeenCalled()
  })

  it('点击"前往检索"跳转 Search', async () => {
    mocks.state!.selectedPapers.value = mockPapers
    const wrapper = mountCompareView()
    await flushPromises()

    const buttons = wrapper.findAll('.el-button')
    const searchBtn = buttons.find(b => b.text().includes('前往检索'))
    expect(searchBtn).toBeDefined()
    await searchBtn!.trigger('click')

    expect(mocks.routerPush).toHaveBeenCalledWith({ name: 'Search' })
  })

  it('挂载时未选论文弹出前往检索确认框', async () => {
    mocks.state!.selectedPapers.value = []
    mountCompareView()
    await flushPromises()

    expect(mocks.elMessageBoxConfirm).toHaveBeenCalledWith(
      '尚未选择论文，是否前往检索？',
      '提示',
      expect.objectContaining({ confirmButtonText: '去检索' })
    )
  })
})
