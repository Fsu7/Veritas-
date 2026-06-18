/**
 * EmptyState 组件测试
 *
 * 注：被测组件 EmptyState.vue 模板中未定义 <slot>，
 *     故任务清单中的"默认 slot 渲染自定义内容"用例不适用，已移除。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import EmptyState from '@/components/common/EmptyState.vue'

// Mock @element-plus/icons-vue：用占位组件便于断言
vi.mock('@element-plus/icons-vue', () => ({
  Box: { name: 'Box', template: '<i class="mock-icon mock-icon-box">box</i>' },
  Document: { name: 'Document', template: '<i class="mock-icon mock-icon-document">document</i>' },
  FolderOpened: { name: 'FolderOpened', template: '<i class="mock-icon mock-icon-folder">folder</i>' },
  Search: { name: 'Search', template: '<i class="mock-icon mock-icon-search">search</i>' }
}))

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElIcon: {
    name: 'ElIcon',
    props: ['size'],
    template: '<i class="el-icon"><slot /></i>'
  },
  ElButton: {
    name: 'ElButton',
    props: ['type', 'size'],
    emits: ['click'],
    template: '<button class="el-button" @click="$emit(\'click\')"><slot /></button>'
  }
}))

// ============ 辅助 ============

async function mountEmptyState(props: {
  title?: string
  description?: string
  icon?: 'box' | 'document' | 'folder' | 'search'
  actionText?: string
} = {}) {
  return mount(EmptyState, {
    props: { ...props } as any
  })
}

describe('EmptyState', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('默认 props 渲染：title 应为"暂无数据"', async () => {
    const wrapper = await mountEmptyState()
    expect(wrapper.find('.empty-state__title').text()).toBe('暂无数据')
  })

  it('自定义 title/description 应正确渲染', async () => {
    const wrapper = await mountEmptyState({
      title: '没有匹配结果',
      description: '请尝试调整筛选条件'
    })
    expect(wrapper.find('.empty-state__title').text()).toBe('没有匹配结果')
    expect(wrapper.find('.empty-state__description').text()).toBe('请尝试调整筛选条件')
  })

  it('icon="search" 时应渲染 Search 图标', async () => {
    const wrapper = await mountEmptyState({ icon: 'search' })
    expect(wrapper.find('.mock-icon-search').exists()).toBe(true)
    // 默认 box 不应出现
    expect(wrapper.find('.mock-icon-box').exists()).toBe(false)
  })

  it('提供 actionText 时应显示操作按钮', async () => {
    const wrapper = await mountEmptyState({ actionText: '刷新' })
    const btn = wrapper.find('.empty-state__action')
    expect(btn.exists()).toBe(true)
    expect(btn.text()).toBe('刷新')
  })

  it('未提供 actionText 时不应显示操作按钮', async () => {
    const wrapper = await mountEmptyState()
    expect(wrapper.find('.empty-state__action').exists()).toBe(false)
  })

  it('点击 action 按钮应 emit("action") 事件', async () => {
    const wrapper = await mountEmptyState({ actionText: '刷新' })
    const btn = wrapper.find('.empty-state__action')
    await btn.trigger('click')
    expect(wrapper.emitted('action')).toBeTruthy()
    expect(wrapper.emitted('action')?.length).toBe(1)
  })
})
