import { describe, it, expect, beforeEach, vi } from 'vitest'
import { shallowMount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import HomeView from '@/views/HomeView.vue'
import { useUserStore } from '@/stores/userStore'
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

  it('renders AppHeader and AppFooter', () => {
    const wrapper = shallowMount(HomeView)
    expect(wrapper.findComponent({ name: 'AppHeader' }).exists()).toBe(true)
    expect(wrapper.findComponent({ name: 'AppFooter' }).exists()).toBe(true)
  })

  it('renders search title and area', () => {
    const wrapper = shallowMount(HomeView)
    expect(wrapper.find('.home-view__title').exists()).toBe(true)
    expect(wrapper.find('.home-view__search').exists()).toBe(true)
  })

  it('displays recent searches from localStorage', () => {
    storage.saveRecentSearch('test-query')
    const wrapper = shallowMount(HomeView)
    expect(wrapper.find('.home-view__recent').exists()).toBe(true)
  })

  it('shows no recent searches when empty', () => {
    const wrapper = shallowMount(HomeView)
    expect(wrapper.find('.home-view__recent').exists()).toBe(false)
  })

  it('unauthenticated user is not logged in', () => {
    shallowMount(HomeView)
    const userStore = useUserStore()
    expect(userStore.isLoggedIn).toBe(false)
  })

  it('clears recent searches when clear button clicked', async () => {
    storage.saveRecentSearch('test')
    const wrapper = shallowMount(HomeView)

    expect(wrapper.find('.home-view__recent').exists()).toBe(true)

    await wrapper.find('.home-view__clear-btn').trigger('click')
    expect(storage.getRecentSearches()).toEqual([])
  })
})
