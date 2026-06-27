import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'
import type { Paper } from '@/types/paper'

// ============ Mock 基础设施 ============

const mockPaper: Paper = {
  paperId: 'p001',
  title: 'Multi-Agent Systems Survey',
  authors: ['Zhang', 'Li'],
  abstract: 'A comprehensive survey on multi-agent systems.',
  year: 2024,
  venue: 'ACL',
  keywords: ['Multi-Agent', 'LLM'],
  citationCount: 156,
  pdfUrl: 'https://example.com/paper.pdf'
}

// 使用 vi.hoisted 但不依赖 vue 的 ref（在工厂内部创建 ref）
const mocks = vi.hoisted(() => ({
  fetchDetail: vi.fn(),
  toggleFavorite: vi.fn(),
  startAnalysis: vi.fn(),
  cleanup: vi.fn(),
  routerPush: vi.fn(),
  routerBack: vi.fn(),
  elMessage: {
    error: vi.fn(),
    success: vi.fn(),
    info: vi.fn(),
    warning: vi.fn()
  },
  // 响应式状态容器（在测试 beforeEach 中初始化为 ref）
  state: null as null | {
    favorites: ReturnType<typeof ref<string[]>>
    isAnalyzing: ReturnType<typeof ref<boolean>>
    analysisError: ReturnType<typeof ref<string | null>>
    currentAnalysisId: ReturnType<typeof ref<string | null>>
    analysisResults: ReturnType<typeof ref<Map<string, unknown>>>
    analysisStatus: ReturnType<typeof ref<string>>
    profile: ReturnType<typeof ref<unknown>>
  }
}))

vi.mock('@/stores/paperStore', () => ({
  usePaperStore: vi.fn(() => ({
    get favorites() {
      return mocks.state!.favorites.value
    },
    fetchDetail: mocks.fetchDetail,
    toggleFavorite: mocks.toggleFavorite
  }))
}))

vi.mock('@/stores/sessionStore', () => ({
  useSessionStore: vi.fn(() => ({
    get isAnalyzing() {
      return mocks.state!.isAnalyzing.value
    },
    get analysisError() {
      return mocks.state!.analysisError.value
    },
    get currentAnalysisId() {
      return mocks.state!.currentAnalysisId.value
    },
    get analysisResults() {
      return mocks.state!.analysisResults.value
    },
    get analysisStatus() {
      return mocks.state!.analysisStatus.value
    },
    startAnalysis: mocks.startAnalysis,
    cleanup: mocks.cleanup
  }))
}))

vi.mock('@/stores/userStore', () => ({
  useUserStore: vi.fn(() => ({
    get profile() {
      return mocks.state!.profile.value
    },
    token: 'test-token'
  }))
}))

vi.mock('vue-router', () => ({
  useRoute: vi.fn(() => ({ params: { paperId: 'p001' }, query: {} })),
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

import PaperDetailView from '@/views/PaperDetailView.vue'

// ============ 辅助函数 ============

function mountPaperDetailView() {
  return mount(PaperDetailView, {
    global: {
      stubs: {
        'el-skeleton': { name: 'ElSkeleton', template: '<div class="el-skeleton" />', props: ['rows', 'animated'] },
        'el-page-header': {
          name: 'ElPageHeader',
          template: '<div class="el-page-header"><slot /></div>',
          props: ['title', 'content'],
          emits: ['back']
        },
        'el-card': { name: 'ElCard', template: '<div class="el-card"><slot /><slot name="header" /></div>' },
        'el-text': { name: 'ElText', template: '<span class="el-text"><slot /></span>', props: ['type', 'size'] },
        'el-tag': { name: 'ElTag', template: '<span class="el-tag"><slot /></span>', props: ['type', 'size', 'effect'] },
        'el-button': {
          name: 'ElButton',
          template:
            '<button class="el-button" @click="$emit(\'click\')"><slot /></button>',
          props: ['type', 'size', 'loading', 'disabled']
        },
        'el-icon': { name: 'ElIcon', template: '<span class="el-icon"><slot /></span>' },
        'el-empty': { name: 'ElEmpty', template: '<div class="el-empty"><slot /></div>', props: ['description'] },
        'el-alert': { name: 'ElAlert', template: '<div class="el-alert" />', props: ['type', 'title', 'showIcon'] },
        AnalysisCard: { name: 'AnalysisCard', template: '<div class="mock-analysis-card" />', props: ['analysis', 'showPlainExplanation'] },
        EmptyState: {
          name: 'EmptyState',
          template:
            '<div class="mock-empty-state"><button class="empty-action" @click="$emit(\'action\')">{{ actionText }}</button></div>',
          props: ['title', 'description', 'icon', 'actionText'],
          emits: ['action']
        },
        ErrorState: {
          name: 'ErrorState',
          template:
            '<div class="mock-error-state"><button class="retry-btn" @click="$emit(\'retry\')">重试</button></div>',
          props: ['title', 'description', 'error', 'actionText'],
          emits: ['retry']
        }
      }
    }
  })
}

// ============ 测试 ============

describe('PaperDetailView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
    // 初始化响应式状态
    mocks.state = {
      favorites: ref<string[]>([]),
      isAnalyzing: ref<boolean>(false),
      analysisError: ref<string | null>(null),
      currentAnalysisId: ref<string | null>(null),
      analysisResults: ref<Map<string, unknown>>(new Map()),
      analysisStatus: ref<string>('idle'),
      profile: ref<unknown>(null)
    }
    mocks.fetchDetail.mockResolvedValue(mockPaper)
    mocks.toggleFavorite.mockResolvedValue(undefined)
    mocks.startAnalysis.mockResolvedValue({})
  })

  it('加载详情时显示 loading 状态（el-skeleton）', async () => {
    // 让 fetchDetail 永远不 resolve，保持 loading 状态
    mocks.fetchDetail.mockReturnValue(new Promise(() => {}))
    const wrapper = mountPaperDetailView()
    await flushPromises()

    expect(wrapper.find('.el-skeleton').exists()).toBe(true)
  })

  it('详情加载成功后渲染标题、摘要、关键词', async () => {
    const wrapper = mountPaperDetailView()
    await flushPromises()

    expect(wrapper.find('.paper-detail-view__title').text()).toContain(
      'Multi-Agent Systems Survey'
    )
    expect(wrapper.find('.paper-detail-view__abstract').text()).toContain(
      'A comprehensive survey on multi-agent systems.'
    )
    // 关键词标签
    const tags = wrapper.findAll('.el-tag')
    expect(tags.length).toBeGreaterThanOrEqual(2)
  })

  it('详情加载成功后渲染作者元数据', async () => {
    const wrapper = mountPaperDetailView()
    await flushPromises()

    const meta = wrapper.find('.paper-detail-view__meta')
    expect(meta.exists()).toBe(true)
    expect(meta.text()).toContain('Zhang, Li')
    expect(meta.text()).toContain('2024')
    expect(meta.text()).toContain('ACL')
  })

  it('点击收藏按钮调用 paperStore.toggleFavorite', async () => {
    const wrapper = mountPaperDetailView()
    await flushPromises()

    const buttons = wrapper.findAll('.el-button')
    // 找到收藏按钮（包含"收藏"文字）
    const favBtn = buttons.find(b => b.text().includes('收藏'))
    expect(favBtn).toBeDefined()
    await favBtn!.trigger('click')
    await flushPromises()

    expect(mocks.toggleFavorite).toHaveBeenCalledWith('p001')
    expect(mocks.elMessage.success).toHaveBeenCalled()
  })

  it('已收藏状态显示"已收藏"按钮文案', async () => {
    mocks.state!.favorites.value = ['p001']
    const wrapper = mountPaperDetailView()
    await flushPromises()

    const buttons = wrapper.findAll('.el-button')
    const favBtn = buttons.find(b => b.text().includes('已收藏'))
    expect(favBtn).toBeDefined()
  })

  it('加载失败时显示 ErrorState 并支持重试', async () => {
    mocks.fetchDetail.mockRejectedValue(new Error('网络错误'))
    const wrapper = mountPaperDetailView()
    await flushPromises()

    expect(wrapper.find('.mock-error-state').exists()).toBe(true)

    // 重试
    mocks.fetchDetail.mockResolvedValue(mockPaper)
    await wrapper.find('.retry-btn').trigger('click')
    await flushPromises()

    expect(mocks.fetchDetail).toHaveBeenCalledTimes(2)
  })

  it('点击触发AI分析按钮调用 sessionStore.startAnalysis', async () => {
    const wrapper = mountPaperDetailView()
    await flushPromises()

    const buttons = wrapper.findAll('.el-button')
    const analyzeBtn = buttons.find(b => b.text().includes('触发AI分析'))
    expect(analyzeBtn).toBeDefined()
    await analyzeBtn!.trigger('click')
    await flushPromises()

    expect(mocks.startAnalysis).toHaveBeenCalledWith(
      'Multi-Agent Systems Survey',
      'p001'
    )
  })

  it('组件卸载时调用 sessionStore.cleanup', async () => {
    const wrapper = mountPaperDetailView()
    await flushPromises()

    wrapper.unmount()
    expect(mocks.cleanup).toHaveBeenCalled()
  })
})
