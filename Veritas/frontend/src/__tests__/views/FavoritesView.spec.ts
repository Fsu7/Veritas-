import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'
import type { Paper } from '@/types/paper'

// ============ Mock 基础设施 ============

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

// 使用 vi.hoisted 但不依赖 vue 的 ref（在 beforeEach 中初始化）
const mocks = vi.hoisted(() => ({
  fetchFavorites: vi.fn(),
  toggleFavorite: vi.fn(),
  routerPush: vi.fn(),
  elMessage: {
    error: vi.fn(),
    success: vi.fn(),
    info: vi.fn(),
    warning: vi.fn()
  },
  state: null as null | {
    favoritesList: ReturnType<typeof ref<Paper[]>>
    favoritesTotal: ReturnType<typeof ref<number>>
    favoritesLoading: ReturnType<typeof ref<boolean>>
    favoritesError: ReturnType<typeof ref<string | null>>
  }
}))

vi.mock('@/stores/paperStore', () => ({
  usePaperStore: vi.fn(() => ({
    get favoritesList() {
      return mocks.state!.favoritesList.value
    },
    get favoritesTotal() {
      return mocks.state!.favoritesTotal.value
    },
    get favoritesLoading() {
      return mocks.state!.favoritesLoading.value
    },
    get favoritesError() {
      return mocks.state!.favoritesError.value
    },
    fetchFavorites: mocks.fetchFavorites,
    toggleFavorite: mocks.toggleFavorite
  }))
}))

vi.mock('vue-router', () => ({
  useRoute: vi.fn(() => ({ params: {}, query: {} })),
  useRouter: vi.fn(() => ({ push: mocks.routerPush, back: vi.fn() }))
}))

vi.mock('element-plus', async (importOriginal) => {
  const actual = await importOriginal() as Record<string, unknown>
  return {
    ...actual,
    ElMessage: mocks.elMessage,
    ElMessageBox: { confirm: vi.fn().mockResolvedValue('confirm') }
  }
})

import FavoritesView from '@/views/FavoritesView.vue'

// ============ 辅助函数 ============

function mountFavoritesView() {
  return mount(FavoritesView, {
    global: {
      stubs: {
        'el-tag': { name: 'ElTag', template: '<span class="el-tag"><slot /></span>', props: ['type', 'size', 'effect'] },
        'el-alert': { name: 'ElAlert', template: '<div class="el-alert" />', props: ['title', 'type', 'showIcon', 'closable'] },
        'el-row': { name: 'ElRow', template: '<div class="el-row"><slot /></div>', props: ['gutter'] },
        'el-col': { name: 'ElCol', template: '<div class="el-col"><slot /></div>', props: ['xs', 'sm', 'md', 'lg'] },
        'el-pagination': {
          name: 'ElPagination',
          template: '<div class="el-pagination" />',
          props: ['currentPage', 'pageSize', 'total', 'layout', 'background'],
          emits: ['update:currentPage', 'currentChange']
        },
        PaperCard: {
          name: 'PaperCard',
          template:
            '<div class="mock-paper-card" @click="$emit(\'select\', paper.paperId)"><button class="fav-btn" @click.stop="$emit(\'favorite\', paper.paperId)">收藏</button></div>',
          props: ['paper', 'isFavorited'],
          emits: ['select', 'favorite']
        },
        EmptyState: {
          name: 'EmptyState',
          template:
            '<div class="mock-empty-state"><button class="empty-action" @click="$emit(\'action\')">{{ actionText }}</button></div>',
          props: ['title', 'description', 'icon', 'actionText'],
          emits: ['action']
        }
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

describe('FavoritesView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
    mocks.state = {
      favoritesList: ref<Paper[]>([]),
      favoritesTotal: ref<number>(0),
      favoritesLoading: ref<boolean>(false),
      favoritesError: ref<string | null>(null)
    }
    mocks.fetchFavorites.mockResolvedValue(undefined)
    mocks.toggleFavorite.mockResolvedValue(undefined)
  })

  it('挂载时调用 paperStore.fetchFavorites 加载收藏列表', async () => {
    mountFavoritesView()
    await flushPromises()

    expect(mocks.fetchFavorites).toHaveBeenCalledWith(1, 10)
  })

  it('收藏列表非空时渲染 PaperCard 列表', async () => {
    mocks.state!.favoritesList.value = mockPapers
    mocks.state!.favoritesTotal.value = mockPapers.length
    const wrapper = mountFavoritesView()
    await flushPromises()

    const cards = wrapper.findAll('.mock-paper-card')
    expect(cards.length).toBe(2)
  })

  it('渲染收藏总数标签', async () => {
    mocks.state!.favoritesList.value = mockPapers
    mocks.state!.favoritesTotal.value = 2
    const wrapper = mountFavoritesView()
    await flushPromises()

    expect(wrapper.find('.favorites-view__title').text()).toContain('我的收藏')
    const tag = wrapper.find('.el-tag')
    expect(tag.text()).toContain('共 2 篇')
  })

  it('收藏列表为空时展示 EmptyState', async () => {
    mocks.state!.favoritesList.value = []
    mocks.state!.favoritesTotal.value = 0
    const wrapper = mountFavoritesView()
    await flushPromises()

    expect(wrapper.find('.mock-empty-state').exists()).toBe(true)
    expect(wrapper.find('.empty-action').text()).toContain('去搜索论文')
  })

  it('点击 EmptyState 操作按钮跳转到搜索页', async () => {
    mocks.state!.favoritesList.value = []
    mocks.state!.favoritesTotal.value = 0
    const wrapper = mountFavoritesView()
    await flushPromises()

    await wrapper.find('.empty-action').trigger('click')

    expect(mocks.routerPush).toHaveBeenCalledWith('/search')
  })

  it('点击 PaperCard 触发 select 跳转到论文详情', async () => {
    mocks.state!.favoritesList.value = mockPapers
    mocks.state!.favoritesTotal.value = mockPapers.length
    const wrapper = mountFavoritesView()
    await flushPromises()

    await wrapper.find('.mock-paper-card').trigger('click')

    expect(mocks.routerPush).toHaveBeenCalledWith('/paper/p001')
  })

  it('点击收藏按钮调用 toggleFavorite 并重新加载列表', async () => {
    mocks.state!.favoritesList.value = mockPapers
    mocks.state!.favoritesTotal.value = mockPapers.length
    const wrapper = mountFavoritesView()
    await flushPromises()

    mocks.fetchFavorites.mockClear()
    await wrapper.find('.fav-btn').trigger('click')
    await flushPromises()

    expect(mocks.toggleFavorite).toHaveBeenCalledWith('p001')
    expect(mocks.elMessage.success).toHaveBeenCalledWith('已取消收藏')
    expect(mocks.fetchFavorites).toHaveBeenCalled()
  })

  it('toggleFavorite 失败时 ElMessage.error 提示', async () => {
    mocks.state!.favoritesList.value = mockPapers
    mocks.state!.favoritesTotal.value = mockPapers.length
    mocks.toggleFavorite.mockRejectedValue(new Error('操作失败'))
    const wrapper = mountFavoritesView()
    await flushPromises()

    await wrapper.find('.fav-btn').trigger('click')
    await flushPromises()

    expect(mocks.elMessage.error).toHaveBeenCalledWith('操作失败')
  })

  it('加载错误时显示 el-alert', async () => {
    mocks.state!.favoritesError.value = '加载失败'
    const wrapper = mountFavoritesView()
    await flushPromises()

    expect(wrapper.find('.el-alert').exists()).toBe(true)
  })

  it('总数大于 pageSize 时显示分页器', async () => {
    mocks.state!.favoritesList.value = mockPapers
    mocks.state!.favoritesTotal.value = 25
    const wrapper = mountFavoritesView()
    await flushPromises()

    expect(wrapper.find('.favorites-view__pagination').exists()).toBe(true)
    expect(wrapper.find('.el-pagination').exists()).toBe(true)
  })

  it('总数不大于 pageSize 时不显示分页器', async () => {
    mocks.state!.favoritesList.value = mockPapers
    mocks.state!.favoritesTotal.value = 5
    const wrapper = mountFavoritesView()
    await flushPromises()

    expect(wrapper.find('.favorites-view__pagination').exists()).toBe(false)
  })
})
