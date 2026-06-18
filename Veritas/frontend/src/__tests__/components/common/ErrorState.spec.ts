/**
 * ErrorState 组件测试
 *
 * 注：被测组件 ErrorState.vue 模板中未定义 <slot>，
 *     故任务清单中的"默认 slot 渲染自定义内容"用例不适用，已移除。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ErrorState from '@/components/common/ErrorState.vue'

// Mock @element-plus/icons-vue
vi.mock('@element-plus/icons-vue', () => ({
  WarningFilled: {
    name: 'WarningFilled',
    template: '<i class="mock-icon mock-icon-warning">warning</i>'
  }
}))

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElIcon: {
    name: 'ElIcon',
    props: ['size', 'color'],
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

async function mountErrorState(props: {
  title?: string
  description?: string
  error?: Error | string | null
  actionText?: string
} = {}) {
  return mount(ErrorState, {
    props: { ...props } as any
  })
}

describe('ErrorState', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('默认 props 渲染：title="加载失败"，actionText="重试"', async () => {
    const wrapper = await mountErrorState()
    expect(wrapper.find('.error-state__title').text()).toBe('加载失败')
    const btn = wrapper.find('.error-state__action')
    expect(btn.exists()).toBe(true)
    expect(btn.text()).toBe('重试')
  })

  it('自定义 title/description 应正确渲染', async () => {
    const wrapper = await mountErrorState({
      title: '请求出错',
      description: '网络连接失败，请检查网络'
    })
    expect(wrapper.find('.error-state__title').text()).toBe('请求出错')
    expect(wrapper.find('.error-state__description').text()).toBe('网络连接失败，请检查网络')
  })

  it('error 为 Error 对象时应显示 error.message', async () => {
    const wrapper = await mountErrorState({
      error: new Error('服务器内部错误')
    })
    expect(wrapper.find('.error-state__description').text()).toBe('服务器内部错误')
  })

  it('error 为字符串时应显示该字符串', async () => {
    const wrapper = await mountErrorState({
      error: '请求超时'
    })
    expect(wrapper.find('.error-state__description').text()).toBe('请求超时')
  })

  it('error 和 description 都未提供时应显示"请稍后重试"', async () => {
    const wrapper = await mountErrorState()
    expect(wrapper.find('.error-state__description').text()).toBe('请稍后重试')
  })

  it('点击重试按钮应 emit("retry") 事件', async () => {
    const wrapper = await mountErrorState()
    const btn = wrapper.find('.error-state__action')
    await btn.trigger('click')
    expect(wrapper.emitted('retry')).toBeTruthy()
    expect(wrapper.emitted('retry')?.length).toBe(1)
  })

  it('自定义 actionText 应正确渲染', async () => {
    const wrapper = await mountErrorState({ actionText: '重新加载' })
    expect(wrapper.find('.error-state__action').text()).toBe('重新加载')
  })
})
