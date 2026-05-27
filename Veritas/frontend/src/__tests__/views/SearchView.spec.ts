import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { usePaperStore } from '@/stores/paperStore'
import SearchView from '@/views/SearchView.vue'

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
  useRoute: () => ({
    query: { q: 'Multi-Agent' },
  }),
}))

vi.mock('@/api/paper', () => ({
  paperApi: {
    search: vi.fn().mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      size: 10,
      totalPages: 0
    }),
    addFavorite: vi.fn(),
    removeFavorite: vi.fn()
  }
}))

describe('SearchView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('renders search input area', () => {
    const wrapper = mount(SearchView)
    expect(wrapper.find('.search-view__header').exists()).toBe(true)
  })

  it('renders search-view container', () => {
    const wrapper = mount(SearchView)
    expect(wrapper.find('.search-view').exists()).toBe(true)
  })

  it('has BEM class names', () => {
    const wrapper = mount(SearchView)
    expect(wrapper.find('.search-view__header').exists()).toBe(true)
  })

  it('uses paperStore for search results', () => {
    const store = usePaperStore()
    expect(store.searchResults).toBeDefined()
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })
})
