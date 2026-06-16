/**
 * LoadingOverlay 组件测试
 */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import LoadingOverlay from '@/components/common/LoadingOverlay.vue'

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElIcon: {
    props: ['size'],
    template: '<i class="el-icon"><slot /></i>'
  },
  Loading: { template: '<i>loading-icon</i>' }
}))

vi.mock('@element-plus/icons-vue', () => ({
  Loading: { template: '<i>loading-icon</i>' }
}))

async function mountLoadingOverlay(props: {
  visible?: boolean
  text?: string
  zIndex?: number
} = {}) {
  return mount(LoadingOverlay, {
    props: {
      visible: true,
      ...props
    },
    global: {
      stubs: {
        Teleport: {
          template: '<div class="teleport"><slot /></div>'
        }
      }
    }
  })
}

describe('LoadingOverlay', () => {
  it('visible=true 时应渲染遮罩', async () => {
    const wrapper = await mountLoadingOverlay({ visible: true })
    expect(wrapper.find('.loading-overlay').exists()).toBe(true)
  })

  it('visible=false 时不应渲染遮罩', async () => {
    const wrapper = await mountLoadingOverlay({ visible: false })
    expect(wrapper.find('.loading-overlay').exists()).toBe(false)
  })

  it('应显示自定义文字', async () => {
    const wrapper = await mountLoadingOverlay({
      visible: true,
      text: '正在搜索...'
    })
    expect(wrapper.find('.loading-overlay__text').text()).toBe('正在搜索...')
  })

  it('默认文字应为"加载中..."', async () => {
    const wrapper = await mountLoadingOverlay({ visible: true })
    expect(wrapper.find('.loading-overlay__text').text()).toBe('加载中...')
  })
})
