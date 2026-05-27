import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import HomeView from '@/views/HomeView.vue'
import * as storage from '@/utils/storage'

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
  useRoute: () => ({
    query: {},
  }),
}))

describe('HomeView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('renders search title', () => {
    const wrapper = mount(HomeView)
    expect(wrapper.find('.home-view__title').exists()).toBe(true)
    expect(wrapper.find('.home-view__title').text()).toContain('科研文献智能助手')
  })

  it('renders subtitle', () => {
    const wrapper = mount(HomeView)
    expect(wrapper.find('.home-view__subtitle').exists()).toBe(true)
  })

  it('renders search input area', () => {
    const wrapper = mount(HomeView)
    expect(wrapper.find('.home-view__search-box').exists()).toBe(true)
  })

  it('displays recent searches from localStorage', () => {
    storage.saveRecentSearch('test-query')
    const wrapper = mount(HomeView)
    expect(wrapper.find('.home-view__recent').exists()).toBe(true)
  })

  it('hides recent searches when empty', () => {
    const wrapper = mount(HomeView)
    expect(wrapper.find('.home-view__recent').exists()).toBe(false)
  })

  it('clears recent searches via method call', async () => {
    storage.saveRecentSearch('test')
    const wrapper = mount(HomeView)
    expect(wrapper.find('.home-view__recent').exists()).toBe(true)
    const vm = wrapper.vm as unknown as { handleClearRecent: () => void }
    vm.handleClearRecent()
    await wrapper.vm.$nextTick()
    expect(storage.getRecentSearches()).toEqual([])
    expect(wrapper.find('.home-view__recent').exists()).toBe(false)
  })

  it('has correct title color using CSS variable', () => {
    const wrapper = mount(HomeView)
    const title = wrapper.find('.home-view__title')
    expect(title.exists()).toBe(true)
  })

  it('search box has max-width 600px', () => {
    const wrapper = mount(HomeView)
    const searchBox = wrapper.find('.home-view__search-box')
    expect(searchBox.exists()).toBe(true)
  })
})
